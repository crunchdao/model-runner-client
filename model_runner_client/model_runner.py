import asyncio
import atexit
import logging

import grpc
from google.protobuf import empty_pb2
from grpc.aio import AioRpcError

from model_runner_client.protos.model_runner_pb2 import DataType, InferRequest
from model_runner_client.protos.model_runner_pb2_grpc import ModelRunnerStub
from model_runner_client.utils.datatype_transformer import decode_data

logger = logging.getLogger("model_runner_client")


class ModelRunner:
    def __init__(self, model_id: str, model_name: str, ip: str, port: int):

        self.model_id = model_id
        self.model_name = model_name
        self.ip = ip
        self.port = port
        logger.info(f"**ModelRunner** New model runner created: {self.model_id}, {self.model_name}, {self.ip}:{self.port}, let's connect it")

        self.grpc_channel = None
        self.grpc_stub = None
        self.retry_attempts = 5  # args ?
        self.min_retry_interval = 2  # 2 seconds
        self.closed = False

    def __del__(self):
        logger.debug(f"**ModelRunner** Model runner {self.model_id} is destroyed")
        atexit.register(self.close_sync)

    async def init(self) -> bool:
        for attempt in range(1, self.retry_attempts + 1):
            if self.closed:
                logger.debug(f"**ModelRunner** Model runner {self.model_id} closed, aborting initialization")
                return False
            try:
                self.grpc_channel = grpc.aio.insecure_channel(f"{self.ip}:{self.port}")
                self.grpc_stub = ModelRunnerStub(self.grpc_channel)
                await self.grpc_stub.Setup(empty_pb2.Empty())  # maybe orchestrator has to do that ?
                logger.info(f"**ModelRunner** model runner: {self.model_id}, {self.model_name}, is connected and ready")
                return True
            except (AioRpcError, asyncio.TimeoutError) as e:
                logger.error(f"**ModelRunner** Model {self.model_id} initialization failed on attempt {attempt}/{self.retry_attempts}: {e}")
            except Exception as e:
                logger.error(f"**ModelRunner** Unexpected error during initialization of model {self.model_id}: {e}", exc_info=True)

            if attempt < self.retry_attempts:
                backoff_time = 2 ** attempt  # Backoff with exponential delay
                logger.warning(f"**ModelRunner** Retrying in {backoff_time} seconds...")
                await asyncio.sleep(backoff_time)
            else:
                logger.error(f"**ModelRunner** Model {self.model_id} failed to initialize after {self.retry_attempts} attempts.")
                # todo what is the behavior here ? remove it locally ?
                return False

    async def predict(self, argument_type: DataType, argument_value: bytes):
        logger.debug(f"**ModelRunner** Doing prediction of model_id:{self.model_id}, name:{self.model_name}, argument_type:{argument_type}")
        prediction_request = InferRequest(type=argument_type, argument=argument_value)

        response = await self.grpc_stub.Infer(prediction_request)

        return decode_data(response.prediction, response.type)

    def close_sync(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.close())

    async def close(self):
        self.closed = True
        if self.grpc_channel:
            await self.grpc_channel.close()
            logger.debug(f"**ModelRunner** Model runner {self.model_id} grpc connection closed")
