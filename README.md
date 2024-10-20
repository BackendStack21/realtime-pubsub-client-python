# Realtime Pub/Sub Client for Python

The `realtime-pubsub-client` is a Python client library for interacting
with [Realtime Pub/Sub](https://realtime.21no.de) applications. It enables developers to manage real-time WebSocket
connections, handle subscriptions, and process messages efficiently. The library provides a simple and flexible API to
interact with realtime applications, supporting features like publishing/sending messages, subscribing to topics,
handling acknowledgements, and waiting for replies with timeout support.

## Features

- **WebSocket Connection Management**: Seamlessly connect and disconnect from the Realtime Pub/Sub service with
  automatic reconnection support.
- **Topic Subscription**: Subscribe and unsubscribe to topics for receiving messages.
- **Topic Publishing**: [Publish](https://realtime.21no.de/documentation/#publishers) messages to specific topics with
  optional message types and compression.
- **Message Sending**: [Send](https://realtime.21no.de/documentation/#websocket-inbound-messaging) messages to backend
  applications with optional message types and compression.
- **Event Handling**: Handle incoming messages with custom event listeners.
- **Acknowledgements and Replies**: Wait for gateway acknowledgements or replies to messages with timeout support.
- **Error Handling**: Robust error handling and logging capabilities.
- **Asynchronous Support**: Built using `asyncio` for efficient asynchronous programming.

## Installation

Install the `realtime-pubsub-client` library via pip:

```bash
pip install realtime-pubsub-client
```

## Getting Started

This guide will help you set up and use the `realtime-pubsub-client` library in your Python project.

### Connecting to the Server

First, import the `RealtimeClient` class and create a new instance with the required configuration:

```python
import asyncio
import logging
import os
from realtime_pubsub_client import RealtimeClient


async def main():
    async def get_url():
        # replace with your access token retrieval strategy
        access_token = os.environ.get('ACCESS_TOKEN')
        app_id = os.environ.get('APP_ID')

        # return the WebSocket URL with the access token
        return f"wss://genesis.r7.21no.de/apps/{app_id}?access_token={access_token}"

    client_options = {
        'logger': logging.getLogger('RealtimeClient'),
        'websocket_options': {
            'url_provider': get_url,
        },
    }
    client = RealtimeClient(client_options)

    async def on_session_started(connection_info):
        print('Connection ID:', connection_info['id'])
        # Subscribe to topics here
        await client.subscribe_remote_topic('topic1')
        await client.subscribe_remote_topic('topic2')

    client.on('session.started', on_session_started)

    await client.connect()
    await client.wait_for('session.started')


asyncio.run(main())
```

### Subscribing to Incoming Messages

You can handle messages for specific topics and message types:

> **Note**: The topic and message type are separated by a dot (`.`) in the event name.

```python
def handle_message(message, reply_fn):
    # Message handling logic here
    print('Received message:', message['data']['payload'])


client.on('topic1.action1', handle_message)
```

Wildcard subscriptions are also supported:

```python
client.on('topic1.*', handle_message)
```

### Publishing Messages

Publish messages to a topic:

```python
await client.publish('topic1', 'Hello, world!', message_type='text-message')
```

### Responding to Incoming Messages

Set up event listeners to handle incoming messages:

```python
async def handle_message(message, reply_fn):
    # Processing the message
    print('Received message:', message['data']['payload'])

    # Sending a reply
    await reply_fn('Message received!', 'ok')


client.on('topic1.text-message', handle_message)
```

### Waiting for Acknowledgements and Replies

- **`wait_for_ack(timeout=None)`**: Waits for an acknowledgement of the message, with an optional timeout in seconds.
- **`wait_for_reply(timeout=None)`**: Waits for a reply to the message, with an optional timeout in seconds.

Wait for the Realtime Gateway acknowledgement after publishing a message:

```python
waiter = await client.publish('secure/peer-to-peer1', 'Hi', message_type='text-message')
await waiter.wait_for_ack()
```

Wait for the Realtime Gateway acknowledgement after sending a message:

```python
waiter = await client.send({
    # Message payload
}, message_type='create')
await waiter.wait_for_ack()
```

Wait for a reply with a timeout:

```python
waiter = await client.send({
    # Message payload
}, message_type='create')
await waiter.wait_for_reply(timeout=5)  # Wait for up to 5 seconds
```

### Error Handling

Handle errors and disconnections:

```python
def on_error(error):
    print('WebSocket error:', error)


def on_close(event):
    print('WebSocket closed:', event)


client.on('error', on_error)
client.on('close', on_close)
```

## API Reference

### RealtimeClient

#### Constructor

```python
RealtimeClient(config)
```

Creates a new `RealtimeClient` instance.

- **`config`**: Configuration options for the client.

#### Methods

- **`connect()`**: Connects the client to the WebSocket Messaging Gateway.

  ```python
  await client.connect()
  ```

- **`disconnect()`**: Terminates the WebSocket connection.

  ```python
  await client.disconnect()
  ```

- **`subscribe_remote_topic(topic)`**: [Subscribes](https://realtime.21no.de/documentation/#subscribers) the connection
  to a remote topic.

  ```python
  await client.subscribe_remote_topic(topic)
  ```

- **`unsubscribe_remote_topic(topic)`**: [Unsubscribes](https://realtime.21no.de/documentation/#subscribers) the
  connection from a remote topic.

  ```python
  await client.unsubscribe_remote_topic(topic)
  ```

- **`publish(topic, payload, message_type="broadcast", compress=False, message_id=None)`**: Publishes a message to a topic.

  ```python
  waiter = await client.publish(topic, payload)
  ```

  Returns a `WaitFor` instance to wait for acknowledgements or replies.

- **`send(payload, compress=False, message_id=None)`**: Sends a message to the server.

  ```python
  waiter = await client.send(payload, options)
  ```

  Returns a `WaitFor` instance to wait for acknowledgements or replies.

- **`wait(ms)`**: Waits for a specified duration in milliseconds. Utility function for waiting in async functions.

  ```python
  await wait(ms)
  ```

#### Events

- **`'session.started'`**: Emitted when the session starts.

  ```python
  client.on('session.started', on_session_started)
  ```

- **`'error'`**: Emitted on WebSocket errors.

  ```python
  client.on('error', on_error)
  ```

- **`'close'`**: Emitted when the WebSocket connection closes.

  ```python
  client.on('close', on_close)
  ```

- **Custom Events**: Handle custom events based on topic and message type.

  ```python
  client.on('TOPIC_NAME.MESSAGE_TYPE', handle_message)
  ```

  > **Note**: Wildcard subscriptions are also supported.

## License

This library is licensed under the MIT License.

---

For more detailed examples and advanced configurations, please refer to
the [documentation](https://realtime.21no.de/docs).

## Notes

- Ensure that you have an account and an app set up with [Realtime Pub/Sub](https://realtime.21no.de).
- Customize the `url_provider` or URL to retrieve the access token for connecting to your realtime application.
- Implement the `get_auth_token` function according to your authentication mechanism.
- Optionally use the `logger` option to integrate with your application's logging system.
- Handle errors and disconnections gracefully to improve the robustness of your application.
- Make sure to handle timeouts when waiting for replies to avoid hanging operations.

---

Feel free to contribute to this project by submitting issues or pull requests
on [GitHub](https://github.com/BackendStack21/realtime-pubsub-client-python).