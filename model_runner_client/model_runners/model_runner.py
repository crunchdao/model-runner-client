import abc
import asyncio
import logging
from enum import Enum
from typing import Any

import grpc
from grpc.aio import AioRpcError

from ..errors import InvalidCoordinatorUsageError

logger = logging.getLogger("model_runner_client.model_runner")


class ModelRunner:

    class ErrorType(Enum):
        GRPC_CONNECTION_FAILED = "GRPC_CONNECTION_FAILED"
        FAILED = "FAILED"
        BAD_IMPLEMENTATION = "BAD_IMPLEMENTATION"
        ABORTED = "ABORTED"

    def __init__(
        self,
        deployment_id: str,
        model_id: str,
        model_name: str,
        ip: str,
        port: int,
        infos: dict[str, Any],
        retry_backoff_factor: float = 2
    ):
        self.deployment_id = deployment_id
        self.model_id = model_id
        self.model_name = model_name
        self.ip = ip
        self.port = port
        self.infos = infos
        logger.info(f"New model runner created: {self.model_id}, {self.model_name}, {self.ip}:{self.port}, let's connect it")
        self.retry_backoff_factor = retry_backoff_factor

        self.grpc_channel = None
        self.retry_attempts = 5  # args ?
        self.min_retry_interval = 2  # 2 seconds
        self.closed = False
        self.consecutive_failures = 0
        self.consecutive_timeouts = 0

    @abc.abstractmethod
    async def setup(self, grpc_channel) -> tuple[bool, ErrorType | None]:
        pass

    async def init(self) -> tuple[bool, ErrorType | None]:
        options = [
            # Very fast reconnection
            ("grpc.initial_reconnect_backoff_ms", 100),  # 100 ms on the first attempt
            ("grpc.min_reconnect_backoff_ms", 100),  # minimum 100 ms
            ("grpc.max_reconnect_backoff_ms", 1000),  # maximum 1 second (avoids excessive hammering)

          #  ("grpc.http2.min_time_between_pings_ms", 1000),
          #  ("grpc.http2.max_pings_without_data", 0),
            ("grpc.keepalive_time_ms", 300000),  # ping every 5 minutes
            ("grpc.keepalive_timeout_ms", 500),  # wait 500ms for ACK
            ("grpc.keepalive_permit_without_calls", 1),
        ]

        grpc_setup_timeout = 10 # 10s
        for attempt in range(1, self.retry_attempts + 1):
            if self.closed:
                logger.debug(f"Model runner {self.model_id} closed, aborting initialization")
                return False, self.ErrorType.ABORTED
            try:
                self.grpc_channel = grpc.aio.insecure_channel(f"{self.ip}:{self.port}", options)
                await asyncio.wait_for(self.grpc_channel.channel_ready(), timeout=grpc_setup_timeout)
                # todo what happen is this take long time, need to add timeout ????
                setup_succeed, error = await self.setup(self.grpc_channel)
                if setup_succeed:
                    logger.info(f"model runner: {self.model_id}, {self.model_name}, is connected and ready")
                return setup_succeed, error

            except (AioRpcError, asyncio.TimeoutError) as e:
                logger.warning(f"Model runner {self.model_id} initialization failed due to connection or timeout error.")
                last_error = e

            except InvalidCoordinatorUsageError:
                raise

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

    async def close(self):
        self.closed = True
        if self.grpc_channel:
            await self.grpc_channel.close()
            logger.debug(f"Model runner {self.model_id} grpc connection closed")
