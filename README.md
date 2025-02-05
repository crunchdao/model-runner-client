# Model Runner Client

**Model Runner Client** is a Python library that allows you, as a Coordinator, to interact with models participating in your crunch. It tracks which models join or leave through a WebSocket connection to the model nodes.

- **Real-Time Model Sync**: Each model participating in your crunch is an instance of `ModelRunner`, maintained via WebSocket in the `ModelCluster`.
- **Concurrent Predictions (with Timeout Handling)**: Use the `ModelConcurrentRunner` to request predictions from all models simultaneously. Define a timeout to avoid blocking if a model takes too long to predict.

## Installation

```bash
pip install model-runner-client
```

> **Note**: Adjust this command (e.g., `pip3` or virtual environments) depending on your setup.

## Usage

Below is a quick example focusing on the ModelConcurrentRunner. It handles concurrent predictions for you and returns all results in one go.

```python
import asyncio
from model_runner_client.model_concurrent_runner import ModelConcurrentRunner
from model_runner_client.protos.model_runner_pb2 import DataType
from model_runner_client.utils.datatype_transformer import encode_data

async def main():
    # crunch_id, host, and port are values provided by crunchdao
    concurrent_runner = ModelConcurrentRunner(
        timeout=10,
        crunch_id="bird-game",
        host="localhost",
        port=8000
    )

    # Initialize communication with the model nodes to fetch 
    # models that want to predict and set up the model cluster
    await concurrent_runner.init()

    async def prediction_call():
        while True:
            # Your data to be predicted (X)
            value = {
                'falcon_location': 21.179864629354732,
                'time': 230.96231205799998,
                'dove_location': 19.164986723324326,
                'falcon_id': 1
            }

            # Encode data as binary and request a prediction
            result = await concurrent_runner.predict(
                DataType.JSON,
                encode_data(DataType.JSON, value)
            )

            # You receive a dictionary of predictions
            for model_runner, model_predict_result in result.items():
                print(f"{model_runner.model_id}: {model_predict_result}")

            # This pause (30s) simulates other work 
            # the Coordinator might perform between predictions
            await asyncio.sleep(30)

    # Keep the cluster updated with `concurrent_runner.sync()`, 
    # which maintains a permanent WebSocket connection.
    # Then run our prediction process.
    await asyncio.gather(
        asyncio.create_task(concurrent_runner.sync()),
        asyncio.create_task(prediction_call())
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nReceived exit signal, shutting down gracefully.")
```

### Important Notes

- **Prediction Failures & Timeouts**: A prediction may fail or exceed the defined timeout, so be sure to handle these cases appropriately. Refer to `ModelPredictResult.Status` for details.
- **Custom Implementations**: If you need more control over your workflow, you can manage each model individually. Instead of using `ModelConcurrentRunner`, you can directly leverage `ModelRunner` instances from the `ModelCluster`, customizing how you schedule predictions and handle results.

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests if you encounter any bugs or want to suggest improvements.

## License

This project is distributed under the [MIT License](https://choosealicense.com/licenses/mit/). See the LICENSE file for details.