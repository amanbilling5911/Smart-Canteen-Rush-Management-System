import heapq
import itertools


class PriorityOrderQueue:
    """A max-priority queue that keeps earlier orders first on ties."""

    def __init__(self):
        self._heap = []
        self._sequence = itertools.count()

    def enqueue(self, order, priority):
        """Add an order; a larger priority number means higher priority."""
        if not isinstance(priority, int) or priority < 1:
            raise ValueError("Priority must be a positive whole number.")
        sequence = next(self._sequence)
        heapq.heappush(self._heap, (-priority, sequence, order))

    def dequeue(self):
        """Remove the highest-priority order, or None when empty."""
        if not self._heap:
            return None
        return heapq.heappop(self._heap)[2]

    def peek(self):
        """Return the next order without removing it."""
        if not self._heap:
            return None
        return self._heap[0][2]

    def get_all(self):
        """Return pending orders in the order they will be processed."""
        return [entry[2] for entry in sorted(self._heap)]

    def is_empty(self):
        return not self._heap

    def __len__(self):
        return len(self._heap)
