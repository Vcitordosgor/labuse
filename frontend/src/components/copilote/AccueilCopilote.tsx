// M78 → M133 · ACCUEIL Copilote v3 (maquette docs/DA-COPILOTE-ACCUEIL-v3.html). Corrige les 4 défauts
// post-M118 : (1) le titre ne promet plus l'ancienne mission d'instruction (morte en M118) ; (2) le placeholder est une
// VRAIE mission (donnée), plus l'exemple d'instruction morte ; (3) les 4 capacités deviennent du TEXTE
// (libellé + exemple réel), non cliquables — le routeur comprend seul, rien à choisir ; (4) le champ
// passe EN PREMIER, sous le hero. Titre/sous-titre/placeholder/aide + capacités SERVIS (jamais en dur).
// Surface IA → accent MAUVE (cp-ia) ; le mint ne reste QUE sur le brief du matin (veille ≠ IA).
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { ilYA } from '../../lib/format'
import { getAccueilCopilote, getBrief, type AccueilCopiloteMeta, type BriefMatin,
  type CopiloteMission } from '../../lib/api'

// RETOURS-3 R12 (maquette-copilote-v3) — une TUILE d'icône contrastée par capacité (fond mauve ~22 %,
// contour ~48 %, glyphe 20 px stroke 2.1). Mappée sur la `cle` servie (donnees/web/expliquer/preparer) ;
// une clé inconnue tombe sur l'étincelle générique (jamais de tuile vide).
const CAP_ICONS: Record<string, JSX.Element> = {
  donnees: <><circle cx="11" cy="11" r="7" /><path d="m16.2 16.2 4.3 4.3" /></>,
  web: <><circle cx="12" cy="12" r="8.5" /><path d="M3.5 12h17" /><path d="M12 3.5a13 13 0 0 1 0 17 13 13 0 0 1 0-17Z" /></>,
  expliquer: <><path d="M9.5 17.5h5" /><path d="M10.5 20.5h3" /><path d="M12 3a6 6 0 0 1 3.4 10.9c-.5.4-.9 1-.9 1.6H9.5c0-.6-.4-1.2-.9-1.6A6 6 0 0 1 12 3Z" /></>,
  preparer: <><path d="M6 2.5h8.5L19 7v14.5H6z" /><path d="M14 2.5V7h5" /><path d="M9 12h7M9 16h5" /></>,
}
const CAP_ICON_FALLBACK = <path d="M12 2.5 14 9l6.5 2L14 13l-2 6.5L10 13l-6.5-2L10 9l2-6.5Z" strokeLinejoin="round" />

