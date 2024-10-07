import os
from dotenv import load_dotenv
from src.client import *

# Load variables from .env into os.environ
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)


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
        print('Session started:', message)
        await client.subscribe_remote_topic('chat')

    client.on('session.started', handle_session_started)

    # Send a message
    wait_for = await client.send('Hello, world!', {
        'messageType': 'text-message'
    })
    await wait_for.wait_for_ack()

    # Define a message handler
    def handle_message(message, reply_fn):
        print('New chat message arrived:', message)

        reply_fn({
            'text': 'Hello, back!'
        })

    # Subscribe to chat.text-message events
    client.on('chat.text-message', handle_message)

    wait_for = await client.publish('chat', 'Hello out there!', {
        'messageType': 'text-message'
    })
    response = await wait_for.wait_for_reply()
    print('Reply:', response)

    # Disconnect from the server
    await client.disconnect()


# Run the main coroutine
asyncio.run(main())
