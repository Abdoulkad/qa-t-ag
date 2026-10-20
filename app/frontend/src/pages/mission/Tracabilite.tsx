import type { Tracabilite as T } from "../../api";
import { MessageErreur, useDonnees } from "../../composants";

export default function Tracabilite({ missionId }: { missionId: number }) {
  const { donnees: t, erreur } = useDonnees<T>(`/missions/${missionId}/tracabilite`);
  if (erreur) return <div className="panneau-corps"><MessageErreur erreur={erreur} /></div>;
  if (!t) return <div className="charge">Chargement…</div>;
  if (!t.matrice.length) {
    return <div className="vide">La matrice apparaîtra une fois les critères d'acceptation établis.</div>;
  }
  const techniques = Object.entries(t.par_technique);
  return (
    <>
      <div className="panneau-corps rangee" style={{ gap: 24 }}>
        <span>Couverture : <strong>{t.couverture === null ? "—" : t.couverture + " %"}</strong>
          <span className="discret-texte"> des exigences et critères ont au moins un cas</span></span>
        {techniques.length > 0 && (
          <span className="discret-texte">
            {techniques.map(([k, v]) => `${v} en ${k}`).join(", ")}
          </span>
        )}
      </div>
      <div className="table-defile">
        <table>
          <thead><tr><th style={{ width: 110 }}>Référence</th><th>Énoncé</th><th>Cas qui la couvrent</th></tr></thead>
          <tbody>
            {t.matrice.map((l) => (
              <tr key={l.reference}>
                <td><span className="ref">{l.reference}</span></td>
                <td>{l.libelle || <span className="discret-texte">Identifiant cité dans le texte d'origine</span>}</td>
                <td>{l.cas.length
                  ? l.cas.map((c) => <span key={c} className="ref" style={{ marginRight: 8 }}>{c}</span>)
                  : <span style={{ color: "var(--alerte)" }}>Aucun cas</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {t.regles.length > 0 && (
        <>
          <div className="panneau-corps" style={{ paddingBottom: 0 }}>
            <h3>Règles métier → critères → cas</h3>
            <p className="discret-texte">Chaque règle validée doit être vérifiée par au moins un critère, lui-même couvert par un cas.</p>
          </div>
          <div className="table-defile">
            <table>
              <thead><tr><th style={{ width: 90 }}>Règle</th><th>Énoncé</th><th style={{ width: 150 }}>Critères</th><th>Cas</th></tr></thead>
              <tbody>
                {t.regles.map((r) => (
                  <tr key={r.code}>
                    <td><span className="ref">{r.code}</span></td>
                    <td>{r.texte}</td>
                    <td>{r.criteres.length
                      ? r.criteres.map((c) => <span key={c} className="ref" style={{ marginRight: 6 }}>{c}</span>)
                      : <span style={{ color: "var(--alerte)" }}>Aucun critère</span>}</td>
                    <td>{r.cas.length
                      ? r.cas.map((c) => <span key={c} className="ref" style={{ marginRight: 6 }}>{c}</span>)
                      : <span style={{ color: "var(--alerte)" }}>Aucun cas</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      {t.cas_sans_reference.length > 0 && (
        <div className="panneau-corps message-erreur" style={{ margin: 12 }}>
          Cas sans exigence tracée : {t.cas_sans_reference.join(", ")}
        </div>
      )}
    </>
  );
}
