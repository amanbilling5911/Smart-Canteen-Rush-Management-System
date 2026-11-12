import unittest

from priority_queue import PriorityOrderQueue


class PriorityOrderQueueTests(unittest.TestCase):
    def test_highest_priority_is_processed_first(self):
        queue = PriorityOrderQueue()
        queue.enqueue("Low", 1)
        queue.enqueue("High", 5)
        queue.enqueue("Medium", 3)

        self.assertEqual(queue.dequeue(), "High")
        self.assertEqual(queue.dequeue(), "Medium")
        self.assertEqual(queue.dequeue(), "Low")

    def test_equal_priorities_keep_fifo_order(self):
        queue = PriorityOrderQueue()
        queue.enqueue("First", 4)
        queue.enqueue("Second", 4)
        queue.enqueue("Third", 4)

        self.assertEqual(queue.dequeue(), "First")
        self.assertEqual(queue.dequeue(), "Second")
        self.assertEqual(queue.dequeue(), "Third")

    def test_empty_queue_returns_none(self):
        queue = PriorityOrderQueue()

        self.assertIsNone(queue.dequeue())
        self.assertIsNone(queue.peek())
        self.assertTrue(queue.is_empty())

    def test_priority_must_be_positive(self):
        queue = PriorityOrderQueue()

        with self.assertRaises(ValueError):
            queue.enqueue("Invalid", 0)


if __name__ == "__main__":
    unittest.main()
