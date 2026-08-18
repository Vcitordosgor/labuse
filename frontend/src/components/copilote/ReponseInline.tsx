// M78 · 2a — réponse inline QUESTION/OUTIL/VERIFICATION/PROJET/VEILLE/refus (le routeur n'a pas
// lancé de mission lourde). Le bouton de porte ouvre l'outil PRÉ-REMPLI (parcelPrefill/calcPrefill/
// pluPrefill, M-ENTREE/M60). Partagé : Copilote plein écran + surfaces embarquées (§5).
// M78-quater #5 — pouces 👍/👎 RETIRÉS (ne faisaient rien de visible) ; le feedback reviendra en lien
// texte discret (BACKLOG).
import { preDossierUrl, type CopiloteV2Reponse } from '../../lib/api'
import { EMPTY_FILTERS, useApp } from '../../store/useApp'

// M112 — un kind de document → son URL PDF (le front connaît les patterns des 4 exports).
function docUrl(kind: string, idu: string): string {
  if (kind === 'pre-dossier') return preDossierUrl(idu)
  return `/${kind}/${idu}.pdf`   // dossier · dossier-banquier · argumentaire
}

export function ReponseInline({ v2, ton = 'mint' }: {
  v2: CopiloteV2Reponse; ton?: 'mint' | 'violet'
  // M113 · Phase 4 — plus AUCUN bouton de confirmation ni de correction sur une réponse : une
  // réponse qui ne convient pas se corrige en RELANÇANT. Le récap M109 (« J'ai compris : … ») reste,
  // mais comme une PHRASE d'information, jamais un bouton.
}) {
  const { setModule, setParcelPrefill, setCalcPrefill, setPluPrefill,
    setView, setCommune, setFilters, openSurveillance, toggleOutils, outilsOpen } = useApp()
  const mauve = ton === 'violet'
  const ouvrir = () => {
    if (!v2.porte) return
    if (v2.prefill_plu) setPluPrefill(v2.prefill_plu)
    else if (v2.prefill === 'calcPrefill' && v2.prefill_idu) setCalcPrefill(v2.prefill_idu)
    else if (v2.prefill_idu) setParcelPrefill(v2.prefill_idu)
    setModule(v2.porte)
  }
  // M112 P2.1 — ouvrir la CARTE FILTRÉE : la facette est le point unique (mêmes critères comptés).
  const ouvrirCarte = () => {
    const cf = v2.carte_filtre!
    setFilters({ ...EMPTY_FILTERS, ...(cf.filtres as Partial<typeof EMPTY_FILTERS>) })
    if (cf.commune) setCommune(cf.commune)
    setView('cartes')
  }
  const btnCls = mauve
    ? 'border-violet/40 bg-violet/10 text-violet hover:bg-violet/15'
    : 'border-mint/40 bg-mint/10 text-mint hover:bg-mint/15'
  const bord = v2.refus && v2.refus !== 'hors_sujet' ? 'border-cp-amber/30'
    : v2.intent === 'HORS_SUJET' ? 'border-cp-line2' : mauve ? 'border-violet/30' : 'border-mint/25'
  return (
    <div data-reponse className={`rounded-2xl border ${bord} bg-cp-card px-5 py-4 text-left`}>
      {/* M102-B2 — récap systématique : une phrase, un bouton Corriger, jamais un formulaire. */}
      {v2.compris && (
        <p data-compris className="mb-2 text-[11.5px] text-cp-muted">{v2.compris}</p>
      )}
      <p className="whitespace-pre-wrap text-[13.5px] leading-relaxed text-cp-txt">{v2.text}</p>
      {v2.porte && (
        <button data-reponse-porte onClick={ouvrir}
          className={`mt-3 rounded-lg border px-4 py-2 font-display text-[12px] font-semibold transition-colors duration-quick ${btnCls}`}>
          Ouvrir l'outil →
        </button>
      )}
      {/* M112 P2.1 — carte filtrée (les critères comptés, posés sur la carte). */}
      {v2.carte_filtre && (
        <button data-reponse-carte onClick={ouvrirCarte}
          className={`mt-3 rounded-lg border px-4 py-2 font-display text-[12px] font-semibold transition-colors duration-quick ${btnCls}`}>
          Ouvrir la carte filtrée sur {v2.carte_filtre.libelle} →
        </button>
      )}
      {/* M112 P2.2 — Surveillance (le bon volet). */}
      {v2.surveillance && (
        <button data-reponse-surveillance onClick={() => openSurveillance(v2.surveillance!.volet)}
          className={`mt-3 rounded-lg border px-4 py-2 font-display text-[12px] font-semibold transition-colors duration-quick ${btnCls}`}>
          Ouvrir la Surveillance →
        </button>
      )}
      {/* M112 P2.3 — document (PDF, IDU résolu). */}
      {v2.document && (
        <a data-reponse-document href={docUrl(v2.document.kind, v2.document.idu)} target="_blank" rel="noreferrer"
          className={`mt-3 inline-block rounded-lg border px-4 py-2 font-display text-[12px] font-semibold transition-colors duration-quick ${btnCls}`}>
          Éditer le {v2.document.libelle} →
        </a>
      )}
      {/* M116 · D4 — « ouvrir un outil » sans outil précis : la voie = la LISTE des outils (jamais un refus). */}
      {v2.outils_liste && (
        <button data-reponse-outils onClick={() => { if (!outilsOpen) toggleOutils() }}
          className={`mt-3 rounded-lg border px-4 py-2 font-display text-[12px] font-semibold transition-colors duration-quick ${btnCls}`}>
          Voir les outils d'analyse →
        </button>
      )}
      {(v2.sources?.length ?? 0) > 0 && (
        <p className="mt-2.5 font-mono text-[10px] text-cp-faint">{v2.sources!.join(' · ')}</p>
      )}
    </div>
  )
}
