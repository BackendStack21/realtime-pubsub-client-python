"""
This module provides a `RealtimeClient` class for real-time communication over WebSocket,
including event handling, message publishing, and reconnection logic.

Classes:
- `EventEmitter`: A simple event emitter for handling events with wildcard support.
- `WaitFor`: A class for waiting on acknowledgments or replies.
- `RealtimeClient`: The main class representing the real-time client.

Functions:
- `reply(client, message)`: Creates a reply function for incoming messages.
"""

import asyncio  # Asynchronous I/O library
import json  # JSON encoding and decoding
import secrets  # Generate secure random numbers
import logging  # Logging library
from typing import Callable  # Type hinting support
from websockets import connect, exceptions


class EventEmitter:
    """
    A simple event emitter class that allows registering and emitting events.
    Supports wildcard events using '*' and '**' with '.' as the separator.
    """

    def __init__(self):
        """
        Initialize an `EventEmitter` instance with an empty events dictionary.
        """
        self._events = {}

    def on(self, event: str, listener: Callable):
        """
        Register a listener for a specific event, with support for wildcards.

        Args:
            event (str): The name of the event, can include wildcards ('*' or '**').
            listener (Callable): The function to call when the event is emitted.
        """
        if event not in self._events:
            self._events[event] = []
        self._events[event].append(listener)

    def off(self, event: str, listener: Callable):
        """
        Remove a listener for a specific event.

        Args:
            event (str): The name of the event.
            listener (Callable): The function to remove from the event listeners.
        """
        if event in self._events:
            try:
                self._events[event].remove(listener)
                if not self._events[event]:
                    del self._events[event]
            except ValueError:
                # Listener not found in the list
                pass

    def emit(self, event: str, *args, **kwargs):
        """
        Trigger all listeners associated with an event, supporting wildcards.

        Args:
            event (str): The name of the event to emit.
            *args: Positional arguments to pass to the event listeners.
            **kwargs: Keyword arguments to pass to the event listeners.
        """
        listeners = []
        for event_pattern, event_listeners in self._events.items():
            if self.event_matches(event_pattern, event):
                listeners.extend(event_listeners)
        for listener in listeners:
            if asyncio.iscoroutinefunction(listener):
                asyncio.create_task(listener(*args, **kwargs))
            else:
                listener(*args, **kwargs)

    def once(self, event: str, listener: Callable):
        """
        Register a listener for a specific event that will be called at most once.

        Args:
            event (str): The name of the event.
            listener (Callable): The function to call when the event is emitted.
        """

        def _once_listener(*args, **kwargs):
            listener(*args, **kwargs)
            self.off(event, _once_listener)

        self.on(event, _once_listener)

    @staticmethod
    def event_matches(pattern: str, event_name: str) -> bool:
        """
        Check if an event pattern matches an event name, supporting wildcards '*' and '**'.

        Args:
            pattern (str): The event pattern, may include wildcards '*' and '**'.
            event_name (str): The event name to match against.

        Returns:
            bool: True if the pattern matches the event name, False otherwise.
        """

        def match_segments(pattern_segments, event_segments):
            i = j = 0
            while i < len(pattern_segments) and j < len(event_segments):
                if pattern_segments[i] == '**':
                    # '**' matches any number of segments, including zero
                    if i == len(pattern_segments) - 1:
                        # '**' at the end matches all remaining segments
                        return True
                    else:
                        # Try to match remaining pattern with any position in event_segments
                        for k in range(j, len(event_segments) + 1):
                            if match_segments(pattern_segments[i + 1:], event_segments[k:]):
                                return True
                        return False
                elif pattern_segments[i] == '*':
                    # '*' matches exactly one segment
                    i += 1
                    j += 1
                elif pattern_segments[i] == event_segments[j]:
                    # Exact match
                    i += 1
                    j += 1
                else:
                    return False
            while i < len(pattern_segments) and pattern_segments[i] == '**':
                i += 1
            return i == len(pattern_segments) and j == len(event_segments)

        pattern_segments = pattern.split('.')
        event_segments = event_name.split('.')
        return match_segments(pattern_segments, event_segments)


