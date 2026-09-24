// Copilote v2 — écran de premier niveau, CHAT-ONLY (COPILOTE-2 lot 4 : le moteur de missions lourdes
// v1 et son rendu de run — entonnoir/fil d'instruction/résultats/journal SSE — sont RETIRÉS). Le
// Copilote sert TROIS chemins inline (FICHE / OUTIL / WEB, ReponseInline) : il résume, ouvre un outil
// pré-rempli, ou cite le web ; il ne produit plus de shortlist ni d'avis lui-même. Tokens cp-*/mauve IA.
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { copiloteV2Ask, copiloteV2Missions, copiloteV2Mission, ApiError, is429,
  type CopiloteMission, type CopiloteV2Reponse } from '../../lib/api'
import { ReponseInline } from './ReponseInline'
import { AccueilCopilote } from './AccueilCopilote'
import { ParcoursProjet } from '../projets/ParcoursProjet'
import { TraitementEnCours } from './ui'
import { useApp } from '../../store/useApp'

// halo discret de la maquette (radial mauve en haut à droite et en bas à gauche)
const FOND = {
  backgroundImage:
    'radial-gradient(ellipse 900px 460px at 78% -10%, rgba(180,151,240,.06), transparent 62%), ' +
    'radial-gradient(ellipse 700px 460px at 5% 105%, rgba(180,151,240,.05), transparent 62%)',
}

