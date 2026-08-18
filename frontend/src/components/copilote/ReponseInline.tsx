// M78 · 2a → M117 — réponse inline QUESTION/OUTIL/VEILLE/refus, au GABARIT CARTE de la maquette
// DA-COPILOTE-v2 : carte IA (mauve) par défaut, `warn` pour un refus/critère non applicable, `err`
// pour une erreur, `neutral` pour un hors-sujet. Kicker mono, récap M109 en phrase (jamais un bouton),
// source en mono, PORTE cliquable (la voie — D6 : un refus utile propose une voie, jamais un champ).
// Partagé : Copilote plein écran + surfaces embarquées (§5). Surface IA → mauve exclusif.
import { preDossierUrl, type CopiloteV2Reponse } from '../../lib/api'
import { EMPTY_FILTERS, useApp } from '../../store/useApp'

function docUrl(kind: string, idu: string): string {
  if (kind === 'pre-dossier') return preDossierUrl(idu)
  return `/${kind}/${idu}.pdf`   // dossier · dossier-banquier · argumentaire
}

// refus → un kicker mono lisible (jamais un slug). L'absence = pas de kicker (réponse normale).
const KICKER: Record<string, string> = {
  critere_non_applicable: 'CRITÈRE NON APPLICABLE', aucun_outil: "PAS D'OUTIL DÉDIÉ",
  web_rien_trouve: 'RIEN TROUVÉ SUR LE WEB', proprietaire_pp: 'DONNÉE NON OUVERTE',
  projection: 'PAS DE PROJECTION', outil_a_choisir: 'CHOISIR UN OUTIL',
}

export function ReponseInline({ v2 }: { v2: CopiloteV2Reponse }) {
  const { setModule, setParcelPrefill, setCalcPrefill, setPluPrefill,
    setView, setCommune, setFilters, openSurveillance, toggleOutils, outilsOpen } = useApp()
  const ouvrir = () => {
    if (!v2.porte) return
    if (v2.prefill_plu) setPluPrefill(v2.prefill_plu)
    else if (v2.prefill === 'calcPrefill' && v2.prefill_idu) setCalcPrefill(v2.prefill_idu)
    else if (v2.prefill_idu) setParcelPrefill(v2.prefill_idu)
    setModule(v2.porte)
  }
  const ouvrirCarte = () => {
    const cf = v2.carte_filtre!
    setFilters({ ...EMPTY_FILTERS, ...(cf.filtres as Partial<typeof EMPTY_FILTERS>) })
    if (cf.commune) setCommune(cf.commune)
    setView('cartes')
  }

  const refus = v2.refus || null
  const variant = v2.erreur || v2.degraded ? 'err'
    : refus === 'hors_sujet' ? 'neutral'
      : refus ? 'warn' : 'ia'
  // M117 · D10 — un SEUL gabarit de précision : la carte IA avec le kicker « PRÉCISION » ; le champ
  // est le champ PERMANENT du fil (autofocus quand clarification), jamais un second cadre.
  const kickerClarif = v2.clarification && !refus ? 'PRÉCISION' : null
  const card = {
    ia: 'border-cp-ia-border bg-cp-ia-bg', warn: 'border-cp-warn-border bg-cp-warn-bg',
    err: 'border-cp-danger-border bg-cp-danger-bg', neutral: 'border-cp-line2 bg-cp-card',
  }[variant]
  const porteCls = variant === 'warn'
    ? 'border-cp-warn-border bg-cp-warn/[0.08] text-cp-warn hover:bg-cp-warn/15'
    : 'border-cp-ia-border-on bg-cp-ia/[0.06] text-cp-ia hover:bg-cp-ia/12'
  const kick = refus ? KICKER[refus] : kickerClarif

  return (
    <div data-reponse data-variant={variant} className={`rounded-xl border ${card} px-[18px] py-4 text-left`}>
      {kick && (
        <div className={`mb-2.5 font-mono text-[11px] tracking-[.14em] ${variant === 'warn' ? 'text-cp-warn' : variant === 'err' ? 'text-cp-danger' : 'text-cp-ia'}`}>{kick}</div>
      )}
      {/* récap M109 — une PHRASE d'information, jamais un bouton (D7 : déjà dédupliqué côté serveur). */}
      {v2.compris && <p data-compris className="mb-2.5 text-[12px] leading-snug text-cp-muted">{v2.compris}</p>}
      <p className="whitespace-pre-wrap text-[14px] leading-relaxed text-cp-txt">{v2.text}</p>

      {v2.porte && (
        <button data-reponse-porte onClick={ouvrir}
          className={`mt-3.5 inline-flex rounded-lg border px-3.5 py-2 font-display text-[12.5px] transition-colors duration-quick ${porteCls}`}>
          Ouvrir l'outil →
        </button>
      )}
      {v2.carte_filtre && (
        <button data-reponse-carte onClick={ouvrirCarte}
          className={`mt-3.5 inline-flex rounded-lg border px-3.5 py-2 font-display text-[12.5px] transition-colors duration-quick ${porteCls}`}>
          Voir sur la carte {v2.carte_filtre.libelle} →
        </button>
      )}
      {v2.surveillance && (
        <button data-reponse-surveillance onClick={() => openSurveillance(v2.surveillance!.volet)}
          className={`mt-3.5 inline-flex rounded-lg border px-3.5 py-2 font-display text-[12.5px] transition-colors duration-quick ${porteCls}`}>
          Ouvrir la Surveillance →
        </button>
      )}
      {v2.document && (
        <a data-reponse-document href={docUrl(v2.document.kind, v2.document.idu)} target="_blank" rel="noreferrer"
          className={`mt-3.5 inline-flex rounded-lg border px-3.5 py-2 font-display text-[12.5px] transition-colors duration-quick ${porteCls}`}>
          Éditer le {v2.document.libelle} →
        </a>
      )}
      {/* D4/D6 — la voie « ouvrir un outil » : la LISTE des outils, jamais un refus sec. */}
      {v2.outils_liste && (
        <button data-reponse-outils onClick={() => { if (!outilsOpen) toggleOutils() }}
          className={`mt-3.5 inline-flex rounded-lg border px-3.5 py-2 font-display text-[12.5px] transition-colors duration-quick ${porteCls}`}>
          Voir les outils d'analyse →
        </button>
      )}
      {(v2.sources?.length ?? 0) > 0 && (
        <p className="mt-3 font-mono text-[10.5px] uppercase tracking-[.06em] text-cp-faint">SOURCE · {v2.sources!.join(' · ')}</p>
      )}
    </div>
  )
}
