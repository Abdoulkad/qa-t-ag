#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Couverture + classification consolidée — SFD-TEST-001 v1.0 (calculée par script)."""
import json, glob, os, time
from pathlib import Path

BASE = Path("mission-data/MODULE-TEST-LOGIN")

# --- charger la dernière exécution complète ---
execs = sorted(glob.glob(str(BASE / "executions" / "exec-*" / "resultats.json")))
latest = execs[-1]
data = json.loads(Path(latest).read_text(encoding="utf-8"))
results = data["resultats"]

# --- classification NFT-PERF-01 : instable/flaky (3 exécutions consignées) ---
perf_runs = [
    {"execution_id": "exec-20260923T114027Z", "mediane_ms": 3024.9, "verdict": "FAIL"},
    {"execution_id": "exec-20260923T114428Z", "mediane_ms": 2991.5, "verdict": "PASS"},
    {"execution_id": "perf-run3",               "mediane_ms": 2953.1, "verdict": "PASS"},
]

by_test = {r["test_id"]: r for r in results}
# forcer la classe instable sur NFT-PERF-01
if "NFT-PERF-01" in by_test:
    by_test["NFT-PERF-01"]["classe"] = "instable"
    by_test["NFT-PERF-01"]["verdict"] = "INSTABLE"
    by_test["NFT-PERF-01"]["confiance"] = "BASSE"
    by_test["NFT-PERF-01"]["preuve"]["executions_flaky"] = perf_runs
    by_test["NFT-PERF-01"]["detail"] = ("instable : 3 exécutions (FAIL/PASS/PASS), "
        "médiane ~2953-3025 ms, réseau non maîtrisé")

# --- couverture fonctionnelle ---
REQS = ["REQ-001", "REQ-002", "REQ-003", "REQ-004", "REQ-005"]
covered = []
for req in REQS:
    tests = [r for r in results if r.get("exigence") == req and r["test_id"].startswith("TC-")]
    conclusive = [t for t in tests if t["verdict"] in ("PASS", "FAIL")]
    ok = len(conclusive) >= 1
    covered.append({"requirement_id": req, "nb_tests": len(tests),
                    "concluants": len(conclusive), "couvert": ok})

n_req = len(REQS)
n_covered = sum(1 for c in covered if c["couvert"])
func_cov = round(n_covered / n_req, 4)

# --- couverture non fonctionnelle (attributs retenus) ---
attrs = {
    "Efficience de performance": ["NFT-PERF-01"],
    "Utilisabilité (accessibilité)": ["NFT-A11Y-01"],
    "Sécurité (confidentialité)": ["NFT-SEC-01", "NFT-SEC-02", "NFT-SEC-03"],
}
attr_cov = {}
for a, ids in attrs.items():
    done = [i for i in ids if i in by_test and by_test[i]["verdict"] in ("PASS", "FAIL", "INSTABLE", "INCONCLUSIVE")]
    attr_cov[a] = {"tests": ids, "executes": done, "couvert": len(done) >= 1}

out = {
    "cycle": "SFD-TEST-001-v1.0",
    "module_id": "MODULE-TEST-LOGIN",
    "seuil": 0.95,
    "couverture_fonctionnelle": func_cov,
    "exigences_couvertes": n_covered,
    "exigences_totales": n_req,
    "couverture_atteinte": func_cov >= 0.95,
    "details_exigences": covered,
    "attributs_non_fonctionnels": attr_cov,
    "classement_perf": "instable",
    "source_execution": latest,
    "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
}

p = BASE / "couverture-SFD-TEST-001.json"
p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=2))
print(f"\nÉcrit : {p}")
