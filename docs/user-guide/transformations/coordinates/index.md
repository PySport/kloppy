# Dataset transformations

Kloppy's [`.transform()`][kloppy.domain.Dataset.transform] method allows you to adapt the [spatial representation](../../concepts/coordinates/index.md) of a dataset. This can be useful if you need to align data from different providers or to run analyses that assume a standard pitch size or attacking direction.

```python
dataset.transform(
    to_orientation: Optional[Orientation | str] = None,
    to_pitch_dimensions: Optional[PitchDimensions] = None,
    to_coordinate_system: Optional[CoordinateSystem | Provider | str] = None
)
```

Each argument targets a specific spatial aspect.

## Transforming the orientation

In soccer, the direction of play changes between halves. This can be inconvenient when analyzing the data. For example, when creating a heatmap you want the data to be aligned such that all players are attacking in the same direction during the entire game. To enable such analysis, kloppy provides a set of orientation modes to change the dataset's orientation. The example below changes the orientation such that the home team plays from left-to-right in the first half, switching at halftime.

```python
from kloppy.domain import Orientation

ds = dataset.transform(
    to_orientation=Orientation.HOME_AWAY
)
```

The `to_orientation` argument accepts both an [`Orientation`][kloppy.domain.Orientation] (e.g., `Orientation.HOME_AWAY`) and an orientation mode's name (e.g., `"home-away"`).

#### Supported orientations

The following orientation modes are supported:

| Orientation             | Description                                                                                                                                     |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `home-away`             | The home team plays from left to right in the first period. The away team plays from left to right in the second period.                        |
| `away-home`             | The away team plays from left to right in the first period. The home team plays from left to right in the second period.                        |
| `static-home-away`      | The home team plays from left to right in both periods.                                                                                         |
| `static-away-home`      | The away team plays from left to right in both periods.                                                                                         |
| `action-executing-team` | The team that executes the action plays from left to right. Used in event stream data only. Equivalent to "ball-owning-team" for tracking data. |
| `ball-owning-team`      | The team that is currently in possession of the ball plays from left to right.                                                                  |

#### When to use each orientation

- Use `home-away` or `away-home` when you want to reflect the game's actual direction of play. This is useful when comparing with video.
- Use `static-home-away` or `static-away-home` for building visualizations or running analysis where each team attacks in the same direction across both halves.
- Use `ball-owning-team` or `action-executing-team` when analyzing movements or events in a consistent attacking direction for both teams.

## Transforming the pitch dimensions

Soccer datasets often come with varying pitch dimensions depending on the provider or stadium in which the game was played. To ensure consistency across matches, generating visualizations, or feeding data into models—it’s important to normalize the pitch dimensions. The example below illustrates how the data can be rescaled to a standardized pitch that is 105 meters long and 68 meters wide, which is a commonly used standard (e.g., in UEFA competitions).

```python
from kloppy.domain import Dimension, MetricPitchDimensions

ds = dataset.transform(
    to_pitch_dimensions=MetricPitchDimensions(
        standardized=True,
        x_dim=Dimension(min=0, max=105),
        y_dim=Dimension(min=0, max=68),
    )
)
```

#### Supported pitch dimensions

Kloppy defines a couple of common pitch configurations:

