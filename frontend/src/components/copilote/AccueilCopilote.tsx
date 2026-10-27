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
// RECETTE-OUTILS-4 (U6) — `CAP_ICONS` (icônes des 4 capacités) n'est plus utilisé : la section
// « Ce qu'il sait faire » est retirée. Seule l'étincelle générique reste (repli des exemples).
const CAP_ICON_FALLBACK = <path d="M12 2.5 14 9l6.5 2L14 13l-2 6.5L10 13l-6.5-2L10 9l2-6.5Z" strokeLinejoin="round" />

// RECETTE-OUTILS-2 (R24) — NEUF exemples en grille 3×3 (maquette « Copilote, exemples »), un par chemin
// traité : parcelle · propriétaire · PLU · procédure · pièges · argumentaire · assemblage · blocs
// fonciers · successions. Chacun porte SON icône de type. Cliquer PRÉ-REMPLIT la barre (onChange + focus).
// Un seul texte change (R24) : « Quel est le potentiel d'un assemblage… » → « Quel potentiel pour… ».
const EXEMPLES_R12: { t: string; ic: string }[] = [
  { t: 'Dis-moi tout sur la parcelle 97415000CV1186', ic: 'parcelle' },
  { t: 'Combien de parcelles possède CBO Territoria ?', ic: 'proprietaire' },
  { t: 'Quelles sont les règles du PLU en zone Ua à Saint-Paul ?', ic: 'plu' },
  { t: 'Y a-t-il une procédure PLU en cours à Saint-Pierre ?', ic: 'procedure' },
  { t: 'Quels sont les pièges de la parcelle 97415000CV1186 ?', ic: 'pieges' },
  { t: 'Prépare un argumentaire pour aborder ce propriétaire', ic: 'argumentaire' },
  { t: 'Quel potentiel pour un assemblage autour de 97411000AD0213 ?', ic: 'assemblage' },
  { t: "Montre les blocs fonciers d'un même propriétaire au Tampon", ic: 'blocs' },
  { t: 'Quelles successions à venir à Saint-Paul ?', ic: 'successions' },
  // RECETTE-PROD-1 (D7) — 10ᵉ exemple (2 rangées de 5).
  { t: "Calcule la taxe d'aménagement de 97415000BY0083", ic: 'taxe' },
]

// R24 — une icône par TYPE (24×24, stroke) : loupe · bâtiment · livre · horloge · triangle · bulle ·
// blocs (4 carrés) · couches · sablier. Rendue 18 px dans un carré violet sombre de 32 px.
const EX_ICONS: Record<string, ReactNode> = {
  parcelle: <><circle cx="11" cy="11" r="7" /><path d="m16.5 16.5 4 4" /></>,
  proprietaire: <><path d="M4 21V8l8-4 8 4v13" /><path d="M9 21v-6h6v6" /></>,
  plu: <><path d="M5 4a1 1 0 0 1 1-1h13v15H6a1 1 0 0 0-1 1V4Z" /><path d="M6 15h13" /></>,
  procedure: <><circle cx="12" cy="12" r="8.5" /><path d="M12 7.5v5l3.5 2" /></>,
  pieges: <><path d="M12 3.5 2.5 20h19L12 3.5Z" /><path d="M12 10v4" /><path d="M12 17h.01" /></>,
  argumentaire: <><path d="M4 5h16v11H9l-5 4V5Z" /></>,
  assemblage: <><rect x="3.5" y="3.5" width="7" height="7" rx="1" /><rect x="13.5" y="3.5" width="7" height="7" rx="1" /><rect x="3.5" y="13.5" width="7" height="7" rx="1" /><rect x="13.5" y="13.5" width="7" height="7" rx="1" /></>,
  blocs: <><path d="m12 3 9 5-9 5-9-5 9-5Z" /><path d="m3 13 9 5 9-5" /></>,
  successions: <><path d="M6.5 3h11M6.5 21h11" /><path d="M7 3c0 4.5 10 5.5 10 9s-10 4.5-10 9" /><path d="M17 3c0 4.5-10 5.5-10 9s10 4.5 10 9" /></>,
  taxe: <><circle cx="12" cy="12" r="8.5" /><path d="M15 9.6a3.3 3.3 0 1 0 0 4.8" /><path d="M8 11h5M8 13h4" /></>,
}

// R24 — « les IDU en mono » : on isole les IDU (8 chiffres · 2 lettres · 4 chiffres) dans le texte et
// on les rend en police mono, le reste en texte courant.
function avecIduMono(t: string): ReactNode {
  return t.split(/(\d{8}[A-Z]{2}\d{4})/).map((p, i) =>
    /^\d{8}[A-Z]{2}\d{4}$/.test(p) ? <span key={i} className="font-mono">{p}</span> : <span key={i}>{p}</span>)
}

