import abc
import asyncio
import logging
import math
import uuid
from enum import Enum
from typing import Any

import grpc
from grpc.aio import AioRpcError

from ..errors import InvalidCoordinatorUsageError
from ..security.credentials import SecureCredentials
from ..security.grpc_auth_interceptor import StaticAuthMetadata, WalletTlsAuthClientInterceptor
from ..security.tls_peer_key import fetch_peer_rsa_spki_mtls, TlsProbeError, is_tls_connection
from ..security.wallet_gelegation import AuthError

logger = logging.getLogger("model_runner_client.model_runner")


class ModelRunner:
    class ErrorType(Enum):
        GRPC_CONNECTION_FAILED = "GRPC_CONNECTION_FAILED"
        FAILED = "FAILED"
        BAD_IMPLEMENTATION = "BAD_IMPLEMENTATION"
        ABORTED = "ABORTED"
        AUTH_ERROR = "AUTH_ERROR"

    def __init__(
        self,
        deployment_id: str,
        model_id: str,
        model_name: str,
        ip: str,
        port: int,
        infos: dict[str, Any],
        retry_backoff_factor: float = 2,
        secure_credentials: SecureCredentials | None = None
    ):
        self.runner_id = uuid.uuid4().hex  # unique identifier per instance
        self.deployment_id = deployment_id
        self.model_id = model_id
        self.model_name = model_name
        self.ip = ip
        self.port = port
        self.infos = infos
        logger.info(f"New model runner created: {self.model_id}, {self.model_name}, {self.ip}:{self.port}, let's connect it")
        self.retry_backoff_factor = retry_backoff_factor

        self.grpc_channel = None
        self.grpc_health_channel = None
        self.retry_attempts = 5  # args ?
        self.min_retry_interval = 2  # 2 seconds
        self.closed = False
        self.consecutive_failures = 0
        self.consecutive_timeouts = 0
        self.cooldown_calls_remaining = 0

        self.secure_credentials = secure_credentials
        self.server_hostname = f"model-node-{self.model_id}.crunchdao.internal"

    @abc.abstractmethod
    async def setup(self, grpc_channel) -> tuple[bool, ErrorType | None]:
        pass

    async def init(self) -> tuple[bool, ErrorType | None]:
        self.grpc_options: list[tuple[str, any]] = [
            # Very fast reconnection
            ("grpc.initial_reconnect_backoff_ms", 100),  # 100 ms on the first attempt
            ("grpc.min_reconnect_backoff_ms", 100),  # minimum 100 ms
            ("grpc.max_reconnect_backoff_ms", 1000),  # maximum 1 second (avoids excessive hammering)

            #  ("grpc.http2.min_time_between_pings_ms", 1000),
            #  ("grpc.http2.max_pings_without_data", 0),
            ("grpc.keepalive_time_ms", 300000),  # ping every 5 minutes
            ("grpc.keepalive_timeout_ms", 500),  # wait 500ms for ACK
            ("grpc.keepalive_permit_without_calls", 0),
        ]

        is_secure_connection = self.secure_credentials is not None
        if is_secure_connection:
            self.grpc_options.append(("grpc.ssl_target_name_override", self.server_hostname))
            self.grpc_options.append(("grpc.default_authority", self.server_hostname))

        grpc_setup_timeout = 10  # 10s
        for attempt in range(1, self.retry_attempts + 1):
            if self.closed:
                logger.debug(f"Model runner {self.model_id} closed, aborting initialization")
                return False, self.ErrorType.ABORTED
            try:
                if is_secure_connection:
                    await self._connect_secure_channels()
                else:
                    self._connect_insecure_channels()

                await asyncio.wait_for(self.grpc_channel.channel_ready(), timeout=grpc_setup_timeout)
                await asyncio.wait_for(self.grpc_health_channel.channel_ready(), timeout=grpc_setup_timeout)

                # todo what happen is this take long time, need to add timeout ????
                setup_succeed, error = await self.setup(self.grpc_channel)
                if setup_succeed:
                    logger.info(f"model runner: {self.model_id}, {self.model_name}, is connected and ready")
                return setup_succeed, error

            except (AioRpcError, asyncio.TimeoutError) as e:
                if not is_secure_connection and await is_tls_connection(self.ip, self.port):
                    raise InvalidCoordinatorUsageError("The Model Nodes are in secure mode and credentials were not provided for connection.")

                logger.warning(f"Initialization of model runner {self.model_id} failed due to a connection or timeout error: {e}")
                last_error = e

            except InvalidCoordinatorUsageError:
                raise

            except (AuthError, TlsProbeError) as e:
                logger.warning(f"Model runner {self.model_id} initialization failed due to authentication error => {e}")
                return False, self.ErrorType.AUTH_ERROR

            # too large todo improve
            except Exception as e:
                logger.error(f"Unexpected error during initialization of model {self.model_id}", exc_info=True)
                last_error = e

            if attempt < self.retry_attempts:
                backoff_time = self.retry_backoff_factor ** attempt  # Backoff with exponential delay
                logger.warning(f"Retrying in {backoff_time} seconds...")
                await asyncio.sleep(backoff_time)
            else:
                logger.error(f"Model {self.model_id} failed to initialize after {self.retry_attempts} attempts.", exc_info=last_error)
                return False, self.ErrorType.GRPC_CONNECTION_FAILED

    def register_failure(self):
        self.consecutive_failures += 1

    def register_timeout(self):
        self.consecutive_timeouts += 1

    def reset_failures(self):
        self.consecutive_failures = 0

    def reset_timeouts(self):
        self.consecutive_timeouts = 0

    def should_skip_for_timeout_reason(self) -> bool:
        """
        Returns True if the model should skip the current call
        to 'breathe' based on the number of consecutive timeouts.
        The cooldown is expressed in number of calls instead of time.
        """
        if self.cooldown_calls_remaining > 0:
            self.cooldown_calls_remaining -= 1
            return True

        if self.cooldown_calls_remaining == 0:
            self.cooldown_calls_remaining = -1
            return False  # give chance to no timeout

        if self.consecutive_timeouts > 0:
            cooldown_calls = math.ceil(self.consecutive_timeouts / 2)
            self.cooldown_calls_remaining = cooldown_calls
            if cooldown_calls > 0:
                self.cooldown_calls_remaining = cooldown_calls
                logger.debug(
                    f"[{self.model_name}] {self.consecutive_timeouts} consecutive timeouts, "
                    f"cooling down for {cooldown_calls} calls"
                )
                self.cooldown_calls_remaining -= 1
                return True

        return False

    def _connect_insecure_channels(self):
        # Main gRPC channel (for model interaction)
        self.grpc_channel = grpc.aio.insecure_channel(f"{self.ip}:{self.port}", self.grpc_options)
        # Separate health check channel (isolated TCP connection)
        self.grpc_health_channel = grpc.aio.insecure_channel(f"{self.ip}:{self.port}", self.grpc_options)

    async def _connect_secure_channels(self):
        target = f"{self.ip}:{self.port}"
        peer_tls = await fetch_peer_rsa_spki_mtls(
            host=self.ip,
            port=self.port,
            tls_ctx=self.secure_credentials.tls_ctx,
            server_hostname=self.server_hostname
        )

        client_creds = grpc.ssl_channel_credentials(
            root_certificates=peer_tls.leaf_cert_pem,
            private_key=self.secure_credentials.key_bytes,
            certificate_chain=self.secure_credentials.cert_bytes,
        )

        call_creds = grpc.metadata_call_credentials(StaticAuthMetadata(self.secure_credentials.metadata))

        channel_creds = grpc.composite_channel_credentials(client_creds, call_creds)

        self.grpc_channel = grpc.aio.secure_channel(
            target=target,
            credentials=channel_creds,
            options=self.grpc_options,
            interceptors=[
                WalletTlsAuthClientInterceptor(
                    expected_wallet_pub_b58=self.infos.get("cruncher_wallet_pubkey"),
                    expected_hotkey=self.infos.get("cruncher_hotkey"),
                    expected_model_id=self.model_id,
                    tls_pub=peer_tls.spki_der
                )
            ]
        )

        # Separate health check channel (isolated TCP connection)
        self.grpc_health_channel = grpc.aio.secure_channel(target, channel_creds, self.grpc_options)

    async def close(self):
        self.closed = True
        tasks = []
        if self.grpc_channel:
            tasks.append(self.grpc_channel.close())
        if self.grpc_health_channel:
            tasks.append(self.grpc_health_channel.close())

        if tasks:
            await asyncio.gather(*tasks)

        logger.debug(f"Model runner {self.model_id} gRPC connections closed")
