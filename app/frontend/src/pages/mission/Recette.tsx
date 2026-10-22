import { useEffect, useRef, useState, type ClipboardEvent, type FormEvent } from "react";
import { api, imageProtegee, telecharger, type Mission } from "../../api";
import { MessageErreur, Pastille, useAction, useDonnees, Volet } from "../../composants";
import {
  date, GRAVITES_ANOMALIE, REPRODUCTIBILITES, STATUT_ANOMALIE, STATUT_EXECUTION,
} from "../../libelles";

// --- Données renvoyées par GET /missions/{id}/recette ------------------------------

interface Personne { id: number; nom: string; email: string }
interface PreuveR { id: number; nom: string; type: string; taille: number; empreinte: string }
interface ExecutionR {
  id: number; passage: number; statut: string; libelle: string; resultat_obtenu: string;
  commentaire: string; testeur: Personne | null; execute_le: string; preuves: PreuveR[];
}
interface CasR {
  id: number; code: string; titre: string; objectif: string; exigence: string; references: string[];
  priorite: string; type: string; preconditions: string; donnees_test: string; etapes: string;
  resultat_attendu: string; statut_cas: string; statut: string | null;
  executable: boolean; en_reserve: boolean;
  anomalies_ouvertes: string[]; executions: ExecutionR[];
}
interface AnomalieR {
  modifiable: boolean;
  id: number; code: string; cas_id: number; cas: string; titre: string; description: string;
  gravite: string | null; reproductibilite: string | null; statut: string; motif_statut: string | null;
  agent: { etat: string | null; gravite: string | null; reproductibilite: string | null;
    titre: string | null; justification: string | null; erreur: string | null };
  qualifie_par: Personne | null; qualifie_le: string | null; motif_requalification: string | null;
  cree_le: string;
}
interface EtatRecette {
  statut_mission: string; ouverte: boolean; ia_configuree: boolean;
  suivi_reserves: boolean; reserves_restantes: string[];
  compteurs: Record<string, number>; cas: CasR[]; anomalies: AnomalieR[]; reserves: string[];
  cloture: { decision: string; commentaire: string; reserves: string[]; decideur: Personne;
    auto_validation: boolean; decide_le: string;
    levee: { le: string; par: Personne; auto_validation: boolean; commentaire: string | null } | null } | null;
}

const nom = (p: Personne | null) => (p ? p.nom || p.email : "—");

