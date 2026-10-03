from io import BytesIO
from pathlib import Path

from kloppy import skillcorner, wyscout


class NonSeekableStream:
    def __init__(self, data: bytes):
        self._data = BytesIO(data)

    def read(self, *args, **kwargs):
        return self._data.read(*args, **kwargs)

    def readinto(self, *args, **kwargs):
        return self._data.readinto(*args, **kwargs)

    def seekable(self):
        return False

    def readable(self):
        return True


def test_wyscout_non_seekable(base_dir: Path):
    event_v2_data = base_dir / "files" / "wyscout_events_v2.json"
    with open(event_v2_data, "rb") as f:
        data = f.read()

    stream = NonSeekableStream(data)
    # This should not raise an error and successfully load
    dataset = wyscout.load(event_data=stream, coordinates="wyscout")
    assert len(dataset.records) > 0


def test_skillcorner_non_seekable(base_dir: Path):
    meta_data = base_dir / "files" / "skillcorner_match_data.json"
    raw_data = base_dir / "files" / "skillcorner_structured_data.json"

    with open(meta_data, "rb") as f:
        meta = f.read()

    with open(raw_data, "rb") as f:
        raw = f.read()

    meta_stream = NonSeekableStream(meta)
    raw_stream = NonSeekableStream(raw)

    dataset = skillcorner.load(
        meta_data=meta_stream,
        raw_data=raw_stream,
        coordinates="skillcorner",
    )
    assert len(dataset.records) > 0
