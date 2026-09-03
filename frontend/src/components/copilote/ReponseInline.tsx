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
// COPILOTE-REFONTE — le MUR « PAS D'OUTIL DÉDIÉ » disparaît : quand aucun outil ne couvre, le serveur
// bascule sur la connaissance générale (badge « RÉPONSE GÉNÉRALE ») ou propose une voie — plus de slug sec.
const KICKER: Record<string, string> = {
  critere_non_applicable: 'CRITÈRE NON APPLICABLE',
  web_rien_trouve: 'RIEN TROUVÉ SUR LE WEB', proprietaire_pp: 'DONNÉE NON OUVERTE',
  projection: 'PAS DE PROJECTION', outil_a_choisir: 'CHOISIR UN OUTIL',
}

export function ReponseInline({ v2 }: { v2: CopiloteV2Reponse }) {
  const { setModule, setParcelPrefill, setCalcPrefill, setPluPrefill, setM22Prefill, setEtudeZonePrefill,
    setView, setFilters, setVerdict, openListing, openSurveillance, toggleOutils, outilsOpen, select } = useApp()
  // M118 — la VOIE d'un refus-voie : NAVIGATION pure vers la surface qui fait le travail (jamais une
  // exécution). Chaque cible mène à son écran ; la fiche/courrier ouvre la parcelle si l'IDU est connu.
  const allerVoie = () => {
    const v = v2.voie!
    if (v.cible === 'projets') setView('projets')
    else if (v.cible === 'surveillance') openSurveillance('secteurs')
    else if (v.cible === 'outils') { if (!outilsOpen) toggleOutils() }
    else if (v.cible === 'fiche' || v.cible === 'courriers') {
      if (v.idu) { setView('cartes'); select(v.idu) } else if (v.cible === 'courriers') setModule('courriers')
      else setView('cartes')
    }
  }
  const ouvrir = () => {
    if (!v2.porte) return
    if (v2.prefill_programme) setM22Prefill(v2.prefill_programme)   // Q11 — pré-remplit la Faisabilité (M22)
    else if (v2.prefill_etude_zone) setEtudeZonePrefill(v2.prefill_etude_zone)   // DESTINATIONS-1 (X4.4)
    else if (v2.prefill_plu) setPluPrefill(v2.prefill_plu)
    else if (v2.prefill === 'calcPrefill' && v2.prefill_idu) setCalcPrefill(v2.prefill_idu)
    else if (v2.prefill_idu) setParcelPrefill(v2.prefill_idu)
    setModule(v2.porte)
  }
  const ouvrirCarte = () => {
    const cf = v2.carte_filtre!
    // M137-I — à l'arrivée, le résultat est DÉJÀ VISIBLE : filtre appliqué + listing ouvert, pas un
    // filtre à confirmer. Trois points :
    //  • la commune passe par le FILTRE `communes` (et non `setCommune`) → on RESTE en mode ÎLE, dont
    //    le listing est SERVEUR (getResults) et applique TOUS les critères, signaux compris. Le mode
    //    commune, lui, liste le GeoJSON filtré CLIENT (matchAll) qui IGNORE les signaux → il aurait
    //    montré toutes les parcelles de la commune, pas les {N} annoncées (mesuré : 33 910 vs 66).
    //  • FIX-PONT-TIER — `analyseLabuse` dépend du critère ANNONCÉ :
    //     - question NON-TIER (signaux/surface, portés par `rest`) → analyseLabuse reste FAUX : mode
    //       FACTUEL, le compte = celui du Copilote (facette `tiers=None` ≡ « toute la trame » ; parade
    //       M137-I mesurée 33 910 vs 66). L'analyse retirerait l'étage 0 → compte plus petit.
    //     - question PAR TIER (`cf.filtres.tiers`) → analyseLabuse VRAI : sinon `tiersParam` (api.ts),
    //       en factuel, IGNORE `filters.tiers` et sert la trame entière → la carte contredirait le
    //       compte annoncé (ex. « brûlantes » annoncées, commune entière affichée). Armé, il sert
    //       EXACTEMENT ces tiers → même SQL que le comptage du Copilote → mêmes chiffres.
    //  • `setVerdict(true)` monte ResultsSection ; `openListing()` ouvre le panneau sur la liste.
    const parTier = Array.isArray(cf.filtres.tiers) && (cf.filtres.tiers as unknown[]).length > 0
    setFilters({ ...EMPTY_FILTERS, ...(cf.filtres as Partial<typeof EMPTY_FILTERS>),
      ...(cf.commune ? { communes: [cf.commune] } : {}),
      ...(parTier ? { analyseLabuse: true } : {}) })
    setVerdict(true)
    openListing()
    setView('cartes')
  }

  const refus = v2.refus || null
  // COPILOTE-REFONTE (DA point 8) — le MAUVE (surface IA) est RÉSERVÉ à ce qui EST de l'IA :
  //  · `general` (voie b, connaissance générale) = assumé IA → mauve + badge « hors données LABUSE » ;
  //  · une réponse SOURCÉE LABUSE (voie a : sources/outil, hors refus) N'EST PAS de l'IA → variante
  //    `sourced` NON mauve (la donnée ne se déguise pas en avis d'IA). Le reste (clarification…) = IA.
  const sourced = !v2.general && !refus && !v2.erreur && !v2.degraded
    && ((v2.sources && v2.sources.length > 0) || !!v2.tool)
  const variant = v2.erreur || v2.degraded ? 'err'
    : refus === 'hors_sujet' ? 'neutral'
      : refus ? 'warn'
        : sourced ? 'sourced' : 'ia'
  // M117 · D10 — un SEUL gabarit de précision : la carte IA avec le kicker « PRÉCISION » ; le champ
  // est le champ PERMANENT du fil (autofocus quand clarification), jamais un second cadre.
  const kickerClarif = v2.clarification && !refus ? 'PRÉCISION' : null
  const card = {
    ia: 'border-cp-ia-border bg-cp-ia-bg', warn: 'border-cp-warn-border bg-cp-warn-bg',
    err: 'border-cp-danger-border bg-cp-danger-bg', neutral: 'border-cp-line2 bg-cp-card',
    sourced: 'border-cp-line2 bg-cp-card',   // donnée LABUSE : neutre, jamais le mauve de l'IA
  }[variant]
  const porteCls = variant === 'warn'
    ? 'border-cp-warn-border bg-cp-warn/[0.08] text-cp-warn hover:bg-cp-warn/15'
    : 'border-cp-ia-border-on bg-cp-ia/[0.06] text-cp-ia hover:bg-cp-ia/12'
  // le badge voie b PRIME sur le kicker de refus/précision (le refus « aucun_outil » n'existe plus en mur).
  const kick = v2.general ? 'RÉPONSE GÉNÉRALE — HORS DONNÉES LABUSE' : refus ? KICKER[refus] : kickerClarif

  return (
    <div data-reponse data-variant={variant} className={`rounded-xl border ${card} px-[18px] py-4 text-left`}>
      {kick && (
        <div className={`mb-2.5 font-mono text-[11px] tracking-[.14em] ${variant === 'warn' ? 'text-cp-warn' : variant === 'err' ? 'text-cp-danger' : 'text-cp-ia'}`}>{kick}</div>
      )}
      {/* récap M109 — une PHRASE d'information, jamais un bouton (D7 : déjà dédupliqué côté serveur). */}
      {v2.compris && <p data-compris className="mb-2.5 text-[12px] leading-snug text-cp-muted">{v2.compris}</p>}
      <p className="whitespace-pre-wrap text-[14px] leading-relaxed text-cp-txt">{v2.text}</p>

      {/* DESTINATIONS-1 (X4.4) — la PHRASE SOURCÉE du verdict destination, servie TELLE QUELLE
          (article/page/millésime/CDAC) — le fait exact sous la formulation, jamais reformulé. */}
      {v2.destination_phrase && (
        <p data-destination-phrase className="mt-2.5 rounded-lg border border-cp-line2 bg-cp-card/60 px-3 py-2 text-[12px] leading-snug text-cp-muted">
          {v2.destination_phrase}
        </p>
      )}

      {v2.porte && (
        <button data-reponse-porte onClick={ouvrir}
          className={`mt-3.5 inline-flex rounded-lg border px-3.5 py-2 font-display text-[12.5px] transition-colors duration-quick ${porteCls}`}>
          {v2.porte === 'etude-zone' && v2.prefill_etude_zone ? 'Étude de zone →' : "Ouvrir l'outil →"}
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
          Ouvrir la Veille →
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
      {/* M118 — la VOIE d'un refus-voie : navigation vers la surface qui fait le travail. */}
      {v2.voie && (
        <button data-reponse-voie data-voie-cible={v2.voie.cible} onClick={allerVoie}
          className={`mt-3.5 inline-flex rounded-lg border px-3.5 py-2 font-display text-[12.5px] transition-colors duration-quick ${porteCls}`}>
          {v2.voie.libelle} →
        </button>
      )}
      {(v2.sources?.length ?? 0) > 0 && (
        <p className="mt-3 font-mono text-[10.5px] uppercase tracking-[.06em] text-cp-faint">SOURCE · {v2.sources!.join(' · ')}</p>
      )}
    </div>
  )
}