export default function Recette({ mission: m, recharger }: { mission: Mission; recharger: () => void }) {
  const { donnees: r, erreur, recharger: relire } = useDonnees<EtatRecette>(`/missions/${m.id}/recette`);
  const [onglet, setOnglet] = useState<"cas" | "anomalies">("cas");
  const [ouvert, setOuvert] = useState<number | null>(null);
  const exporter = useAction();
  const toutRelire = () => { relire(); recharger(); };

  // AG-09 travaille en tâche de fond : on relit tant qu'une qualification est en cours
  const agentAuTravail = !!r?.anomalies.some((a) => a.agent.etat === "EN_COURS");
  useEffect(() => {
    if (!agentAuTravail) return;
    const t = setInterval(relire, 3000);
    return () => clearInterval(t);
  }, [agentAuTravail, relire]);

  if (erreur) return <div className="panneau-corps"><MessageErreur erreur={erreur} /></div>;
  if (!r) return <div className="charge">Chargement de la recette…</div>;
  const c = r.compteurs;
  const casOuvert = r.cas.find((x) => x.id === ouvert) ?? null;
  const segments: [string, number, string][] = [
    ["Succès", c.PASS, "var(--succes)"], ["Échec", c.FAIL, "var(--alerte)"],
    ["Non testable", c.BLOCKED, "var(--attente)"], ["Non exécuté", c.NOT_RUN, "var(--encre-pale)"],
  ];
  return (
    <>
      <div className="panneau-corps pile" style={{ gap: 12 }}>
        <div className="rangee" style={{ gap: 18 }}>
          {segments.map(([libelle, n, couleur]) => (
            <span key={libelle}><strong style={{ color: couleur }}>{n}</strong> {libelle.toLowerCase()}</span>
          ))}
          <span><strong>{c.A_EXECUTER}</strong> à exécuter</span>
          <span><strong style={{ color: c.anomalies_ouvertes ? "var(--alerte)" : undefined }}>{c.anomalies_ouvertes}</strong> anomalie{c.anomalies_ouvertes > 1 ? "s" : ""} ouverte{c.anomalies_ouvertes > 1 ? "s" : ""}</span>
          <button className="bouton" style={{ marginLeft: "auto" }}
                  disabled={exporter.enCours || r.statut_mission === "VALIDEE"}
                  title={r.statut_mission === "VALIDEE" ? "Disponible dès la première exécution"
                    : r.cloture ? "Cahier de recette au gabarit Word DSI" : "Document de travail : recette non clôturée"}
                  onClick={() => exporter.lancer(() => telecharger(`/missions/${m.id}/cahier-recette`))}>
            {exporter.enCours ? "Export…" : r.cloture ? "Cahier de recette (Word)" : "Cahier de recette (brouillon)"}
          </button>
        </div>
        <div className="barre-progres" aria-hidden="true" style={{ height: 9 }}>
          {segments.map(([libelle, n, couleur]) => (
            <div key={libelle} style={{ width: `${(100 * n) / Math.max(c.total, 1)}%`, background: couleur }} />
          ))}
        </div>
        <MessageErreur erreur={exporter.erreur} />
        {r.statut_mission === "VALIDEE" && (
          <div className="message-info">
            Les cas sont validés à PV-2. Ouvrez un cas pour enregistrer son premier passage : la recette démarre
            avec la première exécution.
          </div>
        )}
        <div className="puces" role="tablist" aria-label="Vue de la recette">
          <button type="button" role="tab" className="puce" aria-pressed={onglet === "cas"} aria-selected={onglet === "cas"}
                  onClick={() => setOnglet("cas")}>Cas · {c.total}</button>
          <button type="button" role="tab" className="puce" aria-pressed={onglet === "anomalies"} aria-selected={onglet === "anomalies"}
                  onClick={() => setOnglet("anomalies")}>Anomalies · {r.anomalies.length}</button>
        </div>
      </div>

      {onglet === "cas" ? (
        <div className="table-defile">
          <table>
            <thead><tr><th>Cas</th><th>Priorité</th><th style={{ width: 130 }}>Dernier passage</th>
              <th style={{ width: 80 }}>Passages</th><th>Anomalie</th></tr></thead>
            <tbody>
              {r.cas.map((x) => {
                const dernier = x.executions[x.executions.length - 1];
                return (
                  <tr key={x.id} className="cliquable" onClick={() => setOuvert(x.id)}>
                    <td><span className="ref">{x.code}</span> {x.titre}
                      {r.suivi_reserves && x.en_reserve && <> <Pastille ton="attente">En réserve</Pastille></>}
                      <div className="sous">{x.references.join(" · ")}</div></td>
                    <td>{x.priorite}</td>
                    <td>{dernier
                      ? <Pastille ton={STATUT_EXECUTION[dernier.statut].ton}>{STATUT_EXECUTION[dernier.statut].libelle}</Pastille>
                      : <span className="discret-texte">À exécuter</span>}</td>
                    <td>{x.executions.length || "—"}</td>
                    <td>{x.anomalies_ouvertes.map((a) => <span key={a} className="ref" style={{ marginRight: 6 }}>{a}</span>)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <Anomalies mission={m} recette={r} apres={toutRelire} />
      )}

      <Cloture mission={m} recette={r} apres={toutRelire} />

      {casOuvert && (
        <VoletExecution mission={m} cas={casOuvert} ouverte={casOuvert.executable} suivi={r.suivi_reserves} fermer={() => setOuvert(null)}
                        apres={toutRelire} />
      )}
    </>
  );
}

// --- Exécution d'un cas ------------------------------------------------------------------

function VoletExecution({ mission: m, cas, ouverte, suivi, fermer, apres }: {
  mission: Mission; cas: CasR; ouverte: boolean; suivi: boolean; fermer: () => void; apres: () => void;
}) {
  const [statut, setStatut] = useState("");
  const [obtenu, setObtenu] = useState("");
  const [commentaire, setCommentaire] = useState("");
  const [captures, setCaptures] = useState<File[]>([]);
  const action = useAction();

  const ajouter = (fichiers: FileList | File[] | null) => {
    const images = Array.from(fichiers ?? []).filter((f) => /^image\/(png|jpeg)$/.test(f.type));
    setCaptures((avant) => [...avant, ...images].slice(0, 5));
  };
  const coller = (ev: ClipboardEvent) => {
    const images = Array.from(ev.clipboardData.files).filter((f) => f.type.startsWith("image/"));
    if (images.length) { ev.preventDefault(); ajouter(images); }
  };
  const exigences: Record<string, string> = {
    PASS: "Résultat obtenu et au moins une capture obligatoires.",
    FAIL: "Résultat obtenu et au moins une capture obligatoires.",
    BLOCKED: "Commentaire obligatoire : pourquoi le cas n'a pas pu être testé.",
    NOT_RUN: "Commentaire obligatoire : pourquoi le cas n'est pas exécuté.",
  };
  const envoyer = (ev: FormEvent) => {
    ev.preventDefault();
    action.lancer(async () => {
      const f = new FormData();
      f.append("statut", statut);
      f.append("resultat_obtenu", obtenu);
      f.append("commentaire", commentaire);
      captures.forEach((c) => f.append("captures", c, c.name || "capture.png"));
      await api(`/missions/${m.id}/cas/${cas.id}/executions`, { methode: "POST", formulaire: f });
      setStatut(""); setObtenu(""); setCommentaire(""); setCaptures([]);
      apres();
    });
  };
  const bloc = (titre: string, texte: string) => (
    <div className="champ"><span className="etiquette">{titre}</span>
      <div style={{ whiteSpace: "pre-wrap" }}>{texte || <span className="discret-texte">—</span>}</div></div>
  );
  return (
    <Volet titre={<><span className="ref">{cas.code}</span> {cas.titre}</>}
           sousTitre={`${cas.priorite} · ${cas.references.join(" · ")}`} fermer={fermer}>
      {bloc("Objectif", cas.objectif)}
      {bloc("Préconditions", cas.preconditions)}
      {bloc("Données de test", cas.donnees_test)}
      {bloc("Étapes", cas.etapes)}
      <div className="message-info">{bloc("Résultat attendu", cas.resultat_attendu)}</div>

      {ouverte ? (
        <form className="pile execution-form" onSubmit={envoyer} onPaste={coller}>
          <h3 style={{ margin: "8px 0 0" }}>Passage {cas.executions.length + 1}</h3>
          <div className="choix-statut" role="radiogroup" aria-label="Statut d'exécution">
            {Object.entries(STATUT_EXECUTION).map(([code, s]) => (
              <button key={code} type="button" role="radio" aria-checked={statut === code}
                      className={"ton-" + s.ton} onClick={() => setStatut(code)}>{s.libelle}</button>
            ))}
          </div>
          {statut && <div className="discret-texte">{exigences[statut]}</div>}
          <div className="champ">
            <label htmlFor="obtenu">Résultat obtenu</label>
            <textarea id="obtenu" rows={3} value={obtenu} onChange={(e) => setObtenu(e.target.value)}
                      placeholder="Ce que vous avez constaté à l'écran, factuellement" />
          </div>
          <div className="champ">
            <label htmlFor="commentaire">Commentaire</label>
            <textarea id="commentaire" rows={2} value={commentaire} onChange={(e) => setCommentaire(e.target.value)} />
          </div>
          <div className="champ">
            <label htmlFor="captures">Captures d'écran (PNG ou JPEG, 5 au plus{statut === "PASS" || statut === "FAIL" ? ", au moins une obligatoire" : ""})</label>
            <input id="captures" type="file" accept="image/png,image/jpeg" multiple
                   onChange={(e) => { ajouter(e.target.files); e.target.value = ""; }} />
            <span className="aide">Astuce : collez une capture directement (Ctrl+V) dans ce formulaire.</span>
            {captures.length > 0 && (
              <div className="vignettes">
                {captures.map((f, i) => (
                  <figure key={i}>
                    <VignetteLocale fichier={f} libelle={`Capture ${i + 1} à envoyer`} />
                    <button type="button" className="lien" onClick={() => setCaptures(captures.filter((_, j) => j !== i))}>Retirer</button>
                  </figure>
                ))}
              </div>
            )}
          </div>
          <MessageErreur erreur={action.erreur} />
          <div><button className="bouton principal"
                       disabled={action.enCours || !statut || ((statut === "PASS" || statut === "FAIL") && captures.length === 0)}
                       title={(statut === "PASS" || statut === "FAIL") && captures.length === 0 ? "Joignez au moins une capture d'écran" : undefined}>
            {action.enCours ? "Enregistrement…" : `Enregistrer le passage ${cas.executions.length + 1}`}
          </button></div>
        </form>
      ) : (
        <p className="discret-texte">{suivi
          ? "Recette clôturée : seuls les cas en réserve peuvent encore être rejoués. Ce cas n'en fait pas partie."
          : "La recette n'est pas ouverte à l'exécution (clôturée ou avant PV-2)."}</p>
      )}

      {cas.executions.length > 0 && (
        <div className="pile">
          <h3 style={{ margin: "12px 0 0" }}>Historique des passages</h3>
          {[...cas.executions].reverse().map((e) => (
            <div key={e.id} className="passage">
              <div className="rangee" style={{ justifyContent: "space-between" }}>
                <strong>Passage {e.passage}</strong>
                <Pastille ton={STATUT_EXECUTION[e.statut].ton}>{e.libelle}</Pastille>
              </div>
              <div className="discret-texte">{nom(e.testeur)} · {date(e.execute_le)}</div>
              {e.resultat_obtenu && <div style={{ whiteSpace: "pre-wrap" }}>{e.resultat_obtenu}</div>}
              {e.commentaire && <div className="discret-texte" style={{ whiteSpace: "pre-wrap" }}>« {e.commentaire} »</div>}
              {e.preuves.length > 0 && (
                <div className="vignettes">
                  {e.preuves.map((p) => <Capture key={p.id} missionId={m.id} preuve={p} />)}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </Volet>
  );
}

/** Aperçu d'une capture avant envoi, dessiné dans un canevas : l'image est décodée
 *  par le navigateur, aucune adresse ni aucun nom de fichier n'entre dans la page. */
function VignetteLocale({ fichier, libelle }: { fichier: File; libelle: string }) {
  const toile = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    let actif = true;
    createImageBitmap(fichier).then((image) => {
      const c = toile.current;
      if (!actif || !c) { image.close(); return; }
      const echelle = Math.max(c.width / image.width, c.height / image.height);
      const l = image.width * echelle, h = image.height * echelle;
      c.getContext("2d")?.drawImage(image, (c.width - l) / 2, (c.height - h) / 2, l, h);
      image.close();
    }).catch(() => {});
    return () => { actif = false; };
  }, [fichier]);
  return <canvas ref={toile} width={240} height={160} role="img" aria-label={libelle} className="vignette-toile" />;
}

/** Capture enregistrée : chargée avec le jeton de session, ouverte en grand au clic. */
function Capture({ missionId, preuve }: { missionId: number; preuve: PreuveR }) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    let actif = true;
    let locale: string | null = null;
    imageProtegee(`/missions/${missionId}/preuves/${preuve.id}`)
      .then((u) => { locale = u; if (actif) setUrl(u); else URL.revokeObjectURL(u); })
      .catch(() => {});
    return () => { actif = false; if (locale) URL.revokeObjectURL(locale); };
  }, [missionId, preuve.id]);
  return (
    <figure title={`${preuve.nom} · SHA-256 ${preuve.empreinte}`}>
      {url ? <a href={url} target="_blank" rel="noreferrer"><img src={url} alt={preuve.nom} /></a>
        : <div className="vignette-vide">…</div>}
      <figcaption>{preuve.nom}</figcaption>
    </figure>
  );
}

// --- Anomalies -------------------------------------------------------------------------------

function Anomalies({ mission: m, recette: r, apres }: { mission: Mission; recette: EtatRecette; apres: () => void }) {
  if (!r.anomalies.length) {
    return <div className="vide"><strong>Aucune anomalie</strong>Chaque cas en échec ouvre une anomalie, qualifiée par AG-09 puis par vous.</div>;
  }
  return (
    <div className="panneau-corps pile">
      {r.anomalies.map((a) => <CarteAnomalie key={a.id} mission={m} a={a} ouverte={a.modifiable} iaConfiguree={r.ia_configuree} apres={apres} />)}
    </div>
  );
}

function CarteAnomalie({ mission: m, a, ouverte, iaConfiguree, apres }: {
  mission: Mission; a: AnomalieR; ouverte: boolean; iaConfiguree: boolean; apres: () => void;
}) {
  const [gravite, setGravite] = useState(a.gravite ?? a.agent.gravite ?? "");
  const [repro, setRepro] = useState(a.reproductibilite ?? a.agent.reproductibilite ?? "Non déterminée");
  const [titre, setTitre] = useState(a.qualifie_par ? a.titre : a.agent.titre ?? "");
  const [motif, setMotif] = useState("");
  const [motifStatut, setMotifStatut] = useState("");
  const action = useAction();
  const resolue = a.statut === "FERMEE" || a.statut === "REJETEE";
  const ecart = !!a.agent.gravite && gravite !== a.agent.gravite;
  useEffect(() => {          // la proposition d'AG-09 arrive après l'ouverture de la carte
    if (!a.gravite && a.agent.gravite) {
      setGravite(a.agent.gravite);
      setRepro(a.agent.reproductibilite ?? "Non déterminée");
      if (a.agent.titre) setTitre(a.agent.titre);
    }
  }, [a.agent.gravite, a.agent.reproductibilite, a.agent.titre, a.gravite]);

  const qualifier = () => action.lancer(async () => {
    await api(`/missions/${m.id}/anomalies/${a.id}/qualification`,
      { methode: "PUT", corps: { gravite, reproductibilite: repro, titre, motif } });
    setMotif("");
    apres();
  });
  const changer = (act: string) => action.lancer(async () => {
    await api(`/missions/${m.id}/anomalies/${a.id}/statut`, { methode: "POST", corps: { action: act, motif: motifStatut } });
    setMotifStatut("");
    apres();
  });
  const relancerAgent = () => action.lancer(async () => {
    await api(`/missions/${m.id}/anomalies/${a.id}/agent`, { methode: "POST" });
    apres();
  });

  return (
    <article className="carte-anomalie">
      <header className="rangee" style={{ justifyContent: "space-between" }}>
        <div>
          <span className="ref">{a.code}</span> <strong>{a.titre}</strong>
          <div className="discret-texte">Cas {a.cas} · ouverte le {date(a.cree_le)}</div>
        </div>
        <div className="rangee" style={{ gap: 6 }}>
          {a.gravite ? <Pastille ton={a.gravite === "Mineure" ? "neutre" : a.gravite === "Majeure" ? "attente" : "alerte"}>{a.gravite}</Pastille>
            : <Pastille ton="attente">À qualifier</Pastille>}
          <Pastille ton={STATUT_ANOMALIE[a.statut].ton}>{STATUT_ANOMALIE[a.statut].libelle}</Pastille>
        </div>
      </header>
      <div style={{ whiteSpace: "pre-wrap", fontSize: "0.92rem" }}>{a.description}</div>
      {a.motif_statut && <div className="discret-texte">{a.motif_statut}</div>}

      {/* Proposition d'AG-09 */}
      {a.agent.etat === "EN_COURS" && <div className="message-info" role="status">AG-09 qualifie l'anomalie…</div>}
      {a.agent.etat === "PROPOSEE" && (
        <div className="proposition-agent">
          <div className="etiquette">Proposition d'AG-09</div>
          <div><strong>{a.agent.gravite}</strong> · {a.agent.reproductibilite}</div>
          <div className="discret-texte">« {a.agent.titre} »</div>
          <div style={{ fontSize: "0.9rem" }}>{a.agent.justification}</div>
        </div>
      )}
      {a.agent.etat === "ECHEC" && (
        <div className="message-erreur">AG-09 n'a pas pu qualifier l'anomalie : {a.agent.erreur}. Qualifiez-la vous-même
          {ouverte && iaConfiguree && !resolue && <> ou <button className="lien" onClick={relancerAgent} disabled={action.enCours}>relancez AG-09</button></>}.</div>
      )}

      {a.qualifie_par && (
        <div className="discret-texte">Qualifiée par {nom(a.qualifie_par)} le {date(a.qualifie_le)}
          {a.motif_requalification && <> · motif : « {a.motif_requalification} »</>}</div>
      )}

      {ouverte && !resolue && (
        <div className="pile" style={{ gap: 8 }}>
          <div className="rangee" style={{ alignItems: "flex-end" }}>
            <div className="champ" style={{ flex: 1, minWidth: 130 }}>
              <label htmlFor={"g-" + a.id}>Gravité retenue</label>
              <select id={"g-" + a.id} value={gravite} onChange={(e) => setGravite(e.target.value)}>
                <option value="" disabled>Choisir…</option>
                {GRAVITES_ANOMALIE.map((g) => <option key={g}>{g}</option>)}
              </select>
            </div>
            <div className="champ" style={{ flex: 1, minWidth: 150 }}>
              <label htmlFor={"r-" + a.id}>Reproductibilité</label>
              <select id={"r-" + a.id} value={repro} onChange={(e) => setRepro(e.target.value)}>
                {REPRODUCTIBILITES.map((g) => <option key={g}>{g}</option>)}
              </select>
            </div>
          </div>
          <div className="champ">
            <label htmlFor={"t-" + a.id}>Titre</label>
            <input id={"t-" + a.id} type="text" value={titre} placeholder={a.titre} onChange={(e) => setTitre(e.target.value)} />
          </div>
          {ecart && (
            <div className="champ">
              <label htmlFor={"m-" + a.id}>Motif (AG-09 proposait « {a.agent.gravite} »)</label>
              <input id={"m-" + a.id} type="text" value={motif} onChange={(e) => setMotif(e.target.value)} />
            </div>
          )}
          <div className="rangee">
            <button className="bouton principal petit" disabled={action.enCours || !gravite || (ecart && !motif.trim())}
                    onClick={qualifier}>{a.gravite ? "Mettre à jour la qualification" : ecart ? "Retenir ma qualification" : a.agent.gravite ? "Confirmer la proposition" : "Qualifier"}</button>
          </div>
          <div className="rangee actions-anomalie">
            <input type="text" value={motifStatut} onChange={(e) => setMotifStatut(e.target.value)}
                   placeholder={a.statut === "OUVERTE" ? "Référence de livraison ou motif du rejet" : "Motif du rejet"}
                   aria-label="Motif ou référence" style={{ flex: 1, minWidth: 180 }} />
            {a.statut === "OUVERTE" && (
              <button className="bouton petit" disabled={action.enCours} onClick={() => changer("CORRIGER")}
                      title="La correction est livrée : rejouez le cas pour fermer l'anomalie">Déclarer corrigée</button>
            )}
            <button className="bouton discret petit" disabled={action.enCours || !motifStatut.trim()} onClick={() => changer("REJETER")}
                    title="Ce n'est pas une anomalie (erreur de test, comportement attendu) : motif obligatoire">Rejeter</button>
          </div>
          {a.statut === "CORRIGEE" && <div className="discret-texte">Rejouez le cas {a.cas} : un passage réussi ferme l'anomalie, un échec la rouvre.</div>}
        </div>
      )}
      {ouverte && a.statut === "REJETEE" && (
        <div className="rangee">
          <input type="text" value={motifStatut} onChange={(e) => setMotifStatut(e.target.value)}
                 placeholder="Motif de la réouverture" aria-label="Motif de la réouverture" style={{ flex: 1 }} />
          <button className="bouton petit" disabled={action.enCours || !motifStatut.trim()} onClick={() => changer("ROUVRIR")}>Rouvrir</button>
        </div>
      )}
      <MessageErreur erreur={action.erreur} />
    </article>
  );
}

// --- Clôture -------------------------------------------------------------------------------------

function Cloture({ mission: m, recette: r, apres }: { mission: Mission; recette: EtatRecette; apres: () => void }) {
  const [commentaire, setCommentaire] = useState("");
  const action = useAction();
  if (r.cloture) {
    const d = r.cloture;
    const lever = () => action.lancer(async () => {
      await api(`/missions/${m.id}/recette/levee-reserves`, { methode: "POST", corps: { commentaire } });
      setCommentaire("");
      apres();
    });
    return (
      <div className="panneau-corps pile">
        <div className={d.decision === "CLOTURE" || d.levee ? "message-info" : "message-erreur"} style={{ color: "var(--encre)" }}>
          <strong>Recette clôturée {d.decision === "CLOTURE" ? "sans réserve" : "avec réserves"}</strong> le {date(d.decide_le)} par {nom(d.decideur)}
          {d.auto_validation && " (acteur unique de la mission)"}.
          {d.commentaire && <div>« {d.commentaire} »</div>}
          {d.reserves.length > 0 && <>
            <div style={{ marginTop: 6 }}>Réserves enregistrées à la clôture :</div>
            <ul style={{ margin: "2px 0 0" }}>{d.reserves.map((x) => <li key={x}>{x}</li>)}</ul>
          </>}
          {d.levee && (
            <div style={{ marginTop: 8 }}><strong>Réserves levées</strong> le {date(d.levee.le)} par {nom(d.levee.par)}
              {d.levee.auto_validation && " (acteur unique de la mission)"}.
              {d.levee.commentaire && <> « {d.levee.commentaire} »</>}</div>
          )}
        </div>
        {r.suivi_reserves && (
          <section className="pile cloture" aria-labelledby="titre-levee" style={{ paddingTop: 12 }}>
            <h3 id="titre-levee" style={{ margin: 0 }}>Lever les réserves</h3>
            <p className="discret-texte">
              Seuls les cas en réserve peuvent encore être rejoués, et leurs anomalies déclarées corrigées, rejetées
              ou rouvertes. La décision de clôture ci-dessus ne change pas.
            </p>
            {r.reserves_restantes.length > 0
              ? <>
                  <div className="discret-texte">{r.reserves_restantes.length} point{r.reserves_restantes.length > 1 ? "s restent" : " reste"} à lever :</div>
                  <ul className="reserves">{r.reserves_restantes.map((x) => <li key={x}>{x}</li>)}</ul>
                </>
              : <div className="message-info">Tous les cas en réserve sont réussis et leurs anomalies résolues : les réserves peuvent être levées.</div>}
            <div className="champ">
              <label htmlFor="commentaire-levee">Commentaire (facultatif)</label>
              <input id="commentaire-levee" type="text" value={commentaire} onChange={(e) => setCommentaire(e.target.value)}
                     placeholder="Ex. : corrections vérifiées en version 1.2.1" />
            </div>
            <MessageErreur erreur={action.erreur} />
            <div><button className="bouton principal" disabled={action.enCours || r.reserves_restantes.length > 0}
                         onClick={lever}>Lever les réserves</button></div>
          </section>
        )}
      </div>
    );
  }
  if (r.statut_mission !== "EN_RECETTE") return null;
  const cloturer = (decision: string) => action.lancer(async () => {
    await api(`/missions/${m.id}/recette/cloture`, { methode: "POST", corps: { decision, commentaire } });
    apres();
  });
  return (
    <section className="panneau-corps pile cloture" aria-labelledby="titre-cloture">
      <h3 id="titre-cloture" style={{ margin: 0 }}>Clôturer la recette</h3>
      {r.reserves.length === 0
        ? <p className="discret-texte">Tous les cas sont réussis et aucune anomalie n'est ouverte : la recette peut être clôturée sans réserve.</p>
        : <>
            <p className="discret-texte">{r.reserves.length} point{r.reserves.length > 1 ? "s restent" : " reste"} ouvert{r.reserves.length > 1 ? "s" : ""}. Une clôture est possible avec réserves, motif à l'appui ; elles seront figées dans la décision et le cahier.</p>
            <ul className="reserves">{r.reserves.map((x) => <li key={x}>{x}</li>)}</ul>
            <div className="champ">
              <label htmlFor="motif-cloture">Motif de la clôture avec réserves</label>
              <textarea id="motif-cloture" rows={2} value={commentaire} onChange={(e) => setCommentaire(e.target.value)}
                        placeholder="Ex. : mise en production acceptée par le métier, ANO-001 corrigée en 1.2.1" />
            </div>
          </>}
      <MessageErreur erreur={action.erreur} />
      <div className="rangee">
        {r.reserves.length === 0
          ? <button className="bouton principal" disabled={action.enCours} onClick={() => cloturer("CLOTURE")}>Clôturer sans réserve</button>
          : <button className="bouton principal" disabled={action.enCours || !commentaire.trim()} onClick={() => cloturer("CLOTURE_AVEC_RESERVES")}>Clôturer avec réserves</button>}
      </div>
    </section>
  );
}