- [`MetricPitchDimensions`][kloppy.domain.MetricPitchDimensions]: The standard pitch dimensions in meters by [IFAB regulations](https://www.theifab.com/laws/latest/the-field-of-play). The length of the pitch can be between 90 and 120 meters, and the width can be between 45 and 90 meters. All other dimensions are fixed.
- [`ImperialPitchDimensions`][kloppy.domain.ImperialPitchDimensions]: The same standard pitch dimensions by [IFAB regulations](https://www.theifab.com/laws/latest/the-field-of-play) but in yards.
- [`NormalizedPitchDimensions`][kloppy.domain.NormalizedPitchDimensions]: The pitch dimensions are normalized to a unit square, where the length and width of the pitch are 1. All other dimensions are scaled accordingly from the `MetricPitchDimensions` based on the `pitch_length` and `pitch_width`. For example, for a pitch of 70m wide, the goal will be 7.32 / 70 = 0.1046 units wide.
- [`OptaPitchDimensions`][kloppy.domain.OptaPitchDimensions]: The standardized pitch dimensions used by Opta.
- [`WyscoutPitchDimensions`][kloppy.domain.WyscoutPitchDimensions]: The standardized pitch dimensions used by Wyscout.

|                           | [`MetricPitchDimensions`][kloppy.domain.MetricPitchDimensions] | [`ImperialPitchDimensions`][kloppy.domain.ImperialPitchDimensions] | [`NormalizedPitchDimensions`][kloppy.domain.NormalizedPitchDimensions] | [`OptaPitchDimensions`][kloppy.domain.OptaPitchDimensions] | [`WyscoutPitchDimensions`][kloppy.domain.WyscoutPitchDimensions] |
| ------------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------ | ---------------------------------------------------------------------- | ---------------------------------------------------------- | ---------------------------------------------------------------- |
| **Length**                | 90-120 m                                                       | 100-130 yd                                                         | 1 unit                                                                 | 100 units                                                  | 100 units                                                        |
| **Width**                 | 45-90 m                                                        | 50-100 yd                                                          | 1 unit                                                                 | 100 units                                                  | 100 units                                                        |
| **Goal Width**            | 7.32 m                                                         | 8 yd                                                               | -                                                                      | 9.6 units                                                  | 12.0 units                                                       |
| **Goal Area (Width)**     | 18.32 m                                                        | 20 yd                                                              | -                                                                      | 26.4 units                                                 | 26.0 units                                                       |
| **Goal Area (Length)**    | 5.5 m                                                          | 6 yd                                                               | -                                                                      | 5.8 units                                                  | 6.0 units                                                        |
| **Penalty Area (Width)**  | 40.32 m                                                        | 44.1 yd                                                            | -                                                                      | 57.8 units                                                 | 62.0 units                                                       |
| **Penalty Area (Length)** | 16.5 m                                                         | 18 yd                                                              | -                                                                      | 17.0 units                                                 | 16.0 units                                                       |
| **Center Circle Radius**  | 9.15 m                                                         | 10 yd                                                              | -                                                                      | 9.0 units                                                  | 8.84 units                                                       |

You can also define custom pitch dimensions. This is explained [here](../../concepts/coordinates/index.md#pitchdimensions).

#### When to use each pitch dimension

Choosing the right pitch dimension type depends on two main considerations:

1. Do you want to preserve real-world measurements (in meters/yards) or normalize to a unit scale?
2. Should the pitch be standardized to a common format, or should it reflect the original stadium-specific size?

Here’s how to decide:

##### Metric/Imperial vs. Normalized

- With **metric/imperial** pitch dimensions, coordinates are expressed in meters/yards, which match real-world distances. This is ideal for physical analysis (e.g., distance covered, sprinting speed) and visualization.
- With **normalized** pitch dimensions, the pitch is scaled to a unit square (1×1). Use this when the absolute pitch size doesn’t matter. This is especially useful for machine learning models that expect fixed input ranges or when performing and analysis that depend on zones of the pitch that scale with the pitch size (e.g., the first, middle and final third).

##### Standardized vs. Non-standardized

- Use **standardized pitch dimensions** when you want to bring multiple datasets to a consistent size for comparison, visualization, or modeling. This is especially important in cross-match or cross-provider analysis, where pitch sizes vary.
- Use **non-standardized pitch dimensions** when you want to retain the original dimensions of each dataset, reflecting the exact field size used in that match.

#### How it works

The transformation scales all x and y coordinates proportionally such that the relevant position to the pitch markings are maintained. So, if a shot is half-way between the penalty spot and the penalty-area box, it stays that way after conversion. For a detailed explanation, see the [mplsoccer docs](https://mplsoccer.readthedocs.io/en/latest/gallery/pitch_plots/plot_standardize.html).

## Transforming the coordinate system

To directly compare or merge datasets from different providers, they should be aligned to a common coordinate system. This goes beyond changing the pitch dimensions. In kloppy, a coordinate system defines the location of the origin, the orientation of the y-axis and the pitch dimensions. This is explained in detail [here](../../concepts/coordinates/index.md).

The example below illustrates how to convert a dataset to Tracab's default coordinate system.

```python
from kloppy.domain import Provider

ds = dataset.transform(to_coordinate_system=Provider.TRACAB)
```

The `to_coordinate_system` argument accepts a [`Provider`][kloppy.domain.Provider] (e.g., `Provider.TRACAB`), a provider's name (e.g., `"tracab"`) or a coordinate system (e.g., `TracabCoordinateSystem(pitch_length=108, pitch_width=69)`).

!!! note

    You **cannot** use `to_pitch_dimensions` and `to_coordinate_system` together in a single call.

    - Use `to_coordinate_system` when aligning coordinate systems across providers.
    - Use `to_pitch_dimensions` when normalizing the physical scale of the pitch.
