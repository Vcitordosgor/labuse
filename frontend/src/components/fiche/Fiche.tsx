import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Tip } from '../Tip'
import { Bouton } from '../ui/Bouton'
import { Badge } from '../ui/Badge'
import { useEffect, useMemo, useState, useRef, type ReactNode } from 'react'
import { addToPipeline, ajouterParcelle, ApiError, archivePipeline, createProjet, getDossierStatut, getFaisabilite, getFiche, getGabarit, getMoi, getParcelExposition, getPipelineForParcel, getPipelineMeta, getProjets, getWatch, is429, patchPipeline, postSignalement, preDossierUrl, projetsPourParcelle, SOURCE, toggleWatch } from '../../lib/api'
import { verdictMeta } from '../../lib/status'
import { AnalyseLabuseCard } from './AnalyseLabuseCard'   // RETOURS-14 P1 — carte « Analyse LABUSE » extraite (testable), affiche la version servie
import { fmtInt, fmtM2, fmtDateNum, fmtLibelleBrut, iduComplet } from '../../lib/format'
import { layerLabel } from '../../lib/layers'
import { CLIENT } from '../../lib/strings'
import { Squelette } from '../Loading'
import { EmptyState, ErrorState } from '../States'
import { DeplacerMenu } from '../crm/DeplacerMenu'   // DA-FIX-5c — menu « Déplacer vers… » partagé (kanban CRM)
import { AskBar } from './AskBar'
import { FinancierQuestionnaire } from './FinancierQuestionnaire'
import { GabaritLine } from './GabaritLine'
import { cadastreGeoportailUrl, googleMapsUrl, pagesJaunes } from './liensExternes'
import { LogoCadastre, LogoPagesJaunes, LogoGoogleMaps } from './logosServices'
import { PourquoiPasTab } from './PourquoiPas'
import { ScoreV2Block } from './ScoreV2Block'
import { BlocIndisponible } from './BlocIndisponible'
import { CoproprietesBlock } from './CoproprietesBlock'
import { ProprietaireHistorique } from './ProprietaireHistorique'
import type { Onglet } from '../../lib/types'
import { useApp } from '../../store/useApp'
import { GrilleOutils, OutilCase } from '../shared/GrilleOutils'   // PROJETS-V5 (E9) — grille d'outils partagée
import { IC, FicheAccordionCtx, RefDrawer, GroupLabel, MicroJauge, MicroPastilles, RateLimit429, Line, EligibiliteReplie, PorteOutil, FactRow, FactNote, Vigilance } from './primitives'
// FICHE-RANGEMENT-2 Lot 1 — LE BASCULEMENT : la fiche est recomposée en 11 sections PAR NATURE,
// chacune un RefDrawer inline qui COMPOSE les blocs feuilles (extraits aux étapes 3a-3c). Les
// sections « fourre-tout » ConstructibiliteSection / LeBienSection sont dissoutes ; les quatre
// sections encore mono-nature (Risques, Réseaux, Marché, Quartier) restent des composants réutilisés.
// Fiche ré-exporte Calculette + FaisabiliteTab (consommés par CalculetteFonciere / M22Programme).
import { TransformationBlock, FaisabiliteTab, BilanTab, TaxeAmenagementBlock, RtaaFromBilan, DispositifsBody, ModeBBody } from './constructibilite'
import { BatiBlock, FiliationBlock } from './leBien'
// KELFONCIER-FIX-2 (Partie B) — les formes de la maquette v3 (Verdict · Tuiles · BarreEmpilée…).
import { Verdict, Tuiles, type Tuile, BarreEmpilee, type Part, Lignes, Ligne, Pastilles, type Pastille, OutilsSection, type OutilSection, InfoI, Repli } from './formes'
import { RisquesSection } from './risques'
import { MarcheSection, DerniereVenteBlock } from './marche'
import { ReseauxSection, EquipementsBadges } from './reseaux'
import { ProfilAltimetrique } from './ProfilAltimetrique'   // RETOURS-13 P6
import { AutourSection, HistoriqueSiteBlock } from './autour'
import { ReglementPluBlock } from './blocks'   // FICHE-RANGEMENT-2 Lot 1 — extraits (cycle-free)
export { Calculette, FaisabiliteTab } from './constructibilite'
export type { CalcResult } from './constructibilite'


// FICHE-RANGEMENT-2 Lot 1 — le tiroir client « Données et méthode » est RETIRÉ (métrologie de
// complétude = lecture admin/Circuit, pas cliente) : IcdBlockView supprimé (0-caller côté fiche).
// Le payload `f.icd` reste servi par le back (disponible côté admin).

// RETOURS-11 F2 — id de tiroir (RefDrawer) → libellé de section, pour tagger le signalement
// avec « la section ouverte » (jamais une clé technique à l'écran).
// FICHE-RANGEMENT-2/3 — les 11 sections PAR NATURE (accordéon exclusif). Mode B (Réhabilitation)
// n'est plus un tiroir : il vit DANS §11 Simulation (FICHE-RANGEMENT-3 Lot 3).
const SECTION_LABELS: Record<string, string> = {
  identite: 'Identité',
  terrain: 'Terrain',
  bati: 'Bâti',
  urbanisme: 'Urbanisme',
  risques: 'Risques et environnement',
  reseaux: 'Réseaux et desserte',
  fiscalite: 'Fiscalité et dispositifs',
  marche: 'Marché',
  quartier: 'Quartier',
  potentiel: 'Potentiel',
  simulation: 'Simulation',
}

// ── M9 lot 3 — Signaler une erreur (file de QA humaine, aucune action automatique) ──
const SIGNALEMENT_TYPES: [string, string][] = [
  ['faux_positif', 'Erreur de détection (piscine, PV…)'], ['zonage', 'Zonage PLU'],
  ['bati', 'Bâti / occupation'], ['adresse', 'Adresse'], ['proprietaire', 'Propriétaire'],
  ['risque', 'Risque'], ['score', 'Score / verdict'], ['viabilisation', 'Viabilisation'], ['autre', 'Autre'],
]
// RETOURS-11 F2 — le signalement de fiche porte l'IDU, la SECTION ouverte et (côté Produit) le
// type « Donnée ». La section arrive pré-remplie dans le champ concerné (éditable) : le signalement
// atterrit dans Produit avec la mention « parcelle <IDU> — <Section> ».
function SignalerErreur({ idu, section }: { idu: string; section?: string | null }) {
  const [open, setOpen] = useState(false)
  const [type, setType] = useState('faux_positif')
  const [champ, setChamp] = useState(section ?? '')
  const [commentaire, setCommentaire] = useState('')
  // La section ouverte change pendant qu'on lit la fiche → on garde le champ à jour tant que
  // l'utilisateur n'a pas ouvert le formulaire (une fois ouvert, on ne réécrit plus sa saisie).
  useEffect(() => { if (!open) setChamp(section ?? '') }, [section, open])
  const m = useMutation({ mutationFn: () => postSignalement({ idu, type_erreur: type, champ: champ || undefined, commentaire: commentaire || undefined }) })
  if (m.isSuccess) {
    return (
      <div data-signalement-ok className="card-elev px-3 py-2.5 text-[11px] text-txt-mut">
        ✓ Signalement enregistré (n°{m.data.id}) — merci. Il sera revu manuellement.
      </div>
    )
  }
  if (!open) {
    return (
      <button data-signaler-erreur onClick={() => setOpen(true)}
        className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11px] text-txt-mut hover:border-mint hover:text-mint">
        ⚑ Signaler une erreur
      </button>
    )
  }
  return (
    <div data-signalement-form className="card-elev px-3 py-2.5">
      <p className="label-caps">Signaler une erreur</p>
      <label className="mt-2 block text-[11px] text-txt-mut">Type d’erreur
        <select data-signalement-type value={type} onChange={(e) => setType(e.target.value)} className="mt-0.5 w-full rounded-md border border-line-2 bg-surface-3 px-2 py-1 text-xs text-txt">
          {SIGNALEMENT_TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
      </label>
      <label className="mt-2 block text-[11px] text-txt-mut">Champ concerné (optionnel)
        <input value={champ} onChange={(e) => setChamp(e.target.value)} placeholder="ex. piscine, zonage, adresse"
          className="mt-0.5 w-full rounded-md border border-line-2 bg-surface-3 px-2 py-1 text-xs text-txt placeholder:text-txt-dim" />
      </label>
      <label className="mt-2 block text-[11px] text-txt-mut">Commentaire
        <textarea data-signalement-commentaire value={commentaire} onChange={(e) => setCommentaire(e.target.value)} rows={2} placeholder="Décrivez l’erreur constatée"
          className="mt-0.5 w-full rounded-md border border-line-2 bg-surface-3 px-2 py-1 text-xs text-txt placeholder:text-txt-dim" />
      </label>
      <div className="mt-2 flex items-center gap-2">
        <button data-signalement-submit onClick={() => m.mutate()} disabled={m.isPending}
          className="rounded-md bg-mint px-3 py-1 text-xs font-medium text-mint-ink">
          {m.isPending ? 'Envoi…' : 'Envoyer'}
        </button>
        <button onClick={() => setOpen(false)} className="text-[11px] text-txt-mut hover:text-txt">Annuler</button>
        {m.isError && <span className="text-[11px] text-st-ecartee">Échec — réessayez.</span>}
      </div>
      <p className="mt-1.5 text-[10px] leading-snug text-txt-dim">Aucune modification automatique des données : votre signalement entre dans une file de vérification humaine.</p>
    </div>
  )
}


// M14 — suivi de cible : événements sur cette parcelle SANS l'entrer au pipeline.
function WatchButton({ idu }: { idu: string }) {
  const qc = useQueryClient()
  const setToast = useApp((s) => s.setToast)
  const w = useQuery({ queryKey: ['watch', idu], queryFn: () => getWatch(idu) })
  // RETOURS-11F M10 — la cloche EST le pont vers la Veille (dans les deux sens : retirer depuis
  // Veille éteint la cloche via la même clé de requête `suivis`). Le toast dit où la retrouver.
  const t = useMutation({
    mutationFn: () => toggleWatch(idu),
    onSuccess: (res: { watched?: boolean } | void) => {
      qc.invalidateQueries({ queryKey: ['watch', idu] })
      qc.invalidateQueries({ queryKey: ['suivis'] })   // la liste Veille › Parcelles reflète aussitôt
      const nowOn = (res && typeof res === 'object' && 'watched' in res) ? !!res.watched : !w.data?.watched
      setToast(nowOn ? 'Parcelle suivie — retrouvez-la dans Veille › Parcelles.'
                     : 'Parcelle retirée du suivi.')
    },
  })
  const on = w.data?.watched
  // C4 · cloche = suivi ; style référence (31×31, vert actif quand suivie).
  return (
    <button onClick={() => t.mutate()} className="hbtn"
      style={on ? { background: 'var(--mint-bg)', borderColor: 'var(--mint)', color: 'var(--mint)' } : undefined}
      aria-label={on ? CLIENT.fiche.suivreActif : CLIENT.fiche.suivre}>
      <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M10 5a2 2 0 1 1 4 0a7 7 0 0 1 4 6v3a4 4 0 0 0 2 3H4a4 4 0 0 0 2-3v-3a7 7 0 0 1 4-6" /><path d="M9 17v1a3 3 0 0 0 6 0v-1" /></svg>
    </button>
  )
}

// EXPRESS-01 · bouton « copier l'IDU » — copie la chaîne BRUTE 14 car. (sans espace),
// celle qu'on colle dans GPU/DVF/SIG. Style référence (bouton 31×31, retour visuel vert).
// M61 P5 — bouton « copier » discret, réutilisable (IDU + adresse). Libellés paramétrables.
function CopyIdu({ value, aria = 'Copier l’IDU', dataAttr = 'idu' }: {
  value: string; aria?: string; titre?: string; okTitre?: string; dataAttr?: string
}) {
  const [ok, setOk] = useState(false)
  const copier = async () => {
    try {
      await navigator.clipboard.writeText(value)
      setOk(true)
      setTimeout(() => setOk(false), 1400)
    } catch { /* presse-papier indisponible : on ne fait rien de destructeur */ }
  }
  return (
    <button onClick={copier} data-fiche-copy={dataAttr} aria-label={aria}
      style={{ border: 'none', background: 'none', padding: 2, display: 'flex', alignItems: 'center', justifyContent: 'center', color: ok ? 'var(--mint)' : 'var(--txt-ghost)', cursor: 'pointer', flexShrink: 0 }}>
      {ok
        ? <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m5 12 5 5 9-11" /></svg>
        : <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="9" width="11" height="11" rx="2" /><path d="M5 15V5a2 2 0 0 1 2-2h9" /></svg>}
    </button>
  )
}

// M55-L point 3 — l'icône « partager » (pack apporteur : lien public filigrané) a été RETIRÉE du
// header de la fiche (décision Vic). La fonction ShareButton et l'import createShare deviennent
// 0-caller côté front → retirés aussi (endpoint back /partners/share intact, revient au besoin).

// CONNEXIONS-2 Lot 3 (KO-8) — « Ajouter au CRM » propose LA COLONNE (menu ; défaut = 1re colonne),
// au lieu d'imposer silencieusement la colonne par défaut. Le clic ouvre le menu ; le choix envoie
// `status` au back (qui le valide contre les colonnes du tenant).
function PipelineButton({ idu }: { idu: string }) {
  const qc = useQueryClient()
  const [open, setOpen] = useState(false)
  const state = useQuery({ queryKey: ['pipeline-parcel', idu], queryFn: () => getPipelineForParcel(idu) })
  const inPipe = state.data?.in_pipeline
  const meta = useQuery({ queryKey: ['pipeline-meta'], queryFn: getPipelineMeta, enabled: open || !!inPipe })
  const add = useMutation({
    mutationFn: (status?: string) => addToPipeline(idu, status),
    onSuccess: () => {
      setOpen(false)
      qc.invalidateQueries({ queryKey: ['pipeline-parcel', idu] })
      qc.invalidateQueries({ queryKey: ['pipeline'] })
    },
  })
  // DA-FIX-5c — depuis la fiche, quand la parcelle est suivie, on DÉPLACE la carte vers une autre
  // colonne (même menu « Déplacer vers… » que le kanban) ou on la RETIRE du CRM (archivage réversible,
  // restaurable depuis « Archivées »). Les deux invalident le bloc pour refléter l'état à l'instant.
  const invalider = () => {
    qc.invalidateQueries({ queryKey: ['pipeline-parcel', idu] })
    qc.invalidateQueries({ queryKey: ['pipeline'] })
  }
  const deplacer = useMutation({
    mutationFn: (status: string) => patchPipeline(state.data!.entry!.id, { status }),
    onSuccess: invalider,
  })
  const retirer = useMutation({
    mutationFn: () => archivePipeline(state.data!.entry!.id),
    onSuccess: invalider,
  })
  const cols = meta.data?.columns ?? []
  // RETOURS-11 T3 (03/09) — le menu se ferme au clic n'importe où ailleurs et à Échap.
  const wrap = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => { if (wrap.current && !wrap.current.contains(e.target as Node)) setOpen(false) }
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('mousedown', onDown); document.addEventListener('keydown', onKey)
    return () => { document.removeEventListener('mousedown', onDown); document.removeEventListener('keydown', onKey) }
  }, [open])
  return (
    // ADMIN-1 AD1 — « + CRM » = VERT (contour --mint via .act-mint, survol plein vert via .hover-fill),
    // largeur ÉGALE à « + Projet » (flex-1). Le choix de colonne reste APRÈS le clic (menu ci-dessous).
    // RETOURS-11 T3 — bouton OPAQUE (act-cmp) tant que le menu est ouvert.
    <div ref={wrap} className="relative flex-1">
      <button
        onClick={() => !inPipe && setOpen((o) => !o)}
        disabled={!!inPipe || add.isPending}
        aria-disabled={!!inPipe}
        className={`act w-full whitespace-nowrap ${inPipe ? 'act-cmp cursor-default' : open ? 'act-cmp' : 'act-mint hover-fill'}`}
      > {/* RECETTE-1 R28 — infobulle au survol retirée (le bouton porte déjà son libellé) */}
        {add.isPending ? 'Ajout…' : inPipe ? CLIENT.fiche.crmDedans : CLIENT.fiche.crmAjouter}
      </button>
      {open && !inPipe && (
        <div data-crm-menu className="absolute right-0 z-30 mt-1 min-w-[190px] rounded-lg border border-line bg-surface-2 p-1 shadow-lg">
          <div className="px-2 py-1 text-[10.5px] uppercase tracking-wide text-txt-dim">Ajouter dans…</div>
          {cols.map((c, i) => (
            <button key={c.key} data-crm-col={c.key} onClick={() => add.mutate(c.key)}
              className="hover-fill flex w-full items-center justify-between gap-2 rounded-md px-2 py-1.5 text-left text-[12.5px] text-txt">
              <span>{c.label}</span>{i === 0 && <span className="text-[10px] text-txt-dim">défaut</span>}
            </button>
          ))}
          {!cols.length && <Squelette lignes={2} className="px-2 py-1.5" />}
        </div>
      )}
      {/* DA-FIX-5c — bloc CRM de la fiche : le MÊME menu « Déplacer vers… » que les cartes du kanban
          (mêmes colonnes, même composant). « ✓ Dans le CRM » reste au-dessus. */}
      {inPipe && state.data?.entry && (
        <div className="mt-1.5">
          <DeplacerMenu columns={cols} currentStatus={state.data.entry.status}
            onMove={(status) => deplacer.mutate(status)} onRetirer={() => retirer.mutate()} />
        </div>
      )}
    </div>
  )
}

/** F7 (M12) — rattacher la parcelle à un PROJET depuis la fiche. Jumeau NEUTRE de « + CRM »
 *  (RETOURS-7 Z1 : même bord/fond, survol plein vert ; plus de mauve, réservé à l'IA). Actif =
 *  accent menthe + nom du/des projet(s). La parcelle atterrit dans « À trier » (proposee).
 *  MULTI-PROJET AUTORISÉ : une parcelle peut nourrir plusieurs projets (dédup par projet côté
 *  serveur). Déjà rattachée → bouton actif (violet plein) + nom du/des projet(s) ; clic = ouvrir. */
