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
from ..model_runners.model_runner import ModelRunner

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
    ):
        self.timeout = timeout
        self.host = host
        self.port = port
        self.model_cluster = ModelCluster(crunch_id, self.host, self.port, self.create_model_runner)

        self.max_consecutive_failures = max_consecutive_failures
        self.max_consecutive_timeout = max_consecutive_timeouts

        # TODO: Implement this. If the option is enabled, allow the model time to recover after a timeout.
        # self.enable_recovery_mode
        # self.recovery_time

    async def init(self):
        await self.model_cluster.init()

    async def sync(self):
        await self.model_cluster.sync()

    @abstractmethod
    def create_model_runner(
        self,
        deployment_id: str,
        model_id: str,
        model_name: str,
        ip: str,
        port: int,
        infos: dict[str, Any]
    ) -> ModelRunner:
        pass

    async def _execute_concurrent_method(
        self,
        method_name: str,
        *args: tuple[Any],
        **kwargs: dict[str, Any]
    ) -> dict[ModelRunner, ModelPredictResult]:
        """
        Executes a method concurrently across all models in the cluster.

        Args:
            method_name (str): Name of the method to call on each model.
            *args: Positional arguments to pass to the method.
            **kwargs: Keyword arguments to pass to the method.

        Returns:
            dict[ModelRunner, ModelPredictResult]: A dictionary where the key is the model runner,
            and the value is the result or error status of the method call.
        """

        tasks = [
            self._execute_model_method_with_timeout(model, method_name, *args, **kwargs)
            for model in self.model_cluster.models_run.values()
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
        *args: tuple[Any],
        **kwargs: dict[str, Any],
    ) -> ModelPredictResult:

        start_time = asyncio.get_event_loop().time()
        exec_time_f = lambda: int((asyncio.get_event_loop().time() - start_time) * 1_000_000)

        try:
            method = getattr(model, method_name)
            try:
                result, error = await method(*args, **kwargs, timeout=self.timeout)
            except ValueError:  # decode error
                error = ModelRunner.ErrorType.FAILED

            exec_time = exec_time_f()

            if not error:
                model.reset_failures()
                model.reset_timeouts()

                return ModelPredictResult.of_success(model, result, exec_time)

            if error == ModelRunner.ErrorType.BAD_IMPLEMENTATION:
                # TODO(Abdennour), don't this need to be awaited?
                asyncio.create_task(self.model_cluster.process_failure(model, 'BAD_IMPLEMENTATION'))  # the model will be stopped
            else:
                model.register_failure()

                if self.max_consecutive_failures and model.consecutive_failures > self.max_consecutive_failures:
                    # TODO(Abdennour), don't this need to be awaited?
                    asyncio.create_task(self.model_cluster.process_failure(model, 'MULTIPLE_FAILED'))

            return ModelPredictResult.of_failed(model, exec_time)

        except (asyncio.TimeoutError, AioRpcError) as e:
            exec_time = exec_time_f()

            logger.warning(f"Method {method_name} on model {model.model_id}, {model.model_name} timed out after {self.timeout} seconds.", exc_info=True)

            # 1) Busy case: RESOURCE_EXHAUSTED means the server rejected because it's running another call (basically the last call who timeout)
            if isinstance(e, AioRpcError) and e.code() == StatusCode.RESOURCE_EXHAUSTED:
                logger.debug(f"The model runner {model.model_id} is busy (RESOURCE_EXHAUSTED). No penalty is applied while it recovers")
                return ModelPredictResult.of_timeout(model, exec_time)  # neutral, no penalty

            # 2) Health check
            health_serving = False
            try:
                hstub = health_pb2_grpc.HealthStub(model.grpc_channel)
                resp = await hstub.Check(
                    health_pb2.HealthCheckRequest(service=""),
                    timeout=self.timeout,
                    wait_for_ready=False
                )
                health_serving = (resp.status == health_pb2.HealthCheckResponse.SERVING)
            except Exception as he:
                logger.warning(f"Health check failed for model {model.model_id}, {model.model_name}: {he}")

            # 3) Decision: penalize vs reconnect
            if health_serving:
                # Application timeout while service is SERVING => penalize
                model.register_timeout()
            else:
                # Health failed or NOT_SERVING => reconnect
                logger.debug(f"Health not SERVING for model {model.model_id}; scheduling reconnect.")
                asyncio.create_task(self.model_cluster.reconnect_model_runner(model))


            if self.max_consecutive_timeout and model.consecutive_timeouts > self.max_consecutive_timeout:
                asyncio.create_task(self.model_cluster.process_failure(model, 'MULTIPLE_TIMEOUT'))

            return ModelPredictResult.of_timeout(model, exec_time)

        except Exception:
            logger.error(f"Unexpected error during concurrent execution of method {method_name} on model {model.model_id}", exc_info=True)

            return ModelPredictResult.of_failed(model)
