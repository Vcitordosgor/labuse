// CIRCUIT-P (lot 4.1) — le deep-link de la page de détail dans l'URL, pour qu'un lien du journal ou
// d'un mail ouvre directement la bonne page. Namespacé `cx=<type>:<id>` et fusionné dans le hash
// existant (l'app cliente sérialise déjà des filtres dans le hash — on ne l'écrase pas). La
// navigation dans l'app (journal → détail, chips) passe par des callbacks, jamais par le hash :
// le hash n'est que pour l'ouverture depuis l'extérieur.
export type Detail = { type: 'reservoir' | 'robinet' | 'pompe'; id: number | string }

export function parseCx(hash: string): Detail | null {
  const p = new URLSearchParams((hash || '').replace(/^#/, ''))
  const v = p.get('cx')
  if (!v) return null
  if (v === 'pompe') return { type: 'pompe', id: 'pompe' }
  const [type, ...rest] = v.split(':')
  const id = rest.join(':')
  if (type === 'reservoir' && id) return { type, id: Number(id) }
  if (type === 'robinet' && id) return { type, id }
  return null
}

export function ecrireCx(hash: string, detail: Detail | null): string {
  const p = new URLSearchParams((hash || '').replace(/^#/, ''))
  if (!detail) p.delete('cx')
  else p.set('cx', detail.type === 'pompe' ? 'pompe' : `${detail.type}:${detail.id}`)
  const s = p.toString()
  return s ? '#' + s : ''
}
