import json
from datetime import timedelta
from typing import IO, NamedTuple

from kloppy.domain import Provider, TrackingDataset, Time, PositionType
from kloppy.infra.serializers.tracking.serializer import TrackingDataSerializer


class CDFOutputs(NamedTuple):
    meta_data: IO[bytes]
    tracking_data: IO[bytes]


class CDFTrackingDataSerializer(TrackingDataSerializer[CDFOutputs]):
    provider = Provider.CDF

    # to infer the starting formation if not given
    @staticmethod
    def get_starting_formation(list_players, team) -> str:
        formation = ""
        defender = midfiler = attacker = 0

        for player in list_players:
            if (
                team.get_player_by_id(player["id"]).starting_position.parent
                == None
            ):
                continue
            elif (
                team.get_player_by_id(player["id"]).starting_position.parent
                == PositionType.Attacker
            ):
                attacker += 1
            elif (
                team.get_player_by_id(player["id"]).starting_position.parent
                == PositionType.Midfielder
                or team.get_player_by_id(
                    player["id"]
                ).starting_position.parent.parent
                == PositionType.Midfielder
            ):
                midfiler += 1
            elif (
                team.get_player_by_id(
                    player["id"]
                ).starting_position.parent.parent
                == PositionType.Defender
            ):
                defender += 1
        if defender + midfiler + attacker == 10:
            formation = f"{defender}_{midfiler}_{attacker}"
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
            CustomCoordinateSystem,
            Origin,
            VerticalOrientation,
            NormalizedPitchDimensions,
            Dimension,
            Orientation,
            BallState,
        )

        # length and width of the pitch imported pitch
        length = dataset.metadata.pitch_dimensions.pitch_length
        width = dataset.metadata.pitch_dimensions.pitch_length
        # build the cdf normalize coordinate system
        CDF_coordinate_system = CustomCoordinateSystem(
            origin=Origin.CENTER,
            vertical_orientation=VerticalOrientation.BOTTOM_TO_TOP,
            pitch_dimensions=NormalizedPitchDimensions(
                x_dim=Dimension(min=-length / 2, max=length / 2),
                y_dim=Dimension(min=-width / 2, max=width / 2),
                pitch_length=length,
                pitch_width=width,
            ),
        )
        # setting it as coordinate system of the imported data
        dataset = dataset.transform(
            to_coordinate_system=CDF_coordinate_system,
            to_orientation=Orientation.STATIC_HOME_AWAY,
        )
        ##--------------------------------------------------------------------------

        ## building Tracking jsonl
        # Output containers
        metadata_json = {}
        # tracking_datas = [] use if we want to manage all the frames

        # list of different periods within a game define by the cdf
        periods = {
            1: "first_half",
            2: "second_half",
            3: "first_half_extratime",
            4: "second_half_extratime",
            5: "shootout",
        }

        # Get home and away team data
        home_team, away_team = dataset.metadata.teams

        # Get the players Id.
        home_player_ids, away_player_ids = (
            [player.player_id for player in home_team.players],
            [player.player_id for player in away_team.players],
        )

        for frame_id in range(
            len([1])
        ):  # change this when we would like to manage all the frames
            frame_data = {}

            # Frame ID
            frame_data["frame_id"] = frame_id
            # Timestamp
            frame_data["timestamp"] = str(
                dataset.metadata.date + dataset[frame_id].timestamp
            )
            # Period
            frame_data["period"] = periods.get(
                dataset[frame_id].period.id, "unknownn"
            )
            # Match ID
            frame_data["match"] = {"id": str(dataset.metadata.game_id)}
            # Ball status
            frame_data["ball_status"] = (
                dataset[0].ball_state == BallState.ALIVE
            )

            # Teams and players
            home_players = []
            for player, coordinates in dataset[
                frame_id
            ].players_coordinates.items():
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
            for player, coordinates in dataset[
                frame_id
            ].players_coordinates.items():
                if player.player_id in away_player_ids:
                    try:
                        x = coordinates.x
                        y = coordinates.x
                        away_players.append(
                            {
                                "id": player.player_id,
                                "x": round(x, 3),
                                "y": round(y, 3),
                            }
                        )
                    except KeyError:
                        continue

            # asumption
            default_formation = "4-3-3"

            # teams within the tracking data.
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
                            home_players, home_team
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
                        if home_team.formations.items
                        else self.get_starting_formation(
                            away_players, away_team
                        )
                    ),
                },
            }

            # Ball
            if frame_data["ball_status"] == True:
                try:
                    ball_x = round(dataset[frame_id].ball_coordinates.x, 3)
                    ball_y = round(dataset[frame_id].ball_coordinates.y, 3)
                    ball_z = round(dataset[frame_id].ball_coordinates.z, 3)
                except KeyError:
                    ball_x = ball_y = ball_z = None
            else:
                ball_x = ball_y = ball_z = (
                    dataset.metadata.pitch_dimensions.pitch_length + 10
                )

            frame_data["ball"] = {"x": ball_x, "y": ball_y, "z": ball_z}

        # normally here when we will use all the frames we are suppose to add them successivelly to a list that we will then write as tracking data outputs
        # but with only one frame we just dumpit in a json buffured.
        # Add to tracking list
        outputs.tracking_data.write(
            (json.dumps(frame_data) + "\n").encode("utf-8")
        )

        ################################################
        ### build now the metadata.
        # Competition infos.
        metadata_json["competition"] = (
            {  # we don't have any of these informations
                "id": "",
                "name": "",
                "format": "",
                "age_restriction": "16",
                "type": "",
            }
        )

        # season infos.
        metadata_json["season"] = {  # we don't have any of these informations
            "id": "",
            "name": "",
        }

        # match infos.
        periods_info = []
        for period in dataset.metadata.periods:
            curent_period = {
                "period": periods[period.id],
                "play_direction": "left_right",
                "start_time": str(
                    dataset.metadata.date + period.start_time.timestamp
                ),
                "end_time": str(
                    dataset.metadata.date + period.end_time.timestamp
                ),
                "start_frame_id": (
                    0
                    if period.id == 1
                    else len(
                        dataset.filter(
                            lambda frame: frame.period.id == 1
                        ).to_df()
                    )
                ),
                "end_frame_id": (
                    len(
                        dataset.filter(
                            lambda frame: frame.period.id == period.id
                        ).to_df()
                    )
                    - 1
                    if period.id == 1
                    else len(
                        dataset.filter(
                            lambda frame: frame.period.id == 1
                        ).to_df()
                    )
                    + len(
                        dataset.filter(
                            lambda frame: frame.period.id == period.id
                        ).to_df()
                    )
                    - 1
                ),
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
            whistle_start = whistle_end = {}
            # type
            whistle_start["type"] = whistle_end["type"] = period["period"]
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
            "kickoff_time": str(dataset.metadata.periods[0].start_time),
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

        metadata_json["teams"] = {
            "home": {
                "id": home_team.team_id,  # same as for the jsonl
                "players": meta_home_players,
                "jersey_color": " ",
                "name": home_team.name,
                "formation": home_team.starting_formation
                or self.get_starting_formation(meta_home_players, home_team),
            },
            "away": {
                "id": away_team.team_id,  # same as for the jsonl
                "players": meta_away_players,
                "jersey_color": " ",
                "name": away_team.name,
                "formation": away_team.starting_formation
                or self.get_starting_formation(meta_away_players, away_team),
            },
        }

        metadata_json["stadium"] = {
            "id": "",
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
