import logging

from model_runner_client.model_runners.model_runner import ModelRunner
from model_runner_client.grpc.generated.train_infer_pb2_grpc import TrainInferServiceStub
from model_runner_client.grpc.generated.train_infer_pb2 import InferRequest, InferResponse, Trai
from model_runner_client.grpc.generated.commons_pb2 import Variant, VariantType
from google.protobuf import empty_pb2

from model_runner_client.utils.datatype_transformer import decode_data

logger = logging.getLogger("model_runner_client")


class TrainInferModelRunner(ModelRunner):
    def __init__(self,
                 model_id: str,
                 model_name: str,
                 ip: str,
                 port: int):
        """
        Initialize the TrainInferModelRunner.

        Args:
            model_id (str): Unique identifier of the model instance.
            model_name (str): The name of the model.
            ip (str): The IP address of the model runner service.
            port (int): The port number of the model runner service.
        """

        self.grpc_stub = None
        super().__init__(model_id, model_name, ip, port)

    async def setup(self, grpc_channel):
        self.grpc_stub = TrainInferServiceStub(self.grpc_channel)
        await self.grpc_stub.Setup(empty_pb2.Empty())

    async def predict(self, argument_type: VariantType, argument_value: bytes):
        logger.debug(f"**ModelRunner** Doing prediction of model_id:{self.model_id}, name:{self.model_name}, argument_type:{argument_type}")
        prediction_request = InferRequest(Variant(type=argument_type, value=argument_value))

        response: InferResponse = await self.grpc_stub.Infer(prediction_request)

        return decode_data(response.prediction.value, response.prediction.type)

    async def train(self, argument_type: VariantType, argument_value: bytes):
        raise Exception("Not implemented yet")