// RETOURS-11 A1 — `onExemple` (lancer un exemple) n'est plus utilisé : les exemples PRÉ-REMPLISSENT
// la barre (via onChange). Le prop reste toléré dans le type pour ne pas casser l'appelant.
export function AccueilCopilote({ value, onChange, onSubmit, occupe, reponse,
  missions, retentionJours = 7, onReprendre }: {
  value: string
  onChange: (v: string) => void
  onSubmit: () => void
  occupe?: boolean            // dispatch en cours (le routeur réfléchit)
  reponse?: ReactNode         // réponse inline QUESTION/OUTIL/refus (2a → 2e)
  missions?: CopiloteMission[]           // §2b — historique (« Vos dernières questions »)
  retentionJours?: number                // RETOURS-8 (R11) — rétention affichée sous les fils passés
  onReprendre?: (m: CopiloteMission) => void
  onExemple?: (t: string) => void        // RETOURS-9 (Q10.4) — clic sur un exemple → lance la question
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
          className="shrink-0 rounded-lg bg-cp-ia px-5 py-2.5 text-[13px] font-medium text-cp-ia-on transition-[filter] duration-quick hover:brightness-110">
          {occupe ? '…' : 'Envoyer'}
        </button>
      </div>
      {/* RETOURS-11 A1 (03/09) — les exemples ne sont plus ici : ils forment le NIVEAU 3, sous les
          capacités (regroupés), et PRÉ-REMPLISSENT la barre au clic (voir plus bas). */}

      {/* RECETTE-OUTILS-4 (U6) — la section « Ce qu'il sait faire » (titre + 4 capacités en texte) est
          RETIRÉE : elle doublait ce que les exemples montrent déjà. Les EXEMPLES remontent à sa place,
          juste sous la barre d'envoi. */}

      {/* RETOURS-11 A1 (03/09) — EXEMPLES regroupés (les 3 raccourcis + les 4 exemples des capacités,
          dédoublonnés). Cliquer PRÉ-REMPLIT la barre (ne lance plus) : l'utilisateur ajuste puis
          envoie. Survol plein mauve via .hover-fill-ia. */}
      {!reponse && (
        <div data-accueil-exemples className="mb-8">
          <p className="mb-2.5 font-mono text-[10px] tracking-[.12em] text-cp-faint">EXEMPLES</p>
          {/* RECETTE-PROD-1 (D7) — DEUX rangées de 5 cartes (10 exemples) : 5 colonnes, hauteurs égales
              (auto-rows-fr + h-full), icône À GAUCHE et texte À DROITE sur la même ligne (flex-row),
              AUCUN texte tronqué (plus de line-clamp). IDU en mono. Cliquer PRÉ-REMPLIT la barre. */}
          <div className="grid grid-cols-5 gap-3 auto-rows-fr">
            {EXEMPLES_R12.map((ex) => (
              <button key={ex.t} data-accueil-exemple data-ex-type={ex.ic} onClick={() => { onChange(ex.t); ref.current?.focus() }}
                className="hover-fill-ia flex h-full min-h-[84px] flex-row items-start gap-2.5 rounded-xl border border-cp-line bg-cp-card p-2.5 text-left transition-colors duration-quick hover:border-cp-ia/40">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-cp-ia/15 text-cp-ia">
                  <svg viewBox="0 0 24 24" className="h-[18px] w-[18px]" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">{EX_ICONS[ex.ic] ?? CAP_ICON_FALLBACK}</svg>
                </span>
                <span className="min-w-0 flex-1 self-center text-[12px] leading-tight text-cp-txt">{avecIduMono(ex.t)}</span>
              </button>
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
          {/* RETOURS-10 (T5) — « voir tout · N » remonte dans l'EN-TÊTE de section (à droite), comme la
              maquette ; il n'y a plus de bouton séparé sous la liste. Toujours quatre fils au repos. */}
          <div className="mb-2.5 flex items-baseline justify-between font-mono text-[10px] tracking-[.12em] text-cp-faint">
            <span>MÉMOIRE</span>
            {questions.length > 4 && (
              <button data-histo-tout onClick={() => setToutHisto((v) => !v)}
                className="tracking-[.06em] text-cp-muted transition-colors duration-quick hover:text-cp-txt">
                {toutHisto ? 'réduire' : `voir tout · ${questions.length}`}
              </button>
            )}
          </div>
          <div className="flex flex-col gap-1">
            {/* RETOURS-11 A3 (03/09) — plus de liseré blanc sous chaque boîte ; TRAIT LATÉRAL GAUCHE MAUVE
                (comme le trait vert des entrées du menu Outils) ; survol PLEIN mauve via .hover-fill-ia. */}
            {questionsVisibles.map((m) => (
              <button key={m.id} data-mission-reprendre onClick={() => onReprendre?.(m)}
                className="hover-fill-ia flex items-center gap-3 rounded-r-[10px] border-l-2 border-cp-ia px-3 py-2.5 text-left">
                <span className="min-w-0 flex-1 truncate text-[14px] text-cp-txt">{m.titre}</span>
                {m.run_id && <span className="shrink-0 rounded border border-cp-ia/30 px-1.5 py-px text-[9px] uppercase tracking-wide text-cp-ia">recherche</span>}
                <span className="shrink-0 whitespace-nowrap font-mono text-[11px] text-cp-faint">{ilYA(m.updated_at)}</span>
              </button>
            ))}
          </div>
          {/* RETOURS-8 (R11.3) — bandeau discret : la rétention est dite, jamais cachée. */}
          <p data-accueil-retention className="mt-3 text-[11px] text-cp-faint">
            Vos conversations sont conservées {retentionJours} jour{retentionJours > 1 ? 's' : ''}.
          </p>
        </div>
      )}
    </div>
  )
}
