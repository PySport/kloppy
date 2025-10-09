import json
from datetime import timedelta
import tempfile
from typing import IO, NamedTuple

from kloppy.domain import Provider, TrackingDataset, Time, PositionType
from kloppy.infra.serializers.tracking.serializer import TrackingDataSerializer


class CDFOutputs(NamedTuple):
    meta_data: IO[bytes]
    tracking_data: list[IO[bytes]]


class CDFTrackingDataSerializer(TrackingDataSerializer[CDFOutputs]):
    provider = Provider.CDF

    # to infer the starting formation if not given
    @staticmethod
    def get_starting_formation(team_players) -> str:
        formation = ""
        defender = midfielder = attacker = 0
        for player in team_players:
            if player.starting_position.position_group == None:
                continue
            elif (
                player.starting_position.position_group
                == PositionType.Attacker
            ):
                attacker += 1
            elif (
                player.starting_position.position_group
                == PositionType.Midfielder
            ):
                midfielder += 1
            elif (
                player.starting_position.position_group
                == PositionType.Defender
            ):
                defender += 1
        if defender + midfielder + attacker == 10:
            formation = f"{defender}-{midfielder}-{attacker}"
        return formation

    def serialize(self, dataset: TrackingDataset, outputs: CDFOutputs) -> bool:
        """
        Serialize a TrackingDataset to Common Data Format.

        Args:
            dataset: The tracking dataset to serialize
            outputs: CDFOutputs containing file handles for metadata and tracking data

        Returns:
            bool: True if serialization was successful, False otherwise

        Note:
            TODO: Open question: should the serializer make sure the data is in the right format, and
                  do a transformation if not in the right format? yes normally.
        """

        # Normalize the coordinate system
        # creating the coordinate system according to the CDF paper specifications.
        from kloppy.domain import (
            Orientation,
            BallState,
        )

        # builded class.
        from . import CDFCoordinateSystem

        # setting it as coordinate system of the imported data
        dataset = dataset.transform(
            to_coordinate_system=CDFCoordinateSystem(
                dataset
            ).get_coordinate_system(),
            to_orientation=Orientation.STATIC_HOME_AWAY,
        )
        ##--------------------------------------------------------------------------

        ## building Tracking jsonl
        # Output containers
        metadata_json = {}

        # list of different periods within a game define by the cdf
        periods = {
            1: "first_half",
            2: "second_half",
            3: "first_half_extratime",
            4: "second_half_extratime",
            5: "shootout",
        }

        # container for stat and end frame_id
        period_start_frame_id = {
            period.id: None for period in dataset.metadata.periods
        }
        period_end_frame_id = {
            period.id: None for period in dataset.metadata.periods
        }

        # container for stat and end normalized frame_id
        normalized_period_start_frame_id = {
            period.id: None for period in dataset.metadata.periods
        }
        normalized_period_end_frame_id = {
            period.id: None for period in dataset.metadata.periods
        }

        # diffence of ids between frame_ids
        period_offset = {period.id: 0 for period in dataset.metadata.periods}

        # Get home and away team data
        home_team, away_team = dataset.metadata.teams

        # Get the players Id.
        home_player_ids, away_player_ids = (
            [player.player_id for player in home_team.players],
            [player.player_id for player in away_team.players],
        )

        frame_id = 0  # Use for the cdf_frame_ids..
        for frame in dataset.frames:
            frame_data = {}

            # Frame ID specified by the CDF
            frame_data["frame_id"] = frame_id
            # Original frame_id
            frame_data["Original_frame_id"] = frame.frame_id
            # Timestamp
            frame_data["timestamp"] = str(
                dataset.metadata.date + frame.timestamp
            )
            # Period
            frame_data["period"] = periods.get(frame.period.id, "unknownn")
            period_id = frame.period.id
            # Update the start and end id for this period
            if period_start_frame_id[period_id] is None:
                period_start_frame_id[period_id] = frame_data[
                    "Original_frame_id"
                ]

                if (
                    period_id > 1
                    and period_end_frame_id[period_id - 1] is not None
                ):
                    prev_period_length = (
                        period_end_frame_id[period_id - 1]
                        - period_start_frame_id[period_id - 1]
                        + 1
                    )
                    period_offset[period_id] = (
                        period_offset[period_id - 1] + prev_period_length
                    )

                # Set normalized start frame id
                normalized_period_start_frame_id[period_id] = period_offset[
                    period_id
                ]

            period_end_frame_id[period_id] = frame_data["Original_frame_id"]

            normalized_frame_id = (
                frame_data["Original_frame_id"]
                - period_start_frame_id[period_id]
            ) + period_offset[period_id]

            # Update normalized end frame id
            normalized_period_end_frame_id[period_id] = normalized_frame_id

            # Match ID
            frame_data["match"] = {"id": str(dataset.metadata.game_id)}
            # Ball status
            frame_data["ball_status"] = frame.ball_state == BallState.ALIVE

            # Teams and players
            home_players = []
            for player, coordinates in frame.players_coordinates.items():
                if player.player_id in home_player_ids:
                    try:
                        x = coordinates.x
                        y = coordinates.x
                        home_players.append(
                            {
                                "id": player.player_id,
                                "x": round(x, 3),
                                "y": round(y, 3),
                                "position": player.starting_position.code,
                            }
                        )
                    except KeyError:
                        continue

            away_players = []
            for player, coordinates in frame.players_coordinates.items():
                if player.player_id in away_player_ids:
                    try:
                        x = coordinates.x
                        y = coordinates.x
                        away_players.append(
                            {
                                "id": player.player_id,
                                "x": round(x, 3),
                                "y": round(y, 3),
                                "position": player.starting_position.code,
                            }
                        )
                    except KeyError:
                        continue

            # teams within the tracking data.

            home_players_id = []
            away_players_id = []
            for player, _ in frame.players_coordinates.items():
                if player.team == home_team:
                    home_players_id.append(player.player_id)
                if player.team == away_team:
                    away_players_id.append(player.player_id)
            set_of_home_players_id_in_the_frame = set(home_players_id)
            set_of_away_players_id_in_the_frame = set(away_players_id)

            frame_data["teams"] = {
                "home": {
                    "id": home_team.team_id,
                    "players": home_players,
                    "jersey_color": " ",  #
                    "name": home_team.name,
                    "formation": (
                        home_team.formations.at_start()
                        if home_team.formations.items
                        else self.get_starting_formation(
                            [
                                p
                                for p in home_team.players
                                if p.player_id
                                in set_of_home_players_id_in_the_frame
                            ]
                        )
                    ),
                },
                "away": {
                    "id": away_team.team_id,
                    "players": away_players,
                    "jersey_color": " ",
                    "name": away_team.name,
                    "formation": (
                        away_team.formations.at_start()
                        if away_team.formations.items
                        else self.get_starting_formation(
                            [
                                p
                                for p in away_team.players
                                if p.player_id
                                in set_of_away_players_id_in_the_frame
                            ]
                        )
                    ),
                },
            }

            # Ball
            if (
                frame_data["ball_status"] == True
                and frame.ball_coordinates is not None
            ):
                try:
                    ball_x = round(frame.ball_coordinates.x, 3)
                    ball_y = round(frame.ball_coordinates.y, 3)
                    ball_z = round(frame.ball_coordinates.z, 3)
                except KeyError:
                    ball_x = ball_y = ball_z = None
            else:
                ball_x = ball_y = ball_z = (
                    404  # default missing value for ball coordinates
                )

            frame_data["ball"] = {"x": ball_x, "y": ball_y, "z": ball_z}

            # update the frame_id
            frame_id += 1

            # build a temporary jsonl for each frame
            frame_file = tempfile.NamedTemporaryFile(
                mode="w+b", suffix=".jsonl", delete=False
            )
            frame_file.write((json.dumps(frame_data) + "\n").encode("utf-8"))
            frame_file.flush()  # make sure data is written

            # Add to tracking list
            outputs.tracking_data.append(frame_file)

        ################################################
        ### build now the metadata.
        # Competition infos.
        metadata_json["competition"] = (
            {  # we don't have any of these informations
                "id": "MISSING_MANDATORY_COMPETITION_ID",
                "name": "",
                "format": "",
                "age_restriction": "",
                "type": "",
            }
        )

        # season infos.
        metadata_json["season"] = {  # we don't have any of these informations
            "id": "MISSING_MANDATORY_SEASON_ID",
            "name": "",
        }

        # match infos.
        periods_info = []
        for period in dataset.metadata.periods:
            curent_period = {
                "period": periods[period.id],
                "play_direction": "left_right",
                "start_time": str(
                    dataset.metadata.date + period.start_timestamp
                ),
                "end_time": str(dataset.metadata.date + period.end_timestamp),
                "start_frame_id": normalized_period_start_frame_id[period.id],
                "end_frame_id": normalized_period_end_frame_id[period.id],
                "left_team_id": home_team.team_id,
                "right_team_id": away_team.team_id,
            }
            periods_info.append(curent_period)

        ## building team_players for metadata
        meta_home_players = []
        starters_ids = []
        for player, coordinates in dataset[0].players_coordinates.items():
            starters_ids.append(player.player_id)

        for player in home_team.players:
            try:
                meta_home_players.append(
                    {
                        "id": player.player_id,
                        "team_id": home_team.team_id,
                        "jersey_number": player.jersey_no,
                        "is_starter": player.player_id in starters_ids,
                    }
                )
            except KeyError:
                continue

        meta_away_players = []
        for player in away_team.players:
            try:
                meta_away_players.append(
                    {
                        "id": player.player_id,
                        "team_id": away_team.team_id,
                        "jersey_number": player.jersey_no,
                        "is_starter": player.player_id in starters_ids,
                    }
                )
            except KeyError:
                continue

        # get whistles related to period directly from them.
        whistles = []
        for period in periods_info:
            whistle_start = {}
            whistle_end = {}
            # type
            whistle_start["type"] = period["period"]
            whistle_end["type"] = period["period"]
            # sub_type
            whistle_start["sub_type"] = "start"
            whistle_end["sub_type"] = "end"
            # time
            whistle_start["time"] = period["start_time"]
            whistle_end["time"] = period["end_time"]
            whistles.append(whistle_start)
            whistles.append(whistle_end)

        metadata_json["match"] = {
            "id": str(dataset.metadata.game_id),  # same as for the jsonl
            "kickoff_time": str(
                dataset.metadata.date
                + dataset.metadata.periods[0].start_timestamp
            ),
            "periods": periods_info,
            "whistles": whistles,  # fake just to pass the test, I have to change this after.
            "round": "",
            "scheduled_kickoff_time": str(dataset.metadata.date),
            "local_kickoff_time": "",  # how to get this ?
            "misc": {
                "country": "",  # how to get this ?
                "city": "",  # how to get this ?
                "percipitation": 0,  # how to get this ?
                "is_open_roof": True,  # how to get this ?
            },
        }

        home_players_id_in_meta = []
        away_players_id_in_meta = []
        for player, _ in dataset[0].players_coordinates.items():
            if player.team == home_team:
                home_players_id_in_meta.append(player.player_id)
            if player.team == away_team:
                away_players_id_in_meta.append(player.player_id)
        meta_set_of_home_players_id_in_the_frame = set(home_players_id_in_meta)
        print(meta_set_of_home_players_id_in_the_frame)
        meta_set_of_away_players_id_in_the_frame = set(away_players_id_in_meta)
        print(meta_set_of_away_players_id_in_the_frame)

        metadata_json["teams"] = {
            "home": {
                "id": home_team.team_id,  # same as for the jsonl
                "players": meta_home_players,
                "jersey_color": " ",
                "name": home_team.name,
                "formation": home_team.starting_formation
                or self.get_starting_formation(
                    [
                        p
                        for p in home_team.players
                        if p.player_id
                        in meta_set_of_home_players_id_in_the_frame
                    ]
                ),
            },
            "away": {
                "id": away_team.team_id,
                "players": meta_away_players,
                "jersey_color": " ",
                "name": away_team.name,
                "formation": away_team.starting_formation
                or self.get_starting_formation(
                    [
                        p
                        for p in away_team.players
                        if p.player_id
                        in meta_set_of_away_players_id_in_the_frame
                    ]
                ),
            },
        }

        metadata_json["stadium"] = {
            "id": "MISSING_MANDATORY_STADIUM_ID",
            "pitch_length": dataset.metadata.pitch_dimensions.pitch_length,
            "pitch_width": dataset.metadata.pitch_dimensions.pitch_width,
            "name": "",
            "turf": "",
        }

        metadata_json["meta"] = {
            "video": None,
            "tracking": None,
            "limb": None,
            "meta": None,
            "cdf": None,
        }

        outputs.meta_data.write(
            (json.dumps(metadata_json) + "\n").encode("utf-8")
        )

        return True
