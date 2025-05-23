# Exporting Data

Kloppy allows you to export datasets into various formats, making it easy to integrate kloppy with the broader Python data analysis and sports analytics ecosystem.

## Built-in export options

- [Pandas / Polars](./dataframes.md): Convert datasets to a Pandas or Polars DataFrame for powerful data manipulation, analysis, and export to common formats like CSV, Excel, and Parquet.
- [Sportscode](./sportscode.md): Export data to Hudl Sportscode’s XML format, enabling direct integration with video analysis workflows.

## Third-party integrations

Kloppy aims to be a bridge between the raw match data and software to derive insights from this data. Currently, the following software packages integrate with kloppy:

- [`socceraction`](https://socceraction.readthedocs.io/en/latest/documentation/data/index.html#loading-data-with-kloppy) can convert a kloppy event datasets to the SPADL format and compute action value ratings (xT and VAEP).
- [unravelsports](https://github.com/UnravelSports/unravelsports) can convert a kloppy tracking dataset into graphs to train graph neural networks and compute pressing intensity.
