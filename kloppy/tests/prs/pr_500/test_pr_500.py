"""
Test for PR 500: Fix for Stats Perform pass receiver detection.

This test verifies that event ID '2328592303' correctly identifies
receiver player ID 'aksjicf4keobpav3tuujngell'.
"""

from pathlib import Path

import pytest

from kloppy import statsperform
from kloppy.domain import EventDataset


@pytest.fixture(scope="module")
def pr_500_metadata_xml() -> Path:
    return Path(__file__).parent / "pr_500_ma1.xml"


@pytest.fixture(scope="module")
def pr_500_event_data_xml() -> Path:
    return Path(__file__).parent / "pr_500_ma3.xml"


@pytest.fixture(scope="module")
def pr_500_event_dataset(
    pr_500_metadata_xml: Path, pr_500_event_data_xml: Path
) -> EventDataset:
    return statsperform.load_event(
        ma1_data=pr_500_metadata_xml,
        ma3_data=pr_500_event_data_xml,
        coordinates="opta",
    )


class TestPR500PassReceiverFix:
    """Test for PR 500: Stats Perform pass receiver detection fix."""

    def test_pass_receiver_identification(
        self, pr_500_event_dataset: EventDataset
    ):
        """Test that event ID '2328592303' correctly identifies receiver player ID 'aksjicf4keobpav3tuujngell'."""

        # Get the specific pass event
        pass_event = pr_500_event_dataset.get_event_by_id("2328592303")

        # Verify it's a pass event
        assert (
            pass_event is not None
        ), "Event 2328592303 should exist in dataset"
        assert (
            pass_event.event_type.value == "PASS"
        ), f"Event should be a pass, got {pass_event.event_type.value}"

        # Verify the passer
        assert (
            pass_event.player.player_id == "2nrmndj0uq3f46c2cb1fbf85"
        ), "Incorrect passer player ID"
        assert (
            pass_event.player.full_name == "M. Heyer"
        ), "Incorrect passer name"

        # Verify the receiver - this is the main test for the fix
        assert (
            pass_event.receiver_player is not None
        ), "Pass should have a receiver player"
        assert (
            pass_event.receiver_player.player_id == "aksjicf4keobpav3tuujngell"
        ), f"Expected receiver player ID 'aksjicf4keobpav3tuujngell', got '{pass_event.receiver_player.player_id}'"
        assert (
            pass_event.receiver_player.full_name == "M. Wintzheimer"
        ), "Incorrect receiver name"

        # Verify the receive timestamp is set
        assert (
            pass_event.receive_timestamp is not None
        ), "Pass should have a receive timestamp"

        # Verify the next event is the ball reception by the correct player
        next_event = pass_event.next_record
        assert (
            next_event is not None
        ), "There should be a next event after the pass"
        assert (
            next_event.player.player_id == "aksjicf4keobpav3tuujngell"
        ), "Next event should be by the receiver player"
