#!/usr/bin/env python3
"""Journal de campagne append-only (SFD §9, §8.2).

Chaque événement est une ligne JSONL horodatée en UTC par le script. Append-only.

Auto-test : python journal.py (code 0 = OK).
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timezone

CHAMPS_OBLIGATOIRES = ("campaign_id", "agent_id", "event")


def _horodatage_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class Journal:
    """Journal append-only, une ligne JSONL par événement."""

    def __init__(self, chemin):
        self.chemin = chemin

    def ajouter(self, entree):
        for champ in CHAMPS_OBLIGATOIRES:
            if champ not in entree or not entree[champ]:
                raise ValueError("Champ obligatoire manquant : %s" % champ)
        entree = dict(entree)
        entree["timestamp_utc"] = _horodatage_utc()
        ligne = json.dumps(entree, ensure_ascii=False, sort_keys=True)
        with open(self.chemin, "a", encoding="utf-8") as f:
            f.write(ligne + "\n")
        return entree["timestamp_utc"]

    def cycle_commence(self, campaign_id, agent_id="AG-07"):
        """Début de cycle idempotent : un seul cycle_commence par campaign_id."""
        for e in self.lire():
            if e.get("campaign_id") == campaign_id and e.get("event") == "cycle_commence":
                return None
        return self.ajouter({"campaign_id": campaign_id, "agent_id": agent_id,
                             "event": "cycle_commence", "status": "BROUILLON"})

    def lire(self):
        if not os.path.isfile(self.chemin):
            return []
        with open(self.chemin, "r", encoding="utf-8") as f:
            return [json.loads(l) for l in f if l.strip()]

    def compter(self):
        return len(self.lire())


def _auto_test():
    fd, chemin = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.unlink(chemin)
    echecs = []
    try:
        j = Journal(chemin)
        j.cycle_commence("C-1")
        j.cycle_commence("C-1")
        if j.compter() != 1:
            echecs.append(("cycle_commence non idempotent", j.compter()))
        j.cycle_commence("C-2")
        if j.compter() != 2:
            echecs.append(("second campaign_id absent", j.compter()))
        try:
            j.ajouter({"campaign_id": "C-3"})
            echecs.append(("champ manquant accepté", []))
        except ValueError:
            pass
    finally:
        os.unlink(chemin)
    return echecs


if __name__ == "__main__":
    echecs = _auto_test()
    if echecs:
        for e in echecs:
            print("ÉCHEC:", e)
        sys.exit(1)
    print("Auto-test journal.py : OK (append-only, UTC, cycle_commence idempotent)")
    sys.exit(0)
