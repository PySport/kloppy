import inspect
import abc
from typing import Type, Dict


# from .builder import DatasetBuilder
from kloppy.utils import camelcase_to_snakecase

_DATASET_REGISTRY: Dict[str, Type["DatasetBuilder"]] = {}


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
