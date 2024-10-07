import unittest
import logging
import asyncio
from unittest.mock import AsyncMock, patch
import json

# Import your RealtimeClient module
from realtime_pubsub_client.client import RealtimeClient, WaitFor


class TestRealtimeClient(unittest.IsolatedAsyncioTestCase):
    """
    Test suite for the RealtimeClient class, covering WebSocket operations
    such as connecting, disconnecting, publishing, subscribing, and handling events.
    """

    def setUp(self):
        """
        Set up the test environment by patching the WebSocket connection and creating a mock WebSocket object.
        """
        # Patch 'connect' in 'src.client' where it is used, preventing actual WebSocket connections
        self.patcher = patch('realtime_pubsub_client.client.connect', new_callable=AsyncMock)
        self.mock_connect = self.patcher.start()  # Start the patcher
        self.addCleanup(self.patcher.stop)  # Stop patcher when test ends

        # Create a mock WebSocket object
        self.mock_ws = AsyncMock()
        self.mock_ws.closed = False  # Initially, WebSocket is not closed
        self.mock_ws.close = AsyncMock()  # Mock close method
        self.mock_ws.send = AsyncMock()  # Mock send method

        # Set up an empty iterator for incoming messages
        self.mock_ws.__aiter__.return_value = iter([])

        # Set the mock 'connect' to return the mock WebSocket
        self.mock_connect.return_value = self.mock_ws

        # Example URL for WebSocket connection
        url = f"wss://mock.genesis.r7.21no.de/apps/XXX?access_token=XXX"

        # Initialize RealtimeClient with configuration
        self.client = RealtimeClient({
            'logger': logging.getLogger('TestRealtimeClient'),
            'websocket_options': {
                'url_provider': url
            }
        })

    async def test_connect(self):
        """
        Test establishing a WebSocket connection.
        Ensures that the client connects and the WebSocket object is properly initialized.
        """
        await self.client.connect()
        self.assertIsNotNone(self.client.ws)  # Ensure WebSocket connection is established
        self.assertFalse(self.client.ws.closed)  # Ensure WebSocket is not closed

    async def test_disconnect(self):
        """
        Test disconnecting from the WebSocket server.
        Ensures that the WebSocket is closed and cleaned up correctly.
        """
        await self.client.connect()
        ws = self.client.ws  # Save reference to WebSocket before disconnecting
        await self.client.disconnect()
        ws.close.assert_awaited_once()  # Ensure close method was awaited
        self.assertIsNone(self.client.ws)  # Ensure WebSocket object is set to None after disconnect

    async def test_publish(self):
        """
        Test publishing a message to a topic.
        Ensures that the message is sent over the WebSocket and the WaitFor object is returned.
        """
        await self.client.connect()
        waiter = await self.client.publish('test.topic', {'key': 'value'}, {'messageType': 'test-message'})
        self.assertIsInstance(waiter, WaitFor)  # Ensure a WaitFor instance is returned
        self.client.ws.send.assert_awaited_once()  # Ensure the message was sent

    async def test_send(self):
        """
        Test sending a direct message to the WebSocket server.
        Ensures that the message is sent, and a WaitFor object is returned for acknowledgment.
        """
        await self.client.connect()
        waiter = await self.client.send({'key': 'value'}, {'messageType': 'test-message'})
        self.assertIsInstance(waiter, WaitFor)  # Ensure a WaitFor instance is returned
        self.client.ws.send.assert_awaited_once()  # Ensure the message was sent

    async def test_subscribe_remote_topic(self):
        """
        Test subscribing to a remote topic.
        Ensures that the subscription request is sent over the WebSocket, and the topic is tracked.
        """
        await self.client.connect()
        await self.client.subscribe_remote_topic('test.topic')
        self.client.ws.send.assert_awaited_once()  # Ensure subscription was sent
        self.assertIn('test.topic', self.client.subscribed_topics)  # Ensure topic is tracked

    async def test_unsubscribe_remote_topic(self):
        """
        Test unsubscribing from a remote topic.
        Ensures that the unsubscription request is sent, and the topic is removed from tracking.
        """
        await self.client.connect()
        await self.client.subscribe_remote_topic('test.topic')
        self.client.ws.send.reset_mock()  # Reset the mock to track unsubscribe call
        await self.client.unsubscribe_remote_topic('test.topic')
        self.client.ws.send.assert_awaited_once()  # Ensure unsubscription was sent
        self.assertNotIn('test.topic', self.client.subscribed_topics)  # Ensure topic is removed

    async def test_receive_message(self):
        """
        Test receiving a message from the WebSocket.
        Ensures that the incoming message is processed and the corresponding event is triggered.
        """
        await self.client.connect()

        # Mock the incoming messages
        self.mock_ws.__aiter__.return_value = [json.dumps({
            'topic': 'test.topic',
            'messageType': 'test-message',
            'data': {'key': 'value'}
        })]

        called = []  # Store received messages

        # Define an event listener
        def listener(message, reply_fn):
            called.append(message)

        # Subscribe to test.topic.test-message events
        self.client.on('test.topic.test-message', listener)

        # Allow time for the message to be processed
        await asyncio.sleep(0.1)

        # Ensure the message was received and processed
        self.assertEqual(len(called), 1)
        self.assertEqual(called[0]['data'], {'key': 'value'})

    async def test_handle_close(self):
        """
        Test handling WebSocket close events.
        Ensures that the client attempts to reconnect after a close event.
        """
        await self.client.connect()
        # Patch the connect method to simulate a reconnect
        with patch.object(self.client, 'connect', new_callable=AsyncMock) as mock_reconnect:
            await self.client.handle_close(Exception('Closed'))
            mock_reconnect.assert_awaited_once()  # Ensure reconnect was attempted

    async def test_wait_for_event(self):
        """
        Test waiting for an event with a timeout.
        Ensures that the client successfully waits for a specific event within the timeout period.
        """

        async def trigger_event():
            await asyncio.sleep(0.1)
            self.client.emit('test.event', 'data')  # Trigger the event

        # Create a future to wait for the event
        future = asyncio.ensure_future(self.client.wait_for('test.event', timeout=1))
        asyncio.ensure_future(trigger_event())  # Trigger the event in the background

        result = await future  # Wait for the event to be emitted
        self.assertEqual(result, ('data',))  # Ensure the event data matches

    async def test_wait_for_event_timeout(self):
        """
        Test waiting for an event that times out.
        Ensures that the client raises a TimeoutError if the event is not emitted within the timeout.
        """
        with self.assertRaises(TimeoutError):
            await self.client.wait_for('test.event', timeout=0.1)

    async def test_handle_error(self):
        """
        Test handling WebSocket errors.
        Ensures that the error is logged and the error event is emitted.
        """
        called = []  # Store received errors

        # Define an error listener
        def error_listener(error):
            called.append(error)

        # Subscribe to error events
        self.client.on('error', error_listener)

        # Simulate an error
        self.client.handle_error(Exception('Test error'))

        # Ensure the error event was emitted
        self.assertEqual(len(called), 1)
        self.assertEqual(str(called[0]), 'Test error')
