import abc
import asyncio
import logging
from enum import Enum

from model_runner_client.model_cluster import ModelCluster
from model_runner_client.model_runners.model_runner import ModelRunner

logger = logging.getLogger("model_runner_client")


class ModelPredictResult:
    class Status(Enum):
        SUCCESS = "SUCCESS"
        FAILED = "FAILED"
        TIMEOUT = "TIMEOUT"

    def __init__(self, model_runner: ModelRunner, result: any, status: Status):
        self.model_runner = model_runner
        self.result = result
        self.status = status

    def __str__(self):
        return f"ModelPredictResult(model_runner={self.model_runner}, result={self.result}, status={self.status.name})"


class ModelConcurrentRunner:
    def __init__(self, timeout: int, crunch_id: str, host: str, port: int):
        self.timeout = timeout
        self.host = host
        self.port = port
        self.model_cluster = ModelCluster(crunch_id, self.host, self.port, self.create_model_runner)

        # TODO: If the model returns failures exceeding max_consecutive_failures, exclude the model. Maybe also inform the orchestrator to STOP the model ?
        # self.max_consecutive_failures

        # TODO: Implement this. If the option is enabled, allow the model time to recover after a timeout.
        # self.enable_recovery_mode
        # self.recovery_time

    async def init(self):
        await self.model_cluster.init()

    async def sync(self):
        await self.model_cluster.sync()

    @abc.abstractmethod
    def create_model_runner(self, model_id: str, model_name: str, ip: str, port: int) -> ModelRunner:
        pass

    async def _execute_concurrent_method(self, method_name: str, *args, **kwargs) -> dict[ModelRunner, ModelPredictResult]:
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

        logger.debug(f"**ModelConcurrentRunner** Executing '{method_name}' tasks concurrently: {tasks}")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {result.model_runner: result for result in results if not isinstance(result, asyncio.CancelledError)}

    async def _execute_model_method_with_timeout(self, model: ModelRunner, method_name: str, *args, **kwargs) -> ModelPredictResult:
        try:
            # Dynamically fetch the method and call it with the provided arguments
            method = getattr(model, method_name)
            result = await asyncio.wait_for(method(*args, **kwargs), timeout=self.timeout)

            return ModelPredictResult(model, result, ModelPredictResult.Status.SUCCESS)
        except asyncio.TimeoutError:
            return ModelPredictResult(model, None, ModelPredictResult.Status.TIMEOUT)
        except Exception as e:
            return ModelPredictResult(model, str(e), ModelPredictResult.Status.FAILED)
