import unittest
from unittest.mock import AsyncMock, MagicMock

from realtime_pubsub_client.client import WaitFor


class TestWaitFor(unittest.IsolatedAsyncioTestCase):
    """
    Test suite for the WaitFor class, which provides mechanisms to wait for
    acknowledgments and replies when interacting with the RealtimeClient.
    """

    async def test_wait_for_ack(self):
        """
        Test waiting for an acknowledgment from the client.

        Simulates the behavior of waiting for an 'ack' event with a specific ID.
        Ensures that the correct event is awaited and the result is returned as expected.
        """
        # Create a mock client and set up the mock wait_for method
        client = MagicMock()
        client.wait_for = AsyncMock(return_value='acknowledged')

        # Define options with a specific message ID
        options = '1234'

        # Create an instance of WaitFor with the mock client and options
        waiter = WaitFor(client, options)

        # Await the acknowledgment
        result = await waiter.wait_for_ack(timeout=1)

        # Assert that the result matches the mock return value
        self.assertEqual(result, 'acknowledged')

        # Assert that the correct event was awaited with the right ID and timeout
        client.wait_for.assert_awaited_with('ack.1234', 1)

    async def test_wait_for_reply(self):
        """
        Test waiting for a reply from the client.

        Simulates the behavior of waiting for a 'response' event with a specific ID.
        Ensures that the correct event is awaited and the result is returned as expected.
        """
        # Create a mock client and set up the mock wait_for method
        client = MagicMock()
        client.wait_for = AsyncMock(return_value='response')

        # Define options with a specific message ID
        options = '5678'

        # Create an instance of WaitFor with the mock client and options
        waiter = WaitFor(client, options)

        # Await the reply
        result = await waiter.wait_for_reply(timeout=1)

        # Assert that the result matches the mock return value
        self.assertEqual(result, 'response')

        # Assert that the correct event was awaited with the right ID and timeout
        client.wait_for.assert_awaited_with('response.5678', 1)
