import unittest

from queue_system import OrderQueue


class OrderQueueTests(unittest.TestCase):
    def test_orders_are_processed_fifo(self):
        queue = OrderQueue()
        queue.enqueue("Order 1")
        queue.enqueue("Order 2")
        queue.enqueue("Order 3")

        self.assertEqual(queue.dequeue(), "Order 1")
        self.assertEqual(queue.dequeue(), "Order 2")
        self.assertEqual(queue.dequeue(), "Order 3")

    def test_empty_queue_returns_none(self):
        queue = OrderQueue()

        self.assertIsNone(queue.dequeue())
        self.assertIsNone(queue.peek())
        self.assertTrue(queue.is_empty())

    def test_peek_does_not_remove_order(self):
        queue = OrderQueue()
        queue.enqueue("Order 1")

        self.assertEqual(queue.peek(), "Order 1")
        self.assertEqual(len(queue), 1)


if __name__ == "__main__":
    unittest.main()
