// M78 · 2a — PAGE D'ACCUEIL du Copilote v2. Recopiée de docs/DA-COPILOTE-ACCUEIL.html (fait foi) :
// promesse + tagline ([N] = comptage DYNAMIQUE du bandeau, jamais en dur), une barre unique, trois
// cartes Chercher/Vérifier/Veiller à deux exemples cliquables (le clic REMPLIT la barre, ne lance
// rien), pied de garanties. Retirés (mandat) : onglets « BIENTÔT », paragraphe défensif, pitch « il
// ne calcule rien ». Tokens cp-*/mint = palette de la maquette (--mint #4ADE80, --carte #101612).
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { fmtInt, ilYA } from '../../lib/format'
import { getBrief, type AccueilChiffres, type BriefMatin, type CopiloteMission } from '../../lib/api'

type Carte = { past: string; titre: string; desc: (parc: string) => string }

// M78-quater #3 — la carte « Veiller » est retirée (la veille n'est pas exposée sur cet écran ; le
// mécanisme reste en code, écran dédié au BACKLOG). Remplacée par « Demander » = le parcours des
// QUESTIONS DIRECTES (maquette PARCOURS B), qui fonctionne aujourd'hui (base + web, sinon refus honnête).
const CARTES: Carte[] = [
  { past: '⌕', titre: 'Chercher',
    desc: (parc) => `Décrivez le terrain ou le programme. Les moteurs passent les ${parc} parcelles au crible.` },
  { past: '?', titre: 'Demander',
    desc: () => "Une question directe — PLU, propriétaire, délais, marché. Le Copilote répond avec sa source, ou le dit s'il ne sait pas." },
  { past: '⚖', titre: 'Vérifier',
    desc: () => "Une parcelle qu'on vous propose. Le Copilote instruit à charge et à décharge, et rend un avis sourcé." },
]

// M87 P2 — SIX exemples FIXES, dans cet ordre (fini la rotation aléatoire de l'ancien POOL de 19 :
// retirée, une grille figée vaut mieux qu'un tirage qui change à chaque visite). Chaque exemple porte
// son étiquette d'intention. Un clic REMPLIT la barre, ne lance rien.
const EXEMPLES: { intent: string; txt: string }[] = [
  { intent: 'Chercher', txt: 'Quelles parcelles appartiennent à la SIDR ?' },
  { intent: 'Chercher', txt: 'Combien de parcelles à Saint-Paul ?' },
  { intent: 'Veiller', txt: 'Préviens-moi de tout nouveau permis à Saint-Paul' },
  { intent: 'Vérifier', txt: 'Qui est le maire de Saint-Denis ?' },
  { intent: 'Vérifier', txt: 'Qui gère les dossiers de financement des bailleurs sociaux à la Région ?' },
  { intent: 'Agir', txt: 'Je veux écrire au propriétaire de cette parcelle' },
]