export function CopiloteView() {
  const [brief, setBrief] = useState('')
  // M102-B2 — LE FIL : ce qui a été demandé, compris, répondu — lisible tour par tour. Quand le
  // Copilote pose une question (clarification), le champ de réponse apparaît DANS le fil.
  const [fil, setFil] = useState<{ q: string; r: CopiloteV2Reponse; echec?: boolean }[]>([])
  const [reponseFil, setReponseFil] = useState('')
  // M107 P3 — expiration du fil par INACTIVITÉ (TTL servi par /ask, jamais recopié).
  const [ttlMin, setTtlMin] = useState(10)
  const [filExpire, setFilExpire] = useState(false)
  const derniereActivite = useRef<number>(Date.now())
  const [dispatching, setDispatching] = useState(false)
  const [missions, setMissions] = useState<CopiloteMission[]>([])   // §2b — historique
  const [retentionJours, setRetentionJours] = useState(7)
  const [convId, setConvId] = useState<number | null>(null)
  const [projetForm, setProjetForm] = useState<{ prefill: Record<string, unknown> } | null>(null)  // M113 P3
  const briefRef = useRef<HTMLTextAreaElement | null>(null)

  const rafraichirMissions = () => copiloteV2Missions()
    .then((d) => { setMissions(d.missions); setRetentionJours(d.retention_jours) }).catch(() => {})
  useEffect(() => { void rafraichirMissions() }, [])

  // M78 · 2a — dispatch : le routeur décide, la réponse rejoint le fil (inline). COPILOTE-2 lot 4 —
  // plus de récap-péage ni de run : RECHERCHE/VERIFICATION reviennent en réponse OUTIL (une passerelle).
  const interroger = async (msg: string) => {
    const m = msg.trim()
    if (!m || dispatching) return
    setDispatching(true)
    setBrief('')
    if (filExpire) { setFil([]); setFilExpire(false) }
    derniereActivite.current = Date.now()
    try {
      const r = await copiloteV2Ask(m, { conversation_id: convId })
      if (r.conversation_id != null) setConvId(r.conversation_id)
      if (r.contexte_ttl_minutes) setTtlMin(r.contexte_ttl_minutes)
      void rafraichirMissions()
      // M113 P3 — le parcours projet guidé : le serveur ne crée JAMAIS directement ; il renvoie le
      // préremplissage compris et le front ouvre le formulaire (qui protège par construction).
      if (r.projet_form) { setProjetForm(r.projet_form); return }
      setFil((f) => [...f, { q: m, r }])
      setReponseFil('')
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
  const soumettre = () => void interroger(brief)

  // M107 P3 — minuteur d'inactivité : quand le fil dort plus de ttlMin, l'expiration est ANNONCÉE
  // (bandeau « nouvelle conversation ») et le contexte serveur abandonné (convId null).
  useEffect(() => {
    if (fil.length === 0 || filExpire) return
    const t = setInterval(() => {
      if (Date.now() - derniereActivite.current > ttlMin * 60_000) {
        setFilExpire(true); setConvId(null)
      }
    }, 15_000)
    return () => clearInterval(t)
  }, [fil.length, filExpire, ttlMin])

  const nouveauFil = () => {
    setFil([]); setConvId(null); setFilExpire(false); setReponseFil(''); setBrief('')
    setProjetForm(null); briefRef.current?.focus()
  }
  const ttlNotice = filExpire ? (
    <p data-fil-expire className="rounded-xl border border-cp-line2 bg-cp-card2 px-4 py-2.5 text-[12px] text-cp-muted">
      ⏱ <b className="text-cp-txt">Nouvelle conversation</b> — le fil précédent a expiré ({ttlMin} min d'inactivité). Votre prochain message repart de zéro.
    </p>
  ) : null
  const boutonNouveauFil = (
    <button data-fil-nouveau onClick={nouveauFil}
      className="self-start rounded-lg border border-cp-line bg-transparent px-4 py-2 font-display text-[12px] font-semibold text-cp-muted transition-colors duration-quick hover:border-cp-line2 hover:text-cp-txt">
      ↻ Nouveau fil
    </button>
  )
  const avecChrome = (node: ReactNode) => (
    <div className="flex flex-col gap-3 text-left">{ttlNotice}{node}{boutonNouveauFil}</div>
  )

  // §2b — rouvrir une mission passée : restaure le FIL COMPLET (inline). COPILOTE-2 lot 4 — plus de
  // reprise de run (run_id) : une conversation est une suite de tours inline.
  const rouvrir = async (m: CopiloteMission) => {
    try {
      const conv = await copiloteV2Mission(m.id)
      setConvId(conv.id)
      const tours: { q: string; r: CopiloteV2Reponse }[] = []
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

  const { entretienDirect, clearEntretienDirect } = useApp()
  const setView = useApp((s) => s.setView)
  const setOpenProjet = useApp((s) => s.setOpenProjet)
  // GB-031/GB-039 — Échap ferme le Copilote (retour à la carte), avec le patron double-échap : un
  // champ non vide rend d'abord le focus (protège la saisie), sinon Échap ferme.
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return
      const brief = document.querySelector('[aria-label="Brief du matin"]')
      if (brief && brief.getAttribute('aria-hidden') !== 'true') return
      const el = document.activeElement as HTMLInputElement | HTMLTextAreaElement | null
      if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') && (el.value ?? '').trim()) {
        el.blur(); return
      }
      setView('cartes')
    }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [setView])
  useEffect(() => {
    if (entretienDirect === null) return
    setBrief((b) => b.trim() ? b : (entretienDirect || 'je veux monter une opération immobilière'))
    briefRef.current?.focus()
    clearEntretienDirect()
  }, [entretienDirect, clearEntretienDirect])

  return (
    <div data-copilote className="min-h-0 flex-1 overflow-y-auto bg-cp-bg font-sans text-[13px] text-cp-txt" style={FOND}>
      <div className="mx-auto max-w-[1000px] px-6 pb-12 pt-9">
        <AccueilCopilote value={brief} onChange={setBrief} onSubmit={soumettre}
          occupe={dispatching}
          onExemple={(t) => { setBrief(t); void interroger(t) }}
          missions={missions} retentionJours={retentionJours} onReprendre={rouvrir}
          reponse={projetForm
            ? avecChrome(<ParcoursProjet prefill={projetForm.prefill} accent="ia"
                onVoir={(p) => { setProjetForm(null); setOpenProjet(p) }}
                onFermer={() => setProjetForm(null)} />)
            : (fil.length > 0 || dispatching) ? (
              <div data-fil className="flex flex-col gap-3 text-left">
                {ttlNotice}
                <div className={filExpire ? 'flex flex-col gap-3 opacity-50' : 'flex flex-col gap-3'}>
                  {fil.map((t, i) => (
                    <div key={i} className="flex flex-col gap-1.5">
                      <p data-fil-question className="self-end rounded-xl bg-cp-violet/10 px-3.5 py-1.5 text-[12.5px] text-cp-txt">
                        {t.q}
                      </p>
                      <ReponseInline v2={t.r} />
                      {t.echec && i === fil.length - 1 && !dispatching && (
                        <button data-fil-reessayer onClick={() => void interroger(t.q)}
                          className="self-start rounded-lg border border-cp-amber/40 bg-cp-amber/10 px-3.5 py-1.5 font-display text-[12px] font-semibold text-cp-amber hover:bg-cp-amber/15">
                          Réessayer
                        </button>
                      )}
                    </div>
                  ))}
                </div>
                {dispatching && <TraitementEnCours />}
                {!dispatching && fil.length > 0 && (
                  <div data-fil-reponse className="flex items-center gap-2">
                    <input autoFocus={fil[fil.length - 1].r.clarification === true}
                      value={reponseFil} onChange={(e) => setReponseFil(e.target.value)}
                      onKeyDown={(e) => { if (e.key === 'Enter' && reponseFil.trim()) { void interroger(reponseFil); setReponseFil('') } }}
                      placeholder={fil[fil.length - 1].r.clarification ? 'Votre réponse…' : 'Répondre, corriger ou préciser…'}
                      className="min-w-0 flex-1 rounded-lg border border-violet/30 bg-cp-card px-3.5 py-2 text-[13px] text-cp-txt placeholder:text-cp-faint focus:border-violet focus:outline-none" />
                    <button data-fil-envoyer disabled={!reponseFil.trim()}
                      onClick={() => { void interroger(reponseFil); setReponseFil('') }}
                      className="rounded-lg border border-violet/40 bg-violet/10 px-3.5 py-2 font-display text-[12px] font-semibold text-violet hover:bg-violet/15">
                      Répondre
                    </button>
                  </div>
                )}
                {!dispatching && fil.length > 0 && boutonNouveauFil}
              </div>
            ) : null} />
      </div>
    </div>
  )
}
