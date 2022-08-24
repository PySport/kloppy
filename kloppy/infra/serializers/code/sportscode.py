import logging
from typing import Union, IO, NamedTuple

from lxml import objectify, etree


from kloppy.domain import (
    CodeDataset,
    Code,
    Period,
    Metadata,
    Provider,
    DatasetFlag,
    Score,
    Orientation,
)
from kloppy.exceptions import SerializationError

from .base import CodeDataDeserializer, CodeDataSerializer

logger = logging.getLogger(__name__)


def parse_value(s: str) -> Union[str, float, int]:
    try:
        func = float if "." in s else int
        return func(s)
    except ValueError:
        return str(s)


def parse_labels(instance):
    ret = {}
    for label in instance.iterchildren("label"):
        group = label.find("group")
        text = parse_value(str(label.find("text")))
        if group is None:
            ret[text] = True
        else:
            ret[str(group)] = text
    return ret


class SportsCodeInputs(NamedTuple):
    data: IO[bytes]


class SportsCodeDeserializer(CodeDataDeserializer[SportsCodeInputs]):
    def deserialize(self, inputs: SportsCodeInputs) -> CodeDataset:
        all_instances = objectify.fromstring(inputs.data.read())

        codes = []
        period = Period(id=1, start_timestamp=0, end_timestamp=0)
        for instance in all_instances.ALL_INSTANCES.iterchildren():
            end_timestamp = float(instance.end)

            code = Code(
                period=period,
                code_id=str(instance.ID),
                code=str(instance.code),
                timestamp=float(instance.start),
                end_timestamp=end_timestamp,
                labels=parse_labels(instance),
                ball_state=None,
                ball_owning_team=None,
            )
            period.end_timestamp = end_timestamp
            codes.append(code)

        return CodeDataset(
            metadata=Metadata(
                teams=[],
                periods=[period],
                pitch_dimensions=None,
                score=Score(0, 0),
                frame_rate=0.0,
                orientation=Orientation.NOT_SET,
                flags=~(DatasetFlag.BALL_OWNING_TEAM | DatasetFlag.BALL_STATE),
                provider=Provider.OTHER,
                coordinate_system=None,
            ),
            records=codes,
        )


class SportsCodeSerializer(CodeDataSerializer):
    def serialize(self, dataset: CodeDataset) -> bytes:
        root = etree.Element("file")
        all_instances = etree.SubElement(root, "ALL_INSTANCES")
        for i, code in enumerate(dataset.codes):
            relative_period_start = 0
            for period in dataset.metadata.periods:
                if period == code.period:
                    break
                else:
                    relative_period_start += period.duration

            instance = etree.SubElement(all_instances, "instance")
            id_ = etree.SubElement(instance, "ID")
            id_.text = code.code_id or str(i + 1)

            start = etree.SubElement(instance, "start")
            start.text = str(relative_period_start + code.start_timestamp)

            end = etree.SubElement(instance, "end")
            end.text = str(relative_period_start + code.end_timestamp)

            code_ = etree.SubElement(instance, "code")
            code_.text = code.code

            for group, text in code.labels.items():
                # Labels can be in two formats:
                # {"name": "value"} or {"name": True}
                label = etree.SubElement(instance, "label")
                if isinstance(text, bool):
                    if not text:
                        raise SerializationError(
                            f"You are not allowed to pass a False value for {group}"
                        )

                    text_ = etree.SubElement(label, "text")
                    text_.text = group
                else:
                    group_ = etree.SubElement(label, "group")
                    group_.text = str(group)

                    text_ = etree.SubElement(label, "text")
                    text_.text = str(text)

        return etree.tostring(
            root,
            pretty_print=True,
            xml_declaration=True,
            encoding="utf-8",  # This might not work with some tools because they expected 'ascii'.
            method="xml",
        )
