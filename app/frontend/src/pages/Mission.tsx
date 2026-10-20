import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type EntreeJournal, type Mission, type Version } from "../api";
import { MessageErreur, PastilleMission, useAction, useDonnees, useSuiviTache } from "../composants";
import { date, EVENEMENTS } from "../libelles";
import CasTests from "./mission/CasTests";
import Exigence, { traitee, type EtapeExigence } from "./mission/Exigence";
import Porte from "./mission/Porte";
import Tracabilite from "./mission/Tracabilite";

const NOM_TACHE: Record<string, string> = {
  ANALYSE: "L'analyse (AG-01)", REECRITURE: "La réécriture", CONCEPTION: "La conception (AG-02)",
};

const LIBELLE_TACHE: Record<string, string> = {
  ANALYSE: "L'agent AG-01 analyse l'exigence",
  REECRITURE: "L'agent réécrit l'exigence à partir de vos réponses",
  CONCEPTION: "L'agent AG-02 conçoit les cas de test",
};

type Etape = EtapeExigence | "concevoir" | "recette";
type Vue = Etape | "tracabilite" | "journal";

/** L'étape à montrer en arrivant sur la mission, selon où elle en est. */
function etapeParDefaut(m: Mission, v: Version): Etape {
  switch (m.statut) {
    case "ANALYSE_EN_COURS": case "ECHEC_ANALYSE": return "analyser";
    case "CLARIFICATION": return v.defauts.some((d) => !d.validation) ? "analyser" : "clarifier";
    case "REECRITURE": case "ATTENTE_PV1": return "reecrire";
    case "A_CORRIGER": return v.texte_reecrit ? "reecrire" : "analyser";
    default: return "concevoir";
  }
}

export default function MissionPage() {
  const { id } = useParams();
  const { donnees: m, erreur, recharger } = useDonnees<Mission>("/missions/" + id);
  const [vue, setVue] = useState<Vue | null>(null);
  const [numeroVersion, setNumeroVersion] = useState<number | null>(null);
  const suivi = useSuiviTache(recharger);

  // Reprend le suivi d'une tâche lancée ailleurs (ou avant un rechargement)
  useEffect(() => {
    if (m && m.taches_en_cours.length && !suivi.enCours) suivi.suivre(m.taches_en_cours[0]);
  }, [m]); // eslint-disable-line react-hooks/exhaustive-deps

  // Quand la mission change de phase (fin d'une tâche, décision), on montre la bonne étape
  useEffect(() => { setVue(null); }, [m?.statut]);

  if (erreur) return <MessageErreur erreur={erreur} />;
  if (!m) return <div className="charge">Chargement de la mission…</div>;

  const courante = m.versions[m.versions.length - 1];
  const version = m.versions.find((v) => v.numero === numeroVersion) ?? courante;
  const historique = version !== courante;
  const vueActive: Vue = vue ?? etapeParDefaut(m, courante);
  const tacheType = suivi.tache?.type ?? (m.statut === "ANALYSE_EN_COURS" ? "ANALYSE"
    : m.statut === "REECRITURE" ? "REECRITURE" : null);
  const lancerTache = (tacheId: number) => { suivi.suivre(tacheId); recharger(); };
  const occupe = suivi.enCours || m.taches_en_cours.length > 0;

  return (
    <div className="pile">
      <div className="entete-page" style={{ marginBottom: 0 }}>
        <div>
          <div className="fil"><Link to="/">Vue de pilotage</Link> / <span className="ref">{m.reference}</span></div>
          <h1>{m.titre}</h1>
          <p className="rangee" style={{ marginTop: 6 }}>
            <PastilleMission statut={m.statut} />
            <span>Version {courante.numero} · {courante.nom_source}</span>
            {courante.ia.modele && <span className="discret-texte">IA : {courante.ia.fournisseur} · {courante.ia.modele}</span>}
          </p>
        </div>
        <div className="rangee">
          {m.versions.length > 1 && (
            <select value={version.numero} onChange={(e) => setNumeroVersion(Number(e.target.value))}
                    aria-label="Version affichée" style={{ width: "auto" }}>
              {m.versions.map((v) => (
                <option key={v.numero} value={v.numero}>
                  Version {v.numero}{v === courante ? " (courante)" : " (archivée)"}
                </option>
              ))}
            </select>
          )}
          <button className="bouton" aria-pressed={vueActive === "tracabilite"} onClick={() => setVue("tracabilite")}>Traçabilité</button>
          <button className="bouton" aria-pressed={vueActive === "journal"} onClick={() => setVue("journal")}>Journal</button>
        </div>
      </div>

      <Parcours mission={m} version={courante} active={vueActive} choisir={(e) => setVue(e)} />

      {occupe && (
        <div className="message-info tache-en-cours" role="status">
          {LIBELLE_TACHE[tacheType ?? ""] ?? "L'agent travaille"}… Cette page se met à jour toute seule ;
          vous pouvez aussi la quitter.
        </div>
      )}
      {!occupe && m.derniere_tache?.etat === "ECHEC" && (
        <div className="message-erreur" role="alert">
          <strong>{NOM_TACHE[m.derniere_tache.type] ?? "L'agent"} a échoué</strong>
          {m.derniere_tache.termine_le && <> le {date(m.derniere_tache.termine_le)}</>} :{" "}
          {m.derniere_tache.erreur}
        </div>
      )}
      {historique && (
        <div className="message-info">
          Vous consultez la version {version.numero}, archivée en lecture seule.{" "}
          <button className="bouton discret petit" onClick={() => setNumeroVersion(null)}>Revenir à la version courante</button>
        </div>
      )}
      {!historique && <Corrections mission={m} lancerTache={lancerTache} />}

      <div className="deux-colonnes">
        <div className="panneau" style={{ minWidth: 0 }}>
          {(vueActive === "analyser" || vueActive === "clarifier" || vueActive === "reecrire") && (
            <Exigence mission={m} version={version} modifiable={!historique} recharger={recharger}
                      lancerTache={lancerTache} occupe={occupe} etape={vueActive} allerA={(e) => setVue(e)} />
          )}
          {vueActive === "concevoir" && <CasTests mission={m} historique={historique} recharger={recharger} />}
          {vueActive === "recette" && (
            <div className="vide"><strong>Recette</strong>L'exécution des cas, les preuves et le cahier de recette
              arrivent au lot 3. En attendant, exportez le cahier des cas depuis l'étape Concevoir.</div>
          )}
          {vueActive === "tracabilite" && <Tracabilite missionId={m.id} />}
          {vueActive === "journal" && <JournalMission missionId={m.id} />}
        </div>

        <div className="pile">
          {m.porte_en_attente && !historique
            ? <Porte mission={m} recharger={recharger} lancerTache={lancerTache} />
            : <ProchaineEtape mission={m} version={courante} occupe={occupe} aller={(e) => setVue(e)} lancerTache={lancerTache} />}
          <Avancement mission={m} version={courante} />
          <Decisions mission={m} />
          <Participants mission={m} recharger={recharger} />
        </div>
      </div>
    </div>
  );
}

