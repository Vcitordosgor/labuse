// M26-B — écran Copilote (vue de premier niveau). PROJECTION de l'event log M26-A :
// aucune logique métier, aucun recalcul. Design : maquette B4 de référence
// (docs/mandats/copilote_maquette_B4_reference_M26B.html), tokens cp-*.
// Les 5 états : 1 terminé · 2 en cours (AUCUN résultat partiel — règle 5) · 3 précision
// (le run REPREND, ne redémarre pas) · 4 zéro retenue (honnête, relances non chiffrées)
// · 5 quota (aucun run créé). Un rafraîchissement en plein run retombe sur le même fil
// (run épinglé + rejeu after_seq).
import { useEffect, useRef, useState, type ReactNode } from 'react'
import type { MissionActive } from '../../lib/copilote'
import { CLIENT } from '../../lib/strings'
import { copiloteV2Ask, copiloteV2Missions, copiloteV2Mission, ApiError, is429,
  type CopiloteMission, type CopiloteV2Reponse } from '../../lib/api'
import { ReponseInline } from './ReponseInline'
import { RecapConfirmation } from './RecapConfirmation'
import { CopiloteEmbarque } from './CopiloteEmbarque'
import { AccueilCopilote } from './AccueilCopilote'
import { ParcoursProjet } from '../projets/ParcoursProjet'
import { ChipsCompris } from './ChipsCompris'
import { BlocLivrable } from './BlocLivrable'
import { Entonnoir } from './Entonnoir'
import { FilInstruction } from './FilInstruction'
import { Resultats, type EtiquettesMoteurs } from './Resultats'
import { PillStatut, SecHead, TraitementEnCours } from './ui'
import { runEpingle, useCopiloteRun } from './useCopiloteRun'
import { calibrageConnu, entonnoirEnCours, etatInterpretation, type VueCopilote } from './reduireEvenements'
import { useApp } from '../../store/useApp'

const S = CLIENT.copilote

// halo discret de la maquette (radial mint en haut à droite, violet en bas à gauche)
const FOND = {
  backgroundImage:
    'radial-gradient(ellipse 900px 460px at 78% -10%, rgba(180,151,240,.06), transparent 62%), ' +
    'radial-gradient(ellipse 700px 460px at 5% 105%, rgba(180,151,240,.05), transparent 62%)',
}

const TON_STATUT: Record<string, 'mint' | 'violet' | 'ambre' | 'rouge'> = {
  interpreting: 'violet', running: 'violet', awaiting_user: 'ambre', paused: 'ambre',
  done: 'mint', failed: 'rouge', cancelled: 'rouge',
}

/** Étiquette produite par chaque moteur, lue dans le fil (payload, jamais inventée). */
const etiquettesDe = (vue: VueCopilote): EtiquettesMoteurs => {
  const de = (m: string) => vue.etapes.find((e) => e.moteur === m)?.fait?.etiquette ?? null
  return { criblage: de('criblage'), faisabilite: de('faisabilite'),
           marche_dvf: de('marche_dvf'), risques: de('risques') }
}

