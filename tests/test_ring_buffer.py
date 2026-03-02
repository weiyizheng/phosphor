import numpy as np

from phosphor.ring_buffer import RingBuffer


def test_write_and_read():
    buf = RingBuffer(capacity=1024, channels=2)
    data = np.ones((512, 2), dtype=np.float32)
    buf.write(data)
    out = buf.read(512)
    assert out.shape == (512, 2)
    np.testing.assert_array_equal(out, data)


def test_read_returns_zeros_when_empty():
    buf = RingBuffer(capacity=1024, channels=2)
    out = buf.read(256)
    assert out.shape == (256, 2)
    np.testing.assert_array_equal(out, 0)


def test_overwrites_oldest_on_overflow():
    buf = RingBuffer(capacity=4, channels=1)
    buf.write(np.array([[1.0], [2.0], [3.0], [4.0]], dtype=np.float32))
    buf.write(np.array([[5.0]], dtype=np.float32))
    out = buf.read(4)
    assert 1.0 not in out[:, 0]


def test_write_pos_stays_bounded_after_large_write():
    buf = RingBuffer(capacity=8, channels=1)
    big = np.arange(1000, dtype=np.float32).reshape(-1, 1)
    buf.write(big)
    assert buf._write_pos == 0
