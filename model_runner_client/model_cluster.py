import json
import logging

from .model_runners import ModelRunner
from .websocket_client import WebsocketClient

logger = logging.getLogger("model_runner_client.model_cluster")
import asyncio


class ModelCluster:
    def __init__(self, crunch_id: str, ws_host: str, ws_port: int, model_factory: callable, report_failure=True):
        """
        ModelCluster constructor.

        :param crunch_id: The Crunch ID that this cluster is responsible for.
        :param ws_host: The WebSocket server's host.
        :param ws_port: The WebSocket server's port.
        """
        self.crunch_id = crunch_id
        self.models_run: dict[str, ModelRunner] = {}
        self.pending_model_runs: dict[str, ModelRunner] = {}  # Track model runners being initialized
        logger.debug(f"Initializing ModelCluster with Crunch ID: {crunch_id}")
        self.ws_client = WebsocketClient(ws_host, ws_port, crunch_id, event_handler=self.handle_event)
        self.model_factory = model_factory
        self.report_failure = report_failure

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
        """
        Update cluster state based on model state changes.

        State handling (only for matching deployment_id):
          - STOPPED/RECOVERING: remove model (running or pending)
          - RUNNING + same IP/port: update infos (if running)
          - RUNNING + new IP/port or new model: (re)connect
        """
        tasks = []
        for model_update in data:
            deployment_id = model_update.get("deployment_id")
            model_id = model_update.get("model_id")
            infos = model_update.get("infos")
            model_name = infos.get("model_name") if infos else None
            state = model_update.get("state")
            ip = model_update.get("ip")
            port = model_update.get("port")
            logger.debug(f"Updating model with ID: {model_id}")

            # Find the model in the current state (running or pending)
            model_runner = self.models_run.get(model_id) or self.pending_model_runs.get(model_id)
            if model_runner and deployment_id != model_runner.deployment_id:
                logger.debug(f"Model with ID {model_id} exists but with different deployment ID {deployment_id}<>{model_runner.deployment_id}. Ignoring.")
                model_runner = None

            if state == "STOPPED":
                if model_runner:
                    tasks.append(self.remove_model_runner(model_runner))
                    logger.debug(f"Model with ID {model_id} removed due to 'stopped' state.")
                else:
                    logger.debug(f"Model with ID {model_id} and deployment ID {deployment_id} is not found. No action required for 'STOPPED'.")

            elif state == "RECOVERING":
                if model_runner:
                    tasks.append(self.remove_model_runner(model_runner))
                    logger.debug(f"Model with ID {model_id} removed due to 'recovering' state. It will be back if recovery succeeds.")
                else:
                    logger.debug(f"Model with ID {model_id} and deployment ID {deployment_id} is not found. No action required for 'RECOVERING'.")

            elif state == "RUNNING":
                if model_runner and model_runner.ip == ip and model_runner.port == port:
                    # Same IP/port, just update infos if it's a running model
                    if model_id in self.models_run:
                        logger.debug(f"Model with ID {model_id} is already running in the cluster. Updating infos")
                        model_runner.infos = infos
                        model_runner.model_name = model_name
                    else:
                        logger.debug(f"Model with ID {model_id} is pending with same IP/port. No action required.")
                else:
                    # New model or IP/port changed
                    if model_runner:
                        logger.debug(f"Model with ID {model_id} has new IP/port ({model_runner.ip}:{model_runner.port} -> {ip}:{port}). Reconnecting.")
                    else:
                        logger.debug(f"New model with ID {model_id} is running, we add it to the cluster state.")
                    new_model_runner = self.model_factory(
                        deployment_id=deployment_id,
                        model_id=model_id,
                        model_name=model_name,
                        ip=ip,
                        port=port,
                        infos=infos
                    )
                    # add_model_runner handles removal of existing model and aborting pending
                    tasks.append(self.add_model_runner(new_model_runner))

            else:
                logger.warning(f"Model updated: {model_id}, with state: {state} => This state is not handled...")

        await asyncio.gather(*tasks)

    async def add_model_runner(self, model_runner: ModelRunner):
        """
        Asynchronously initialize a model_runner and add it to the cluster state.
        """
        logger.debug(f"Adding model {model_runner.model_id} (deployment: {model_runner.deployment_id})")

        # Remove any existing model (running or pending) with the same model_id
        current_model = self.models_run.get(model_runner.model_id) or self.pending_model_runs.get(model_runner.model_id)
        if current_model:
            logger.info(f"Model {current_model.model_id}: replacing existing (deployment: {current_model.deployment_id})")
            await self.remove_model_runner(current_model)

        # Track this model runner as pending during initialization
        self.pending_model_runs[model_runner.model_id] = model_runner
        try:
            is_initialized, error = await model_runner.init()
        finally:
            # Remove from pending regardless of outcome
            if self.pending_model_runs.get(model_runner.model_id) is model_runner:
                del self.pending_model_runs[model_runner.model_id]

        if is_initialized:
            self.models_run[model_runner.model_id] = model_runner
        else:
            if error == ModelRunner.ErrorType.BAD_IMPLEMENTATION:
                await self.process_failure(model_runner, 'BAD_IMPLEMENTATION')
            elif error == ModelRunner.ErrorType.ABORTED:
                return
            elif error in [ModelRunner.ErrorType.GRPC_CONNECTION_FAILED, ModelRunner.ErrorType.AUTH_ERROR]:
                await self.process_failure(model_runner, 'CONNECTION_FAILED')
            else:
                await self.process_failure(model_runner, 'MULTIPLE_FAILED')

    async def process_failure(self, model_runner: ModelRunner, failure_code: str, failure_reason: str = None):
        if not self.report_failure:
            logger.warning(f"Process failure is disabled: model_id={model_runner.model_id}, failure_code={failure_code}, failure_reason={failure_reason}")
            return

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
        Asynchronously close a model_runner and remove it from the cluster state (running or pending).
        """
        logger.debug(f"Closing model {model_runner.model_id} (deployment: {model_runner.deployment_id})")
        await model_runner.close()
        if self.models_run.get(model_runner.model_id) is model_runner:
            del self.models_run[model_runner.model_id]
        if self.pending_model_runs.get(model_runner.model_id) is model_runner:
            del self.pending_model_runs[model_runner.model_id]
        logger.info(f"Model {model_runner.model_id} removed (deployment: {model_runner.deployment_id})")

    async def reconnect_model_runner(self, model_runner: ModelRunner):
        try:
            logger.info(f"Model {model_runner.model_id}: reconnecting")
            await self.remove_model_runner(model_runner)
            model_runner = self.model_factory(
                deployment_id=model_runner.deployment_id,
                model_id=model_runner.model_id,
                model_name=model_runner.model_name,
                ip=model_runner.ip,
                port=model_runner.port,
                infos=model_runner.infos
            )
            await self.add_model_runner(model_runner)
        except Exception as e:
            logger.error(f"Error reconnecting model with ID: {model_runner.model_id}: {e}", exc_info=True)


async def start(self):
    """
    Start the WebSocket client and handle events.
    """
    try:
        await self.ws_client.connect()
    except Exception as e:
        logger.error(f"Failed to start WebSocket client: {e}", exc_info=True)
