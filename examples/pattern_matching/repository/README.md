# kloppy-query

Video analysts spend a lot of time searching for interesting moments in the video. Probably a certain type of moments can be described by a pattern: pass, pass, shot, etc. In that case, can we automate the search?

We might be able to do so. The kloppy library now provides a search mechanism based on regular expressions to search for patterns within event data.

To make the use event simpler, kloppy comes with `kloppy-query`. This command line tool does all the heavy lifting for you and gives you a nice xml, ready for use in your favorite video analyse software.

## Usage 

```shell script
# grab some data from statsbomb open data project
wget https://github.com/statsbomb/open-data/blob/master/data/events/15946.json?raw=true -O events.json
wget https://raw.githubusercontent.com/statsbomb/open-data/master/data/lineups/15946.json -O lineup.json

# run the query
kloppy-query --input-statsbomb=events.json,lineup.json --query-file=ball_recovery.py --output-xml=ball_recovery.xml

# check output
cat ball_recovery.xml
```


```xml
<?xml version='1.0' encoding='utf-8'?>
<file>
    <ALL_INSTANCES>
        <instance>
            <ID>0</ID>
            <code>away</code>
            <start>0.0</start>
            <end>16.15</end>
        </instance>
        <instance>
            <ID>1</ID>
            <code>home</code>
            <start>4.15</start>
            <end>29.687</end>
        </instance>
        <instance>
            <ID>2</ID>
            <code>away</code>
            <start>17.687</start>
            <end>71.228</end>
        </instance>
        <instance>
            <ID>3</ID>
            <code>home success</code>
            <start>59.227999999999994</start>
            <end>85.809</end>
        </instance>
    </ALL_INSTANCES>
</file>
```

## Without output file
It's possible to only show stats and don't write a XML file.

```shell script
$ kloppy-query --input-statsbomb=events.json,lineup.json --query-file=ball_recovery.py --stats=text 2>/dev/null
Home:
        total count: 73
                success: 22 (30%)
                no success: 51 (70%)

Away:
        total count: 86
                success: 7 (8%)
                no success: 79 (92%)


# or in json format
$ kloppy-query --input-statsbomb=events.json,lineup.json --query-file=ball_recovery.py --stats=json 2>/dev/null
{
    "away_total": 86,
    "away_success": 7,
    "home_total": 73,
    "home_success": 22
}

# or print matches
$ kloppy-query --input-statsbomb=events.json,lineup.json --query-file=ball_recovery.py --show-events

Match 2: away no-success
126756d5-bfe3-44a7-a2c3-d36fb4d0a548 PASS INCOMPLETE / 1: 24.687 / away  5 / 35.5x68.5
df65f591-1131-4565-ad3c-7295ccdf3f26 PASS COMPLETE   / 1: 30.008 / home  1 / 13.5x27.5
9a0bd516-551c-4e12-832e-a85b92dffcff PASS COMPLETE   / 1: 34.738 / home  3 / 34.5x53.5
d0c15c32-4a22-442a-82e6-916e54266de3 PASS COMPLETE   / 1: 37.467 / home  2 / 49.5x71.5
e4a69750-20f6-401f-bd10-4f1b4cd25b7a PASS COMPLETE   / 1: 38.184 / home 20 / 55.5x62.5
f8030bfa-a45c-4a41-80e8-def34021d09d PASS COMPLETE   / 1: 39.870 / home  2 / 47.5x68.5
b7c78e80-bb42-4b8f-94a6-999e88b4e32e PASS COMPLETE   / 1: 44.029 / home 23 / 42.5x24.5
43ba8e37-a6b8-4c61-964f-b7c2f8ab1863 PASS COMPLETE   / 1: 46.653 / home 18 / 54.5x4.5
2b0b8ea1-4b03-40f6-aadf-d2b71e3bf6b4 PASS COMPLETE   / 1: 49.171 / home  4 / 51.5x15.5
bb173a3c-9289-4040-b547-1e1d9b136e27 PASS COMPLETE   / 1: 54.192 / home  3 / 56.5x51.5
d2d49535-0037-4b01-9d4c-7715dbb58665 PASS COMPLETE   / 1: 59.988 / home 23 / 62.5x25.5
8bd96804-d1c5-4657-a081-0e8eb0bf3881 PASS COMPLETE   / 1: 63.663 / home  3 / 63.5x52.5
029b5f5d-0220-4f56-873d-e3db9cdb7c7e PASS INCOMPLETE / 1: 66.228 / home 10 / 76.5x77.5

Match 3: home SUCCESS
029b5f5d-0220-4f56-873d-e3db9cdb7c7e PASS INCOMPLETE / 1: 66.228 / home 10 / 76.5x77.5
4667e094-bbd7-40a5-8ba3-82ba220558d1 PASS COMPLETE   / 1: 67.685 / away  6 / 21.5x13.5
90b4252c-a9ad-4671-b158-9b3be1e51629 PASS COMPLETE   / 1: 72.116 / away  3 / 1.5x3.5
53e333dc-7cb9-472b-b4b9-c6a773b2d919 PASS COMPLETE   / 1: 76.219 / home  5 / 76.5x76.5
410ff4d0-1aa5-4856-bcc4-4288880285f4 PASS COMPLETE   / 1: 80.809 / home 23 / 64.5x33.5
```