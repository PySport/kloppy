def docstring_inherit_attributes(parent):
    def inherit(obj):
        other_docs, attribute_docs = obj.__doc__.split("Attributes:\n")

        own_attributes = [
            attribute.strip()
            for attribute in attribute_docs.strip().split("\n")
        ]

        parent_attributes = [
            attribute.strip()
            for attribute in parent.__doc__.split("Attributes:\n")[-1]
            .strip()
            .split("\n")
        ]
        obj.__doc__ = (
            other_docs
            + "Attributes:\n        "
            + "\n        ".join(parent_attributes)
            + "\n        "
            + "\n        ".join(own_attributes)
            + "\n"
        )
        return obj

    return inherit
