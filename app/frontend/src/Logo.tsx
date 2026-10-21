/** Logo QA-T-AG : carré bleu (bleu profond + bleu secondaire), losange blanc de la
 *  Human Gate, coche de la validation humaine, étoile cyan discrète de l'IA. Même dessin que public/logo-qatag.svg ;
 *  en dessous de 28 px, la version simplifiée (public/logo-qatag-petit.svg, favicon). */
export function Logo({ taille = 36 }: { taille?: number }) {
  if (taille < 28) return <LogoPetit taille={taille} />;
  return (
    <svg width={taille} height={taille} viewBox="0 0 32 32" role="img" aria-label="QA-T-AG">
      <rect x="0" y="0" width="32" height="32" rx="8" fill="#1f5fa6" />
      <path d="M0 21 L32 11 V24 a8 8 0 0 1 -8 8 H8 a8 8 0 0 1 -8 -8 Z" fill="#174a83" />
      <path d="M16 5.5 26.5 16 16 26.5 5.5 16Z" fill="rgba(255,255,255,0.14)" stroke="#ffffff"
            strokeWidth="2" strokeLinejoin="round" />
      <path d="m11.4 16.3 3.2 3.2 6.2-6.6" fill="none" stroke="#ffffff" strokeWidth="2.4"
            strokeLinecap="round" strokeLinejoin="round" />
      <path d="M25.6 4.3 26.05 5.75 27.5 6.2 26.05 6.65 25.6 8.1 25.15 6.65 23.7 6.2 25.15 5.75Z" fill="#7fdcf2" opacity="0.9" />
    </svg>
  );
}

/** Logo et nom, pour la barre latérale et la page de connexion. */
export function Marque({ sousTitre = true }: { sousTitre?: boolean }) {
  return (
    <>
      <Logo />
      <span>
        <span className="marque-nom">QA<span className="marque-tiret">-</span>T<span className="marque-tiret">-</span>AG</span>
        {sousTitre && <span className="marque-sous">L'IA au service de la qualité logicielle</span>}
      </span>
    </>
  );
}

/** Version petites tailles (moins de 28 px, favicon) : aplat bleu, losange et coche
 *  épaissis, sans étoile ni deux tons qui deviendraient illisibles. */
export function LogoPetit({ taille = 16 }: { taille?: number }) {
  return (
    <svg width={taille} height={taille} viewBox="0 0 32 32" role="img" aria-label="QA-T-AG">
      <rect width="32" height="32" rx="7" fill="#1f5fa6" />
      <path d="M16 4.2 27.8 16 16 27.8 4.2 16Z" fill="none" stroke="#ffffff" strokeWidth="3" strokeLinejoin="round" />
      <path d="m11 16.4 3.6 3.6 6.6-7.2" fill="none" stroke="#ffffff" strokeWidth="3.4"
            strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