def reply(client, message):
    """
    Creates a reply function for the given client and message.

    This function generates a `reply_function` that can be used to send a response back to the sender
    of the incoming message. It ensures that the reply is correctly routed to the appropriate connection.

    Args:
        client (RealtimeClient): The `RealtimeClient` instance used to send the reply.
        message (dict): The incoming message to which the reply is responding.

    Returns:
        Callable: A function that sends a reply message.

    Raises:
        ValueError: If the connection ID is not available in the incoming message.
    """

    def reply_function(data, status='ok', options=None):
        """
        Sends a reply message back to the sender of the original message.

        Args:
            data: The payload data to send in the reply.
            status (str, optional): The status of the reply. Defaults to 'ok'.
            options (dict, optional): Additional message options. Defaults to None.

        Returns:
            WaitFor: An instance to wait for acknowledgments or replies.

        Raises:
            ValueError: If the connection ID is not available in the message.
        """
        connection_id = message['data'].get('client', {}).get('connectionId')
        if connection_id:
            return asyncio.create_task(client.publish(
                f'priv/{connection_id}',
                {
                    'data': data,
                    'status': status,
                    'id': message['data'].get('id'),
                },
                {
                    'messageType': 'response',
                    'compress': options.get('compress', False) if options else False,
                },
            ))
        else:
            raise ValueError('Connection ID is not available in the message')

    return reply_function


class WaitFor:
    """
    Class representing a factory for waiting on acknowledgments or replies.

    The `WaitFor` class provides methods to wait for acknowledgments from the Messaging Gateway
    or replies from other subscribers or backend services. It is used in conjunction with
    message publishing and sending methods to ensure reliable communication.
    """

    def __init__(self, client, options):
        """
        Initialize a new instance of the `WaitFor` class.

        Args:
            client (RealtimeClient): The `RealtimeClient` instance associated with this factory.
            options (dict): The message options used for publishing or sending messages.
        """
        self.client = client
        self.options = options

    async def wait_for_ack(self, timeout=5):
        """
        Wait for an acknowledgment event with a timeout.

        Args:
            timeout (int, optional): The maximum time to wait for the acknowledgment in seconds. Defaults to 5.

        Returns:
            Any: The acknowledgment data received.

        Raises:
            TimeoutError: If the acknowledgment is not received within the timeout period.
        """
        return await self.client.wait_for(f"ack.{self.options['id']}", timeout)

    async def wait_for_reply(self, timeout=5):
        """
        Wait for a reply event with a timeout.

        Args:
            timeout (int, optional): The maximum time to wait for the reply in seconds. Defaults to 5.

        Returns:
            Any: The reply data received.

        Raises:
            TimeoutError: If the reply is not received within the timeout period.
        """
        return await self.client.wait_for(f"response.{self.options['id']}", timeout)


async def wait(ms):
    """
    Wait for a specified duration before proceeding.

    Useful for introducing delays or pacing message sending in your application flow.

    Args:
        ms (int): The duration to wait in milliseconds.

    Returns:
        None
    """
    await asyncio.sleep(ms / 1000.0)


def get_random_id():
    """
    Generate a random identifier string.

    Utilizes the `secrets` module to create secure, unique message identifiers.

    Returns:
        str: A random string suitable for use as a message ID.
    """
    return secrets.token_hex(16)


