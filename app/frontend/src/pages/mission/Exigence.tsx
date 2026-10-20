import { useState } from "react";
import { api, type Defaut, type ElementSource, type Mission, type PhraseCouverture, type Question, type Version } from "../../api";
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
        <TableDefauts missionId={m.id} defauts={v.defauts} questions={v.questions}
                      modifiable={clarification} recharger={recharger} />
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
          {v.questions.filter((q) => q.nature !== "COMPLEMENTAIRE").map((q) => (
            <QuestionLigne key={q.id} q={q} missionId={m.id} modifiable={clarification} recharger={recharger}
                           selectionnee={selQuestions.includes(q.id)}
                           basculer={() => basculer(selQuestions, setSelQuestions, q.id)} />
          ))}
          {clarification && <Precision missionId={m.id} recharger={recharger} />}
        </div>
        {v.questions.some((q) => q.nature === "COMPLEMENTAIRE") && (
          <>
            <h3 style={{ margin: "16px 0 4px" }}>Questions complémentaires</h3>
            <p className="discret-texte" style={{ marginBottom: 8 }}>
              Règles absentes du texte, repérées par l'agent. Elles ne pèsent pas dans le score et ne bloquent pas la
              réécriture ; vos réponses deviennent des sources, comme les autres.
            </p>
            <div className="panneau">
              {v.questions.filter((q) => q.nature === "COMPLEMENTAIRE").map((q) => (
                <QuestionLigne key={q.id} q={q} missionId={m.id} modifiable={clarification} recharger={recharger}
                               selectionnee={selQuestions.includes(q.id)}
                               basculer={() => basculer(selQuestions, setSelQuestions, q.id)} />
              ))}
            </div>
          </>
        )}
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
          <h2 style={{ marginBottom: 10 }}>User Story réécrite</h2>
          <div className="cote-a-cote">
            <div>
              <div className="etiquette" style={{ marginBottom: 6 }}>Texte d'origine</div>
              <TexteOrigine texte={v.texte} couverture={v.couverture} />
            </div>
            <div>
              <div className="etiquette" style={{ marginBottom: 6 }}>Proposition de l'agent</div>
              <div className="texte-exigence">{v.texte_reecrit}</div>
            </div>
          </div>

          {v.couverture.length > 0 && (
            <Couverture missionId={m.id} phrases={v.couverture} modifiable={ecartable} recharger={recharger} />
          )}

          <h3 style={{ margin: "18px 0 4px" }}>Règles métier</h3>
          <p className="discret-texte" style={{ marginBottom: 8 }}>
            Ce que le métier impose. Chaque règle cite sa source ; c'est la partie à faire relire par le métier.
          </p>
          <ListeElements objet="règle" chemin="regles" elements={v.regles} missionId={m.id}
                         ecartable={ecartable} recharger={recharger} vide="Aucune règle métier dans cette version."
                         lien={(e) => {
                           const crit = v.regles.find((r) => r.id === e.id)?.criteres ?? [];
                           return crit.length ? "Vérifiée par " + crit.join(", ") : "Vérifiée par aucun critère";
                         }} />

          <h3 style={{ margin: "18px 0 4px" }}>Critères d'acceptation</h3>
          <p className="discret-texte" style={{ marginBottom: 8 }}>Ce qu'on vérifie. Les cas de test seront conçus à partir de ces critères.</p>
          <ListeElements objet="critère" chemin="criteres" elements={v.criteres} missionId={m.id}
                         ecartable={ecartable} recharger={recharger} vide="Aucun critère."
                         lien={(e) => {
                           const regs = v.criteres.find((c) => c.id === e.id)?.regles ?? [];
                           const ecartees = regs.filter((r) => !v.regles.some((x) => x.code === r));
                           if (!regs.length) return null;
                           return "Vérifie " + regs.join(", ") + (ecartees.length ? " — règle écartée : " + ecartees.join(", ") : "");
                         }} />

          {v.points_ouverts.length > 0 && (
            <>
              <h3 style={{ margin: "18px 0 4px" }}>Points ouverts</h3>
              <p className="discret-texte" style={{ marginBottom: 8 }}>
                Sujets que l'agent n'a transformés ni en règle ni en critère, faute de source. Ils ne bloquent pas PV-1 :
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
        {q.nature === "COMPLEMENTAIRE" && <Pastille ton="neutre">Complémentaire</Pastille>}
        {q.decision && <Pastille ton="attente">{DECISION_QUESTION[q.decision]}</Pastille>}
      </div>
      {q.nature === "COMPLEMENTAIRE" && (q.sujet || q.pourquoi) && (
        <div className="discret-texte">
          {q.sujet && <strong>{q.sujet}</strong>}{q.sujet && q.pourquoi && " — "}{q.pourquoi}
        </div>
      )}
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

const FEMININ = ["question", "règle", "phrase"];  // « défaut » reste au masculin

/** Barre d'action groupée : une décision et un motif communs, une ligne de journal par élément. */
function BarreDecision({ nombre, objet, options, appliquer, annuler }: {
  nombre: number; objet: string; options: { valeur: string; libelle: string }[];
  appliquer: (decision: string, motif: string) => Promise<void>; annuler: () => void;
}) {
  const [motif, setMotif] = useState("");
  const action = useAction();
  return (
    <div className="message-info pile" style={{ gap: 8, marginBottom: 10 }}>
      <strong>{nombre} {objet}{nombre > 1 ? "s" : ""} sélectionné{FEMININ.includes(objet) ? "e" : ""}{nombre > 1 ? "s" : ""}</strong>
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

const CLASSE_PHRASE: Record<string, string> = {
  COUVERTE: "couverte", NON_COUVERTE: "non-couverte", JUSTIFIEE: "justifiee", TITRE: "titre", CADRE: "titre",
};

/** Texte d'origine, phrase par phrase, coloré selon sa reprise (RA-48). */
function TexteOrigine({ texte, couverture }: { texte: string; couverture: PhraseCouverture[] }) {
  if (!couverture.length) return <div className="texte-exigence">{texte}</div>;
  return (
    <div className="texte-exigence phrases-origine" style={{ whiteSpace: "normal" }}>
      {couverture.map((p) => (
        <span key={p.id}>
          <span className={"phrase " + CLASSE_PHRASE[p.statut]}
                title={p.statut === "NON_COUVERTE" ? `Phrase ${p.numero} : reprise par aucune règle ni aucun critère`
                  : p.statut === "JUSTIFIEE" ? `Non reprise volontairement : ${p.motif}`
                  : p.statut === "TITRE" ? "Titre : non contrôlé"
                  : p.statut === "CADRE" ? "Rôle ou bénéfice de la User Story : repris par la User Story réécrite, non contrôlé"
                  : `Phrase ${p.numero} : reprise`}>
            {p.texte}
          </span>{" "}
        </span>
      ))}
    </div>
  );
}

function Couverture({ missionId, phrases, modifiable, recharger }: {
  missionId: number; phrases: PhraseCouverture[]; modifiable: boolean; recharger: () => void;
}) {
  const [sel, setSel] = useState<number[]>([]);
  const annuler = useAction();
  const controlees = phrases.filter((p) => p.statut !== "TITRE" && p.statut !== "CADRE");
  const cadrage = phrases.filter((p) => p.statut === "CADRE").length;
  const reprises = controlees.filter((p) => p.statut === "COUVERTE").length;
  const aTraiter = controlees.filter((p) => p.statut === "NON_COUVERTE");
  const justifiees = controlees.filter((p) => p.statut === "JUSTIFIEE");
  return (
    <div style={{ marginTop: 12 }}>
      <div className="legende">
        <strong>{reprises}/{controlees.length} phrases reprises</strong>
        <span><span className="phrase couverte">reprise</span></span>
        <span><span className="phrase non-couverte">non reprise</span></span>
        <span><span className="phrase justifiee">non reprise, justifiée</span></span>
        {cadrage > 0 && <span><span className="phrase titre">cadrage (rôle, bénéfice) : non contrôlé</span></span>}
      </div>
      {(aTraiter.length > 0 || justifiees.length > 0) && (
        <div className="pile" style={{ marginTop: 10, gap: 8 }}>
          {modifiable && sel.length > 0 && (
            <BarreDecision nombre={sel.length} objet="phrase"
              options={[{ valeur: "JUSTIFIER", libelle: "Non reprise volontairement" }]}
              appliquer={async (_d, motif) => {
                await api(`/missions/${missionId}/phrases-justification`, { methode: "PUT", corps: { ids: sel, motif } });
                setSel([]); recharger();
              }} annuler={() => setSel([])} />
          )}
          <div className="panneau">
            {aTraiter.length > 0 && (
              <div className="critere hypothese">
                <p className="discret-texte" style={{ marginBottom: 6 }}>
                  Ces phrases du texte d'origine ne sont reprises par aucune règle ni aucun critère. Relancez la réécriture
                  après avoir précisé le besoin, ou déclarez-les non reprises volontairement, avec un motif.
                </p>
                {modifiable && aTraiter.length > 1 && (
                  <label className="rangee discret-texte" style={{ gap: 8, marginBottom: 4 }}>
                    <input type="checkbox" checked={aTraiter.every((p) => sel.includes(p.id))}
                           onChange={(e) => setSel(e.target.checked ? aTraiter.map((p) => p.id) : [])} />
                    Sélectionner les {aTraiter.length} phrases non reprises
                  </label>
                )}
                {aTraiter.map((p) => (
                  <label key={p.id} className="rangee" style={{ gap: 8, alignItems: "baseline" }}>
                    {modifiable && (
                      <input type="checkbox" checked={sel.includes(p.id)} aria-label={"Sélectionner la phrase " + p.numero}
                             onChange={() => setSel(sel.includes(p.id) ? sel.filter((x) => x !== p.id) : [...sel, p.id])} />
                    )}
                    <span className="ref">Phrase {p.numero}</span>
                    <span>« {p.texte} »</span>
                  </label>
                ))}
              </div>
            )}
            {justifiees.map((p) => (
              <div key={p.id} className="critere">
                <div className="rangee" style={{ alignItems: "baseline" }}>
                  <span className="ref">Phrase {p.numero}</span>
                  <span style={{ flex: 1 }}>« {p.texte} »</span>
                  <Pastille ton="neutre">Non reprise, justifiée</Pastille>
                </div>
                <div className="rangee">
                  <span className="discret-texte">Le {date(p.justifie_le)} : « {p.motif} »</span>
                  {modifiable && (
                    <button className="bouton discret petit" disabled={annuler.enCours}
                            onClick={() => annuler.lancer(async () => {
                              await api(`/missions/${missionId}/phrases-justification`,
                                { methode: "PUT", corps: { ids: [p.id], motif: null } });
                              recharger();
                            })}>Annuler la justification</button>
                  )}
                </div>
              </div>
            ))}
          </div>
          <MessageErreur erreur={annuler.erreur} />
        </div>
      )}
    </div>
  );
}

/** Règles métier ou critères : même contrôle des sources, même écart motivé et groupé. */
function ListeElements({ objet, chemin, elements, missionId, ecartable, recharger, vide, lien }: {
  objet: "règle" | "critère"; chemin: "regles" | "criteres"; elements: ElementSource[]; missionId: number;
  ecartable: boolean; recharger: () => void; vide: string; lien: (e: ElementSource) => string | null;
}) {
  const [sel, setSel] = useState<number[]>([]);
  const hypotheses = elements.filter((e) => e.statut === "HYPOTHESE");
  const ecarter = async (ids: number[], motif: string) => {
    await api(`/missions/${missionId}/${chemin}`, { methode: "DELETE", corps: { ids, motif } });
    setSel([]); recharger();
  };
  return (
    <>
      {ecartable && sel.length > 0 && (
        <BarreDecision nombre={sel.length} objet={objet} options={[{ valeur: "ECARTER", libelle: "Écarter" }]}
                       appliquer={(_d, motif) => ecarter(sel, motif)} annuler={() => setSel([])} />
      )}
      <div className="panneau">
        {elements.length === 0 && <div className="vide">{vide}</div>}
        {ecartable && hypotheses.length > 1 && (
          <div className="critere" style={{ padding: "8px 18px" }}>
            <label className="rangee discret-texte" style={{ gap: 8 }}>
              <input type="checkbox" checked={hypotheses.every((e) => sel.includes(e.id))}
                     onChange={(ev) => setSel(ev.target.checked ? hypotheses.map((e) => e.id) : [])} />
              Sélectionner {objet === "règle" ? "toutes les règles hypothèses" : "toutes les hypothèses"}
            </label>
          </div>
        )}
        {elements.map((e) => (
          <ElementLigne key={e.id} e={e} objet={objet} ecartable={ecartable} lien={lien(e)}
                        selectionne={sel.includes(e.id)}
                        basculer={() => setSel(sel.includes(e.id) ? sel.filter((x) => x !== e.id) : [...sel, e.id])}
                        ecarter={(motif) => ecarter([e.id], motif)} />
        ))}
      </div>
    </>
  );
}

function ElementLigne({ e, objet, ecartable, lien, selectionne, basculer, ecarter }: {
  e: ElementSource; objet: "règle" | "critère"; ecartable: boolean; lien: string | null;
  selectionne: boolean; basculer: () => void; ecarter: (motif: string) => Promise<void>;
}) {
  const [ouvert, setOuvert] = useState(false);
  const [motif, setMotif] = useState("");
  const action = useAction();
  const alerte = lien?.includes("écartée") || lien === "Vérifiée par aucun critère";
  return (
    <div className={"critere" + (e.statut === "HYPOTHESE" ? " hypothese" : "")}>
      <div className="rangee" style={{ alignItems: "baseline" }}>
        {ecartable && <input type="checkbox" checked={selectionne} onChange={basculer} aria-label={"Sélectionner " + e.code} />}
        <span className="ref">{e.code}</span>
        <span style={{ flex: 1 }}>{e.texte}</span>
        {e.statut === "HYPOTHESE"
          ? <Pastille ton="attente">Hypothèse</Pastille>
          : <Pastille ton="succes">Sourcé{objet === "règle" ? "e" : ""}</Pastille>}
      </div>
      <div className="sources">
        {e.sources.map((s) => <span key={s} className="source">{s}</span>)}
        {e.sources_rejetees.map((s) => (
          <span key={s} className="source rejetee" title="Source refusée par le contrôle : introuvable, sans réponse ou règle non sourcée">{s}</span>
        ))}
        {!e.sources.length && !e.sources_rejetees.length && objet === "règle" && <span className="discret-texte">Aucune source citée</span>}
      </div>
      {lien && <div className="lien-element" style={alerte ? { color: "var(--alerte)" } : undefined}>{lien}</div>}
      {e.statut === "HYPOTHESE" && (
        <p className="discret-texte" style={{ marginTop: 6 }}>
          Ni le texte d'origine ni vos réponses ne justifient entièrement {objet === "règle" ? "cette règle" : "ce critère"}.
          Répondez à la question qui manque puis relancez la réécriture, ou écartez-{objet === "règle" ? "la" : "le"}.
        </p>
      )}
      {ecartable && !ouvert && (
        <button className="bouton discret petit" style={{ marginTop: 6 }} onClick={() => setOuvert(true)}>
          Écarter {objet === "règle" ? "cette règle" : "ce critère"}
        </button>
      )}
      {ouvert && (
        <div className="rangee" style={{ marginTop: 8 }}>
          <input type="text" placeholder="Pourquoi l'écarter ?" value={motif} onChange={(ev) => setMotif(ev.target.value)}
                 style={{ flex: 1, minWidth: 200 }} aria-label={"Motif pour écarter " + e.code} />
          <button className="bouton rejeter petit" disabled={!motif.trim() || action.enCours}
                  onClick={() => action.lancer(() => ecarter(motif))}>Écarter</button>
          <button className="bouton discret petit" onClick={() => setOuvert(false)}>Annuler</button>
          <MessageErreur erreur={action.erreur} />
        </div>
      )}
    </div>
  );
}

const STATUT_DEFAUT: Record<string, { libelle: string; ton: "neutre" | "succes" | "attente" }> = {
  A_EXAMINER: { libelle: "À examiner", ton: "attente" },
  CONFIRME: { libelle: "Confirmé", ton: "succes" },
  ECARTE: { libelle: "Écarté", ton: "neutre" },
};

/** Tableau de revue QA-REV-02 : extrait, type, criticité motivée, question, statut de validation. */
function TableDefauts({ missionId, defauts, questions, modifiable, recharger }: {
  missionId: number; defauts: Defaut[]; questions: Question[]; modifiable: boolean; recharger: () => void;
}) {
  const [sel, setSel] = useState<number[]>([]);
  const [ouvert, setOuvert] = useState<{ id: number; mode: "ECARTER" | "CRITICITE" } | null>(null);
  const action = useAction();
  if (!defauts.length) return <div className="panneau"><div className="vide">Aucun défaut relevé.</div></div>;
  const aExaminer = defauts.filter((d) => !d.validation);
  const valider = (ids: number[], act: string, motif = "") => action.lancer(async () => {
    await api(`/missions/${missionId}/defauts-validation`, { methode: "PUT", corps: { ids, action: act, motif } });
    setSel([]); setOuvert(null); recharger();
  });
  return (
    <div className="pile" style={{ gap: 8 }}>
      <div className="rangee" style={{ justifyContent: "space-between" }}>
        <span className="discret-texte">
          {aExaminer.length
            ? `${aExaminer.length} défaut${aExaminer.length > 1 ? "s" : ""} à examiner : l'analyse de l'agent est une aide, c'est vous qui validez.`
            : "Tous les défauts ont été examinés."}
        </span>
        {modifiable && aExaminer.length > 1 && (
          <button className="bouton petit" disabled={action.enCours}
                  onClick={() => valider(aExaminer.map((d) => d.id), "CONFIRMER")}>
            Confirmer les {aExaminer.length} défauts à examiner
          </button>
        )}
      </div>
      {modifiable && sel.length > 0 && (
        <BarreDecision nombre={sel.length} objet="défaut"
          options={[{ valeur: "ECARTER", libelle: "Écarter (faux positif)" }]}
          appliquer={async (_d, motif) => {
            await api(`/missions/${missionId}/defauts-validation`,
              { methode: "PUT", corps: { ids: sel, action: "ECARTER", motif } });
            setSel([]); recharger();
          }} annuler={() => setSel([])} />
      )}
      <MessageErreur erreur={action.erreur} />
      <div className="panneau table-defile">
        <table className="table-defauts">
          <thead>
            <tr>
              {modifiable && <th style={{ width: 28 }} />}
              <th style={{ width: 70 }}>Réf.</th>
              <th>Extrait source, constat et question</th>
              <th style={{ width: 160 }}>Type et criticité</th>
              <th style={{ width: 125 }}>Statut</th>
            </tr>
          </thead>
          <tbody>
            {defauts.map((d) => {
              const q = questions.find((x) => x.defaut_id === d.id);
              const statut = STATUT_DEFAUT[d.validation ?? "A_EXAMINER"];
              return [
                <tr key={d.id} className={d.validation === "ECARTE" ? "ecarte" : ""}>
                  {modifiable && (
                    <td>{d.validation !== "ECARTE" && (
                      <input type="checkbox" checked={sel.includes(d.id)} aria-label={"Sélectionner " + d.code}
                             onChange={() => setSel(sel.includes(d.id) ? sel.filter((x) => x !== d.id) : [...sel, d.id])} />
                    )}</td>
                  )}
                  <td><span className="ref">{d.code}</span>{d.section && <div className="sous">{d.section}</div>}</td>
                  <td>
                    {d.citation && (
                      <div className={"citation" + (d.citation_verifiee ? "" : " non-verifiee")}>
                        « {d.citation} »
                        {!d.citation_verifiee && <div style={{ color: "var(--alerte)", fontSize: "0.8rem" }}>Citation introuvable dans le texte d'origine</div>}
                      </div>
                    )}
                    {d.constat && <div className="constat">{d.constat}</div>}
                    {q && <div style={{ marginTop: 6 }}><span className="ref">{q.code}</span> {q.question}</div>}
                  </td>
                  <td>
                    <div><strong>{d.categorie}</strong></div>
                    <div className={"gravite-" + d.gravite}>
                      {d.gravite}{d.gravite_initiale && <span className="discret-texte"> (agent : {d.gravite_initiale})</span>}
                    </div>
                    {d.gravite === "Bloquante" && <div className="sous" style={{ color: "var(--alerte)" }}>Bloque la conception des tests</div>}
                    {d.justification && <div className="justif">{d.justification}</div>}
                    {d.motif_requalification && <div className="justif">Requalifié : « {d.motif_requalification} »</div>}
                  </td>
                  <td>
                    <Pastille ton={statut.ton}>{statut.libelle}</Pastille>
                    {d.validation === "ECARTE" && d.motif_validation && <div className="sous">« {d.motif_validation} »</div>}
                    {modifiable && (
                      <div className="pile" style={{ gap: 2, marginTop: 6, alignItems: "flex-start" }}>
                        {!d.validation && (
                          <button className="bouton discret petit" disabled={action.enCours}
                                  onClick={() => valider([d.id], "CONFIRMER")}>Confirmer</button>
                        )}
                        {d.validation !== "ECARTE" && (
                          <button className="bouton discret petit" onClick={() => setOuvert({ id: d.id, mode: "ECARTER" })}>Écarter…</button>
                        )}
                        {d.validation !== "ECARTE" && (
                          <button className="bouton discret petit" onClick={() => setOuvert({ id: d.id, mode: "CRITICITE" })}>Criticité…</button>
                        )}
                        {d.validation && (
                          <button className="bouton discret petit" disabled={action.enCours}
                                  onClick={() => valider([d.id], "ANNULER")}>Remettre à examiner</button>
                        )}
                      </div>
                    )}
                  </td>
                </tr>,
                ouvert?.id === d.id && (
                  <tr key={d.id + "-f"} className="formulaire">
                    <td colSpan={modifiable ? 5 : 4}>
                      <FormulaireDefaut defaut={d} mode={ouvert.mode} missionId={missionId}
                                        fermer={() => setOuvert(null)} apres={() => { setOuvert(null); recharger(); }} />
                    </td>
                  </tr>
                ),
              ];
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function FormulaireDefaut({ defaut: d, mode, missionId, fermer, apres }: {
  defaut: Defaut; mode: "ECARTER" | "CRITICITE"; missionId: number; fermer: () => void; apres: () => void;
}) {
  const [motif, setMotif] = useState("");
  const [gravite, setGravite] = useState(d.gravite === "Bloquante" ? "Majeure" : "Bloquante");
  const action = useAction();
  return (
    <div className="rangee">
      <strong>{d.code}</strong>
      {mode === "CRITICITE" && (
        <select value={gravite} onChange={(e) => setGravite(e.target.value)} aria-label={"Nouvelle criticité de " + d.code}>
          {["Bloquante", "Majeure", "Mineure"].filter((g) => g !== d.gravite).map((g) => <option key={g}>{g}</option>)}
        </select>
      )}
      <input type="text" value={motif} onChange={(e) => setMotif(e.target.value)} style={{ flex: 1, minWidth: 220 }}
             aria-label={"Motif pour " + d.code}
             placeholder={mode === "ECARTER" ? "Pourquoi est-ce un faux positif ?" : "Pourquoi changer la criticité ? (impact)"} />
      <button className={"bouton petit" + (mode === "ECARTER" ? " rejeter" : "")} disabled={!motif.trim() || action.enCours}
              onClick={() => action.lancer(async () => {
                if (mode === "ECARTER") {
                  await api(`/missions/${missionId}/defauts-validation`,
                    { methode: "PUT", corps: { ids: [d.id], action: "ECARTER", motif } });
                } else {
                  await api(`/missions/${missionId}/defauts/${d.id}/criticite`,
                    { methode: "PUT", corps: { gravite, motif } });
                }
                apres();
              })}>{mode === "ECARTER" ? "Écarter" : "Changer la criticité"}</button>
      <button className="bouton discret petit" onClick={fermer}>Annuler</button>
      <MessageErreur erreur={action.erreur} />
    </div>
  );
}
