// CHASSE-DOCS-FIX-1 (Lot 5.1) — « Sources modifiées depuis » réagit AUSSI aux SAISIES.
//
// L'empreinte des hypothèses est calculée par le front À LA GÉNÉRATION et STOCKÉE AVEC LE DOCUMENT
// CÔTÉ SERVEUR (documents_generes, cf. api.ts genererBilan / etudePdfInit → hypotheses._empreinte,
// renvoyée par la bibliothèque). Le badge compare cette empreinte serveur (cross-poste, visible d'un
// autre poste ou pour un collègue) à l'empreinte de l'ÉDITEUR VIVANT — celle-ci reste locale par nature
// (une édition en cours n'existe que là où on édite), publiée en localStorage par l'éditeur (noterEditeur).
// Aucun nouveau composant, DA existante. Clé éditeur = (type, idu).

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

function _set(k: string, v: string): void { try { localStorage.setItem(k, v) } catch { /* navigation privée */ } }
function _get(k: string): string | null { try { return localStorage.getItem(k) } catch { return null } }

/** L'éditeur a bougé : on note l'empreinte COURANTE des saisies (publiée en localStorage, par nature locale). */
export function noterEditeur(docType: string, idu: string | null | undefined, hypotheses: unknown): void {
  if (idu) _set(_kEd(docType, idu), empreinte(hypotheses))
}

/** Vrai si l'éditeur vivant diffère de l'empreinte STOCKÉE AVEC LE DOCUMENT (serveur) → badge « Sources
 * modifiées depuis ». Pas d'empreinte serveur (vieux doc) ou pas d'éditeur ouvert ici → pas de faux positif. */
export function editeurDiffere(docType: string, idu: string | null | undefined, empreinteServeur?: string | null): boolean {
  if (!idu || !empreinteServeur) return false
  const ed = _get(_kEd(docType, idu))
  return !!(ed && ed !== empreinteServeur)
}