/** Les étapes de la mission : c'est la navigation principale. Chaque étape montre
 *  son avancement ; les Human Gates sont des losanges. */
function Parcours({ mission: m, version: v, active, choisir }: {
  mission: Mission; version: Version; active: Vue; choisir: (e: Etape) => void;
}) {
  const phase = ({ ANALYSE_EN_COURS: 0, ECHEC_ANALYSE: 0, CLARIFICATION: 1, REECRITURE: 2, ATTENTE_PV1: 2,
    CONCEPTION: 3, ATTENTE_PV2: 3, VALIDEE: 4, EN_RECETTE: 4, CLOTUREE: 5, A_CORRIGER: -1 } as Record<string, number>)[m.statut] ?? -1;
  const decision = (p: string) => v.decisions.find((d) => d.porte === p);
  const examines = v.defauts.filter((d) => d.validation).length;
  const traitees = v.questions.filter(traitee).length;
  const etapes: { cle: Etape; nom: string; detail: string; dispo: boolean; echec?: boolean }[] = [
    { cle: "analyser", nom: "Analyser", dispo: v.defauts.length > 0 || phase === 0, echec: m.statut === "ECHEC_ANALYSE",
      detail: m.statut === "ANALYSE_EN_COURS" ? "Analyse en cours" : m.statut === "ECHEC_ANALYSE" ? "Analyse en échec"
        : `${v.defauts.length} défauts · ${examines} examinés` },
    { cle: "clarifier", nom: "Clarifier", dispo: v.questions.length > 0,
      detail: v.questions.length ? `${traitees} / ${v.questions.length} questions traitées` : "Réponses métier" },
    { cle: "reecrire", nom: "Réécrire", dispo: !!v.texte_reecrit || phase >= 1,
      detail: v.texte_reecrit ? `${v.regles.length} règles · ${v.criteres.length} critères` : "Règles et critères" },
    { cle: "concevoir", nom: "Concevoir", dispo: m.cas.total > 0 || phase >= 3, echec: !!m.en_echec && m.statut === "CONCEPTION",
      detail: m.cas.total ? `${m.cas.total} cas · ${m.cas.prets} prêts` : "Cas de test" },
    { cle: "recette", nom: "Recette", dispo: phase >= 4, detail: "Lot 3 · exécution" },
  ];
  const porte = (nom: "PV-1" | "PV-2", attente: number) => {
    const d = decision(nom);
    const etat = d?.decision === "REJETE" ? "fermee" : phase > attente || d?.decision === "APPROUVE" ? "ouverte"
      : m.porte_en_attente === nom ? "attend" : "";
    return (
      <div key={nom} className={"parcours-porte " + etat} title={"Human Gate " + nom}>
        <span className="losange" aria-hidden="true" />{nom}
      </div>
    );
  };
  const rendu = etapes.map((e, i) => {
    const etat = e.echec ? "echec" : phase > i ? "faite" : phase === i ? "courante" : "";
    const contenu = (
      <>
        <span className="parcours-numero" aria-hidden="true">{etat === "faite" ? "✓" : etat === "echec" ? "!" : i + 1}</span>
        <span><span className="parcours-nom">{e.nom}</span><span className="parcours-detail">{e.detail}</span></span>
      </>
    );
    return e.dispo
      ? <button key={e.cle} type="button" className={"parcours-etape " + etat} aria-current={active === e.cle ? "step" : undefined}
                onClick={() => choisir(e.cle)}>{contenu}</button>
      : <div key={e.cle} className={"parcours-etape indisponible " + etat}>{contenu}</div>;
  });
  return (
    <nav className="parcours" aria-label="Étapes de la mission">
      {rendu[0]}{rendu[1]}{rendu[2]}{porte("PV-1", 2)}{rendu[3]}{porte("PV-2", 3)}{rendu[4]}
    </nav>
  );
}

