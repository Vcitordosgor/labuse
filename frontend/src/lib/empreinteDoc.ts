// CHASSE-DOCS-FIX-1 (Lot 5.1) — « Sources modifiées depuis » réagit AUSSI aux SAISIES.
//
// À la génération d'un Bilan (hypothèses) ou d'une Étude de faisabilité (scénario/config), on fige
// l'EMPREINTE de ces saisies. Quand l'éditeur change ensuite SANS régénérer, « Mes documents » compare
// l'empreinte de l'éditeur à celle figée et allume le badge EXISTANT « Sources modifiées depuis ».
//
// Tout côté client (localStorage) : aucun nouveau composant, aucune route, DA existante. Clé = (type, idu)
// → une seule génération suivie par parcelle et par type de document (la plus récente).

function _stable(obj: unknown): string {
  // JSON canonique (clés triées à chaque niveau) → insensible à l'ordre d'insertion des clés.
  const seen = new WeakSet<object>()
  const norm = (v: unknown): unknown => {
    if (v && typeof v === 'object') {
      if (seen.has(v as object)) return null
      seen.add(v as object)
      if (Array.isArray(v)) return v.map(norm)
      const o = v as Record<string, unknown>
      return Object.fromEntries(Object.keys(o).sort().map((k) => [k, norm(o[k])]))
    }
    return v
  }
  return JSON.stringify(norm(obj))
}

/** Empreinte courte et stable (djb2) d'un objet d'hypothèses/scénario. */
export function empreinte(obj: unknown): string {
  const s = _stable(obj)
  let h = 5381
  for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) | 0
  return (h >>> 0).toString(36)
}

const _kEd = (t: string, idu: string) => `labuse:doc-ed:${t}:${idu}`
const _kGen = (t: string, idu: string) => `labuse:doc-gen:${t}:${idu}`

function _set(k: string, v: string): void { try { localStorage.setItem(k, v) } catch { /* navigation privée */ } }
function _get(k: string): string | null { try { return localStorage.getItem(k) } catch { return null } }

/** L'éditeur a bougé : on note l'empreinte COURANTE des saisies. */
export function noterEditeur(docType: string, idu: string | null | undefined, hypotheses: unknown): void {
  if (idu) _set(_kEd(docType, idu), empreinte(hypotheses))
}

/** Un document vient d'être généré : on fige l'empreinte (éditeur = génération → « à jour »). */
export function noterGeneration(docType: string, idu: string | null | undefined, hypotheses: unknown): void {
  if (!idu) return
  const e = empreinte(hypotheses)
  _set(_kGen(docType, idu), e)
  _set(_kEd(docType, idu), e)
}

/** Vrai si l'éditeur diffère de la dernière génération suivie (→ badge « Sources modifiées depuis »). */
export function editeurModifie(docType: string, idu: string | null | undefined): boolean {
  if (!idu) return false
  const gen = _get(_kGen(docType, idu))
  const ed = _get(_kEd(docType, idu))
  return !!(gen && ed && gen !== ed)
}
