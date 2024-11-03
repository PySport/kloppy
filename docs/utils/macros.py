"""
Mkdocs-macros module
"""

import yaml
import griffe
import pandas as pd
import re
from griffe import Docstring

kloppy = griffe.load("kloppy", resolve_aliases=True)

_EVENT_DATA_PROVIDERS = {
    "statsbomb": "StatsBomb",
    "statsperform": "Stats Perform",
    "wyscout_v2": "Wyscout (v2)",
    "wyscout_v3": "Wyscout (v3)",
    "datafactory": "DataFactory",
    "sportec": "Sportec",
    "metrica_json": "Metrica (JSON)",
}
_DEFAULT_EVENT_TYPE_SPEC = {
    "providers": { provider_key: {"status": "unknown"} for provider_key in _EVENT_DATA_PROVIDERS },
    "attributes": {},
}
_DEFAULT_EVENT_ATTRIBUTE_SPEC = {
    "providers": { provider_key: {"status": "unknown"} for provider_key in _EVENT_DATA_PROVIDERS },
}

def replace_unescaped_pipes(text: str) -> str:
    """
    Replace unescaped pipes.

    For regex explanation, see https://regex101.com/r/s8H588/1

    Args:
        text (str): input string

    Returns:
        str: output string
    """
    return re.sub(r"(?<!\\)\|", "\\|", text)


def convert_to_md_table(df: pd.DataFrame, markdown_kwargs: dict) -> str:
    """
    Convert dataframe to markdown table using tabulate.
    """
    # Escape any pipe characters, | to \|
    # See https://github.com/astanin/python-tabulate/issues/241
    df.columns = [
        replace_unescaped_pipes(c) if isinstance(c, str) else c for c in df.columns
    ]

    # Avoid deprecated applymap warning on pandas>=2.0
    # See https://github.com/timvink/mkdocs-table-reader-plugin/issues/55
    if pd.__version__ >= "2.1.0":
        df = df.map(lambda s: replace_unescaped_pipes(s) if isinstance(s, str) else s)
    else:
        df = df.applymap(
            lambda s: replace_unescaped_pipes(s) if isinstance(s, str) else s
        )

    if "index" not in markdown_kwargs:
        markdown_kwargs["index"] = False
    if "tablefmt" not in markdown_kwargs:
        markdown_kwargs["tablefmt"] = "pipe"

    return df.to_markdown(**markdown_kwargs)


def render_provider_spec(spec, provider_key):
    """
    Render the spec for a given provider.
    """
    if provider_key in spec["providers"]:
        provider_spec = spec["providers"][provider_key]
        status = provider_spec.get("status", "unknown")
        implementation = provider_spec.get("implementation", "unknown")
        if status == "parsed":
            return f':material-check:{{ title="{implementation}" }}'
        elif status == "not implemented":
            return ':material-progress-helper:{ title="not implemented" }'
        elif status == "not supported":
            return ':material-close:{ title="not supported" }'
    else:
        return ':material-progress-question:{ title="Status unkown" }'