/** Ce qui bloque la suite, avec des liens vers l'étape concernée. */
function ProchaineEtape({ mission: m, version: v, occupe, aller, lancerTache }: {
  mission: Mission; version: Version; occupe: boolean; aller: (e: Etape) => void; lancerTache: (id: number) => void;
}) {
  const action = useAction();
  if (m.statut !== "CLARIFICATION") {
    return (
      <section className="panneau reperes">
        <div className="reperes-tete">
          <div className="etiquette">Prochaine étape</div>
          <div className="reperes-titre">{m.prochaine_action}</div>
        </div>
        {m.statut === "VALIDEE" && (
          <div className="panneau-corps discret-texte">
            Les cas sont validés et figés. Exportez le cahier des cas depuis l'étape{" "}
            <button className="lien" onClick={() => aller("concevoir")}>Concevoir</button>.
          </div>
        )}
      </section>
    );
  }
  const bloquantes = v.questions.filter((q) => q.bloquante && !traitee(q));
  const aExaminer = v.defauts.filter((d) => !d.validation).length;
  const ouvertes = v.questions.filter((q) => !q.bloquante && !traitee(q)).length;
  return (
    <section className="panneau reperes">
      <div className="reperes-tete">
        <div className="etiquette">Prochaine étape</div>
        <div className="reperes-titre">{v.texte_reecrit ? "Relancer la réécriture" : "Réécrire l'exigence"}</div>
      </div>
      <ul className="reperes-liste">
        {bloquantes.map((q) => (
          <li key={q.id}><span className="repere-icone bloque" aria-hidden="true">!</span>
            <span><button className="lien ref" onClick={() => aller("clarifier")}>{q.code}</button> bloquante, sans réponse</span></li>
        ))}
        {bloquantes.length === 0 && (
          <li><span className="repere-icone ok" aria-hidden="true">✓</span><span>Questions bloquantes traitées</span></li>
        )}
        {aExaminer > 0 && (
          <li><span className="repere-icone info" aria-hidden="true">i</span>
            <span><button className="lien" onClick={() => aller("analyser")}>{aExaminer} défaut{aExaminer > 1 ? "s" : ""} à examiner</button> (conseillé, non bloquant)</span></li>
        )}
        {ouvertes > 0 && (
          <li><span className="repere-icone info" aria-hidden="true">i</span>
            <span>{ouvertes} question{ouvertes > 1 ? "s" : ""} sans réponse deviendr{ouvertes > 1 ? "ont" : "a"} des points ouverts</span></li>
        )}
      </ul>
      <div className="panneau-corps" style={{ paddingTop: 0 }}>
        <MessageErreur erreur={action.erreur} />
        <button className="bouton principal" style={{ width: "100%" }} disabled={action.enCours || occupe || bloquantes.length > 0}
                onClick={() => action.lancer(async () => {
                  const r = await api<{ tache_id: number }>(`/missions/${m.id}/reecriture`, { methode: "POST" });
                  lancerTache(r.tache_id);
                })}>{v.texte_reecrit ? "Relancer la réécriture" : "Réécrire l'exigence"}</button>
        {bloquantes.length > 0 && (
          <div className="discret-texte" style={{ textAlign: "center", marginTop: 6 }}>
            S'active quand {bloquantes.length > 1 ? `les ${bloquantes.length} questions bloquantes sont traitées` : "la question bloquante est traitée"}.
          </div>
        )}
      </div>
    </section>
  );
}

