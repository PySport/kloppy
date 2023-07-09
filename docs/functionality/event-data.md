## Supported Event Data Providers

- [DataFactory](#datafactory)
- [Metrica](#metrica)
- [Opta](#opta)
- [Sportec](#sportec)
- [SportsCode](#sportscode)
- [StatsBomb](#statsbomb)
- [WyScout](#wyscout)


### DataFactory

#### load
`kloppy.kloppy._providers.datafactory.load(event_data, event_types=None, coordinates=None, event_factory=None)`

This function loads DataFactory event data into an `EventDataset`.

##### Parameters
- `event_data: FileLike`: This should be the filename (or another file-like object) of the JSON file that contains the events to be loaded. This JSON file should follow the DataFactory's specific format.

##### Optional Parameters
- `event_types: Optional[List[str]] = None`: This is an optional parameter where you can specify a list of the types of events you're interested in. If this is `None`, then all event types in the data will be loaded.
- `coordinates: Optional[str] = None`: An optional parameter for specifying the coordinate system to be used. The default is `None`, which means the default coordinate system of the data will be used. 
- `event_factory: Optional[EventFactory] = None`: An optional `EventFactory` object that will be used to create the events. If this is `None`, then the default `EventFactory` specified in the configuration (via `get_config("event_factory")`) will be used.

##### Returns
- `EventDataset`: An instance of the `EventDataset` class, filled with the loaded events.

Please consult the `EventFactory` and `EventDataset` documentation for more details on these classes.

---

### Metrica

### load_event
`kloppy.kloppy._providers.datafactory.load_event(event_data, meta_data, event_types=None, coordinates=None, event_factory=None)`

This function loads event data into an `EventDataset`.

##### Parameters
- `event_data: FileLike`: The filename (or another file-like object) of the file that contains the event data.
- `meta_data: FileLike`: The filename (or another file-like object) of the file that contains the meta data.

##### Optional Parameters
- `event_types: Optional[List[str]] = None`: A list of the types of events to load. If `None`, all events will be loaded.
- `coordinates: Optional[str] = None`: An optional parameter for specifying the coordinate system to be used. The default is `None`, which means the default coordinate system of the data will be used. See [Coordinate Systems](../coordinate-systems/) for more information.
- `event_factory: Optional[EventFactory] = None`: An optional `EventFactory` object that will be used to create the events. If this is `None`, then the default `EventFactory` specified in the configuration (via `get_config("event_factory")`) will be used.

##### Returns
- `EventDataset`: An instance of the `EventDataset` class, filled with the loaded event data.

Please consult the `EventFactory` and `EventDataset` documentation for more details on these classes.

---

### Opta

### load
`kloppy.kloppy._providers.opta.load(f7_data, f24_data, event_types=None, coordinates=None, event_factory=None)`

This function loads Opta event data into an `EventDataset`.

##### Parameters
- `f7_data: FileLike`: The filename (or another file-like object) of the file that contains the F7 Opta events data.
- `f24_data: FileLike`: The filename (or another file-like object) of the file that contains the F24 Opta lineup information.

##### Optional Parameters
- `event_types: Optional[List[str]] = None`: A list of the types of events to load. If `None`, all events will be loaded.
- `coordinates: Optional[str] = None`: An optional parameter for specifying the coordinate system to be used. The default is `None`, which means the default coordinate system of the data will be used. See [Coordinate Systems](../coordinate-systems/) for more information.
- `event_factory: Optional[EventFactory] = None`: An optional `EventFactory` object that will be used to create the events. If this is `None`, then the default `EventFactory` specified in the configuration (via `get_config("event_factory")`) will be used.

##### Returns
- `EventDataset`: An instance of the `EventDataset` class, filled with the loaded event data.

Please consult the `EventFactory` and `EventDataset` documentation for more details on these classes.

---

### Sportec

### load
`kloppy.kloppy._providers.sportec.load(f7_data, f24_data, event_types=None, coordinates=None, event_factory=None)`

This function loads Opta event data into an `EventDataset`.

##### Parameters
- `event_data: FileLike`: The filename (or another file-like object) of the file that contains the events.
- `meta_data: FileLike`: The filename (or another file-like object) of the file that contains the match information.

##### Optional Parameters
- `event_types: Optional[List[str]] = None`: A list of the types of events to load. If `None`, all events will be loaded.
- `coordinates: Optional[str] = None`: An optional parameter for specifying the coordinate system to be used. The default is `None`, which means the default coordinate system of the data will be used. See [Coordinate Systems](../coordinate-systems/) for more information.
- `event_factory: Optional[EventFactory] = None`: An optional `EventFactory` object that will be used to create the events. If this is `None`, then the default `EventFactory` specified in the configuration (via `get_config("event_factory")`) will be used.

##### Returns
- `EventDataset`: An instance of the `EventDataset` class, filled with the loaded event data.

Please consult the `EventFactory` and `EventDataset` documentation for more details on these classes.

---

### Sportscode

---

### load
`kloppy.kloppy._providers.sportscode.load(data)`

This function loads SportsCode data into a `CodeDataset`.

##### Parameters
- `data: str`: The filename (or a file-like object) of the SportsCode data file to load.

##### Returns
- `CodeDataset`: An instance of the `CodeDataset` class, filled with the loaded SportsCode data.

Please consult the `CodeDataset` documentation for more details on these classes.

---

### save
`kloppy.kloppy._providers.sportscode.save(dataset, output_filename)`

This function saves a `CodeDataset` to a SportsCode data file.

##### Parameters
- `dataset: CodeDataset`: The `CodeDataset` instance to save.
- `output_filename: str`: The name of the file to save the dataset to. 

##### Returns
This function does not return any value.

Note: The data is written in binary mode to the specified file.

Please consult the `CodeDataset` documentation for more details on this class.

---

### StatsBomb

### load
`kloppy.kloppy._providers.statsbomb.load(event_data, lineup_data, three_sixty_data=None, event_types=None, coordinates=None, event_factory=None)`

This function loads StatsBomb event data into an `EventDataset`.

##### Parameters
- `event_data: FileLike`: The filename (or another file-like object) of the file containing the events.
- `lineup_data: FileLike`: The filename (or another file-like object) of the file containing the lineup information.

##### Optional Parameters
- `three_sixty_data: Optional[FileLike] = None`: The filename (or another file-like object) of the file containing the 360 data. If this is not provided, the function will still run, but without the 360 data.
- `event_types: Optional[List[str]] = None`: A list of the types of events to load. If `None`, all events will be loaded.
- `coordinates: Optional[str] = None`: The coordinate system to be used. The default is `None`. See [Coordinate Systems](../coordinate-systems/) for more information.
- `event_factory: Optional[EventFactory] = None`: The `EventFactory` that will be used to create the events. If `None`, the default `EventFactory` will be used.

##### Returns
- `EventDataset`: An instance of the `EventDataset` class, filled with the loaded event data.

---

### load_open_data
`kloppy.kloppy._providers.statsbomb.load_open_data(match_id='15946', event_types=None, coordinates=None, event_factory=None)`

This function loads StatsBomb public data into an `EventDataset`.

##### Parameters
- `match_id: Union[str, int] = '15946'`: The ID of the match to be loaded.

##### Optional Parameters
- `event_types: Optional[List[str]] = None`: A list of the types of events to load. If `None`, all events will be loaded.
- `coordinates: Optional[str] = None`: The coordinate system to be used. The default is `None`. See [Coordinate Systems](../coordinate-systems/) for more information.
- `event_factory: Optional[EventFactory] = None`: The `EventFactory` that will be used to create the events. If `None`, the default `EventFactory` will be used.

##### Returns
- `EventDataset`: An instance of the `EventDataset` class, filled with the loaded event data.

Please consult the `EventFactory` and `EventDataset` documentation for more details on these classes.

##### Note
By using this function, you agree to the StatsBomb public data user agreement, which can be found [here](https://github.com/statsbomb/open-data/blob/master/LICENSE.pdf).

---

### WyScout

### load
`kloppy.kloppy._providers.wyscout.load(event_data, event_types=None, coordinates=None, event_factory=None, data_version=None)`

This function loads Wyscout event data into an `EventDataset`.

##### Parameters
- `event_data: FileLike`: The filename (or another file-like object) of the XML file containing the events and metadata.

##### Optional Parameters
- `event_types: Optional[List[str]] = None`: A list of the types of events to load. If `None`, all events will be loaded.
- `coordinates: Optional[str] = None`: The coordinate system to be used. The default is `None`. See [Coordinate Systems](../coordinate-systems/) for more information.
- `event_factory: Optional[EventFactory] = None`: The `EventFactory` that will be used to create the events. If `None`, the default `EventFactory` will be used.
- `data_version: Optional[str] = None`: The version of the data to load. If `None`, the deserializer will be automatically identified.

##### Returns
- `EventDataset`: An instance of the `EventDataset` class, filled with the loaded event data.

---

### load_open_data
`kloppy.kloppy._providers.wyscout.load_open_data(match_id='2499841', event_types=None, coordinates=None, event_factory=None)`

This function loads Wyscout open data into an `EventDataset`.

##### Parameters
- `match_id: Union[str, int] = '2499841'`: The ID of the match to be loaded.

##### Optional Parameters
- `event_types: Optional[List[str]] = None`: A list of the types of events to load. If `None`, all events will be loaded.
- `coordinates: Optional[str] = None`: The coordinate system to be used. The default is `None`. See [Coordinate Systems](../coordinate-systems/) for more information.
- `event_factory: Optional[EventFactory] = None`: The `EventFactory` that will be used to create the events. If `None`, the default `EventFactory` will be used.

##### Returns
- `EventDataset`: An instance of the `EventDataset` class, filled with the loaded event data.

Please consult the `EventFactory` and `EventDataset` documentation for more details on these classes.

