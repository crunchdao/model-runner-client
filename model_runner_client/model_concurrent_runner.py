import asyncio
import logging
from enum import Enum

from model_runner_client.model_cluster import ModelCluster
from model_runner_client.model_runner import ModelRunner
from model_runner_client.protos.model_runner_pb2 import DataType

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
        self.model_cluster = ModelCluster(crunch_id, self.host, self.port)

        # TODO: If the model returns failures exceeding max_consecutive_failures, exclude the model. Maybe also inform the orchestrator to STOP the model ?
        #self.max_consecutive_failures

        # TODO: Implement this. If the option is enabled, allow the model time to recover after a timeout.
        #self.enable_recovery_mode
        #self.recovery_time


    async def init(self):
        await self.model_cluster.init()

    async def sync(self):
        await self.model_cluster.sync()

    async def predict(self, argument_type: DataType, argument_value: bytes) -> dict[ModelRunner, ModelPredictResult]:
        tasks = [self._predict_with_timeout(model, argument_type, argument_value)
                 for model in self.model_cluster.models_run.values()]
        logger.debug(f"**ModelConcurrentRunner** predict tasks: {tasks}")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {result.model_runner: result for result in results}

    async def _predict_with_timeout(self, model: ModelRunner, argument_type: DataType, argument_value: bytes):
        try:
            result = await asyncio.wait_for(
                model.predict(argument_type, argument_value), timeout=self.timeout
            )
            return ModelPredictResult(model, result, ModelPredictResult.Status.SUCCESS)
        except asyncio.TimeoutError:
            return ModelPredictResult(model, None, ModelPredictResult.Status.TIMEOUT)
        except Exception as e:
            return ModelPredictResult(model, str(e), ModelPredictResult.Status.FAILED)