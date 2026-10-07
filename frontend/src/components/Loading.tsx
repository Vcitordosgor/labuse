import { useEffect, useState } from 'react'

// CHARGEMENT-1 — L'UNIQUE indicateur de chargement de l'app. Trois petits points menthe (le vert de
// marque) qui défilent en boucle. Deux variantes et RIEN d'autre :
//   • `inline`  — dans un bouton, une case, une ligne de texte (flux horizontal, hauteur de ligne).
//   • `bloc`    — centré dans un panneau vide le temps que la donnée arrive.
// Il ne s'affiche QUE si l'attente dépasse un court délai (300 ms par défaut) : les actions rapides
// ne clignotent pas. Il remplace tous les anciens indicateurs (spinners, « Chargement… » texte,
// squelettes gris) — un seul langage visuel. `Loading`/`Skeleton`/`Squelette` ne sont plus que des
// adaptateurs de compatibilité qui rendent CE composant (voir bas de fichier).

// Délai avant d'AFFICHER : le composant est monté quand l'attente commence et démonté quand elle
// finit. S'il est démonté avant `ms`, rien ne s'est jamais affiché (pas de clignotement). `ms=0`
// affiche tout de suite (cas rares où l'on veut un retour immédiat).
export function useDelai(ms = 300): boolean {
  const [pret, setPret] = useState(ms <= 0)
  useEffect(() => {
    if (ms <= 0) return
    const t = window.setTimeout(() => setPret(true), ms)
    return () => window.clearTimeout(t)
  }, [ms])
  return pret
}

export function Chargement({
  variant = 'bloc',
  label,
  className = '',
  accent = 'mint',
  delai = 300,
}: {
  variant?: 'inline' | 'bloc'
  label?: string
  className?: string
  // Les points sont TOUJOURS menthe (le vert de marque) — Outils et Copilote compris. Seul 'courant'
  // existe en plus : la couleur du texte courant, pour que les points restent visibles DANS un bouton
  // plein (ex. menthe foncé sur fond menthe).
  accent?: 'mint' | 'courant'
  delai?: number
}) {
  const pret = useDelai(delai)
  if (!pret) return null

  const tone = accent === 'courant' ? 'bg-current' : 'bg-mint'
  const dots = (
    <span className="inline-flex items-center gap-1" aria-hidden>
      {[0, 1, 2].map((i) => (
        <span key={i} className={`labuse-dot h-1.5 w-1.5 rounded-full ${tone}`}
          style={{ animationDelay: `${i * 160}ms` }} />
      ))}
    </span>
  )

  if (variant === 'inline') {
    return (
      <span className={`inline-flex items-center gap-2 align-middle text-txt-mut ${className}`}
        role="status" aria-live="polite" aria-busy="true">
        {dots}
        {label && <span className="text-xs">{label}</span>}
      </span>
    )
  }

  return (
    <div className={`flex min-h-[48px] w-full flex-col items-center justify-center gap-2 py-3 text-txt-mut ${className}`}
      role="status" aria-live="polite" aria-busy="true">
      {dots}
      {label && <span className="text-xs">{label}</span>}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Adaptateurs de compatibilité — tous les anciens points d'appel (≈ 90) continuent
// d'importer `Loading`/`Skeleton`/`Squelette`, mais rendent désormais le MÊME composant.
// Le nouveau code doit utiliser `Chargement`. `lignes`/`bloc`/`big` sont tolérés et ignorés
// (le dessin ne dépend plus du nombre de lignes : trois points, point final).

export function Loading({ label, className = '' }:
  { label?: string; className?: string; big?: boolean }) {
  return <Chargement variant="inline" label={label} className={className} />
}

export function Skeleton({ className = '' }: { className?: string }) {
  return <Chargement variant="bloc" className={className} />
}

export function Squelette({ bloc: _bloc, className = '', label }:
  { lignes?: number; bloc?: boolean; className?: string; label?: string }) {
  return <Chargement variant="bloc" label={label} className={className} />
}
