from typing import Any, Callable, cast
from warnings import warn

from ..grpc.generated.commons_pb2 import Argument, KwArgument
from ..model_concurrent_runners.model_concurrent_runner import ModelConcurrentRunner, ModelPredictResult
from ..model_runners import ArgumentsType, DynamicSubclassModelRunner
from ..model_runners.model_runner import ModelRunner


class _Sentinel:
    pass


class DynamicSubclassModelConcurrentRunner(ModelConcurrentRunner):
    """
    A concurrent runner responsible for managing and invoking dynamic subclass model runners.

    This class interacts with model orchestrators to perform remote method calls concurrently on multiple models.
    """

    def __init__(
        self,
        timeout: int,
        crunch_id: str,
        host: str,
        port: int,
        base_classname: str,
        instance_args: list[Argument] = None,
        instance_kwargs: list[KwArgument] = None,
        **kwargs
    ):
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

        super().__init__(timeout, crunch_id, host, port, **kwargs)

        instance_args = instance_args or []
        instance_kwargs = instance_kwargs or []

        self.base_classname = base_classname
        self.instance_args = instance_args
        self.instance_kwargs = instance_kwargs

    def create_model_runner(
        self,
        **kwargs
    ) -> DynamicSubclassModelRunner:
        return DynamicSubclassModelRunner(
            self.base_classname,
            self.instance_args,
            self.instance_kwargs,
            secure_credentials=self.secure_credentials,
            gateway_credentials=self.gateway_credentials,
            **kwargs
        )

    async def call(
        self,
        method_name: str,
        arguments: ArgumentsType = cast(Any, _Sentinel),
        args: list[Argument] = cast(Any, _Sentinel),
        kwargs: list[KwArgument] = cast(Any, _Sentinel),
        timeout: int | None = None,
        model_runs: list[ModelRunner] | None = None,
    ) -> dict[ModelRunner, ModelPredictResult]:
        """
        Executes a specific method concurrently on all connected model runners.

        Args:
            method_name (str): The name of the method to call on each model runner. For example, "predict" or "update_state".
            arguments (tuple[list[Argument], list[KwArgument]]): The name of the method to call on each model runner. For example, "predict" or "update_state".
            args (list[Argument]): Deprecated, a list of positional arguments to be passed to the method.
            kwargs (list[KwArgument]): Deprecated, a list of keyword arguments to be passed to the method.
           model_runs (list[ModelRunner] | None): A list of model runners to execute the method on. If None, the method
                will execute on all available model runners.

        Returns:
            dict[ModelRunner, ModelPredictResult]: A dictionary where each key is a `ModelRunner` instance
            representing a connected model, and each value is a `ModelPredictResult` object containing the result,
            error status, or timeout information for that model.
        """

        if args is not _Sentinel or kwargs is not _Sentinel:
            warn("Using 'args' and 'kwargs' is deprecated. ", DeprecationWarning, stacklevel=2)

        if arguments is _Sentinel:
            if args is _Sentinel:
                args = []
            if kwargs is _Sentinel:
                kwargs = []

            arguments = (args, kwargs)

        return await self._execute_concurrent_method(
            'call',
            timeout,
            model_runs,
            method_name,
            arguments,
        )
