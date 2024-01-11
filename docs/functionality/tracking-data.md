## Metrica

### load_tracking_csv
`kloppy.kloppy._providers.datafactory.load_tracking_csv(home_data, away_data, sample_rate=None, limit=None, coordinates=None)`

This function loads tracking data from CSV files into a `TrackingDataset`.

##### Parameters
- `home_data: FileLike`: This is the filename (or another file-like object) of the CSV file that contains the home team's tracking data.
- `away_data: FileLike`: This is the filename (or another file-like object) of the CSV file that contains the away team's tracking data.

##### Optional Parameters
- `sample_rate: Optional[float] = None`: The sample rate to be used when loading the tracking data. The default is `None`.
- `limit: Optional[int] = None`: The maximum number of tracking events to load from the file. The default is `None`, which means all tracking events will be loaded.
- `coordinates: Optional[str] = None`: The coordinate system to be used. The default is `None`. See [Coordinate Systems](../coordinate-systems/) for more information.

##### Returns
- `TrackingDataset`: An instance of the `TrackingDataset` class, filled with the loaded tracking data.

---

### load_tracking_epts
`kloppy.kloppy._providers.datafactory.load_tracking_epts(meta_data, raw_data, sample_rate=None, limit=None, coordinates=None)`

This function loads EPTS tracking data into a `TrackingDataset`.

##### Parameters
- `meta_data: FileLike`: The filename (or another file-like object) of the file that contains the meta data.
- `raw_data: FileLike`: The filename (or another file-like object) of the file that contains the raw tracking data.

##### Optional Parameters
- `sample_rate: Optional[float] = None`: The sample rate to be used when loading the tracking data. The default is `None`.
- `limit: Optional[int] = None`: The maximum number of tracking events to load from the file. The default is `None`, which means all tracking events will be loaded.
- `coordinates: Optional[str] = None`: The coordinate system to be used. The default is `None`.

##### Returns
- `TrackingDataset`: An instance of the `TrackingDataset` class, filled with the loaded tracking data.

---

### load_open_data
`kloppy.kloppy._providers.datafactory.load_open_data(match_id="1", sample_rate=None, limit=None, coordinates=None)`

This function loads open data for a specific match into a `TrackingDataset`.

##### Parameters
- `match_id: Union[str, int] = "1"`: The ID of the match to load. This can be 1, 2, or 3.

##### Optional Parameters
- `sample_rate: Optional[float] = None`: The sample rate to be used when loading the tracking data. The default is `None`.
- `limit: Optional[int] = None`: The maximum number of tracking events to load from the file. The default is `None`, which means all tracking events will be loaded.
- `coordinates: Optional[str] = None`: The coordinate system to be used. The default is `None`.

##### Returns
- `TrackingDataset`: An instance of the `TrackingDataset` class, filled with the loaded tracking data.

In the event that a non-supported `match_id` is provided, a `KloppyError` will be raised.

---

## SecondSpectrum

### load
`kloppy.kloppy._providers.secondspectrum.load(meta_data, raw_data, additional_meta_data, sample_rate, limit, coordinates, only_alive)`

This function loads Second Spectrum tracking data into a `TrackingDataset`.

##### Parameters
- `meta_data: FileLike`: The filename (or a file-like object) of the metadata file.
- `raw_data: FileLike`: The filename (or a file-like object) of the raw data file.

##### Optional Parameters
- `additional_meta_data: Optional[FileLike] = None`: An optional filename (or a file-like object) of additional metadata file.
- `sample_rate: Optional[float] = None`: An optional sampling rate for the tracking data. If not provided, all data points will be included. ie. `1/5` or `1/2`
- `limit: Optional[int] = None`: An optional limit on the number of data points to load. If not provided, all data points will be loaded.
- `coordinates: Optional[str] = None`: An optional coordinate system to use when loading the data. If not provided, the default coordinate system will be used.  See [Coordinate Systems](../coordinate-systems/) for more information.
- `only_alive: Optional[bool] = False`: If set to True, only the frames where the ball is in play ('alive') will be included.

##### Returns
- `TrackingDataset`: An instance of the `TrackingDataset` class, filled with the loaded Second Spectrum data.

Please consult the `TrackingDataset` documentation for more details on this class.

---

## SkillCorner

### load
`kloppy.kloppy._providers.skillcorner.load(meta_data, raw_data, sample_rate, limit, coordinates, include_empty_frames)`

This function loads SkillCorner tracking data into a `TrackingDataset`.

