import { useState } from "react";
import { api, type Critere, type Mission, type Question, type Version } from "../../api";
import { MessageErreur, Pastille, useAction } from "../../composants";
import { date, DECISION_QUESTION } from "../../libelles";

interface Props {
  mission: Mission;
  version: Version;
  modifiable: boolean;
  recharger: () => void;
  lancerTache: (id: number) => void;
  occupe: boolean;
}

function couleurScore(s: number) {
  return s >= 70 ? "var(--succes)" : s >= 40 ? "var(--attente)" : "var(--alerte)";
}

export default function Exigence({ mission: m, version: v, modifiable, recharger, lancerTache, occupe }: Props) {
  const clarification = modifiable && !v.figee && (m.statut === "CLARIFICATION" || m.statut === "ATTENTE_PV1");
  const reecriture = useAction();
  const bloquantesSansReponse = v.questions.filter((q) => q.bloquante && !q.reponse && !q.decision);
  const [selQuestions, setSelQuestions] = useState<number[]>([]);
  const [selCriteres, setSelCriteres] = useState<number[]>([]);
  const basculer = (liste: number[], fixer: (l: number[]) => void, id: number) =>
    fixer(liste.includes(id) ? liste.filter((x) => x !== id) : [...liste, id]);
  const ecartable = modifiable && !v.figee && m.statut === "ATTENTE_PV1";
  const sansReponse = v.questions.filter((q) => !q.reponse);

  if (m.statut === "ANALYSE_EN_COURS" && !v.defauts.length) {
    return <div className="vide">L'analyse est en cours. Les défauts et les questions apparaîtront ici.</div>;
  }

  return (
    <div className="pile" style={{ padding: 18 }}>
      {/* --- Analyser ----------------------------------------------------- */}
      <section>
        <div className="rangee" style={{ justifyContent: "space-between", marginBottom: 10 }}>
          <h2>Analyse de l'exigence</h2>
          {v.score_clarte !== null && (
            <div className="score" title="Calculé par script : 100 − 25 par défaut bloquant − 10 par majeur − 3 par mineur">
              <span className="discret-texte">Clarté</span>
              <div className="score-jauge"><div style={{ width: v.score_clarte + "%", background: couleurScore(v.score_clarte) }} /></div>
              <span className="score-valeur">{v.score_clarte}<span className="discret-texte">/100</span></span>
            </div>
          )}
        </div>
        {v.code_controle_revue === 1 && (
          <div className="message-erreur" style={{ marginBottom: 10 }}>
            Le contrôle par script a trouvé des citations absentes du texte d'origine : elles sont marquées en rouge.
            Vérifiez ces défauts avant de vous y fier.
          </div>
        )}
        <div className="panneau">
          {v.defauts.length === 0 && <div className="vide">Aucun défaut relevé.</div>}
          {v.defauts.map((d) => (
            <div key={d.id} className="defaut">
              <div className="rangee">
                <span className="ref">{d.code}</span>
                <strong>{d.categorie}</strong>
                <span className={"gravite-" + d.gravite}>{d.gravite}</span>
                {d.section && <span className="discret-texte">{d.section}</span>}
              </div>
              {d.citation && (
                <div className={"citation" + (d.citation_verifiee ? "" : " non-verifiee")}>
                  « {d.citation} »
                  {!d.citation_verifiee && <div style={{ color: "var(--alerte)", fontSize: "0.8rem" }}>Citation introuvable dans le texte d'origine</div>}
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* --- Clarifier ---------------------------------------------------- */}
      <section>
        <div className="rangee" style={{ justifyContent: "space-between", marginBottom: 10 }}>
          <div>
            <h2>Questions métier</h2>
            <p className="discret-texte">
              Vos réponses sont les seules sources que l'agent peut utiliser, en plus du texte d'origine.
            </p>
          </div>
        </div>
        {clarification && selQuestions.length > 0 && (
          <BarreDecision nombre={selQuestions.length} objet="question" options={[
            { valeur: "HORS_PERIMETRE", libelle: "Déclarer hors périmètre" },
            { valeur: "REPORTEE", libelle: "Reporter" }]}
            appliquer={async (decision, motif) => {
              await api(`/missions/${m.id}/questions-decision`,
                { methode: "PUT", corps: { ids: selQuestions, decision, motif } });
              setSelQuestions([]); recharger();
            }} annuler={() => setSelQuestions([])} />
        )}
        <div className="panneau">
          {v.questions.length === 0 && <div className="vide">Aucune question.</div>}
          {clarification && sansReponse.length > 1 && (
            <div className="question" style={{ padding: "8px 18px" }}>
              <label className="rangee discret-texte" style={{ gap: 8 }}>
                <input type="checkbox"
                       checked={sansReponse.every((q) => selQuestions.includes(q.id))}
                       onChange={(e) => setSelQuestions(e.target.checked ? sansReponse.map((q) => q.id) : [])} />
                Sélectionner les {sansReponse.length} questions sans réponse
              </label>
            </div>
          )}
          {v.questions.map((q) => (
            <QuestionLigne key={q.id} q={q} missionId={m.id} modifiable={clarification} recharger={recharger}
                           selectionnee={selQuestions.includes(q.id)}
                           basculer={() => basculer(selQuestions, setSelQuestions, q.id)} />
          ))}
          {clarification && <Precision missionId={m.id} recharger={recharger} />}
        </div>
        {clarification && (
          <div className="pile" style={{ marginTop: 12, gap: 8 }}>
            {bloquantesSansReponse.length > 0 && (
              <p className="discret-texte">
                Traitez les questions bloquantes ({bloquantesSansReponse.map((q) => q.code).join(", ")}) pour lancer
                la réécriture : répondez-y, ou déclarez-les hors périmètre ou reportées.
              </p>
            )}
            <MessageErreur erreur={reecriture.erreur} />
            <div>
              <button className="bouton principal"
                      disabled={reecriture.enCours || occupe || bloquantesSansReponse.length > 0}
                      onClick={() => reecriture.lancer(async () => {
                        const r = await api<{ tache_id: number }>(`/missions/${m.id}/reecriture`, { methode: "POST" });
                        lancerTache(r.tache_id);
                      })}>
                {v.texte_reecrit ? "Relancer la réécriture avec ces réponses" : "Réécrire l'exigence"}
              </button>
            </div>
          </div>
        )}
      </section>

      {/* --- Réécrire ----------------------------------------------------- */}
      {v.texte_reecrit && (
        <section>
          <h2 style={{ marginBottom: 10 }}>Exigence réécrite</h2>
          <div className="cote-a-cote">
            <div>
              <div className="etiquette" style={{ marginBottom: 6 }}>Texte d'origine</div>
              <div className="texte-exigence">{v.texte}</div>
            </div>
            <div>
              <div className="etiquette" style={{ marginBottom: 6 }}>Proposition de l'agent</div>
              <div className="texte-exigence">{v.texte_reecrit}</div>
            </div>
          </div>
          <h3 style={{ margin: "18px 0 8px" }}>Critères d'acceptation</h3>
          {ecartable && selCriteres.length > 0 && (
            <BarreDecision nombre={selCriteres.length} objet="critère"
              options={[{ valeur: "ECARTER", libelle: "Écarter" }]}
              appliquer={async (_d, motif) => {
                await api(`/missions/${m.id}/criteres`, { methode: "DELETE", corps: { ids: selCriteres, motif } });
                setSelCriteres([]); recharger();
              }} annuler={() => setSelCriteres([])} />
          )}
          <div className="panneau">
            {ecartable && v.criteres.filter((c) => c.statut === "HYPOTHESE").length > 1 && (
              <div className="critere" style={{ padding: "8px 18px" }}>
                <label className="rangee discret-texte" style={{ gap: 8 }}>
                  <input type="checkbox"
                         checked={v.criteres.filter((c) => c.statut === "HYPOTHESE").every((c) => selCriteres.includes(c.id))}
                         onChange={(e) => setSelCriteres(e.target.checked
                           ? v.criteres.filter((c) => c.statut === "HYPOTHESE").map((c) => c.id) : [])} />
                  Sélectionner toutes les hypothèses
                </label>
              </div>
            )}
            {v.criteres.map((c) => (
              <CritereLigne key={c.id} c={c} missionId={m.id} ecartable={ecartable} recharger={recharger}
                            selectionne={selCriteres.includes(c.id)}
                            basculer={() => basculer(selCriteres, setSelCriteres, c.id)} />
            ))}
          </div>
          {v.points_ouverts.length > 0 && (
            <>
              <h3 style={{ margin: "18px 0 4px" }}>Points ouverts</h3>
              <p className="discret-texte" style={{ marginBottom: 8 }}>
                Sujets que l'agent n'a pas transformés en critères, faute de source. Ils ne bloquent pas PV-1 :
                le valideur les voit au moment de décider, et ils restent hors des cas de test.
              </p>
              <div className="panneau">
                <ul style={{ margin: 0, padding: "12px 18px 12px 34px" }}>
                  {v.points_ouverts.map((p) => <li key={p}>{p}</li>)}
                </ul>
              </div>
            </>
          )}
        </section>
      )}

      {!v.texte_reecrit && (
        <section>
          <h2 style={{ marginBottom: 10 }}>Texte d'origine</h2>
          <div className="texte-exigence">{v.texte}</div>
        </section>
      )}
      <p className="discret-texte">Empreinte SHA-256 de la version : <code>{v.empreinte.slice(0, 16)}…</code></p>
    </div>
  );
}

function QuestionLigne({ q, missionId, modifiable, recharger, selectionnee, basculer }: {
  q: Question; missionId: number; modifiable: boolean; recharger: () => void;
  selectionnee: boolean; basculer: () => void;
}) {
  const [reponse, setReponse] = useState(q.reponse ?? "");
  const [decider, setDecider] = useState<"HORS_PERIMETRE" | "REPORTEE" | null>(null);
  const [motif, setMotif] = useState("");
  const action = useAction();
  const change = reponse.trim() !== (q.reponse ?? "");
  const appliquer = (decision: string | null, m: string) => action.lancer(async () => {
    await api(`/missions/${missionId}/questions-decision`,
      { methode: "PUT", corps: { ids: [q.id], decision, motif: m } });
    setDecider(null); setMotif(""); recharger();
  });
  return (
    <div className="question">
      <div className="question-texte">
        {modifiable && !q.reponse && (
          <input type="checkbox" checked={selectionnee} onChange={basculer} aria-label={"Sélectionner " + q.code} />
        )}
        <span className="ref">{q.code}</span>
        <span style={{ flex: 1 }}>{q.question}</span>
        {q.bloquante && <Pastille ton="alerte">Bloquante</Pastille>}
        {q.ajoutee_par_humain && <Pastille ton="neutre">Précision ajoutée</Pastille>}
        {q.decision && <Pastille ton="attente">{DECISION_QUESTION[q.decision]}</Pastille>}
      </div>
      {q.decision ? (
        <div className="rangee">
          <span className="discret-texte">
            {DECISION_QUESTION[q.decision]} le {date(q.decide_le)} : « {q.motif_decision} »
          </span>
          {modifiable && (
            <button className="bouton discret petit" disabled={action.enCours}
                    onClick={() => appliquer(null, "")}>Annuler la décision</button>
          )}
          <MessageErreur erreur={action.erreur} />
        </div>
      ) : modifiable ? (
        <>
          <textarea rows={2} value={reponse} onChange={(e) => setReponse(e.target.value)}
                    placeholder="Votre réponse (ou celle du Product Owner)" aria-label={"Réponse à " + q.code} />
          <div className="rangee">
            <button className="bouton petit" disabled={!change || action.enCours}
                    onClick={() => action.lancer(async () => {
                      await api(`/missions/${missionId}/questions/${q.id}`, { methode: "PUT", corps: { reponse } });
                      recharger();
                    })}>Enregistrer la réponse</button>
            {q.repondu_le && !change && <span className="discret-texte">Répondu le {date(q.repondu_le)}</span>}
            {!q.reponse && !decider && <>
              <button className="bouton discret petit" onClick={() => setDecider("HORS_PERIMETRE")}>Hors périmètre</button>
              <button className="bouton discret petit" onClick={() => setDecider("REPORTEE")}>Reporter</button>
            </>}
          </div>
          {decider && (
            <div className="rangee">
              <input type="text" value={motif} onChange={(e) => setMotif(e.target.value)} style={{ flex: 1, minWidth: 200 }}
                     placeholder={decider === "HORS_PERIMETRE" ? "Pourquoi est-ce hors périmètre ?" : "Pourquoi reporter ? (ex. en attente du PO)"}
                     aria-label={"Motif pour " + q.code} />
              <button className="bouton petit" disabled={!motif.trim() || action.enCours}
                      onClick={() => appliquer(decider, motif)}>{DECISION_QUESTION[decider]}</button>
              <button className="bouton discret petit" onClick={() => setDecider(null)}>Annuler</button>
            </div>
          )}
          <MessageErreur erreur={action.erreur} />
        </>
      ) : (
        <div className={q.reponse ? "" : "discret-texte"}>{q.reponse ?? "Sans réponse"}</div>
      )}
    </div>
  );
}

/** Barre d'action groupée : une décision et un motif communs, une ligne de journal par élément. */
function BarreDecision({ nombre, objet, options, appliquer, annuler }: {
  nombre: number; objet: string; options: { valeur: string; libelle: string }[];
  appliquer: (decision: string, motif: string) => Promise<void>; annuler: () => void;
}) {
  const [motif, setMotif] = useState("");
  const action = useAction();
  return (
    <div className="message-info pile" style={{ gap: 8, marginBottom: 10 }}>
      <strong>{nombre} {objet}{nombre > 1 ? "s" : ""} sélectionné{objet === "question" ? "e" : ""}{nombre > 1 ? "s" : ""}</strong>
      <div className="rangee">
        <input type="text" value={motif} onChange={(e) => setMotif(e.target.value)} style={{ flex: 1, minWidth: 220 }}
               placeholder="Motif commun (obligatoire)" aria-label="Motif commun" />
        {options.map((o) => (
          <button key={o.valeur} className="bouton petit" disabled={!motif.trim() || action.enCours}
                  onClick={() => action.lancer(() => appliquer(o.valeur, motif))}>{o.libelle}</button>
        ))}
        <button className="bouton discret petit" onClick={annuler}>Tout désélectionner</button>
      </div>
      <span className="discret-texte">Chaque élément garde sa propre ligne dans le journal QA.</span>
      <MessageErreur erreur={action.erreur} />
    </div>
  );
}

function Precision({ missionId, recharger }: { missionId: number; recharger: () => void }) {
  const [ouvert, setOuvert] = useState(false);
  const [question, setQuestion] = useState("");
  const [reponse, setReponse] = useState("");
  const action = useAction();
  if (!ouvert) {
    return (
      <div className="question">
        <div>
          <button className="bouton discret petit" onClick={() => setOuvert(true)}>Ajouter une précision</button>
          <span className="discret-texte"> — une information que l'agent n'a pas demandée mais qui compte.</span>
        </div>
      </div>
    );
  }
  return (
    <form className="question" onSubmit={(e) => {
      e.preventDefault();
      action.lancer(async () => {
        await api(`/missions/${missionId}/questions`, { methode: "POST", corps: { question, reponse } });
        setQuestion(""); setReponse(""); setOuvert(false);
        recharger();
      });
    }}>
      <input type="text" required placeholder="Sujet, ex. : Notification après réinitialisation"
             value={question} onChange={(e) => setQuestion(e.target.value)} aria-label="Sujet de la précision" />
      <textarea rows={2} required placeholder="La règle, ex. : un e-mail de confirmation est envoyé"
                value={reponse} onChange={(e) => setReponse(e.target.value)} aria-label="Contenu de la précision" />
      <div className="rangee">
        <button className="bouton petit" disabled={action.enCours}>Ajouter la précision</button>
        <button type="button" className="bouton discret petit" onClick={() => setOuvert(false)}>Annuler</button>
      </div>
      <MessageErreur erreur={action.erreur} />
    </form>
  );
}

function CritereLigne({ c, missionId, ecartable, recharger, selectionne, basculer }: {
  c: Critere; missionId: number; ecartable: boolean; recharger: () => void;
  selectionne: boolean; basculer: () => void;
}) {
  const [ecarter, setEcarter] = useState(false);
  const [motif, setMotif] = useState("");
  const action = useAction();
  return (
    <div className={"critere" + (c.statut === "HYPOTHESE" ? " hypothese" : "")}>
      <div className="rangee" style={{ alignItems: "baseline" }}>
        {ecartable && <input type="checkbox" checked={selectionne} onChange={basculer} aria-label={"Sélectionner " + c.code} />}
        <span className="ref">{c.code}</span>
        <span style={{ flex: 1 }}>{c.texte}</span>
        {c.statut === "HYPOTHESE"
          ? <Pastille ton="attente">Hypothèse</Pastille>
          : <Pastille ton="succes">Sourcé</Pastille>}
      </div>
      <div className="sources">
        {c.sources.map((s) => <span key={s} className="source">{s}</span>)}
        {c.sources_rejetees.map((s) => (
          <span key={s} className="source rejetee" title="Source refusée par le contrôle : introuvable ou sans réponse">{s}</span>
        ))}
        {!c.sources.length && !c.sources_rejetees.length && <span className="discret-texte">Aucune source citée</span>}
      </div>
      {c.statut === "HYPOTHESE" && (
        <p className="discret-texte" style={{ marginTop: 6 }}>
          Ni le texte d'origine ni vos réponses ne justifient ce critère. Répondez à la question qui manque puis relancez
          la réécriture, ou écartez-le.
        </p>
      )}
      {ecartable && !ecarter && (
        <button className="bouton discret petit" style={{ marginTop: 6 }} onClick={() => setEcarter(true)}>Écarter ce critère</button>
      )}
      {ecarter && (
        <div className="rangee" style={{ marginTop: 8 }}>
          <input type="text" placeholder="Pourquoi l'écarter ?" value={motif} onChange={(e) => setMotif(e.target.value)}
                 style={{ flex: 1, minWidth: 200 }} aria-label={"Motif pour écarter " + c.code} />
          <button className="bouton rejeter petit" disabled={!motif.trim() || action.enCours}
                  onClick={() => action.lancer(async () => {
                    await api(`/missions/${missionId}/criteres/${c.id}`, { methode: "DELETE", corps: { motif } });
                    recharger();
                  })}>Écarter</button>
          <button className="bouton discret petit" onClick={() => setEcarter(false)}>Annuler</button>
          <MessageErreur erreur={action.erreur} />
        </div>
      )}
    </div>
  );
}
