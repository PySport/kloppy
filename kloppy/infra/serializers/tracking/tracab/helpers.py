import logging
import warnings
import json
import html
from datetime import timedelta, timezone
from typing import Dict
from dateutil.parser import parse

from lxml import objectify

from kloppy.domain import (
    Team,
    Period,
    Orientation,
    Ground,
    Player,
)
from kloppy.domain.models import PositionType
from kloppy.exceptions import DeserializationError

from kloppy.utils import performance_logging
from .common import position_types_mapping


logger = logging.getLogger(__name__)


def load_meta_data_json(meta_data):
    meta_data = json.load(meta_data)

    def __create_team(team_data, ground):
        team = Team(
            team_id=str(team_data["TeamID"]),
            name=html.unescape(team_data["ShortName"]),
            ground=ground,
        )

        team.players = [
            Player(
                player_id=str(player["PlayerID"]),
                team=team,
                first_name=html.unescape(player["FirstName"]),
                last_name=html.unescape(player["LastName"]),
                name=html.unescape(
                    player["FirstName"] + " " + player["LastName"]
                ),
                jersey_no=int(player["JerseyNo"]),
                starting=True if player["StartingPosition"] != "S" else False,
                starting_position=position_types_mapping.get(
                    player["StartingPosition"], PositionType.Unknown
                ),
            )
            for player in team_data["Players"]
        ]

        return team

    with performance_logging("Loading metadata", logger=logger):
        frame_rate = meta_data["FrameRate"]
        pitch_size_width = meta_data["PitchShortSide"] / 100
        pitch_size_length = meta_data["PitchLongSide"] / 100

        periods = []
        for period_id in (1, 2, 3, 4):
            period_start_frame = meta_data[f"Phase{period_id}StartFrame"]
            period_end_frame = meta_data[f"Phase{period_id}EndFrame"]
            if period_start_frame != 0 or period_end_frame != 0:
                periods.append(
                    Period(
                        id=period_id,
                        start_timestamp=timedelta(
                            seconds=period_start_frame / frame_rate
                        ),
                        end_timestamp=timedelta(
                            seconds=period_end_frame / frame_rate
                        ),
                    )
                )

        home_team = __create_team(meta_data["HomeTeam"], Ground.HOME)
        away_team = __create_team(meta_data["AwayTeam"], Ground.AWAY)
        teams = [home_team, away_team]

    date = meta_data.get("Kickoff", None)
    if date is not None:
        date = parse(date).astimezone(timezone.utc)
    game_id = meta_data.get("GameID", None)

    return (
        pitch_size_length,
        pitch_size_width,
        teams,
        periods,
        frame_rate,
        date,
        game_id,
    )


def load_meta_data_xml(meta_data):
    def __create_team(
        team_data, ground, start_frame_id, id_suffix="Id", player_item="Player"
    ):
        team = Team(
            team_id=str(team_data[f"Team{id_suffix}"]),
            name=html.unescape(team_data["ShortName"]),
            ground=ground,
        )

        team.players = [
            Player(
                player_id=str(player[f"Player{id_suffix}"]),
                team=team,
                first_name=html.unescape(player["FirstName"]),
                last_name=html.unescape(player["LastName"]),
                name=html.unescape(
                    player["FirstName"] + " " + player["LastName"]
                ),
                jersey_no=int(player["JerseyNo"]),
                starting=player["StartFrameCount"] == start_frame_id,
                starting_position=position_types_mapping.get(
                    player.get("StartingPosition"), PositionType.Unknown
                ),
            )
            for player in team_data["Players"][player_item]
        ]

        return team

    with performance_logging("Loading metadata", logger=logger):
        meta_data = objectify.fromstring(meta_data.read())

        periods = []

        if hasattr(meta_data, "match"):
            id_suffix = "Id"
            player_item = "Player"

            match = meta_data.match
            frame_rate = int(match.attrib["iFrameRateFps"])
            pitch_size_width = float(
                match.attrib["fPitchXSizeMeters"].replace(",", ".")
            )
            pitch_size_height = float(
                match.attrib["fPitchYSizeMeters"].replace(",", ".")
            )
            date = parse(meta_data.match.attrib["dtDate"]).replace(
                tzinfo=timezone.utc
            )
            game_id = meta_data.match.attrib["iId"]

            for period in match.iterchildren(tag="period"):
                start_frame_id = int(period.attrib["iStartFrame"])
                end_frame_id = int(period.attrib["iEndFrame"])
                if start_frame_id != 0 or end_frame_id != 0:
                    periods.append(
                        Period(
                            id=int(period.attrib["iId"]),
                            start_timestamp=timedelta(
                                seconds=start_frame_id / frame_rate
                            ),
                            end_timestamp=timedelta(
                                seconds=end_frame_id / frame_rate
                            ),
                        )
                    )
        elif hasattr(meta_data, "Phase1StartFrame"):
            date = parse(str(meta_data["Kickoff"]))
            game_id = str(meta_data["GameID"])
            id_suffix = "ID"
            player_item = "item"

            frame_rate = int(meta_data["FrameRate"])
            pitch_size_width = float(meta_data["PitchLongSide"]) / 100
            pitch_size_height = float(meta_data["PitchShortSide"]) / 100
            for i in [1, 2, 3, 4, 5]:
                start_frame_id = int(meta_data[f"Phase{i}StartFrame"])
                end_frame_id = int(meta_data[f"Phase{i}EndFrame"])
                if start_frame_id != 0 or end_frame_id != 0:
                    periods.append(
                        Period(
                            id=i,
                            start_timestamp=timedelta(
                                seconds=start_frame_id / frame_rate
                            ),
                            end_timestamp=timedelta(
                                seconds=end_frame_id / frame_rate
                            ),
                        )
                    )

            orientation = (
                Orientation.HOME_AWAY
                if bool(meta_data["Phase1HomeGKLeft"])
                else Orientation.AWAY_HOME
            )
        else:
            raise NotImplementedError(
                """This 'meta_data' format is currently not supported..."""
            )

        if hasattr(meta_data, "HomeTeam") and hasattr(meta_data, "AwayTeam"):
            home_team = __create_team(
                meta_data["HomeTeam"],
                Ground.HOME,
                start_frame_id=start_frame_id,
                id_suffix=id_suffix,
                player_item=player_item,
            )
            away_team = __create_team(
                meta_data["AwayTeam"],
                Ground.AWAY,
                start_frame_id=start_frame_id,
                id_suffix=id_suffix,
                player_item=player_item,
            )
        else:
            home_team = Team(team_id="home", name="home", ground=Ground.HOME)
            away_team = Team(team_id="away", name="away", ground=Ground.AWAY)
        teams = [home_team, away_team]
        return (
            pitch_size_height,
            pitch_size_width,
            teams,
            periods,
            frame_rate,
            date,
            game_id,
        )


def load_meta_data(meta_data_extension, meta_data):
    if meta_data_extension == ".xml":
        return load_meta_data_xml(meta_data)
    elif meta_data_extension == ".json":
        return load_meta_data_json(meta_data)
    else:
        raise ValueError(
            "Tracab meta data file format could not be recognized, it should be either .xml or .json"
        )
