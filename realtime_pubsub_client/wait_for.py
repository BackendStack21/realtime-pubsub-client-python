"""
This module contains the `WaitFor` class representing a factory for waiting on acknowledgments or replies.

Classes:
- WaitFor: A class representing a factory for waiting on acknowledgments or replies.
"""


class WaitFor:
    """
    Class representing a factory for waiting on acknowledgments or replies.

    The `WaitFor` class provides methods to wait for acknowledgments from the Messaging Gateway
    or replies from other subscribers or backend services. It is used in conjunction with
    message publishing and sending methods to ensure reliable communication.
    """

    def __init__(self, client, message_id):
        """
        Initialize a new instance of the `WaitFor` class.

        Args:
            client (RealtimeClient): The `RealtimeClient` instance associated with this factory.
            message_id (str): The unique identifier for the message being acknowledged or replied to.
        """
        self.client = client
        self.message_id = message_id

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
        return await self.client.wait_for(f"ack.{self.message_id}", timeout)

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
        return await self.client.wait_for(f"response.{self.message_id}", timeout)