export function AccueilCopilote({ value, onChange, onSubmit, onPick, chiffres, occupe, reponse,
  missions, onReprendre }: {
  value: string
  onChange: (v: string) => void
  onSubmit: () => void
  onPick: (ex: string) => void
  chiffres: AccueilChiffres | null
  occupe?: boolean            // dispatch en cours (le routeur réfléchit)
  reponse?: ReactNode         // réponse inline QUESTION/OUTIL/refus (2a → 2e)
  missions?: CopiloteMission[]           // §2b — historique (« Vos dernières questions »)
  onReprendre?: (m: CopiloteMission) => void
}) {
  const ref = useRef<HTMLTextAreaElement | null>(null)
  useEffect(() => { ref.current?.focus() }, [])
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

  // [N] et [parc] DYNAMIQUES — masqués (pas inventés) si le bandeau ne les a pas encore.
  const nSources = chiffres?.sources != null ? String(chiffres.sources) : null
  const parc = chiffres?.parcelles != null ? fmtInt(chiffres.parcelles) : 'toutes les'

  return (
    <div data-accueil className="mx-auto max-w-[640px] px-2 pt-6">
      <div className="mb-2 text-center">
        <span className="font-mono text-[10px] tracking-[.16em] text-cp-muted">COPILOTE</span>
      </div>
      <h1 className="mb-2.5 text-center font-display text-[30px] font-semibold leading-[1.2] tracking-[-.5px] text-cp-txt">
        Dites ce que vous cherchez.<br />Le Copilote <span className="text-mint">instruit</span>.
      </h1>
      <p data-accueil-tagline className="mb-8 text-center text-[13px] text-cp-muted">
        Une parcelle instruite en une minute{nSources ? <> — <b className="text-cp-txt">{nSources}</b> sources</> : null}, chaque chiffre daté.
      </p>

      {/* M87 P1 — LE CLAIM, permanent et STATIQUE (aucune animation, aucun curseur). Classe .claim de la
          maquette DA-ACCUEIL-BRIEF-v1. Visible à tout moment sur l'accueil, plus seulement à l'état initial. */}
      <div data-claim className="mx-auto mb-8 max-w-[640px] rounded-xl border border-cp-line bg-cp-card/60 px-[22px] py-[18px] text-left">
        <p className="mb-[5px] text-[15px] font-semibold text-cp-txt">Tout le foncier de La Réunion. Au même endroit.</p>
        <p className="text-[13px] text-cp-muted">Données à jour — cadastre, PLU, permis, ventes, risques. Chaque chiffre porte sa date.</p>
      </div>

      {/* M87 P6 — LE BRIEF quitte le flux de l'accueil : une BARRE (classe .brief-btn de la maquette).
          N = brief.n (event_log, J-1) — même point de lecture que l'e-mail Brevo. N=0 → « Rien de neuf
          depuis hier », la barre ne disparaît pas. Vert/neutre, jamais mauve (faits datés, pas d'IA). */}
      {brief && (
        <button data-brief-btn onClick={() => setBriefOpen(true)}
          className="mx-auto mb-2 mt-4 flex items-center gap-3 rounded-xl border border-cp-line bg-cp-card/60 px-[18px] py-3 transition-colors duration-quick hover:border-mint/60">
          <span className="h-[7px] w-[7px] shrink-0 rounded-full bg-mint" />
          <span className="text-[13px] text-cp-txt">Votre brief du matin</span>
          <span className="font-mono text-[11.5px] text-cp-muted">
            {briefN > 0 ? `${briefN} événement${briefN > 1 ? 's' : ''} depuis hier` : 'Rien de neuf depuis hier'}
          </span>
          <span className="text-cp-muted">→</span>
        </button>
      )}

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
          Ce qui a bougé sur <b className="font-semibold text-cp-txt">vos parcelles suivies</b> et dans <b className="font-semibold text-cp-txt">vos zones de veille</b> depuis hier.
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

      {/* barre unique — M87 P2 : FOCUS sans contour vert. Le contour :focus-visible mint (index.css) est
          neutralisé sur le champ ; le focus reste PERCEPTIBLE au clavier via la barre (border renforcée +
          fond #12170F, comme la maquette). On remplace le focus, on ne le supprime pas (accessibilité). */}
      <div data-accueil-barre className="mb-3.5 flex items-center gap-3 rounded-xl border border-cp-line bg-cp-card/60 py-2 pl-[18px] pr-2 transition-colors duration-quick focus-within:border-cp-line2 focus-within:bg-[#12170F]">
        <textarea ref={ref} data-brief rows={1} value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); if (value.trim()) onSubmit() } }}
          placeholder="15 logements à Saint-Denis, budget foncier 800 k€…"
          className="max-h-24 min-h-[24px] flex-1 resize-none bg-transparent py-1.5 text-[14px] leading-normal text-cp-txt outline-none focus-visible:outline-none placeholder:text-cp-faint" />
        <button data-accueil-envoyer onClick={() => value.trim() && onSubmit()} disabled={!value.trim() || occupe}
          className="shrink-0 rounded-lg bg-mint px-5 py-2.5 text-[13px] font-medium text-mint-on transition-[filter] duration-quick hover:brightness-110 disabled:opacity-40">
          {occupe ? '…' : 'Envoyer'}
        </button>
      </div>
      <p className="mb-4 text-center text-[11px] text-cp-faint">
        Écrivez librement — le Copilote comprend s'il faut chercher, vérifier ou veiller.
      </p>

      {/* M87 P2 — SIX exemples FIXES (plus de rotation aléatoire), grille régulière 3×2 (1 colonne
           sous 820 px), chaque exemple porte son étiquette d'intention en petites capitales mono.
           Classes .examples / .ex de la maquette. Un clic REMPLIT la barre, ne lance rien. */}
      {!reponse && (
        <div data-accueil-exemples className="mx-auto mb-8 grid max-w-[820px] grid-cols-1 gap-2 min-[820px]:grid-cols-3">
          {EXEMPLES.map((e) => (
            <button key={e.txt} data-accueil-ex onClick={() => onPick(e.txt)}
              className="rounded-lg border border-cp-line bg-transparent px-3.5 py-[11px] text-left text-[12.5px] leading-[1.35] text-cp-muted transition-colors duration-quick hover:border-cp-line2 hover:text-cp-txt">
              <span className="mb-[5px] block font-mono text-[9.5px] uppercase tracking-[.12em] text-cp-faint">{e.intent}</span>
              {e.txt}
            </button>
          ))}
        </div>
      )}

      {reponse && <div data-accueil-reponse className="mb-8">{reponse}</div>}

      {/* #2 — VOS DERNIÈRES QUESTIONS : conversations passées, dédoublonnées, datées en relatif, 4 max
           puis « voir tout ». Rouvrir en restaure le fil. Masqué si l'historique est vide. */}
      {questions.length > 0 && (
        <div data-accueil-historique className="mb-8">
          <p className="mb-2 font-mono text-[10px] tracking-[.16em] text-cp-muted">VOS DERNIÈRES QUESTIONS</p>
          <div className="flex flex-col gap-1.5">
            {questionsVisibles.map((m) => (
              <button key={m.id} data-mission-reprendre onClick={() => onReprendre?.(m)}
                className="flex items-center gap-3 rounded-lg border border-cp-line bg-cp-card/50 px-3.5 py-2 text-left transition-colors duration-quick hover:border-mint/30">
                <span className="min-w-0 flex-1 truncate text-[12px] text-cp-txt">{m.titre}</span>
                {m.run_id && <span className="shrink-0 rounded border border-mint/30 px-1.5 py-px text-[9px] uppercase tracking-wide text-mint">recherche</span>}
                <span className="shrink-0 font-mono text-[10px] text-cp-faint">{ilYA(m.updated_at)}</span>
              </button>
            ))}
          </div>
          {questions.length > 4 && (
            <button data-histo-tout onClick={() => setToutHisto((v) => !v)}
              className="mt-2 text-[11px] text-cp-muted hover:text-cp-txt">
              {toutHisto ? 'Réduire' : `Voir tout (${questions.length})`}
            </button>
          )}
        </div>
      )}

      {/* trois missions — les archétypes (les exemples VARIÉS vivent en pool sous la barre, §1) */}
      <div className="mb-8 grid grid-cols-1 gap-2.5 sm:grid-cols-3">
        {CARTES.map((c) => (
          <div key={c.titre} data-mission-carte className="rounded-[9px] bg-cp-card p-4">
            <div className="mb-2 flex items-center gap-2.5">
              <div className="flex h-7 w-7 items-center justify-center rounded-[7px] bg-[#12291D] text-[14px] text-mint">{c.past}</div>
              <span className="font-display text-[13.5px] font-medium text-cp-txt">{c.titre}</span>
            </div>
            <p className="text-[11px] leading-[1.5] text-cp-muted">{c.desc(parc)}</p>
          </div>
        ))}
      </div>

      {/* pied de garanties */}
      <div className="flex flex-wrap items-center justify-center gap-x-5 gap-y-1.5 border-t border-cp-line pt-4">
        <span className="text-[10px] text-cp-faint">✓ Chaque étape journalisée</span>
        <span className="text-[10px] text-cp-faint">◆ Sourcé, estimé ou absent — jamais autre chose</span>
        <span className="text-[10px] text-cp-faint">◉ La Réunion uniquement</span>
      </div>
    </div>
  )
}
