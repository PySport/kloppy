from kloppy.exceptions import DeserializationError

from .deserializer_v3 import WyscoutDeserializerV3
from .wyscout_periods import parse_period_id


def _parse_starting_formation(
    raw_events, wyId: str
) -> tuple[str, dict[str, str]]:
    """Return the starting scheme and the position code of each starting player.

    In v4, formations are grouped by "home" / "away". Each formation can span
    multiple periods. "matchPeriodStart" can be null when the tagged video is
    no longer available.
    """
    team_formations = [
        formation
        for side in ("home", "away")
        for formation in raw_events["formations"].get(side, [])
        if str(formation["teamId"]) == wyId
    ]
    if not team_formations:
        raise DeserializationError(f"No formations found for team {wyId}")

    first_formation = min(
        team_formations,
        key=lambda formation: (
            parse_period_id(formation["matchPeriodStart"])
            if formation["matchPeriodStart"]
            else float("inf"),
            formation["startSec"],
        ),
    )

    starting_positions = {
        str(player["playerId"]): player["position"]
        for player in first_formation["players"]
    }
    return first_formation["scheme"], starting_positions


class WyscoutDeserializerV4(WyscoutDeserializerV3):
    """Deserializer for Wyscout API v4 event data.

    The v4 events have the same structure as v3. Only the "formations" object
    has a new shape.
    """

    @staticmethod
    def _parse_starting_formation(
        raw_events, wyId: str
    ) -> tuple[str, dict[str, str]]:
        return _parse_starting_formation(raw_events, wyId)
