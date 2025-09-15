import asyncio
from unittest.mock import ANY

import pytest
from grpc.aio import AioRpcError
from model_runner_client.model_runners.model_runner import ModelRunner, InvalidCoordinatorUsageError

from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch, MagicMock


class TestModelRunner(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.runner = ModelRunner(deployment_id="deployment_id_1", model_id="test_id", model_name="test_name", ip="127.0.0.1", port=5000, infos={})
        self.runner.setup = AsyncMock(return_value=(True, None))
        self.runner.retry_backoff_factor = 0

    @patch('model_runner_client.model_runners.model_runner.grpc.aio.insecure_channel')
    async def test_init_successful(self, mock_insecure_channel):
        mock_insecure_channel.return_value.channel_ready = AsyncMock(return_value=False)
        success, error = await self.runner.init()

        self.assertTrue(success)
        self.assertIsNone(error)
        mock_insecure_channel.assert_called_once_with("127.0.0.1:5000", ANY)
        self.runner.setup.assert_called_once()

    @patch('model_runner_client.model_runners.model_runner.grpc.aio.insecure_channel')
    async def test_init_grpc_error(self, mock_insecure_channel):
        mock_insecure_channel.side_effect = AioRpcError
        success, error = await self.runner.init()

        self.assertEqual(mock_insecure_channel.call_count, self.runner.retry_attempts)
        self.assertFalse(success)
        self.assertEqual(error, ModelRunner.ErrorType.GRPC_CONNECTION_FAILED)

    @patch('model_runner_client.model_runners.model_runner.grpc.aio.insecure_channel')
    async def test_init_timeout_error(self, mock_insecure_channel):
        mock_insecure_channel.side_effect = asyncio.TimeoutError
        success, error = await self.runner.init()

        self.assertEqual(mock_insecure_channel.call_count, self.runner.retry_attempts)
        self.assertFalse(success)
        self.assertEqual(error, ModelRunner.ErrorType.GRPC_CONNECTION_FAILED)

    @patch('model_runner_client.model_runners.model_runner.grpc.aio.insecure_channel')
    async def test_init_aborted(self, mock_insecure_channel):
        await self.runner.close()

        success, error = await self.runner.init()

        self.assertFalse(success)
        self.assertEqual(error, ModelRunner.ErrorType.ABORTED)

    @patch('model_runner_client.model_runners.model_runner.grpc.aio.insecure_channel')
    async def test_init_unexpected_error(self, mock_insecure_channel):
        mock_insecure_channel.side_effect = Exception("Unexpected error")

        success, error = await self.runner.init()

        # Assert
        self.assertFalse(success)
        self.assertEqual(error, ModelRunner.ErrorType.GRPC_CONNECTION_FAILED)

    @patch('model_runner_client.model_runners.model_runner.grpc.aio.insecure_channel')
    async def test_init_invalid_coordinator_usage_error(self, mock_insecure_channel):
        mock_insecure_channel.return_value.channel_ready = AsyncMock(return_value=False)
        self.runner.setup = AsyncMock(side_effect=InvalidCoordinatorUsageError)

        with self.assertRaises(InvalidCoordinatorUsageError):
            await self.runner.init()

    @patch('model_runner_client.model_runners.model_runner.grpc.aio.insecure_channel')
    async def test_init_invalid_coordinator_error(self, mock_insecure_channel):
        mock_insecure_channel.return_value.channel_ready = AsyncMock(return_value=False)
        self.runner.setup = AsyncMock(return_value=(False, ModelRunner.ErrorType.BAD_IMPLEMENTATION))

        success, error = await self.runner.init()
        self.assertFalse(success)
        self.assertEqual(error, ModelRunner.ErrorType.BAD_IMPLEMENTATION)
