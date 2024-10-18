import dataclasses
import warnings
from dataclasses import fields

from kloppy.domain import Frame


def create_frame(**kwargs) -> Frame:
    """
    Do the actual construction of a frame.

    This method does a couple of things:
    1. Fill in some arguments when not passed
    2. Pass only arguments that are accepted by the Frame class.
    """
    if "statistics" not in kwargs:
        kwargs["statistics"] = []

    relevant_kwargs = {
        field.name: kwargs.get(field.name, field.default)
        for field in fields(Frame)
        if field.init
        and not (
            field.default == dataclasses.MISSING and field.name not in kwargs
        )
    }

    if len(relevant_kwargs) < len(kwargs):
        skipped_kwargs = set(kwargs.keys()) - set(relevant_kwargs.keys())
        warnings.warn(
            f"The following arguments were skipped: {skipped_kwargs}"
        )

    frame = Frame(**relevant_kwargs)

    return frame
