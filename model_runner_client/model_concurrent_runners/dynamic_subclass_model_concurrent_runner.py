from model_runner_client.grpc.generated.commons_pb2 import Argument, KwArgument
from model_runner_client.model_concurrent_runners.model_concurrent_runner import ModelConcurrentRunner, ModelPredictResult
from model_runner_client.model_runners.dynamic_subclass_model_runner import DynamicSubclassModelRunner
from model_runner_client.model_runners.model_runner import ModelRunner


class DynamicSubclassModelConcurrentRunner(ModelConcurrentRunner):
    """
    A concurrent runner responsible for managing and invoking dynamic subclass model runners.

    This class interacts with model orchestrators to perform remote method calls concurrently on multiple models.
    """

    def __init__(self,
                 timeout: int,
                 crunch_id: str,
                 host: str,
                 port: int,
                 base_classname,
                 instance_args: list[Argument] = None,
                 instance_kwargs: list[KwArgument] = None):
        """
        Initializes the DynamicSubclassModelConcurrentRunner.

        Args:
            timeout (int): Maximum wait time (in seconds) for a model call to complete.
            crunch_id (str): Unique identifier of specific crunch.
            host (str): Host address of the model orchestrator for accessing connected/available models.
            port (int): Port of the model orchestrator for communication.
            base_classname: The base classname used to identify and implement the first matching class.
            instance_args (list[Argument]): Positional arguments passed to the implementation of the identified class.
            instance_kwargs (list[KwArgument]): Keyword arguments passed to the implementation of the identified class.
        """
        self.base_classname = base_classname
        self.instance_args = instance_args
        self.instance_kwargs = instance_kwargs

        super().__init__(timeout, crunch_id, host, port)

    def create_model_runner(self, model_id: str, model_name: str, ip: str, port: int, infos: dict) -> ModelRunner:
        """
        Factory method to create a model runner instance
        """
        return DynamicSubclassModelRunner(self.base_classname, model_id, model_name, ip, port, infos, self.instance_args, self.instance_kwargs)

    async def call(self, method_name: str, args: list[Argument] = None, kwargs: list[KwArgument] = None) -> dict[ModelRunner, ModelPredictResult]:
        """
        Executes a specific method concurrently on all connected model runners.

        Args:
            method_name (str): The name of the method to call on each model runner. For example, "predict" or "update_state".
            args (list[Argument]): A list of positional arguments to be passed to the method.
            kwargs (list[KwArgument]): A list of keyword arguments to be passed to the method.

        Returns:
            dict[ModelRunner, ModelPredictResult]: A dictionary where each key is a `ModelRunner` instance
            representing a connected model, and each value is a `ModelPredictResult` object containing the result,
            error status, or timeout information for that model.
        """
        return await self._execute_concurrent_method('call', method_name, args, kwargs)
