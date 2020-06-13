import inspect
import re
import abc
from typing import Type, Dict


_first_cap_re = re.compile("(.)([A-Z][a-z0-9]+)")
_all_cap_re = re.compile("([a-z0-9])([A-Z])")

# from .builder import DatasetBuilder
_DATASET_REGISTRY: Dict[str, Type["DatasetBuilder"]] = {}


def camelcase_to_snakecase(name):
    """Convert camel-case string to snake-case."""
    s1 = _first_cap_re.sub(r"\1_\2", name)
    return _all_cap_re.sub(r"\1_\2", s1).lower()


class RegisteredDataset(abc.ABCMeta):
    def __new__(mcs, cls_name, bases, class_dict):
        name = camelcase_to_snakecase(cls_name)
        class_dict["name"] = name
        builder_cls = super(RegisteredDataset, mcs).__new__(
            mcs, cls_name, bases, class_dict
        )
        if not inspect.isabstract(builder_cls):
            _DATASET_REGISTRY[name] = builder_cls
        return builder_cls
