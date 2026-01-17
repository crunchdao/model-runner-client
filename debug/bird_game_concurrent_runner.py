import asyncio
import logging

from model_runner_client.model_concurrent_runners import DynamicSubclassModelConcurrentRunner
from model_runner_client.grpc.generated.commons_pb2 import VariantType, Argument, Variant
from model_runner_client.security.credentials import SecureCredentials


async def main():
    from model_runner_client.utils.datatype_transformer import encode_data

    logging.basicConfig(
        format="{asctime:^20} | {levelname:^8} | {message}",
        style="{",
        # level=logging.DEBUG
    )
    logger = logging.getLogger("model_runner_client")
    logger.setLevel(logging.DEBUG)
    host = "localhost"


    secure_credentials = SecureCredentials.from_directory(
        path="../../crunch-certificate/coordinator-3/issued-certificate"
    )

    concurrent_runner = DynamicSubclassModelConcurrentRunner(
        timeout=10,
        crunch_id="bird-game",
        host=host,
        port=9091,
        base_classname='birdgame.trackers.trackerbase.TrackerBase',
        secure_credentials=secure_credentials,
        report_failure=False
    )

    await concurrent_runner.init()

    async def prediction_call():
        while True:
            payload = {'falcon_location': 21.179864629354732, 'time': 230.96231205799998, 'dove_location': 19.164986723324326, 'falcon_id': 1}
            payload_encoded = encode_data(VariantType.JSON, payload)
            await concurrent_runner.call(method_name='tick',
                                         args=[
                                             Argument(position=1, data=Variant(type=VariantType.JSON, value=payload_encoded))
                                         ])

            result = await concurrent_runner.call(method_name='predict')

            for model_runner, model_predict_result in result.items():
                logger.debug(f"model_runner: {model_runner.model_id}, model_predict_result: {model_predict_result}")

            logger.debug("sleeping for 30 seconds")
            await asyncio.sleep(30)

    await asyncio.gather(asyncio.create_task(concurrent_runner.sync()), asyncio.create_task(prediction_call()))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nReceived exit signal, shutting down gracefully.")
