import os
import time

from dotenv import load_dotenv
from src.client import *

# Load variables from .env into os.environ
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)


async def main():
    async def get_url():
        # replace with your access token retrieval strategy
        access_token = os.environ.get('ACCESS_TOKEN')
        app_id = os.environ.get('APP_ID')

        # return the WebSocket URL with the access token
        return f"wss://genesis.r7.21no.de/apps/{app_id}?access_token={access_token}"

    config = {
        'logger': logging.getLogger('RealtimeClient'),
        'websocket_options': {
            'url_provider': get_url,
        }
    }
    client = RealtimeClient(config)

    # Connect to the WebSocket server
    await client.connect()
    client.logger.info('Connected to WebSocket server')

    # Define a message handler
    async def handle_session_started(message):
        await client.subscribe_remote_topic('secure/inbound')

    client.on('session.started', handle_session_started)

    async def handle_get_time(message, reply_fn):
        client.logger.info('Responding to gettime request...')
        await reply_fn({
            'time': time.time()
        }, status='ok')

    client.on('secure/inbound.gettime', handle_get_time)

    async def handle_presence(message, reply_fn):
        client.logger.info(f"Presence event received: {message}")
        if message['data']['payload']['status'] == 'connected':
            client.logger.info(f"Client {message['data']['client']['connectionId']} connected...")
        elif message['data']['payload']['status'] == 'disconnected':
            client.logger.info(f"Client {message['data']['client']['connectionId']} disconnected...")

    client.on('secure/inbound.presence', handle_presence)

    while client.ws and not client.ws.closed:
        await asyncio.sleep(1)


# Run the main coroutine
asyncio.run(main())
