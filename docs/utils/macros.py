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
        replace_unescaped_pipes(c) if isinstance(c, str) else c
        for c in df.columns
    ]

    # Avoid deprecated applymap warning on pandas>=2.0
    # See https://github.com/timvink/mkdocs-table-reader-plugin/issues/55
    if pd.__version__ >= "2.1.0":
        df = df.map(
            lambda s: replace_unescaped_pipes(s) if isinstance(s, str) else s
        )
    else:
        df = df.applymap(
            lambda s: replace_unescaped_pipes(s) if isinstance(s, str) else s
        )

    if "index" not in markdown_kwargs:
        markdown_kwargs["index"] = False
    if "tablefmt" not in markdown_kwargs:
        markdown_kwargs["tablefmt"] = "pipe"

    return df.to_markdown(**markdown_kwargs)


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
            spec = yaml.safe_load(file)

        columns = ["Type"]
        data = []

        for provider_key, provider_name in _EVENT_DATA_PROVIDERS.items():
            columns += [provider_name]

        for event_type, event_type_spec in spec["event_types"].items():
            event_name = eval(
                kloppy[event_type.replace("kloppy.", "")]
                .members["event_name"]
                .value
            )
            row = [f"[{event_name}][{event_type}]"]
            for provider_key, provider_name in _EVENT_DATA_PROVIDERS.items():
                if provider_key in event_type_spec["providers"]:
                    status = event_type_spec["providers"][provider_key].get(
                        "status", "unknown"
                    )
                    implementation = event_type_spec["providers"][
                        provider_key
                    ].get("implementation", "unknown")
                    if status == "parsed":
                        row += [
                            f':material-check:{{ title="{implementation}" }}'
                        ]
                    elif status == "not implemented":
                        row += [
                            ':material-progress-helper:{ title="not implemented" }'
                        ]
                    elif status == "not supported":
                        row += [':material-close:{ title="not supported" }']
                else:
                    row += [
                        ':material-progress-question:{ title="Status unkown" }'
                    ]
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
        with open("docs/reference/providers/spec.yaml", "r") as file:
            spec = yaml.safe_load(file)

        class_spec = kloppy[x.replace("kloppy.", "")]
        docstring = Docstring(class_spec.docstring.value, lineno=1).parse(
            "google"
        )

        attr_docstrings = next(
            (d.value for d in docstring if d.kind.name == "attributes"), list()
        )

        columns = ["Name", "Type", "Description"]
        data = []

        for key, name in _EVENT_DATA_PROVIDERS.items():
            columns += [name]

        for attr in attr_docstrings:
            row = [attr.name, attr.annotation, attr.description]
            if attr.name in spec["event_types"][x].get("attributes", {}):
                attr_spec = spec["event_types"][x]["attributes"][
                    attr.name
                ].get("providers", {})
                for (
                    provider_key,
                    provider_name,
                ) in _EVENT_DATA_PROVIDERS.items():
                    if provider_key in attr_spec:
                        status = attr_spec[provider_key].get(
                            "status", "unknown"
                        )
                        implementation = attr_spec[provider_key].get(
                            "implementation", "unknown"
                        )
                        if status == "parsed":
                            row += [
                                f':material-check:{{ title="{implementation}" }}'
                            ]
                        elif status == "not implemented":
                            row += [
                                ':material-progress-helper:{ title="not implemented" }'
                            ]
                        elif status == "not supported":
                            row += [
                                ':material-close:{ title="not supported" }'
                            ]
                    else:
                        row += [
                            ':material-progress-question:{ title="Status unkown" }'
                        ]
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

<p><span class="doc-section-title">Attributes:</span></p>
{table}
"""
