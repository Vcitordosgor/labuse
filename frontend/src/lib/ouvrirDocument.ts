// DOCS-FIX-1 (Lot 3, P3/P4) — OUVRIR UN DOCUMENT PROPREMENT.
//
// On REPREND le comportement déjà éprouvé du Bilan (FinancierQuestionnaire.ouvrirDoc) plutôt que
// d'en inventer un : au lieu d'un `window.open('/doc.pdf')` « cru » qui laisse l'onglet BLANC 15-24 s
// pendant la génération puis affiche du JSON brut sur 404/422/500, on `fetch` le document :
//   • pendant la génération, le bouton appelant montre qu'il travaille (état `enCours`), l'app ne fige pas ;
//   • au succès, le PDF s'ouvre depuis un blob (nouvel onglet) ;
//   • en cas d'erreur, un message LISIBLE EN FRANÇAIS est rendu dans l'app (inline ou toast au choix
//     de l'appelant) — JAMAIS de JSON ni d'onglet blanc.
//
// Hook (pas un composant : aucune DA nouvelle) réutilisé par la page Docs (porte + bibliothèque) et
// par les tuiles de la fiche, pour que les 7 documents se comportent partout pareil.
import { useState } from 'react'

// Message FR par statut, en NOMMANT les manques quand le back les fournit (422, comme le Bilan).
async function messageDErreur(r: Response): Promise<string> {
  const detail = (await r.json().catch(() => null))?.detail
  const texte = (d: unknown): string | null =>
    typeof d === 'string' ? d : (d && typeof d === 'object' && typeof (d as { message?: unknown }).message === 'string'
      ? (d as { message: string }).message : null)
  if (r.status === 422) {
    const manques = (detail as { manques?: { libelle?: string }[] } | null)?.manques
    if (Array.isArray(manques) && manques.length)
      return `Document non établissable : il manque ${manques.map((m) => m.libelle).filter(Boolean).join(', ')}.`
    return texte(detail) || 'Document non établissable sur cette parcelle (donnée réglementaire manquante).'
  }
  if (r.status === 404)
    return texte(detail) || "Parcelle inconnue de l'analyse en cours — ce document n'est pas disponible ici."
  if (r.status === 403)
    return texte(detail) || "Ce document n'est pas accessible avec votre offre."
  return texte(detail) || "Le document n'a pas pu être généré (erreur technique). Réessayez ; si cela persiste, signalez-le au support."
}

/** `ouvrir(url, cle)` : fetch + ouverture blob, avec un état d'attente `enCours` (la clé du document
 *  en génération, ou null) et un message d'erreur. Si `onErreur` est fourni (ex. le toast produit),
 *  l'erreur y est envoyée ; sinon elle est exposée dans `erreur` pour un rendu inline. */
export function useOuvrirDocument(onErreur?: (msg: string) => void) {
  const [enCours, setEnCours] = useState<string | null>(null)
  const [erreur, setErreur] = useState<string | null>(null)
  // IMPLANTATION-3 — `init` optionnel : certains documents (l'Étude de faisabilité) se génèrent par
  // POST (la configuration voyage dans le corps), pas par une URL GET. Le reste (blob, erreurs FR,
  // état d'attente) est IDENTIQUE — les deux portes se comportent comme les 7 autres documents.
  const ouvrir = async (url: string, cle: string = url, init?: RequestInit): Promise<boolean> => {
    setErreur(null); setEnCours(cle)
    try {
      const r = await fetch(url, init)
      if (!r.ok) { const m = await messageDErreur(r); (onErreur ?? setErreur)(m); return false }
      window.open(URL.createObjectURL(await r.blob()), '_blank', 'noopener')
      return true
    } catch {
      const m = "Le document n'a pas pu être généré — vérifiez votre connexion et réessayez."
      ;(onErreur ?? setErreur)(m); return false
    } finally {
      setEnCours(null)
    }
  }
  return { ouvrir, enCours, erreur, effacerErreur: () => setErreur(null) }
}
