from collections import deque


class OrderQueue:
    """A FIFO queue for normal canteen orders."""

    def __init__(self):
        self._orders = deque()

    def enqueue(self, order):
        """Add an order to the back of the queue."""
        self._orders.append(order)

    def dequeue(self):
        """Remove and return the oldest order, or None when empty."""
        if not self._orders:
            return None
        return self._orders.popleft()

    def peek(self):
        """Return the oldest order without removing it."""
        if not self._orders:
            return None
        return self._orders[0]

    def get_all(self):
        """Return pending orders from oldest to newest."""
        return list(self._orders)

    def is_empty(self):
        return not self._orders

    def __len__(self):
        return len(self._orders)
