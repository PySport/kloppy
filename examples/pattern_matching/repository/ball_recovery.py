from kloppy import event_pattern_matching as pm

# This file can be consumed by kloppy-query command line like this:


# kloppy-query --input-statsbomb=events.json,lineup.json --query-file=ball_recovery.py --output-xml=test.xml
query = pm.Query(
    event_types=["pass", "shot"],
    pattern=(
        pm.match_pass(
            capture="last_pass_of_team_a"
        ) +
        pm.match_pass(
            team=pm.not_same_as("last_pass_of_team_a.team")
        ) * slice(1, None) +
        pm.group(
            pm.match_pass(
                success=True,
                team=pm.same_as("last_pass_of_team_a.team"),
                timestamp=pm.function(
                    lambda timestamp, last_pass_of_team_a_timestamp:
                    timestamp - last_pass_of_team_a_timestamp < 10
                )
            ) + (
                pm.match_pass(
                    success=True,
                    team=pm.same_as("last_pass_of_team_a.team")
                ) |
                pm.match_shot(
                    team=pm.same_as("last_pass_of_team_a.team")
                )
            ),
            capture="success"
        ) * slice(0, 1)
    )
)
