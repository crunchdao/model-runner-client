import asyncio
import logging

from model_runner_client.model_concurrent_runner import ModelConcurrentRunner
from model_runner_client.protos.model_runner_pb2 import DataType


async def main():
    from model_runner_client.utils.datatype_transformer import encode_data

    logging.basicConfig(
        format="{asctime:^20} | {levelname:^8} | {message}",
        style="{",
        # level=logging.DEBUG
    )
    logger = logging.getLogger("model_runner_client")
    logger.setLevel(logging.DEBUG)

    concurrent_runner = ModelConcurrentRunner(timeout=10, crunch_id="bird-game", host="localhost", port=8000)
    await concurrent_runner.init()

    async def prediction_call():
        while True:
            value = {'falcon_location': 21.179864629354732, 'time': 230.96231205799998, 'dove_location': 19.164986723324326, 'falcon_id': 1}
            result = await concurrent_runner.predict(DataType.JSON, encode_data(DataType.JSON, value))
            for model_runner, model_predict_result in result.items():
                logger.debug(f"**ModelConcurrentRunner** model_runner: {model_runner.model_id}, model_predict_result: {model_predict_result}")

            logger.debug("**ModelConcurrentRunner** sleeping for 30 seconds")
            await asyncio.sleep(30)

    await asyncio.gather(asyncio.create_task(concurrent_runner.sync()), asyncio.create_task(prediction_call()))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nReceived exit signal, shutting down gracefully.")