// PROJETS-V4 (V5) — FIN DU MODE COLLANT. Le bouton ouvre TOUJOURS un menu listant tous les projets
// actifs (nom + taille du vivier) + « Nouveau projet avec cette parcelle ». Le choix ajoute la parcelle
// aux Retenues du projet et affiche une confirmation brève. RIEN n'est mémorisé (le state `projetCible`
// est supprimé) : la fiche suivante rouvre le même menu complet.
function ProjetButton({ idu }: { idu: string }) {
  const qc = useQueryClient()
  const setOpenProjet = useApp((s) => s.setOpenProjet)
  const [open, setOpen] = useState(false)
  const [confirmMsg, setConfirmMsg] = useState<string | null>(null)
  const attache = useQuery({ queryKey: ['projets-parcelle', idu], queryFn: () => projetsPourParcelle(idu) })
  // RETOURS-12 J2 — le menu lit la liste À L'OUVERTURE, TOUJOURS FRAÎCHE : `staleTime 0` +
  // `refetchOnMount:'always'` → un projet créé juste avant (ailleurs, sans invalidation garantie du
  // cache) apparaît immédiatement, sans rechargement de page (bug « le projet n'apparaissait pas »).
  const projetsQ = useQuery({ queryKey: ['projets'], queryFn: getProjets, enabled: open,
    staleTime: 0, refetchOnMount: 'always' })
  const flash = (nom: string) => { setOpen(false); setConfirmMsg(nom); window.setTimeout(() => setConfirmMsg((m) => (m === nom ? null : m)), 2800) }
  const invalider = () => {
    qc.invalidateQueries({ queryKey: ['projets-parcelle', idu] })
    qc.invalidateQueries({ queryKey: ['projets'] })
    qc.invalidateQueries({ queryKey: ['parcours'] })   // les kanbans concernés se rafraîchissent
  }
  const add = useMutation({
    mutationFn: (pid: number) => ajouterParcelle(pid, idu),
    onSuccess: (_r, pid) => { invalider(); flash((projetsQ.data ?? []).find((x) => x.id === pid)?.nom ?? 'projet') },
  })
  // « Nouveau projet avec cette parcelle » : crée un projet DE ZÉRO puis y ajoute la parcelle (Retenues).
  const nouveau = useMutation({
    mutationFn: async () => {
      const r = await createProjet({ cadrage: {}, de_zero: true })
      await ajouterParcelle(r.projet.id, idu)
      return r.projet
    },
    onSuccess: (p) => { invalider(); flash(p.nom) },
  })
  const attaches = attache.data?.projets ?? []
  const dejaIds = new Set(attaches.map((p) => p.id))
  const inProjet = attaches.length > 0
  const candidats = (projetsQ.data ?? []).filter((p) => p.statut === 'actif')
  const vivier = (p: { counts?: { proposee?: number; retenue?: number; ecartee?: number; a_analyser?: number } }) => {
    const c = p.counts ?? {}
    return (c.proposee ?? 0) + (c.retenue ?? 0) + (c.ecartee ?? 0) + (c.a_analyser ?? 0)
  }

  // RETOURS-11 T3 (03/09) — le menu se ferme au clic ailleurs et à Échap.
  const wrap = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => { if (wrap.current && !wrap.current.contains(e.target as Node)) setOpen(false) }
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('mousedown', onDown); document.addEventListener('keydown', onKey)
    return () => { document.removeEventListener('mousedown', onDown); document.removeEventListener('keydown', onKey) }
  }, [open])
  return (
    <div ref={wrap} className="relative flex-1">
      <button
        data-projet-fiche onClick={() => setOpen((o) => !o)} aria-expanded={open}
        /* ADMIN-1 AD1 — « + Projet » = JAUNE (contour + texte --amber, famille de la chip « Fiche commune »),
           survol plein ambre via .hover-fill-amber ; rattaché = accent ambre (.act-amber-on). Aucun mauve.
           RETOURS-11 T3 — bouton OPAQUE (act-amber-on) tant que le menu est ouvert. */
        className={`act w-full whitespace-nowrap ${inProjet || open ? 'act-amber-on' : 'act-amber hover-fill-amber'}`}
        >
        {inProjet ? (attaches.length > 1 ? `✓ ${attaches.length} projets` : `✓ ${attaches[0].nom}`) : '+ Projet'}
      </button>

      {confirmMsg && (
        <div data-projet-confirm className="absolute bottom-10 left-0 z-30 whitespace-nowrap rounded-md border border-mint/40 bg-mint/10 px-2.5 py-1.5 text-[11px] text-mint">
          ✓ Ajoutée à « {confirmMsg} »
        </div>
      )}

      {open && (
        <div data-projet-fiche-menu className="floating absolute bottom-10 left-0 z-30 w-72 p-2 text-[11px]">
          <p className="label-caps px-1 pb-1 text-txt-dim">Ajouter cette parcelle à…</p>
          {projetsQ.isLoading && <Squelette lignes={2} className="px-1 py-2" />}
          {!projetsQ.isLoading && candidats.length === 0 && (
            <p className="px-1 py-2 leading-snug text-txt-dim">Aucun projet actif — créez-en un ci-dessous.</p>
          )}
          <div className="max-h-56 space-y-0.5 overflow-y-auto">
            {candidats.map((p) => {
              const deja = dejaIds.has(p.id)
              return (
                <button key={p.id} data-projet-fiche-cible={p.id} disabled={add.isPending}
                  onClick={() => (deja ? (setOpenProjet({ id: p.id, nom: p.nom }), setOpen(false)) : add.mutate(p.id))}
                  className="hover-fill-amber flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-txt transition-colors duration-quick"
                  >
                  <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-mint" />
                  <span className="min-w-0 flex-1 truncate">{p.nom}</span>
                  <span className="shrink-0 font-mono text-[10px] text-txt-dim">{deja ? 'déjà ↗' : vivier(p).toLocaleString('fr-FR')}</span>
                </button>
              )
            })}
          </div>
          <div className="my-1.5 h-px bg-line/40" />
          <button data-projet-fiche-nouveau disabled={nouveau.isPending} onClick={() => nouveau.mutate()}
            className="hover-fill-amber flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-mint transition-colors duration-quick"
            >
            <span aria-hidden>＋</span><span className="flex-1">{nouveau.isPending ? 'Création…' : 'Nouveau projet avec cette parcelle'}</span>
          </button>
        </div>
      )}
    </div>
  )
}

// M-Q P2-73 — un SEUL formateur de montants dans l'app (LOI-3). L'ancien `fmtEurCompact()` local (seuil
// k€ à 1 000) divergeait de `fmtEurCompact` (seuil k€ à 10 000) : 5 000 € s'affichait « 5 k€ »
// en fiche, « 5 000 € » au copilote. On bascule sur `fmtEurCompact` (format.ts) — même dessin
// partout. Le copilote l'utilisait déjà correctement.

// RETOURS-11F4 (F8) : EquipementsBadges (piscine/pente) a déménagé dans `reseaux.tsx`.

// FICHE-RANGEMENT-1 Lot 1 (doublon #5) — `prescriptionsInfo` ne dérivait les drapeaux EBC/ER QUE
// pour le bloc Signaux du haut, retiré (doublon du tiroir « Dispositifs et périmètres », qui porte
// EBC/ER avec leur contexte). Plus aucun lecteur → fonction retirée.


/** M11 · SURFACE C — onglet FAISABILITÉ : le résultat, le calcul TRACÉ étape par étape (déterministe,
 *  exact, sourcé), l'explication IA À LA DEMANDE (violet premium, ancrée sur les steps). M60 P1a : la
 *  calculette interactive DÉMÉNAGE dans l'outil « Calculette foncière » (moteur unique) ; la fiche garde
 *  le bilan en LECTURE (capacité, gabarit, SDP) + une PORTE pré-remplie (rendue au pied du tiroir). */
