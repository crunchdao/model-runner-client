from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from model_runner_client.model_concurrent_runners.model_concurrent_runner import ModelConcurrentRunner
from model_runner_client.model_concurrent_runners.model_concurrent_runner import ModelPredictResult
from model_runner_client.model_runners.model_runner import ModelRunner

class TestModelConcurrentRunner(IsolatedAsyncioTestCase):
    def setUp(self):
        self.model_runner_1 = ModelRunner("mock_model_1", "MockModel", "127.0.0.1", 1234)
        self.model_runner_1.test_method = AsyncMock(return_value=("mock_result_1", None))
        self.model_runner_1.init = AsyncMock()

        self.model_runner_2 = ModelRunner("mock_model_2", "MockModel", "127.0.0.1", 1234)
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


        self.concurrent_runner = ModelConcurrentRunner(
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

    async def test_execute_concurrent_method_timeout(self):
        self.model_runner_2.test_method = AsyncMock(side_effect=TimeoutError)

        results = await self.concurrent_runner._execute_concurrent_method("test_method")

        self.assertEqual(results[self.model_runner_1].result, "mock_result_1")
        self.assertIsNone(results[self.model_runner_2].result)
        self.assertEqual(results[self.model_runner_1].status, ModelPredictResult.Status.SUCCESS)
        self.assertEqual(results[self.model_runner_2].status, ModelPredictResult.Status.TIMEOUT)

    async def test_execute_concurrent_method_multiple_failure(self):
        self.model_runner_2.test_method = AsyncMock(return_value=(None, ModelRunner.ErrorType.FAILED))

        for i in range(ModelConcurrentRunner.MAX_CONSECUTIVE_FAILURES + 1):
            results = await self.concurrent_runner._execute_concurrent_method("test_method")

        self.mock_model_cluster.process_failure.assert_called_with(self.model_runner_2, 'MULTIPLE_FAILED')
        self.assertEqual(results[self.model_runner_1].result, "mock_result_1")
        self.assertIsNone(results[self.model_runner_2].result)
        self.assertEqual(results[self.model_runner_1].status, ModelPredictResult.Status.SUCCESS)
        self.assertEqual(results[self.model_runner_2].status, ModelPredictResult.Status.FAILED)

    async def test_execute_concurrent_method_multiple_timeout(self):
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