def define_env(env):
    """
    This is the hook for defining variables, macros and filters

    - variables: the dictionary that contains the environment variables
    - macro: a decorator function, to declare a macro.
    - filter: a function with one of more arguments,
        used to perform a transformation
    """

    @env.macro
    def render_event_types():
        with open("docs/reference/providers/spec.yaml", "r") as file:
            spec = yaml.safe_load(file)["event_types"]


        # Create table
        columns, data = ["Type"], []
        for provider_name in _EVENT_DATA_PROVIDERS.values():
            columns += [provider_name]

        # Create a row for each event type
        for event_type, event_type_spec in spec.items():
            event_name = eval(
                kloppy[event_type.replace("kloppy.", "")].members["event_name"].value
            )
            row = [f"[{event_name}][{event_type}]"]
            for provider_key, provider_name in _EVENT_DATA_PROVIDERS.items():
                row += [render_provider_spec(event_type_spec, provider_key)]
            data += [row]

        table = convert_to_md_table(
            pd.DataFrame(data, columns=columns), {"index": False}
        )

        return f"""
<p><span class="doc-section-title">Event types:</span></p>
{table}
"""

    @env.macro
    def render_event_type(x):
        # Load spec file
        with open("docs/reference/providers/spec.yaml", "r") as file:
            spec = {**_DEFAULT_EVENT_TYPE_SPEC, **yaml.safe_load(file)["event_types"][x]}

        # Parse docstring of event type
        class_spec = kloppy[x.replace("kloppy.", "")]
        docstring = Docstring(class_spec.docstring.value, lineno=1).parse("google")

        # Get event type attributes
        attr_docstrings = next(
            (d.value for d in docstring if d.kind.name == "attributes"), list()
        )

        # Create table
        columns, data = ["Name", "Type", "Description"], []
        for provider_name in _EVENT_DATA_PROVIDERS.values():
            columns += [provider_name]

        # Create a row for each attribute
        for attr in attr_docstrings:
            row = []
            row += [attr.name]
            anchor = class_spec.members[attr.name].annotation.canonical_path
            if anchor.startswith("kloppy."):
                row += [f"[`{attr.annotation}`][{anchor}]"]
            else:
                row += [f"`{attr.annotation}`"]
            row += [attr.description]

            # Check if there is a record in the spec file for the attribute
            if attr.name in spec["attributes"]:
                attr_spec = spec["attributes"][attr.name]
                for provider_key, provider_name in _EVENT_DATA_PROVIDERS.items():
                    row += [render_provider_spec(attr_spec, provider_key)]
            else:
                for (
                    provider_key,
                    provider_name,
                ) in _EVENT_DATA_PROVIDERS.items():
                    row += ["-"]

            data += [row]

            if anchor.startswith("kloppy."):
                attr_class_spec = kloppy[anchor.replace("kloppy.", "")]
                anchor_is_enum = any([b.name =='Enum' for a in attr_class_spec.resolved_bases for b in a.bases])
                if attr_class_spec.docstring and anchor_is_enum:
                    attr_class_docstring = Docstring(attr_class_spec.docstring.value, lineno=1).parse("google")
                    attr_class_attr_docstrings = next(
                        (d.value for d in attr_class_docstring if d.kind.name == "attributes"), list()
                    )
                    for attr_value in attr_class_attr_docstrings:
                        row = [""]
                        row += [attr_value.name]
                        row += [attr_value.description]
                        # Check if there is a record in the spec file for the attribute value
                        if attr.name in spec["attributes"] and attr_value.name in spec["attributes"][attr.name]["values"]:
                            attr_value_spec = spec["attributes"][attr.name]["values"][attr_value.name]
                            for provider_key, provider_name in _EVENT_DATA_PROVIDERS.items():
                                row += [render_provider_spec(attr_value_spec, provider_key)]
                        else:
                            for (
                                provider_key,
                                provider_name,
                            ) in _EVENT_DATA_PROVIDERS.items():
                                row += ["-"]

                        data += [row]


        anchor = f'<a id="{x}"></a>'  # FIXME: this does not work

        description = docstring[0].value

        table = convert_to_md_table(
            pd.DataFrame(data, columns=columns), {"index": False}
        )

        return f"""
{anchor}

{description}

<p><span class="doc-section-title">Attributes</span></p>
{table}
"""

    @env.macro
    def render_result_type(x):
        # Load spec file
        with open("docs/reference/providers/spec.yaml", "r") as file:
            spec = {**_DEFAULT_EVENT_TYPE_SPEC, **yaml.safe_load(file)["event_types"][x]}

        # Parse docstring of event type
        class_spec = kloppy[x.replace("kloppy.", "")]
        docstring = Docstring(class_spec.docstring.value, lineno=1).parse("google")

        # Get event type attributes
        attr_docstrings = next(
            (d.value for d in docstring if d.kind.name == "attributes"), list()
        )

        # Create table
        columns, data = ["Name", "Description"], []
        for provider_name in _EVENT_DATA_PROVIDERS.values():
            columns += [provider_name]

        # Create a row for each attribute
        for attr in attr_docstrings:
            row = []
            row += [attr.name]
            row += [attr.description]

            # Check if there is a record in the spec file for the attribute
            if attr.name in spec["attributes"]:
                attr_spec = {**_DEFAULT_EVENT_ATTRIBUTE_SPEC, **spec["attributes"][attr.name]}
                for (provider_key, provider_spec) in attr_spec["providers"].items():
                    status = provider_spec["status"]
                    implementation = provider_spec.get("implementation", "unknown")
                    if status == "parsed":
                        row += [f':material-check:{{ title="{implementation}" }}']
                    elif status == "not implemented":
                        row += [
                            ':material-progress-helper:{ title="not implemented" }'
                        ]
                    elif status == "not supported":
                        row += [':material-close:{ title="not supported" }']
                    else:
                        row += [':material-progress-question:{ title="Status unkown" }']

                if "values" in attr_spec:
                    for v in attr_spec["values"]:
                        for (provider_key, provider_spec) in attr_spec["values"][v]["providers"].items():
                            status = provider_spec["status"]
                            implementation = provider_spec.get("implementation", "unknown")
                            if status == "parsed":
                                row += [f':material-check:{{ title="{implementation}" }}']
                            elif status == "not implemented":
                                row += [
                                    ':material-progress-helper:{ title="not implemented" }'
                                ]
                            elif status == "not supported":
                                row += [':material-close:{ title="not supported" }']
                            else:
                                row += [':material-progress-question:{ title="Status unkown" }']




            else:
                for (
                    provider_key,
                    provider_name,
                ) in _EVENT_DATA_PROVIDERS.items():
                    row += ["-"]

            data += [row]

        anchor = f'<a id="{x}"></a>'  # FIXME: this does not work

        description = docstring[0].value

        table = convert_to_md_table(
            pd.DataFrame(data, columns=columns), {"index": False}
        )

        return f"""
<p><span class="doc-section-title">{description}</span></p>
{table}
"""