export function Fiche({ idu }: { idu: string }) {
  const select = useApp((s) => s.select)
  // M55-L point 5 — verdict à la demande : mémoire par parcelle pour la session (store).
  const verdictRevele = useApp((s) => !!s.verdictRevele[idu])
  const revelerVerdict = useApp((s) => s.revelerVerdict)
  // M61 P2 — bloc Analyse repliable : déplié par défaut (absent du map), état par parcelle/session.
  const analyseReplie = useApp((s) => !!s.analyseReplie[idu])
  const toggleAnalyseReplie = useApp((s) => s.toggleAnalyseReplie)
  const moduleFiche = useApp((s) => s.moduleFiche)
  const setModule = useApp((s) => s.setModule)
  const setM02Prefill = useApp((s) => s.setM02Prefill)     // M60 P1c — porte Scan patrimoine (SIREN)
  const setCourrierPrefill = useApp((s) => s.setCourrierPrefill)  // CONNEXIONS-2 Lot 3 (KO-5) — Courrier pré-rempli sur la parcelle
  const setParcelPrefill = useApp((s) => s.setParcelPrefill)  // RECETTE-6 (D2) — porte « Remonter le temps »
  const setFlyToF = useApp((s) => s.setFlyTo)
  const setPluPrefillF = useApp((s) => s.setPluPrefill)    // M60 P1c — porte Annuaire PLU (insee+zone)
  const setPluVueF = useApp((s) => s.setPluVue)            // M137-P — porte directe vers une vue de l'outil PLU
  const setCalcPrefill = useApp((s) => s.setCalcPrefill)   // FICHE-RANGEMENT-2 Lot 1 — porte Calculette (§11)
  const modBlock = moduleFiche[idu]
  const sourceLine = useApp((s) => s.sourceLine)
  // EXPORTS-2 lot 8 — `calculette` ne pilote plus le PDF/Argumentaire (retirés) ; le Financier lit
  // le questionnaire persisté. La calculette de la fiche reste (store), sans sélecteur ici.
  // Échap ferme la fiche — sauf si le drawer source est ouvert (il consomme Échap en premier)
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !useApp.getState().sourceLine && !useApp.getState().tool) select(null)
    }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [select])
  void sourceLine
  // M55-O phase 2.1c : `setTab` retiré (0-caller après retrait de goDrawer) — `tab` reste figé à
  // 'synthese' (le seul contenu), gardé pour le garde de rendu.
  const [tab] = useState<'synthese' | Onglet | 'bilan' | 'faisabilite' | 'pourquoi'>('synthese')
  // M19 · migration strangler onglets → tiroirs. MIGRATED = onglets déjà fondus dans la pile
  // Synthèse (leur contenu vit en FicheDrawer). Un clic d'onglet migré ouvre + scrolle le tiroir
  // (au lieu de basculer la vue) ; les onglets non migrés gardent l'ancienne bascule `tab`.
  // M55-L point 10 — accordéon EXCLUSIF des tiroirs (store, par parcelle). openId = tiroir ouvert
  // (null = tout fermé). La valeur du contexte est mémoïsée (identité stable tant que rien ne bouge).
  const tiroirOuvert = useApp((s) => s.ficheTiroir[idu] ?? null)
  const setFicheTiroir = useApp((s) => s.setFicheTiroir)
  const accValue = useMemo(
    () => ({ openId: tiroirOuvert, toggle: (id: string) => setFicheTiroir(idu, tiroirOuvert === id ? null : id) }),
    [tiroirOuvert, idu, setFicheTiroir],
  )
  // M55-O phase 2.1c : `goDrawer`/`pendingScroll` retirés — leurs seuls appelants (liens vers les
  // tiroirs « pourquoi »/« renouvellement ») ont disparu avec l'absorption de ces tiroirs dans le
  // bloc Analyse. Le lien « voir pourquoi » de l'écartée scrolle désormais vers les motifs inline.
  // A6 (post-revue) : recherche DANS la fiche (≠ barre du haut). La loupe de la fiche filtre le
  // CONTENU de la fiche (toutes les lignes tracées, tous onglets), pas le dashboard.
  const [ficheSearchOpen, setFicheSearchOpen] = useState(false)
  const [ficheQuery, setFicheQuery] = useState('')
  // KELFONCIER-FIX-1 (Lot G) — panneau Street View (jamais en pleine page) ; ouvert au clic « Voir la rue ».
  const [streetViewOpen, setStreetViewOpen] = useState(false)
  // RETOURS-8 (R7) — la fiche en ONGLETS : Analyse (la fiche détaillée), Autour (le voisinage isochrone),
  // Actions (CRM · Projet · Courrier · exports) — accès direct aux actions sans faire défiler l'analyse.
  // RETOURS-9 (Q8.1) — onglets de fiche retirés : plus d'état d'onglet, la fiche défile d'un tenant.
  // M61 P1 — panneau IA unifié : 'aucun' = les deux boutons ; 'question' = AskBar pleine largeur ;
  // 'synthese' = panneau Synthèse pleine largeur. Le panneau actif REMPLACE la rangée de boutons
  // (ne se pose plus À CÔTÉ). Synthèse : la mutation vit ICI (persiste au repli) → replier puis
  // rouvrir ne relance AUCUN appel IA. Réinitialisée seulement au changement de parcelle.
  // RETOURS-13 P1 — « Synthèse IA » retirée : l'IA en tête se réduit à « Poser une question »
  // (Copilote / AskBar). Plus de mutation de synthèse (getExplain) portée par la fiche.
  const [iaOuvert, setIaOuvert] = useState<'aucun' | 'question'>('aucun')
  useEffect(() => { setIaOuvert('aucun') }, [idu])  // eslint-disable-line react-hooks/exhaustive-deps
  const { data: f, isLoading, isError, error, refetch } = useQuery({ queryKey: ['fiche', idu], queryFn: () => getFiche(idu) })
  // RECETTE-8 W22 — l'exposition (orientation + pente) remplace la vue mer dans la tête de fiche.
  // Calcul lazy (MNT RGE ALTI + gdaldem ~0,5 s) : la tuile affiche « … » puis la valeur.
  const expo = useQuery({ queryKey: ['exposition', idu], queryFn: () => getParcelExposition(idu),
    enabled: !!idu, staleTime: 6 * 60 * 60 * 1000, retry: false })
  const fq = ficheQuery.trim().toLowerCase()
  // FICHE-RANGEMENT-2 Lot 3 / FICHE-RECHERCHE-1 — « recherche dans tout » : une requête ouvre TOUS
  // les tiroirs (forceOpen via le contexte accordéon), surligne en place ET liste les résultats
  // (effet ci-dessous → `results`), qui pilotent la liste sous la barre.
  const accValueF = useMemo(() => ({ ...accValue, forceOpen: !!fq }), [accValue, fq])
  // FICHE-RECHERCHE-1 — la loupe fonctionne comme une barre de recherche : en tapant, une LISTE de
  // résultats (libellé de la ligne + nom de sa section) apparaît sous la barre ; un clic ouvre la
  // section et scrolle jusqu'à la ligne. Le surlignage EN PLACE (API Custom Highlight, sans mutation
  // du DOM React) est conservé pour le reste. `results` alimente la liste ; `focusKey` le résultat cliqué.
  type FicheResult = { key: string; label: string; section: string; el: HTMLElement }
  const [results, setResults] = useState<FicheResult[]>([])
  const [focusKey, setFocusKey] = useState<string | null>(null)
  useEffect(() => {
    const HL: any = (typeof CSS !== 'undefined' && (CSS as any).highlights) ? (CSS as any).highlights : null
    const q = ficheQuery.trim().toLowerCase()
    if (!HL) { setResults([]); return }
    if (!q) { HL.delete('fiche-search'); HL.delete('fiche-search-focus'); setResults([]); setFocusKey(null); return }
    let raf = 0
    const run = () => {
      const box = document.querySelector('.fiche-v6') as HTMLElement | null
      if (!box) return
      box.querySelectorAll('details:not([open])').forEach((d) => { (d as HTMLDetailsElement).open = true })
      const ranges: Range[] = []
      const res: FicheResult[] = []
      const seen = new Set<HTMLElement>()
      const walker = document.createTreeWalker(box, NodeFilter.SHOW_TEXT, {
        acceptNode: (n) => {
          const p = (n as Text).parentElement
          if (!p || p.closest('input,textarea,script,style,[data-fiche-results]')) return NodeFilter.FILTER_REJECT
          return (n.textContent || '').toLowerCase().includes(q) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT
        },
      })
      let node: Node | null
      while ((node = walker.nextNode())) {
        const low = (node.textContent || '').toLowerCase()
        let i = low.indexOf(q); let matched = false
        while (i !== -1) {
          const r = document.createRange(); r.setStart(node, i); r.setEnd(node, i + q.length)
          ranges.push(r); matched = true
          i = low.indexOf(q, i + q.length)
        }
        if (!matched) continue
        // le RÉSULTAT = la « ligne » qui contient la correspondance (FactRow, filet, porte, item de
        // liste, paragraphe…), dédupliquée ; sa SECTION = le tiroir conteneur (SECTION_LABELS).
        const p = (node as Text).parentElement!
        const lineEl = (p.closest('.f-row, .f-vig, .f-rappel, .porte-outil, li, p, .stat, [data-fiche-perimetre], [data-dispositif-dom], [data-aleas-detail] > div') as HTMLElement) || p
        if (seen.has(lineEl)) continue
        seen.add(lineEl)
        const sid = p.closest('[data-drawer]')?.getAttribute('data-drawer') || ''
        const section = SECTION_LABELS[sid] || 'Analyse LABUSE'
        const label = (lineEl.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 80)
        if (label) res.push({ key: `${sid}#${res.length}#${label.slice(0, 24)}`, label, section, el: lineEl })
      }
      HL.set('fiche-search', new (window as any).Highlight(...ranges))
      setResults(res)
    }
    run()
    // le MutationObserver rattrape les blocs asynchrones (bilan, traducteur…) MAIS ignore les
    // mutations de notre propre liste de résultats (sinon boucle : liste rendue → mutation → run).
    const obs = new MutationObserver((muts) => {
      if (muts.every((m) => (m.target as Element).parentElement?.closest?.('[data-fiche-results]') || (m.target as Element).closest?.('[data-fiche-results]'))) return
      cancelAnimationFrame(raf); raf = requestAnimationFrame(run)
    })
    const box0 = document.querySelector('.fiche-v6')
    if (box0) obs.observe(box0, { childList: true, subtree: true, characterData: true })
    return () => { cancelAnimationFrame(raf); obs.disconnect(); HL.delete('fiche-search'); HL.delete('fiche-search-focus') }
  }, [ficheQuery, f])
  // FICHE-RECHERCHE-1 — clic sur un résultat : ouvre (déjà ouvert via forceOpen) + scrolle la ligne
  // au centre + surligne PLUS FORT la correspondance cliquée (registre `fiche-search-focus`).
  const goToResult = (r: { key: string; el: HTMLElement }) => {
    setFocusKey(r.key)
    r.el.scrollIntoView({ block: 'center', behavior: 'smooth' })
    const HL: any = (typeof CSS !== 'undefined' && (CSS as any).highlights) ? (CSS as any).highlights : null
    const q = ficheQuery.trim().toLowerCase()
    if (!HL || !q) return
    const ranges: Range[] = []
    const w = document.createTreeWalker(r.el, NodeFilter.SHOW_TEXT, {
      acceptNode: (n) => (n.textContent || '').toLowerCase().includes(q) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT,
    })
    let n: Node | null
    while ((n = w.nextNode())) {
      const low = (n.textContent || '').toLowerCase(); let i = low.indexOf(q)
      while (i !== -1) { const rg = document.createRange(); rg.setStart(n, i); rg.setEnd(n, i + q.length); ranges.push(rg); i = low.indexOf(q, i + q.length) }
    }
    HL.set('fiche-search-focus', new (window as any).Highlight(...ranges))
  }

  // Correctif M5 (verdict d'en-tête) : étage 0 prime (bannière écartée + motifs, inchangé) ;
  // sinon un run v2 présent pilote bannière + badge (tier, rang, ×N) ; le statut matrice
  // legacy descend en « historique » dans la section Qualité — plus jamais verdict principal.
  const verdict = f ? verdictMeta(f.statut, f.score_v2?.tier, f.etage0) : null
  const v2Pilote = !!(f?.score_v2 && !f.etage0)
  const verdictEcartee = f ? (f.etage0 || (v2Pilote ? f.score_v2!.tier === 'ecartee' : f.statut === 'ecartee')) : false
  // C1 : motif principal d'écartement, affiché À CÔTÉ du badge (plus de bandeau rouge séparé).
  // Le détail complet reste dans l'onglet « Pourquoi pas » (rien n'est supprimé — R1).
  const hardLines = f?.lines.filter((l) => l.result === 'HARD_EXCLUDE') ?? []
  const ecarteeMotif = hardLines[0] ? layerLabel(hardLines[0].layer) : (f ? 'exclusion légale ou physique — motif détaillé dans l’analyse' : '')  // M129-D : plus de Q/q_score à l'écran
  // M52 L2 (correction #1) : parcelle écartée/déclassée MAIS à signal ×N fort → cadrage « signal
  // brut ». Sans lui, « Déclassée » + « très forte probabilité relative » côte à côte forment une
  // contradiction (famille M48 : un statut mort à côté d'une promesse). Le ×N reste (réel), il
  // devient « signal brut » ; le mot passe en atténué ; un encadré dit que l'écartement PRIME et
  // pourquoi la fréquence est absente. Déclenché hors tiers servables (verdict.tier == null) et
  // seulement si le signal dépasse la moyenne (×N ≥ 2) — l'écartée simple ×1,3 reste sobre.
  const multBase = f?.score_v2?.mult_base ?? null
  const signalEcarte = !!(f?.score_v2 && verdict && verdict.tier == null && (multBase ?? 0) >= 2)
  // PALIERS-1 — le ×N (rapport à la moyenne de la commune) s'affiche À CÔTÉ de Priorité et À
  // suivre SEULEMENT (rang + réglette de position). « Sans signal » n'a pas de ×N à l'écran ;
  // le cas écartée-à-signal-fort (M52, « signal brut ») reste, il est cadré à part.
  const montreMultiple = verdict?.tier === 'priorite' || verdict?.tier === 'a_suivre'
  const motifEcart = verdict?.label.includes(' — ') ? verdict.label.split(' — ').slice(1).join(' — ') : ecarteeMotif
  // M52 L2 — hiérarchie : l'essentiel (droit du sol + économie) s'ouvre à l'arrivée pour un tier
  // SERVABLE (verdict.tier ≠ null : brûlante/chaude/à-creuser/réserve). L'écartée simple n'ouvre
  // M55-L point 10 : `servable` (ex-pilote de defaultOpen des tiroirs Règles/Faisabilité) retiré —
  // l'accordéon est désormais tout fermé à l'ouverture (état initial légal), plus d'auto-ouverture.
  // FICHE-RANGEMENT-2 Lot 1 — `donneesAbsentes` (« Ce que LABUSE ne peut pas savoir ») vivait dans le
  // tiroir client « Données et méthode », retiré (métrologie admin) → calcul supprimé (0-caller).
  const ongletLines = (o: Onglet) => f?.lines.filter((l) => l.onglet === o) ?? []
  // RETOURS-11F4 (F6/F7) : les lignes Risques ET Marché (marcheLines, prix de sortie, socio-éco)
  // vivent dans `RisquesSection` / `MarcheSection`. RECETTE-6 (C5) : les tuiles « Terrain nu » et
  // « Bâti ancien » ayant quitté l'en-tête, `dvfSecteur` n'est plus dérivé ici (le prix du terrain nu
  // vit dans MarcheSection — dont la « Valeur au prix du secteur » rapatriée, cf. C2).
  // Proprio : le signal dominant s'il existe (gérant âgé, procédure…), sinon le type de
  // propriétaire. Jamais d'identité de personne physique (boussole).
  // RETOURS-11F F11 — 🔴 double en-tête : quand un propriétaire moral est connu (ex. « PACIFIC »),
  // une ligne cascade résiduelle « propriétaire inconnu / non renseigné » ne doit PLUS coexister
  // (deux affirmations contradictoires sur le même écran). On masque ces lignes-là dès qu'un PM est su.
  // FICHE-RANGEMENT-3 Lot 4 — les lignes SANS OBJET PAR NATURE n'apprennent rien : quand le
  // propriétaire est une personne physique, les attributs de personne morale (âge du dirigeant,
  // BODACC, dénomination PM) ne s'affichent plus. (PM connu : on masque déjà les résidus « inconnu ».)
  const proprioLines = ongletLines('proprio').filter((l) => {
    const det = l.detail ?? ''
    if (f?.proprietaire_moral && /inconnu|non renseign|non recens/i.test(det)) return false
    if (!f?.proprietaire_moral && /sans objet|dirigeant|personne morale|bodacc/i.test(det)) return false
    return true
  })
  // FICHE-SANS-OBJET-1 — même repli qu'en §4/§5 pour §1 Identité : les vérifications proprio
  // SANS OBJET PAR NATURE d'une personne physique (BODACC, âge dirigeant, dénomination PM) ne sont
  // plus JETÉES en silence (Lot 4 les retirait du flux) — elles reviennent dans un repli « N sans
  // objet », replié par défaut (flux principal inchangé). Côté PM, les résidus « inconnu » masqués
  // sont des CONTRADICTIONS (RETOURS-11F F11), pas des « sans objet » → jamais surfacés.
  const proprioSansObjet = f && !f.proprietaire_moral
    ? ongletLines('proprio').filter((l) => /sans objet|dirigeant|personne morale|bodacc/i.test(l.detail ?? ''))
    : []
  const proprioSignal = proprioLines.filter((l) => (l.weight ?? 0) > 0).sort((a, b) => (b.weight ?? 0) - (a.weight ?? 0))[0]
  const proprioType = f?.proprietaire_moral?.denomination ?? (f?.proprietaire_moral ? 'personne morale' : 'personne physique / non recensé')
  // Règles : zone PLU + SDP résiduelle (données déjà chargées).
  const reglesLines = ongletLines('regles')
  const reglesZone = f?.reglement_plu?.zones?.[0]?.zone
  const reglesSdp = f?.potentiel_transformation?.sdp_residuelle_m2
  // M19 réf. · faisabilité au niveau fiche pour la MICRO-PREUVE fermée (gabarit / logements /
  // charge). MÊME queryKey ['bilan', idu] que Faisabilité/Bilan → cache partagé, zéro requête en +.
  const faisa = useQuery({ queryKey: ['bilan', idu], queryFn: () => getFaisabilite(idu), enabled: !!f })
  const cap = faisa.data?.capacite
  const fo = cap?.fourchette
  // GABARIT-6 (P1) — l'en-tête « Urbanisme » lit la HAUTEUR RÉGLEMENTAIRE SOURCÉE par la MÊME fonction
  // que le tiroir §10 et l'outil (endpoint /outils/gabarit ; MÊME clé react-query que <GabaritLine>, cache
  // partagé, zéro requête en plus). Corrige GABARIT-AUDIT-1 : l'en-tête servait niveaux × 3 m (une
  // estimation d'étages présentée comme un « max »), qui contredisait le règlement cité et le tiroir §10.
  const gab = useQuery({ queryKey: ['gabarit', idu], queryFn: () => getGabarit(idu), retry: false, enabled: !!f })
  // M56-B3/B4 : zone A (agricole) et N (naturelle) = inconstructibles par principe. ATTENTION :
  // « AU » (à urbaniser) EST constructible → on exclut AU (« A » non suivi de « U »). Les zones
  // numérotées (1AU/2AU) commencent par un chiffre → non captées. U reste constructible.
  const nonConstructible = !!(reglesZone && /^(A(?!U)|N)/i.test(reglesZone))
  // RETOURS-11F4 (F5) : logMax/capaciteNulle/logementsTxt (valeur d'en-tête Constructibilité) vivent
  // désormais dans `ConstructibiliteSection` (constructibilite.tsx). Fiche ne les calcule plus.
  // micro-preuve Règles : jauge = part de SDP DÉJÀ consommée (le reste = potentiel).
  const pctConsomme = f?.potentiel_transformation?.pct_consomme
  const reglesArticle = f?.reglement_plu?.zones?.[0]?.articles?.[0]?.reference
  // M55-N point 8 : l'en-tête « Règles d'urbanisme » porte une CONTRAINTE de gabarit (hauteur max)
  // — plus la SDP résiduelle, qui vivait AUSSI dans l'en-tête « Faisabilité » (doublon M55-L P14).
  // Faisabilité garde la SDP ; la SDP reste accessible dans le corps du tiroir (potentiel/faisa).
  // Hauteur absente (faisabilité non calculée) → pas de valeur d'en-tête (le micro-jauge porte
  // déjà zone + article), jamais la SDP ni un doublon du zonage.
  // M56-B3 fix 6 : la colonne droite d'Urbanisme n'est JAMAIS vide. Hauteur connue → « N m max » ;
  // sinon l'ÉTAT de constructibilité de la zone (A/N = non constructible) ; à défaut, le RefDrawer
  // affiche « — » (--txt-faint). Zone A (agricole) et N (naturelle) = inconstructibles par principe.
  // M57-P1 (Q5) : « non constructible » affirmait plus que ce que le code sait (préfixe de zone
  // seul ; STECAL différé, extensions non traitées). Reformulé « constructibilité très limitée »
  // + « i » citant les exceptions non évaluées. Le CALCUL et la règle de zone sont inchangés.
  // faîtage = le « max » réglementaire ; l'égout, si la règle le distingue, part en sous-ligne. Hauteur en
  // prospect (ex. Saint-Denis Ud) → « Non chiffrée ». Le calcul niveaux × étage reste dans la capacité
  // (11 étapes) sous « niveaux constructibles », jamais ici sous « max ».
  const gd = gab.data && gab.data.status === 'ok' ? gab.data : null
  const fmtH = (m: number) => m.toLocaleString('fr-FR')
  const reglesGabarit: ReactNode =
    gd && gd.hauteurStatus !== 'not_integrated' && gd.hauteurReglementaireM != null
      ? (gd.hauteurBase === 'egout'
          ? `${fmtH(gd.hauteurReglementaireM)} m à l'égout`
          : gd.hauteurEgoutM != null
            ? <span style={{ display: 'inline-flex', flexDirection: 'column', alignItems: 'flex-end', lineHeight: 1.15 }}>
                <span>{fmtH(gd.hauteurReglementaireM)} m max</span>
                <span style={{ fontSize: 10, color: 'var(--txt-dim)' }}>égout {fmtH(gd.hauteurEgoutM)} m</span>
              </span>
            : `${fmtH(gd.hauteurReglementaireM)} m max`)
      : gd && gd.hauteurStatus === 'not_integrated'
        ? <span className="t-val absent" style={{ maxWidth: 'none' }}>Non chiffrée (prospect)</span>
        : nonConstructible
          ? <span className="t-val absent" style={{ maxWidth: 'none', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
              constructibilité très limitée
              <Tip side="top" tip="Les zones A et N interdisent la construction neuve à usage d'habitation, sauf exceptions non évaluées par LABUSE : STECAL, extension d'un bâtiment existant, construction agricole. À vérifier au règlement.">
                <span role="button" tabIndex={0} aria-label="Exceptions à la constructibilité" style={{ color: 'var(--txt-ghost)', fontSize: 11, cursor: 'help', flexShrink: 0 }}>ⓘ</span>
              </Tip>
            </span>
          : undefined
  // FICHE-RANGEMENT-1 Lot 1 (doublon #5) — `presc` (drapeaux EBC/ER) alimentait le bloc Signaux du
  // haut, retiré (doublon du tiroir « Dispositifs et périmètres »). Plus de lecteur → const retirée.

  // M56-B5 : conteneur fiche ramené de 440px (M55-L, +10 %) à 400px — sa largeur d'avant.
  // VALEUR UNIQUE ici (un critère, un seul endroit). `max-w-full` garde la fiche dans l'écran
  // aux petites largeurs (aucun débordement horizontal). Ne PAS toucher les tailles de texte
  // ni les paddings (calés en M56-B3 : panneau 14, .gr 10 vertical, .gr partagée).
  return (
    <FicheAccordionCtx.Provider value={accValueF}>
    <aside className="fiche-v6 apparition absolute right-0 top-0 z-10 flex h-full w-[400px] max-w-full flex-col border-l border-line shadow-2xl">
      {/* C1 : le bandeau « écartée » séparé est retiré — le motif s'affiche à côté du badge
          (en-tête, plus bas) et « voir pourquoi » ouvre l'onglet « Pourquoi pas ». Les motifs
          sourcés y restent intégralement (R1 : rien n'est supprimé). */}
      {f?.evenement === 'rouge' && (
        <div className="shrink-0 border-b border-st-ecartee/40 bg-st-ecartee/15 px-5 py-2.5">
          {/* R3 (PJ5) : vocabulaire matrice non thermique — « priorité dossier » (thermique = tier P servi) */}
          <div className="flex items-center gap-2 text-xs font-medium text-st-ecartee">● ÉVÉNEMENT — force « priorité dossier »</div>
          {f.evenement_detail && <div className="mt-1 text-[11px] leading-snug text-st-ecartee/90">{f.evenement_detail}</div>}
        </div>
      )}

      {/* bloc MODULE (doctrine : en tête de fiche, violet) */}
      {modBlock && (
        <div className="shrink-0 border-b border-violet/20 bg-violet/[0.07] px-5 py-3">
          <p className="label-caps text-violet">Module · {modBlock.module}</p>
          <div className="mt-1.5 flex flex-col gap-1">
            {modBlock.lines.map(([k, v]) => (
              <div key={k} className="flex justify-between gap-3 text-[11px]">
                <span className="text-txt-dim">{k}</span>
                <span className="text-right text-txt">{v}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ═══ EN-TÊTE + CARTE VERDICT (DA §4). M56-B3 fix 3 : plus de filet ni de fond distinct
          sous l'en-tête — le panneau est un seul fond continu --bg-1 du haut au pied.
          M56-B3 fix 7 : padding panneau 16→14 (densité). ═══ */}
      {/* RECETTE-8 W12 — le conteneur défilant s'ouvre DÈS la carte d'en-tête : la tête ne « colle »
          plus au défilement (elle était flex-shrink:0, fixe, et recouvrait le contenu qui passait
          dessous). Elle défile désormais AVEC le reste — un seul corps qui défile du haut au pied.
          M56-B6 · DA-FICHE-v6 — EN-TÊTE en CARTE .head (identité + chiffres). */}
      {/* RETOURS-14 P3 — PLUS de pt-1 : le padding-haut du conteneur défilant décalait l'en-tête collé
          (sticky top:0 se cale au bord du padding), laissant un liseré de 4px au-dessus par lequel le
          contenu défilait. Sans padding-haut, l'en-tête colle au BORD du panneau (voir .tete-collee, coins
          hauts carrés = fond plein jusqu'au bord). L'espacement des tuiles reste porté par gap-3. */}
      {/* FICHE-FIX-5 (Lot B) — AUCUNE marge au-dessus de l'en-tête : le bloc collant est opaque
          (--bg-2) jusqu'au bord HAUT du panneau (lui-même --bg-0 opaque), plus de trou par lequel on
          voyait les boutons de carte derrière. (Annule le pt-2.5 flottant de FIX-4 A1.) */}
      <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto overflow-x-clip px-[14px] pb-4">
      {/* RETOURS-13 P7 — EN-TÊTE COLLÉ. SEUL le bloc identité (PARCELLE·commune, IDU, adresse, icônes,
          croix de fermeture) reste collé en haut au défilement — un client ferme la fiche sans remonter.
          Les 6 tuiles NE collent PAS (carte séparée dessous). Le bloc est un ENFANT DIRECT du conteneur
          défilant (sinon il décolle avec son parent) et NON dans une carte `overflow:hidden` (qui
          clipperait le sticky) : fond opaque + ombre pour couvrir ce qui passe dessous. FINITIONS-2 avait
          annulé un sticky qui embarquait AUSSI les tuiles et recouvrait le contenu ; ici, identité seule. */}
      <div className="tete-collee" data-fiche-tete-collee>
          <div className="head-top">
            {/* RETOURS-11 R3 — la colonne gauche pousse (flex:1) pour donner sa largeur à l'adresse,
                qui tient alors sur UNE ligne (tronquée en … si vraiment trop longue, voir .addr). */}
            <div style={{ minWidth: 0, flex: 1 }}>
              <div className="eyebrow">PARCELLE{f?.commune ? ` · ${f.commune.toUpperCase()}` : ''}</div>
              {/* IDU complet (mono) + copier sans cadre, collé à la référence. */}
              <div className="ref" data-fiche-idu>{iduComplet(idu) || 'Absent'}{iduComplet(idu) && <CopyIdu value={iduComplet(idu)} />}</div>
              {/* RETOURS-15 U7 — l'adresse QUITTE cette colonne (réduite par les logos + cloche à
                  droite : elle y wrappait « à la moitié » alors que la pleine largeur est libre
                  dessous) → rangée .addr-row pleine largeur sous le head-top. */}
              {/* RETOURS-8 (R7) — le lien « Pages jaunes » quitte l'adresse : il remonte en tête,
                  à côté de l'IDU, dans le trio Maps · Cadastre · Pages jaunes (voir .hbtns). */}
            </div>
            <div className="hbtns">
              {/* RETOURS-11 F1 (03/09) — trois boutons-LOGOS (Cadastre Géoportail · Pages Jaunes · Google
                  Maps) À CÔTÉ de la cloche, remplaçant les trois grandes pastilles sur deux lignes. Logos
                  publics stockés en local (SVG inline, aucune requête externe), nom complet au survol. Les
                  URL restent construites par les fonctions pures testées (liensExternes.ts). */}
              {f && (() => {
                const pj = pagesJaunes(f.adresse, f.commune)
                return (
                  <>
                    {f.coords && (
                      <a data-cadastre-link className="hbtn" target="_blank" rel="noreferrer noopener"
                        href={cadastreGeoportailUrl(f.coords)} aria-label="Cadastre Géoportail">
                        <LogoCadastre />
                      </a>
                    )}
                    {pj.url && (
                      <a data-fiche-pj data-pj-commune-seule={pj.commune_seule || undefined} className="hbtn"
                        target="_blank" rel="noreferrer noopener" href={pj.url}
                        aria-label={pj.commune_seule ? 'Pages Jaunes — commune' : 'Pages Jaunes'}>
                        <LogoPagesJaunes />
                      </a>
                    )}
                    {f.coords && (
                      <a data-maps-link className="hbtn" target="_blank" rel="noreferrer noopener"
                        href={googleMapsUrl(f.coords)} aria-label="Google Maps (épingle sur la parcelle)">
                        <LogoGoogleMaps />
                      </a>
                    )}
                    {/* KELFONCIER-FIX-1 (Lot G) — « Voir la rue » : n'apparaît QUE si le serveur sert
                        un embed Street View (clé GOOGLE_MAPS_EMBED_KEY posée) ; sinon masqué, sans erreur.
                        Ouvre un panneau (jamais en pleine page), centré sur le centroïde de la parcelle. */}
                    {f.street_view?.embed_url && (
                      <button data-street-view-btn className="hbtn" onClick={() => setStreetViewOpen((o) => !o)}
                        style={streetViewOpen ? { borderColor: 'var(--mint)', color: 'var(--mint)' } : undefined}
                        aria-label="Voir la rue (Street View)" title="Voir la rue">
                        <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
                          <circle cx="12" cy="8" r="3" /><path d="M6 20c0-3 3-5 6-5s6 2 6 5" /><path d="M3 12h2M19 12h2" />
                        </svg>
                      </button>
                    )}
                  </>
                )
              })()}
              <WatchButton idu={idu} />
              <button className="hbtn" onClick={() => setFicheSearchOpen((o) => { if (o) setFicheQuery(''); return !o })}
                style={ficheSearchOpen ? { borderColor: 'var(--mint)', color: 'var(--mint)' } : undefined}
                aria-label="Rechercher dans cette fiche">
                <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"><circle cx="11" cy="11" r="6" /><path d="m20 20-3.5-3.5" /></svg>
              </button>
              <button className="hbtn" onClick={() => select(null)} aria-label="Fermer la fiche">
                <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"><path d="M18 6 6 18" /><path d="m6 6 12 12" /></svg>
              </button>
            </div>
          </div>

          {/* KELFONCIER-FIX-1 (Lot G) — panneau Street View INLINE (jamais en pleine page) : l'embed
              Google Maps (mode panorama) centré sur le centroïde de la parcelle. Rendu seulement quand
              ouvert ET que le serveur a servi une URL (clé posée). */}
          {streetViewOpen && f?.street_view?.embed_url && (
            <div data-street-view-panel className="mt-2 overflow-hidden rounded-lg border border-line-2 bg-surface-2">
              <div className="flex items-center justify-between px-3 py-1.5">
                <span className="label-caps text-txt-mut">Vue de la rue</span>
                <button className="hbtn" onClick={() => setStreetViewOpen(false)} aria-label="Fermer la vue de la rue">
                  <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"><path d="M18 6 6 18" /><path d="m6 6 12 12" /></svg>
                </button>
              </div>
              <iframe data-street-view-iframe title="Vue de la rue (Google Street View)"
                src={f.street_view.embed_url} loading="lazy"
                referrerPolicy="no-referrer-when-downgrade" allowFullScreen
                className="block h-[220px] w-full border-0" />
            </div>
          )}

          {/* RETOURS-15 U7 — ADRESSE en rangée PLEINE LARGEUR (moins l'icône copier) : une ligne
              tant que ça tient, ellipse avec l'adresse complète au survol (title) sinon. Elle ne
              partage plus sa largeur avec les logos/cloche. M61 P5 — copiable (user-select). */}
          <div className={`addr addr-row${f?.secteur ? ' has-sect' : ''}`} data-fiche-adresse>
            <span style={{ userSelect: 'text', minWidth: 0 }}>{f?.adresse ?? CLIENT.fiche.adresseAbsente}</span>
            {f?.adresse && <CopyIdu value={f.adresse} aria="Copier l’adresse" titre="Copier l’adresse" okTitre="Adresse copiée" dataAttr="adresse" />}
            {!f?.adresse && (
              // RECETTE-8 W11 — « i » fonctionnel icône-seule → `garder` (sinon bulle muette, S10).
              <Tip side="top" tip={CLIENT.fiche.adresseAbsenteInfo} garder>
                <span data-adresse-absente-i role="button" tabIndex={0} aria-label="Pourquoi l’adresse manque"
                  style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 14, height: 14, borderRadius: 9999, border: '1px solid var(--line-3)', color: 'var(--txt-ghost)', fontSize: 9, fontWeight: 700, lineHeight: 1, cursor: 'help', verticalAlign: 'middle' }}>i</span>
              </Tip>
            )}
          </div>
          {/* GEOPF-3 — SECTEUR : lieu-dit BD NYME le plus proche (rayon borné), sous l'adresse. Rien si aucun.
              KELFONCIER-FIX-2 (Lot A) — RENTRÉ DANS LA CARTE : même padding horizontal (14px) que l'adresse
              via `.sect-line` (avant : `.addr` nu, sans padding → la ligne débordait à gauche, hors carte).
              Libellé gris (--txt-dim = maquette --mut), nom en clair (--txt-hi = maquette --txt), comme .sect. */}
          {f?.secteur && (
            <div className="sect-line" data-fiche-secteur>
              Secteur : <b>{f.secteur}</b>
            </div>
          )}
      </div>{/* /.tete-collee — RETOURS-13 P7 : bloc identité COLLÉ (les 6 tuiles ne collent pas) */}

      {/* RETOURS-13 P7 — les 6 tuiles vivent dans leur PROPRE carte, sous l'en-tête collé : elles
          DÉFILENT (elles ne collent pas). `shrink-0` OBLIGATOIRE : cette carte est un enfant flex
          DIRECT du conteneur défilant et son `overflow:hidden` ramène sa taille mini flex à 0 → sans
          shrink-0 elle s'écrase à 1px et clippe les 6 tuiles (l'ancien code l'enveloppait dans un div
          sans overflow, ce qui l'en protégeait). */}
      <div className="head shrink-0" data-fiche-tuiles style={{ marginTop: 6 }}>
        {/* RETOURS-11 F1 — les trois accès (Cadastre · Pages Jaunes · Google Maps) ont MONTÉ dans
            l'en-tête à côté de la cloche, en boutons-logos (voir .hbtns ci-dessus). Les anciennes
            pastilles pleines sur deux lignes sont retirées. */}

        {/* FICHE-TUILES-OUTILS-1 Lot 1 — LE BANDEAU DE SIX CHIFFRES est REMIS sous l'en-tête (il avait
            été dissous en FICHE-RANGEMENT-2 Lot 1 ; à l'usage, la vue d'ensemble manquait avec un
            accordéon tout replié). Style d'origine (data-bandeau-chiffres, « i » de source par tuile).
            CHANGEMENT : « Taxe foncière » → « Risques » (compteur + niveau, comme le badge de §5).
            DOUBLON ASSUMÉ : ces six valeurs vivent AUSSI dans leur section — c'est un SOMMAIRE, pas
            une duplication. NE PAS les retirer lors d'un audit « une notion, un endroit ». */}
        {f && (() => {
          const nf = (n: number) => n.toLocaleString('fr-FR')
          const z = (reglesZone ?? '').toUpperCase()
          const zoneSous = !z ? undefined
            : z.startsWith('AU') ? 'à urbaniser' : z.startsWith('U') ? 'constructible'
            : z.startsWith('A') ? 'agricole' : z.startsWith('N') ? 'naturelle' : undefined
          const pente = f.terrain?.pente_moy_deg
          const penteSous = pente == null ? undefined
            : pente < 5 ? 'plat' : pente < 15 ? 'modérée' : pente < 30 ? 'forte' : 'très forte'
          // Risques — compteur (vigilances de l'onglet risques) + niveau, comme le badge de §5.
          const vigils = f.lines.filter((l) => l.onglet === 'risques' && (l.result === 'SOFT_FLAG' || l.result === 'HARD_EXCLUDE'))
          const aleas = f.aleas?.liste ?? []
          const risqueNiveau = aleas.some((a) => a.redhibitoire) ? 'aléa rédhibitoire'
            : aleas.some((a) => /fort|élev/i.test(a.niveau ?? '')) ? 'aléa fort'
            : vigils.length > 0 ? `vigilance${vigils.length > 1 ? 's' : ''}` : 'rien à signaler'
          type Tuile = { l: string; v: string; s?: string; i?: string; vide?: boolean }
          const tuiles: Tuile[] = [
            { l: 'Surface', v: f.surface_m2 != null ? fmtM2(f.surface_m2) : '—', vide: f.surface_m2 == null,
              i: 'Contenance cadastrale de la parcelle (DGFiP).' },
            { l: 'Zone', v: reglesZone ?? 'Non publié au GPU', s: zoneSous, vide: reglesZone == null,
              i: 'Zone du PLU au point de la parcelle (règlement communal, archive GPU). « Non publié au GPU » : la commune n’a pas déposé de document opposable.' },
            { l: 'Pente', v: pente != null ? `${nf(pente)} °` : '—', s: penteSous, vide: pente == null,
              i: 'Pente moyenne du terrain, calculée sur le modèle de relief RGE ALTI (IGN). À La Réunion elle commande le coût de terrassement autant que la constructibilité. « — » : relief non disponible sur la parcelle.' },
            (() => {
              const e = expo.data
              const orient = e?.orientation
              const v = expo.isLoading ? '…' : (orient && orient !== 'plat' ? orient : orient === 'plat' ? 'Plat' : '—')
              // FICHE-FIX-2 P6 — la PENTE vit UNE fois (tuile « Pente », emprise de la parcelle,
              // 13,8°). L'Exposition ne montre PLUS sa propre pente (fenêtre versant 200 m = 17,4°, un
              // autre périmètre) : elle ne garde que l'orientation (l'azimut, qui a besoin du contexte
              // du versant, reste au tiroir Terrain). Fin des deux pentes côte à côte dans l'en-tête (§1.2).
              const s = orient === 'plat' ? 'terrain quasi plat'
                : expo.isLoading ? 'calcul en cours'
                : !orient ? 'relief non disponible' : 'versant (RGE ALTI)'
              return { l: 'Exposition', v, s, vide: !orient,
                i: 'Orientation du versant de la parcelle (Nord, Sud-Est…), calculée sur le modèle d’altitude RGE ALTI (IGN) dans une fenêtre autour du centroïde. La PENTE affichée est celle de l’emprise (tuile « Pente ») — l’exposition n’en montre pas une seconde. Remplace la « vue mer » (abandonnée). « — » : relief non disponible sur la parcelle.' } as Tuile
            })(),
            { l: 'Risques', v: vigils.length > 0 ? `${vigils.length}` : '—', s: risqueNiveau, vide: vigils.length === 0,
              i: 'Vigilances évaluées sur la parcelle (aléas, servitudes, sols…) — compteur et niveau, comme le badge de §5. Le détail est dans « Risques et environnement ».' },
            { l: 'SDP restante', v: reglesSdp != null && reglesSdp > 0 ? `${fmtInt(reglesSdp)} m²` : '—',
              s: reglesSdp != null && reglesSdp > 0 ? undefined : (reglesZone && /^(A|N)/i.test(reglesZone) ? 'zone non constructible' : 'pas de potentiel résiduel'),
              vide: !(reglesSdp != null && reglesSdp > 0),
              i: 'Surface de plancher que le PLU autorise ENCORE sur la parcelle (potentiel résiduel). « — » : zone non constructible ou plus de potentiel.' },
          ]
          return (
            <div className="stats" data-bandeau-chiffres>
              {tuiles.map((c) => (
                <div className="stat" key={c.l}>
                  <div className="stat-l">
                    {c.l.toUpperCase()}
                    {c.i && (
                      <Tip tip={c.i} garder side="bottom">
                        <span role="button" tabIndex={0} aria-label={`Source : ${c.l}`}
                          className="flex h-[12px] w-[12px] shrink-0 items-center justify-center rounded-full border border-line-2 text-[7px] font-bold leading-none text-txt-dim hover:border-mint hover:text-mint">i</span>
                      </Tip>
                    )}
                  </div>
                  <div className={`stat-v${c.vide ? ' vide' : ''}`}>{c.v}</div>
                  {c.s && <div className="stat-s">{c.s}</div>}
                </div>
              ))}
            </div>
          )
        })()}
        </div>{/* /.head — carte des 6 tuiles (défile ; l'en-tête identité au-dessus reste collé, P7) */}
        {/* RETOURS-9 (Q8.1) — ONGLETS Analyse · Autour · Actions RETIRÉS : retour à la fiche UNIQUE qui
            défile. « Autour » est un tiroir de la fiche (et existe dans les outils) ; « Actions » (CRM/
            Projet/exports) vit déjà en pied de fiche. Plus rien à choisir : tout défile d'un seul tenant. */}

      {/* M68 P1a — DÉFILEMENT UNIQUE : le bloc Analyse (CTA + carte verdict), la bannière RNU, les
          signaux, puis les tiroirs / actions / exports / mention légale vivent tous DANS ce conteneur
          `overflow-y-auto flex-1`. La fiche défile donc jusqu'au pied EN TOUTE circonstance (bloc
          Analyse absent / déplié / replié, synthèse ouverte, n'importe quel tiroir ouvert). Avant M68,
          le bloc Analyse était dans le wrapper flex-shrink:0 et affamait ce conteneur (cf. RAPPORT_M68).
          RETOURS-9 (Q8.1) — plus d'onglet : ce conteneur est le SEUL corps défilant de la fiche.
          RECETTE-8 W12 — ce conteneur est désormais OUVERT plus haut (juste avant la carte d'en-tête)
          pour que la tête défile avec le reste ; ici on ne rouvre plus rien. */}
        {/* wrapper NON-flex : conserve l'espacement interne d'origine du bloc Analyse (marges inline). */}
        <div>

        {/* M55-L point 5 — VERDICT À LA DEMANDE. À l'ouverture (verdict non encore demandé pour
            cette parcelle dans la session), un BOUTON vert remplace le bloc verdict — l'avis n'est
            jamais imposé à qui veut d'abord des informations. C'est le SEUL élément vert de ce
            niveau. Au clic, le bloc verdict complet se déploie (mémorisé par parcelle, session).
            Vaut aussi en mode factuel (le bouton apparaît pareillement : rien n'est imposé, tout
            est accessible). Les PDF gardent le verdict sans condition (rail back inchangé). */}
        {/* RETOURS-13 P1 — EN-TÊTE À DEUX BOUTONS (« Synthèse IA » retirée). Même rangée (.ia = flex),
            même hauteur (Bouton 32px) : « Demander à LABUSE d'analyser la parcelle → » (principal,
            plein, vert) + « Poser une question » (secondaire, Copilote). L'analyse RÉVÈLE le verdict
            SERVI : f.analyse_labuse vient de getFiche(idu) = `/parcels/{idu}?source=${SOURCE}`, où
            SOURCE = VITE_RUN_LABEL injecté depuis config/served_run.txt (run servi). Aucune version
            de scoring codée en dur : la bascule q_v11→q_v15 change le run servi, la fiche suit sans
            toucher au code. « Poser une question » déploie le Copilote (AskBar) juste dessous. */}
        {f && (
          <>
            {iaOuvert !== 'question' && (
              <div className="ia">
                {verdict && !verdictRevele && (
                  <Bouton data-demander-analyse niveau="primaire" ton="vert" className="flex-1" onClick={() => revelerVerdict(idu)}>
                    {CLIENT.fiche.demanderAnalyse}
                  </Bouton>
                )}
                <Bouton onClick={() => setIaOuvert('question')} data-askbar-open niveau="secondaire" ton="ia" className="flex-1">
                  <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}><path d="M20 4H4v13h5l3 3 3-3h2z" /></svg>
                  Poser une question
                </Bouton>
              </div>
            )}
            {iaOuvert === 'question' && <AskBar idu={idu} zone={null} startOpen onClose={() => setIaOuvert('aucun')} />}
          </>
        )}
        {/* ══════ ANALYSE-1 — CARTE « ANALYSE LABUSE » (nouveau moteur : Score LABUSE + Signal) ══════
            À la demande (verdictRevele). La BANDE en toutes lettres (mot + couleur franche, dominante),
            le Signal de mutation en BADGE SECONDAIRE, et les contributions FR EN ENTIER (ce qui monte /
            ce qui baisse). Aucun chiffre brut de score ni de probabilité. « Analyse incomplète » montre
            sa cause. Le score ne s'affiche QUE sur la fiche et dans l'Analyse (mandat §4). */}
        {f?.analyse_labuse?.bande && verdictRevele && (
          // RETOURS-14 P1 — carte extraite. `version={SOURCE}` = le run servi (config/served_run.txt,
          // injecté au build), JAMAIS une version codée en dur ; la fiche a lu ce même run via
          // getFiche(idu) = `/parcels/{idu}?source=${SOURCE}` (cf. commentaire en-tête à deux boutons).
          <AnalyseLabuseCard analyse={f.analyse_labuse!} version={SOURCE} />
        )}
        {/* CARTE VERDICT (ancien moteur, run servi) — teintée selon le tier. ANALYSE-1 : MASQUÉE dès que
            le nouveau moteur porte un verdict (`analyse_labuse`), pour qu'aucun ancien mot (Priorité / À
            suivre / Sans signal / Écartée) n'apparaisse sur la fiche. La réglette « ×N vs moyenne » et la
            fréquence par tier (ancien moteur) tombent avec elle — à re-brancher sur le nouveau moteur si
            Vic le souhaite (hors mandat ANALYSE-1). */}
        {f && verdict && verdictRevele && !f.analyse_labuse && (
          // M61 P2 — le bloc Analyse est un TIROIR : en-tête cliquable (Analyse LABUSE + verdict au
          // repli + chevron), corps repliable. État par parcelle (analyseReplie), déplié par défaut,
          // INDÉPENDANT de l'accordéon exclusif des 7 tiroirs (aucun autre tiroir ne se ferme).
          <div data-verdict-card style={{ marginTop: 8, background: `${verdict.color}12`, border: `1px solid ${verdict.color}59`, borderRadius: 6, overflow: 'hidden' }}>
            <button data-analyse-toggle onClick={() => toggleAnalyseReplie(idu)} aria-expanded={!analyseReplie}
              style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, background: 'none', border: 0, cursor: 'pointer', padding: '13px 16px', textAlign: 'left' }}>
              <span style={{ display: 'flex', alignItems: 'baseline', gap: 9, minWidth: 0, flexWrap: 'wrap' }}>
                <span style={{ fontSize: 10, letterSpacing: 1.4, color: 'var(--lab)', textTransform: 'uppercase' }}>Analyse LABUSE</span>
                {analyseReplie && <span data-analyse-verdict style={{ fontSize: 14, fontWeight: 600, color: verdict.color }}>{verdict.label}</span>}
              </span>
              <span className="chev" style={{ color: 'var(--txt-faint)', flexShrink: 0, fontSize: 14, lineHeight: 1 }}>{analyseReplie ? '›' : '⌃'}</span>
            </button>
            {!analyseReplie && (
            <div data-analyse-corps style={{ padding: '0 16px 15px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
              <div style={{ minWidth: 0 }}>
                <p style={{ margin: 0, fontSize: 10, letterSpacing: 1.4, color: 'var(--lab)' }}>VERDICT LABUSE</p>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 9, marginTop: 5, flexWrap: 'wrap' }}>
                  <span data-badge-verdict style={{ fontSize: 23, fontWeight: 500, color: verdict.color, lineHeight: 1 }}>{verdict.label}</span>
                  {v2Pilote && f.score_v2?.rang != null && montreMultiple && (
                    <span style={{ fontSize: 12, color: 'var(--lab)' }}>rang {f.score_v2.rang}</span>
                  )}
                  {verdictEcartee && (
                    <span data-ecartee-motif style={{ fontSize: 12, color: 'var(--lab)' }}>
                      · {ecarteeMotif} <button onClick={() => document.querySelector('[data-analyse-motifs]')?.scrollIntoView({ behavior: 'smooth', block: 'center' })} style={{ background: 'none', border: 0, padding: 0, color: '#E8695A', textDecoration: 'underline', cursor: 'pointer', fontSize: 12 }}>{CLIENT.fiche.ecarteeVoir}</button>
                    </span>
                  )}
                </div>
              </div>
              {f.score_v2 != null && (
                <div style={{ textAlign: 'right', flexShrink: 0 }}>
                  {/* FICHE-RANGEMENT-1 Lot 1 (doublon #7) — la « Probabilité de vente sous 1 an » (fraction)
                      vit UNE fois, dans le bloc canonique ScoreV2Block plus bas (qui seul porte percentile,
                      rang et les badges copro/veille/événement). On retire l'écho de l'en-tête du verdict ;
                      le mot d'échelle (unique) reste ici, à côté du verdict. */}
                  {/* mot d'échelle : en couleur du tier quand servable ; ATTÉNUÉ quand écartée à
                      signal fort (le mot ne doit pas faire promesse à côté d'un statut mort). */}
                  {f.score_v2.verbal?.mot && (
                    <p style={{ margin: '2px 0 0', fontSize: 11.5, fontWeight: 600, color: signalEcarte ? '#8C7468' : verdict.color }}>
                      {signalEcarte ? <>{f.score_v2.verbal.mot} <span style={{ fontWeight: 500, color: 'var(--lab)' }}>· écartée</span></> : f.score_v2.verbal.mot}
                    </p>
                  )}
                </div>
              )}
            </div>
            {/* M52 Lot 1 — réglette de position (×N, échelle LOG — arbitrage Vic L2, plus le
                percentile rang), fréquence mesurée par tier, « pourquoi ce score ». Présentation ;
                aucun calcul. Pas de note /100, pas d'étoiles (doctrine). */}
            {f.score_v2 && (
              <div style={{ margin: '12px 0 0' }}>
                {/* PALIERS-1 — la réglette de position (×N vs moyenne commune) : Priorité / À suivre
                    seulement (+ le cas écartée-signal-brut). « Sans signal » ne l'affiche pas. */}
                {f.score_v2.verbal?.reglette_pct != null && (montreMultiple || signalEcarte) && (
                  <>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9.5, color: 'var(--txt-off)', marginBottom: 3 }}>
                      <span>moyenne</span><span>très forte</span>
                    </div>
                    <div style={{ position: 'relative', height: 7, borderRadius: 4, background: 'linear-gradient(90deg,#3a4d44,#6fb3d9 35%,#ffc266 70%,#ff7a59)' }}>
                      <i data-reglette style={{ position: 'absolute', top: -3, left: `${f.score_v2.verbal.reglette_pct}%`, width: 3, height: 13, background: '#fff', borderRadius: 4, boxShadow: '0 0 5px #000' }} />
                    </div>
                  </>
                )}
                {/* écartée/déclassée à signal fort : l'écartement PRIME — dit pourquoi la fréquence
                    est absente (doctrine étage 0 M5). Bordure « terre éteinte », pas de menthe. */}
                {signalEcarte && (
                  <p data-signal-ecarte style={{ margin: '9px 0 0', fontSize: 11, color: '#b9a898', borderLeft: '3px solid #8C7468', paddingLeft: 8 }}>
                    La parcelle porte {(multBase ?? 0) >= 4 ? 'un signal fort' : 'un signal au-dessus de la moyenne'}{f.score_v2.fraction ? <> ({f.score_v2.fraction} sous 1 an)</> : null} <b>mais elle est écartée</b>{motifEcart ? <> : {motifEcart.toLowerCase()}</> : null} — l’écartement prime. La fréquence par tier ne s’affiche pas.
                    <span aria-label="Le signal est réel ; l’écartement (étage 0) prime sur le signal (doctrine M5). On montre le signal ET la raison de l’écart." style={{ marginLeft: 4, cursor: 'help', borderBottom: '1px dotted #5f7568' }}>ⓘ</span>
                  </p>
                )}
                {f.score_v2.verbal?.frequence && (
                  <p data-freq style={{ margin: '9px 0 0', fontSize: 11, color: 'var(--txt-dim)', borderLeft: '3px solid #5fd0a8', paddingLeft: 8 }}>
                    {f.score_v2.verbal.frequence.sous_moyenne
                      ? <>Fréquence de vente en dessous de la moyenne de l’île (à horizon plus lointain).</>
                      : <>Parmi les parcelles de ce niveau, environ <b>{f.score_v2.verbal.frequence.sur_100} sur 100</b> ont été vendues en {f.score_v2.verbal.frequence.fenetre}, contre ~{f.score_v2.verbal.frequence.base_sur_100} sur 100 en moyenne.</>}
                    <span aria-label={f.score_v2.verbal.frequence.source_dite} style={{ marginLeft: 4, cursor: 'help', borderBottom: '1px dotted #5f7568' }}>ⓘ</span>
                  </p>
                )}
                {/* FICHE-RANGEMENT-1 Lot 1 (doublon #6) — « Pourquoi ce score » vivait DEUX fois dans la
                    même carte Analyse (ici en inline + dans ScoreV2Block juste dessous). On garde le bloc
                    canonique ScoreV2Block (self-fetch /v2/score, versionné, porte percentile/rang/badges)
                    et on retire l'écho inline. Réglette et fréquence (non dupliquées) restent au-dessus. */}
              </div>
            )}
            {/* chips d'arguments — M61 P3 : les pastilles « constructible {zone} » et « N vigilance(s) »
                sont RETIRÉES (doublon au mot près des tiroirs Urbanisme et Risques). Reste le seul
                signal qui n'existe nulle part ailleurs à ce niveau : le signal propriétaire (violet). */}
            {proprioSignal && (
              <div style={{ margin: '13px 0 0', paddingTop: 12, borderTop: `1px solid ${verdict.color}33`, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                <span style={{ fontSize: 11, background: '#1c1630', color: '#c9b6f2', border: '1px solid #3d3159', borderRadius: 6, padding: '3px 9px' }}>{fmtLibelleBrut(proprioSignal.detail).replace(/\s*—.*$/, '').slice(0, 34)}</span>
              </div>
            )}
            {/* DENSIFIER-PLI (PISCINES-2 Lot B) — le badge « Densifier l'existant — rang N/M » lisait le
                précalcul figé `parcel_renouvellement` (plus aucun écran ne le lit). Le potentiel de
                densification s'obtient maintenant via le filtre « Déjà bâti » + « SDP restante » (porte
                ci-dessus), sur le run servi. Badge retiré. */}

            {/* ═══ M55-O phase 2.1b — BLOC ANALYSE : TOUT l'avis LABUSE rassemblé (déployé au clic) ═══
                Aujourd'hui éparpillé (P dans « Les données », motifs dans « Pourquoi pas ? »,
                renouvellement et éligibilité en tiroirs) → réuni ici. Aucune donnée nouvelle. */}
            {/* P (probabilité de mutation) + « Pourquoi ce score » — déménagé du tiroir Les données. */}
            <div data-analyse-p style={{ marginTop: 13, paddingTop: 12, borderTop: `1px solid ${verdict.color}33` }}>
              <ScoreV2Block idu={idu} />
            </div>
            {/* M61 P4 — la section « RENOUVELLEMENT — POURQUOI CE RANG » a été REGROUPÉE dans le
                dépliant « Pourquoi ce rang » juste sous le rang (voir data-renouv-pourquoi ci-dessus). */}
            {/* Motifs rédhibitoires (« Pourquoi pas ? ») — tiroir entier absorbé. */}
            {(verdictEcartee || f.lines.some((l) => l.result === 'SOFT_FLAG')) && (
              <div data-analyse-motifs style={{ marginTop: 12, paddingTop: 12, borderTop: `1px solid ${verdict.color}33` }}>
                <p style={{ margin: '0 0 8px', fontSize: 10, letterSpacing: 0.8, color: 'var(--lab)', textTransform: 'uppercase' }}>Pourquoi pas ?</p>
                <PourquoiPasTab idu={idu} />
              </div>
            )}
            {/* Vérifications d'éligibilité — ✓ N passées (contrôles PASS du tiroir Urbanisme, repliés). */}
            <EligibiliteReplie lines={reglesLines} color={verdict.color} />
            </div>
            )}
          </div>
        )}

        {/* M65 P1 — le BANDEAU D'ATTENTION ambre « Marché peu actif à … » (ancien .band replié
            sur f.qualite_commune.degradee) est SUPPRIMÉ. La donnée n'est pas perdue : le tiroir
            « Qualité de la mesure · <commune> » (data-qualite-commune, plus bas) porte le détail
            complet (RR intra, échantillon, base %, libellé, source) dès que qualite_commune existe. */}

        {/* MANDAT RNU (B3) : bannière commune sans document local — étiquetage OBLIGATOIRE,
            flag général (config/rnu_communes.yaml). Jamais une affirmation de constructibilité ;
            la PAU est une ESTIMATION (wording validé Vic, servi par l'API — jamais reformulé ici). */}
        {f?.rnu && (
          <div data-rnu-banner style={{ marginTop: 10, background: '#2a2213', border: '1px solid #4a3c20', borderRadius: 6, padding: '9px 12px' }}>
            <p style={{ margin: 0, fontSize: 11.5, fontWeight: 600, color: '#e6b15c' }}>⚠ {f.rnu.libelle}</p>
            <p style={{ margin: '4px 0 0', fontSize: 10.5, lineHeight: 1.5, color: '#c9b98e' }}>
              {f.rnu.detail}
            </p>
            {f.rnu.dans_pau != null && (
              <p data-rnu-pau style={{ margin: '5px 0 0', fontSize: 10.5, lineHeight: 1.5, color: '#e6b15c' }}>
                {f.rnu.dans_pau ? 'Parcelle DANS l’enveloppe urbanisée estimée.' : 'Parcelle HORS de l’enveloppe urbanisée estimée.'}
                <span style={{ color: '#c9b98e' }}> {f.rnu.avertissement_pau}</span>
              </p>
            )}
          </div>
        )}

        {/* M29 (b)/(b) — signaux mérite/héritage (#9) et acquérabilité (#11) : information
            seule, libellés factuels arbitrés, AUCUN effet de classement. Champs absents = rien. */}
        {(f as any)?.entree_tete?.libelle && (
          <p data-entree-tete style={{ margin: '8px 0 0', fontSize: 11, color: '#8FA69A' }}>
            {(f as any).entree_tete.libelle} <span style={{ color: '#5a6b62' }}>({(f as any).entree_tete.etiquette})</span>
          </p>
        )}
        {(f as any)?.acquerabilite?.libelle && (
          <p data-acquerabilite style={{ margin: '4px 0 0', fontSize: 11, color: '#8FA69A' }}>
            assemblage : {(f as any).acquerabilite.libelle}
          </p>
        )}

        {/* M56-B4 point 2 — les drapeaux EBC / ER (prescriptions PLU, information seule) ne
            flottent plus dans le flux d'ACTIONS : ils descendent sous un micro-label « SIGNAUX »,
            juste avant LE TERRAIN (rendu plus bas). */}
        </div>{/* /wrapper non-flex du bloc Analyse (M68 P1a) — la suite défile aussi */}

      {ficheSearchOpen && (
        <div className="shrink-0 border-b border-line bg-surface-2">
          <div className="flex items-center gap-2 px-5 py-2">
            <input autoFocus data-fiche-search value={ficheQuery} onChange={(e) => setFicheQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Escape' && (setFicheQuery(''), setFicheSearchOpen(false))}
              placeholder="Chercher dans cette fiche (risque, réseau, ICPE…)"
              className="min-w-0 flex-1 rounded-md border border-line-2 bg-surface-3 px-2.5 py-1 text-xs text-txt placeholder:text-txt-dim focus:border-mint focus:outline-none" />
            {/* FICHE-RECHERCHE-1 — accord correct (« 1 résultat surligné ») ; « aucun résultat »
                (jamais un compteur à zéro). Le compteur = le nombre de LIGNES trouvées (la liste). */}
            {fq && <span data-fiche-search-count className="shrink-0 text-[11px] text-txt-mut">{results.length === 0
              ? 'aucun résultat'
              : `${results.length} résultat${results.length > 1 ? 's' : ''} surligné${results.length > 1 ? 's' : ''}`}</span>}
          </div>
          {/* FICHE-RECHERCHE-1 — la LISTE des résultats sous la barre : libellé de la ligne + sa
              section. Un clic ouvre la section (déjà ouverte via forceOpen) et scrolle jusqu'à la
              ligne, surlignée plus fort (goToResult). */}
          {fq && results.length > 0 && (
            <div data-fiche-results className="max-h-52 overflow-y-auto border-t border-line/60">
              {results.map((r) => (
                <button key={r.key} data-fiche-result onClick={() => goToResult(r)}
                  className={`flex w-full items-baseline justify-between gap-3 px-5 py-1.5 text-left text-[11px] transition-colors hover:bg-surface-3 ${focusKey === r.key ? 'bg-surface-3' : ''}`}>
                  <span className="min-w-0 truncate text-txt">{r.label}</span>
                  <span className="shrink-0 text-[10px] uppercase tracking-wide text-txt-dim">{r.section}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* M19 (réf. ordre) : la barre d'onglets est RETIRÉE — la fiche est une pile de tiroirs
          empilés, navigable au scroll ; plus de navigation par onglets. */}

      {/* M68 P1a — l'ancien conteneur de défilement est FUSIONNÉ dans celui ouvert après l'en-tête
          (plus haut) : un seul conteneur `overflow-y-auto flex-1` pour tout le corps de la fiche. */}
        {/* FICHE-RANGEMENT-2 Lot 3 — plus de liste à plat qui remplaçait la fiche : la recherche
            garde la pile, ouvre tous les tiroirs (forceOpen) + les « sans objet », et surligne
            les correspondances en place (effet CSS.highlights). Le compteur est dans la barre. */}
        {isLoading && <Squelette lignes={6} label="Chargement de la fiche" />}
        {isError && (is429(error) ? (
          <RateLimit429 error={error} refetch={refetch} />
        ) : error instanceof ApiError && error.status === 404 ? (
          /* G1 (M12) : une parcelle absente du run (copro non classée, hors périmètre, ou clic
             sur une trame sans idu) N'EST PAS une panne. Message NEUTRE, sans tonalité d'erreur —
             on invite simplement à re-sélectionner une parcelle. Aucun « serveur injoignable ». */
          <div data-fiche-hors-run>
            <EmptyState
              title="Cette parcelle n'est pas dans le périmètre analysé."
              hint="Sélectionnez une parcelle sur la carte pour afficher sa fiche."
              action={
                <button onClick={() => select(null)} className="min-h-7 rounded border border-line-2 px-2 py-1 text-txt transition-colors duration-quick hover:border-mint/60 hover:text-txt-hi">Fermer</button>
              } />
          </div>
        ) : (
          <div data-fiche-erreur>
            {/* Item 3 (UX V1) : wording client — plus jamais « relancer labuse api » face à un
                utilisateur. Le détail technique reste lisible, en ligne discrète (hint). */}
            <ErrorState
              message="Connexion au serveur impossible — vérifiez votre réseau ou réessayez."
              retry={() => refetch()}
              hint={error instanceof Error && error.message
                ? <span className="break-all font-mono text-[10px] text-txt-dim">détail : {error.message}</span>
                : undefined} />
          </div>
        ))}
        {f && tab === 'synthese' && (() => {
          // micro-preuves (spec) dérivées des données déjà chargées
          const shorten = (s: string) => fmtLibelleBrut(s).replace(/\s*[—(].*$/, '').trim()
          const proprioPastilles = proprioLines.filter((l) => (l.weight ?? 0) > 0).slice(0, 3).map((l) => shorten(l.detail).slice(0, 26))
          // ALGO-1 item 2 : l'accent proprio ne dépend plus du Score V (retiré de l'affichage)
          const proprioAccent = !!proprioSignal
          // FICHE-RANGEMENT-2 Lot 1 — les 6 tuiles d'en-tête sont DISSOUTES : chaque valeur (et son
          // « i » de source) est reportée VERBATIM dans le RefDrawer de sa section (RECETTE-5..8).
          const nf = (n: number) => n.toLocaleString('fr-FR')
          // Surface → bandeau de tête (le bloc `data-fiche-tuiles`) UNIQUEMENT ; retirée d'Identité
          // (KELFONCIER-FIX-2 Lot G, maquette v3 : la contenance ne se répète pas dans la section).
          // Zone → §4 Urbanisme (zone PLU au point de la parcelle) + son sous-titre lisible.
          const zUp = (reglesZone ?? '').toUpperCase()
          const zoneSous = !zUp ? undefined
            : zUp.startsWith('AU') ? 'à urbaniser' : zUp.startsWith('U') ? 'constructible'
            : zUp.startsWith('A') ? 'agricole' : zUp.startsWith('N') ? 'naturelle' : undefined
          const tuileZone = { v: reglesZone ?? 'Non publié au GPU', s: zoneSous, vide: reglesZone == null,
            i: 'Zone du PLU au point de la parcelle (règlement communal, archive GPU). « Non publié au GPU » : la commune n’a pas déposé de document opposable.' }
          // Pente → §2 Terrain (RGE ALTI) + sous-titre par degrés (plat → très forte).
          const penteDeg = f.terrain?.pente_moy_deg
          const penteSous = penteDeg == null ? undefined
            : penteDeg < 5 ? 'plat' : penteDeg < 15 ? 'modérée' : penteDeg < 30 ? 'forte' : 'très forte'
          const tuilePente = { v: penteDeg != null ? `${nf(penteDeg)} °` : '—', s: penteSous, vide: penteDeg == null,
            i: 'Pente moyenne du terrain, calculée sur le modèle de relief RGE ALTI (IGN). À La Réunion elle commande le coût de terrassement autant que la constructibilité. « — » : relief non disponible sur la parcelle.' }
          // Exposition → §2 Terrain (orientation du versant + pente, MNT RGE ALTI, sans ligne de vue).
          const expoData = expo.data
          const expoOrient = expoData?.orientation
          // FICHE-FIX-2 P6 — l'Exposition ne montre plus la pente du versant (fenêtre 200 m ≠ emprise) :
          // la pente vit UNE fois dans la tuile « Pente » (emprise). L'azimut du versant reste servi
          // ci-dessous (aspect_deg) car l'orientation, elle, a besoin du contexte du versant.
          const tuileExpo = {
            v: expo.isLoading ? '…' : (expoOrient && expoOrient !== 'plat' ? expoOrient : expoOrient === 'plat' ? 'Plat' : '—'),
            s: expoOrient === 'plat' ? 'terrain quasi plat'
              : expo.isLoading ? 'calcul en cours'
              : !expoOrient ? 'relief non disponible' : 'versant (RGE ALTI, fenêtre 200 m)',
            vide: !expoOrient,
            i: 'Orientation du versant de la parcelle (Nord, Sud-Est…), calculée sur le modèle d’altitude RGE ALTI (IGN) dans une fenêtre de 200 m autour du centroïde. La pente affichée est celle de l’emprise (tuile « Pente ») ; l’exposition n’en affiche pas une seconde. « — » : relief non disponible sur la parcelle.' }
          // Taxe foncière → §7 Fiscalité (TFPB part communale, REI DGFiP) — désormais en Tuile (Lot I).
          const tfpb = f.fiscalite?.tfpb_commune_pct
          // SDP restante → §10 Potentiel (potentiel résiduel autorisé par le PLU).
          const tuileSdp = { v: reglesSdp != null && reglesSdp > 0 ? `${fmtInt(reglesSdp)} m²` : '—',
            s: reglesSdp != null && reglesSdp > 0 ? undefined : (reglesZone && /^(A|N)/i.test(reglesZone) ? 'zone non constructible' : 'pas de potentiel résiduel'),
            vide: !(reglesSdp != null && reglesSdp > 0),
            i: 'Surface de plancher que le PLU autorise ENCORE sur la parcelle (potentiel résiduel). « — » : zone non constructible ou plus de potentiel.' }
          // ChiffreDissous — présente une ex-tuile d'en-tête comme un fait de section (label · valeur ·
          // sous-titre · « i » source), grammaire FactRow. Reporté verbatim des 6 tuiles (RECETTE-8 W11).
          const ChiffreDissous = ({ l, t }: { l: string; t: { v: string; s?: string; vide?: boolean; i: string } }) => (
            <FactRow label={<>{l}{' '}
              <Tip tip={t.i} garder side="bottom"><span role="button" tabIndex={0} aria-label={`Source : ${l}`}
                className="ml-0.5 inline-flex h-[12px] w-[12px] items-center justify-center rounded-full border border-line-2 text-[7px] font-bold leading-none text-txt-dim align-middle hover:border-mint hover:text-mint">i</span></Tip></>}
              value={<>{t.v}{t.s ? <small className="ml-1 text-txt-dim">{t.s}</small> : null}</>}
              tone={t.vide ? 'mute' : undefined} />
          )
          // RETOURS-11F4 (F8) : viabValue/viabColor/viabConfirmee/viabContext vivent dans `ReseauxSection`.
          return (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
            {/* rien ne flotte : équipements, alerte accès, Q/A, statut, signaux → DANS les tiroirs (R1). */}

            {/* M55-L point 11 — BOUTONS IA EN TÊTE de fiche (mauve = couleur IA LABUSE, cf. « + Projet »
                / « Pourquoi ce score »), mis en valeur, visibles sans défilement dès l'ouverture.
                « Une question ? » (AskBar) + « Synthèse ». Même palette violette qu'avant (aucun
                nouveau composant), remontée + encadrée. */}
            {/* DA §4 — DEUX boutons .b-iris côte à côte, un libellé chacun. Les résultats
                (réponse AskBar, synthèse) se déploient en dessous. */}
            {/* M56-B3 fix 5 — DEUX .b-iris LÉGERS (moins que le bouton d'analyse) : hauteur réduite
                (padding 8px 11px), contenu aligné à GAUCHE, icône mauve 13px + libellé 12.5px. */}
            {/* M56-B6 · DA-FICHE-v6 — deux .ia-btn (34px) côte à côte ; icônes SVG conservées. */}
            {/* M61 P1 — le panneau actif (question ou synthèse) REMPLACE la rangée des deux boutons,
                pleine largeur ; « Replier » y ramène les boutons. Repli/réouverture de la synthèse
                ne relance aucun appel (mutation portée par la fiche, cf. syntheseM). */}
            {/* RETOURS-13 P1 — la rangée IA d'en-tête (« Poser une question » + ex-« Synthèse IA »)
                a REMONTÉ à côté du bouton d'analyse (bloc Analyse, plus haut) : les deux boutons
                de tête vivent désormais sur UNE rangée. Plus rien à rendre ici. */}

            {/* M55-O phase 2.1c : Mode B unifié et rattaché à la Constructibilité (rendu unique plus
                bas). L'ancien rendu « remonté » pour la déclassée à signal fort est retiré. */}

            {/* FICHE-RANGEMENT-1 Lot 1 (doublon #5) — les badges SIGNAUX (EBC / ER) faisaient doublon avec
                le tiroir « Dispositifs et périmètres », qui porte EBC et ER AVEC leur contexte (n° d'ER,
                part d'emprise, aux côtés des SUP / DPU / PEB). On retire le teaser du haut ; la présence
                reste signalée en un coup d'œil par la pastille « N périmètres » de la ligne fermée du tiroir. */}

            {/* M55-O phase 3.4 — GROUPE SILENCIEUX « LE TERRAIN » : Urbanisme · Constructibilité
                (+ Mode B) · Risques et protections. */}
            {/* M137-E — le Copilote embarqué « Demander au Copilote sur cette parcelle… » est RETIRÉ :
                la loupe (recherche intra-fiche) + « Poser une question » (AskBar) couvrent déjà le besoin. */}

            {/* ═══ FICHE-RANGEMENT-2 Lot 1 — LES 11 SECTIONS PAR NATURE (basculement) ═══
                Groupes silencieux : Le bien (Identité·Terrain·Bâti) · Le droit du sol (Urbanisme·
                Risques·Réseaux·Fiscalité) · Le marché (Marché·Quartier) · Le projet (Potentiel·
                Simulation). Accordéon exclusif inchangé (RefDrawer / FicheAccordionCtx). Chaque
                section COMPOSE des blocs feuilles ; aucune ligne n'est perdue vs les 12 tiroirs. */}
            <GroupLabel>Le bien</GroupLabel>

            {/* ① IDENTITÉ — ce qui identifie le bien : surface (ex-tuile), propriétaire (relocalisé
                §1), dernière vente DVF (ex-Marché), filiation cadastrale, historique des permis DE la
                parcelle (ex-Autour). CARTE ACCENTUÉE VIOLETTE = le signal propriétaire chaud. */}
            {/* FICHE-RANGEMENT-3 Lot 4 — la commune n'est plus rappelée en sous-titre (déjà dans
                l'en-tête « PARCELLE · <COMMUNE> ») : le sous-titre ne porte que le signal propriétaire. */}
            <RefDrawer id="identite" icon={IC.proprio} name="Identité" accent={proprioAccent}
              context={proprioSignal ? (f.proprietaire_moral ? proprioType : 'personne physique') : undefined}
              value={proprioSignal ? shorten(proprioSignal.detail).slice(0, 20) : (f.proprietaire_moral ? proprioType.slice(0, 18) : 'Particulier')}
              micro={proprioPastilles.length ? <MicroPastilles items={proprioPastilles} /> : undefined}>
              <div className="flex flex-col gap-3">
                {/* KELFONCIER-FIX-2 (Lot G) — maquette v3 : Verdict + Tuiles×4 (SIREN · Créée·état ·
                    Activité · BODACC). Surface retirée d'ici (elle vit dans le bandeau de tête, doublon
                    assumé §sommaire). Aucune donnée recalculée : SIREN, activité, état, procédure sont
                    servis (SIRENE / DGFiP) et réagencés tels quels. */}
                {/* ⑤ PROPRIÉTÉ (relocalisée §1) — société (M43) + signaux vendeur. */}
                <div className="flex flex-col gap-2">
                {f.proprietaire_moral ? (() => {
                  const pm = f.proprietaire_moral
                  const id = pm.identite
                  const anc = f.anciennete_detention
                  const proc = pm.etat_societe
                  const tuiles: Tuile[] = [
                    { label: 'SIREN',
                      valeur: pm.siren
                        ? <a data-annuaire-entreprises href={id?.annuaire_url ?? `https://annuaire-entreprises.data.gouv.fr/entreprise/${pm.siren}`}
                            target="_blank" rel="noreferrer noopener" className="font-mono text-mint hover:underline">{pm.siren}</a>
                        : '—',
                      sous: pm.siren ? 'annuaire des entreprises ↗' : undefined, ton: pm.siren ? undefined : 'gris' },
                    { label: 'Créée · état',
                      valeur: <>{id?.date_creation ? id.date_creation.slice(0, 4) : '—'}{id?.actif != null ? <small style={{ marginLeft: 4, color: id.actif ? 'var(--mint)' : 'var(--st-ecartee)' }}>{id.actif ? 'active' : 'cessée'}</small> : null}</>,
                      sous: id?.source ? 'SIRENE' : undefined, ton: id?.date_creation ? undefined : 'gris' },
                    { label: 'Activité', valeur: <span style={{ fontSize: 12 }}>{id?.activite ?? '—'}</span>,
                      sous: id?.ape ?? undefined, ton: id?.activite ? undefined : 'gris' },
                    { label: 'BODACC', valeur: <span style={{ fontSize: 12 }}>{proc ? proc.libelle : 'aucune procédure'}</span>,
                      sous: proc ? 'procédure collective' : 'DGFiP / BODACC', ton: proc ? 'ambre' : 'vert' },
                  ]
                  return (
                    <div>
                      <Verdict ton="vert" reponse={pm.denomination ?? 'Propriétaire (personne morale)'}
                        contexte={[anc?.disponible && anc.depuis_annee ? `propriétaire depuis ${anc.depuis_annee}` : null,
                          proc ? proc.libelle : 'aucune procédure collective'].filter(Boolean).join(' — ') || undefined} />
                      <Tuiles items={tuiles} />
                      {(id?.siege || pm.groupe_label) && (
                        <Lignes>
                          {id?.siege && <Ligne label="Siège" valeur={<>{id.siege}{id.siege_commune ? <small> · {id.siege_commune}</small> : null}</>} />}
                          {pm.groupe_label && <Ligne label="Groupe" valeur={pm.groupe_label} />}
                        </Lignes>
                      )}
                      {proc && (
                        <FactNote>{proc.libelle} (Sourcé {proc.etats.map((e) => e.source).filter((s, i, a) => a.indexOf(s) === i).join(' / ')}) — {proc.note}</FactNote>
                      )}
                    </div>
                  )
                })() : (
                  /* FICHE-FIX-5 (Lot C) — personne physique : Verdict clair, le paragraphe SPF/CERFA
                     derrière le « i » (plus de paragraphe gris dans le flux). Le bouton « Courrier SPF »
                     reste en pied (OutilsSection, plus bas). */
                  <Verdict ton="gris" reponse="Propriétaire non identifié"
                    contexte={<>personne physique ou hors fichier des personnes morales<InfoI aria="Comment identifier le propriétaire" tip="L'identité nominative d'une personne physique n'est pas automatisée : elle passe par une demande au Service de la publicité foncière (SPF), courrier CERFA. Le bouton « Courrier SPF » ci-dessous le pré-remplit sur la parcelle." /></>} />
                )}
                {/* FICHE-FIX-4 (Lot C) — la liste brute des lignes « proprio » (BODACC, « personne
                    morale »…) FAISAIT DOUBLON avec les Tuiles/Verdict ci-dessus (maquette : aucune
                    liste grise ici). Les signaux vendeur restent portés par les pastilles de l'en-tête
                    du tiroir (proprioPastilles) ; `proprioLines` reste calculé pour elles. */}
                {/* L1 (KF-2) — historique du propriétaire moral par millésime + diff constaté (hors
                    scoring). R6 : `pm` dit au composant si la parcelle a un propriétaire moral —
                    absence de timeline = ligne honnête (PM) ou silence justifié (PP). */}
                <ProprietaireHistorique h={f.proprietaire_historique} pm={!!f.proprietaire_moral} />
                {/* FICHE-FIX-4 (Lot C) — ancienneté de détention en une Ligne « Détention ≥ N ans
                    (depuis AAAA) », source derrière le « i ». RETOUCHES-1 C.14 : PM = millésimes DGFiP
                    (1ʳᵉ apparition du SIREN) ; PP = dernière mutation DVF (jamais nommée). */}
                {f.anciennete_detention?.disponible && (
                  <div data-anciennete><Lignes>
                    <Ligne label={<>Détention<InfoI tip={`${f.anciennete_detention.source}${f.anciennete_detention.millesime ? ` · ${f.anciennete_detention.millesime}` : ''}`} aria="Source de l'ancienneté de détention" /></>}
                      valeur={<>≥ {f.anciennete_detention.depuis_ans} an{(f.anciennete_detention.depuis_ans ?? 0) > 1 ? 's' : ''}{f.anciennete_detention.depuis_annee ? ` (depuis ${f.anciennete_detention.depuis_annee})` : ''}</>} />
                  </Lignes></div>
                )}
                {/* M125-2 — copropriété(s) RNIC rattachées (donnée réelle, cible bailleur/copro) */}
                {f.coproprietes && f.coproprietes.length > 0 && <CoproprietesBlock copros={f.coproprietes} />}
                {/* FICHE-FIX-4 (Lot C) — outil en pied : Scan patrimoine (PM) OU Courrier SPF (PP), en
                    bouton OutilsSection au lieu d'une grande carte PorteOutil. */}
                {f.proprietaire_moral?.siren ? (
                  <OutilsSection outils={[{ label: 'Scan patrimoine du propriétaire', principal: true, full: true, data: 'patrimoine',
                    onClick: () => { setM02Prefill(f.proprietaire_moral!.siren!); setModule('patrimoine') } }]} />
                ) : !f.proprietaire_moral ? (
                  <OutilsSection outils={[{ label: CLIENT.fiche.export.spf, principal: true, full: true, data: 'spf-letter',
                    onClick: () => { setCourrierPrefill(idu); setModule('courriers') } }]} />
                ) : null}
                </div>
                {/* DERNIÈRE VENTE (DVF) — fait d'identité, relocalisé de Marché (§8→§1). */}
                <DerniereVenteBlock f={f} />
                {/* FILIATION cadastrale officielle — relocalisée de « Le bien » (leBien.tsx §1). */}
                <FiliationBlock f={f} />
                {/* HISTORIQUE des permis DE la parcelle — relocalisé de « Autour » (§9→§1). */}
                <HistoriqueSiteBlock f={f} />
                {/* FICHE-SANS-OBJET-1 — repli « N sans objet » de §1 (modèle §5) : les vérifications
                    proprio sans objet par nature d'une personne physique reviennent ici (repliées),
                    au lieu d'être jetées en silence. */}
                {proprioSansObjet.length > 0 && (
                  <details data-identite-sans-objet>
                    <summary className="cursor-pointer text-[12px] font-semibold text-txt-mut" style={{ listStyle: 'none' }}>
                      <span className="text-mint">✓</span> {proprioSansObjet.length} couche{proprioSansObjet.length > 1 ? 's' : ''} sans objet — déplier
                    </summary>
                    <div className="mt-1.5 flex flex-col gap-1">
                      {proprioSansObjet.map((l, i) => <Line key={i} line={l} hideWeight hideDate />)}
                    </div>
                  </details>
                )}
              </div>
            </RefDrawer>

            {/* ② TERRAIN — ce qui touche le sol : pente + exposition (ex-tuiles), surface au sol libre
                + artificialisation OCS GE (TerrainDuBienBlock §2), piscine (EquipementsBadges, ex-Réseaux). */}
            <RefDrawer id="terrain" icon={IC.terrain} name="Terrain"
              context={[penteSous ? `pente ${penteSous}` : null, expoOrient && expoOrient !== 'plat' ? String(expoOrient) : null].filter(Boolean).join(' · ') || undefined}
              value={penteDeg != null ? `${nf(penteDeg)} °` : (expoOrient && expoOrient !== 'plat' ? String(expoOrient) : undefined)}>
              <div className="flex flex-col gap-3">
                {/* KELFONCIER-FIX-2 (Lot F) — maquette v3 : Verdict + Tuiles (pente·expo·surface
                    libre·sol artificialisé) + BarreEmpilée CoSIA. Toutes les valeurs sont servies
                    (aucun recalcul) ; le verdict réagence des faits déjà servis. */}
                {(() => {
                  const lb = f.le_bien
                  const cos = lb?.cosia_couverture
                  const artif = lb?.ocsge?.part_artif_pct
                  const vRep = expoOrient === 'plat' ? 'Terrain plat'
                    : expoOrient ? `Versant ${expoOrient}`
                    : (penteSous ? `Terrain ${penteSous}` : 'Terrain')
                  const vCtx = [
                    penteDeg != null ? `${nf(penteDeg)} °` : null,
                    lb?.surface_libre_m2 != null ? `${fmtInt(lb.surface_libre_m2)} m² au sol libre` : null,
                    artif != null ? `${artif.toLocaleString('fr-FR')} % artificialisé (OCS GE)` : null,
                  ].filter(Boolean).join(' · ')
                  const tuiles: Tuile[] = [
                    { label: 'Pente', valeur: <>{tuilePente.v}{tuilePente.s ? <small> {tuilePente.s}</small> : null}</>, ton: tuilePente.vide ? 'gris' : undefined },
                    { label: 'Exposition', valeur: tuileExpo.v, sous: tuileExpo.s, ton: tuileExpo.vide ? 'gris' : undefined },
                  ]
                  if (lb?.surface_libre_m2 != null) tuiles.push({ label: 'Surface au sol libre', valeur: <>{fmtInt(lb.surface_libre_m2)} <small>m²</small></> })
                  if (artif != null) tuiles.push({ label: 'Sol artificialisé', valeur: <>{artif.toLocaleString('fr-FR')} <small>%</small></>, sous: `OCS GE ${lb!.ocsge!.millesime}` })
                  const parts = ([
                    cos?.part_impermeabilisee_pct != null ? { pct: cos.part_impermeabilisee_pct, color: '#6b7280', label: `Imperméabilisé ${cos.part_impermeabilisee_pct.toLocaleString('fr-FR')} %` } : null,
                    cos?.part_vegetalisee_boisee_pct != null ? { pct: cos.part_vegetalisee_boisee_pct, color: 'var(--mint)', label: `Végétalisé ${cos.part_vegetalisee_boisee_pct.toLocaleString('fr-FR')} %` } : null,
                    cos?.part_sol_nu_pct != null ? { pct: cos.part_sol_nu_pct, color: 'var(--line-2)', label: `Sol nu ${cos.part_sol_nu_pct.toLocaleString('fr-FR')} %` } : null,
                  ].filter(Boolean) as Part[])
                  return (
                    <>
                      <Verdict ton="vert" reponse={vRep} contexte={vCtx || undefined} />
                      <Tuiles items={tuiles} />
                      {parts.length > 0 && (
                        <div data-le-bien-terrain>
                          <GroupLabel>Couverture du sol · CoSIA 20 cm</GroupLabel>
                          <BarreEmpilee parts={parts} />
                        </div>
                      )}
                    </>
                  )
                })()}
                {/* FICHE-RANGEMENT-3 Lot 5 — AZIMUT du versant (aspect_deg, MNT RGE ALTI) : le cap
                    précis derrière l'orientation lisible (0° = Nord, sens horaire). */}
                {expoData?.aspect_deg != null && (
                  <div data-terrain-azimut>
                    <Ligne label="Azimut du versant"
                      valeur={<>{nf(expoData.aspect_deg)} <small>° (0 = Nord, sens horaire)</small></>} />
                  </div>
                )}
                <EquipementsBadges idu={idu} />
                {/* RETOURS-13 P6 — coupe altimétrique (repliable) le long du plus grand axe, ou d'une
                    ligne dessinée. Lue LIVE dans le RGE ALTI (le même relief que la pente ci-dessus). */}
                <ProfilAltimetrique idu={idu} />
                <FactNote>OCS GE (IGN, donnée d’îlot, décret 2023-1096) · CoSIA (IGN, détection IA, mesure de la parcelle) · pente et exposition RGE ALTI (IGN).</FactNote>
              </div>
            </RefDrawer>

            {/* ③ BÂTI — le bâtiment existant (emprise, CoSIA, hauteur, DPE, toit, RNB → BatiBlock §3).
                S'omet si rien d'évaluable (couche bâtiments non ingérée → le_bien absent). */}
            {f.le_bien?.disponible && (
              <RefDrawer id="bati" icon={IC.faisa} name="Bâti"
                context={f.le_bien.occupation_label || 'bâti existant'}
                value={f.le_bien.nb_batiments != null && f.le_bien.nb_batiments > 0
                  ? <Badge ton="vert">{f.le_bien.nb_batiments} bâtiment{f.le_bien.nb_batiments > 1 ? 's' : ''}</Badge>
                  : <Badge ton="vert">terrain nu</Badge>}>
                <BatiBlock f={f} />
              </RefDrawer>
            )}

            <GroupLabel>Le droit du sol</GroupLabel>

            {/* ④ URBANISME — droit du sol : zone (ex-tuile) + PLU/procédure/traducteur/règlement/
                situation (ex-tiroir Règles) + RTAA DOM (§4) + dispositifs ER/EBC/DPU/PEB/SUP (§4) +
                mixité sociale (non renseignée à ce jour). */}
            {/* FICHE-RANGEMENT-1 Lot 1 (doublon #2) — le CODE DE ZONE vit UNE fois : ici en tuile
                dissoute (glance) + en détail dans ReglementPluBlock (« Règlement — zone X »). */}
            {/* FICHE-RANGEMENT-3 Lot 2 — « N % SDP consommée » n'apparaît plus DANS le sous-titre :
                la micro-jauge (première ligne du tiroir ouvert) le porte déjà. Le sous-titre ne garde
                que l'article/zone non publiée (rien quand la zone est connue → la jauge suffit). */}
            <RefDrawer id="urbanisme" icon={IC.regles} name="Urbanisme"
              value={reglesGabarit}
              context={reglesZone ? undefined : (reglesArticle ? `art. ${reglesArticle}` : 'zone non publiée au GPU')}
              micro={pctConsomme != null
                ? <MicroJauge pct={pctConsomme} label={CLIENT.fiche.sdpConsommee(pctConsomme)} tip={CLIENT.fiche.sdpConsommeeTip(reglesSdp ?? null)} />
                : <MicroJauge pct={0} label={[reglesArticle ? `art. ${reglesArticle}` : null].filter(Boolean).join(' · ') || 'PLU'} />}>
              <div className="flex flex-col gap-3">
                {/* FICHE-FIX-4 (Lot F) — VERDICT COMPLET pour TOUTES les zones (calibrées ou non) :
                    zone + nature + « N destinations interdites · N sous condition » (comptes servis
                    reglement_plu.zones[].destinations). Aucun nombre recalculé. */}
                {(reglesZone || f.au_ouverture) && (() => {
                  const dst = (f.reglement_plu?.zones ?? []).reduce((a, z) => ({
                    int: a.int + (z.destinations?.interdites?.length ?? 0),
                    sc: a.sc + (z.destinations?.sous_conditions?.length ?? 0),
                  }), { int: 0, sc: 0 })
                  const destTxt = [dst.int > 0 ? `${dst.int} destination${dst.int > 1 ? 's' : ''} interdite${dst.int > 1 ? 's' : ''}` : null,
                    dst.sc > 0 ? `${dst.sc} sous condition` : null].filter(Boolean).join(' · ') || null
                  return (
                    <Verdict ton={f.au_ouverture?.bloquant ? 'ambre' : 'vert'}
                      reponse={reglesZone
                        ? <>{reglesZone}{zoneSous ? `, ${zoneSous}` : ''}{f.au_ouverture ? ` : ${f.au_ouverture.statut}` : ''}</>
                        : 'Zone non publiée au GPU'}
                      contexte={f.au_ouverture?.motif || destTxt || undefined} />
                  )
                })()}
                <ChiffreDissous l="Zone" t={tuileZone} />
                {/* M75 — obligation APER (ombrières PV, grand parking > 1 500 m²) : contrainte
                    réglementaire portant sur le terrain, INFORMATION. Libellé backend (mêmes mots
                    que les exports). « potentiellement concerné », jamais « soumis à ». */}
                {/* FICHE-RANGEMENT-2 Lot 4 — grammaire visuelle unique : APER, fraîcheur PLU et Radar
                    procédures partageaient le MÊME motif (filet gauche + titre + prose) codé à la main
                    trois fois. Ils passent au filet partagé <Vigilance> (ambre par défaut ; mint « à
                    jour » ; creuser « en cours »). Contenu inchangé ; le style est désormais unique. */}
                {f.aper && (
                  <div data-aper>
                    <Vigilance title={<><span aria-hidden className="mr-1">🅿</span>{f.aper.note}</>}>
                      {f.aper.etat}.
                    </Vigilance>
                  </div>
                )}
                {/* FICHE-FIX-4 (Lot F) — PLU en une Ligne : « approuvé le JJ/MM/AAAA » + badge document
                    (opposable / procédure). Le détail (fait foi, procédure en cours, action) derrière le « i ». */}
                {f.plu_fraicheur?.libelle && (() => {
                  const pf = f.plu_fraicheur!
                  const paras = [pf.fait_foi ? `✓ ${pf.fait_foi}` : null,
                    pf.en_cours ? (pf.statut === 'a_jour' ? pf.en_cours : `En cours (non servi) : ${pf.en_cours}`) : null,
                    pf.action ? `→ ${pf.action}` : null, pf.note].filter(Boolean) as string[]
                  return (
                    <div data-plu-fraicheur={pf.statut}><Lignes>
                      <Ligne label={<>PLU{paras.length > 0 ? <InfoI tip={<div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>{paras.map((s, i) => <span key={i}>{s}</span>)}</div>} aria="Sur le document PLU" /> : null}</>}
                        valeur={<span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>{pf.horizon ? `approuvé le ${fmtDateNum(pf.horizon)}` : (pf.document_servi || 'document')}{pf.statut === 'a_jour' && <Badge ton="vert">document</Badge>}</span>} />
                    </Lignes></div>
                  )
                })()}
                {/* M41 — Radar procédures PLU : stade + conséquences parcellaires servables. */}
                {f.radar_procedure?.indisponible && <BlocIndisponible titre="Radar procédures PLU" />}
                {f.radar_procedure?.synthese?.etat && (
                  <div data-radar-procedure>
                    <Vigilance tone="creuser" title={<><span className="mr-1">📡</span>{f.radar_procedure.synthese.etat}</>}>
                      {f.radar_procedure.veille_au && (
                        <span className="block text-[10px] text-mint">Veille AU — {f.radar_procedure.veille_au}</span>
                      )}
                      {f.radar_procedure.sursis ? (
                        <span className="block text-[10px] text-st-ecartee">
                          Sursis à statuer — {f.radar_procedure.sursis.texte}
                          <span className="block text-txt-dim">{f.radar_procedure.sursis.base_legale}</span>
                        </span>
                      ) : (
                        <span className="block text-[10px] text-txt-dim">Sursis à statuer : non servi (débat PADD non constaté à ce jour).</span>
                      )}
                    </Vigilance>
                  </div>
                )}
                {/* M55-O phase 2.2 — la jauge « Qualité » (q_score) est RETIRÉE de la fiche : mesurée
                    non discriminante en M55-N (82,5 % à la base neutre 50). Seule « Confiance données »
                    (ICD, tiroir Données) reste. Le champ back q_score n'est PAS touché (consommé
                    ailleurs : App, Kanban, MapView, filtres…) — seul l'affichage fiche disparaît. */}
                {/* FINITIONS-1 (P13) — l'encart « Demander à l'IA de traduire le PLU » est RETIRÉ. */}
                {f.reglement_plu && <ReglementPluBlock rp={f.reglement_plu} />}
                {/* KELFONCIER-FIX-1 (Lot A) — STATUT D'OUVERTURE de la zone AU, sous la zone. Une zone
                    AU n'est constructible que si son règlement l'a ouverte ; « fermée »/« sous condition »
                    en ambre, avec le motif cité du règlement. Rien si la parcelle n'est pas en AU marquée. */}
                {f.au_ouverture && (
                  <div data-au-ouverture className="mt-1">
                    <FactRow label={`Zone AU${f.au_ouverture.zone_lib ? ` (${f.au_ouverture.zone_lib})` : ''}`}
                      value={<span className={f.au_ouverture.bloquant ? 'text-amber' : undefined}>{f.au_ouverture.statut}</span>}
                      tone={f.au_ouverture.bloquant ? 'warn' : undefined}
                      src={f.au_ouverture.source} />
                    {f.au_ouverture.motif && <FactNote>{f.au_ouverture.motif}</FactNote>}
                    {/* KELFONCIER-FIX-1 (Lot A) — PONT depuis la ligne vers l'outil PLU « Procédure &
                        changement », qui simule la bascule d'une zone AU en U (« Simuler l'ouverture »). */}
                    <PorteOutil ico="⇢" data="simuler-ouverture" titre="Simuler l'ouverture de la zone AU"
                      sous={f.au_ouverture.zone_lib ? `Ce que la bascule ${f.au_ouverture.zone_lib} → U changerait` : 'Ce que la bascule AU → U changerait'}
                      onClick={() => { setPluVueF('changement'); setModule('plu') }} />
                  </div>
                )}
                {/* M55-O phase 2.1c : le potentiel de transformation (SDP consommée/résiduelle/
                    surélévation) DÉMÉNAGE vers « Constructibilité » — il relève de la capacité, pas
                    du droit du sol pur. */}
                {/* M55-O phase 2.1b : les contrôles PASS (« sans objet ») partent dans
                    « Vérifications d'éligibilité » (bloc Analyse) ; ici, seules les lignes PLU
                    substantielles (non-PASS) restent — fini le mur de lignes « sans objet ». */}
                {/* M57-P1 (Q4) : points signés RETIRÉS ici (hideWeight) — le fait, la source et la
                    date restent. « Pourquoi ce score » (bloc Analyse) garde ses contributions. */}
                {/* RETOURS-23 — les faits de situation (zonage, SDP résiduelle, surface, parc…) sous un
                    kicker « Situation », comme la maquette ; primitive Line inchangée (détail + source). */}
                {/* FICHE-RANGEMENT-3 Lot 2 — la ligne « Zonage PLU » (layer zonage_plu_gpu) répète la
                    tuile « Zone » en tête → retirée (une seule ligne pour la zone). La ligne « bâti :
                    N bâtiments » (layer bati) répète §3 Bâti (nb_batiments) → retirée. */}
                {(() => { const rl = reglesLines.filter((l) => l.result !== 'PASS' && l.layer !== 'zonage_plu_gpu' && l.layer !== 'bati'); return rl.length > 0
                  ? <div><GroupLabel>Situation</GroupLabel><div className="flex flex-col gap-1">{rl.map((l, i) => <Line key={i} line={l} hideWeight hideDate />)}</div></div> : null })()}
                {/* FICHE-FIX-4 (Lot F) — les 2 outils PLU (Annuaire · Vérif procédure) en boutons
                    OutilsSection au lieu de grandes cartes PorteOutil. M137-P : Annuaire ouvre le hub
                    pré-rempli (commune + zone servie) ; Vérif procédure lit selectedIdu. */}
                <OutilsSection outils={[
                  { label: 'Annuaire PLU', principal: true, data: 'annuaire',
                    onClick: () => { setPluPrefillF({ insee: idu.slice(0, 5), zone: reglesZone ?? null }); setModule('plu') } },
                  { label: 'Vérif procédure', data: 'verif-procedure',
                    onClick: () => { setPluVueF('procedure'); setModule('plu') } },
                ]} />
                {/* RTAA DOM (§4) — rappel réglementaire de conception, servi par le bilan (b.rtaa). */}
                <RtaaFromBilan idu={idu} />
                {/* Dispositifs et périmètres (§4) — ER / EBC / doc urba / DPU / PEB / SUP (SOURCES-1 lot 1). */}
                {f.dispositifs && <DispositifsBody d={f.dispositifs} />}
                {/* SOURCES-FIX-1 A3 — SCOT (document supra-communal opposable au PLU). FICHE-FIX-4
                    (Lot F) : en Ligne comme les autres, source derrière le « i ». */}
                {f.scot && (
                  <div data-scot><Lignes>
                    <Ligne label={<>SCOT<InfoI tip={<>Schéma de cohérence territoriale — document supra-communal opposable au PLU. {f.scot.source}</>} aria="Sur le SCOT" /></>}
                      valeur={f.scot.disponible
                        ? <>{f.scot.nom ?? 'SCOT'}{f.scot.date_approbation ? <small> · approuvé le {fmtDateNum(f.scot.date_approbation)}</small> : (f.scot.statut ? <small> · {f.scot.statut}</small> : null)}</>
                        : 'hors périmètre'}
                      ton={f.scot.disponible ? undefined : 'gris'}
                      title={f.scot.disponible ? (f.scot.nom ?? undefined) : undefined} />
                  </Lignes></div>
                )}
                {/* FICHE-FIX-2 P4 — mixité sociale (LLS) branchée sur la règle VALIDÉE de la zone
                    (reglement_plu.mixite, lue des regles calibrées). Validée → seuil + quota + citation
                    sourcés ; propose/absente → « non modélisée pour cette zone » (jamais « non
                    renseigné », jamais un 0 muet). La 11e étape de la capacité porte le nombre résultant. */}
                {(() => {
                  const mx = f.reglement_plu?.mixite
                  const valide = mx?.statut === 'valide' && mx?.quota_pct != null
                  return (
                    <div data-mixite>
                      <GroupLabel right={valide ? <Badge ton="vert">Sourcé</Badge> : <Badge ton="neutre">non modélisée</Badge>}>Mixité sociale (LLS)</GroupLabel>
                      {valide ? (
                        <>
                          <FactRow label="Quota de logements sociaux" value={<>{mx!.quota_pct} <small>%</small></>} />
                          <FactRow label="Seuil de déclenchement"
                            value={mx!.seuil_logements != null ? <>{mx!.seuil_logements} <small>logements</small></> : '—'} />
                          <FactNote>
                            {mx!.article ? `${mx!.article}${mx!.page_pdf ? ` (p. ${mx!.page_pdf})` : ''} — ` : ''}
                            {mx!.citation ? `« ${mx!.citation} »` : 'clause de mixité sociale validée au règlement de zone.'}
                          </FactNote>
                        </>
                      ) : (
                        <>
                          <FactRow label="Clause de mixité sociale" tone="mute" value="non modélisée pour cette zone" />
                          <FactNote>
                            {mx?.statut === 'propose'
                              ? 'Clause détectée au règlement mais non validée (feuille « propose ») — non modélisée pour cette zone.'
                              : 'Aucune clause de mixité sociale validée pour cette zone dans le règlement calibré.'}
                          </FactNote>
                        </>
                      )}
                    </div>
                  )
                })()}
                {/* FICHE-SANS-OBJET-1 — §4 a désormais SON propre repli « N sans objet », calqué EXACT
                    sur §5 Risques (même libellé, même style, replié par défaut). Les lignes PASS de
                    l'onglet `regles` (« Hors forêt publique », « Hors zone humide », « Hors parc
                    national », « Non concerné SAFER »…) y sont ramassées au lieu de disparaître en
                    silence. EXCLUES car déjà re-servies ailleurs (jamais deux fois) : `bati` (→ §3
                    Bâti), `dpu` & `peb` (→ Dispositifs et périmètres), `zonage_plu_gpu` (→ tuile Zone). */}
                {(() => {
                  const so = reglesLines.filter((l) => l.result === 'PASS' && !['bati', 'dpu', 'peb', 'zonage_plu_gpu'].includes(l.layer))
                  return so.length > 0 ? (
                    <details data-urbanisme-sans-objet>
                      <summary className="cursor-pointer text-[12px] font-semibold text-txt-mut" style={{ listStyle: 'none' }}>
                        <span className="text-mint">✓</span> {so.length} couche{so.length > 1 ? 's' : ''} sans objet — déplier
                      </summary>
                      <div className="mt-1.5 flex flex-col gap-1">
                        {so.map((l, i) => <Line key={i} line={l} hideWeight hideDate />)}
                      </div>
                    </details>
                  ) : null
                })()}
              </div>
            </RefDrawer>

            {/* ⑤ RISQUES ET ENVIRONNEMENT — aléas, sols, vigilances, SUP, lignes HT/MT → risques.tsx. */}
            <RisquesSection f={f} idu={idu} />

            {/* ⑥ RÉSEAUX ET DESSERTE — fibre, accès + transport, gestionnaires, viabilisation (+ solaire),
                axes et nuisances → reseaux.tsx. */}
            <ReseauxSection f={f} idu={idu} />

            {/* ⑦ FISCALITÉ ET DISPOSITIFS — taxe foncière (ex-tuile) + fiscal & leviers (QPV/TVA §7) +
                taxe d'aménagement (§7) + dispositifs territoriaux ZFANG/FRR/DOM (relocalisés §7). */}
            {/* FICHE-RANGEMENT-3 Lot 4 — la commune (sous-titre) est retirée : déjà dans l'en-tête. */}
            <RefDrawer id="fiscalite" icon={IC.fiscal} name="Fiscalité et dispositifs"
              value={f.territoire_fiscal?.zfang?.regime === 'renforce'
                ? <Badge ton="vert">ZFANG renforcé</Badge>
                : tfpb != null ? `${nf(tfpb)} %` : undefined}>
              <div className="flex flex-col gap-3">
                {/* KELFONCIER-FIX-2 (Lot I) — maquette v3 : Verdict + Tuiles (taxe foncière · taxe
                    d'aménagement) + Pastilles des dispositifs de la commune. Taux et dispositifs sont
                    servis (REI DGFiP · CGI · DHUP) ; aucun taux recalculé. Détail conservé en dessous. */}
                {/* FICHE-FIX-4 (Lot I) — 4 tuiles (taxe foncière · taxe d'aménagement · zonage A/B/C ·
                    TVA), Pastilles allumées ET éteintes (ZFANG/FRR/ORT/QPV/PVD/Cœur de ville), les
                    4 paragraphes de dispositifs dans un Repli, disclaimer en source. Aucun taux recalculé. */}
                {(() => {
                  const terf = f.territoire_fiscal
                  const ta = f.taxe_amenagement
                  const dom = terf?.dispositifs_dom ?? []
                  const zonageVal = dom.find((d) => /zonage/i.test(d.libelle))?.libelle.split(':').pop()?.trim()
                  const tvaM = dom.find((d) => /tva/i.test(d.libelle))?.libelle.match(/(\d+[,.]?\d*)\s*%/)
                  const allTxt = [...(terf?.perimetres ?? []).map((p) => p.libelle), ...dom.map((d) => d.libelle)].join(' | ').toLowerCase()
                  const has = (re: RegExp) => re.test(allTxt)
                  const ortDate = dom.find((d) => /revitalisation|\bort\b/i.test(d.libelle))?.libelle.match(/(\d{4}-\d{2}-\d{2})/)?.[1]
                  const disp: Pastille[] = [
                    { label: 'ZFANG', on: !!terf?.zfang },
                    { label: 'FRR', on: !!terf?.frr },
                    { label: 'ORT', on: has(/\bort\b|revitalisation/), date: ortDate ? fmtDateNum(ortDate) : undefined },
                    { label: 'QPV', on: has(/\bqpv\b|quartier prioritaire/) },
                    { label: 'PVD', on: has(/petites villes/) },
                    { label: 'Cœur de ville', on: has(/c[œo]eur de ville/) },
                  ]
                  const tuiles: Tuile[] = []
                  if (tfpb != null) tuiles.push({ label: 'Taxe foncière', valeur: <>{nf(tfpb)} <small>%</small></>, sous: 'part communale' })
                  if (ta && (ta.taux_communal_pct != null || ta.taux_departemental_pct != null))
                    tuiles.push({ label: "Taxe d'aménagement", valeur: <>{ta.taux_communal_pct ?? '—'} + {ta.taux_departemental_pct ?? '—'} <small>%</small></>, sous: 'commune · dépt' })
                  if (zonageVal) tuiles.push({ label: 'Zonage A/B/C', valeur: zonageVal, sous: 'PTZ · loyers' })
                  if (tvaM) tuiles.push({ label: 'TVA', valeur: `${tvaM[1]} %`, sous: 'DOM · 2,1 % LLS' })
                  return (
                    <>
                      {(terf?.zfang || terf?.frr || zonageVal) && (
                        <Verdict ton="vert"
                          reponse={[terf?.zfang ? 'Zone franche (ZFANG)' : null, terf?.frr ? 'France Ruralités (FRR)' : null, disp[2].on ? 'ORT signée' : null].filter(Boolean).join(', ') || 'Dispositifs fiscaux'}
                          contexte={[zonageVal ? `zone ${zonageVal} (PTZ/loyers)` : null, tvaM ? `TVA ${tvaM[1]} %` : null].filter(Boolean).join(' · ') || undefined} />
                      )}
                      {tuiles.length > 0 && <Tuiles items={tuiles} />}
                      <GroupLabel>Dispositifs de la commune</GroupLabel>
                      <Pastilles items={disp} />
                      {/* FICHE-1 lot 5 — taxe d'aménagement en BOUTON (change les hypothèses). */}
                      {f.taxe_amenagement && (
                        <OutilsSection outils={[{ label: "Calculer la taxe d'aménagement", principal: true, full: true, data: 'taxe-amenagement-outil',
                          onClick: () => { setParcelPrefill(idu); setModule('taxe-amenagement') } }]} />
                      )}
                      {/* détail des dispositifs (les 4 paragraphes) + calcul de taxe (RAP, exonérations) → Repli. */}
                      {(f.taxe_amenagement || terf) && (
                        <Repli label="détail des dispositifs">
                          {f.taxe_amenagement && <TaxeAmenagementBlock t={f.taxe_amenagement} />}
                          {terf && (
                            <div className="flex flex-col gap-2.5" data-territoire-fiscal>
                              {(terf.perimetres ?? []).map((p) => (
                                <div key={p.libelle} data-fiche-perimetre className="border-l-2 border-mint pl-3">
                                  <p className="text-[12px] font-semibold text-txt-hi">{p.libelle}{p.derive && <span className="ml-1.5 rounded bg-surface-2 px-1 py-px text-[9px] uppercase tracking-wide text-txt-dim">estimé</span>}</p>
                                  <p className="mt-0.5 text-[11.5px] leading-snug text-txt">{p.detail}</p>
                                  <FactNote>{p.source}</FactNote>
                                </div>
                              ))}
                              {([['ZFANG — zone franche d’activité', terf.zfang],
                                 ['FRR — France Ruralités Revitalisation (ex-ZRR)', terf.frr]] as const)
                                .filter(([, a]) => !!a).map(([titre, a]) => (
                                <div key={titre}>
                                  <p className="text-[12px] font-semibold text-txt-hi">{titre}</p>
                                  <p className="mt-0.5 text-[11.5px] leading-snug text-txt">{a!.libelle}</p>
                                  <FactNote>{a!.source_ref} · <a href={a!.lien} target="_blank" rel="noreferrer" className="underline hover:text-mint">voir le texte</a></FactNote>
                                </div>
                              ))}
                              {(terf.dispositifs_dom ?? []).map((d) => (
                                <div key={d.libelle} data-dispositif-dom>
                                  <p className="text-[12px] font-semibold text-txt-hi">{d.libelle}</p>
                                  <p className="mt-0.5 text-[11.5px] leading-snug text-txt">{d.detail}</p>
                                  <FactNote>{d.source}</FactNote>
                                </div>
                              ))}
                            </div>
                          )}
                        </Repli>
                      )}
                      {f.territoire_fiscal?.avertissement && <FactNote>{f.territoire_fiscal.avertissement}</FactNote>}
                    </>
                  )
                })()}
              </div>
            </RefDrawer>

            <GroupLabel>Le marché</GroupLabel>

            {/* ⑧ MARCHÉ — prix de secteur, prix de sortie, VEFA, voisinage, annonces Radar → marche.tsx. */}
            <MarcheSection f={f} idu={idu} />

            {/* ⑨ QUARTIER — équipements, socio-éco, IRIS, isochrone, permis à proximité → autour.tsx. */}
            <AutourSection f={f} idu={idu} />

            <GroupLabel>Le projet</GroupLabel>

            {/* ⑩ POTENTIEL — SDP restante (ex-tuile) + potentiel de transformation (SDP conso/résid,
                marge H) + capacité constructible (SHAB vendable, calcul tracé). Lecture ; la simulation
                interactive (charge foncière, outils) vit en §11. */}
            <RefDrawer id="potentiel" icon={IC.potentiel} name="Potentiel"
              context={fo?.niveaux ? `${fo.niveaux} · calcul tracé` : 'calcul tracé'}
              value={reglesSdp != null && reglesSdp > 0 ? `${fmtInt(reglesSdp)} m² SDP` : undefined}>
              <div className="flex flex-col gap-3">
                {/* KELFONCIER-FIX-2 (Lot J) — maquette v3 : Verdict en tête (rouge quand la construction
                    neuve n'est pas autorisée : zone AU non ouverte ou zone A/N). Réagence des faits
                    déjà servis (au_ouverture, zone, SDP résiduelle), aucun calcul de capacité refait. */}
                {/* FICHE-FIX-4 (Lot L) — UNE seule phrase de verdict (avant, écrite 3× : ici + dans
                    FaisabiliteTab + GabaritLine). Quand la construction neuve n'est pas autorisée :
                    verdict ROUGE + tuile SDP + ligne « pourquoi » + boutons ; le panneau Faisabilité
                    (Terrain libéré, Tester un projet, hypothèses, gabarit) est REPLIÉ sous « Étudier
                    quand même ». Sinon : panneau ouvert. On ne modifie PAS FaisabiliteTab/GabaritLine. */}
                {(() => {
                  const inconstructible = !!f.au_ouverture?.bloquant || (!!reglesZone && /^(A|N)/i.test(reglesZone))
                  const pourquoi = f.au_ouverture?.motif
                    || (reglesZone && /^A/i.test(reglesZone) ? 'Zone agricole — construction de logements non autorisée.'
                      : reglesZone && /^N/i.test(reglesZone) ? 'Zone naturelle — construction non autorisée.' : null)
                  const outils: OutilSection[] = []
                  if (f.commune) outils.push({ label: "Densifier l'existant", data: 'densifier-filtre',
                    onClick: () => { const st = useApp.getState(); st.setCommunesFilter([f.commune!]); st.setFilter('renouvellement', true); st.setFilter('sdpMin', 200); st.openFiltres() } })
                  outils.push({ label: 'Ouvrir le Gabarit', principal: true, data: 'gabarit',
                    onClick: () => { setParcelPrefill(idu); setModule('programme') } })
                  const panneau = (
                    <div className="flex flex-col gap-3">
                      {f.potentiel_transformation && <TransformationBlock pt={f.potentiel_transformation} />}
                      <FaisabiliteTab idu={idu} />
                      <GabaritLine idu={idu} />
                    </div>
                  )
                  return (
                    <>
                      <Verdict ton={inconstructible ? 'rouge' : (reglesSdp != null && reglesSdp > 0 ? 'vert' : 'ambre')}
                        reponse={inconstructible
                          ? `Construction neuve non autorisée${reglesZone ? ` en ${reglesZone}` : ''}`
                          : (reglesSdp != null && reglesSdp > 0 ? `${fmtInt(reglesSdp)} m² de SDP résiduelle` : 'Pas de SDP résiduelle exploitable')}
                        contexte={!inconstructible && fo?.niveaux ? `capacité ${fo.niveaux}` : undefined} />
                      <ChiffreDissous l="SDP restante" t={tuileSdp} />
                      {inconstructible && pourquoi && <p className="text-[11.5px] leading-snug text-txt-mut" data-potentiel-pourquoi>{pourquoi}</p>}
                      {faisa.data?.delaisse && <div data-delaisse><Vigilance title={faisa.data.delaisse.libelle} /></div>}
                      <OutilsSection outils={outils} />
                      {inconstructible
                        ? <Repli label="Étudier quand même">{panneau}</Repli>
                        : panneau}
                    </>
                  )
                })()}
              </div>
            </RefDrawer>

            {/* ⑪ SIMULATION — la charge foncière (bilan) + la Réhabilitation (Mode B, FICHE-RANGEMENT-3
                Lot 3 : rentrée DANS §11, plus un 12e tiroir) + les outils de projet (Faisabilité,
                Calculette, Assemblage). 11 tiroirs au total. */}
            <RefDrawer id="simulation" icon={IC.confiance} name="Simulation"
              context="charge foncière · réhabilitation · outils projet"
              value={<Badge ton="vert">bilan</Badge>}>
              <div className="flex flex-col gap-3">
                {/* KELFONCIER-FIX-2 (Lot J) — maquette v3 : Verdict prix de sortie (servi, base du
                    bilan) + OutilsSection en pied (Faisabilité · Calculette · Assemblage). */}
                {/* FICHE-FIX-4 (Lot L) — le paragraphe explicatif passe derrière le « i » ; les 3 boutons restent. */}
                {(() => {
                  const prix = faisa.data?.marche?.median
                  return (
                    <Verdict ton="vert"
                      reponse={<>Prix de sortie retenu {prix != null ? `${fmtInt(Number(prix))} €/m²` : '—'}<InfoI aria="Sur le prix de sortie" tip="C'est le prix affiché dans « Marché » (prix de sortie bâti secteur) — il sert de base au bilan de charge foncière ci-dessous." /></>} />
                  )
                })()}
                <BilanTab idu={idu} />
                {/* Réhabilitation (Mode B) — bloc inline (ModeBBody), plus un tiroir séparé. */}
                {f.mode_b?.indisponible
                  ? <BlocIndisponible titre="Réhabilitation (Mode B)" />
                  : f.mode_b?.disponible && <ModeBBody idu={idu} initial={f.mode_b} />}
                <OutilsSection outils={[
                  { label: 'Faisabilité', principal: true, data: 'faisabilite-outil',
                    onClick: () => { setParcelPrefill(idu); setModule('programme') } },
                  { label: 'Calculette foncière', data: 'calculette',
                    onClick: () => { setCalcPrefill(idu); setModule('calculette-fonciere') } },
                  { label: 'Assemblage', full: true, data: 'assemblage-outil',
                    onClick: () => { setParcelPrefill(idu); setModule('assemblage') } },
                ] satisfies OutilSection[]} />
              </div>
            </RefDrawer>

            {/* M55-L point 11 : le bloc IA (« Une question ? » + « Synthèse ») est REMONTÉ en tête
                de fiche (voir plus haut, data-ia-tete). Il ne vit plus en bas de la pile. */}

            {/* ═══ BARRE D'ACTIONS · 2 niveaux (spec) — DANS le flux (fin du « double écran de vide ») ═══ */}
            <div>
              {/* M56-B6 · DA-FICHE-v6 — actions de pied en .actions (+ CRM · + Projet · Comparer),
                  sans filet séparateur (le relief vient du contraste fond/carte). */}
              {/* M60 P1d — « Comparer » DÉPLACÉ dans le groupe « OUTILS SUR CETTE PARCELLE » (portes,
                  plus bas). La barre d'actions garde + CRM · + Projet (actions de suivi, pas des outils). */}
              <div className="actions">
                <PipelineButton idu={idu} />
                <ProjetButton idu={idu} />
              </div>
              {/* RECETTE-7 (B4) — une respiration entre la rangée + CRM / + Projet et la grille
                  des 6 boutons (elles se touchaient).
                  RECETTE-9 T7 — 10 px restait trop faible (les deux rangées paraissaient collées) :
                  on double franchement la respiration + un filet de séparation discret pour marquer
                  que « + CRM / + Projet » (suivi) et les 6 documents/outils sont deux familles. */}
              <div aria-hidden style={{ height: 24, marginTop: 8, borderTop: '.5px solid #1E2A23' }} />
              {/* M55-L point 8 — BARRE D'ACTIONS sur une GRILLE 4×2 (décision Vic).
                  Ligne 1 : PDF · Dossier · Finance · Cadastre. Ligne 2 : 1950 · Maps · Courrier ·
                  Pré-dossier PC. M137-F : Pré-dossier PC RENTRE dans la grille (4e case de la 2e
                  ligne, ex-ligne pleine largeur retirée) — même gabarit `.exp` que les autres.
                  Les tuiles Cadastre / 1950 / Maps restent conditionnées à f.coords. */}
              {/* M60 P1d — « EXPORTS ET OUTILS » SCINDÉ en deux groupes : EXPORTS (documents,
                  inchangés) puis « OUTILS SUR CETTE PARCELLE » (portes compactes, plus bas). */}
              {/* PROJETS-V5 (E9) — les EXPORTS passent sur le composant PARTAGÉ GrilleOutils (même rendu +
                  survol que la grille d'outils de la fiche commune). Les icônes SVG et la logique des tuiles
                  (PDF, Dossier, Financier, Pré-dossier…) sont conservées. */}
              {/* RECETTE-6 (D1, décision Vic) — le titre « EXPORTS » est RETIRÉ : ce ne sont pas que des
                  exports (Courrier, Remonter le temps sont des OUTILS). La grille reste, sans en-tête. */}
              {/* EXPORTS-2 lot 8 — documents (builder unique) : Dossier · Financier · Apporteur ·
                  Pré-dossier PC · Courrier · Remonter le temps (RECETTE-6 D2). */}
              <GrilleOutils cols={3}>
                <DossierTile idu={idu} />
                {/* RECETTE-1 R28 — infobulles au survol retirées des tuiles d'export (le nom suffit). */}
                <BanquierButton idu={idu} />
                <OutilCase nom="Apporteur" data-apporteur href={`/apporteur/${idu}.pdf`}
                  ic={<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /><path d="M8 9h8" /><path d="M8 13h5" /></svg>} />
                <PreDossierTile idu={idu} />
                <OutilCase nom={CLIENT.fiche.export.courrier} data-courrier-tile onClick={() => { setCourrierPrefill(idu); setModule('courriers') }}
                  ic={<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="5" width="18" height="14" rx="2" /><path d="m3 7 9 6 9-6" /></svg>} />
                {/* RECETTE-6 (D2, décision Vic) — 6e bouton « Remonter le temps » : ouvre l'outil PRÉ-REMPLI
                    sur la parcelle (setParcelPrefill + recentrage) ; le fil de retour vers la fiche est
                    inhérent (setModule préserve selectedIdu → fermer l'outil ramène la fiche). Retiré de
                    l'accueil (cf. AccueilPreuves). */}
                <OutilCase nom="Remonter le temps" data-temps-tile
                  onClick={() => { setParcelPrefill(idu); if (f?.coords) setFlyToF({ center: f.coords, zoom: 18 }); setModule('temps') }}
                  ic={<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="8.5" /><path d="M12 7.3V12l3.1 1.9" /></svg>} />
              </GrilleOutils>
              {/* M70 déc. 12 — la grille terminale « OUTILS SUR CETTE PARCELLE » est SUPPRIMÉE
                  (elle recréait une page Outils bis). Chaque outil est désormais une PORTE
                  contextuelle en pied du tiroir où il a un rapport étroit avec les données :
                  Comparer + Remonter le temps → Marché ; Vérif procédure PLU → Urbanisme ;
                  Contrôle avant achat + Servitudes invisibles → Risques ; Courrier SPF + Scan
                  patrimoine → Propriétaire ; Faisabilité + Calculette + Assemblage → Constructibilité
                  (M-ENTREE : Faisabilité accepte un IDU en mode « par parcelle » ; Assemblage l'ajoute en
                  1ʳᵉ du lot). */}
              {/* Mention légale conservée (présente aussi dans les PDF, back). */}
              <p data-disclaimer-legal className="legal">
                Estimations indicatives issues de données publiques — ni conseil juridique/notarial ni garantie de constructibilité. <span data-disclaimer-cu>Ces informations ne remplacent pas un certificat d'urbanisme.</span>
              </p>
              {/* RETOURS-11 F2 — « Signaler une erreur » = DERNIER bloc de la fiche (F0). Il porte
                  la section ouverte : le signalement arrive dans Produit « parcelle <IDU> — <Section> ». */}
              <div className="mt-2">
                <SignalerErreur idu={idu} section={SECTION_LABELS[tiroirOuvert ?? ''] ?? null} />
              </div>
            </div>
          </div>
          )
        })()}
      </div>


    </aside>
    </FicheAccordionCtx.Provider>
  )
}


/** M54-EXPO-2 — « Synthèse IA » : prose IA de toute la fiche (GET /parcels/{idu}/explain). La
 *  couche 2 M-T garantit une sortie soit VALIDÉE (available) soit un repli STUB déterministe
 *  (available=false, stub=true) — on affiche le libellé de repli quand c'est un stub. Le quota IA
 *  existant s'applique au niveau du socle IA ; un 429 tombe dans le message d'erreur. */
// RETOURS-13 P1 — « Synthèse IA » retirée de la fiche : le panneau SyntheseIAPanel (mutation
// getExplain portée par la fiche) est SUPPRIMÉ. Le Copilote reste accessible par « Poser une
// question » (AskBar). L'endpoint GET /parcels/{idu}/explain n'a plus de point d'entrée front
// (NON supprimé côté back — peut resservir ; décision Vic).


// M55-L point 7 : le widget feedback `FeedbackStrip` (« Ce lead vous est-il utile ? ») est retiré
// de la fiche → fonction 0-caller supprimée, imports `postFeedback`/`FeedbackVerdict` retirés.
// ⚠ BACKEND : le endpoint POST /feedback (M54-EXPO A4, models.ParcelFeedback) n'a plus AUCUN point
// d'entrée côté front — NON supprimé côté back (décision Vic requise ; peut revenir, p. ex. CRM).


/** M54-EXPO-2 Volet C — tuile « Dossier » enrichie du STATUT (GET /dossier/statut) : quota
 *  restant du mois affiché, ou grisée + raison si le générateur n'est pas déployé (501). La barre
 *  à 7 tuiles n'est PAS réordonnée : c'est la même cellule, avec l'état en plus. */
function DossierTile({ idu }: { idu: string }) {
  const st = useQuery({ queryKey: ['dossier-statut'], queryFn: getDossierStatut })
  const icon = <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /></svg>
  const d = st.data
  if (d && !d.disponible) return (
    <OutilCase nom="Dossier" ic={icon} disabled data-dossier-indispo title={d.raison ?? 'Générateur de dossier indisponible'} />
  )
  const compteur = d && !d.illimite && d.restants != null
  const tip = d ? (d.illimite ? 'Dossier parcelle PDF brandé (illimité — Intégral)' : `Dossier parcelle PDF brandé — ${d.restants}/${d.quota_mois} restants ce mois`) : 'Dossier parcelle PDF brandé'
  return (
    <OutilCase nom="Dossier" ic={icon} href={`/dossier/${idu}.pdf`} title={tip} data-dossier-tile
      chiffre={compteur ? `· ${d!.restants}` : undefined} />
  )
}


/** M54-EXPO — tuile « Pré-dossier PC » (ZIP CERFA). Réservée au plan Intégral (backend :
 *  pre_dossier.py → plans.acces('pre_dossier_pc') = 403 sinon + quota M-K). Le front lit le plan
 *  (getMoi) et grise la tuile hors Intégral (pas de téléchargement d'un 403). */
function PreDossierTile({ idu }: { idu: string }) {
  const moi = useQuery({ queryKey: ['moi'], queryFn: getMoi })
  const integral = moi.data?.plan === 'integral'
  const icon = <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M21 8v13H3V3h10" /><path d="M16 3h5v5" /><path d="M8 13h6M8 17h4" /></svg>
  if (!integral) return (
    <OutilCase nom={CLIENT.fiche.export.preDossier} ic={icon} disabled data-predossier-gate
      title={`${CLIENT.fiche.export.preDossierTip} — ${CLIENT.fiche.export.preDossierGate}`} />
  )
  return (
    <OutilCase nom={CLIENT.fiche.export.preDossier} ic={icon} href={preDossierUrl(idu)} title={CLIENT.fiche.export.preDossierTip} data-predossier />
  )
}


/** B1.5 — bouton Dossier banquier à ÉTATS : clic → préparation asynchrone côté serveur
 *  (le PDF pesait 9,3 s bloquants), sonde /statut toutes les 1,5 s, puis « prêt — ouvrir »
 *  (cache serveur : ouverture ~ms). Erreur : message court + réessai. Si le cache est déjà
 *  chaud, le premier clic ouvre directement (même geste utilisateur → pas de popup bloquée). */
// EXPORTS-2 lot 4 — le bouton « Financier » ouvre le QUESTIONNAIRE (4 écrans) ; le questionnaire
// rempli alimente le document Financier (le bouton bascule sur le document au lot 8).
function BanquierButton({ idu }: { idu: string }) {
  const [open, setOpen] = useState(false)
  const icon = <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="6" width="18" height="12" rx="2" /><circle cx="12" cy="12" r="2.5" /></svg>
  return (
    <>
      <OutilCase nom={CLIENT.fiche.export.finance} ic={icon} onClick={() => setOpen(true)}
        data-banquier-btn title={CLIENT.fiche.export.banquierTip} />
      {open && <FinancierQuestionnaire idu={idu} onClose={() => setOpen(false)} />}
    </>
  )
}


