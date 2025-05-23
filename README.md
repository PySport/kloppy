<a href='https://kloppy.pysport.org'><img style="width: 120px; height: 139px" src="https://github.com/PySport/kloppy/raw/master/docs/assets/logo.png" align="right" /></a>
> klop·pen (klopte, heeft geklopt) - juist zijn; overeenkomen, uitkomen met: *dat klopt, dat kan kloppen* is juist; *dat klopt als een zwerende vinger* dat is helemaal juist

[![PyPI Latest Release](https://img.shields.io/pypi/v/kloppy.svg)](https://pypi.org/project/kloppy/)
[![Downloads](https://pepy.tech/badge/kloppy/month)](https://pepy.tech/project/kloppy/month)
![](https://img.shields.io/github/license/PySport/kloppy)
![](https://img.shields.io/pypi/pyversions/kloppy)
[![Powered by PySport](https://img.shields.io/badge/powered%20by-PySport-orange.svg?style=flat&colorA=104467&colorB=007D8A)](https://pysport.org)

# Soccer Data Processing, *Simplified*

Each data provider uses its own proprietary formats, event definitions, and coordinate system to capture soccer match data. This **lack of standardization** makes it difficult to build software or perform analysis across multiple providers. Kloppy solves this challenge by introducing a **vendor-independent data model** for both **event and tracking data**. It also streamlines data preprocessing, ensuring **seamless integration into your data analysis and video analysis workflows**. By standardizing and simplifying access to soccer match data, kloppy aims to be an essential building block for anyone working with soccer data.

## Table of Contents

- [Supported data providers](#supported-data-providers)
- [Main features](#main-features)
- [Where to get it](#where-to-get-it)
- [Documentation](#documentation)
- [Contributing to kloppy](#contributing-to-kloppy)
- [License](#license)

## Supported data providers
Kloppy provides support for loading data from the following providers:

| Provider            | Event Data | Tracking Data | Public Data  | Docs  | Notes |
|---------------------|:----------:|:-------------:|:------------:|:-----:|:-----|
| [DataFactory][datafactory]         | ✓          |               |               | [↗][datafactory-doc] |  |
| [Hawkeye (2D)][hawkeye]        |            | ✓             |               | [↗][hawkeye-doc] | Joint tracking data is not yet supported |
| [Metrica][metrica]             | ✓          | ✓             | [↗][metrica-data] | [↗][metrica-doc] | |
| [PFF][pff]                 | ⧗          | ✓             | [↗][pff-data]     | [↗][pff-doc]     | |
| [SecondSpectrum][ss]      | [⧗][ss-pr] | ✓      |               | [↗][ss-doc]       | |
| [Signality][signality]           |            | ✓             |               | [↗][signality-doc] |  |
| [SkillCorner][skillcorner]         |            | ✓             | [↗][skillcorner-data] | [↗][skillcorner-doc] | |
| [Sportec][sportec]             | ✓          | ✓             | [↗][sportec-data] | [↗][sportec-doc] | |
| [StatsBomb][statsbomb]           | ✓         |               | [↗][statsbomb-data] | [↗][statsbomb-doc] | Includes 360 freeze frame data support |
| [Stats Perform][statsperform] | ✓          | ✓             |               | [↗][statsperform-doc] | Includes support for MA1, MA3, and MA25 data feeds |
| [Opta][opta] | ✓          |               |               | [↗][opta-doc] | Includes support for F7, F24 and F73 XML data feeds |
| [Tracab][tracab]              |            | ✓             |               | [↗][tracab-doc] |  |
| [Wyscout][wyscout]             | ✓          |               | [↗][wyscout-data] | [↗][wyscout-doc] | Includes support for v2 and v3 data |

[datafactory]: https://www.datafactory.la/en/
[datafactory-doc]: https://kloppy.pysport.org/user-guide/loading-data/datafactory
[hawkeye]: https://www.hawkeyeinnovations.com/data
[hawkeye-doc]: https://kloppy.pysport.org/user-guide/loading-data/hawkeye
[metrica]: https://www.metrica-sports.com/
[metrica-data]: https://github.com/metrica-sports/sample-data  
[metrica-doc]: https://kloppy.pysport.org/user-guide/loading-data/metrica
[pff]: https://fc.pff.com/
[pff-data]: https://drive.google.com/drive/u/0/folders/1_a_q1e9CXeEPJ3GdCv_3-rNO3gPqacfa  
[pff-doc]: https://kloppy.pysport.org/user-guide/loading-data/pff
[signality]: https://www.spiideo.com/
[signality-doc]: https://kloppy.pysport.org/user-guide/loading-data/signality
[skillcorner]: https://skillcorner.com/
[skillcorner-data]: https://github.com/SkillCorner/opendata  
[skillcorner-doc]: https://kloppy.pysport.org/user-guide/loading-data/skillcorner
[sportec]: https://sportec-solutions.de/en/index.html
[sportec-data]: https://www.nature.com/articles/s41597-025-04505-y  
[sportec-doc]: https://kloppy.pysport.org/user-guide/loading-data/sportec
[ss]: https://www.geniussports.com/
[ss-doc]: https://kloppy.pysport.org/user-guide/loading-data/secondspectrum
[ss-pr]: https://github.com/PySport/kloppy/pull/437  
[statsbomb]: https://statsbomb.com/
[statsbomb-data]: https://github.com/statsbomb/open-data  
[statsbomb-doc]: https://kloppy.pysport.org/user-guide/loading-data/statsbomb
[statsperform]: https://www.statsperform.com/
[statsperform-doc]: user-guide/loading-data/statsperform
[opta]: https://www.statsperform.com/opta/
[opta-doc]: user-guide/loading-data/opta
[tracab]: https://tracab.com/products/tracab-technologies/
[tracab-doc]: https://kloppy.pysport.org/user-guide/loading-data/tracab
[wyscout]: https://www.hudl.com/en_gb/products/wyscout
[wyscout-data]: https://github.com/koenvo/wyscout-soccer-match-event-dataset  
[wyscout-doc]: https://kloppy.pysport.org/user-guide/loading-data/wyscout

✓ Implemented &nbsp;&nbsp;  ⧗ In progress or partial support

## Main features

Here are just a few of the things that kloppy does well.

#### 🗄️ Loading data
Kloppy implements a **standardized data model** that can load event and tracking data from the **most common data providers**, supporting both public and proprietary data. Moreover, it does not matter where or how the data is stored: kloppy can handle **compressed files** and load data directly from **the cloud**.

```python
from kloppy import sportec

dataset = sportec.load_open_event_data(match_id="J03WMX")
```

#### 🔍 Querying data 

Video analysts spend a lot of time searching for bespoke moments. Often, these moments follow recognizable patterns—like pass, pass, shot. Kloppy provides a **powerful search mechanism** based on regular expressions, enabling you to find these bespoke moments more quickly and easily.

```python
goals = dataset.filter("shot.goal")
```

#### 🔄 Transforming data 
Different data providers use different coordinate systems, which can make combining datasets challenging. Additionally, it can be convenient to change the orientation of the data or normalize pitch dimensions for specific analyses. Kloppy handles these **data transformations** seamlessly.

```python
goals_ltr = goals.transform(
    to_coordinate_system="opta",
    to_orientation="ACTION_EXECUTING_TEAM"
)
```

#### 💾 Exporting data
Once your data is in the right shape, export it as **a Polars or Pandas dataframe** for efficient analysis, or as **SportsCode XML** to support your video analysis workflow. Kloppy's data model is also **compatible with other popular soccer analytics libraries**.

```python
df_goals = goals_ltr.to_df(
  "player", 
  "coordinates_*", 
  assist=lambda event: event.prev("pass"),
  engine="polars"
)
```

## Where to get it

The source code is hosted on GitHub at: [https://github.com/PySport/kloppy](https://github.com/PySport/kloppy).

The easiest way to install kloppy is via **pip**:

```bash
pip install kloppy
```

You can also install from GitHub for the latest updates:

```sh
pip install git+https://github.com/PySport/kloppy.git
```

For more details, refer to the [installation guide](https://kloppy.pysport.org/getting-started/installation/).

## Documentation

The official documentation is hosted at [https://kloppy.pysport.org](https://kloppy.pysport.org). 

## Contributing to kloppy
Kloppy can only exist because of a passionate and dedicated open-source community. All contributions, bug reports, bug fixes, documentation improvements, enhancements, and ideas are welcome. An overview on how to contribute can be found in the **[contributing guide](https://kloppy.pysport.org/contributing)**.

<a href="https://github.com/PySport/kloppy/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=PySport/kloppy" />
</a>

Made with [contrib.rocks](https://contrib.rocks).

## Sponsors

Kloppy is powered by **[PySport](https://pysport.org/)** (non-profit, RSIN: 866294211). Consider [contributing](#contributing-to-kloppy) or [donating](https://pysport.org/) to ensure its longevity!

## License

Kloppy is distributed under the terms of the [BSD 3 license](LICENSE).