##### Parameters
- `meta_data: FileLike`: The filename (or a file-like object) of the metadata file.
- `raw_data: FileLike`: The filename (or a file-like object) of the raw data file.

##### Optional Parameters
- `sample_rate: Optional[float] = None`: An optional sampling rate for the tracking data. If not provided, all data points will be included. ie. `1/5` or `1/2`
- `limit: Optional[int] = None`: An optional limit on the number of data points to load. If not provided, all data points will be loaded.
- `coordinates: Optional[str] = None`: An optional coordinate system to use when loading the data. If not provided, the default coordinate system will be used.  See [Coordinate Systems](../coordinate-systems/) for more information.
- `include_empty_frames: Optional[bool] = False`: If set to True, frames with no data will be included in the dataset.

##### Returns
- `TrackingDataset`: An instance of the `TrackingDataset` class, filled with the loaded SkillCorner data.

Please consult the `TrackingDataset` documentation for more details on this class.

---

### load_open_data
`kloppy.kloppy._providers.skillcorner.load_open_data(match_id, sample_rate, limit, coordinates, include_empty_frames)`

This function loads SkillCorner tracking data for a specific match into a `TrackingDataset`.

##### Parameters
- `match_id: Union[str, int]`: The ID of the match to load data for.

##### Optional Parameters
- `sample_rate: Optional[float] = None`: An optional sampling rate for the tracking data. If not provided, all data points will be included.
- `limit: Optional[int] = None`: An optional limit on the number of data points to load. If not provided, all data points will be loaded.
- `coordinates: Optional[str] = None`: An optional coordinate system to use when loading the data. If not provided, the default coordinate system will be used.
- `include_empty_frames: Optional[bool] = False`: If set to True, frames with no data will be included in the dataset.

##### Returns
- `TrackingDataset`: An instance of the `TrackingDataset` class, filled with the loaded SkillCorner data.

Please consult the `TrackingDataset` documentation for more details on this class.

---

## StatsPerform

### load
`kloppy.kloppy._providers.statsperform.load(meta_data, raw_data, sample_rate, limit, coordinates, only_alive)`

This function loads StatsPerform tracking data into a `TrackingDataset`.

##### Parameters
- `meta_data: FileLike`: The filename (or a file-like object) of the metadata file. This corresponds to the StatsPerform MA1 file (XML format) which contains single game live data and lineups.
- `raw_data: FileLike`: The filename (or a file-like object) of the raw data file. This corresponds to the StatsPerform MA25 file (TXT format) which contains tracking data.

##### Optional Parameters
- `sample_rate: Optional[float] = None`: An optional sampling rate for the tracking data. If not provided, all data points will be included. For example, `1/5` or `1/2`.
- `limit: Optional[int] = None`: An optional limit on the number of data points to load. If not provided, all data points will be loaded.
- `coordinates: Optional[str] = None`: An optional coordinate system to use when loading the data. If not provided, the default coordinate system will be used.  See [Coordinate Systems](../coordinate-systems/) for more information.
- `only_alive: Optional[bool] = False`: If set to True, only the frames where the ball is in play ('alive') will be included.

##### Returns
- `TrackingDataset`: An instance of the `TrackingDataset` class, filled with the loaded StatsPerform data.

Please consult the `TrackingDataset` documentation for more details on this class.


---

## TRACAB

### load
`kloppy.kloppy._providers.tracab.load(meta_data, raw_data, sample_rate, limit, coordinates, only_alive)`

This function loads TRACAB tracking data into a `TrackingDataset`.

##### Parameters
- `meta_data: FileLike`: The filename (or a file-like object) of the metadata file.
- `raw_data: FileLike`: The filename (or a file-like object) of the raw data file.

##### Optional Parameters
- `sample_rate: Optional[float] = None`: An optional sampling rate for the tracking data. If not provided, all data points will be included. For example, `1/5` or `1/2`.
- `limit: Optional[int] = None`: An optional limit on the number of data points to load. If not provided, all data points will be loaded.
- `coordinates: Optional[str] = None`: An optional coordinate system to use when loading the data. If not provided, the default coordinate system will be used.  See [Coordinate Systems](../coordinate-systems/) for more information.
- `only_alive: Optional[bool] = True`: If set to True, only the frames where the ball is in play ('alive') will be included.

##### Returns
- `TrackingDataset`: An instance of the `TrackingDataset` class, filled with the loaded TRACAB data.

Please consult the `TrackingDataset` documentation for more details on this class.