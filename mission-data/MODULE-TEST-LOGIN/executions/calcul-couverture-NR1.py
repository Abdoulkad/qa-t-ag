#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Couverture + classification + comparaison de non-régression — NR1.
Calcule par script (jamais estimé) à partir des exécutions réelles.
Compare l'exécution NR1 à la ligne de base du cycle 1 pour détecter toute régression.
"""
import json
import time
from pathlib import Path

BASE = Path("mission-data/MODULE-TEST-LOGIN")
NR1_EXEC = "exec-20260924T154529Z"
BASELINE_EXEC = "exec-20260923T114428Z"

def load(exec_id):
    p = BASE / "executions" / exec_id / "resultats.json"
    return json.loads(p.read_text(encoding="utf-8"))

nr1 = load(NR1_EXEC)
base = load(BASELINE_EXEC)

by_test_nr1 = {r["test_id"]: r for r in nr1["resultats"]}
by_test_base = {r["test_id"]: r for r in base["resultats"]}

# --- Historique NFT-PERF-01 (flaky) : 3 runs cycle 1 (journal QA-2026-000007) + NR1 ---
perf_runs = [
    {"execution_id": "exec-20260923T114027Z", "mediane_ms": 3024.9, "verdict": "FAIL"},
    {"execution_id": "exec-20260923T114428Z", "mediane_ms": 2991.5, "verdict": "PASS"},
    {"execution_id": "perf-run3",               "mediane_ms": 2953.1, "verdict": "PASS"},
]
# ajouter le run NR1 depuis les données réelles
nr1_perf = by_test_nr1["NFT-PERF-01"]
perf_runs.append({
    "execution_id": NR1_EXEC,
    "mediane_ms": nr1_perf["preuve"]["mediane_ms"],
    "verdict": nr1_perf["verdict"],
})

# classification instable : verdicts divergents sur >=3 runs
verdicts = [r["verdict"] for r in perf_runs]
instable = len(set(verdicts)) > 1 and len(perf_runs) >= 3

# --- Couverture fonctionnelle ---
REQS = ["REQ-001", "REQ-002", "REQ-003", "REQ-004", "REQ-005"]
covered = []
for req in REQS:
    tests = [r for r in nr1["resultats"] if r.get("exigence") == req and r["test_id"].startswith("TC-")]
    concluants = [t for t in tests if t["verdict"] in ("PASS", "FAIL")]
    covered.append({"requirement_id": req, "nb_tests": len(tests),
                    "concluants": len(concluants),
                    "couvert": len(concluants) >= 1})
n_req = len(REQS)
n_covered = sum(1 for c in covered if c["couvert"])
func_cov = round(n_covered / n_req, 4)

# --- Couverture non fonctionnelle (attributs retenus) ---
attrs = {
    "Efficience de performance": ["NFT-PERF-01"],
    "Utilisabilité (accessibilité)": ["NFT-A11Y-01"],
    "Sécurité (confidentialité)": ["NFT-SEC-01", "NFT-SEC-02", "NFT-SEC-03"],
}
attr_cov = {}
for a, ids in attrs.items():
    done = [i for i in ids if i in by_test_nr1
            and by_test_nr1[i]["verdict"] in ("PASS", "FAIL", "INSTABLE", "INCONCLUSIVE")]
    attr_cov[a] = {"tests": ids, "executes": done, "couvert": len(done) >= 1}

# --- Comparaison non-régression (NR1 vs base cycle 1), test par test ---
regression = []
for tid in sorted(by_test_base):
    b = by_test_base[tid]
    n = by_test_nr1.get(tid)
    if tid == "NFT-PERF-01":
        # instable dans les deux cycles : pas une régression fonctionnelle
        continue
    if n is None:
        regression.append({"test_id": tid, "base": b["verdict"], "nr1": "MANQUANT",
                           "regression": True})
    elif b["verdict"] == n["verdict"]:
        regression.append({"test_id": tid, "base": b["verdict"], "nr1": n["verdict"],
                           "regression": False})
    else:
        regression.append({"test_id": tid, "base": b["verdict"], "nr1": n["verdict"],
                           "regression": True})

n_regressions = sum(1 for r in regression if r["regression"])

out = {
    "cycle": "SFD-TEST-001-v1.0-NR1",
    "campagne": "non-regression",
    "module_id": "MODULE-TEST-LOGIN",
    "seuil": 0.95,
    "couverture_fonctionnelle": func_cov,
    "exigences_couvertes": n_covered,
    "exigences_totales": n_req,
    "couverture_atteinte": func_cov >= 0.95,
    "details_exigences": covered,
    "attributs_non_fonctionnels": attr_cov,
    "nft_perf_01": {
        "classe": "instable" if instable else "fait",
        "verdict": "INSTABLE" if instable else nr1_perf["verdict"],
        "confiance": "BASSE",
        "historique_runs": perf_runs,
        "note": "médiane oscillant autour du seuil 3000 ms (réseau non maîtrisé, Sandbox publique)",
    },
    "non_regression": {
        "baseline": BASELINE_EXEC,
        "execution_nr1": NR1_EXEC,
        "nb_tests_compares": len(regression),
        "nb_regressions": n_regressions,
        "detail": regression,
        "verdict": "AUCUNE_REGRESSION" if n_regressions == 0 else "REGRESSION_DETECTEE",
    },
    "source_execution": NR1_EXEC,
    "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
}

p = BASE / "couverture-SFD-TEST-001-NR1.json"
p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=2))
print(f"\nÉcrit : {p}")