function Journal({ evenements, fermer }: {
  evenements: ReturnType<typeof useCopiloteRun>['evenements']; fermer: () => void
}) {
  return (
    <div data-journal className="mt-4 rounded-2xl border border-cp-line bg-cp-card px-5 py-4">
      <div className="mb-3 flex items-baseline gap-3">
        <h3 className="font-display text-[13.5px] font-semibold text-cp-txt">{S.journal.titre}</h3>
        <p className="text-[11px] text-cp-faint">{S.journal.sousTitre}</p>
        <button onClick={fermer} className="ml-auto text-[11px] text-cp-muted hover:text-cp-txt">
          {S.journal.fermer} ✕
        </button>
      </div>
      <div className="max-h-[420px] overflow-y-auto font-mono text-[10.5px] leading-relaxed text-cp-muted">
        {evenements.map((e) => (
          <div key={e.seq} className="border-b border-cp-line py-1.5 last:border-none">
            <span className="text-cp-faint">#{e.seq}</span>{' '}
            <span className="font-semibold text-cp-txt">{e.kind}</span>{' '}
            <span className="break-all">{JSON.stringify(e.payload)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

/** Secondes écoulées depuis le premier événement du run (affichage seulement). */
function useChrono(depuis: string | null, actif: boolean): number | null {
  const [, retick] = useState(0)
  useEffect(() => {
    if (!actif) return
    const t = setInterval(() => retick((n) => n + 1), 1000)
    return () => clearInterval(t)
  }, [actif])
  if (!depuis) return null
  const s = Math.max(0, Math.round((Date.now() - new Date(depuis).getTime()) / 1000))
  return Number.isFinite(s) ? s : null
}


export function CopiloteView() {
  const run = useCopiloteRun()
  const { vue } = run
  const [brief, setBrief] = useState('')
  const [mission] = useState<MissionActive>('instruire')   // v2 : le routeur décide, plus d'onglets
  const [journalOuvert, setJournalOuvert] = useState(false)
  // M102-B2 — LE FIL : ce qui a été demandé, compris, répondu — lisible tour par tour. Quand le
  // Copilote pose une question (clarification), le champ de réponse apparaît DANS le fil.
  const [fil, setFil] = useState<{ q: string; r: CopiloteV2Reponse; echec?: boolean }[]>([])
  const [reponseFil, setReponseFil] = useState('')
  // M107 P3 — expiration du fil par INACTIVITÉ (TTL servi par /ask, jamais recopié) :
  // annoncée à l'écran (« nouvelle conversation »), jamais un fil vidé en silence.
  const [ttlMin, setTtlMin] = useState(10)
  const [filExpire, setFilExpire] = useState(false)
  const derniereActivite = useRef<number>(Date.now())
  const [recap, setRecap] = useState<CopiloteV2Reponse | null>(null)      // §M78-bis — péage de confirmation
  // M107 — la demande qui a produit le récap (la barre se vide désormais : elle ne peut plus la porter)
  const [recapBrief, setRecapBrief] = useState('')
  const [recapConfirme, setRecapConfirme] = useState<string | null>(null)  // reste en tête pendant l'instruction
  const [dispatching, setDispatching] = useState(false)
  const [missions, setMissions] = useState<CopiloteMission[]>([])   // §2b — historique
  const [retentionJours, setRetentionJours] = useState(7)            // RETOURS-8 (R11) — bandeau rétention
  const [convId, setConvId] = useState<number | null>(null)         // conversation en cours (chaînée)
  // M133 — plus de `scenario` : l'accueil v3 ne force AUCUN mode (les chips sont partis). Le routeur
  // comprend seul ; le serveur ne reçoit plus d'intention forcée depuis l'écran d'accueil.
  const [projetForm, setProjetForm] = useState<{ prefill: Record<string, unknown> } | null>(null)  // M113 P3
  const briefRef = useRef<HTMLTextAreaElement | null>(null)

  const rafraichirMissions = () => copiloteV2Missions()
    .then((d) => { setMissions(d.missions); setRetentionJours(d.retention_jours) }).catch(() => {})
  useEffect(() => { void rafraichirMissions() }, [])
  // M78-quater #3 — la veille n'est plus exposée sur cet écran (bloc retiré) ; le mécanisme (intention
  // VEILLE, stockage, évaluation) reste branché côté serveur. Écran veilles dédié = BACKLOG.

  // M78 · 2a / M78-bis — dispatch : le routeur décide. RECHERCHE/VERIFICATION passent par un RÉCAP de
  // confirmation (péage §5 : le coût d'une mauvaise interprétation est élevé) AVANT d'instruire ;
  // QUESTION/OUTIL/PROJET/VEILLE/refus répondent immédiatement (la réponse inline).
  const interroger = async (msg: string, opts?: { confirme?: boolean }) => {
    const m = msg.trim()
    if (!m || dispatching) return
    setDispatching(true); setRecap(null)
    // M107 P2.3 — la barre SE VIDE après envoi : elle ne garde plus la question précédente à
    // l'écran comme si elle attendait quelque chose (le fil et le récap portent la mémoire).
    setBrief('')
    // M107 P3 — un fil expiré repart de zéro AU MESSAGE SUIVANT (l'annonce était à l'écran).
    if (filExpire) { setFil([]); setFilExpire(false) }
    derniereActivite.current = Date.now()
    if (!opts?.confirme) setRecapConfirme(null)        // nouveau brief = nouveau contexte
    try {
      // M133 — aucun scénario forcé : le routeur classe le message en texte libre (comportement M112).
      const r = await copiloteV2Ask(m, { conversation_id: convId, confirme: opts?.confirme })
      if (r.conversation_id != null) setConvId(r.conversation_id)
      if (r.contexte_ttl_minutes) setTtlMin(r.contexte_ttl_minutes)
      void rafraichirMissions()
      // M113 P3 — le parcours projet guidé : le serveur ne crée JAMAIS directement ; il renvoie le
      // préremplissage compris et le front ouvre le formulaire (qui protège par construction).
      if (r.projet_form) { setProjetForm(r.projet_form); setBrief(''); return }
      // M118 — un REFUS-VOIE (refus="hors_mission", intent RECHERCHE/VERIFICATION conservé) N'EST PAS
      // une mission lourde : il rejoint le fil comme une réponse (carte warn + voie), il NE lance
      // JAMAIS le run. Le Copilote resserré n'instruit plus depuis le chat.
      const lourde = (r.intent === 'RECHERCHE' || r.intent === 'VERIFICATION') && !r.refus
      if (lourde && !opts?.confirme && (r.needs_confirmation || r.clarification_recap)) {
        // PÉAGE : on montre le récap, on n'instruit pas. M107 : le brief de travail est le
        // BRIEF EFFECTIF servi (fil composé) — jamais la réponse nue du dernier tour.
        setRecap(r); setRecapBrief(r.brief_effectif ?? m)
      } else if (r.intent === 'RECHERCHE' && !r.refus) {   // confirmé → on lance le run M26-A (jamais un refus-voie)
        const bfr = r.brief_effectif ?? m
        setRecapConfirme(r.recap ?? bfr); void run.instruire(mission, bfr)
      } else {
        setFil((f) => [...f, { q: m, r }])             // M102-B2 — le tour rejoint le fil
        setReponseFil('')
      }
    } catch (e) {
      // FIX-COPILOTE F3 — un 429 (plafond quotidien du Copilote atteint) porte un message CLAIR du
      // serveur : on l'affiche verbatim, SANS bouton Réessayer (ça repart à minuit, pas « dans un
      // instant » — un retry ne ferait que re-cogner le plafond).
      const quota = is429(e)
      const echec = (quota
        ? { text: (e as ApiError).detail ?? 'Limite quotidienne du Copilote atteinte — elle repart à minuit.', intent: null, erreur: true }
        // M102 P1 (constat 2) — jamais un message technique (le detail d'une HTTPException aval
        // arrivait BRUT ici, avec l'identifiant de run) : phrase honnête, la trace vit côté serveur.
        // M107 — l'échec est RÉCUPÉRABLE sur place : le tour porte un bouton Réessayer.
        : { text: 'Je n’ai pas pu traiter votre demande — le service ne répond pas. Réessayez dans un instant.', intent: null, erreur: true }) as CopiloteV2Reponse
      setFil((f) => [...f, { q: m, r: echec, echec: !quota }])
    } finally { setDispatching(false) }
  }
  const soumettre = () => void interroger(brief)

  // M107 P3 — le minuteur d'inactivité : quand le fil dort plus de ttlMin, l'expiration est
  // ANNONCÉE (bandeau « nouvelle conversation ») et le contexte serveur est abandonné
  // (convId null) ; le fil reste visible, estompé, jusqu'au message suivant.
  useEffect(() => {
    if (fil.length === 0 || filExpire) return
    const t = setInterval(() => {
      if (Date.now() - derniereActivite.current > ttlMin * 60_000) {
        setFilExpire(true); setConvId(null)
      }
    }, 15_000)
    return () => clearInterval(t)
  }, [fil.length, filExpire, ttlMin])

  // §M78-bis — callbacks du récap. reask : ré-interprète (option/chip) → nouveau récap. lancer :
  // valide → RECHERCHE lance le run avec le brief final, VERIFICATION produit l'avis (confirme).
  // corriger : remet le brief dans la barre (jamais verrouillée) pour réécrire.
  const reask = (nouveauBrief: string) => { setBrief(nouveauBrief); void interroger(nouveauBrief) }
  const lancerRecap = (finalBrief: string) => {
    const intent = recap?.intent
    // M107 P2.3 — la barre se vide au lancement aussi : le récap confirmé (en tête) porte la mémoire.
    setRecap(null); setBrief('')
    if (intent === 'VERIFICATION') { void interroger(finalBrief, { confirme: true }) }
    else { setRecapConfirme(recap?.recap ?? finalBrief); void run.instruire(mission, finalBrief) }
  }
  const corrigerRecap = (b: string) => { setRecap(null); setBrief(b); setTimeout(() => briefRef.current?.focus(), 0) }
  // M117 · D8 — « Nouveau fil » et l'annonce du TTL sur TOUS les chemins (fil, récap-péage, formulaire
  // projet), plus seulement le fil. Repart de zéro : vide tout, refocalise le brief.
  const nouveauFil = () => {
    setFil([]); setConvId(null); setFilExpire(false); setReponseFil(''); setBrief('')
    setRecap(null); setProjetForm(null); briefRef.current?.focus()
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
  // enveloppe un gabarit d'action (récap-péage / formulaire projet) avec l'annonce TTL + « Nouveau fil ».
  const avecChrome = (node: ReactNode) => (
    <div className="flex flex-col gap-3 text-left">{ttlNotice}{node}{boutonNouveauFil}</div>
  )

  // §2b — rouvrir une mission passée : RECHERCHE (run_id) rejoue le run ; sinon restaure la dernière
  // réponse Copilote de la conversation (inline). On reprend là où on s'est arrêté.
  const rouvrir = async (m: CopiloteMission) => {
    if (m.run_id) { charger(m.run_id); return }
    try {
      const conv = await copiloteV2Mission(m.id)
      setConvId(conv.id)
      // M102-B2 — la reprise restaure le FIL COMPLET (demandé/répondu), pas seulement le dernier tour.
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

  // rafraîchissement en plein run : on recharge le run épinglé, le SSE rejoue le fil
  const { charger } = run
  useEffect(() => {
    const id = runEpingle()
    if (id) charger(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // M65 P4 — « Décrire un projet » (liste Projets) arme `entretienDirect` puis navigue ici :
  // l'amorce prend place dans le brief (ancien flux IAStub → ProjetEntretien, désormais absorbé
  // par le Copilote). Consommée une fois, puis effacée. Ne pas écraser un brief déjà saisi.
  const { entretienDirect, clearEntretienDirect } = useApp()
  const selectParcelle = useApp((s) => s.select)
  const setView = useApp((s) => s.setView)
  const setOpenProjet = useApp((s) => s.setOpenProjet)   // M113 P3 — « Voir le projet → »
  // M78-bis — ouvrir la fiche existante d'une parcelle restituée (setView PUIS select, ordre respecté).
  const ouvrirFiche = (idu: string) => { setView('cartes'); selectParcelle(idu) }
  // GB-031/GB-039 — Échap ferme le Copilote (retour à la carte). Une modale brief interne a la priorité
  // (elle porte [data-brief-close]) ; le journal se ferme d'abord. PATRON DOUBLE-ÉCHAP (comme Comparaison) :
  // si le focus est dans un champ AVEC du texte, le 1er Échap REND le focus (protège la saisie), le 2e
  // (focus hors champ) ferme. Champ VIDE ou focus hors champ → Échap ferme directement (plus de garde
  // input-focus qui neutralisait l'Échap quand la zone de saisie est auto-focus — l'écart GB-039).
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return
      // GB-039 — le panneau « Brief du matin » est TOUJOURS dans le DOM (translaté hors-écran quand
      // fermé) : on détecte son ouverture RÉELLE par `aria-hidden` (l'ancienne garde `[data-brief-close]`
      // le trouvait toujours → l'Échap ne fermait jamais). S'il est ouvert, il gère Échap lui-même.
      const brief = document.querySelector('[aria-label="Brief du matin"]')
      if (brief && brief.getAttribute('aria-hidden') !== 'true') return
      const el = document.activeElement as HTMLInputElement | HTMLTextAreaElement | null
      if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') && (el.value ?? '').trim()) {
        el.blur(); return                       // 1er Échap : champ non vide → rend le focus, ne ferme pas
      }
      if (journalOuvert) { setJournalOuvert(false); return }
      setView('cartes')                          // champ vide / focus hors champ → ferme
    }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [journalOuvert, setView])
  useEffect(() => {
    if (entretienDirect === null) return
    setBrief((b) => b.trim() ? b : (entretienDirect || 'je veux monter une opération immobilière'))
    briefRef.current?.focus()
    clearEntretienDirect()
  }, [entretienDirect, clearEntretienDirect])

  const actif = run.runId != null
  const terminal = vue.statut === 'done' || vue.statut === 'failed' || vue.statut === 'cancelled'
  const enAttente = vue.statut === 'awaiting_user'
  const enInstruction = actif && !terminal && !enAttente
  const fini = vue.statut === 'done' && vue.recap != null
  // M78-bis — un run rejoué au boot en PAUSE (awaiting_user) est un RÉSIDU d'avant le récap : la
  // confirmation-récap a REMPLACÉ la pause, et son UI (clarification pleine page + bouton « répondre »)
  // n'existe plus. Un tel run court-circuiterait l'accueil et resterait bloqué sur « EN PAUSE » sans
  // moyen d'avancer. On le dépingle → l'accueil (2a) reprend la main. Ne touche pas au run serveur.
  const { reinitialiser } = run
  useEffect(() => {
    if (enAttente) reinitialiser()
  }, [enAttente, reinitialiser])
  const communes = (vue.briefJson?.communes as string[] | undefined) ?? null
  const nLogements = (vue.briefJson?.programme as { logements?: number } | undefined)?.logements
  const nFaits = vue.etapes.filter((e) => e.etat === 'faite' || e.etat === 'echouee').length
  const chrono = useChrono(run.evenements[0]?.created_at ?? null, enInstruction)

  // relances de l'état 4 — NON CHIFFRÉES : le brief d'origine revient en console,
  // l'utilisateur ajuste lui-même (aucun chiffre inventé par l'écran)
  const relancer = () => {
    setBrief(vue.briefRaw ?? brief)
    briefRef.current?.focus()
    briefRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'center' })
  }

  // §2c/2d — modifier un critère (chip) : si une instruction tourne, on l'ANNULE proprement (le
  // client pilote, il ne subit pas) puis on relance avec les critères corrigés. Aucun job zombie.
  const relancerAvec = async (nouveauBrief: string) => {
    if (!nouveauBrief.trim()) return
    setBrief(nouveauBrief)
    if (enInstruction || enAttente) await run.annuler()
    void run.instruire(mission, nouveauBrief)
  }
  // « + corriger » : ramène le brief dans la barre d'accueil (édition libre), instruction annulée.
  const corrigerDansBarre = (b: string) => {
    setBrief(b)
    if (enInstruction || enAttente) void run.annuler()
    run.reinitialiser()
    setTimeout(() => briefRef.current?.focus(), 0)
  }

  const pill = run.quota != null
    ? <PillStatut ton="rouge">{S.quota.pill}</PillStatut>
    : actif
      ? <PillStatut ton={TON_STATUT[vue.statut] ?? 'violet'}
          pulse={vue.statut === 'running' || vue.statut === 'interpreting'}>
          {S.statuts[vue.statut] ?? vue.statut}
          {enInstruction && chrono != null ? ` · ${chrono} s` : ''}
        </PillStatut>
      : null

  return (
    <div data-copilote className="min-h-0 flex-1 overflow-y-auto bg-cp-bg font-sans text-[13px] text-cp-txt" style={FOND}>
      <div className="mx-auto max-w-[1000px] px-6 pb-12 pt-9">
        {!actif ? (
          /* ── 2a · ACCUEIL recopié de la maquette (idle) — la barre dispatche via le routeur v2 ── */
          <AccueilCopilote value={brief} onChange={setBrief} onSubmit={soumettre}
            occupe={dispatching}
            onExemple={(t) => { setBrief(t); void interroger(t) }}
            missions={missions} retentionJours={retentionJours} onReprendre={rouvrir}
            reponse={projetForm
              ? /* M113 P3 — le parcours projet guidé, prérempli ; M117 D8 — TTL + « Nouveau fil ». */
                avecChrome(<ParcoursProjet prefill={projetForm.prefill} accent="ia"
                  onVoir={(p) => { setProjetForm(null); setOpenProjet(p) }}
                  onFermer={() => setProjetForm(null)} />)
              : recap
              ? /* M117 D8 — le récap-péage porte aussi le TTL + « Nouveau fil ». */
                avecChrome(<RecapConfirmation data={recap} brief={recapBrief} onReask={reask}
                  onLancer={lancerRecap} onCorriger={corrigerRecap}
                  onRepondre={(t) => void interroger(t)} />)
              : (fil.length > 0 || dispatching) ? (
                /* M102-B2 — LE FIL : demandé / compris / répondu, tour par tour. */
                <div data-fil className="flex flex-col gap-3 text-left">
                  {/* M107 P3 / M117 D8 — l'expiration ANNONCÉE (helper partagé, présent sur tous les chemins). */}
                  {ttlNotice}
                  <div className={filExpire ? 'flex flex-col gap-3 opacity-50' : 'flex flex-col gap-3'}>
                  {fil.map((t, i) => (
                    <div key={i} className="flex flex-col gap-1.5">
                      <p data-fil-question className="self-end rounded-xl bg-cp-violet/10 px-3.5 py-1.5 text-[12.5px] text-cp-txt">
                        {t.q}
                      </p>
                      <ReponseInline v2={t.r} />
                      {/* M107 — l'échec est récupérable SUR PLACE : un bouton, pas une consigne. */}
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
                    /* M107 P2 — le champ de réponse est PERMANENT dans le fil : on répond à une
                       question, on corrige ou on précise AU MÊME ENDROIT (autofocus quand le
                       Copilote vient de poser une question). */
                    <div data-fil-reponse className="flex items-center gap-2">
                      <input autoFocus={fil[fil.length - 1].r.clarification === true}
                        value={reponseFil} onChange={(e) => setReponseFil(e.target.value)}
                        onKeyDown={(e) => { if (e.key === 'Enter' && reponseFil.trim()) { void interroger(reponseFil); setReponseFil('') } }}
                        placeholder={fil[fil.length - 1].r.clarification ? 'Votre réponse…' : 'Répondre, corriger ou préciser…'}
                        className="min-w-0 flex-1 rounded-lg border border-violet/30 bg-cp-card px-3.5 py-2 text-[13px] text-cp-txt placeholder:text-cp-faint focus:border-violet focus:outline-none" />
                      <button data-fil-envoyer disabled={!reponseFil.trim()}
                        onClick={() => { void interroger(reponseFil); setReponseFil('') }}
                        className="rounded-lg border border-violet/40 bg-violet/10 px-3.5 py-2 font-display text-[12px] font-semibold text-violet hover:bg-violet/15 disabled:opacity-40">
                        Répondre
                      </button>
                    </div>
                  )}
                  {!dispatching && fil.length > 0 && boutonNouveauFil}
                </div>
              ) : null} />
        ) : (
          <>
            <div className="mb-4 flex items-center gap-3">
              <span className="font-display text-[10.5px] uppercase tracking-[.24em] text-cp-muted">{S.crumb}</span>
              {pill}
              {run.fluxInterrompu && (
                <span data-flux-interrompu className="text-[10.5px] text-cp-amber">{S.fluxInterrompu}</span>
              )}
            </div>
            {/* §M78-bis 2 — le récap validé RESTE en tête pendant l'instruction et sur les résultats :
                le client qui revient (notification) relit son brief en une ligne. */}
            {recapConfirme && (
              <div data-recap-confirme className="mb-4 rounded-xl border border-cp-ia/20 bg-cp-ia/[0.04] px-4 py-2 text-[12.5px] leading-snug text-cp-muted">
                <span className="text-cp-ia">✦</span> {recapConfirme}
              </div>
            )}
            {/* barre principale — JAMAIS verrouillée (§complément) : le client peut toujours écrire. */}
            <div className="flex flex-wrap items-start gap-5 rounded-[18px] border border-cp-ia/35 bg-gradient-to-b from-cp-ia/5 to-white/[0.015] p-5 shadow-[0_0_60px_rgba(180,151,240,.06)]">
              <div className="min-w-[250px] flex-1">
                <textarea data-brief ref={briefRef} value={brief} onChange={(e) => setBrief(e.target.value)}
                  placeholder={S.placeholder} rows={2}
                  className="w-full resize-none bg-transparent font-sans text-base leading-normal text-cp-txt outline-none placeholder:text-cp-faint focus:outline-none" />
              </div>
              <div className="flex flex-col items-end gap-2">
                {enInstruction ? (
                  <button data-annuler onClick={() => void run.annuler()}
                    className="rounded-[13px] border border-cp-line2 px-6 py-3.5 font-display text-[13px] font-bold uppercase tracking-wide text-cp-muted">
                    {S.annuler}
                  </button>
                ) : (
                  <button data-instruire onClick={soumettre}
                    disabled={!brief.trim() || run.enCreation || dispatching}
                    className="rounded-[13px] bg-cp-ia px-7 py-3.5 font-display text-[13px] font-bold uppercase tracking-wide text-cp-ia-on shadow-[0_0_36px_rgba(180,151,240,.28)] transition-transform duration-quick hover:brightness-110 disabled:opacity-40">
                    {S.instruire} →
                  </button>
                )}
                <div className="flex items-center gap-2 text-[10.5px] text-cp-faint">
                  <i className="h-1 w-1 rounded-full bg-cp-ia" />
                  {enInstruction ? S.enCoursSerment(nFaits, vue.plan.length || 6) : S.serment}
                </div>
              </div>
            </div>
            {/* §2c — « COMPRIS : » chips éditables des critères déduits (dès brief_parsed) */}
            {vue.briefJson && (
              <div className="mt-4">
                <ChipsCompris briefJson={vue.briefJson} enCours={enInstruction}
                  onRelancer={relancerAvec} onCorriger={corrigerDansBarre} />
              </div>
            )}
          </>
        )}

        {/* ── état 5 · quota atteint AVANT création — aucun run, aucun moteur ── */}
        {run.quota && (
          <div data-quota-panel
            className="mt-9 rounded-2xl border border-cp-red/30 bg-gradient-to-br from-cp-red/10 to-cp-red/[0.02] px-6 py-7 text-center">
            <div className="mx-auto mb-3.5 flex h-11 w-11 items-center justify-center rounded-full border border-cp-red/45 text-cp-red">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
                <circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" />
              </svg>
            </div>
            <h3 className="font-display text-[19px] font-semibold tracking-tight text-cp-txt">
              {S.quota.titre(run.quota.quota)}
            </h3>
            {/* le corps du 429, verbatim — c'est lui qui dit quand ça repart */}
            <p data-quota-detail className="mx-auto mt-2 max-w-[62ch] text-[13px] text-cp-muted">{run.quota.detail}</p>
            <p className="mx-auto mt-1.5 max-w-[62ch] text-[13px] text-cp-muted">{S.quota.aucunRun}</p>
            <p className="mx-auto mt-3 max-w-[62ch] text-[12px] text-cp-faint">{S.quota.distinct}</p>
          </div>
        )}
        {run.erreur && (
          <p data-erreur className="mt-5 rounded-xl border border-cp-red/30 bg-cp-red/10 px-4 py-3 text-[12px] text-cp-red">
            {run.erreur}
          </p>
        )}

        {/* §M78-bis complément — l'écran « PRÉCISION NÉCESSAIRE » (clarification pleine page + 24 chips
            + barre verrouillée « EN ATTENTE ») est RETIRÉ : la clarification est désormais une bulle du
            récap (≤ 4 options, barre jamais verrouillée), AVANT l'instruction. De même, plus aucune étape
            « en attente » n'est affichée tant que l'instruction n'est pas lancée. */}

        {/* ── état 2 · instruction en cours — AUCUN résultat partiel (règle 5) ── */}
        {enInstruction && vue.plan.length > 0 && (
          <>
            <SecHead titre={S.entonnoir.titre} sousTitre={S.entonnoir.sousTitreEnCours} />
            <Entonnoir etages={entonnoirEnCours(vue)} communes={communes}
              calibrage={calibrageConnu(vue)} enCours />
            <SecHead titre={S.fil.titre}
              meta={S.fil.metaEtape(Math.min(nFaits + 1, vue.plan.length), vue.plan.length)} />
            <FilInstruction etapes={vue.etapes} interpretation={etatInterpretation(vue)} />
            <SecHead titre={S.resultats.titreEnCours} />
            <div data-en-cours
              className="rounded-2xl border border-dashed border-cp-line2 bg-cp-card px-8 py-9 text-center text-[12.5px] leading-relaxed text-cp-faint">
              {S.enCours}<br />{S.enCoursNote}
            </div>
          </>
        )}

        {vue.statut === 'cancelled' && (
          <p data-annulee className="mt-9 rounded-2xl border border-cp-line2 bg-cp-card px-6 py-5 text-[12.5px] text-cp-muted">
            {S.annulee}{vue.motifAnnulation ? ` — ${vue.motifAnnulation}` : ''}
          </p>
        )}
        {vue.statut === 'failed' && vue.echec && (
          <p data-echec className="mt-9 rounded-2xl border border-cp-red/30 bg-cp-red/[0.06] px-6 py-5 text-[12.5px] leading-relaxed text-cp-txt">
            {vue.echec.message}{vue.echec.detail ? <span className="text-cp-muted"> ({vue.echec.detail})</span> : null}
          </p>
        )}

        {/* ── états 1 & 4 · instruction terminée (zéro n'est PAS une erreur — règle 6) ── */}
        {fini && vue.recap && (
          <>
            <SecHead titre={S.entonnoir.titre} sousTitre={S.entonnoir.sousTitre} />
            <Entonnoir etages={vue.recap.entonnoir} communes={communes}
              dureeMs={vue.final?.duree_totale_ms ?? null}
              exhaustif={vue.recap.exhaustif} calibrage={vue.recap.calibrage}
              requalification={vue.recap.requalification ?? null} />

            <SecHead titre={S.fil.titre} meta={S.fil.meta(vue.etapes.length)} />
            <FilInstruction etapes={vue.etapes} />

            <SecHead titre={S.resultats.titre(vue.recap.n_restituees)}
              meta={S.resultats.meta(vue.recap.n_retenues)} />
            {/* §5 surface 2 — affiner par le Copilote : la shortlist courante devient le contexte */}
            {vue.recap.n_restituees > 0 && (
              <div className="mb-3">
                <CopiloteEmbarque contexte={{ selection: vue.recap.restituees_idu
                    ?? (vue.recap.restituees ?? []).map((p) => p.idu) }}
                  placeholder="Affiner par le Copilote sur cette shortlist…"
                  exemples={['Laquelle est la moins risquée ?', 'Compare les deux premières']} />
              </div>
            )}
            {vue.recap.n_restituees > 0 ? (
              <Resultats recap={vue.recap} etiquettes={etiquettesDe(vue)} onOuvrirFiche={ouvrirFiche}
                budgetMax={(vue.briefJson?.budget_max_eur as number | undefined) ?? null}
                titre={[communes?.join(', '), nLogements != null ? `${nLogements} logements` : null]
                  .filter(Boolean).join(' · ')} />
            ) : (
              <div data-zero className="rounded-2xl border border-cp-line2 bg-cp-card px-8 py-8 text-center">
                <div className="mx-auto mb-3.5 flex h-11 w-11 items-center justify-center rounded-full border border-cp-line2 text-cp-muted">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" />
                  </svg>
                </div>
                <h3 className="font-display text-[19px] font-semibold tracking-tight text-cp-txt">{S.resultats.zeroTitre}</h3>
                <p className="mx-auto mt-2 max-w-[62ch] text-[13px] text-cp-muted">{S.resultats.zeroNote}</p>
                <div className="mt-4 flex flex-wrap justify-center gap-2.5">
                  <button data-relance onClick={relancer}
                    className="rounded-xl bg-cp-ia px-5 py-3 font-display text-[12px] font-bold text-cp-ia-on">
                    {S.resultats.relanceBudget}
                  </button>
                  <button data-relance onClick={relancer}
                    className="rounded-xl border border-cp-line2 bg-cp-card2 px-5 py-3 font-display text-[12px] font-bold text-cp-txt">
                    {S.resultats.relanceCommunes}
                  </button>
                </div>
              </div>
            )}
            <BlocLivrable recap={vue.recap} nMoteurs={vue.etapes.length}
              ouvrirJournal={() => setJournalOuvert(true)} />
            {journalOuvert && <Journal evenements={run.evenements} fermer={() => setJournalOuvert(false)} />}
          </>
        )}
      </div>
    </div>
  )
}
