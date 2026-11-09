// Copilote v2 — COPILOTE-4 : le Copilote devient une CONVERSATION (maquette « Copilote en
// conversation »). DEUX colonnes : à gauche la liste des conversations (ConversationsSidebar), au
// centre le FIL. SEULE LA FORME CHANGE — le moteur de réponse (answering.py) et les verrous
// anti-invention de COPILOTE-3 sont intacts. Chaque réponse garde EXACTEMENT son contenu (ReponseInline),
// ses sources deviennent des étiquettes à millésime, et son « geste suivant » reste les boutons que la
// réponse PORTE déjà (ouvrir la fiche / voir la carte / lancer l'outil — jamais inventés).
//
// Deux écrans dans la colonne centrale : ACCUEIL (vide) — « Bonjour. Sur quoi on travaille ? » + six
// suggestions ; et le FIL en cours — en-tête (titre + contexte parcelle quand elle est le sujet),
// messages (client à droite, Copilote à gauche), champ en bas. Tokens cp-*/mauve IA.
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { copiloteV2Ask, copiloteV2Missions, copiloteV2Mission, copiloteV2MissionSupprimer,
  ApiError, is429, type CopiloteMission, type CopiloteV2Reponse } from '../../lib/api'
import { ReponseInline } from './ReponseInline'
import { ConversationsSidebar } from './ConversationsSidebar'
import { ParcoursProjet } from '../projets/ParcoursProjet'
import { TraitementEnCours } from './ui'
import { useApp } from '../../store/useApp'

// halo discret de la maquette (radial mauve en haut à droite et en bas à gauche)
const FOND = {
  backgroundImage:
    'radial-gradient(ellipse 900px 460px at 78% -10%, rgba(180,151,240,.06), transparent 62%), ' +
    'radial-gradient(ellipse 700px 460px at 5% 105%, rgba(180,151,240,.05), transparent 62%)',
}

// Les SIX suggestions de l'accueil (maquette) — un sous-ensemble des exemples actuels, un par chemin :
// parcelle · propriétaire · PLU · procédure · pièges · taxe. Cliquer DÉMARRE la conversation (la
// première question fait disparaître la grille).
const SUGGESTIONS: { t: string; ic: ReactNode }[] = [
  { t: 'Dis-moi tout sur la parcelle 97415000CV1186', ic: <><circle cx="11" cy="11" r="7" /><path d="m16.5 16.5 4 4" /></> },
  { t: 'Combien de parcelles possède CBO Territoria ?', ic: <><path d="M4 21V8l8-4 8 4v13" /><path d="M9 21v-6h6v6" /></> },
  { t: 'Les règles du PLU en zone Ua à Saint-Paul', ic: <><path d="M5 4a1 1 0 0 1 1-1h13v15H6a1 1 0 0 0-1 1V4Z" /><path d="M6 15h13" /></> },
  { t: 'Une procédure PLU en cours à Saint-Pierre ?', ic: <><circle cx="12" cy="12" r="8.5" /><path d="M12 7.5v5l3.5 2" /></> },
  { t: 'Les pièges de la parcelle 97415000CV1186', ic: <><path d="M12 3.5 2.5 20h19L12 3.5Z" /><path d="M12 10v4" /><path d="M12 17h.01" /></> },
  { t: "Calcule la taxe d'aménagement de 97415000BY0083", ic: <><circle cx="12" cy="12" r="8.5" /><path d="M15 9.6a3.3 3.3 0 1 0 0 4.8" /><path d="M8 11h5M8 13h4" /></> },
]

const IDU_RE = /\d{8}[A-Z]{2}\d{4}/

// « les IDU en mono » : on isole les IDU dans un texte et on les rend en police mono.
function avecIduMono(t: string): ReactNode {
  return t.split(/(\d{8}[A-Z]{2}\d{4})/).map((p, i) =>
    IDU_RE.test(p) && p.length === 14 ? <span key={i} className="font-mono">{p}</span> : <span key={i}>{p}</span>)
}

type Tour = { q: string; r: CopiloteV2Reponse; echec?: boolean }
type Sujet = { idu: string; commune: string | null; zone: string | null; surface: string | null }

