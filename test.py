# -*- coding: utf-8 -*-
"""
Created on Sat Nov  9 18:30:23 2024

@author: Amod
"""


from kloppy import pff_fc
import time

# Record start time
start_time = time.time()

dataset = pff_fc.load_tracking(meta_data="kloppy/tests/files/PFF_FC/metadata.csv",
                     roster_meta_data= "kloppy/tests/files/PFF_FC/rosters.csv",
                     raw_data = "kloppy/tests/files/PFF_FC/10517.jsonl.bz2",
                     # Optional Parameters
                     sample_rate = 1/10,
                     limit = 100)
# Record end time
end_time = time.time()

# Calculate elapsed time
elapsed_time = end_time - start_time

print(f"The function took {elapsed_time} seconds to run.")

dataset.to_df().head()

len(dataset.metadata.periods)

print(dataset.to_df().head())
