from typing import IO, NamedTuple

from kloppy.domain import Provider, TrackingDataset
from kloppy.infra.serializers.tracking.serializer import TrackingDataSerializer


class CDFOutputs(NamedTuple):
    meta_data: IO[bytes]
    tracking_data: IO[bytes]


class CDFTrackingDataSerializer(TrackingDataSerializer[CDFOutputs]):
    provider = Provider.CDF

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
                  do a transformation if not in the right format?
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
            BallState
        )
        # length and width of the pitch
        length = dataset.metadata.pitch_dimensions.pitch_length
        width = dataset.metadata.pitch_dimensions.pitch_length
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

        # Convert the dataset into a DataFrame
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

        for frame_id in range(len([1])):
            frame_data = {}

            # Frame ID
            frame_data["frame_id"] = frame_id
            # Timestamp
            frame_data["timestamp"] = dataset[frame_id].timestamp
            # Period
            frame_data["period"] = periods.get(dataset[frame_id].period, "unknown")
            # Match ID (placeholder)
            frame_data["match"] = {"id": dataset.metadata.game_id}
            # Ball status
            ball_state = dataset[frame_id].ball_state
            frame_data["ball_status"] = dataset[0].ball_state == BallState.ALIVE

            # Teams and players
            home_players = []
            for player, coordinates in dataset[frame_id].players_coordinates.items():
                if player.player_id in home_player_ids:
                    try:
                        x = coordinates.x
                        y = coordinates.x
                        home_players.append(
                            {"id": player.player_id, "x": round(x, 3), "y": round(y, 3)}
                        )
                    except KeyError:
                        continue

            away_players = []
            for player, coordinates in dataset[frame_id].players_coordinates.items():
                if player.player_id in away_player_ids:
                    try:
                        x = coordinates.x
                        y = coordinates.x
                        home_players.append(
                            {"id": player.player_id, "x": round(x, 3), "y": round(y, 3)}
                        )
                    except KeyError:
                        continue

            frame_data["teams"] = {
                "home": {"id": home_team.team_id, "players": home_players},
                "away": {"id": away_team.team_id, "players": away_players},
            }

            # Ball
            if frame_data["ball_status"] == True:
                try:
                    ball_x = round(dataset[0].ball_coordinates.x, 3)
                    ball_y = round(dataset[0].ball_coordinates.y, 3)
                    ball_z = round(dataset[0].ball_coordinates.z, 3)
                except KeyError:
                    ball_x = ball_y = ball_z = None
                frame_data["ball"] = {"x": ball_x, "y": ball_y, "z": ball_z}

            # Add to tracking list
            outputs.tracking_data.write(frame_data)

        ### build now the metadata.

        # Copetition infos.
        metadata_json["competition"] = {  # w don't have any of these informations
            "id": "",
            "name": "",
            "format": "",
            "age_restriction": "null",
            "type": "",
        }

        # season infos.
        metadata_json["season"] = {  # w don't have any of these informations
            "id": "",
            "name": "",
        }

        # match infos.
        periods_info = []
        for period in dataset.metadata.periods:
            curent_period = {
                "period": periods[period.id],
                "play_direction": "left_to_rigth",
                "start_time": dataset.metadata.date + period.start_time.timestamp,
                "end_time": dataset.metadata.date + period.end_time.timestamp,
                "start_frame_id": (
                    0
                    if period.id == 1
                    else len(dataset.filter(lambda frame: frame.period.id == 1).to_df())
                ),
                "end_frame_id": (
                    len(dataset.filter(lambda frame: frame.period.id == period.id).to_df())
                    - 1
                    if period.id == 1
                    else len(dataset.filter(lambda frame: frame.period.id == 1).to_df())
                    + len(
                        dataset.filter(lambda frame: frame.period.id == period.id).to_df()
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
                home_players.append(
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
                away_players.append(
                    {
                        "id": player.player_id,
                        "team_id": away_team.team_id,
                        "jersey_number": player.jersey_no,
                        "is_starter": player.player_id in starters_ids,
                    }
                )
            except KeyError:
                continue

        metadata_json["match"] = {
            "match": {
                "id": dataset.metadata.game_id,  # same as for the jsonl
                "kickoff_time": dataset.metadata.periods[0].start_time,
                "periods": periods_info,
                "round": "38",
                "scheduled_kickoff_time": "",  # how to get this ?
                "local_kickoff_time": "",  # how to get this ?
                "misc": {
                    "country": "",  # how to get this ?
                    "city": "",  # how to get this ?
                    "percipitation": 0,  # how to get this ?
                    "is_open_roof": True,  # how to get this ?
                },
            },
            "teams": {
                "home": {
                    "id": home_team.team_id,  # same as for the jsonl
                    "players": meta_home_players,
                },
                "away": {
                    "id": away_team.team_id,  # same as for the jsonl
                    "players": meta_away_players,
                },
            },
        }

        outputs.meta_data.write(metadata_json)
        return True
