"""
A simple event emitter class that allows registering and emitting events.

Classes:
- EventEmitter: A class that allows registering and emitting events.
"""

import asyncio
from typing import Callable  # Type hinting support


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
