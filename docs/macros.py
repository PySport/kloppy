"""
Mkdocs-macros module
"""

import copy
import re
from pathlib import Path
from typing import Any

import griffe
import pandas as pd
import yaml
from griffe import Docstring
from griffe_generics import GenericsExtension

extensions = griffe.load_extensions(GenericsExtension)
kloppy = griffe.load(
    "kloppy",
    resolve_aliases=True,
    extensions=extensions,
)

_EVENT_SPEC_FILE = Path("docs/reference/event-data/spec.yaml")
_EVENT_DATA_PROVIDERS = {
    "statsbomb": "Hudl StatsBomb",
    "statsperform": "Stats Perform / Opta",
    "wyscout_v2": "Wyscout (v2)",
    "wyscout_v3": "Wyscout (v3)",
    "datafactory": "DataFactory",
    "sportec": "Sportec Solutions",
    "metrica_json": "Metrica (JSON)",
}
_DEFAULT_EVENT_ATTRIBUTE_SPEC = {
    "providers": {
        provider_key: {"status": "unknown"}
        for provider_key in _EVENT_DATA_PROVIDERS
    },
}
_DEFAULT_EVENT_TYPE_SPEC = {
    "providers": {
        provider_key: {"status": "unknown"}
        for provider_key in _EVENT_DATA_PROVIDERS
    },
    "attributes": {
        attr_name: _DEFAULT_EVENT_ATTRIBUTE_SPEC
        for attr_name in [
            "event_id",
            "event_type",
            "event_name",
            "qualifiers",
            "dataset",
            "prev_record",
            "next_record",
            "attacking_direction",
        ]
    },
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


def render_provider_spec(spec, provider_key):
    """
    Render the spec for a given provider.
    """
    if provider_key in spec["providers"]:
        provider_spec = spec["providers"][provider_key]
        status = provider_spec.get("status", "unknown")
        implementation = provider_spec.get(
            "implementation", "No implementation details"
        )
        if status == "parsed":
            return f':material-check:{{ title="{implementation}" }}'
        if status == "inferred":
            return f':material-check-circle-outline:{{ title="{implementation}" }}'
        elif status == "not implemented":
            return ':material-progress-helper:{ title="Not implemented" }'
        elif status == "not supported":
            return ':material-close:{ title="Not supported" }'
    else:
        return ':material-progress-question:{ title="Status unkown" }'


def annotation_to_md(annotation):
    if isinstance(annotation, griffe.ExprName):
        attr_anchor = annotation.canonical_path if annotation else None
        if attr_anchor is not None and attr_anchor.startswith("kloppy."):
            return f"[`{annotation.name}`][{attr_anchor}]"
        elif attr_anchor is not None:
            return f"`{annotation}`"
        else:
            return "?"
    elif isinstance(annotation, griffe.ExprSubscript):
        return (
            annotation_to_md(annotation.left)
            + "\["
            + annotation_to_md(annotation.slice)
            + "\]"
        )
    elif isinstance(annotation, griffe.ExprTuple):
        return ", ".join([annotation_to_md(a) for a in annotation.elements])
    elif isinstance(annotation, str):
        return annotation
    raise ValueError(
        f"Unsupported annotation type: {type(annotation)} for {annotation}"
    )


def _deepupdate(target: dict[Any, Any], src: dict[Any, Any]) -> None:
    """Deep update target dict with src.

    For each k,v in src: if k doesn't exist in target, it is deep copied from
    src to target. Otherwise, if v is a list, target[k] is extended with
    src[k]. If v is a set, target[k] is updated with v, If v is a dict,
    recursively deep-update it.

    Args:
        target: The original dictionary which is updated.
        src: The dictionary with which `target` is updated.

    Examples:
        >>> t = {'name': 'ferry', 'hobbies': ['programming', 'sci-fi']}
        >>> deepupdate(t, {'hobbies': ['gaming']})
        >>> print(t)
        {'name': 'ferry', 'hobbies': ['programming', 'sci-fi', 'gaming']}
    """
    for k, v in src.items():
        if isinstance(v, list):
            if k not in target:
                target[k] = copy.deepcopy(v)
            else:
                target[k].extend(v)
        elif isinstance(v, dict):
            if k not in target:
                target[k] = copy.deepcopy(v)
            else:
                _deepupdate(target[k], v)
        elif isinstance(v, set):
            if k not in target:
                target[k] = v.copy()
            else:
                target[k].update(v.copy())
        else:
            target[k] = copy.copy(v)


def _get_object(obj_id):
    return kloppy[obj_id.replace("kloppy.", "")]


def _get_docstring(obj_id):
    obj = _get_object(obj_id)
    docstring = Docstring(obj.docstring.value, lineno=1).parse("google")
    return docstring


def define_env(env):
    """
    This is the hook for defining variables, macros and filters

    - variables: the dictionary that contains the environment variables
    - macro: a decorator function, to declare a macro.
    - filter: a function with one of more arguments,
        used to perform a transformation
    """

    with open(_EVENT_SPEC_FILE, "r") as file:
        event_spec = yaml.safe_load(file)

    @env.macro
    def render_event_types():
        """Create an overview table with all event types."""
        spec = event_spec["event_types"]

        # Create table
        columns, data = ["Type Name"], []
        for provider_name in _EVENT_DATA_PROVIDERS.values():
            columns += [provider_name]

        # Create a row for each event type
        for event_type, event_type_spec in spec.items():
            # event_name = eval(_get_object(event_type).all_members["event_name"].value)
            event_name = _get_object(event_type).name.replace("Event", "")
            row = [f"[{event_name}][{event_type}]"]
            for provider_key, provider_name in _EVENT_DATA_PROVIDERS.items():
                row += [render_provider_spec(event_type_spec, provider_key)]
            data += [row]

        table = convert_to_md_table(
            pd.DataFrame(data=data, columns=columns), {"index": False}
        )

        return f"""
<p><span class="doc-section-title">Event types:</span></p>
{table}
"""

    @env.macro
    def render_provider_selectbox():
        """ "Render a multi-select input to show/hide providers."""
        html_template = """<div class="table-control-panel md-grid">
            <details class="multi-select multi-select-provider">
              <summary>Show/hide data providers</summary>
              <form>
                <fieldset>
                  <legend>Data providers</legend>
                  <ul>
                    {checkboxes}
                  </ul>
                </fieldset>
              </form>
            </details>
        </div>"""

        checkbox_template = """<li>
          <label for="{key}">{label}
            <input type="checkbox" id="{key}" name="{key}" value="{label}" checked>
          </label>
        </li>"""

        # Generate checkboxes dynamically
        checkboxes_html = "\n".join(
            checkbox_template.format(key=key, label=label)
            for key, label in _EVENT_DATA_PROVIDERS.items()
        )

        # Insert checkboxes into the template
        html_output = html_template.format(checkboxes=checkboxes_html)
        return html_output

    @env.macro
    def render_event_type(
        event_type,
        show_providers=True,
        only_generic=False,
        only_specific=False,
    ):
        """Create a detailed table with the attributes of the given event type."""
        spec = event_spec["event_types"].get(event_type, {})
        _deepupdate(
            spec,
            event_spec["event_types"].get("kloppy.domain.GenericEvent", {}),
        )
        _deepupdate(spec, _DEFAULT_EVENT_TYPE_SPEC)

        # Create table
        columns, data = ["group", "Name", "Description"], []
        value_data_tables = []
        for provider_name in _EVENT_DATA_PROVIDERS.values():
            columns += [provider_name]

        def _create_attribute_row(attr):
            row = [attr.name]
            attr_annotation = class_obj.all_members[attr.name].annotation
            row += [
                attr.description
                + "<br/><br/>**TYPE:** "
                + annotation_to_md(attr_annotation)
            ]

            # Check if there is a record in the spec file for the attribute
            if attr.name in spec["attributes"]:
                attr_spec = spec["attributes"][attr.name]
                for (
                    provider_key,
                    provider_name,
                ) in _EVENT_DATA_PROVIDERS.items():
                    row += [render_provider_spec(attr_spec, provider_key)]
            else:
                for (
                    provider_key,
                    provider_name,
                ) in _EVENT_DATA_PROVIDERS.items():
                    row += ["-"]
            return row

        def _create_attribute_value_row(attr_value):
            # row = [""]
            row = [""]
            row += [attr_value.name, attr_value.description]
            # Check if there is a record in the spec file for the attribute value
            if attr.name in spec["attributes"] and attr_value.name in spec[
                "attributes"
            ][attr.name].get("values", {}):
                attr_value_spec = spec["attributes"][attr.name]["values"][
                    attr_value.name
                ]
                for provider_key in _EVENT_DATA_PROVIDERS.keys():
                    row += [
                        render_provider_spec(attr_value_spec, provider_key)
                    ]
            else:
                for provider_key in _EVENT_DATA_PROVIDERS.keys():
                    row += ["-"]
            return row

        for obj_id in ["kloppy.domain.Event", event_type]:
            # Parse docstring of event type
            class_obj = _get_object(obj_id)
            class_docstring = _get_docstring(obj_id)

            # Get event type attribute docstrings
            attr_docstrings = next(
                (
                    d.value
                    for d in class_docstring
                    if d.kind.name == "attributes"
                ),
                list(),
            )
            # Create a row for each attribute
            for attr in attr_docstrings:
                data += [[obj_id] + _create_attribute_row(attr)]

                attr_annotation = class_obj.all_members[attr.name].annotation
                attr_anchor = (
                    attr_annotation.canonical_path
                    if attr_annotation is not None
                    and not isinstance(attr_annotation, str)
                    else None
                )
                if attr_anchor is not None and attr_anchor.startswith(
                    "kloppy."
                ):
                    attr_class_spec = _get_object(attr_anchor)
                    anchor_is_enum = any(
                        [
                            b.name == "Enum"
                            for a in attr_class_spec.resolved_bases
                            for b in a.bases
                        ]
                    )
                    if attr_class_spec.docstring and anchor_is_enum:
                        value_data = []
                        attr_class_docstring = _get_docstring(attr_anchor)
                        attr_class_attr_docstrings = next(
                            (
                                d.value
                                for d in attr_class_docstring
                                if d.kind.name == "attributes"
                            ),
                            list(),
                        )
                        for attr_value in attr_class_attr_docstrings:
                            value_data += [
                                _create_attribute_value_row(attr_value)
                            ]
                        value_data_tables += [
                            (
                                attr_anchor,
                                convert_to_md_table(
                                    pd.DataFrame(
                                        data=value_data, columns=columns
                                    ).drop(columns=["group"]),
                                    {"index": False},
                                ),
                            )
                        ]

        # anchor = f'<a id="{event_type}"></a>'  # FIXME: this does not work
        # anchor = "[](){" + event_type + "}"

        description = class_docstring[0].value

        table = pd.DataFrame(data=data, columns=columns).drop_duplicates(
            subset=["Name"], keep="last"
        )

        if not show_providers:
            table.drop(
                columns=list(_EVENT_DATA_PROVIDERS.values()), inplace=True
            )

        specific_table = convert_to_md_table(
            table.loc[table["group"] != "kloppy.domain.Event"].drop(
                columns=["group"]
            ),
            {"index": False},
        )
        generic_table = convert_to_md_table(
            table.loc[table["group"] == "kloppy.domain.Event"].drop(
                columns=["group"]
            ),
            {"index": False},
        )

        if only_generic:
            return f"{render_provider_selectbox()} {generic_table}"
        if only_specific:
            return f"{render_provider_selectbox()} {specific_table}"
        return f"""
{render_provider_selectbox()}

<h2 id="{event_type}" class="doc doc-heading">
    <code class="doc-symbol doc-symbol-heading doc-symbol-class"></code>
    <span class="doc doc-object-name doc-class-name">{event_type}</span>
    <span class="doc doc-labels">
      <small class="doc doc-label doc-label-dataclass"><code>dataclass</code></small>
    </span>
</h2>

{description}

<p><span class="doc-section-title">Event Specific Attributes</span></p>
{specific_table}

<p><span class="doc-section-title">Event Data General Attributes</span></p>
{generic_table}

""" + "\n".join(
            [
                f"""
<h2 id="{name}" class="doc doc-heading">
    <code class="doc-symbol doc-symbol-heading doc-symbol-class"></code>
    <span class="doc doc-object-name doc-class-name">{name}</span>
</h2>

{table}
"""
                for name, table in value_data_tables
            ]
        )

    @env.macro
    def render_qualifier(qualifier_type, qualifier_value_type):
        """Create a detailed table with the possible values of a qualifier."""
        spec = event_spec["qualifiers"].get(qualifier_type, {})
        _deepupdate(spec, _DEFAULT_EVENT_TYPE_SPEC)

        # Parse docstring of event type
        qualifier_docstring = _get_docstring(qualifier_type)
        value_docstring = _get_docstring(qualifier_value_type)

        # Get qualifier value type
        attr_docstrings = next(
            (
                d.value
                for d in qualifier_docstring
                if d.kind.name == "attributes"
            ),
            list(),
        )

        # Create table
        columns, data = ["Name", "Type", "Description"], []
        for provider_name in _EVENT_DATA_PROVIDERS.values():
            columns += [provider_name]

        # Create a row for each attribute
        for attr in attr_docstrings:
            row = [attr.name]
            # anchor = qualifier_spec.all_members[attr.name].annotation.canonical_path
            # if anchor.startswith("kloppy."):
            #     row += [f"[`{attr.annotation}`][{anchor}]"]
            # else:
            row += [f"`{attr.annotation}`"]
            row += [attr.description]

            # Check if there is a record in the spec file for the attribute
            if attr.name in spec["attributes"]:
                attr_spec = spec["attributes"][attr.name]
                for (
                    provider_key,
                    provider_name,
                ) in _EVENT_DATA_PROVIDERS.items():
                    row += [render_provider_spec(attr_spec, provider_key)]
            else:
                for (
                    provider_key,
                    provider_name,
                ) in _EVENT_DATA_PROVIDERS.items():
                    row += ["-"]

            data += [row]

        # Get qualifier value type
        attr_docstrings = next(
            (d.value for d in value_docstring if d.kind.name == "attributes"),
            list(),
        )

        # Create a row for each attribute
        for attr in attr_docstrings:
            row = ["", attr.name]
            # anchor = value_spec.all_members[attr.name].annotation.canonical_path
            # if anchor.startswith("kloppy."):
            #     row += [f"[`{attr.annotation}`][{anchor}]"]
            # else:
            #     row += [f"`{attr.annotation}`"]
            row += [attr.description]

            # Check if there is a record in the spec file for the attribute
            if attr.name in spec["values"]:
                attr_spec = spec["values"][attr.name]
                for (
                    provider_key,
                    provider_name,
                ) in _EVENT_DATA_PROVIDERS.items():
                    row += [render_provider_spec(attr_spec, provider_key)]
            else:
                for (
                    provider_key,
                    provider_name,
                ) in _EVENT_DATA_PROVIDERS.items():
                    row += ["-"]

            data += [row]

        description = qualifier_docstring[0].value

        table = convert_to_md_table(
            pd.DataFrame(data, columns=columns), {"index": False}
        )

        return f"""
{render_provider_selectbox()}

<h2 id="{qualifier_type}" class="doc doc-heading">
    <code class="doc-symbol doc-symbol-heading doc-symbol-class"></code>
    <span class="doc doc-object-name doc-class-name">{qualifier_type}</span>
    <span class="doc doc-labels">
      <small class="doc doc-label doc-label-dataclass"><code>dataclass</code></small>
    </span>
</h2>

{description}

<p><span class="doc-section-title">Attributes</span></p>
{table}
"""

    @env.macro
    def plot_coordinate_systems(providers=None, cols=3):
        import math
        from io import StringIO

        import matplotlib.pyplot as plt
        from mplsoccer import Pitch

        from kloppy.domain import (
            DatasetType,
            Provider,
            VerticalOrientation,
            build_coordinate_system,
        )

        pitch_kwargs = {
            "line_color": "#94A7AE",
            "axis": False,
            "label": True,
            "pad_left": 0,
            "pad_right": 0,
            "pad_top": 0,
            "pad_bottom": 0,
            "linewidth": 1,
        }
        FONTCOLOR = "gray"
        font_kwargs = {
            "fontsize": 12,
            "ha": "center",
            "va": "bottom",
            "fontweight": "normal",
            "fontstyle": "italic",
            "c": FONTCOLOR,
        }

        if providers is None:
            providers = [
                {"provider": Provider.KLOPPY},
                {"provider": Provider.METRICA},
                {"provider": Provider.TRACAB},
                {"provider": Provider.SECONDSPECTRUM},
                {"provider": Provider.OPTA},
                {"provider": Provider.PFF},
                {"provider": Provider.SKILLCORNER},
                {"provider": Provider.STATSBOMB},
                {
                    "provider": Provider.SPORTEC,
                    "dataset_type": DatasetType.EVENT,
                },
                {
                    "provider": Provider.SPORTEC,
                    "dataset_type": DatasetType.TRACKING,
                },
                {"provider": Provider.WYSCOUT},
                {"provider": Provider.DATAFACTORY},
                # {"provider": Provider.STATSPERFORM},
                {"provider": Provider.HAWKEYE},
                {"provider": Provider.SPORTVU},
            ]
        else:
            providers = [
                {
                    "provider": Provider(item["provider"]),
                    "dataset_type": DatasetType(item["dataset_type"])
                    if "dataset_type" in item
                    else None,
                }
                for item in providers
            ]

        # Determine grid size
        n = len(providers)
        rows = math.ceil(n / cols)

        # Create subplots
        fig, axs = plt.subplots(rows, cols, figsize=(5 * cols, 4 * rows))
        axs = axs.flat  # Flatten for easy iteration

        for ax, provider in zip(axs, providers):
            coordinate_system = build_coordinate_system(
                provider=provider.get("provider"),
                dataset_type=provider.get("dataset_type", None),
                pitch_length=105,
                pitch_width=68,
            )

            pitch = Pitch(
                pitch_type=coordinate_system.to_mplsoccer(), **pitch_kwargs
            )
            pitch.draw(ax=ax)

            if provider.get("dataset_type"):
                ax.set_title(
                    f"{coordinate_system.provider.name}:{provider['dataset_type'].name}",
                    fontsize=18,
                    c="#000",
                    pad=15,
                )
            else:
                ax.set_title(
                    coordinate_system.provider.name,
                    fontsize=18,
                    c="#000",
                    pad=15,
                )

            xmin, xmax, ymin, ymax = pitch.extent
            ax.xaxis.set_ticks([xmin, xmax])
            ax.yaxis.set_ticks([ymin, ymax])
            ax.tick_params(labelsize=10)

            # Add red dot at origin
            origin_x, origin_y = 0, 0
            ax.plot(
                origin_x,
                origin_y,
                "ro",
                markersize=8,
                label="Origin",
                zorder=10,
                clip_on=False,
            )

            # Draw axis arrows
            x_axis_length = 0.1 * (
                coordinate_system.pitch_dimensions.x_dim.max
                - coordinate_system.pitch_dimensions.x_dim.min
            )
            y_axis_length = 0.1 * (
                coordinate_system.pitch_dimensions.y_dim.max
                - coordinate_system.pitch_dimensions.y_dim.min
            )
            ax.annotate(
                "",
                xy=(x_axis_length, 0),
                xytext=(0, 0),
                arrowprops=dict(facecolor="blue", arrowstyle="->"),
                annotation_clip=False,
            )
            ax.annotate(
                "",
                xy=(0, x_axis_length),
                xytext=(0, 0),
                arrowprops=dict(facecolor="green", arrowstyle="->"),
                annotation_clip=False,
            )

            ax.text(
                x_axis_length,
                0,
                "x",
                color="blue",
                fontsize=10,
                va="center",
                fontweight="bold",
                zorder=10,
            )
            if (
                coordinate_system.vertical_orientation
                == VerticalOrientation.BOTTOM_TO_TOP
            ):
                ax.text(
                    0,
                    x_axis_length,
                    "y",
                    color="green",
                    fontsize=10,
                    ha="center",
                    va="bottom",
                    fontweight="bold",
                    zorder=10,
                )
            else:
                ax.text(
                    0,
                    x_axis_length,
                    "y",
                    color="green",
                    fontsize=10,
                    ha="center",
                    va="top",
                    fontweight="bold",
                    zorder=10,
                )

            # Add unit and if standardized
            unit = (
                coordinate_system.pitch_dimensions.unit.name
            )  # e.g., "meters"
            standardized = (
                "yes"
                if coordinate_system.pitch_dimensions.standardized
                else "no"
            )

            ax.text(
                0.5,
                1.05,
                f"unit: {unit} • standardized: {standardized}",
                verticalalignment="bottom",
                horizontalalignment="center",
                transform=ax.transAxes,
                **font_kwargs,
            )

        for ax in axs[len(providers) :]:
            ax.set_visible(False)

        for o in fig.findobj():
            o.set_clip_on(False)

        plt.tight_layout()  # Adjust subplots to fit into the figure area.

        buffer = StringIO()
        plt.savefig(buffer, format="svg")
        return buffer.getvalue()
