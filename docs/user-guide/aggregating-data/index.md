# Aggregating data

The [`.aggregate()`][kloppy.domain.EventDataset.aggregate] method allows you to go from dataset to aggregation in a single line.

```python
dataset = statsbomb.load_open_data()
for item in dataset.aggregate("minutes_played"):
    print(f"{item.player} - {item.duration}")
```
