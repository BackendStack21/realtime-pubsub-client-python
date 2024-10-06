import unittest
from src.client import EventEmitter


class TestEventEmitter(unittest.TestCase):
    """
    Test suite for the EventEmitter class, which provides mechanisms for registering,
    emitting, and removing event listeners, including support for wildcards.
    """

    def setUp(self):
        """
        Set up a new EventEmitter instance before each test.
        """
        self.emitter = EventEmitter()

    def test_event_registration_and_emission(self):
        """
        Test the basic event registration and emission functionality.

        This test ensures that when an event is registered with a listener,
        and the event is emitted, the listener is called with the correct payload.
        """
        called = []

        # Define a simple listener that appends data to the 'called' list
        def listener(data):
            called.append(data)

        # Register the listener to the 'test.event'
        self.emitter.on('test.event', listener)

        # Emit the 'test.event' event with a payload
        self.emitter.emit('test.event', 'payload')

        # Assert that the listener was called with the correct payload
        self.assertEqual(called, ['payload'])

    def test_wildcard_event(self):
        """
        Test wildcard event registration and emission.

        This test ensures that listeners registered with wildcards (e.g., '*.event')
        receive the correct events when any matching event is emitted.
        """
        called = []

        # Define a simple listener that appends data to the 'called' list
        def listener(data):
            called.append(data)

        # Register the listener with a wildcard pattern '*.event'
        self.emitter.on('*.event', listener)

        # Emit various events and check which ones are caught
        self.emitter.emit('test.event', 'payload1')
        self.emitter.emit('other.event', 'payload2')
        self.emitter.emit('test.other', 'payload3')

        # Only 'test.event' and 'other.event' should match '*.event'
        self.assertEqual(called, ['payload1', 'payload2'])

    def test_event_removal(self):
        """
        Test event listener removal.

        This test ensures that after removing a listener for a specific event,
        the listener is no longer called when the event is emitted.
        """
        called = []

        # Define a listener that appends data to the 'called' list
        def listener(data):
            called.append(data)

        # Register the listener to the 'test.event'
        self.emitter.on('test.event', listener)

        # Remove the listener for 'test.event'
        self.emitter.off('test.event', listener)

        # Emit 'test.event' and ensure the listener is not called
        self.emitter.emit('test.event', 'payload')

        # Assert that the listener was not called after removal
        self.assertEqual(called, [])

    def test_once_listener(self):
        """
        Test 'once' listener functionality.

        This test ensures that a listener registered with 'once' is only called
        the first time the event is emitted, and not for subsequent emissions.
        """
        called = []

        # Define a listener that appends data to the 'called' list
        def listener(data):
            called.append(data)

        # Register the listener with 'once' for 'test.event'
        self.emitter.once('test.event', listener)

        # Emit the event twice
        self.emitter.emit('test.event', 'payload1')
        self.emitter.emit('test.event', 'payload2')

        # Assert that the listener was only called for the first emission
        self.assertEqual(called, ['payload1'])

    def test_event_matches(self):
        """
        Test the event pattern matching logic for various event patterns.

        This test verifies that the event matching supports both single-segment ('*')
        and multi-segment ('**') wildcards, and that it correctly matches event names
        against these patterns.
        """
        # Test wildcard pattern matching for events
        self.assertTrue(self.emitter.event_matches('*.event', 'test.event'))
        self.assertFalse(self.emitter.event_matches('*.event', 'test.event.more'))
        self.assertTrue(self.emitter.event_matches('**', 'any.event.name'))
        self.assertTrue(self.emitter.event_matches('test.**', 'test.event.name'))
        self.assertFalse(self.emitter.event_matches('test.*', 'test.event.name'))
