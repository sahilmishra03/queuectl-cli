def test_enqueue_and_dequeue(queue):
    assert queue.size() == 0
    queue.enqueue("job-1")
    assert queue.size() == 1
    dequeued = queue.dequeue()
    assert dequeued == "job-1"
    assert queue.size() == 0


def test_dequeue_empty_queue(queue):
    assert queue.dequeue() is None


def test_priority_order(queue):
    queue.enqueue("job-low", priority=1)
    queue.enqueue("job-high", priority=10)
    queue.enqueue("job-med", priority=5)

    assert queue.size() == 3

    # Highest priority should come out first
    assert queue.dequeue() == "job-high"
    assert queue.dequeue() == "job-med"
    assert queue.dequeue() == "job-low"
    assert queue.size() == 0
