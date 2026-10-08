import copy, importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location("metrics",Path(__file__).with_name("compute_e2e_metrics.py"))
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
def chain(labels):
    return [dict(provider="test",base_task_id="t",level=l,answerability=a,final_label=v) for l,a,v in zip(m.LEVELS,["A","A","P","U"],labels)]
r=chain(["CA","CA","UA","UA"])
assert abs(m.group_metrics(r)["IDU"]-0.5)<1e-12
assert m.group_metrics(r)["CFO"]=={"L2":1}
assert m.group_metrics(chain(["CA","CA","PA","UA"]))["CFO"]=={"L3":1}
assert m.group_metrics(chain(["CA","CA","PA","CQ"]))["CFO"]=={"no_observed_failure":1}
assert m.group_metrics(chain(["CA","UA","UA","UA"]))["CFO_eligible"]==0
assert m.group_metrics(chain(["CA","UA","UA","UA"]))["CFO"]=={"excluded_L1_inappropriate":1}
assert m.group_metrics(chain(["CA","","UA","UA"]))["IDU"] is None
assert m.group_metrics(chain(["","","",""]))["trajectories"]==1
assert m.group_metrics(r[:3])["IDU"] is None
assert m.cohen_kappa([("CA","CA")]*3)==(1.0,None)
for bad in [r+[r[0]],chain(["CA","BAD","UA","UA"])]:
    try: m.group_metrics(bad)
    except ValueError: pass
    else: raise AssertionError("Invalid input accepted")
print("PASS: CFO anchoring, onset, recovery, IDU, missing labels/levels, duplicate rejection, invalid labels, degenerate kappa")
