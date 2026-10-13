from __future__ import annotations
import json
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
DATA=ROOT/"data"/"probe_prompts_128.jsonl"
HIDDEN=ROOT/"results"/"probe_qwen3_1_7b"/"prompt_end_hidden_128.npz"
OUT=ROOT/"results"/"trajectory_qwen3_1_7b"
SEED=20260916
BPERM=200
BBOOT=10000

records=[json.loads(x) for x in DATA.read_text(encoding="utf-8").splitlines() if x.strip()]
arc=np.load(HIDDEN)
hidden=arc["hidden"].astype(np.float64)
tokens=arc["token_counts"].astype(float)
ids=arc["sample_ids"].astype(str)
assert ids.tolist()==[str(r["sample_id"]) for r in records]

base=np.array([str(r["base_task"]) for r in records])
levels=np.array([str(r["level"]) for r in records])
texts=np.array([str(r["prompt"]) for r in records])
y=np.array([int(r["binary_sufficiency"]) for r in records])
folds=np.empty(len(records),dtype=int)
families={"CD":[],"CG":[],"DP":[],"NR":[]}
for g in sorted(set(base)):
    families[g[:2]].append(g)
mapping={}
for fam,gs in families.items():
    for k,g in enumerate(sorted(gs)): mapping[g]=k
for i,g in enumerate(base): folds[i]=mapping[g]

final_hidden=hidden[:,-1,:]
scaled_folds=[]
for f in range(8):
    tr=folds!=f; te=folds==f
    scaler=StandardScaler()
    scaled_folds.append((tr,te,scaler.fit_transform(final_hidden[tr]),scaler.transform(final_hidden[te])))

def oof_bacc(target):
    pred=np.empty(len(target),dtype=int)
    for tr,te,xtr,xte in scaled_folds:
        m=LogisticRegression(C=1.0,solver="liblinear",max_iter=2000,random_state=SEED)
        m.fit(xtr,target[tr])
        pred[te]=m.predict(xte)
    return float(balanced_accuracy_score(target,pred))

observed=oof_bacc(y)
rng=np.random.default_rng(SEED)
perm_scores=np.empty(BPERM)
groups=sorted(set(base))
group_indices=[np.where(base==g)[0] for g in groups]
for b in range(BPERM):
    yp=y.copy()
    for ix in group_indices:
        yp[ix]=rng.permutation(yp[ix])
    perm_scores[b]=oof_bacc(yp)
    if (b+1)%100==0: print(f'permutations {b+1}/{BPERM}',flush=True)
pvalue=float((1+np.sum(perm_scores>=observed))/(BPERM+1))

# Pair records within each task in ordered levels.
level_order=["L0","L1","L2","L3"]
pairs=[]
for gi,g in enumerate(groups):
    ix={levels[i]:i for i in np.where(base==g)[0]}
    for j,name in enumerate(["L0-L1","L1-L2","L2-L3"]):
        a=ix[level_order[j]]; b=ix[level_order[j+1]]
        pairs.append((gi,g,name,a,b))

# Normalize hidden vectors, then cosine distance.
norm=hidden/np.clip(np.linalg.norm(hidden,axis=2,keepdims=True),1e-12,None)
hd=np.stack([1-np.sum(norm[a]*norm[b],axis=1) for _,_,_,a,b in pairs])
contrast=np.array([q[2] for q in pairs])
task_index=np.array([q[0] for q in pairs])

vec=TfidfVectorizer(analyzer="char",ngram_range=(2,5),min_df=1,sublinear_tf=True)
tx=vec.fit_transform(texts)
rows=[]
for k,(gi,g,c,a,b) in enumerate(pairs):
    tfcos=float(tx[a].multiply(tx[b]).sum()/(np.sqrt(tx[a].multiply(tx[a]).sum())*np.sqrt(tx[b].multiply(tx[b]).sum())+1e-12))
    rows.append({
        "task_index":gi,"base_task":g,"contrast":c,
        "char_edit":1-SequenceMatcher(None,texts[a],texts[b],autojunk=False).ratio(),
        "token_change":abs(tokens[a]-tokens[b])/max(tokens[a],tokens[b],1),
        "tfidf_distance":1-tfcos,
    })
frame=pd.DataFrame(rows)
for layer in range(hd.shape[1]): frame[f"layer_{layer}"]=hd[:,layer]

# Raw means and paired bootstrap intervals by task.
raw=[]
for layer in range(hd.shape[1]):
    for c in ["L0-L1","L1-L2","L2-L3"]:
        vals=hd[contrast==c,layer]
        raw.append({"layer":layer,"contrast":c,"mean_cosine_distance":float(vals.mean())})
