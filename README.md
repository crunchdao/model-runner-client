# Model Runner Client

**Model Runner Client** is a Python library that allows you, as a Coordinator, to interact with models participating in your crunch. It tracks which models join or leave through a WebSocket connection to the model nodes.

## Features

- **Real-Time Model Sync**: Each model participating in your crunch is an instance of `ModelRunner`, maintained via WebSocket in the `ModelCluster`.
- **Concurrent Predictions (with Timeout Handling)**: Use the derived class of `ModelConcurrentRunner` (an abstract class) to request predictions from all models simultaneously. Define a timeout to avoid blocking if a model takes too long
  to predict. Make sure to select the proper instance based on the requirements of your crunch.
    - `DynamicSubclassModelConcurrentRunner`: Allows you to find a subclass on the remote model, instantiate it, and access all its methods.
    - `TrainInferModelConcurrentRunner`: Enables communication with a model that has declared the `infer` and `train` methods.

# Installation

The package is [available on PyPI](https://pypi.org/project/model-runner-client).

```bash
pip install model-runner-client
```

> [!NOTE]
> Adjust this command (e.g., `pip3` or virtual environments) depending on your setup.

# Usage

Below are two examples using `DynamicSubclassModelConcurrentRunner`, which handles concurrent predictions for you and returns all results in one go.  
The first shows how to send the same input to all models, while the second demonstrates how to customize arguments for each model individually.

### Shared Arguments for All Models

In the simplest case, the same input is passed to all models. Here's how to structure such a call:

```python
import asyncio
from model_runner_client.model_concurrent_runners.dynamic_subclass_model_concurrent_runner import DynamicSubclassModelConcurrentRunner
from model_runner_client.grpc.generated.commons_pb2 import VariantType, Argument, Variant
from model_runner_client.utils.datatype_transformer import encode_data


async def main():
    # crunch_id, host, and port are values provided by crunchdao
    concurrent_runner = DynamicSubclassModelConcurrentRunner(
        timeout=10,
        crunch_id="bird-game",
        host="localhost",
        port=8000,
        base_classname='birdgame.trackers.trackerbase.TrackerBase'
    )

    # Initialize communication with the model nodes to fetch 
    # models that want to predict and set up the model cluster
    await concurrent_runner.init()

    async def prediction_call():
        while True:
            # Your data to be predicted (X)
            payload = {
                'falcon_location': 21.179864629354732,
                'time': 230.96231205799998,
                'dove_location': 19.164986723324326,
                'falcon_id': 1
            }

            # Encode data as binary and tick
            await concurrent_runner.call(
                method_name='tick',
                arguments=(
                    # args
                    # The order of positional arguments is strictly enforced and must match the model's method signature.
                    # Adding a new positional argument during a crunch would break existing model implementations.
                    [
                        Argument(position=1, data=Variant(type=VariantType.JSON, value=encode_data(VariantType.JSON, payload)))
                    ],

                    # kwargs
                    # These keyword arguments are passed only if the model's method explicitly expects them.
                    # It is recommended to use kwargs for optional parameters, as they can be introduced without breaking compatibility.
                    [],
                )
            )

            # predict now
            result = await concurrent_runner.call(method_name='predict')

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

### Per-Model Arguments (Advanced Usage)

In some situations, you may want to send different arguments to each model.  
You can do this by passing a function to the `arguments` parameter:

```python
# ... (same setup as the first example)

  # Common argument encoded once
  payload_arg = Argument(
    position=1,
    data=Variant(
      type=VariantType.JSON,
      value=encode_data(
        VariantType.JSON,
        {
          'falcon_location': 21.179864629354732,
          'time': 230.96231205799998,
          'dove_location': 19.164986723324326,
          'falcon_id': 1,
        })
    )
  )
  
  
  def prepare_arguments(model_runner: DynamicSubclassModelRunner):
    # Use model_runner.model_id to keep track of model-specific information
    player_uid = model_runner.model_id
  
    performance_metrics_kwarg = KwArgument(
      keyword="performance_metrics",
      data=Variant(
        type=VariantType.JSON,
        value=encode_data(
          VariantType.JSON,
          {
            "wealth": self.players[player_uid]["wealth"],  # load model-specific information
            "likelihood_ewa": self.players[player_uid]["wealth"]
          })
      )
    )
  
    return (
      # args
      # The order of positional arguments is strictly enforced and must match the model's method signature.
      # Adding a new positional argument during a crunch would break existing model implementations.
  
      [payload_arg],
  
      # kwargs
      # These keyword arguments are passed only if the model's method explicitly expects them.
      # It is recommended to use kwargs for optional parameters, as they can be introduced without breaking compatibility.
  
      [performance_metrics_kwarg]
    )
  
  
  result = await concurrent_runner.call(
    method_name='tick',
    arguments=prepare_arguments,
  )

# ... (same post-processing as in the first example)
```

## Important Notes

- **Prediction Failures & Timeouts**: A prediction may fail or exceed the defined timeout, so be sure to handle these cases appropriately. Refer to `ModelPredictResult.Status` for details.
- **Custom Implementations**: If you need more control over your workflow, you can manage each model individually. Instead of using implementations of `ModelConcurrentRunner`, you can directly leverage `ModelRunner` instances from the
  `ModelCluster`, customizing how you schedule predictions and handle results.

# Contributing

Contributions are welcome! Feel free to open issues or submit pull requests if you encounter any bugs or want to suggest improvements.

# License

This project is distributed under the [MIT License](https://choosealicense.com/licenses/mit/).
