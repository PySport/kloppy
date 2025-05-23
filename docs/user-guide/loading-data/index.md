# Loading data

The first step in any data processing workflow is acquiring the data itself. Kloppy supports loading event data, tracking data, and manually tagged code data from the most common data providers. The parsing might work slightly different depending on the provider but in essence, each provider has its own submodule, and each datatype has a corresponding loading function. Below is a quick example of how to load locally-stored event data from StatsBomb to illustrate the general approach.

```python
from kloppy import statsbomb

dataset = statsbomb.load(
    event_data="./match_3788741/events.json",
    lineup_data="./match_3788741/lineups.json",
)
```

The remainder of this guide explains how to adapt this code depending on [the data provider](#supported-data-providers) and [the data storage](#supported-data-storage). Furthermore, we give an overview of [options available](#data-loading-options) while loading the data.

## Supported data providers

Below is an overview of all currently supported providers, along with links to detailed guides on how to load data for each one. Some providers have also made a sample of their data publicly available.

| Provider                                   |                                Event Data                                |  Tracking Data   |    Code Data     |                                          Public Data                                           |
| :----------------------------------------- | :----------------------------------------------------------------------: | :--------------: | :--------------: | :--------------------------------------------------------------------------------------------: |
| [DataFactory](datafactory.ipynb)           |                             :material-check:                             | :material-minus: | :material-minus: |                                                                                                |
| [HawkEye (2D)](hawkeye.ipynb)              |                             :material-minus:                             | :material-check: | :material-minus: |                                                                                                |
| [Metrica](metrica.ipynb)                   |                             :material-minus:                             | :material-check: | :material-minus: |                [:material-eye:](https://github.com/metrica-sports/sample-data)                 |
| [PFF FC](pff.ipynb)                        |                             :material-minus:                             | :material-check: | :material-minus: | [:material-eye:](https://drive.google.com/drive/u/0/folders/1_a_q1e9CXeEPJ3GdCv_3-rNO3gPqacfa) |
| [SecondSpectrum](secondspectrum.ipynb)     | [:material-progress-wrench:](https://github.com/PySport/kloppy/pull/437) | :material-check: | :material-minus: |
| [Signality](signality.ipynb)               |                             :material-minus:                             | :material-check: | :material-minus: |                                                                                                |
| [SkillCorner](skillcorner.ipynb)           |                             :material-minus:                             | :material-check: | :material-minus: |                   [:material-eye:](https://github.com/SkillCorner/opendata)                    |
| [Sportec](sportec.ipynb)                   |                             :material-check:                             | :material-check: | :material-minus: |              [:material-eye:](https://www.nature.com/articles/s41597-025-04505-y)              |
| [Hudl SportsCode](sportscode.ipynb)        |                             :material-minus:                             | :material-minus: | :material-check: |                                                                                                |
| [Hudl StatsBomb](statsbomb.ipynb)          |                             :material-check:                             | :material-minus: | :material-minus: |                    [:material-eye:](https://github.com/statsbomb/open-data)                    |
| [Stats Perform / Opta](statsperform.ipynb) |                             :material-check:                             | :material-check: | :material-minus: |                                                                                                |
| [TRACAB (CyronHego)](tracab.ipynb)         |                             :material-minus:                             | :material-check: | :material-minus: |                                                                                                |
| [WyScout](wyscout.ipynb)                   |                             :material-check:                             | :material-minus: | :material-minus: |              [:material-eye:](https://www.nature.com/articles/s41597-019-0247-7)               |

## Supported data storage

With kloppy, it doesn't really matter where and how the data is stored. Kloppy can transparently load data from local files, the web, and Amazon S3. Additionally, you can extend its functionality by creating [custom adapters](../../examples/adapter.ipynb) to load data from other data sources as needed.

### Local input data

The most straightforward option is load the data from files that are stored on your local filesystem. To do so, you must pass a string or `pathlib.Path` object representing a local file path.

```python
from pathlib import Path
from kloppy import statsbomb

dataset = statsbomb.load(
    event_data=Path("./match_3788741/events.json"),
    lineup_data=Path("./match_3788741/lineups.json"),
)
```

This assumes that you have the data stored locally in your current working directory in a folder called `match_3788741`.

!!! todo

    Some data loaders accept a list of input files.

Alternatively, you can also provide a binary stream.

```python
from pathlib import Path
from kloppy import statsbomb

dataset = statsbomb.load(
    event_data=Path("./match_3788741/events.json").open("rb"),
    lineup_data=Path("./match_3788741/lineups.json").open("rb"),
)
```

And if the input is JSON or XML, you can even directly provide the data as a string.

```python
from pathlib import Path
from kloppy import statsbomb

dataset = statsbomb.load(
    event_data='[{"id": ...}]':,
    lineup_data='[{"team_id" : 217,...}]',
)
```

### External input data

Kloppy uses adapters to load data from external sources. Currently, kloppy is shipped with support for `http` and `s3`, but you can [add your own adapters](../../examples/adapter.ipynb) to support other external sources.

#### HTTP

To load data from a web server, you must provide a string representing a URL. It should start with 'http://' or 'https://'.

```python
from kloppy import statsbomb

dataset = statsbomb.load(
    event_data=Path("http://someurl.com/match_3788741/events.json"),
    lineup_data=Path("htpps://someurl.com/match_3788741/lineups.json"),
)
```

You can pass credentials for authentication via [`set_config`][kloppy.config.set_config].

```python
from kloppy import statsbomb
from kloppy.config import set_config

set_config(
    'adapters.http.basic_authentication',
    { 'user': 'JohnDoe', 'pass': 'asecretkey' }
)

dataset = statsbomb.load(
    event_data="http://someurl.com/match_3788741/events.json",
    lineup_data="htpps://someurl.com/match_3788741/lineups.json",
)
```

#### S3

To load data from Amazon S3, you must provide a string representing a path to a file in an Amazon S3 cloud storage bucket. It should start with 's3://'.

```python
from kloppy import statsbomb

dataset = statsbomb.load(
    event_data="s3://some-bucket/match_3788741/events.json",
    lineup_data="s3://some-bucket/match_3788741/lineups.json",
)
```

To make this work, you'll most likely have to set up authentication. The most secure way to do this is via [boto environment variables](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html#using-environment-variables). Alternatively, if preferred, you can create a [`s3fs.S3FileSystem`](https://s3fs.readthedocs.io/en/latest/api.html#s3fs.core.S3FileSystem) instance and pass it via [`set_config`][kloppy.config.set_config].

```python
import s3fs

from kloppy import statsbomb
from kloppy.config import set_config

set_config(
    'adapters.s3.s3fs',
    s3fs.S3FileSystem(
      key='s3key...',
      secret='asecretkey...',
    )
)

dataset = statsbomb.load(
    event_data='s3://some-bucket/match_3788741/events.json',
    lineup_data='s3://some-bucket/match_3788741/lineups.json'
)
```

### Compressed input data

Compressing the raw data can reduce their file sizes enormously, effectively reducing the data's storage cost. To support this, kloppy can transparently parse compressed files. If the given file path or URL ends with '.gz', '.xz', or '.bz2', the file will be decompressed before being read. This works for all data sources, but below we illustrate it for locally stored data.

```python
from kloppy import statsbomb

dataset = statsbomb.load(
    event_data="./events/3788741.json.gz",
    lineup_data="./lineups/3788741.json.gz",
)
```

## Data loading options

All data loaders support a number of common options to configure how the data should be parsed. This section gives an overview of these common options. Furthermore, specific data loaders might accept additional options. For these, we refer to [the provider-specific guides](#supported-data-providers).

### General

The following options are supported by both event data and tracking data loaders.

#### `coordinates`

By default, kloppy will parse all data to the [`KloppyCoordinateSystem`][kloppy.domain.KloppyCoordinateSystem], which uses normalized pitch dimensions in the range \[0, 1\]. By providing the `coordinates` option, you can parse the data to the coordinate system of any other data provider. This parameter accepts a [`Provider`][kloppy.domain.Provider] value or a provider's name.

```python
from kloppy import statsbomb
from kloppy.domain import Provider

dataset = statsbomb.load(
    event_data="./events/3788741.json.gz",
    lineup_data="./lineups/3788741.json.gz",
    coordinates=Provider.StatsBomb
    # or: coordinates="statsbomb"
)
```

#### `additional_metadata`

You might have additional metadata about a match that is not included in the raw data. You can still add this data to the loaded dataset's metadat trough the `additional_metadat` parameter. This parameter accepts a dictionary with additional data. The dictionary's keys must correspond to attributes of the [`Metadata`][kloppy.domain.Metadata] entity.

```python
from kloppy import statsbomb
from kloppy.domain import Provider

dataset = statsbomb.load(
    event_data="./events/3788741.json.gz",
    lineup_data="./lineups/3788741.json.gz",
    additional_metadata={
        "date": datetime(2020, 8, 23, 0, 0, tzinfo=timezone.utc),
        "game_week": "7",
        "game_id": "3888787",
    }
)
```

### Event data

The following options are only supported by event data loaders.

#### `event_types`

Through the `event_types` parameter you can limit the event types that should be loaded. You can pass a list of [`EventType`][kloppy.domain.EventType] values or a list of event type names.

```python
from kloppy import statsbomb
from kloppy.domain import EventType

dataset = statsbomb.load(
    event_data="./events/3788741.json.gz",
    lineup_data="./lineups/3788741.json.gz",
    event_types=[EventType.Pass, EventType.Shot]
    # or: event_types=["pass", "shot"]
)
```

#### `event_factory`

In some cases, you might want to use certain data is not included in kloppy's data model. This is supported through the `event_factory` parameter. You can define your own customized subclasses of [`Event`][kloppy.domain.Event] that can store the additional data and then implement a [`EventFactory`][kloppy.domain.EventFactory] to parse the data. Below, we illustrate this by parsing StatsBomb's xG values.

```python
from dataclasses import dataclass

from kloppy.domain import EventFactory, create_event, ShotEvent
from kloppy import statsbomb


@dataclass(repr=False)
class StatsBombShotEvent(ShotEvent):
    statsbomb_xg: float = None


class StatsBombEventFactory(EventFactory):
    def build_shot(self, **kwargs) -> ShotEvent:
        kwargs['statsbomb_xg'] = kwargs['raw_event']['shot']['statsbomb_xg']
        return create_event(StatsBombShotEvent, **kwargs)

dataset = statsbomb.load(
    event_data="./events/3788741.json.gz",
    lineup_data="./lineups/3788741.json.gz",
    event_factory=StatsBombEventFactory()
)
```

### Tracking data

The following options are only supported by tracking data loaders.

#### `pitch_length` and `pitch_width`

Some tracking data providers do not record the length and width of the pitch. Yet, this information is important to be able to determine when the ball is out of bounds and to be able to rescale the pitch dimensions. If the pitch length and width are not provided, kloppy will assume default pitch dimensions of 105x68 meter.

```python
from kloppy import statsperform

dataset = statsperform.load_tracking(
    ma1_data="./statsperform_tracking_ma1.json",
    ma25_data="./statsperform_tracking_ma25.txt",
    pitch_length=102.5,
    pitch_width=69.0,
)
```

#### `sample_rate`

The `sample_rate` allows you to downsample the data, reducing the size of the dataset. For example, if the original data is recorded at 20Hz, the data will be loaded at 10Hz with `sample_rate=0.5` and at 5Hz with `sample_rate=0.25`. Upsampling is not supported.

```python
from kloppy import statsperform

dataset = statsperform.load_tracking(
    ma1_data="./statsperform_tracking_ma1.json",
    ma25_data="./statsperform_tracking_ma25.txt",
    sample_rate=0.5,
)
```

#### `limit`

With the `limit` parameter, you can limit the number of frames to load to the first `n` frames. This is mainly useful to testing a parser as loading a full game of tracking data can take some time.

```python
from kloppy import statsperform

dataset = statsperform.load_tracking(
    ma1_data="./statsperform_tracking_ma1.json",
    ma25_data="./statsperform_tracking_ma25.txt",
    limit=50,
)
```

#### `only_alive`

By setting the `only_alive` parameter to `True`, only frames in which the game is not paused will be included.

```python
from kloppy import statsperform

dataset = statsperform.load_tracking(
    ma1_data="./statsperform_tracking_ma1.json",
    ma25_data="./statsperform_tracking_ma25.txt",
    only_alive=True,
)
```
