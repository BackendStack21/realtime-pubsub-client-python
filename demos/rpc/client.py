import os
import time
import logging
import asyncio

from dotenv import load_dotenv
from realtime_pubsub_client import RealtimeClient

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


    # Define a message handler
    async def handle_session_started(message):
        client.logger.info('Requesting server time...')
        waiter = await client.send('', {
            'messageType': 'gettime'
        })

        response, = await waiter.wait_for_reply(timeout=5)
        client.logger.info(f"Server time: {time.ctime(response['data']['time'])}")

        await client.disconnect()

    client.on('session.started', handle_session_started)

    while client.ws and not client.ws.closed:
        await asyncio.sleep(1)

# Run the main coroutine
asyncio.run(main())
