import logging
import sys

from kloppy import load_opta_event_data

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

dataset = load_opta_event_data("1_f24.xml", "1_f7.xml")
