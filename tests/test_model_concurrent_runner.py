from typing import Any
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch, MagicMock

import grpc
from grpc_health.v1 import health_pb2

from model_runner_client.model_concurrent_runners import ModelConcurrentRunner, ModelPredictResult
from model_runner_client.model_runners import ModelRunner


class TestModelConcurrentRunner(IsolatedAsyncioTestCase):
    def setUp(self):
        self.model_runner_1 = ModelRunner("deployment_id_1", "mock_model_1", "MockModel", "127.0.0.1", 1234, {})
        self.model_runner_1.test_method = AsyncMock(return_value=("mock_result_1", None))
        self.model_runner_1.init = AsyncMock()

        self.model_runner_2 = ModelRunner("deployment_id_2", "mock_model_2", "MockModel", "127.0.0.1", 1234, {})
        self.model_runner_2.test_method = AsyncMock(return_value=("mock_result_2", None))
        self.model_runner_2.init = AsyncMock()

        self.patcher = patch("model_runner_client.model_concurrent_runners.model_concurrent_runner.ModelCluster")
        self.addCleanup(self.patcher.stop)
        self.mock_model_cluster_class = self.patcher.start()

        self.mock_model_cluster = self.mock_model_cluster_class.return_value
        self.mock_model_cluster.models_run = {
            "mock_model_1": self.model_runner_1,
            "mock_model_2": self.model_runner_2,
        }
        self.mock_model_cluster.process_failure = AsyncMock()
        self.mock_model_cluster.reconnect_model_runner = AsyncMock()

        class MockModelConcurrentRunner(ModelConcurrentRunner):
            def create_model_runner(self, model_id: str, model_name: str, ip: str, port: int, infos: dict[str, Any]) -> ModelRunner:
                raise NotImplementedError()

        self.concurrent_runner = MockModelConcurrentRunner(
            timeout=10, crunch_id="test-id", host="localhost", port=1234
        )

    async def test_execute_concurrent_method_success(self):
        self.assertIn("mock_model_1", self.concurrent_runner.model_cluster.models_run)
        self.assertEqual(self.model_runner_1, self.mock_model_cluster.models_run["mock_model_1"])

        results = await self.concurrent_runner._execute_concurrent_method("test_method")

        self.assertEqual(results[self.model_runner_1].result, "mock_result_1")
        self.assertEqual(results[self.model_runner_2].result, "mock_result_2")
        self.assertEqual(results[self.model_runner_1].status, ModelPredictResult.Status.SUCCESS)
        self.assertEqual(results[self.model_runner_2].status, ModelPredictResult.Status.SUCCESS)

    
    async def test_execute_concurrent_method_partial_failure(self):
        self.model_runner_2.test_method = AsyncMock(return_value=(None, ModelRunner.ErrorType.FAILED))

        results = await self.concurrent_runner._execute_concurrent_method("test_method")

        self.assertEqual(results[self.model_runner_1].result, "mock_result_1")
        self.assertIsNone(results[self.model_runner_2].result)
        self.assertEqual(results[self.model_runner_1].status, ModelPredictResult.Status.SUCCESS)
        self.assertEqual(results[self.model_runner_2].status, ModelPredictResult.Status.FAILED)

    @patch('grpc_health.v1.health_pb2_grpc.HealthStub', new_callable=MagicMock)
    async def test_execute_concurrent_method_timeout(self, mock_grpc_health: MagicMock):
        mock_grpc_health.return_value.Check = AsyncMock(return_value=health_pb2.HealthCheckResponse(status=health_pb2.HealthCheckResponse.SERVING))
        self.model_runner_2.test_method = AsyncMock(side_effect=TimeoutError)

        results = await self.concurrent_runner._execute_concurrent_method("test_method")

        self.assertEqual(results[self.model_runner_1].result, "mock_result_1")
        self.assertIsNone(results[self.model_runner_2].result)
        self.assertEqual(results[self.model_runner_1].status, ModelPredictResult.Status.SUCCESS)
        self.assertEqual(results[self.model_runner_2].status, ModelPredictResult.Status.TIMEOUT)
        self.assertGreater(results[self.model_runner_2].exec_time_us, 0)
        self.assertEqual(self.model_runner_2.consecutive_timeouts, 1)

    @patch('grpc_health.v1.health_pb2_grpc.HealthStub', new_callable=MagicMock)
    async def test_execute_concurrent_method_timeout_reconnect(self, mock_grpc_health: MagicMock):
        self.concurrent_runner.max_consecutive_timeouts = 1
        mock_grpc_health.return_value.Check = AsyncMock(side_effect=grpc.aio.AioRpcError(grpc.StatusCode.UNAVAILABLE, None, "Service Unavailable"))
        self.model_runner_2.test_method = AsyncMock(side_effect=TimeoutError)
        self.model_runner_2.consecutive_timeouts = 1

        results = await self.concurrent_runner._execute_concurrent_method("test_method")

        self.assertEqual(results[self.model_runner_1].result, "mock_result_1")
        self.assertIsNone(results[self.model_runner_2].result)
        self.assertEqual(results[self.model_runner_1].status, ModelPredictResult.Status.SUCCESS)
        self.assertEqual(results[self.model_runner_2].status, ModelPredictResult.Status.TIMEOUT)
        self.mock_model_cluster.reconnect_model_runner.assert_called_once()
        self.assertEqual(self.model_runner_2.consecutive_timeouts, 1)


    @patch('grpc_health.v1.health_pb2_grpc.HealthStub', new_callable=MagicMock)
    async def test_execute_concurrent_method_timeout_skip(self, mock_grpc_health: MagicMock):
        self.concurrent_runner.max_consecutive_timeouts = 4
        mock_grpc_health.return_value.Check = AsyncMock(return_value=health_pb2.HealthCheckResponse(status=health_pb2.HealthCheckResponse.SERVING))

        del self.mock_model_cluster.models_run["mock_model_1"]
        self.model_runner_2.test_method = AsyncMock(side_effect=TimeoutError)
        self.model_runner_2.consecutive_timeouts = 0

        results = await self.concurrent_runner._execute_concurrent_method("test_method")
        results = await self.concurrent_runner._execute_concurrent_method("test_method")
        results = await self.concurrent_runner._execute_concurrent_method("test_method")
        results = await self.concurrent_runner._execute_concurrent_method("test_method")
        results = await self.concurrent_runner._execute_concurrent_method("test_method")

        self.assertEqual(2, self.model_runner_2.test_method.call_count)
        self.assertEqual(5, self.model_runner_2.consecutive_timeouts)


    async def test_execute_concurrent_method_timeout_busy(self):
        self.model_runner_2.test_method = AsyncMock(side_effect=grpc.aio.AioRpcError(grpc.StatusCode.RESOURCE_EXHAUSTED, None, "Resource Exhausted"))

        results = await self.concurrent_runner._execute_concurrent_method("test_method")

        self.assertEqual(results[self.model_runner_1].result, "mock_result_1")
        self.assertIsNone(results[self.model_runner_2].result)
        self.assertEqual(results[self.model_runner_1].status, ModelPredictResult.Status.SUCCESS)
        self.assertEqual(results[self.model_runner_2].status, ModelPredictResult.Status.TIMEOUT)
        self.assertEqual(self.model_runner_2.consecutive_timeouts, 1)

    async def test_execute_concurrent_method_multiple_failure(self):
        self.model_runner_2.test_method = AsyncMock(return_value=(None, ModelRunner.ErrorType.FAILED))

        for i in range(ModelConcurrentRunner.MAX_CONSECUTIVE_FAILURES + 1):
            results = await self.concurrent_runner._execute_concurrent_method("test_method")

        self.mock_model_cluster.process_failure.assert_called_with(self.model_runner_2, 'MULTIPLE_FAILED')
        self.assertEqual(results[self.model_runner_1].result, "mock_result_1")
        self.assertIsNone(results[self.model_runner_2].result)
        self.assertEqual(results[self.model_runner_1].status, ModelPredictResult.Status.SUCCESS)
        self.assertEqual(results[self.model_runner_2].status, ModelPredictResult.Status.FAILED)

    @patch('grpc_health.v1.health_pb2_grpc.HealthStub', new_callable=MagicMock)
    async def test_execute_concurrent_method_multiple_timeout(self, mock_grpc_health: MagicMock):
        mock_grpc_health.return_value.Check = AsyncMock(return_value=health_pb2.HealthCheckResponse(status=health_pb2.HealthCheckResponse.SERVING))

        self.model_runner_2.test_method = AsyncMock(side_effect=TimeoutError)

        for i in range(ModelConcurrentRunner.MAX_CONSECUTIVE_TIMEOUTS + 1):
            results = await self.concurrent_runner._execute_concurrent_method("test_method")

        self.mock_model_cluster.process_failure.assert_called_with(self.model_runner_2, 'MULTIPLE_TIMEOUT')
        self.assertEqual(results[self.model_runner_1].result, "mock_result_1")
        self.assertIsNone(results[self.model_runner_2].result)
        self.assertEqual(results[self.model_runner_1].status, ModelPredictResult.Status.SUCCESS)
        self.assertEqual(results[self.model_runner_2].status, ModelPredictResult.Status.TIMEOUT)

    async def test_execute_concurrent_method_bad_implementation(self):
        self.model_runner_2.test_method = AsyncMock(return_value=(None, ModelRunner.ErrorType.BAD_IMPLEMENTATION))

        results = await self.concurrent_runner._execute_concurrent_method("test_method")

        self.assertIn(self.model_runner_1, results)
        self.assertIn(self.model_runner_2, results)
        self.mock_model_cluster.process_failure.assert_called_once_with(self.model_runner_2, 'BAD_IMPLEMENTATION')
        self.assertEqual(results[self.model_runner_1].result, "mock_result_1")
        self.assertIsNone(results[self.model_runner_2].result)
        self.assertEqual(results[self.model_runner_1].status, ModelPredictResult.Status.SUCCESS)
        self.assertEqual(results[self.model_runner_2].status, ModelPredictResult.Status.FAILED)
