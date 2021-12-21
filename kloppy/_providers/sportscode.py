from kloppy.domain import CodeDataset
from kloppy.infra.serializers.code.sportscode import (
    SportsCodeSerializer,
    SportsCodeDeserializer,
    SportsCodeInputs,
)
from kloppy.io import open_as_file


def load(data: str) -> CodeDataset:
    deserializer = SportsCodeDeserializer()

    with open_as_file(data) as data_fp:
        return deserializer.deserialize(inputs=SportsCodeInputs(data=data_fp))


def save(dataset: CodeDataset, output_filename: str):
    with open(output_filename, "wb") as fp:
        serializer = SportsCodeSerializer()
        fp.write(serializer.serialize(dataset))