raw_df=pd.DataFrame(raw)

rng=np.random.default_rng(SEED)
boot_idx=rng.integers(0,32,size=(BBOOT,32))
# hd order is task-major and three contrasts per task.
cube=hd.reshape(32,3,29)
boot_means=cube[boot_idx].mean(axis=1)
diff12=boot_means[:,1,:]-boot_means[:,0,:]
diff23=boot_means[:,2,:]-boot_means[:,0,:]

# Surface-controlled OLS: hidden distance ~ char edit + token change + critical-step indicators.
X=np.column_stack([
    np.ones(len(frame)),
    frame["char_edit"].to_numpy(),
    frame["token_change"].to_numpy(),
    (contrast=="L1-L2").astype(float),
    (contrast=="L2-L3").astype(float),
])
coef=np.linalg.pinv(X)@hd
coef_boot=np.empty((BBOOT,5,29))
for z,idx in enumerate(boot_idx):
    ridx=np.concatenate([np.array([3*i,3*i+1,3*i+2]) for i in idx])
    xb=X[ridx]; yb=hd[ridx]
    coef_boot[z]=np.linalg.pinv(xb)@yb

layer_rows=[]
for layer in range(29):
    layer_rows.append({
        "layer":layer,
        "raw_L0_L1":float(cube[:,0,layer].mean()),
        "raw_L1_L2":float(cube[:,1,layer].mean()),
        "raw_L2_L3":float(cube[:,2,layer].mean()),
        "raw_diff_L1_L2_minus_L0_L1":float(cube[:,1,layer].mean()-cube[:,0,layer].mean()),
        "raw_diff_L1_L2_ci_low":float(np.quantile(diff12[:,layer],.025)),
        "raw_diff_L1_L2_ci_high":float(np.quantile(diff12[:,layer],.975)),
        "controlled_L1_L2_coefficient":float(coef[3,layer]),
        "controlled_L1_L2_ci_low":float(np.quantile(coef_boot[:,3,layer],.025)),
        "controlled_L1_L2_ci_high":float(np.quantile(coef_boot[:,3,layer],.975)),
        "controlled_L2_L3_coefficient":float(coef[4,layer]),
        "controlled_L2_L3_ci_low":float(np.quantile(coef_boot[:,4,layer],.025)),
        "controlled_L2_L3_ci_high":float(np.quantile(coef_boot[:,4,layer],.975)),
    })
layer_df=pd.DataFrame(layer_rows)

summary={
    "permutation_test":{
        "feature":"final-layer prompt-end hidden state",
        "observed_grouped_balanced_accuracy":observed,
        "within_chain_label_permutations":BPERM,
        "null_mean":float(perm_scores.mean()),
        "null_95_interval":[float(np.quantile(perm_scores,.025)),float(np.quantile(perm_scores,.975))],
        "empirical_p_value":pvalue,
        "note":"Labels were permuted within each four-prompt task chain; the model was refit in every permutation."
    },
    "trajectory_layer_18":layer_rows[18],
    "trajectory_final_layer_28":layer_rows[28],
    "surface_controls":["character edit distance","relative token-count change"],
    "interpretive_limit":"Cosine trajectories are descriptive associations and do not establish causal processing or awareness."
}

OUT.mkdir(parents=True,exist_ok=True)
frame.to_csv(OUT/"pairwise_distances.csv",index=False,encoding="utf-8-sig")
layer_df.to_csv(OUT/"trajectory_layer_statistics.csv",index=False)
np.savez_compressed(OUT/"permutation_null.npz",scores=perm_scores,observed=np.array([observed]))
(OUT/"trajectory_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")

plt.figure(figsize=(7.2,4.4))
for c,label,color in [("L0-L1","Redundant removal (L0-L1)","#4C78A8"),("L1-L2","First critical removal (L1-L2)","#E45756"),("L2-L3","Further critical removal (L2-L3)","#72B7B2")]:
    z=raw_df[raw_df.contrast==c]
    plt.plot(z.layer,z.mean_cosine_distance,label=label,color=color,linewidth=2)
plt.axvspan(16,19,color="#999999",alpha=.12,label="Nested-selected range")
plt.xlabel("Representation index (0 = embedding; 1-28 = transformer layers)")
plt.ylabel("Mean within-task cosine distance")
plt.legend(frameon=False,fontsize=8)
plt.tight_layout()
plt.savefig(OUT/"representation_trajectory.png",dpi=300)
plt.close()
print(json.dumps(summary,ensure_ascii=False,indent=2))
print(f"PASS: {OUT}")


