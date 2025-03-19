from model_runner_client.grpc.generated.commons_pb2 import Argument, KwArgument, Variant, VariantType
from model_runner_client.model_concurrent_runners.model_concurrent_runner import ModelConcurrentRunner, ModelPredictResult
from model_runner_client.model_runners.train_infer_model_runner import TrainInferModelRunner
from model_runner_client.model_runners.model_runner import ModelRunner

from model_runner_client.utils.datatype_transformer import encode_data


class TrainInferModelConcurrentRunner(ModelConcurrentRunner):
    """
    A concurrent runner for managing and invoking methods on TrainInferModelRunner instances.

    This class supports concurrent execution of `train` and `predict` operations across multiple connected models.
    """

    def __init__(self,
                 timeout: int,
                 crunch_id: str,
                 host: str,
                 port: int):
        """
        Initializes the TrainInferModelConcurrentRunner.

        Args:
            timeout (int): Maximum wait time (in seconds) for a model call to complete.
            crunch_id (str): Unique identifier for the specific crunch.
            host (str): Host address of the model orchestrator managing the models.
            port (int): Port of the model orchestrator for communication.
        """
        super().__init__(timeout, crunch_id, host, port)

    def create_model_runner(self, model_id: str, model_name: str, ip: str, port: int, infos: dict) -> ModelRunner:
        """
        Factory method to create an instance of TrainInferModelRunner.
        """
        return TrainInferModelRunner(model_id, model_name, ip, port, infos)

    async def predict(self, argument_type: VariantType, argument_value) -> dict[ModelRunner, ModelPredictResult]:
        """
        Executes the `predict` method concurrently on all connected models.

        Args:
            argument_type: The type of the argument passed for inference (e.g., data type).
            argument_value: The value of the argument passed for inference (e.g., any type of data).

        Returns:
            dict[ModelRunner, ModelPredictResult]: A dictionary where each key is a `ModelRunner` instance, and
                each value is a `ModelPredictResult` object containing the result, error status, or timeout information.
        """
        if type(argument_value) != bytes:
            argument_value = encode_data(argument_value, argument_type)

        return await self._execute_concurrent_method("predict", argument_type, argument_value)

    async def train(self, argument_type, argument_value) -> dict[ModelRunner, ModelPredictResult]:
        raise Exception("Not implemented yet")
