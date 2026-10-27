#!/usr/bin/env python3
"""Validation des enveloppes d'entrée/sortie (SFD §6.1 / §6.2).

Les schémas JSON sont l'autorité ; ce module les charge et les applique.
Le statut de l'enveloppe de sortie est normalisé via statuts.py avant
validation (résout DEF-001). `attempt_id` est exigé (résout DEF-005,
reprend §10 sur l'idempotence).

Auto-test : `python contrats.py` (code 0 = OK).
"""

import json
import os
import sys

from jsonschema import Draft7Validator, FormatChecker

import statuts

REPERTOIRE = os.path.dirname(os.path.abspath(__file__))


def _chemin_schema(nom):
    """Résout le chemin d'un schéma : layout skill (<racine>/schemas) ou plat."""
    racine = os.path.dirname(REPERTOIRE)
    for base in (racine, REPERTOIRE):
        chemin = os.path.join(base, "schemas", nom)
        if os.path.isfile(chemin):
            return chemin
    return os.path.join(racine, "schemas", nom)


def _charger(nom):
    with open(_chemin_schema(nom), "r", encoding="utf-8") as f:
        return json.load(f)


SCHEMA_ENTREE = _charger("enveloppe-entree.schema.json")
SCHEMA_SORTIE = _charger("enveloppe-sortie.schema.json")


def _erreurs(schema, doc):
    v = Draft7Validator(schema, format_checker=FormatChecker())
    return [e.message for e in v.iter_errors(doc)]


def valider_enveloppe_entree(doc):
    """(ok, erreurs) — validation pure, ne modifie pas l'entrée."""
    errs = _erreurs(SCHEMA_ENTREE, doc)
    return (len(errs) == 0), errs


def valider_enveloppe_sortie(doc):
    """(ok, erreurs) — normalise `status` puis valide. Ne modifie pas `doc`."""
    doc = json.loads(json.dumps(doc))
    if isinstance(doc.get("status"), str):
        try:
            doc["status"] = statuts.normaliser_statut_agent(doc["status"])
        except ValueError as e:
            return False, [str(e)]
    errs = _erreurs(SCHEMA_SORTIE, doc)
    return (len(errs) == 0), errs


# --- Auto-test --------------------------------------------------------------
ENTREE_OK = {
    "schema_version": "1.0",
    "campaign_id": "QA-20261012-DEMO",
    "project_id": "PROJ-001",
    "agent_id": "AG-01",
    "task_id": "TASK-001",
    "input_artifacts": [
        {
            "artifact_id": "SFD-001",
            "path": "entrees/sfd-projet.md",
            "sha256": "a" * 64,
            "version": "1.0",
        }
    ],
    "approved_scope": "analyse documentaire seulement",
    "human_gate_state": "PV-1_PENDING",
    "limits": {"max_duration_seconds": 1200, "max_model_calls": 30, "max_cost": None},
}

SORTIE_OK = {
    "schema_version": "1.0",
    "campaign_id": "QA-20261012-DEMO",
    "task_id": "TASK-001",
    "attempt_id": "ATT-001",
    "agent_id": "AG-01",
    "agent_version": "0.1.0",
    "status": "OK",
    "artifact_path": "livrables/revue/revue-projet.md",
    "input_fingerprints": ["a" * 64],
    "warnings": [],
    "errors": [],
    "metrics": {"duration_seconds": 12.5, "model_calls": 4, "cost": None},
    "human_approval_required": True,
}


def _auto_test():
    echecs = []

    ok, errs = valider_enveloppe_entree(ENTREE_OK)
    if not ok:
        echecs.append(("entrée valide refusée", errs))

    ok, errs = valider_enveloppe_sortie(SORTIE_OK)
    if not ok:
        echecs.append(("sortie valide refusée", errs))

    # alias historique « À_CLARIFIER » -> accepté après normalisation
    s = json.loads(json.dumps(SORTIE_OK))
    s["status"] = "À_CLARIFIER"
    ok, errs = valider_enveloppe_sortie(s)
    if not ok:
        echecs.append(("alias À_CLARIFIER refusé", errs))

    # statut inconnu -> refusé
    s = json.loads(json.dumps(SORTIE_OK))
    s["status"] = "VALIDÉ"
    ok, _ = valider_enveloppe_sortie(s)
    if ok:
        echecs.append(("statut inconnu accepté", []))

    # sha256 malformé -> refusé
    e = json.loads(json.dumps(ENTREE_OK))
    e["input_artifacts"][0]["sha256"] = "pas-un-hash"
    ok, _ = valider_enveloppe_entree(e)
    if ok:
        echecs.append(("sha256 malformé accepté", []))

    # champ obligatoire manquant -> refusé
    e = json.loads(json.dumps(ENTREE_OK))
    del e["task_id"]
    ok, _ = valider_enveloppe_entree(e)
    if ok:
        echecs.append(("task_id manquant accepté", []))

    # attempt_id manquant -> refusé (DEF-005)
    s = json.loads(json.dumps(SORTIE_OK))
    del s["attempt_id"]
    ok, _ = valider_enveloppe_sortie(s)
    if ok:
        echecs.append(("attempt_id manquant accepté", []))

    return echecs


if __name__ == "__main__":
    echecs = _auto_test()
    if echecs:
        for e in echecs:
            print("ÉCHEC:", e)
        print("%d échec(s)" % len(echecs))
        sys.exit(1)
    print("Auto-test contrats.py : OK (7 cas)")
    sys.exit(0)
