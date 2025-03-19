import json
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch, AsyncMock, MagicMock
import asyncio
import websockets
from grpc import Status

from model_runner_client.grpc.generated import commons_pb2
from model_runner_client.grpc.generated.commons_pb2 import Argument, Variant, VariantType
from model_runner_client.grpc.generated.dynamic_subclass_pb2 import SetupResponse, CallResponse
from model_runner_client.model_concurrent_runners.dynamic_subclass_model_concurrent_runner import DynamicSubclassModelConcurrentRunner
from model_runner_client.model_concurrent_runners.model_concurrent_runner import ModelConcurrentRunner, ModelPredictResult
from model_runner_client.model_runners.dynamic_subclass_model_runner import DynamicSubclassModelRunner


def create_model_runner(model_id, model_name, ip, port, infos):
    model_runner = DynamicSubclassModelRunner('birdgame.trackers.trackerbase.TrackerBase', model_id, model_name, ip, port, infos)
    return model_runner


class TestDynamicSubclassModelConcurrentRunner(IsolatedAsyncioTestCase):

    async def ws_handler(self, websocket):
        self.websocket_client = websocket
        self.client_messages = []
        msg = {
            "event": "init", "data":
                [
                    {
                        "model_id": "test_id_1",
                        "model_name": "test_name",
                        "state": "RUNNING",
                        "ip": "127.0.0.1",
                        "port": 5000,
                        "infos": {"model_name": "test1_model_name", "cruncher_id": "test1_cruncher_id", "cruncher_name": "test1_cruncher_name"}
                    }
                ]
        }
        await self.websocket_client.send(json.dumps(msg))
        async for message in self.websocket_client:
            self.client_messages.append(json.loads(message))

    async def _start_test_websocket_server(self):
        self.websocket_server = await websockets.serve(self.ws_handler, "localhost", 9091)

    async def asyncSetUp(self):
        DynamicSubclassModelConcurrentRunner.create_model_runner = MagicMock(side_effect=create_model_runner)
        self.instance = DynamicSubclassModelConcurrentRunner(1,
                                                             'bird-game',
                                                             'localhost',
                                                             9091,
                                                             base_classname='birdgame.trackers.trackerbase.TrackerBase')

    async def asyncTearDown(self):
        self.client_messages.clear()
        self.websocket_client = None

        print("Closing WebSocket server...")
        self.websocket_server.close()
        await self.websocket_server.wait_closed()
        print("WebSocket server closed.")

    @patch('model_runner_client.model_runners.model_runner.grpc.aio.insecure_channel')
    @patch('model_runner_client.model_runners.dynamic_subclass_model_runner.DynamicSubclassServiceStub', new_callable=MagicMock)
    async def test_call(self, mock_grpc_sub, mock_insecure_channel):
        mock_instance = MagicMock()
        mock_grpc_sub.return_value = mock_instance

        mock_instance.Setup = AsyncMock(return_value=SetupResponse(
            status=commons_pb2.Status(code='SUCCESS', message='OK')
        ))

        print("start websocket")
        task = asyncio.create_task(self._start_test_websocket_server())
        print("websocket started")
        await asyncio.sleep(1)  # give time to server starting
        await self.instance.init()

        # after init
        self.assertEqual(1, len(self.instance.model_cluster.models_run))

        # here we test a new model joining in the middle time
        msg_up = {
            "event": "update", "data":
                [
                    {
                        "model_id": "test_id_2",
                        "model_name": "test_name",
                        "state": "RUNNING",
                        "ip": "127.0.0.1",
                        "port": 5001,
                        "infos": {"model_name": "test2_model_name", "cruncher_id": "test2_cruncher_id", "cruncher_name": "test2_cruncher_name"}
                    }
                ]
        }

        await self.websocket_client.send(json.dumps(msg_up))
        try:
            await asyncio.wait_for(self.instance.sync(), timeout=1)
        except asyncio.TimeoutError:
            pass
        self.assertEqual(2, len(self.instance.model_cluster.models_run))

        # here try call to the model
        mock_instance.Call = AsyncMock(return_value=CallResponse(
            status=commons_pb2.Status(code='SUCCESS', message='OK'),
            methodResponse=Variant(type=VariantType.STRING, value=b"PREDICTION")
        ))

        result = await self.instance.call(method_name='tick',
                                          args=[Argument(position=1, data=Variant(type=VariantType.STRING, value=b"PAYLOAD_TEST"))]
                                          )

        self.assertEqual(2, len(result))
        model_ids_result = {model.model_id: result for model, result in result.items()}
        self.assertIn("test_id_1", model_ids_result.keys())
        self.assertIn("test_id_2", model_ids_result.keys())
        self.assertEqual(ModelPredictResult.Status.SUCCESS, model_ids_result["test_id_1"].status)
        self.assertEqual("PREDICTION", model_ids_result["test_id_1"].result)
        self.assertEqual(ModelPredictResult.Status.SUCCESS, model_ids_result["test_id_2"].status)

    @patch('model_runner_client.model_runners.model_runner.grpc.aio.insecure_channel')
    @patch('model_runner_client.model_runners.dynamic_subclass_model_runner.DynamicSubclassServiceStub', new_callable=MagicMock)
    async def test_call_with_error(self, mock_grpc_sub, mock_insecure_channel):
        mock_instance = MagicMock()
        mock_grpc_sub.return_value = mock_instance

        mock_instance.Setup = AsyncMock(return_value=SetupResponse(
            status=commons_pb2.Status(code='SUCCESS', message='OK')
        ))

        task = asyncio.create_task(self._start_test_websocket_server())
        await asyncio.sleep(1)  # give time to server starting
        await self.instance.init()

        try:
            await asyncio.wait_for(self.instance.sync(), timeout=1)
        except asyncio.TimeoutError:
            pass

        # error call
        mock_instance.Call = AsyncMock(return_value=CallResponse(
            status=commons_pb2.Status(code='BAD_IMPLEMENTATION', message='bad implementation'),
            methodResponse=None
        ))

        result = await self.instance.call(method_name='tick',
                                          args=[Argument(position=1, data=Variant(type=VariantType.STRING, value=b"PAYLOAD_TEST"))]
                                          )

        self.assertEqual(1, len(result))
        model_ids_result = {model.model_id: result for model, result in result.items()}
        self.assertIn("test_id_1", model_ids_result.keys())
        self.assertEqual(ModelPredictResult.Status.FAILED, model_ids_result["test_id_1"].status)

        await asyncio.sleep(1)  # wait report of failure over websocket
        self.assertEqual(1, len(self.client_messages))
        self.assertEqual(self.client_messages[0]["event"], "report_failure")

        data = self.client_messages[0]["data"]
        self.assertEqual(1, len(data))
        fist_data = self.client_messages[0]["data"][0]
        self.assertEqual(fist_data["failure_code"], "BAD_IMPLEMENTATION")
        self.assertEqual(fist_data["model_id"], "test_id_1")
        self.assertEqual(fist_data["ip"], "127.0.0.1")

    @patch('model_runner_client.model_runners.model_runner.grpc.aio.insecure_channel')
    @patch('model_runner_client.model_runners.dynamic_subclass_model_runner.DynamicSubclassServiceStub', new_callable=MagicMock)
    async def test_update_infos(self, mock_grpc_sub, mock_insecure_channel):
        mock_instance = MagicMock()
        mock_grpc_sub.return_value = mock_instance

        mock_instance.Setup = AsyncMock(return_value=SetupResponse(
            status=commons_pb2.Status(code='SUCCESS', message='OK')
        ))

        print("start websocket")
        task = asyncio.create_task(self._start_test_websocket_server())
        print("websocket started")
        await asyncio.sleep(1)  # give time to server starting
        await self.instance.init()

        # after init
        self.assertEqual(1, len(self.instance.model_cluster.models_run))
        self.assertEqual(self.instance.model_cluster.models_run["test_id_1"].infos, {"model_name": "test1_model_name", "cruncher_id": "test1_cruncher_id", "cruncher_name": "test1_cruncher_name"})

        # here we test an update of model infos
        msg_up = {
            "event": "update", "data":
                [
                    {
                        "model_id": "test_id_1",
                        "model_name": "test_name",
                        "state": "RUNNING",
                        "ip": "127.0.0.1",
                        "port": 5001,
                        "infos": {"model_name": "test1b_model_name", "cruncher_id": "test1b_cruncher_id", "cruncher_name": "test1b_cruncher_name"}
                    }
                ]
        }

        await self.websocket_client.send(json.dumps(msg_up))
        try:
            await asyncio.wait_for(self.instance.sync(), timeout=1)
        except asyncio.TimeoutError:
            pass
        self.assertEqual(1, len(self.instance.model_cluster.models_run))
        self.assertEqual(self.instance.model_cluster.models_run["test_id_1"].infos, {"model_name": "test1b_model_name", "cruncher_id": "test1b_cruncher_id", "cruncher_name": "test1b_cruncher_name"})