function Avancement({ mission: m, version: v }: { mission: Mission; version: Version }) {
  const lignes: { libelle: string; fait: number; total: number; couleur: string }[] = [];
  if (v.defauts.length) lignes.push({ libelle: "Défauts examinés", fait: v.defauts.filter((d) => d.validation).length, total: v.defauts.length, couleur: "var(--action)" });
  if (v.questions.length) lignes.push({ libelle: "Questions traitées", fait: v.questions.filter(traitee).length, total: v.questions.length, couleur: "var(--attente)" });
  if (m.cas.total) lignes.push({ libelle: "Cas prêts", fait: m.cas.prets, total: m.cas.total, couleur: "var(--succes)" });
  if (!lignes.length) return null;
  return (
    <section className="panneau">
      <div className="panneau-corps pile" style={{ gap: 10 }}>
        <div className="etiquette">Avancement</div>
        {lignes.map((l) => (
          <div key={l.libelle}>
            <div className="rangee" style={{ justifyContent: "space-between", fontSize: "0.9rem" }}>
              <span>{l.libelle}</span><strong>{l.fait} / {l.total}</strong>
            </div>
            <div className="barre-progres"><div style={{ width: (100 * l.fait / l.total) + "%", background: l.couleur }} /></div>
          </div>
        ))}
      </div>
    </section>
  );
}

