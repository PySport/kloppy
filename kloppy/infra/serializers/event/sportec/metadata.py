from datetime import datetime, timedelta
from typing import NamedTuple, Optional

from lxml import objectify

from kloppy.domain import (
    FormationType,
    Ground,
    Official,
    OfficialType,
    Period,
    Player,
    PositionType,
    Score,
    Team,
)
from kloppy.exceptions import DeserializationError

# --- Constants ---

SPORTEC_FPS = 25
SPORTEC_START_FRAMES = {
    1: 10_000,
    2: 100_000,
    3: 200_000,
    4: 250_000,
}

# --- Mappings ---

POSITION_TYPES_MAPPING: dict[str, PositionType] = {
    "TW": PositionType.Goalkeeper,
    "IVR": PositionType.RightCenterBack,
    "IVL": PositionType.LeftCenterBack,
    "STR": PositionType.Striker,
    "STL": PositionType.LeftForward,
    "STZ": PositionType.Striker,
    "ZO": PositionType.CenterAttackingMidfield,
    "LV": PositionType.LeftBack,
    "RV": PositionType.RightBack,
    "DMR": PositionType.RightDefensiveMidfield,
    "DRM": PositionType.RightDefensiveMidfield,
    "DML": PositionType.LeftDefensiveMidfield,
    "DLM": PositionType.LeftDefensiveMidfield,
    "ORM": PositionType.RightMidfield,
    "OLM": PositionType.LeftMidfield,
    "RA": PositionType.RightWing,
    "LA": PositionType.LeftWing,
}

REFEREE_TYPES_MAPPING: dict[str, OfficialType] = {
    "referee": OfficialType.MainReferee,
    "firstAssistant": OfficialType.AssistantReferee,
    "videoReferee": OfficialType.VideoAssistantReferee,
    "videoRefereeAssistant": OfficialType.AssistantVideoAssistantReferee,
    "secondAssistant": OfficialType.AssistantReferee,
    "fourthOfficial": OfficialType.FourthOfficial,
}


# --- Models ---


class SportecMetadata(NamedTuple):
    game_id: str
    date: datetime
    score: Score
    teams: list[Team]
    periods: list[Period]
    x_max: float
    y_max: float
    fps: int
    officials: list[Official]
    game_week: Optional[int] = None


# --- Parsing Functions ---


def _extract_team_and_players(team_elm) -> Team:
    """Extracts a Team object and its Players from the XML element."""
    # Parse Coach Name
    head_coach = next(
        (
            trainer.attrib.get("Shortname")
            or f"{trainer.attrib.get('FirstName')} {trainer.attrib.get('LastName')}"
            for trainer in team_elm.TrainerStaff.iterchildren("Trainer")
            if trainer.attrib["Role"] == "headcoach"
        ),
        None,
    )

    # Parse Formation
    formation_str = team_elm.attrib.get("LineUp", "").split()[0]

    team = Team(
        team_id=team_elm.attrib["TeamId"],
        name=team_elm.attrib["TeamName"],
        ground=Ground.HOME
        if team_elm.attrib["Role"] == "home"
        else Ground.AWAY,
        coach=head_coach,
        starting_formation=(
            FormationType(formation_str)
            if formation_str
            else FormationType.UNKNOWN
        ),
    )

    team.players = [
        Player(
            player_id=p.attrib["PersonId"],
            team=team,
            jersey_no=int(p.attrib["ShirtNumber"]),
            name=(
                p.attrib.get("Shortname")
                or f"{p.attrib.get('FirstName')} {p.attrib.get('LastName')}"
            ),
            first_name=p.attrib["FirstName"],
            last_name=p.attrib["LastName"],
            starting_position=POSITION_TYPES_MAPPING.get(
                p.attrib.get("PlayingPosition"), PositionType.Unknown
            )
            if p.attrib["Starting"] == "true"
            else None,
            starting=p.attrib["Starting"] == "true",
        )
        for p in team_elm.Players.iterchildren("Player")
    ]
    return team


def load_metadata(match_root: objectify.ObjectifiedElement) -> SportecMetadata:
    """Parses the MatchInformation XML root into SportecMetadata."""

    # 1. Pitch Dimensions
    x_max = float(match_root.MatchInformation.Environment.attrib["PitchX"])
    y_max = float(match_root.MatchInformation.Environment.attrib["PitchY"])

    # 2. Teams & Players
    team_path = objectify.ObjectPath("PutDataRequest.MatchInformation.Teams")
    team_elms = list(team_path.find(match_root).iterchildren("Team"))

    teams = []
    for role in ["home", "guest"]:
        team_node = next(
            (t for t in team_elms if t.attrib["Role"] == role), None
        )
        if team_node is None:
            raise DeserializationError(f"Missing {role} team in metadata")
        teams.append(_extract_team_and_players(team_node))

    # 3. Score
    h_score, a_score = match_root.MatchInformation.General.attrib[
        "Result"
    ].split(":")

    # 4. Periods
    other_info = match_root.MatchInformation.OtherGameInformation.attrib

    def create_period(pid: int, duration_key: str):
        if duration_key not in other_info:
            return None
        start_sec = SPORTEC_START_FRAMES[pid] / SPORTEC_FPS
        duration_sec = float(other_info[duration_key]) / 1000
        return Period(
            id=pid,
            start_timestamp=timedelta(seconds=start_sec),
            end_timestamp=timedelta(seconds=start_sec + duration_sec),
        )

    periods = [
        create_period(1, "TotalTimeFirstHalf"),
        create_period(2, "TotalTimeSecondHalf"),
        create_period(3, "TotalTimeFirstHalfExtra"),
        create_period(4, "TotalTimeSecondHalfExtra"),
    ]
    periods = [p for p in periods if p is not None]

    # 5. Officials
    officials = []
    if hasattr(match_root.MatchInformation, "Referees"):
        ref_path = objectify.ObjectPath(
            "PutDataRequest.MatchInformation.Referees"
        )
        for ref in ref_path.find(match_root).iterchildren("Referee"):
            officials.append(
                Official(
                    official_id=ref.attrib["PersonId"],
                    name=ref.attrib["Shortname"],
                    first_name=ref.attrib["FirstName"],
                    last_name=ref.attrib["LastName"],
                    role=REFEREE_TYPES_MAPPING.get(
                        ref.attrib["Role"], OfficialType.Unknown
                    ),
                )
            )

    # 6. Match date
    game_id = match_root.MatchInformation.General.attrib["MatchId"]
    date = datetime.fromisoformat(
        match_root.MatchInformation.General.attrib["KickoffTime"]
    )
    game_week = match_root.MatchInformation.General.attrib.get("MatchDay", None)

    return SportecMetadata(
        game_id=game_id,
        date=date,
        game_week=game_week,
        score=Score(home=int(h_score), away=int(a_score)),
        teams=teams,
        periods=periods,
        x_max=x_max,
        y_max=y_max,
        fps=SPORTEC_FPS,
        officials=officials,
    )
