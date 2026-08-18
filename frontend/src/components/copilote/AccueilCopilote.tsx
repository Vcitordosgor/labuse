// M78 · 2a → M117 · ACCUEIL Copilote v2 (maquette DA-COPILOTE-v2). Un SEUL point d'entrée : les six
// intentions (grille, sous-titres servis par le serveur) remplacent les chips, les six exemples et
// les trois cartes explicatives. Le bandeau de garanties est absorbé sous le titre ; le brief descend
// sous le point d'entrée (ce n'est pas une action de Copilote). Surface IA → accent MAUVE (cp-ia) ;
// le mint ne reste QUE sur le brief du matin (veille ≠ IA).
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { ilYA } from '../../lib/format'
import { getBrief, getScenarios, type AccueilChiffres, type BriefMatin, type CopiloteMission,
  type CopiloteScenario } from '../../lib/api'
import { MODULES } from '../outils/registry'

export function AccueilCopilote({ value, onChange, onSubmit, chiffres, occupe, reponse,
  scenario, onScenario, missions, onReprendre }: {
  value: string
  onChange: (v: string) => void
  onSubmit: () => void
  chiffres: AccueilChiffres | null
  occupe?: boolean            // dispatch en cours (le routeur réfléchit)
  reponse?: ReactNode         // réponse inline QUESTION/OUTIL/refus (2a → 2e)
  scenario?: string | null    // M113 — chip de contexte choisi (null = texte libre)
  onScenario?: (cle: string | null) => void
  missions?: CopiloteMission[]           // §2b — historique (« Vos dernières questions »)
  onReprendre?: (m: CopiloteMission) => void
}) {
  const ref = useRef<HTMLTextAreaElement | null>(null)
  useEffect(() => { ref.current?.focus() }, [])
  // M113 · Phase 2 — les CHIPS de contexte, servis par le serveur (jamais en dur). « Que souhaitez-vous
  // faire ? » Un chip force le scénario ; le champ adapte son placeholder. Le texte libre reste possible
  // (aucun chip sélectionné → le routeur décide, comportement M112). Échec du fetch → pas de chips, la
  // voie libre suffit (dégradation propre).
  const [scenarios, setScenarios] = useState<CopiloteScenario[]>([])
  useEffect(() => { getScenarios().then(setScenarios).catch(() => {}) }, [])
  const scenActif = scenarios.find((s) => s.cle === scenario) || null
  // M85 Phase 3 — le brief du matin (déterministe). Affiché en tête SEULEMENT s'il est frais (non vide) :
  // on ne remplit jamais l'accueil avec un brief creux (l'honnêteté du « rien de neuf »). Vert/neutre,
  // jamais mauve (ce n'est pas de l'IA — ce sont des faits datés). Fetch simple (motif AccueilChiffres
  // de CopiloteView) — pas de QueryClient requis.
  const [brief, setBrief] = useState<BriefMatin | null>(null)
  useEffect(() => { getBrief().then(setBrief).catch(() => {}) }, [])
  // M87 P6 — le brief QUITTE le flux : une barre + un panneau latéral (scrim, Échap, clic-dehors, focus
  // piégé). Recopié de docs/DA-ACCUEIL-BRIEF-v1.html. N vient d'event_log (brief.n) — MÊME point de
  // lecture que l'e-mail Brevo. N=0 → « Rien de neuf depuis hier » et la barre NE disparaît pas.
  const [briefOpen, setBriefOpen] = useState(false)
  const panelRef = useRef<HTMLElement | null>(null)
  useEffect(() => {
    if (!briefOpen) return
    const prev = document.activeElement as HTMLElement | null
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { setBriefOpen(false); return }
      if (e.key === 'Tab' && panelRef.current) {           // focus PIÉGÉ dans le panneau
        const foc = panelRef.current.querySelectorAll<HTMLElement>('button, a[href], [tabindex]:not([tabindex="-1"])')
        if (!foc.length) return
        const first = foc[0], last = foc[foc.length - 1]
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus() }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus() }
      }
    }
    document.addEventListener('keydown', onKey)
    const t = window.setTimeout(() => panelRef.current?.querySelector<HTMLElement>('[data-brief-close]')?.focus(), 0)
    return () => { document.removeEventListener('keydown', onKey); window.clearTimeout(t); prev?.focus?.() }
  }, [briefOpen])
  const briefN = brief?.n ?? 0
  const briefDate = brief?.genere_le
    ? new Date(brief.genere_le).toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' })
    : ''
  const [toutHisto, setToutHisto] = useState(false)   // #2 — « voir tout » au-delà de 4

  // #2 — DÉDOUBLONNER par question (missions déjà triées updated_at DESC → 1re occurrence = plus récente).
  const questions = useMemo(() => {
    const vu = new Set<string>()
    const out: CopiloteMission[] = []
    for (const m of missions ?? []) {
      const cle = (m.titre || '').trim().toLowerCase()
      if (!cle || vu.has(cle)) continue
      vu.add(cle); out.push(m)
    }
    return out
  }, [missions])
  const questionsVisibles = toutHisto ? questions : questions.slice(0, 4)

  // [N] DYNAMIQUE — masqué (pas inventé) si le bandeau ne l'a pas encore. Aucun compte en dur.
  const nSources = chiffres?.sources != null ? String(chiffres.sources) : null

  return (
    <div data-accueil className="mx-auto max-w-[620px] px-2 pt-6">
      {/* HERO — le bandeau de garanties est ABSORBÉ sous le titre (M117). Kicker + « instruit » en mauve. */}
      <div className="mb-9 text-center">
        <div className="mb-3.5 font-mono text-[11px] tracking-[.16em] text-cp-ia">COPILOTE</div>
        <h1 className="mb-2.5 font-display text-[30px] font-medium leading-[1.25] tracking-[-.5px] text-cp-txt">
          Dites ce que vous cherchez.<br />Le Copilote <span className="text-cp-ia">instruit</span>.
        </h1>
        <p data-accueil-tagline className="text-[13px] text-cp-muted">
          {nSources ? <><b className="text-cp-txt">{nSources}</b> sources · </> : null}chaque chiffre daté · La Réunion uniquement
        </p>
      </div>

      {/* M87 P6 — le SCRIM + le PANNEAU latéral (classes .scrim / .panel de la maquette). Clic-dehors et
          Échap ferment (gérés plus haut) ; le focus est piégé. Contenu GROUPÉ par commune (brief.groupes),
          même producteur que l'e-mail — pas de seconde fenêtre qui diverge. */}
      <div onClick={() => setBriefOpen(false)}
        className={`fixed inset-0 z-40 bg-black/55 transition-opacity duration-quick ${briefOpen ? 'opacity-100' : 'pointer-events-none opacity-0'}`} />
      <aside ref={panelRef} aria-label="Brief du matin" aria-hidden={!briefOpen}
        className={`fixed right-0 top-0 z-50 flex h-full w-[min(440px,100%)] flex-col border-l border-cp-line bg-cp-bg transition-transform duration-[240ms] ${briefOpen ? 'translate-x-0' : 'translate-x-full'}`}>
        <header className="flex items-center gap-3 border-b border-cp-line px-[22px] py-5">
          <h2 className="m-0 font-mono text-[11px] tracking-[.16em] text-cp-txt">BRIEF DU MATIN</h2>
          {briefDate && <span className="font-mono text-[11px] text-cp-muted">{briefDate}</span>}
          <button data-brief-close onClick={() => setBriefOpen(false)} aria-label="Fermer le brief"
            className="ml-auto border-0 bg-transparent text-[18px] text-cp-muted transition-colors duration-quick hover:text-cp-txt">✕</button>
        </header>
        <p className="border-b border-cp-line px-[22px] py-4 text-[13px] leading-snug text-cp-muted">
          Ce qui a bougé sur <b className="font-semibold text-cp-txt">vos parcelles suivies</b> et dans <b className="font-semibold text-cp-txt">vos secteurs</b> depuis hier.
        </p>
        <div className="min-h-0 flex-1 overflow-y-auto pb-6">
          {briefN === 0 && <p className="px-[22px] py-6 text-[13px] text-cp-muted">Rien de neuf depuis hier.</p>}
          {(brief?.groupes ?? []).map((g, i) => (
            <div key={i} className="border-b border-cp-line px-[22px] py-4 last:border-b-0">
              <div className="flex items-baseline gap-2.5">
                <h3 className="m-0 text-[14px] font-semibold text-cp-txt">{g.commune}</h3>
                <span className="font-mono text-[11px] text-mint">{g.n} événement{g.n > 1 ? 's' : ''}</span>
                {g.ts_max && <span className="ml-auto font-mono text-[10.5px] text-cp-muted">{ilYA(g.ts_max)}</span>}
              </div>
              {g.sources?.length ? <p className="mt-1.5 text-[12.5px] text-cp-muted">{g.sources.join(' · ')}</p> : null}
              {g.idus?.length ? (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {g.idus.map((id) => <code key={id} className="font-mono text-[10.5px] text-cp-muted">{id}</code>)}
                </div>
              ) : null}
            </div>
          ))}
          {/* Ligne SECTEUR (permis SITADEL, M83) — appoint honnête tant que les crons ne tournent pas. */}
          {(brief?.secteurs?.permis_depuis_hier ?? 0) > 0 && (
            <div className="border-b border-cp-line px-[22px] py-4 last:border-b-0">
              <h3 className="m-0 text-[14px] font-semibold text-cp-txt">Sur vos secteurs</h3>
              <p className="mt-1.5 text-[12.5px] text-cp-muted">
                <b className="text-cp-txt">{brief!.secteurs.permis_depuis_hier}</b> nouveau·x permis depuis hier
                {brief!.secteurs.communes?.length ? <> ({brief!.secteurs.communes.slice(0, 4).join(', ')})</> : null}.
              </p>
            </div>
          )}
        </div>
        {/* Pas de liens morts : la cloche (en haut à droite) et les préférences vivent ailleurs — on le dit. */}
        <footer className="border-t border-cp-line px-[22px] py-3.5 text-[12px] text-cp-muted">
          Retrouvez l'historique complet et vos préférences d'envoi dans la cloche, en haut à droite.
        </footer>
      </aside>

      {/* M117 · les SIX INTENTIONS en grille (remplacent chips + exemples + cartes). Sous-titre servi
          par le serveur (« {n} outils » → MODULES.length, aucun compte en dur). Un clic sélectionne
          (ou désélectionne) le scénario ; le champ adapte son placeholder. Surface IA → mauve. */}
      {!reponse && scenarios.length > 0 && (
        <div data-accueil-intents className="mb-3.5 grid grid-cols-2 gap-2 min-[560px]:grid-cols-3">
          {scenarios.map((s) => {
            const on = s.cle === scenario
            const sub = (s.sub || '').replace('{n}', String(MODULES.length))
            return (
              <button key={s.cle} data-accueil-chip data-chip-cle={s.cle} aria-pressed={on}
                onClick={() => onScenario?.(on ? null : s.cle)}
                className={`rounded-[10px] border px-3.5 py-3.5 text-left transition-colors duration-quick ${
                  on ? 'border-cp-ia bg-cp-ia-bg' : 'border-cp-ia-border bg-cp-ia-bg/40 hover:border-cp-ia-border-on'}`}>
                <div className={`mb-[3px] text-[14px] ${on ? 'text-cp-ia' : 'text-cp-txt'}`}>{s.libelle}</div>
                <div className="text-[12px] leading-[1.4] text-cp-muted">{sub}</div>
              </button>
            )
          })}
        </div>
      )}

      {/* barre unique — M87 P2 : FOCUS sans contour vert. Le contour :focus-visible mint (index.css) est
          neutralisé sur le champ ; le focus reste PERCEPTIBLE au clavier via la barre (border renforcée +
          fond #12170F, comme la maquette). On remplace le focus, on ne le supprime pas (accessibilité).
          M113 — ÉTAPE 2 : le placeholder s'adapte au scénario choisi (servi par le serveur). */}
      <div data-accueil-barre className="mb-3.5 flex items-center gap-3 rounded-xl border border-cp-line bg-cp-card/60 py-2 pl-[18px] pr-2 transition-colors duration-quick focus-within:border-cp-line2 focus-within:bg-[#12170F]">
        <textarea ref={ref} data-brief rows={1} value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); if (value.trim()) onSubmit() } }}
          placeholder={scenActif?.placeholder ?? '15 logements à Saint-Denis, budget foncier 800 k€…'}
          className="max-h-24 min-h-[24px] flex-1 resize-none bg-transparent py-1.5 text-[14px] leading-normal text-cp-txt outline-none focus-visible:outline-none placeholder:text-cp-faint" />
        <button data-accueil-envoyer onClick={() => value.trim() && onSubmit()} disabled={!value.trim() || occupe}
          className="shrink-0 rounded-lg bg-cp-ia px-5 py-2.5 text-[13px] font-medium text-cp-ia-on transition-[filter] duration-quick hover:brightness-110 disabled:opacity-40">
          {occupe ? '…' : 'Envoyer'}
        </button>
      </div>
      <p className="mb-4 text-center text-[11px] text-cp-faint">
        {scenActif ? <>Mode « {scenActif.libelle} » — <button data-chip-liberer onClick={() => onScenario?.(null)}
          className="underline decoration-cp-faint/50 underline-offset-2 hover:text-cp-txt">écrire librement</button> à la place.</>
          : 'Écrivez librement — ou choisissez ce que vous souhaitez faire ci-dessus.'}
      </p>

      {/* M117 — les six exemples et les trois cartes explicatives DISPARAISSENT (les six intentions
           portent seules ce rôle). Le bandeau de garanties est absorbé dans la tagline. */}

      {reponse && <div data-accueil-reponse className="mb-8">{reponse}</div>}

      {/* M117 — LE BRIEF descend SOUS le point d'entrée (ce n'est pas une action de Copilote). Reste
           en MINT : la veille n'est pas de l'IA (seule exception mint sur cette surface). */}
      {!reponse && brief && (
        <button data-brief-btn onClick={() => setBriefOpen(true)}
          className="mb-7 flex w-full items-center gap-3 rounded-[10px] bg-cp-card px-4 py-3 transition-colors duration-quick hover:bg-cp-card2">
          <span className="h-[6px] w-[6px] shrink-0 rounded-full bg-mint" />
          <span className="text-[14px] text-cp-txt">Votre brief du matin</span>
          <span className="ml-auto font-mono text-[12px] uppercase tracking-[.06em] text-cp-muted">
            {briefN > 0 ? `${briefN} événement${briefN > 1 ? 's' : ''} depuis hier` : 'Rien de neuf depuis hier'}
          </span>
          <span className="text-cp-muted">→</span>
        </button>
      )}

      {/* REPRENDRE — conversations passées, dédoublonnées, datées en relatif, 4 max puis « voir tout ». */}
      {!reponse && questions.length > 0 && (
        <div data-accueil-historique className="mb-8">
          <p className="mb-2.5 font-mono text-[10px] tracking-[.12em] text-cp-faint">REPRENDRE</p>
          <div className="flex flex-col">
            {questionsVisibles.map((m) => (
              <button key={m.id} data-mission-reprendre onClick={() => onReprendre?.(m)}
                className="flex items-center gap-3 border-b border-cp-line/60 py-2.5 text-left transition-colors duration-quick last:border-b-0 hover:text-cp-txt">
                <span className="min-w-0 flex-1 truncate text-[14px] text-cp-txt">{m.titre}</span>
                {m.run_id && <span className="shrink-0 rounded border border-cp-ia/30 px-1.5 py-px text-[9px] uppercase tracking-wide text-cp-ia">recherche</span>}
                <span className="shrink-0 font-mono text-[11px] text-cp-faint">{ilYA(m.updated_at)}</span>
              </button>
            ))}
          </div>
          {questions.length > 4 && (
            <button data-histo-tout onClick={() => setToutHisto((v) => !v)}
              className="mt-3 font-mono text-[11px] tracking-[.06em] text-cp-muted hover:text-cp-txt">
              {toutHisto ? 'RÉDUIRE' : `VOIR TOUT · ${questions.length}`}
            </button>
          )}
        </div>
      )}
    </div>
  )
}