function Corrections({ mission: m, lancerTache }: { mission: Mission; lancerTache: (id: number) => void }) {
  const courante = m.versions[m.versions.length - 1];
  const [texte, setTexte] = useState(courante.texte);
  const action = useAction();
  if (m.statut === "CONCEPTION" && m.taches_en_cours.length === 0) {
    return (
      <div className="message-erreur rangee">
        La conception des cas n'a pas abouti.
        <button className="bouton petit" disabled={action.enCours}
                onClick={() => action.lancer(async () => {
                  const r = await api<{ tache_id: number }>(`/missions/${m.id}/relancer`, { methode: "POST" });
                  lancerTache(r.tache_id);
                })}>Relancer la conception</button>
        <MessageErreur erreur={action.erreur} />
      </div>
    );
  }
  if (m.statut !== "A_CORRIGER" && m.statut !== "ECHEC_ANALYSE") return null;
  const rejet = courante.decisions.find((d) => d.decision === "REJETE");
  return (
    <section className="panneau" style={{ borderColor: "#e3b5ac" }}>
      <div className="panneau-entete">
        <div>
          <h2>{m.statut === "A_CORRIGER" ? "Corriger et resoumettre" : "L'analyse n'a pas abouti"}</h2>
          {rejet
            ? <p>Rejetée à {rejet.porte} : « {rejet.commentaire} »</p>
            : <p>Relancez l'analyse, ou corrigez le texte pour créer une nouvelle version.</p>}
        </div>
      </div>
      <div className="panneau-corps pile">
        <div className="champ">
          <label htmlFor="correction">Texte de la version {courante.numero + 1}</label>
          <textarea id="correction" rows={8} value={texte} onChange={(e) => setTexte(e.target.value)} />
        </div>
        <MessageErreur erreur={action.erreur} />
        <div className="rangee">
          <button className="bouton principal" disabled={action.enCours || !texte.trim()}
                  onClick={() => action.lancer(async () => {
                    const r = await api<{ tache_id: number }>(`/missions/${m.id}/versions`,
                      { methode: "POST", corps: { texte } });
                    lancerTache(r.tache_id);
                  })}>Créer la version {courante.numero + 1} et l'analyser</button>
          {m.statut === "ECHEC_ANALYSE" && (
            <button className="bouton" disabled={action.enCours}
                    onClick={() => action.lancer(async () => {
                      const r = await api<{ tache_id: number }>(`/missions/${m.id}/relancer`, { methode: "POST" });
                      lancerTache(r.tache_id);
                    })}>Relancer l'analyse sans changer le texte</button>
          )}
        </div>
      </div>
    </section>
  );
}

function Decisions({ mission: m }: { mission: Mission }) {
  const decisions = m.versions.flatMap((v) => v.decisions.map((d) => ({ ...d, version: v.numero })));
  if (!decisions.length) return null;
  const nom = (id: number) => m.participants.find((p) => p.id === id)?.nom || m.participants.find((p) => p.id === id)?.email || "Superviseur";
  return (
    <section className="panneau">
      <div className="panneau-entete"><h2>Décisions</h2></div>
      <div className="panneau-corps">
        <ul className="journal">
          {decisions.reverse().map((d, i) => (
            <li key={i}>
              <div className="quand">{date(d.decide_le)} · version {d.version}</div>
              <div><strong>{d.porte}</strong> {d.decision === "APPROUVE" ? "approuvé" : "rejeté"} par {nom(d.decideur_id)}</div>
              {d.auto_validation && <div className="discret-texte">Validé par l'unique acteur de la mission</div>}
              {d.commentaire && <div className="discret-texte">« {d.commentaire} »</div>}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function Participants({ mission: m, recharger }: { mission: Mission; recharger: () => void }) {
  const [email, setEmail] = useState("");
  const action = useAction();
  return (
    <section className="panneau">
      <div className="panneau-entete">
        <h2>Participants</h2>
      </div>
      <div className="panneau-corps pile">
        <ul style={{ margin: 0, paddingLeft: 18 }}>
          {m.participants.map((p) => <li key={p.id}>{p.nom || p.email}</li>)}
        </ul>
        <p className="discret-texte">
          {m.participants.length === 1
            ? "Seul participant : vous pouvez valider les Human Gates vous-même. La validation sera marquée comme telle."
            : "Plusieurs participants : un Superviseur qui n'est pas l'auteur doit valider les Human Gates."}
        </p>
        <form className="rangee" onSubmit={(e) => {
          e.preventDefault();
          action.lancer(async () => {
            await api(`/missions/${m.id}/participants`, { methode: "POST", corps: { email } });
            setEmail("");
            recharger();
          });
        }}>
          <input type="email" required placeholder="E-mail d'un collègue" value={email}
                 onChange={(e) => setEmail(e.target.value)} style={{ flex: 1, minWidth: 160 }}
                 aria-label="E-mail du participant à ajouter" />
          <button className="bouton petit" disabled={action.enCours}>Ajouter</button>
        </form>
        <MessageErreur erreur={action.erreur} />
      </div>
    </section>
  );
}

function JournalMission({ missionId }: { missionId: number }) {
  const { donnees } = useDonnees<EntreeJournal[]>(`/missions/${missionId}/journal`);
  return (
    <div className="panneau-corps">
      <ul className="journal">
        {(donnees ?? []).map((e) => (
          <li key={e.id}>
            <div className="quand">{date(e.horodatage)}{e.agent ? " · " + e.agent : ""}</div>
            <div>{EVENEMENTS[e.evenement] ?? e.evenement}</div>
            <DetailsJournal e={e} />
          </li>
        ))}
      </ul>
    </div>
  );
}

function DetailsJournal({ e }: { e: EntreeJournal }) {
  const d = e.details as Record<string, unknown>;
  const morceaux: string[] = [];
  if (d.question) morceaux.push(String(d.question));
  if (d.critere) morceaux.push(String(d.critere));
  if (d.cas) morceaux.push(String(d.cas));
  if (d.motif) morceaux.push("motif : " + String(d.motif));
  if (d.commentaire) morceaux.push("« " + String(d.commentaire) + " »");
  if (d.defauts !== undefined) morceaux.push(`${d.defauts} défaut(s), clarté ${d.score_clarte}/100`);
  if (d.auto_validation) morceaux.push("auto-validation (acteur unique)");
  if (d.erreur) morceaux.push(String(d.erreur));
  if (d.ia) morceaux.push("IA " + String(d.ia));
  return morceaux.length ? <div className="discret-texte">{morceaux.join(" · ")}</div> : null;
}
