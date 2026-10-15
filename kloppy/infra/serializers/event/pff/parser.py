from typing import Any, Dict

class PFFParser:
    
    def _parse_pass(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a pass event from the PFF data.
        """
        return {
            "type": "pass",
            "player_id": event.get("player_id"),
            "start_location": event.get("start_location"),
            "end_location": event.get("end_location"),
            "outcome": event.get("outcome"),
            "distance": event.get("distance"),
            "angle": event.get("angle"),
        }