export function CopiloteView() {
  const [saisie, setSaisie] = useState('')          // UN seul champ : accueil ET fil
  const [fil, setFil] = useState<Tour[]>([])
  const [dispatching, setDispatching] = useState(false)
  const [missions, setMissions] = useState<CopiloteMission[]>([])
  const [retentionJours, setRetentionJours] = useState(30)
  const [convId, setConvId] = useState<number | null>(null)
  const [projetForm, setProjetForm] = useState<{ prefill: Record<string, unknown> } | null>(null)
  const [menuOpen, setMenuOpen] = useState(false)   // mobile : tiroir des conversations
  const champRef = useRef<HTMLTextAreaElement | null>(null)
  const basRef = useRef<HTMLDivElement | null>(null)

  const rafraichirMissions = () => copiloteV2Missions()
    .then((d) => { setMissions(d.missions); setRetentionJours(d.retention_jours) }).catch(() => {})
  useEffect(() => { void rafraichirMissions() }, [])

  // M78 · dispatch : le routeur décide, la réponse rejoint le fil. Le contexte SUIT (conversation_id
  // envoyé → le serveur recharge les derniers tours : une question de suite s'applique à la parcelle
  // du fil sans la répéter).
  const interroger = async (msg: string) => {
    const m = msg.trim()
    if (!m || dispatching) return
    setDispatching(true)
    setSaisie('')
    try {
      const r = await copiloteV2Ask(m, { conversation_id: convId })
      if (r.conversation_id != null) setConvId(r.conversation_id)
      void rafraichirMissions()
      // M113 — le parcours projet guidé : le serveur ne crée JAMAIS directement ; il renvoie le
      // préremplissage compris et le front ouvre le formulaire (qui protège par construction).
      if (r.projet_form) { setProjetForm(r.projet_form); return }
      setFil((f) => [...f, { q: m, r }])
    } catch (e) {
      // FIX-COPILOTE F3 — un 429 (plafond quotidien) porte un message CLAIR du serveur, affiché verbatim,
      // SANS bouton Réessayer (ça repart à minuit). Autre échec → tour récupérable (bouton Réessayer).
      const quota = is429(e)
      const echec = (quota
        ? { text: (e as ApiError).detail ?? 'Limite quotidienne du Copilote atteinte — elle repart à minuit.', intent: null, erreur: true }
        : { text: 'Je n’ai pas pu traiter votre demande — le service ne répond pas. Réessayez dans un instant.', intent: null, erreur: true }) as CopiloteV2Reponse
      setFil((f) => [...f, { q: m, r: echec, echec: !quota }])
    } finally { setDispatching(false) }
  }
  const soumettre = () => void interroger(saisie)

  // Le fil défile vers le bas à chaque nouveau message / pendant que le Copilote réfléchit.
  useEffect(() => { basRef.current?.scrollIntoView({ block: 'end' }) }, [fil.length, dispatching])

  const nouveauFil = () => {
    setFil([]); setConvId(null); setProjetForm(null); setSaisie('')
    champRef.current?.focus()
  }

  // §2b — rouvrir une conversation passée : restaure le FIL COMPLET (inline).
  const rouvrir = async (m: CopiloteMission) => {
    try {
      const conv = await copiloteV2Mission(m.id)
      setConvId(conv.id); setProjetForm(null); setSaisie('')
      const tours: Tour[] = []
      let question: string | null = null
      for (const x of conv.messages) {
        if (x.role === 'client') question = x.texte
        else if (question != null) {
          tours.push({ q: question, r: { text: x.texte, intent: (x.intent as CopiloteV2Reponse['intent']) ?? null } })
          question = null
        }
      }
      setFil(tours)
    } catch { /* silencieux — l'historique ne casse pas l'écran */ }
  }

  const supprimerConv = async (m: CopiloteMission) => {
    try { await copiloteV2MissionSupprimer(m.id) } catch { /* la liste se recale au rafraîchissement */ }
    if (m.id === convId) nouveauFil()
    void rafraichirMissions()
  }

  // Le SUJET du fil : la parcelle quand elle en est l'objet. On lit ce que les réponses PORTENT déjà —
  // le résumé de fiche (idu + commune + tuiles Surface/Zone PLU) en priorité, sinon un IDU vu dans un
  // préremplissage ou dans une question. Jamais inventé ; le contexte SUIT les tours suivants.
  const sujet: Sujet | null = useMemo(() => {
    let riche: Sujet | null = null
    let iduSeul: string | null = null
    for (const t of fil) {
      const rf = t.r.resume_fiche
      if (rf?.idu) {
        const val = (lbl: string) => rf.tuiles?.find((x) => x.libelle === lbl)?.valeur ?? null
        riche = { idu: rf.idu, commune: rf.commune ?? null, zone: val('Zone PLU'), surface: val('Surface') }
      }
      const pid = t.r.prefill_idu || (t.q.match(IDU_RE)?.[0] ?? null)
      if (pid && pid.length === 14) iduSeul = pid
    }
    if (riche) return riche
    if (iduSeul) return { idu: iduSeul, commune: null, zone: null, surface: null }
    return null
  }, [fil])

  const titre = fil[0]?.q ?? ''
  const enFil = fil.length > 0 || dispatching

  const { entretienDirect, clearEntretienDirect } = useApp()
  const setView = useApp((s) => s.setView)
  const setOpenProjet = useApp((s) => s.setOpenProjet)
  // GB-031/GB-039 — Échap : ferme d'abord le tiroir mobile, sinon rend le focus d'un champ non vide,
  // sinon ferme le Copilote (retour à la carte).
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return
      if (menuOpen) { setMenuOpen(false); return }
      const el = document.activeElement as HTMLInputElement | HTMLTextAreaElement | null
      if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') && (el.value ?? '').trim()) { el.blur(); return }
      setView('cartes')
    }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [setView, menuOpen])
  // « Ouvrir dans le Copilote » depuis une surface embarquée : amorce le champ (sans écraser une saisie).
  useEffect(() => {
    if (entretienDirect === null) return
    setSaisie((b) => b.trim() ? b : (entretienDirect || 'je veux monter une opération immobilière'))
    champRef.current?.focus()
    clearEntretienDirect()
  }, [entretienDirect, clearEntretienDirect])

  const onChamp = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Entrée envoie · Maj+Entrée saute une ligne (règle transversale du mandat).
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); if (saisie.trim()) soumettre() }
  }

  const contexteParts = sujet ? [sujet.idu, sujet.commune, sujet.zone, sujet.surface].filter(Boolean) as string[] : []

  // RETOURS-18 (pt 15) — plus de TRAIT GRIS au-dessus de la zone d'écriture (border-t retiré), zone
  // REMONTÉE (padding haut réduit).
  const champ = (
    <div data-copilote-champ className="bg-cp-bg/80 px-4 pb-3.5 pt-1.5 md:px-6">
      <div className="mx-auto flex max-w-[840px] items-end gap-2.5 rounded-xl border border-cp-ia-border bg-cp-card/60 py-2 pl-[16px] pr-2 transition-[border-color,box-shadow] duration-quick focus-within:border-cp-ia focus-within:shadow-[0_0_0_3px_rgba(180,151,240,0.16)]">
        <textarea ref={champRef} data-copilote-saisie rows={1} value={saisie}
          onChange={(e) => setSaisie(e.target.value)} onKeyDown={onChamp}
          aria-label="Votre message au Copilote"
          placeholder={enFil ? 'Continuez la conversation…' : 'Écrivez comme à un collègue…'}
          className="max-h-32 min-h-[24px] flex-1 resize-none bg-transparent py-1.5 text-[14px] leading-normal text-cp-txt outline-none placeholder:text-cp-faint" />
        <button data-copilote-envoyer onClick={soumettre} disabled={!saisie.trim() || dispatching}
          className="shrink-0 rounded-lg bg-cp-ia px-5 py-2.5 text-[13px] font-medium text-cp-ia-on transition-[filter] duration-quick hover:brightness-110 disabled:opacity-50">
          {dispatching ? '…' : 'Envoyer'}
        </button>
      </div>
      {/* RETOURS-18 (pt 15) — « Entrée pour envoyer… » RETIRÉ ; seule la note de prudence reste, dans le fil. */}
      {enFil && (
        <p className="mx-auto mt-2 max-w-[840px] text-[11px] text-cp-faint">
          Le Copilote ne dit que ce que les données portent. Un chiffre engageant vient toujours d’un outil.
        </p>
      )}
    </div>
  )

  // ── ACCUEIL (vide) — « Bonjour. Sur quoi on travaille ? » + six suggestions. ──
  const accueil = (
    <div data-accueil className="flex min-h-full flex-col items-center justify-center px-6 py-10">
      <div className="w-full max-w-[760px] text-center">
        {/* RETOURS-18 (pt 15) — le « C » (pastille), le « Bonjour. » et le sous-titre sont RETIRÉS :
            il ne reste que le titre « Sur quoi on travaille ? », au-dessus des suggestions. */}
        <h1 data-accueil-titre className="mb-7 font-display text-[28px] font-medium leading-[1.2] tracking-[-.4px] text-cp-txt">
          Sur quoi on travaille ?
        </h1>
        <div data-accueil-suggestions className="grid grid-cols-1 gap-3 text-left sm:grid-cols-2">
          {SUGGESTIONS.map((s) => (
            <button key={s.t} data-accueil-suggestion onClick={() => void interroger(s.t)} disabled={dispatching}
              className="hover-fill-ia flex min-h-[60px] items-center gap-3 rounded-xl border border-cp-line bg-cp-card p-3 text-left transition-colors duration-quick hover:border-cp-ia/40 disabled:opacity-60">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-cp-ia/15 text-cp-ia">
                <svg viewBox="0 0 24 24" className="h-[18px] w-[18px]" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">{s.ic}</svg>
              </span>
              <span className="min-w-0 flex-1 text-[13px] leading-snug text-cp-txt">{avecIduMono(s.t)}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )

  // ── LE FIL — client à droite (bulle mauve), Copilote à gauche (carte), sources + boutons dessous. ──
  const thread = (
    <div data-fil role="log" aria-live="polite" aria-relevant="additions text"
      className="mx-auto flex w-full max-w-[840px] flex-col gap-5 px-4 py-6 md:px-6">
      {fil.map((t, i) => (
        <div key={i} className="flex flex-col gap-3">
          <p data-fil-question className="max-w-[85%] self-end whitespace-pre-wrap break-words rounded-2xl rounded-br-sm bg-cp-ia/15 px-4 py-2.5 text-[13px] leading-relaxed text-cp-txt">
            {t.q}
          </p>
          <div className="max-w-[92%] self-start">
            <ReponseInline v2={t.r} />
            {t.echec && i === fil.length - 1 && !dispatching && (
              <button data-fil-reessayer onClick={() => void interroger(t.q)}
                className="mt-2 rounded-lg border border-cp-amber/40 bg-cp-amber/10 px-3.5 py-1.5 font-display text-[12px] font-semibold text-cp-amber hover:bg-cp-amber/15">
                Réessayer
              </button>
            )}
          </div>
        </div>
      ))}
      {dispatching && <div className="max-w-[92%] self-start"><TraitementEnCours /></div>}
      <div ref={basRef} />
    </div>
  )

  // ── le parcours projet guidé prend la colonne centrale (le formulaire protège par construction). ──
  const projet = projetForm && (
    <div className="mx-auto w-full max-w-[840px] px-4 py-6 md:px-6">
      <ParcoursProjet prefill={projetForm.prefill} accent="ia"
        onVoir={(p) => { setProjetForm(null); setOpenProjet(p) }}
        onFermer={() => setProjetForm(null)} />
    </div>
  )

  return (
    <div data-copilote className="flex min-h-0 w-full flex-1 overflow-hidden bg-cp-bg font-sans text-[13px] text-cp-txt" style={FOND}>
      <ConversationsSidebar conversations={missions} activeId={convId} retentionJours={retentionJours}
        onNouvelle={nouveauFil} onOuvrir={rouvrir} onSupprimer={supprimerConv} />

      {/* Mobile : la liste des conversations devient un tiroir (menu). */}
      {menuOpen && (
        <div className="fixed inset-0 z-40 flex md:hidden">
          <div className="absolute inset-0 bg-black/55" onClick={() => setMenuOpen(false)} />
          <div className="relative z-10 bg-cp-bg">
            <ConversationsSidebar mobile conversations={missions} activeId={convId} retentionJours={retentionJours}
              onNouvelle={nouveauFil} onOuvrir={rouvrir} onSupprimer={supprimerConv}
              onFermerMenu={() => setMenuOpen(false)} />
          </div>
        </div>
      )}

      <main className="flex min-w-0 flex-1 flex-col overflow-hidden">
        {/* En-tête du fil (desktop) : titre = la première question ; à droite, le contexte parcelle
            quand elle est le sujet (IDU · commune · zone · surface — ce que les réponses portent). */}
        {enFil && (
          <header className="hidden items-start justify-between gap-4 border-b border-cp-line px-6 py-4 md:flex">
            <div className="min-w-0">
              <div className="mb-0.5 font-mono text-[10px] tracking-[.16em] text-cp-ia">COPILOTE</div>
              <h2 data-fil-titre className="truncate font-display text-[15px] font-semibold text-cp-txt">{titre}</h2>
            </div>
            {sujet && (
              <div data-fil-contexte className="shrink-0 whitespace-nowrap font-mono text-[11px] text-cp-muted">
                {contexteParts.join(' · ')}
              </div>
            )}
          </header>
        )}
        {/* Barre mobile : bouton d'ouverture du tiroir + titre/contexte compacts. */}
        <div className="flex min-w-0 items-center gap-3 border-b border-cp-line px-4 py-2.5 md:hidden">
          <button data-conv-menu onClick={() => setMenuOpen(true)} aria-label="Ouvrir les conversations"
            className="shrink-0 rounded-lg border border-cp-line px-2.5 py-1.5 text-[14px] leading-none text-cp-muted hover:text-cp-txt">☰</button>
          <div className="min-w-0 flex-1">
            {enFil ? (
              <>
                <span data-fil-titre-mobile className="block truncate font-display text-[13px] font-semibold text-cp-txt">{titre}</span>
                {sujet && <span className="block truncate font-mono text-[10.5px] text-cp-muted">{contexteParts.join(' · ')}</span>}
              </>
            ) : (
              <span className="font-mono text-[11px] tracking-[.14em] text-cp-ia">COPILOTE</span>
            )}
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto">
          {projetForm ? projet : enFil ? thread : accueil}
        </div>
        {!projetForm && champ}
      </main>
    </div>
  )
}
