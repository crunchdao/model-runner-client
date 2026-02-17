import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

from grpc import StatusCode
from grpc.aio import AioRpcError
from grpc_health.v1 import health_pb2, health_pb2_grpc

from ..model_cluster import ModelCluster
from ..model_runners import ModelRunner
from ..security.credentials import SecureCredentials
from ..security.gateway_credentials import GatewayCredentials
from ..security.wallet_gelegation import AuthError

logger = logging.getLogger("model_runner_client")


@dataclass
class ModelPredictResult:
    class Status(Enum):
        SUCCESS = "SUCCESS"
        FAILED = "FAILED"
        TIMEOUT = "TIMEOUT"

    model_runner: ModelRunner
    result: Any
    status: Status
    exec_time_us: int

    @staticmethod
    def of_success(model_runner: ModelRunner, result: Any, exec_time: int) -> 'ModelPredictResult':
        return ModelPredictResult(model_runner, result, ModelPredictResult.Status.SUCCESS, exec_time)

    @staticmethod
    def of_failed(model_runner: ModelRunner, exec_time: int) -> 'ModelPredictResult':
        return ModelPredictResult(model_runner, None, ModelPredictResult.Status.FAILED, exec_time)

    @staticmethod
    def of_timeout(model_runner: ModelRunner, exec_time: int) -> 'ModelPredictResult':
        return ModelPredictResult(model_runner, None, ModelPredictResult.Status.TIMEOUT, exec_time)


