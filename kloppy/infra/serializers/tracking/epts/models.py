from dataclasses import dataclass
from typing import List, Dict, Union

from kloppy.domain import Team, Player, MetaData


@dataclass
class PlayerChannel:
    player_channel_id: str
    channel_id: str
    player: Player


@dataclass
class StringRegister:
    name: str

    def to_regex(self, **kwargs) -> str:
        return f"(?P<{self.name}>)"

    @classmethod
    def from_xml_element(cls, elm) -> 'StringRegister':
        return cls(
            name=elm.attrib['name']
        )


@dataclass
class PlayerChannelRef:
    player_channel_id: str

    def to_regex(self, player_channel_map: Dict[str, PlayerChannel], **kwargs) -> str:
        player_channel = player_channel_map[self.player_channel_id]
        team_str = "home" if player_channel.player.team == Team.HOME else "away"
        return f"(?P<player_{team_str}_{player_channel.player.jersey_no}_{player_channel.channel_id}>)"

    @classmethod
    def from_xml_element(cls, elm) -> 'PlayerChannelRef':
        return cls(
            player_channel_id=elm.attrib['playerChannelId']
        )


@dataclass
class BallChannelRef:
    channel_id: str

    def to_regex(self, **kwargs) -> str:
        return f"(?P<ball_{self.channel_id}>)"

    @classmethod
    def from_xml_element(cls, elm) -> 'BallChannelRef':
        return cls(
            channel_id=elm.attrib['channelId']
        )


@dataclass
class SplitRegister:
    separator: str
    children: List[Union[BallChannelRef, PlayerChannelRef, StringRegister, 'SplitRegister']]

    def to_regex(self, **kwargs) -> str:
        return self.separator.join(
            [child.to_regex(**kwargs) for child in self.children]
        )

    @classmethod
    def from_xml_element(cls, elm) -> 'SplitRegister':
        children = []
        for child_elm in elm.iterchildren():
            if child_elm.tag == 'StringRegister':
                child = StringRegister.from_xml_element(child_elm)
            elif child_elm.tag == 'PlayerChannelRef':
                child = PlayerChannelRef.from_xml_element(child_elm)
            elif child_elm.tag == 'BallChannelRef':
                child = BallChannelRef.from_xml_element(child_elm)
            elif child_elm.tag == 'SplitRegister':
                child = SplitRegister.from_xml_element(child_elm)
            else:
                raise Exception(f"Unknown tag {child_elm.tag}")

            children.append(child)

        return cls(
            separator=elm.attrib['separator'],
            children=children
        )


@dataclass
class DataFormatSpecification:
    start_frame: int
    end_frame: int
    split_register: SplitRegister

    @classmethod
    def from_xml_element(cls, elm) -> 'DataFormatSpecification':
        return cls(
            start_frame=int(elm.attrib['startFrame']),
            end_frame=int(elm.attrib['endFrame']),
            split_register=SplitRegister.from_xml_element(elm),
        )

    def to_regex(self, **kwargs) -> str:
        return self.split_register.to_regex(**kwargs)


@dataclass
class EPTSMetaData(MetaData):
    player_channels: List[PlayerChannel]
    data_format_specifications: List[DataFormatSpecification]
    frame_rate: int