class RealtimeClient(EventEmitter):
    """
    `RealtimeClient` class encapsulates WebSocket connection, subscription, and message handling.

    The `RealtimeClient` is the core class for interacting with the Realtime Pub/Sub service.
    It manages the WebSocket connection, handles message publishing and subscribing, and
    provides mechanisms to wait for acknowledgments and replies.
    """

    def __init__(self, config):
        """
        Initialize a new instance of the `RealtimeClient` class.

        Args:
            config (dict): The client configuration options, including WebSocket settings, logger, and event emitter options.
        """
        super().__init__()
        self.ws = None
        self.opts = config
        self.logger = self.opts.get('logger', logging.getLogger(__name__))
        self.websocket_options = self.opts.get('websocket_options', {})
        self.event_loop = asyncio.get_event_loop()
        self.subscribed_topics = set()
        self._is_connecting = False  # To prevent concurrent connection attempts

        # Register event listeners for specific events
        self.on('priv/acks.ack', self._on_ack)
        self.on('*.response', self._on_response)
        self.on('main.welcome', self._on_welcome)

    def _on_ack(self, message, reply_fn):
        """
        Handle acknowledgment messages received from the server.

        Args:
            message (dict): The acknowledgment message data.
            reply_fn (Callable): The reply function to send responses (unused here).
        """
        self.logger.debug(f'Received ack: {message["data"]}')
        self.emit(f"ack.{message['data']['data']}")

    def _on_response(self, message, reply_fn):
        """
        Handle response messages received from other subscribers or backend services.

        Args:
            message (dict): The response message data.
            reply_fn (Callable): The reply function to send responses (unused here).
        """
        if message['topic'].startswith('priv/'):
            self.logger.debug(f'Received response for topic {message["topic"]}: {message["data"]}')
            res = message['data']['payload']
            self.emit(f"response.{res['id']}", res)

    def _on_welcome(self, message, reply_fn):
        """
        Handle 'welcome' messages to indicate that the session has started.

        Args:
            message (dict): The welcome message data.
            reply_fn (Callable): The reply function to send responses (unused here).
        """
        self.logger.info(f'Session started, connection details: {message["data"]["connection"]}')
        self.emit('session.started', message['data']['connection'])

    async def connect(self):
        """
        Establish a connection to the WebSocket server.

        Initiates the WebSocket connection using the provided URL from the `url_provider` function.
        Sets up event handlers for incoming messages, errors, and closure events.

        Raises:
            ValueError: If the WebSocket URL is not provided.
        """
        if self._is_connecting:
            self.logger.warning('Already in the process of connecting. Ignoring new connection attempt.')
            return  # Prevent concurrent connection attempts
        self._is_connecting = True
        backoff = 1
        max_backoff = 60

        while True:
            url_provider = self.websocket_options.get('url_provider')
            if callable(url_provider):
                if asyncio.iscoroutinefunction(url_provider):
                    ws_url = await url_provider()
                else:
                    ws_url = url_provider()
            else:
                ws_url = url_provider

            if not ws_url:
                raise ValueError('WebSocket URL is not provided')

            try:
                max_float = float('inf')
                self.ws = await connect(ws_url, max_size=None, ping_interval=None,  ping_timeout=None)
                self.logger.info(f'Connected to WebSocket URL: {ws_url[:80]}...')  # Masking the URL for security
                asyncio.ensure_future(self._receive_messages())

                backoff = 1
                break
            except Exception as e:
                self.handle_error(e)
                self.logger.warning(f'Retrying connection in {backoff} seconds after failure: {e}')
                await asyncio.sleep(backoff)
                backoff = min(max_backoff, backoff * 2)
        self._is_connecting = False

    async def disconnect(self):
        """
        Disconnect from the WebSocket server.

        Closes the active WebSocket connection and cleans up resources.
        """
        if self.ws:
            self.logger.info('Disconnecting from WebSocket...')
            await self.ws.close()
            self.ws = None
            self.logger.info('WebSocket connection closed.')

    async def publish(self, topic, payload, options=None):
        """
        Publish a message to a specified topic.

        Sends a message payload to the designated topic, allowing subscribers to receive and process it.
        Returns a `WaitFor` instance to enable waiting for acknowledgments or replies.

        Args:
            topic (str): The topic to publish the message to.
            payload (str or dict): The message payload.
            options (dict, optional): Optional message options, including `id`, `messageType`, and `compress`.

        Returns:
            WaitFor: An instance to wait for acknowledgments or replies.

        Raises:
            Exception: If the WebSocket connection is not established.
        """
        if not self.ws or self.ws.closed:
            self.logger.error('Attempted to publish without an active WebSocket connection.')
            raise Exception('WebSocket connection is not established')

        options = options or {}
        options['id'] = options.get('id', get_random_id())

        message = json.dumps({
            'type': 'publish',
            'data': {
                'topic': topic,
                'messageType': options.get('messageType'),
                'compress': options.get('compress', False),
                'payload': payload,
                'id': options['id'],
            },
        })

        self.logger.debug(f'Publishing message to topic {topic}: {payload}')
        await self.ws.send(message)

        return WaitFor(self, options)

    async def send(self, payload, options=None):
        """
        Send a message directly to the server.

        Useful for scenarios where you need to send messages to backend services.
        Returns a `WaitFor` instance to enable waiting for acknowledgments or replies.

        Args:
            payload (str or dict): The message payload.
            options (dict, optional): Optional message options, including `id`, `messageType`, and `compress`.

        Returns:
            WaitFor: An instance to wait for acknowledgments or replies.

        Raises:
            Exception: If the WebSocket connection is not established.
        """
        if not self.ws or self.ws.closed:
            self.logger.error('Attempted to send without an active WebSocket connection.')
            raise Exception('WebSocket connection is not established')

        options = options or {}
        options['id'] = options.get('id', get_random_id())

        message = json.dumps({
            'type': 'message',
            'data': {
                'messageType': options.get('messageType'),
                'compress': options.get('compress', False),
                'payload': payload,
                'id': options['id'],
            },
        })

        self.logger.debug(f'Sending message: {payload}')
        await self.ws.send(message)

        return WaitFor(self, options)

    async def subscribe_remote_topic(self, topic):
        """
        Subscribe to a remote topic to receive messages.

        Establishes a subscription to the specified topic, enabling the client to
        receive messages published to it.

        Args:
            topic (str): The topic to subscribe to.

        Returns:
            RealtimeClient: The `RealtimeClient` instance for method chaining.

        Raises:
            Exception: If the WebSocket connection is not established.
        """
        if not self.ws or self.ws.closed:
            self.logger.error(f'Attempted to subscribe to {topic} without an active WebSocket connection.')
            raise Exception('WebSocket connection is not established')

        self.subscribed_topics.add(topic)

        message = json.dumps({
            'type': 'subscribe',
            'data': {'topic': topic},
        })

        self.logger.info(f'Subscribing to topic: {topic}')
        await self.ws.send(message)

        return self

    async def unsubscribe_remote_topic(self, topic):
        """
        Unsubscribe from a previously subscribed topic.

        Removes the subscription to the specified topic, stopping the client from receiving
        further messages from it.

        Args:
            topic (str): The topic to unsubscribe from.

        Returns:
            RealtimeClient: The `RealtimeClient` instance for method chaining.

        Raises:
            Exception: If the WebSocket connection is not established.
        """
        if not self.ws or self.ws.closed:
            self.logger.error(f'Attempted to unsubscribe from {topic} without an active WebSocket connection.')
            raise Exception('WebSocket connection is not established')

        self.subscribed_topics.discard(topic)

        message = json.dumps({
            'type': 'unsubscribe',
            'data': {'topic': topic},
        })

        self.logger.info(f'Unsubscribing from topic: {topic}')
        await self.ws.send(message)

        return self

    async def _receive_messages(self):
        """
        Internal method to receive messages from the WebSocket.

        Processes messages received from the WebSocket connection, deserializes them,
        and emits appropriate events based on the message topic and type.
        """
        try:
            async for message in self.ws:
                await self.on_message(message)
        except exceptions.ConnectionClosed as e:
            self.logger.warning(f'WebSocket closed: {e}')
            await self.handle_close(e)
        except Exception as e:
            self.handle_error(e)

    async def on_message(self, message):
        """
        Handle incoming WebSocket messages.

        Processes messages received from the WebSocket connection, deserializes them,
        and emits appropriate events based on the message topic and type.

        Args:
            message (str or bytes): The message received from the WebSocket.
        """
        try:
            message_data = json.loads(message.decode('utf-8')) if isinstance(message, bytes) else json.loads(message)
            topic = message_data.get('topic')
            message_type = message_data.get('messageType')
            data = message_data.get('data')
            message_event = {
                'topic': topic,
                'messageType': message_type,
                'data': data,
                'compression': not isinstance(message, str),
            }

            self.logger.debug(f"Incoming message: {message_event}")
            if message_type:
                self.emit(f"{topic}.{message_type}", message_event, reply(self, message_event))
        except Exception as e:
            self.handle_error(e)

    async def wait_for(self, event_name, timeout=None):
        """
        Wait for a specific event to occur within a timeout period.

        Args:
            event_name (str): The name of the event to wait for.
            timeout (int, optional): The maximum time to wait in seconds. Defaults to None.

        Returns:
            Any: The data associated with the event when it occurs.

        Raises:
            TimeoutError: If the event does not occur within the timeout period.
        """
        future = self.event_loop.create_future()

        def _listener(*args, **kwargs):
            if not future.done():
                future.set_result(args)

        self.on(event_name, _listener)

        try:
            result = await asyncio.wait_for(future, timeout)
            self.logger.debug(f"Event '{event_name}' received: {result}")
            return result
        except asyncio.TimeoutError:
            self.logger.error(f"Timeout waiting for event '{event_name}'")
            raise TimeoutError(f"Timeout waiting for event {event_name}")
        finally:
            self.off(event_name, _listener)

    def handle_error(self, error):
        """
        Handle WebSocket errors by logging and emitting an 'error' event.

        Args:
            error (Exception): The error object encountered during WebSocket communication.
        """
        self.logger.error(f'WebSocket error: {error}')
        self.emit('error', error)

    async def handle_close(self, event):
        """
        Handle WebSocket closure events by logging and emitting a 'close' event.

        Args:
            event (Exception): The close event received from the WebSocket.
        """
        self.logger.info(f'WebSocket closed: {event}')
        self.emit('close', event)
        await self.connect()