class ModelConcurrentRunner(ABC):
    """
    Each model is monitored to ensure it remains responsive and stable.
    Two counters are tracked internally:
        - Failures: When a model returns an error.
        - Timeouts: When a model takes too long to respond.

    When a model times out repeatedly, the system pauses it for a few prediction cycles.
    The more timeouts occur, the longer the pause becomes, allowing the model time to recover
    before being queried again.

    Every 20% of the allowed timeout limit, the model performs a health check over a separate connection:
        - If the model reports as healthy (SERVING), it remains active but incurs a minor penalty.
        - If it reports as unhealthy or fails the check, the system reconnects it automatically.

    Once the model responds successfully again, all penalties are cleared, and it resumes normal operation.

    If the model continues to fail or exceed its timeout limit, it is marked as faulty and stopped.
    This can be avoided by setting `report_failure` to False in the `ModelConcurrentRunner` constructor.

    The `secure_credentials` parameter expects a `SecureCredentials` object if the Model nodes are set up
    in secure mode.

    The `report_failure` parameter is set to True by default. If set to False, the system will not report and stop the model node
    Very useful for debugging purposes (example, when you are testing the call interface or TLS certificate is not valid).
    """
    MAX_CONSECUTIVE_FAILURES = 3
    MAX_CONSECUTIVE_TIMEOUTS = 3

    def __init__(
        self,
        timeout: int,
        crunch_id: str,
        host: str,
        port: int,
        max_consecutive_failures: int = MAX_CONSECUTIVE_FAILURES,
        max_consecutive_timeouts: int = MAX_CONSECUTIVE_TIMEOUTS,
        secure_credentials: SecureCredentials | None = None,
        gateway_credentials: GatewayCredentials | None = None,
        report_failure: bool = True,
    ):
        self.timeout = timeout
        self.host = host
        self.port = port
        self.model_cluster = ModelCluster(
            crunch_id,
            self.host,
            self.port,
            self.create_model_runner,
            report_failure=report_failure
        )

        self.max_consecutive_failures = max_consecutive_failures
        self.max_consecutive_timeout = max_consecutive_timeouts

        self.health_check_threshold = max(1, int(self.max_consecutive_timeout * 0.2))
        self.secure_credentials = secure_credentials
        self.gateway_credentials = gateway_credentials

        # TODO: Add recovery mode functionality for handling model timeouts.
        # self.enable_recovery_mode
        # self.recovery_time

    async def init(self):
        await self.model_cluster.init()

    async def sync(self):
        await self.model_cluster.sync()

    @abstractmethod
    def create_model_runner(
        self,
        **kwargs  # Refer to the ModelRunner constructor
    ) -> ModelRunner:
        pass

    async def _execute_concurrent_method(
        self,
        method_name: str,
        timeout: int | None = None,
        model_runs: list[ModelRunner] | None = None,
        *args: tuple[Any],
        **kwargs: dict[str, Any]
    ) -> dict[ModelRunner, ModelPredictResult]:
        """
        Executes a method concurrently across all models in the cluster.

        Args:
            method_name (str): Name of the method to call on each model.
            *args: Positional arguments for the method.
            **kwargs: Keyword arguments for the method.

        Returns:
            dict[ModelRunner, ModelPredictResult]: A dictionary where the key is the model runner,
            and the value is the result or error status of the method call.
        """
        model_runs = model_runs or self.model_cluster.models_run.values()
        tasks = [
            self._execute_model_method_with_timeout(model, method_name, timeout, *args, **kwargs)
            for model in model_runs
        ]

        logger.debug(f"Executing '{method_name}' tasks concurrently: {tasks}")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            result.model_runner: result
            for result in results
            if not isinstance(result, BaseException)
        }


    async def _execute_model_method_with_timeout(
        self,
        model: ModelRunner,
        method_name: str,
        timeout: int | None = None,
        *args: tuple[Any],
        **kwargs: dict[str, Any],
    ) -> ModelPredictResult:
        start_time = asyncio.get_event_loop().time()
        exec_time_f = lambda: int((asyncio.get_event_loop().time() - start_time) * 1_000_000)
        timeout = timeout or self.timeout
        try:
            method = getattr(model, method_name)

            if model.should_skip_for_timeout_reason():
                raise asyncio.TimeoutError()

            try:
                result, error = await method(*args, **kwargs, timeout=timeout)
            except ValueError:  # Decode error
                error = ModelRunner.ErrorType.FAILED

            exec_time = exec_time_f()

            if not error:
                model.reset_failures()
                model.reset_timeouts()

                return ModelPredictResult.of_success(model, result, exec_time)

            if error == ModelRunner.ErrorType.BAD_IMPLEMENTATION:
                asyncio.create_task(self.model_cluster.process_failure(model, 'BAD_IMPLEMENTATION'))  # The model will be stopped
            else:
                model.register_failure()

                if self.max_consecutive_failures and model.consecutive_failures > self.max_consecutive_failures:
                    asyncio.create_task(self.model_cluster.process_failure(model, 'MULTIPLE_FAILED'))

            return ModelPredictResult.of_failed(model, exec_time)

        except (asyncio.TimeoutError, AioRpcError) as e:
            exec_time = exec_time_f()

            logger.debug(
                f"Method {method_name} on model {model.model_id}, {model.model_name} timed out after {timeout} seconds.",
                exc_info=True
            )

            if not (isinstance(e, AioRpcError) and (e.code() in {StatusCode.RESOURCE_EXHAUSTED, StatusCode.DEADLINE_EXCEEDED})) and not isinstance(e, asyncio.TimeoutError):
                logger.error(f"Unexpected error during concurrent execution of method {method_name} on model {model.model_id}", exc_info=True)

            health_serving = True

            # Perform health check when consecutive timeouts reach the threshold
            if model.consecutive_timeouts > 0 and (model.consecutive_timeouts % self.health_check_threshold) == 0:
                try:
                    hstub = health_pb2_grpc.HealthStub(model.grpc_health_channel)
                    resp = await hstub.Check(
                        health_pb2.HealthCheckRequest(service=""),
                        timeout=timeout,
                        wait_for_ready=False
                    )
                    health_serving = (resp.status == health_pb2.HealthCheckResponse.SERVING)
                except Exception as he:
                    health_serving = False
                    logger.warning(f"Health check failed for model {model.model_id}, {model.model_name}: {he}")

            # Determine action: penalize or reconnect
            if health_serving:
                model.register_timeout()
            else:
                logger.debug(f"Health not SERVING for model {model.model_id}; scheduling reconnect.")
                asyncio.create_task(self.model_cluster.reconnect_model_runner(model))

            if self.max_consecutive_timeout and model.consecutive_timeouts > self.max_consecutive_timeout:
                asyncio.create_task(self.model_cluster.process_failure(model, 'MULTIPLE_TIMEOUT'))

            return ModelPredictResult.of_timeout(model, exec_time)

        except AuthError as e:
            logger.error(f"Auth error during concurrent execution of method {method_name} on model {model.model_id}: {e}")
            asyncio.create_task(self.model_cluster.process_failure(model, 'CONNECTION_FAILED', str(e)))

        except Exception:
            logger.error(f"Unexpected error during concurrent execution of method {method_name} on model {model.model_id}", exc_info=True)

            return ModelPredictResult.of_failed(model, exec_time_f())