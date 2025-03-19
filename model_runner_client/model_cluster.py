import json
import logging

from model_runner_client.model_runners.model_runner import ModelRunner
from model_runner_client.websocket_client import WebsocketClient

logger = logging.getLogger("model_runner_client.model_cluster")
import asyncio


class ModelCluster:
    def __init__(self, crunch_id: str, ws_host: str, ws_port: int, model_factory: callable):
        """
        ModelCluster constructor.

        :param crunch_id: The Crunch ID that this cluster is responsible for.
        :param ws_host: The WebSocket server's host.
        :param ws_port: The WebSocket server's port.
        """
        self.crunch_id = crunch_id
        self.models_run = {}
        logger.debug(f"Initializing ModelCluster with Crunch ID: {crunch_id}")
        self.ws_client = WebsocketClient(ws_host, ws_port, crunch_id, event_handler=self.handle_event)
        self.model_factory = model_factory

    async def init(self):
        await self.ws_client.connect()
        await self.ws_client.init()

        logger.debug("WebSocket client initialized.")

    async def sync(self):
        await self.ws_client.listen()

    async def handle_event(self, event_type: str, data: list[dict]):
        """
        Handle WebSocket events (`init` and `update`) and update the cluster's state.

        :param event_type: The type of the event (`init` or `update`).
        :param data: The event data.
        """
        try:
            if event_type == "init":
                logger.debug(f"Processing event type: {event_type}")
                await self.handle_init_event(data)
            elif event_type == "update":
                logger.debug(f"Processing event type: {event_type}")
                await self.handle_update_event(data)
            else:
                logger.warning(f"Unknown event type received: {event_type}")
        except Exception as e:
            logger.error(f"Error processing event {event_type}: {e}", exc_info=True)
            raise e

    async def handle_init_event(self, data: list[dict]):
        """
        Process the `init` event to initialize models run.
        
        :param data: List of models with their initial states.
        """
        logger.debug("Handling 'init' event.")
        await self.update_model_runs(data)

        # Remove models in `self.models_run` that are not present in `data`
        data_model_ids = {model['model_id'] for model in data}
        models_to_remove = self.models_run.keys() - data_model_ids
        tasks = [self.remove_model_runner(self.models_run[model_id]) for model_id in models_to_remove]
        await asyncio.gather(*tasks)
        logger.debug(f"Models with IDs {models_to_remove} removed as they are not in the 'init' event data.")

    async def handle_update_event(self, data: list[dict]):
        """
        Process the `update` event to update model states.
        
        :param data: List of models with their updated states.
        """
        logger.debug("Handling 'update' event.")
        await self.update_model_runs(data)

    async def update_model_runs(self, data):
        tasks = []
        for model_update in data:
            model_id = model_update.get("model_id")
            infos = model_update.get("infos")
            model_name = infos.get("model_name") if infos else None
            state = model_update.get("state")
            ip = model_update.get("ip")
            port = model_update.get("port")
            logger.debug(f"Updating model with ID: {model_id}")

            # Find the model in the current state
            model_runner = self.models_run.get(model_id)

            if model_runner:
                if state == "STOPPED":
                    # Remove model if state is "stopped"
                    tasks.append(self.remove_model_runner(model_runner))
                    logger.debug(f"Model with ID {model_id} removed due to 'stopped' state.")
                elif state == "RUNNING":
                    logger.debug(f"Model with ID {model_id} is already running in the cluster. Updating infos")
                    model_runner.infos = infos
                else:
                    logger.warning(f"Model updated: {model_id}, with state: {state} => This state is not handled...")
            else:
                if state == "STOPPED":
                    logger.debug(f"Model with ID {model_id} is not found in the cluster state, and its state is 'STOPPED'. No action is required.")
                elif state == "RUNNING":
                    logger.debug(f"New model with ID {model_id} is running, we add it to the cluster state.")
                    model_runner = self.model_factory(model_id, model_name, ip, port, infos)
                    tasks.append(self.add_model_runner(model_runner))
                else:
                    logger.warning(f"Model updated: {model_id}, with state: {state} => This state is not handled...")

        await asyncio.gather(*tasks)

    async def add_model_runner(self, model_runner: ModelRunner):
        """
        Asynchronously initialize a model_runner and add it to the cluster state.
        """
        is_initialized, error = await model_runner.init()
        if is_initialized:
            self.models_run[model_runner.model_id] = model_runner
        else:
            if error == ModelRunner.ErrorType.BAD_IMPLEMENTATION:
                await self.process_failure(model_runner, 'BAD_IMPLEMENTATION')
            elif error == ModelRunner.ErrorType.ABORTED:
                return
            elif error == ModelRunner.ErrorType.GRPC_CONNECTION_FAILED:
                await self.process_failure(model_runner, 'CONNECTION_FAILED')
            else:
                await self.process_failure(model_runner, 'MULTIPLE_FAILED')

    async def process_failure(self, model_runner: ModelRunner, failure_code: str, failure_reason: str = None):
        error_msg = {
            "event": "report_failure",
            "data": [
                {
                    "model_id": model_runner.model_id,
                    "failure_code": failure_code,
                    "failure_reason": failure_reason,
                    "ip": model_runner.ip
                }
            ]
        }
        await self.ws_client.send_message(json.dumps(error_msg))
        await self.remove_model_runner(model_runner)

    async def remove_model_runner(self, model_runner: ModelRunner):
        """
        Asynchronously initialize a model_runner and add it to the cluster state.
        """
        await model_runner.close()
        if model_runner.model_id in self.models_run:
            del self.models_run[model_runner.model_id]

    async def start(self):
        """
        Start the WebSocket client and handle events.
        """
        try:
            await self.ws_client.connect()
        except Exception as e:
            logger.error(f"Failed to start WebSocket client: {e}", exc_info=True)
