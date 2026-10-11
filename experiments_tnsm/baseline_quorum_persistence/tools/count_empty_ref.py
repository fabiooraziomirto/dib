import sys
sys.path[:0]=["code/scripts","code/src"]
from moniotr_cross_lab import *
from pathlib import Path
D=Path("/root/Desktop/DIB/data/processed")
data=load(D/"moniotr_full_observations.csv",extra_paths=[D/"yourthings_observations.csv"],collapse_fn=collapse_site_three,label_map=load_label_mapping(Path("docs/label_mapping_v16.csv")))
sites=("US","UK","YT")
for r in sites:
    devs,_,_=per_device_metrics(data,sites,r)
    print(r,"dispositivi",len(devs),"con riferimento vuoto",sum(1 for d in devs if len(data.profiles[r][d])==0))
