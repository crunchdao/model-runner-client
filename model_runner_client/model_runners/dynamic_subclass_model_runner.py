from model_runner_client.model_runners.model_runner import ModelRunner
from model_runner_client.grpc.generated.commons_pb2 import Variant, VariantType, Argument, KwArgument
from model_runner_client.grpc.generated.dynamic_subclass_pb2 import SetupRequest, SetupResponse, CallRequest, CallResponse
from model_runner_client.grpc.generated.dynamic_subclass_pb2_grpc import DynamicSubclassServiceStub
from model_runner_client.utils.datatype_transformer import decode_data
from model_runner_client.errors import InvalidCoordinatorUsageError


class DynamicSubclassModelRunner(ModelRunner):

    def __init__(self,
                 base_classname: str,
                 model_id: str,
                 model_name: str,
                 ip: str,
                 port: int,
                 infos: dict,
                 instance_args: list[Argument] = None,
                 instance_kwargs: list[KwArgument] = None,
                 ):
        """
        Initialize the DynamicSubclassModelRunner.
    
        Args:
            base_classname (str): The base class used to find the model class and instantiate it (Remotely).
                Please provide the full name with module name, Example: "model_runner_client.model_runners.dynamic_subclass_model_runner.ModelRunner".
            model_id (str): Unique identifier of the model instance.
            model_name (str): The name of the model.
            ip (str): The IP address of the model runner service.
            port (int): The port number of the model runner service.
            instance_args (list[Argument]): A list of positional arguments to initialize the model instance.
            instance_kwargs (list[KwArgument]): A list of keyword arguments to initialize the model instance.
        """
        self.base_classname = base_classname
        self.instance_args = instance_args
        self.instance_kwargs = instance_kwargs

        self.grpc_stub: DynamicSubclassServiceStub = None

        super().__init__(model_id, model_name, ip, port, infos)

    async def setup(self, grpc_channel) -> tuple[bool, ModelRunner.ErrorType | None]:
        """
        Asynchronously setup the gRPC stub and initialize the model instance
        with the base class name via the DynamicSubclassServiceStub.

        Raises:
            Any exceptions raised during the gRPC Setup call.
        """
        self.grpc_stub = DynamicSubclassServiceStub(grpc_channel)
        setup_response: SetupResponse = await self.grpc_stub.Setup(SetupRequest(className=self.base_classname, instanceArguments=self.instance_args, instanceKwArguments=self.instance_kwargs))
        status_code = setup_response.status.code
        if status_code == 'SUCCESS':
            return True, None
        elif status_code == 'INVALID_ARGUMENT':
            raise InvalidCoordinatorUsageError(setup_response.status.message)
        elif status_code == 'BAD_IMPLEMENTATION':
            return False, self.ErrorType.BAD_IMPLEMENTATION
        else:
            return False, self.ErrorType.FAILED

    async def call(self, method_name: str, args: list[Argument] = None, kwargs: list[KwArgument] = None) -> tuple[any, ModelRunner.ErrorType | None]:
        """
        An asynchronous method for executing a remote procedure call over gRPC using method name,
        arguments, and keyword arguments.

        Args:
            method_name (str): The name of the remote method to invoke.
            args (list[Argument]): A list of positional arguments for the remote method.
            kwargs (list[KwArgument]): A list of keyword arguments for the remote method.
        """
        if self.grpc_stub is None:
            raise InvalidCoordinatorUsageError("gRPC stub is not initialized, please call setup() first.")

        call_request = CallRequest(methodName=method_name, methodArguments=args, methodKwArguments=kwargs)
        call_response: CallResponse = await self.grpc_stub.Call(call_request)
        if call_response is None:
            return None, self.ErrorType.FAILED

        status_code = call_response.status.code
        if status_code == 'SUCCESS':
            return decode_data(call_response.methodResponse.value, call_response.methodResponse.type), None
        elif status_code == 'INVALID_ARGUMENT' or status_code == 'FAILED_PRECONDITION':
            raise InvalidCoordinatorUsageError(call_response.status.message)
        elif status_code == 'BAD_IMPLEMENTATION':
            return None, self.ErrorType.BAD_IMPLEMENTATION
        else:
            return None, self.ErrorType.FAILED
