# kloppy-query

Video analysts spend a lot time on searching for interesting moments in the video. Probably some of those moments can be described by a pattern: pass, pass, shot, etc. In case it can be described, can we automate the search?

We might be able to do so. The kloppy library now provides a search mechanism based on regular expressions to search for patterns within event data.

To make the use event simpler kloppy comes with `kloppy-query`. This command line tool does all the heavy lifting for you and gives you a nice xml, ready for use in your favorite video analyse software.

## Usage 

```shell script
# grab some data from statsbomb open data project
wget https://github.com/statsbomb/open-data/blob/master/data/events/15946.json?raw=true -O events.json
wget https://raw.githubusercontent.com/statsbomb/open-data/master/data/lineups/15946.json -O lineup.json

kloppy-query --input-statsbomb=events.json,lineup.json --query-file=ball_recovery.py --output-xml=test.xml
```

The output will look like:

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