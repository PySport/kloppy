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

        outputs.meta_data.write(
            b"""{
    "competition": {
      "id": "comp_123",
      "name": "Dutch Eredivisie Under 20",
      "format": "league_20",
      "age_restriction": null,
      "type": "mens"
    },
    "season": {
      "id": "season_2023",
      "name": "2022/23"
    },
    "match": {
      "id": "match_456",
      "kickoff_time": "2023-05-15T19:45:00Z",
      "periods": [
        {
          "period": "first_half",
          "play_direction": "left_right",
          "start_time": "2023-05-15T19:45:00Z",
          "end_time": "2023-05-15T20:30:00Z",
          "start_frame_id": 0,
          "end_frame_id": 27000,
          "left_team_id": "team_789",
          "right_team_id": "team_101"
        },
        {
          "period": "second_half",
          "play_direction": "right_left",
          "start_time": "2023-05-15T20:45:00Z",
          "end_time": "2023-05-15T21:30:00Z",
          "start_frame_id": 27001,
          "end_frame_id": 54000,
          "left_team_id": "team_101",
          "right_team_id": "team_789"
        }
      ],
      "whistles": [
        {
          "type": "first_half",
          "sub_type": "start",
          "time": "2023-05-15T19:45:00Z"
        },
        {
          "type": "first_half",
          "sub_type": "end",
          "time": "2023-05-15T20:30:00Z"
        },
        {
          "type": "second_half",
          "sub_type": "start",
          "time": "2023-05-15T20:45:00Z"
        },
        {
          "type": "second_half",
          "sub_type": "end",
          "time": "2023-05-15T21:30:00Z"
        }
      ],
      "round": "38",
      "scheduled_kickoff_time": "2023-05-15T19:45:00Z",
      "local_kickoff_time": "2023-05-15T20:45:00+01:00",
      "misc": {
        "country": "Netherlands",
        "city": "Breda",
        "percipitation": 0.5,
        "is_open_roof": true
      }
    },
    "teams": {
      "home": {
        "id": "team_789",
        "players": [
          {
            "id": "player_1",
            "team_id": "team_789",
            "jersey_number": 1,
            "is_starter": true
          },
          {
            "id": "player_2",
            "team_id": "team_789",
            "jersey_number": 2,
            "is_starter": true
          },
          {
            "id": "player_3",
            "team_id": "team_789",
            "jersey_number": 3,
            "is_starter": true
          },
          {
            "id": "player_4",
            "team_id": "team_789",
            "jersey_number": 4,
            "is_starter": true
          },
          {
            "id": "player_5",
            "team_id": "team_789",
            "jersey_number": 5,
            "is_starter": true
          },
          {
            "id": "player_6",
            "team_id": "team_789",
            "jersey_number": 6,
            "is_starter": true
          },
          {
            "id": "player_7",
            "team_id": "team_789",
            "jersey_number": 7,
            "is_starter": true
          },
          {
            "id": "player_8",
            "team_id": "team_789",
            "jersey_number": 8,
            "is_starter": true
          },
          {
            "id": "player_9",
            "team_id": "team_789",
            "jersey_number": 9,
            "is_starter": true
          },
          {
            "id": "player_10",
            "team_id": "team_789",
            "jersey_number": 10,
            "is_starter": true
          },
          {
            "id": "player_11",
            "team_id": "team_789",
            "jersey_number": 11,
            "is_starter": true
          },
          {
            "id": "player_12",
            "team_id": "team_789",
            "jersey_number": 12,
            "is_starter": false
          }
        ]
      },
      "away": {
        "id": "team_101",
        "players": [
          {
            "id": "player_101",
            "team_id": "team_101",
            "jersey_number": 1,
            "is_starter": true
          },
          {
            "id": "player_102",
            "team_id": "team_101",
            "jersey_number": 2,
            "is_starter": true
          },
          {
            "id": "player_103",
            "team_id": "team_101",
            "jersey_number": 3,
            "is_starter": true
          },
          {
            "id": "player_104",
            "team_id": "team_101",
            "jersey_number": 4,
            "is_starter": true
          },
          {
            "id": "player_105",
            "team_id": "team_101",
            "jersey_number": 5,
            "is_starter": true
          },
          {
            "id": "player_106",
            "team_id": "team_101",
            "jersey_number": 6,
            "is_starter": true
          },
          {
            "id": "player_107",
            "team_id": "team_101",
            "jersey_number": 7,
            "is_starter": true
          },
          {
            "id": "player_108",
            "team_id": "team_101",
            "jersey_number": 8,
            "is_starter": true
          },
          {
            "id": "player_109",
            "team_id": "team_101",
            "jersey_number": 9,
            "is_starter": true
          },
          {
            "id": "player_110",
            "team_id": "team_101",
            "jersey_number": 10,
            "is_starter": true
          },
          {
            "id": "player_111",
            "team_id": "team_101",
            "jersey_number": 11,
            "is_starter": true
          },
          {
            "id": "player_112",
            "team_id": "team_101",
            "jersey_number": 12,
            "is_starter": false
          }
        ]
      }
    },
    "stadium": {
      "id": "stadium_202",
      "pitch_length": 105.0,
      "pitch_width": 68.0,
      "name": "A Stadium",
      "turf": "grass"
    },
    "meta": {
      "video": {
        "perspective": "stadium",
        "version": "0.1.0",
        "name": "VideoVendor",
        "fps": 25
      },
      "tracking": {
        "version": "0.1.0",
        "name": "TrackingVendor",
        "fps": 25,
        "collection_timing": "live"
      },
      "landmarks": {
        "version": "0.1.0",
        "name": "LimbTrackingVendor",
        "fps": 25,
        "collection_timing": "post"
      },
      "ball": {
        "version": "0.1.0",
        "name": "BallTrackingVendor",
        "fps": 50,
        "collection_timing": "live"
      },
      "event": {
        "collection_timing": "live"
      },
      "meta": {
        "version": "0.1.0",
        "name": "Meta Vendor"
      },
      "cdf": {
        "version": "0.2.0"
      }
    }
  }"""
        )
        outputs.tracking_data.write(
            b'{"frame_id":123456, "timestamp": "2023-10-01T12:00:00Z","period":"first_half","match":{"id":"match_12345"},"ball_status": true,"teams":{"home":{"id":"team_1","players":[{"id":"player_1","x":23.5,"y":45.2},{"id":"player_2","x":56.3,"y":12.8}]},"away":{"id":"team_2","players":[{"id":"player_3","x":78.1,"y":34.9},{"id":"player_4","x":45.6,"y":89}]}},"ball":{"x":50,"y":50,"z":0.5}}'
        )
        return True
