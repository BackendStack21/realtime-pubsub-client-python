import unittest
import logging
import os
from dotenv import load_dotenv
from src.client import RealtimeClient, wait


class TestRealtimeClientRemote(unittest.IsolatedAsyncioTestCase):
    """
    Test suite for RealtimeClient handling remote WebSocket connections.
    Includes tests for connection, disconnection, publishing, subscribing,
    and sending messages with acknowledgment and reply mechanisms.
    """

    def setUp(self):
        """
        Set up the RealtimeClient instance before each test by loading environment variables
        from the .env file and configuring WebSocket connection details.
        """
        # Load variables from .env into os.environ
        load_dotenv()

        # Fetch access token and app ID from environment variables
        access_token = os.environ.get('ACCESS_TOKEN')
        app_id = os.environ.get('APP_ID')

        # Set up client configuration
        config = {
            'logger': logging.getLogger('RealtimeClient'),
            'websocket_options': {
                'urlProvider': f"wss://genesis.r7.21no.de/apps/{app_id}?access_token={access_token}",
            }
        }

        # Initialize RealtimeClient with the config
        self.client = RealtimeClient(config)

    async def test_connect_disconnect(self):
        """
        Test establishing and disconnecting a WebSocket connection.
        Ensures that the client successfully connects and disconnects from the server.
        """
        # Test connection
        await self.client.connect()
        self.assertIsNotNone(self.client.ws)  # Ensure WebSocket connection is established
        self.assertFalse(self.client.ws.closed)  # Ensure WebSocket is not closed

        # Test disconnection
        await self.client.disconnect()
        self.assertIsNone(self.client.ws)  # Ensure WebSocket connection is cleaned up

    async def test_publish_and_reply(self):
        """
        Test publishing a message to a topic and receiving a reply.
        Ensures that a message is sent and the client correctly handles the reply.
        """

        # Define an event handler to subscribe to the 'chat' topic when the session starts
        async def handle_session_started(message):
            await self.client.subscribe_remote_topic('chat')

        # Register session started event listener
        self.client.on('session.started', handle_session_started)

        # Connect to WebSocket
        await self.client.connect()
        # Wait for the session to start
        await self.client.wait_for('session.started')

        # Define a message handler for 'chat.text-message'
        async def handle_message(message, reply_fn):
            self.assertEqual(message['data']['payload'], 'Hello out there!')

            await reply_fn('Hello, back!')  # Reply to the incoming message

        # Subscribe to 'chat.text-message' events
        self.client.on('chat.text-message', handle_message)

        # Publish a message and wait for a reply
        wait_for = await self.client.publish('chat', 'Hello out there!', {
            'messageType': 'text-message'
        })
        response, = await wait_for.wait_for_reply()  # Unpack the single-element response tuple

        # Verify the reply data
        self.assertEqual(response['data'], 'Hello, back!')

        # Disconnect after the test
        await self.client.disconnect()

    async def test_send_and_ack_compressed(self):
        """
        Test sending a message to a topic and receiving an acknowledgment.
        Ensures that a message is sent, and the client waits for the acknowledgment.
        """

        # Define a message handler for incoming text messages
        def handle_message(message, reply_fn):
            self.assertEqual(message['data']['payload'], 'Hello, world!')

        # Subscribe to 'secure/inbound.text-message' events
        self.client.on('secure/inbound.text-message', handle_message)

        # Connect to WebSocket
        await self.client.connect()
        # Wait for the session to start
        await self.client.wait_for('session.started')

        # Send a message and wait for acknowledgment
        wait_for = await self.client.send('Hello, world!', {
            'messageType': 'text-message',
            'compress': True
        })
        await wait_for.wait_for_ack()  # Wait for the acknowledgment

        # Disconnect after the test
        await self.client.disconnect()
