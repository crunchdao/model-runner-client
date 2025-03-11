import asyncio
import atexit
import json
import logging

import websockets
from websockets import State

logger = logging.getLogger("model_runner_client")


class WebsocketClient:
    def __init__(self, host, port, crunch_id, event_handler=None):
        """
        WebsocketClient constructor.

        :param host: WebSocket server host.
        :param port: WebSocket server port.
        :param crunch_id: Crunch ID used to connect to the server.
        :param event_handler: Optional handler for WebSocket events (delegated to ModelCluster).
        """
        self.retry_interval = 10
        self.max_retries = 5
        self.listening = None
        self.host = host
        self.port = port
        self.crunch_id = crunch_id
        self.websocket = None
        self.event_handler = event_handler  # Delegate to ModelCluster
        self.message_queue = asyncio.Queue()

    def __del__(self):
        atexit.register(self.disconnect_sync)

    async def connect(self):
        """
        Establish a WebSocket connection.
        """
        retry_count = 0
        uri = f"ws://{self.host}:{self.port}/{self.crunch_id}"

        while self.max_retries > retry_count:
            try:
                logger.info(f"Connecting to WebSocket server at {uri}")
                self.websocket = await websockets.connect(uri)
                logger.info(f"Connected to WebSocket server at {uri}")
                break
            except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError, OSError, asyncio.TimeoutError) as e:
                logger.warning(f"Connection error ({e.__class__.__name__}): Retrying in {self.retry_interval} seconds...")
            except Exception as e:
                logger.error(f"Unexpected error ({e.__class__.__name__}): {e}", exc_info=True)
                logger.warning(f"Retrying in {self.retry_interval} seconds...")

            await asyncio.sleep(self.retry_interval)
            retry_count += 1

        if retry_count == self.max_retries and not self.websocket:
            raise ConnectionError(f"Failed to connect to WebSocket server at {uri}")

    async def init(self):
        """
        Listen first message who is init from the WebSocket server.
        """
        # retry here doesn't make sens, it comme after connection and connection handle retries
        try:
            message = await self.websocket.recv()
            await self.handle_event(message)
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed by the server.")
        except Exception as e:
            logger.error(f"Error while listening to WebSocket messages: {e}", exc_info=True)

    async def listen(self):
        """
        Listen for messages from the WebSocket server.
        """
        self.listening = True
        while self.listening:
            try:
                if not await self.is_connected():
                    await self.connect()
                    await self._send_pending_messages()

                logger.info("Listening for messages...")
                async for message in self.websocket:
                    await self.handle_event(message)
            except (websockets.exceptions.ConnectionClosed, asyncio.TimeoutError):
                logger.warning(f"Connection lost. Retrying in {self.retry_interval} seconds...")
                await asyncio.sleep(self.retry_interval)
            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}", exc_info=True)
                logger.warning(f"Retrying in {self.retry_interval} seconds...")
                await asyncio.sleep(self.retry_interval)

            finally:
                # Cleanup or reset if needed after the loop iteration
                # For example, clear websocket references if disconnected
                if self.websocket and not self.websocket.state:
                    self.websocket = None

    async def is_connected(self):
        """
        Check if the WebSocket connection is open.
        :return: True if the client is connected, False otherwise.
        """
        return self.websocket is not None and self.websocket.state == State.OPEN

    async def handle_event(self, message):
        """
        Handle incoming WebSocket messages and forward to the event handler.

        :param message: Message received from the server.
        """
        try:
            event = json.loads(message)
            event_type = event.get("event")
            data = event.get("data")

            logger.debug(f"Received event: {event_type}, data: {data}")

            # Delegate to the event handler, if available
            if self.event_handler:
                await self.event_handler(event_type, data)
            else:
                logger.warning("No event handler defined. Event will be ignored.")
        except json.JSONDecodeError:
            logger.error(f"Failed to decode WebSocket message: {message}")

    async def send_message(self, message: str):
        """
        Send a message to the WebSocket server.
        If the connection is not available, store the message in the queue.
        """
        if await self.is_connected():
            try:
                await self.websocket.send(message)
                logger.info(f"Message sent: {message}")
            except (websockets.ConnectionClosed, websockets.InvalidState, asyncio.TimeoutError) as e:
                logger.warning(f"Failed to send message, queuing it: {message}. Error: {e}")
                await self.message_queue.put(message)
        else:
            logger.info(f"Connection unavailable, queuing message: {message}")
            await self.message_queue.put(message)

    async def _send_pending_messages(self):
        """
        Process the queue and send pending messages
        """
        while not self.message_queue.empty():
            message = await self.message_queue.get()
            try:
                await self.websocket.send(message)
                logger.info(f"Message sent from queue: {message}")
            except Exception as e:
                await self.message_queue.put(message)
                raise e

    def disconnect_sync(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.disconnect())

    async def disconnect(self):
        """
        Close the WebSocket connection.
        """
        self.listening = False
        if self.websocket:
            await self.websocket.close()
            logger.info("WebSocket connection closed.")
