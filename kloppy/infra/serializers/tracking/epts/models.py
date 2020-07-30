from dataclasses import dataclass
from typing import List, Dict, Union, Set

from kloppy.domain import Team, Player, Metadata


# TODO: fill this with from SplitRegisters
NON_SPLIT_CHAR_REGEX = "[^,;:]*"


@dataclass
class Channel:
    channel_id: str
    name: str
    unit: str
    sensor: "Sensor"

    @classmethod
    def from_xml_element(cls, elm) -> "Channel":
        return cls(
            channel_id=elm.attrib["id"],
            name=str(elm.find("Name")),
            unit=str(elm.find("Unit")),
            sensor=None,  # should be set from sensor constructor
        )


@dataclass
class PlayerChannel:
    player_channel_id: str
    channel: Channel
    player: Player


@dataclass
class Sensor:
    sensor_id: str
    name: str
    channels: List[Channel]

    @classmethod
    def from_xml_element(cls, elm) -> "Sensor":
        obj = cls(
            sensor_id=elm.attrib["id"],
            name=str(elm.find("Name")),
            channels=[
                Channel.from_xml_element(channel_elm)
                for channel_elm in elm.find("Channels").iterchildren(
                    tag="Channel"
                )
            ],
        )
        for channel in obj.channels:
            channel.sensor = obj

        return obj


@dataclass
class StringRegister:
    name: str

    def to_regex(self, **kwargs) -> str:
        return f"(?P<{self.name}>{NON_SPLIT_CHAR_REGEX})"

    @classmethod
    def from_xml_element(cls, elm) -> "StringRegister":
        return cls(name=elm.attrib["name"])


@dataclass
class PlayerChannelRef:
    player_channel_id: str

    def to_regex(
        self, player_channel_map: Dict[str, PlayerChannel], **kwargs
    ) -> str:
        if self.player_channel_id in player_channel_map:
            player_channel = player_channel_map[self.player_channel_id]
            return f"(?P<player_{player_channel.player.player_id}_{player_channel.channel.channel_id}>{NON_SPLIT_CHAR_REGEX})"
        else:
            return NON_SPLIT_CHAR_REGEX

    @classmethod
    def from_xml_element(cls, elm) -> "PlayerChannelRef":
        return cls(player_channel_id=elm.attrib["playerChannelId"])


@dataclass
class BallChannelRef:
    channel_id: str

    def to_regex(self, ball_channel_map: Dict[str, Channel], **kwargs) -> str:
        if self.channel_id in ball_channel_map:
            return f"(?P<ball_{self.channel_id}>{NON_SPLIT_CHAR_REGEX})"
        else:
            return NON_SPLIT_CHAR_REGEX

    @classmethod
    def from_xml_element(cls, elm) -> "BallChannelRef":
        return cls(channel_id=elm.attrib["channelId"])


@dataclass
class SplitRegister:
    separator: str
    children: List[
        Union[
            BallChannelRef, PlayerChannelRef, StringRegister, "SplitRegister"
        ]
    ]

    def to_regex(self, **kwargs) -> str:
        return (
            self.separator.join(
                [child.to_regex(**kwargs) for child in self.children]
            )
            + f"{self.separator}?"
        )

    @classmethod
    def from_xml_element(cls, elm) -> "SplitRegister":
        children = []
        for child_elm in elm.iterchildren():
            if child_elm.tag == "StringRegister":
                child = StringRegister.from_xml_element(child_elm)
            elif child_elm.tag == "PlayerChannelRef":
                child = PlayerChannelRef.from_xml_element(child_elm)
            elif child_elm.tag == "BallChannelRef":
                child = BallChannelRef.from_xml_element(child_elm)
            elif child_elm.tag == "SplitRegister":
                child = SplitRegister.from_xml_element(child_elm)
            else:
                raise Exception(f"Unknown tag {child_elm.tag}")

            children.append(child)

        return cls(separator=elm.attrib["separator"], children=children)


@dataclass
class DataFormatSpecification:
    start_frame: int
    end_frame: int
    split_register: SplitRegister

    @classmethod
    def from_xml_element(cls, elm) -> "DataFormatSpecification":
        return cls(
            start_frame=int(elm.attrib["startFrame"]),
            end_frame=int(elm.attrib["endFrame"]),
            split_register=SplitRegister.from_xml_element(elm),
        )

    def to_regex(self, **kwargs) -> str:
        return "^" + self.split_register.to_regex(**kwargs) + "$"


@dataclass
class EPTSMetadata(Metadata):
    player_channels: List[PlayerChannel]
    data_format_specifications: List[DataFormatSpecification]
    sensors: List[Sensor]
