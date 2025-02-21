import abc
import asyncio
import atexit
import logging

import grpc
from grpc.aio import AioRpcError

logger = logging.getLogger("model_runner_client")


class ModelRunner:
    def __init__(self, model_id: str, model_name: str, ip: str, port: int):

        self.model_id = model_id
        self.model_name = model_name
        self.ip = ip
        self.port = port
        logger.info(f"**ModelRunner** New model runner created: {self.model_id}, {self.model_name}, {self.ip}:{self.port}, let's connect it")

        self.grpc_channel = None
        self.retry_attempts = 5  # args ?
        self.min_retry_interval = 2  # 2 seconds
        self.closed = False

    def __del__(self):
        logger.debug(f"**ModelRunner** Model runner {self.model_id} is destroyed")
        atexit.register(self.close_sync)

    @abc.abstractmethod
    async def setup(self, grpc_channel):
        pass

    async def init(self) -> bool:
        for attempt in range(1, self.retry_attempts + 1):
            if self.closed:
                logger.debug(f"**ModelRunner** Model runner {self.model_id} closed, aborting initialization")
                return False
            try:
                self.grpc_channel = grpc.aio.insecure_channel(f"{self.ip}:{self.port}")
                await self.setup(self.grpc_channel)
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



    def close_sync(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.close())

    async def close(self):
        self.closed = True
        if self.grpc_channel:
            await self.grpc_channel.close()
            logger.debug(f"**ModelRunner** Model runner {self.model_id} grpc connection closed")


