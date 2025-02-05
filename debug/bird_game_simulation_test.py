import asyncio
import json

import pytest
from websockets import serve

from model_runner_client.model_concurrent_runner import ModelConcurrentRunner
from model_runner_client.utils.datatype_transformer import DataType, encode_data
import logging

# Simulated WebSocket Server
async def websocket_handler(websocket):
    # Parse crunch_id from the path
    path = websocket.request.path
    crunch_id = path.strip("/")

    # Send an "init" event with mocked model states
    init_message = {
        "event": "init",
        "data": [
            {"model_id": "model_1", "model_name": "FalconModel", "state": "RUNNING", "ip": "10.0.2.166", "port": 50051},
            #{"model_id": "model_2", "model_name": "DoveModel", "state": "RUNNING", "ip": "10.0.2.108", "port": 50051},
        ],
    }
    await websocket.send(json.dumps(init_message))

    try:
        await asyncio.sleep(5)
        await websocket.send(
            json.dumps({"event": "update", "data": [{"model_id": "model_1", "state": "STOPPED", "ip": "10.0.2.166", "port": 50051}]})
        )
        async for message in websocket:
            received_message = json.loads(message)
            # Process received messages here if needed
    except:
        pass


# Run WebSocket Server
@pytest.fixture
async def websocket_server():
    server = await serve(websocket_handler, "localhost", 8765)
    yield server
    server.close()
    await server.wait_closed()


# Test the ModelConcurrentRunner with the simulated WebSocket server
@pytest.mark.asyncio
async def test_model_concurrent_runner(websocket_server):
    # Configure the ModelConcurrentRunner
    concurrent_runner = ModelConcurrentRunner(timeout=10, crunch_id="bird-game", host="localhost", port=8765)

    # Initialize the runner
    await concurrent_runner.init()
    sync_task = asyncio.create_task(concurrent_runner.sync())

    # Mocked data for prediction
    value = {
        "falcon_location": 21.179864629354732,
        "time": 230.96231205799998,
        "dove_location": 19.164986723324326,
        "falcon_id": 1,
    }

    # Perform prediction
    result = await concurrent_runner.predict(DataType.JSON, encode_data(DataType.JSON, value))
    for model_runner, model_predict_result in result.items():
        logging.getLogger("model_runner_client").debug(f"model_runner: {model_runner.model_id}, model_predict_result: {model_predict_result}")

    # Verify the result
    assert result is not None
    assert isinstance(result, dict)


    await asyncio.sleep(10)#

    result = await concurrent_runner.predict(DataType.JSON, encode_data(DataType.JSON, value))
    for model_runner, model_predict_result in result.items():
        logging.getLogger("model_runner_client").debug(f"model_runner: {model_runner.model_id}, model_predict_result: {model_predict_result}")

    # Verify the result
    assert result is not None
    assert isinstance(result, dict)

    sync_task.cancel()  # Cancel the sync loop after testing


def main():
    import pytest

    # Configure logging
    logging.basicConfig()
    logger = logging.getLogger("model_runner_client")
    logger.setLevel(logging.DEBUG)


    pytest.main(["--capture=no", "-v", "--asyncio-mode=auto"])

if __name__ == '__main__':
    main()





