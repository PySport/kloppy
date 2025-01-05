from kloppy import impect
from kloppy.domain import EventDataset, DatasetType


def test_dataset(base_dir) -> EventDataset:
    """Load Impect data"""
    dataset = impect.load(
        event_data=base_dir / "files" / "impect_events.json",
        lineup_data=base_dir / "files" / "impect_meta.json",
    )
    assert dataset.dataset_type == DatasetType.EVENT
    return dataset
