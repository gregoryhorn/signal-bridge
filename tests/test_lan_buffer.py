from sb_lan import FeedBuffer


def test_feed_buffer_maxlen_and_seq():
    buf = FeedBuffer(maxlen=3)
    for i in range(5):
        buf.append({"id": str(i)})
    snap = buf.snapshot()
    assert len(snap) == 3
    assert snap[0]["id"] == "2"
    assert buf.seq == 5
