import abc
import inspect

from kloppy._utils import to_snake_case

_STATE_BUILDER_REGISTRY: dict[str, type["StateBuilder"]] = {}  # noqa: F821


class RegisteredStateBuilder(abc.ABCMeta):
    def __new__(mcs, cls_name, bases, class_dict):
        name = to_snake_case(cls_name)
        class_dict["name"] = name
        builder_cls = super().__new__(mcs, cls_name, bases, class_dict)
        if not inspect.isabstract(builder_cls):
            _STATE_BUILDER_REGISTRY[name.replace("_state_builder", "")] = (
                builder_cls
            )
        return builder_cls


def create_state_builder(builder_key: str):
    if builder_key not in _STATE_BUILDER_REGISTRY:
        raise ValueError(
            f"StateBuilder {builder_key} not found. Known builders: {', '.join(_STATE_BUILDER_REGISTRY.keys())}"
        )
    return _STATE_BUILDER_REGISTRY[builder_key]()
