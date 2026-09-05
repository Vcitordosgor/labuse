// RETOURS-12 T2 — SIREN / SIRET cliquable vers Pappers, PARTOUT, par un composant unique.
// Règle : un SIREN = 9 chiffres, un SIRET = 14 chiffres. On lie toujours sur les 9 premiers
// (la fiche entreprise Pappers). Un SIRET reste affiché en entier mais pointe l'entreprise.
// Si la valeur n'a pas 9/14 chiffres valides, PAS de lien (jamais un lien mort) — texte brut.
// Survol conforme à la doctrine (souligné, teinte lien) ; nouvelle fenêtre, rel="noopener".

type Props = {
  value: string | null | undefined
  /** rendu quand la valeur est vide/absente (défaut « — ») */
  fallback?: React.ReactNode
  /** classes du conteneur (défaut : mono discret) */
  className?: string
  /** préfixer par « SIREN » / « SIRET » (défaut false : la surface le fait déjà souvent) */
  label?: boolean
}

/** Ne garde que les chiffres, puis valide la longueur (9 ou 14). */
function chiffres(v: string): string {
  return v.replace(/\D/g, '')
}

export function Siren({ value, fallback = '—', className = 'font-mono text-[10px] text-txt-off', label = false }: Props) {
  const brut = (value ?? '').trim()
  if (!brut) return <span className={className}>{fallback}</span>
  const digits = chiffres(brut)
  const estSiren = digits.length === 9
  const estSiret = digits.length === 14
  const affiche = (label ? (estSiret ? 'SIRET ' : 'SIREN ') : '') + brut
  if (!estSiren && !estSiret) {
    // valeur non conforme : on l'affiche telle quelle, sans lien (jamais de lien mort)
    return <span className={className}>{affiche}</span>
  }
  const siren9 = digits.slice(0, 9)
  const href = `https://www.pappers.fr/entreprise/${siren9}`
  return (
    <a href={href} target="_blank" rel="noopener noreferrer"
      title={`Voir ${estSiret ? "l'établissement" : "l'entreprise"} sur Pappers (${siren9})`}
      className={`${className} text-lien hover:underline`}>
      {affiche}
    </a>
  )
}
