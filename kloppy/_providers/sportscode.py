from kloppy.domain import CodeDataset
from kloppy.infra.serializers.code.sportscode import (
    SportsCodeDeserializer,
    SportsCodeInputs,
    SportsCodeSerializer,
)
from kloppy.io import FileLike, open_as_file


def load(data: FileLike) -> CodeDataset:
    """
    Load SportsCode data.

    Args:
        data: The raw SportsCode XML data.

    Returns:
        The parsed SportsCode data.
    """
    deserializer = SportsCodeDeserializer()

    with open_as_file(data) as data_fp:
        return deserializer.deserialize(inputs=SportsCodeInputs(data=data_fp))


def save(dataset: CodeDataset, output_filename: str) -> None:
    """
    Save SportsCode data to an XML file.

    Args:
        dataset: The SportsCode dataset to save.
        output_filename: The output filename.
    """
    with open(output_filename, "wb") as fp:
        serializer = SportsCodeSerializer()
        fp.write(serializer.serialize(dataset))