export function AccueilCopilote({ value, onChange, onSubmit, occupe, reponse,
  missions, onReprendre }: {
  value: string
  onChange: (v: string) => void
  onSubmit: () => void
  occupe?: boolean            // dispatch en cours (le routeur réfléchit)
  reponse?: ReactNode         // réponse inline QUESTION/OUTIL/refus (2a → 2e)
  missions?: CopiloteMission[]           // §2b — historique (« Vos dernières questions »)
  onReprendre?: (m: CopiloteMission) => void
}) {
  const ref = useRef<HTMLTextAreaElement | null>(null)
  useEffect(() => { ref.current?.focus() }, [])
  // M133 — le HERO (titre/sous-titre/placeholder/aide) + les 4 capacités en TEXTE, servis par le
  // serveur (jamais en dur). Échec du fetch → replis neutres (l'écran reste utilisable, le champ suffit).
  const [meta, setMeta] = useState<AccueilCopiloteMeta | null>(null)
  useEffect(() => { getAccueilCopilote().then(setMeta).catch(() => {}) }, [])
  // M85 Phase 3 — le brief du matin (déterministe). Affiché en tête SEULEMENT s'il est frais (non vide) :
  // on ne remplit jamais l'accueil avec un brief creux (l'honnêteté du « rien de neuf »). Vert/neutre,
  // jamais mauve (ce n'est pas de l'IA — ce sont des faits datés).
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

  return (
    <div data-accueil className="mx-auto max-w-[620px] px-2 pt-6">
      {/* HERO — titre + sous-titre SERVIS (M133). Kicker mauve. La promesse suit le produit (les 4
          missions) — l'ancienne promesse d'instruction est morte en M118. */}
      <div className="mb-6 text-center">
        <div className="mb-3 font-mono text-[11px] tracking-[.16em] text-cp-ia">COPILOTE</div>
        <h1 data-accueil-titre className="mb-2.5 font-display text-[30px] font-medium leading-[1.25] tracking-[-.5px] text-cp-txt">
          {meta?.titre ?? 'Posez votre question.'}
        </h1>
        <p data-accueil-tagline className="text-[13px] text-cp-muted">
          {meta?.sous_titre ?? 'Réponse courte, sourcée, datée — La Réunion uniquement.'}
        </p>
      </div>

      {/* M87 P6 — le SCRIM + le PANNEAU latéral (fixed : hors flux ; leur place ici n'affecte pas
          l'ordre visuel). Clic-dehors et Échap ferment ; le focus est piégé. */}
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

      {/* M133 — LE CHAMP EN PREMIER (l'action principale), sous le hero. Placeholder = un exemple
          d'une VRAIE mission (donnée), servi ; jouer le placeholder tel quel aboutit à la mission 1,
          jamais à un refus. FOCUS sans contour vert (M87 P2). */}
      {/* RETOURS-3 R12 — mauve ASSUMÉ au focus du champ (bordure mauve + halo doux), comme la maquette v3. */}
      <div data-accueil-barre className="mb-3 flex items-center gap-3 rounded-xl border border-cp-ia-border bg-cp-card/60 py-2 pl-[18px] pr-2 transition-[border-color,box-shadow] duration-quick focus-within:border-cp-ia focus-within:shadow-[0_0_0_3px_rgba(180,151,240,0.16)]">
        <textarea ref={ref} data-brief rows={1} value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); if (value.trim()) onSubmit() } }}
          placeholder={meta?.placeholder ?? 'Écrivez ce dont vous avez besoin…'}
          className="max-h-24 min-h-[24px] flex-1 resize-none bg-transparent py-1.5 text-[14px] leading-normal text-cp-txt outline-none focus-visible:outline-none placeholder:text-cp-faint" />
        <button data-accueil-envoyer onClick={() => value.trim() && onSubmit()} disabled={!value.trim() || occupe}
          className="shrink-0 rounded-lg bg-cp-ia px-5 py-2.5 text-[13px] font-medium text-cp-ia-on transition-[filter] duration-quick hover:brightness-110 disabled:opacity-40">
          {occupe ? '…' : 'Envoyer'}
        </button>
      </div>
      <p data-accueil-aide className="mb-9 text-center text-[12px] text-cp-faint">
        {meta?.aide ?? 'Le Copilote comprend ce que vous demandez — rien à choisir.'}
      </p>

      {/* M133 — CE QU'IL SAIT FAIRE : les 4 capacités en TEXTE (libellé + exemple réel entre
          guillemets). NON cliquables — pas de bordure, pas de fond, pas d'état, pas de curseur.
          Des exemples qui enseignent, pas un menu. */}
      {!reponse && meta && meta.capacites.length > 0 && (
        // RETOURS-7 Z2 — même marge (mb-8) que « Reprendre » ci-dessous.
        <div data-accueil-capacites className="mb-8">
          <p className="mb-2.5 font-mono text-[10px] tracking-[.12em] text-cp-faint">CE QU'IL SAIT FAIRE</p>
          {/* RETOURS-3 R12 — chaque capacité porte une TUILE d'icône contrastée (mauve 22 %/48 %) ; le
              bloc reste NON cliquable (curseur défaut, aucun état).
              RETOURS-7 Z2 — grille 2×2 à GOUTTIÈRES RÉGULIÈRES (gap-4 = même espace horizontal et
              vertical) ; chaque exemple sur UNE ligne (truncate) → toutes les tuiles à la même hauteur,
              alignées sur la première ligne de texte (items-start). */}
          <div className="grid grid-cols-1 gap-4 min-[520px]:grid-cols-2">
            {meta.capacites.map((c) => (
              <div key={c.cle} data-accueil-capacite data-cap-cle={c.cle} className="flex cursor-default items-start gap-3">
                <span className="flex h-[38px] w-[38px] shrink-0 items-center justify-center rounded-[10px] border border-cp-ia/[0.48] bg-cp-ia/[0.22] text-cp-ia">
                  <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2.1} strokeLinecap="round" strokeLinejoin="round">{CAP_ICONS[c.cle] ?? CAP_ICON_FALLBACK}</svg>
                </span>
                <div className="min-w-0">
                  <div className="mb-[3px] text-[14px] leading-[1.45] font-medium text-cp-txt">{c.libelle}</div>
                  <div className="truncate text-[12px] leading-[1.45] text-cp-muted" title={c.exemple}>« {c.exemple} »</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {reponse && <div data-accueil-reponse className="mb-8">{reponse}</div>}

      {/* RECETTE-2 LOT D1 — la carte « Votre brief du matin » est RETIRÉE de la section IA. Retrait de
          SURFACE : event_log, crons et envois Brevo sont INTACTS. Devient code mort (non supprimé,
          décision de démontage = geste de Vic) : le hook getBrief + l'endpoint /events/brief + le
          tiroir latéral du brief (briefOpen/panelRef, plus jamais ouvert). Voir compte-rendu. */}

      {/* REPRENDRE — conversations passées, dédoublonnées, datées en relatif, 4 max puis « voir tout ». */}
      {!reponse && questions.length > 0 && (
        <div data-accueil-historique className="mb-8">
          <p className="mb-2.5 font-mono text-[10px] tracking-[.12em] text-cp-faint">REPRENDRE</p>
          <div className="flex flex-col">
            {/* RETOURS-3 R12 / RETOURS-4 S8 — survol PLEIN mauve PROFOND (dégradé, texte inversé sombre) via
                .hover-fill-ia, comme partout ; la date « il y a N j » ne se tronque jamais (whitespace-nowrap). */}
            {questionsVisibles.map((m) => (
              <button key={m.id} data-mission-reprendre onClick={() => onReprendre?.(m)}
                className="hover-fill-ia flex items-center gap-3 rounded-[10px] border-b border-cp-line/60 px-3 py-2.5 text-left last:border-b-0 hover:border-transparent">
                <span className="min-w-0 flex-1 truncate text-[14px] text-cp-txt">{m.titre}</span>
                {m.run_id && <span className="shrink-0 rounded border border-cp-ia/30 px-1.5 py-px text-[9px] uppercase tracking-wide text-cp-ia">recherche</span>}
                <span className="shrink-0 whitespace-nowrap font-mono text-[11px] text-cp-faint">{ilYA(m.updated_at)}</span>
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
