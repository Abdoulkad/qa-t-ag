"""Journal QA chaîné, en ajout seul (RA-34, RA-35).

Chaque entrée porte l'empreinte de la précédente (par organisation) : une
modification directe en base casse la chaîne et `verifier_chaine` la détecte.
La base refuse en plus UPDATE et DELETE sur la table (déclencheur, migration).
"""
import hashlib
import json
from datetime import timezone

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .models import EntreeJournal, maintenant

GENESE = "0" * 64


def _empreinte(precedente, organisation_id, mission_id, acteur_id, agent, evenement,
               details, horodatage):
    contenu = json.dumps({
        "precedente": precedente, "organisation": organisation_id,
        "mission": mission_id, "acteur": acteur_id, "agent": agent,
        "evenement": evenement, "details": details,
        "horodatage": horodatage.astimezone(timezone.utc).isoformat(),
    }, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(contenu.encode("utf-8")).hexdigest()


def ajouter(db: Session, organisation_id: int, evenement: str, *, mission_id=None,
            acteur_id=None, agent=None, details=None) -> EntreeJournal:
    # Verrou par organisation : deux écritures simultanées ne forkent pas la chaîne
    db.execute(text("SELECT pg_advisory_xact_lock(:cle)"), {"cle": 7_000_000 + organisation_id})
    derniere = db.scalar(
        select(EntreeJournal).where(EntreeJournal.organisation_id == organisation_id)
        .order_by(EntreeJournal.id.desc()).limit(1))
    precedente = derniere.empreinte if derniere else GENESE
    details_json = json.dumps(details or {}, sort_keys=True, ensure_ascii=False)
    horodatage = maintenant()
    entree = EntreeJournal(
        organisation_id=organisation_id, mission_id=mission_id, acteur_id=acteur_id,
        agent=agent, evenement=evenement, details=details_json, horodatage=horodatage,
        empreinte_precedente=precedente,
        empreinte=_empreinte(precedente, organisation_id, mission_id, acteur_id, agent,
                             evenement, details_json, horodatage))
    db.add(entree)
    db.flush()
    return entree


def verifier_chaine(db: Session, organisation_id: int) -> tuple[bool, int | None]:
    """(intègre, id de la première entrée fautive)."""
    precedente = GENESE
    entrees = db.scalars(select(EntreeJournal)
                         .where(EntreeJournal.organisation_id == organisation_id)
                         .order_by(EntreeJournal.id))
    for e in entrees:
        attendue = _empreinte(precedente, e.organisation_id, e.mission_id, e.acteur_id,
                              e.agent, e.evenement, e.details, e.horodatage)
        if e.empreinte_precedente != precedente or e.empreinte != attendue:
            return False, e.id
        precedente = e.empreinte
    return True, None
