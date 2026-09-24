import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Tip } from '../Tip'
import { Bouton } from '../ui/Bouton'
import { Badge } from '../ui/Badge'
import { Siren } from '../shared/Siren'   // RETOURS-12 T2 — SIREN cliquable Pappers
import { useEffect, useMemo, useState, useRef, type ReactNode } from 'react'
import { addToPipeline, ajouterParcelle, ApiError, createProjet, getDossierStatut, getExplain, getFaisabilite, getFiche, getMoi, getParcelExposition, getPipelineForParcel, getPipelineMeta, getProjets, getWatch, is429, patchPipeline, postSignalement, preDossierUrl, projetsPourParcelle, toggleWatch } from '../../lib/api'
import { BANDE_META, SIGNAL_META, verdictMeta } from '../../lib/status'
import { fmtInt, fmtM2, fmtLibelleBrut, iduComplet } from '../../lib/format'
import { layerLabel } from '../../lib/layers'
import { CLIENT } from '../../lib/strings'
import { Loading } from '../Loading'
import { AskBar, renderRich } from './AskBar'
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
import { REF, RENOUV, RENOUV_CODE_LABEL, IC, FicheAccordionCtx, RefDrawer, GroupLabel, MicroJauge, MicroPastilles, MicroTriple, RateLimit429, Line, EligibiliteReplie, PorteOutil, FactRow, FactNote, Vigilance } from './primitives'
// FICHE-RANGEMENT-2 Lot 1 — LE BASCULEMENT : la fiche est recomposée en 11 sections PAR NATURE,
// chacune un RefDrawer inline qui COMPOSE les blocs feuilles (extraits aux étapes 3a-3c). Les
// sections « fourre-tout » ConstructibiliteSection / LeBienSection sont dissoutes ; les quatre
// sections encore mono-nature (Risques, Réseaux, Marché, Quartier) restent des composants réutilisés.
// Fiche ré-exporte Calculette + FaisabiliteTab (consommés par CalculetteFonciere / M22Programme).
import { TransformationBlock, FaisabiliteTab, BilanTab, TaxeAmenagementBlock, FiscalLeviersBlock, RtaaFromBilan, DispositifsBody, ModeBBody } from './constructibilite'
import { BatiBlock, TerrainDuBienBlock, FiliationBlock } from './leBien'
import { RisquesSection } from './risques'
import { MarcheSection, DerniereVenteBlock } from './marche'
import { ReseauxSection, EquipementsBadges } from './reseaux'
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
  // SCORING-3 (L5) — RETOUR TERRAIN depuis la fiche : quand la parcelle est suivie, UN clic
  // pose l'état réel après contact (même étiquette que la carte Kanban — par compte, réversible).
  const etiqueter = useMutation({
    mutationFn: (key: string) => patchPipeline(state.data!.entry!.id, { contact_etiquette: key }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['pipeline-parcel', idu] })
      qc.invalidateQueries({ queryKey: ['pipeline'] })
    },
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
          {!cols.length && <div className="px-2 py-1.5 text-[12px] text-txt-mut">Chargement…</div>}
        </div>
      )}
      {/* SCORING-3 (L5) — sélecteur de retour terrain (visible dès que la parcelle est suivie) */}
      {inPipe && state.data?.entry && (
        <select
          data-contact-etiquette
          value={state.data.entry.contact_etiquette ?? ''}
          onChange={(ev) => etiqueter.mutate(ev.target.value)}
          disabled={etiqueter.isPending}
          className={`mt-1.5 w-full cursor-pointer rounded-md border bg-surface-2 px-1.5 py-1 text-[11px] focus:outline-none focus:ring-1 focus:ring-mint/50 ${state.data.entry.contact_etiquette ? 'border-mint/40 text-txt' : 'border-line-2 text-txt-dim'}`}
        >
          <option value="">— retour terrain ?</option>
          {(meta.data?.contact_etiquettes ?? []).map((et) => (
            <option key={et.key} value={et.key}>{et.label}</option>
          ))}
        </select>
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
          {projetsQ.isLoading && <div className="px-1 py-2 text-txt-dim">Chargement…</div>}
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
  // RETOURS-8 (R7) — la fiche en ONGLETS : Analyse (la fiche détaillée), Autour (le voisinage isochrone),
  // Actions (CRM · Projet · Courrier · exports) — accès direct aux actions sans faire défiler l'analyse.
  // RETOURS-9 (Q8.1) — onglets de fiche retirés : plus d'état d'onglet, la fiche défile d'un tenant.
  // M61 P1 — panneau IA unifié : 'aucun' = les deux boutons ; 'question' = AskBar pleine largeur ;
  // 'synthese' = panneau Synthèse pleine largeur. Le panneau actif REMPLACE la rangée de boutons
  // (ne se pose plus À CÔTÉ). Synthèse : la mutation vit ICI (persiste au repli) → replier puis
  // rouvrir ne relance AUCUN appel IA. Réinitialisée seulement au changement de parcelle.
  const [iaOuvert, setIaOuvert] = useState<'aucun' | 'question' | 'synthese'>('aucun')
  const syntheseM = useMutation({ mutationFn: () => getExplain(idu) })
  useEffect(() => { setIaOuvert('aucun'); syntheseM.reset() }, [idu])  // eslint-disable-line react-hooks/exhaustive-deps
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
  const reglesGabarit: ReactNode = fo?.hauteur_m != null
    ? `${fo.hauteur_m} m max`
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
      <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto overflow-x-clip px-[14px] pb-4 pt-1">
      {/* FINITIONS-2 (retour Vic) — le STICKY de l'en-tête (introduit en FINITIONS-1 P12, affiné P3) est
          ANNULÉ : retour EXACT au comportement d'origine — l'en-tête défile avec le reste (un seul corps
          `overflow-y-auto`), la carte `.head` contient identité + adresse + les 6 tuiles, sans collage. */}
      <div style={{ paddingTop: 10 }}>
        <div className="head">
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

          {/* RETOURS-15 U7 — ADRESSE en rangée PLEINE LARGEUR (moins l'icône copier) : une ligne
              tant que ça tient, ellipse avec l'adresse complète au survol (title) sinon. Elle ne
              partage plus sa largeur avec les logos/cloche. M61 P5 — copiable (user-select). */}
          <div className="addr addr-row" data-fiche-adresse>
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
              const s = orient && orient !== 'plat' && e?.pente_moyenne_deg != null ? `pente ${nf(e.pente_moyenne_deg)} °`
                : orient === 'plat' ? 'terrain quasi plat'
                : expo.isLoading ? 'calcul en cours' : 'relief non disponible'
              return { l: 'Exposition', v, s, vide: !orient,
                i: 'Orientation du versant de la parcelle (Nord, Sud-Est…) et sa pente moyenne, calculées sur le modèle d’altitude RGE ALTI (IGN), localement — sans ligne de vue. Remplace la « vue mer » (abandonnée). « — » : relief non disponible sur la parcelle.' } as Tuile
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
        </div>{/* /.head — carte d'en-tête (identité + adresse + bandeau de 6 chiffres), NON sticky (origine) */}
      </div>{/* fin du wrapper d'en-tête (non sticky) — l'en-tête défile avec le reste, comme à l'origine */}
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
        {f && verdict && !verdictRevele && (
          // M56-B6 · DA-FICHE-v6 — bouton d'analyse pleine largeur (.cta, 40px) + légende dessous.
          <>
            <Bouton data-demander-analyse niveau="primaire" ton="vert" className="w-full" onClick={() => revelerVerdict(idu)}>
              {CLIENT.fiche.demanderAnalyse} →
            </Bouton>
            {/* M62-P1 (i) : sous-titre « Le verdict, le score et "pourquoi" — à la demande » RETIRÉ,
                le bouton se suffit (P2). `demanderAnalyseSous` (strings.ts) devient 0-caller. */}
          </>
        )}
        {/* ══════ ANALYSE-1 — CARTE « ANALYSE LABUSE » (nouveau moteur : Score LABUSE + Signal) ══════
            À la demande (verdictRevele). La BANDE en toutes lettres (mot + couleur franche, dominante),
            le Signal de mutation en BADGE SECONDAIRE, et les contributions FR EN ENTIER (ce qui monte /
            ce qui baisse). Aucun chiffre brut de score ni de probabilité. « Analyse incomplète » montre
            sa cause. Le score ne s'affiche QUE sur la fiche et dans l'Analyse (mandat §4). */}
        {f?.analyse_labuse?.bande && verdictRevele && (() => {
          const a = f.analyse_labuse!
          const bm = BANDE_META[a.bande as keyof typeof BANDE_META]
          const sm = a.signal_niveau ? SIGNAL_META[a.signal_niveau as keyof typeof SIGNAL_META] : null
          const nc = a.bande === 'NC'
          if (!bm) return null
          return (
            <div data-analyse-labuse-card style={{ marginTop: 8, background: `${bm.color}12`, border: `1px solid ${bm.color}59`, borderRadius: 6, padding: '13px 16px' }}>
              <p style={{ margin: 0, fontSize: 10, letterSpacing: 1.4, color: 'var(--lab)', textTransform: 'uppercase' }}>Analyse LABUSE</p>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginTop: 6, flexWrap: 'wrap' }}>
                <span data-fiche-bande={a.bande} style={{ fontSize: 22, fontWeight: 600, color: bm.color, lineHeight: 1 }}>{bm.label}</span>
                {sm && !nc && (
                  <span data-fiche-signal={a.signal_niveau}
                    style={{ fontSize: 11, fontWeight: 500, color: sm.color, border: `1px solid ${sm.color}66`, borderRadius: 9999, padding: '2px 8px' }}>{sm.label}</span>
                )}
              </div>
              {nc && a.cause && (
                <p data-fiche-cause style={{ margin: '9px 0 0', fontSize: 12, color: BANDE_META.NC.color }}>Analyse incomplète — {a.cause}.</p>
              )}
              {!nc && a.contributions && a.contributions.length > 0 && (
                <div data-fiche-contributions style={{ marginTop: 11, display: 'flex', flexDirection: 'column', gap: 4 }}>
                  <p style={{ margin: 0, fontSize: 10, letterSpacing: 1, color: 'var(--txt-off)', textTransform: 'uppercase' }}>Ce qui compte</p>
                  {a.contributions.map((c, i) => {
                    const up = c.sens === 'hausse'
                    return (
                      <span key={i} style={{ display: 'inline-flex', alignItems: 'flex-start', gap: 6, fontSize: 12, color: up ? '#5CE6A1' : '#C08A6E' }}>
                        <span aria-hidden style={{ fontSize: 9, fontWeight: 700, marginTop: 2 }}>{up ? '▲' : '▼'}</span>
                        <span style={{ color: 'var(--txt-dim)' }}>{c.libelle}</span>
                      </span>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })()}
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
            {/* M-RENOUV : badge segment Renouvellement (CUIVRE) — le verdict reste « Écartée » ;
                libellé doctrinal sous le badge, jamais « opportunité ». */}
            {f.renouvellement && (
              <div data-renouv-badge style={{ margin: '13px 0 0', paddingTop: 12, borderTop: `1px solid ${verdict.color}33` }}>
                <span style={{ fontSize: 11, fontWeight: 600, background: RENOUV.bg, color: RENOUV.txt, border: `1px solid ${RENOUV.border}`, borderRadius: 6, padding: '3px 9px', alignSelf: 'flex-start' }}>
                  Densifier l’existant — rang {fmtInt(f.renouvellement.rang_segment)}/{fmtInt(f.renouvellement.total_segment)}
                </span>
                <p data-renouv-libelle style={{ margin: '6px 0 0', fontSize: 11, color: 'var(--txt-dim)' }}>{f.renouvellement.libelle}</p>
                {/* M61 P4 — « Pourquoi ce rang » dépliable JUSTE À CÔTÉ du rang (comme « Pourquoi ce
                    score » sous le verdict) ; l'ancienne section basse « RENOUVELLEMENT — POURQUOI CE
                    RANG » est absorbée ici (aucune donnée nouvelle). */}
                <details data-renouv-pourquoi style={{ marginTop: 8 }}>
                  <summary style={{ cursor: 'pointer', fontSize: 11.5, color: RENOUV.txt, fontWeight: 600 }}>Pourquoi ce rang</summary>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 8 }}>
                    <p style={{ margin: 0, fontSize: 11.5, lineHeight: 1.5, color: 'var(--txt-dim)' }}>
                      {f.renouvellement.libelle} — écartée du classement principal ({RENOUV_CODE_LABEL[f.renouvellement.code_bati_origine] ?? f.renouvellement.code_bati_origine}),
                      mais en zone {f.renouvellement.zone_plu ?? '—'} avec une capacité restante réelle.
                    </p>
                    {f.renouvellement.composantes.map((c) => (
                      <div key={c.cle} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <span style={{ flex: 1, fontSize: 11.5, color: REF.name, minWidth: 0 }}>{c.libelle}</span>
                      </div>
                    ))}
                    {/* RETOURS-11F M9 — capacité NETTE des contraintes : on sert la SDP réellement
                        mobilisable (contraintes déduites), avec la brute + la part déduite en mots
                        quand une contrainte s'applique ; jamais un chiffre brut trompeur. */}
                    <MicroTriple items={[
                      f.renouvellement.sdp_nette_m2 != null && f.renouvellement.sdp_nette_m2 > 0
                        ? `SDP nette ${fmtInt(f.renouvellement.sdp_nette_m2)} m²${f.renouvellement.contrainte_pct ? ` (−${f.renouvellement.contrainte_pct} % contraintes)` : ''}`
                        : (f.renouvellement.sdp_residuelle_m2 != null && f.renouvellement.sdp_residuelle_m2 > 0 ? `SDP résiduelle ${fmtInt(f.renouvellement.sdp_residuelle_m2)} m²` : 'SDP résiduelle —'),
                      f.renouvellement.surface_m2 != null ? `assiette ${fmtM2(f.renouvellement.surface_m2)}` : 'assiette —',
                      // OUTILS-FIX-1 C1 — la surélévation n'est plus servie par le segment (batch débranché) ;
                      // le signal vivant reste dans l'onglet Faisabilité. Ici : rang île.
                      `rang île ${fmtInt(f.renouvellement.rang_segment)}/${fmtInt(f.renouvellement.total_segment)}`,
                    ]} />
                    <p style={{ margin: 0, fontSize: 10, color: REF.dim }}>{f.renouvellement.source}</p>
                  </div>
                </details>
              </div>
            )}

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
        {isLoading && (
          <div className="flex flex-col gap-2">
            <Loading label="Chargement de la fiche" className="text-xs" />
            <div className="mt-1 h-16 animate-pulse rounded-lg bg-surface-2" />
            <div className="h-24 animate-pulse rounded-lg bg-surface-2" />
          </div>
        )}
        {isError && (is429(error) ? (
          <RateLimit429 error={error} refetch={refetch} />
        ) : error instanceof ApiError && error.status === 404 ? (
          /* G1 (M12) : une parcelle absente du run (copro non classée, hors périmètre, ou clic
             sur une trame sans idu) N'EST PAS une panne. Message NEUTRE, sans tonalité d'erreur —
             on invite simplement à re-sélectionner une parcelle. Aucun « serveur injoignable ». */
          <div data-fiche-hors-run className="rounded-lg border border-line-2 bg-surface-2 p-4 text-xs">
            <p className="text-txt">Cette parcelle n'est pas dans le périmètre analysé.</p>
            <p className="mt-1 text-txt-dim">Sélectionnez une parcelle sur la carte pour afficher sa fiche.</p>
            <button onClick={() => select(null)} className="mt-2 min-h-7 rounded border border-line-2 px-2 py-1 text-txt transition-colors duration-quick hover:border-mint/60 hover:text-txt-hi">Fermer</button>
          </div>
        ) : (
          <div data-fiche-erreur className="rounded-lg border border-st-ecartee/40 bg-st-ecartee/10 p-4 text-xs">
            {/* Item 3 (UX V1) : wording client — plus jamais « relancer labuse api » face à un
                utilisateur. Le détail technique reste lisible, en ligne discrète. */}
            <p className="text-st-ecartee">Connexion au serveur impossible — vérifiez votre réseau ou réessayez.</p>
            {error instanceof Error && error.message && (
              <p className="mt-1 break-all font-mono text-[10px] text-txt-dim">détail : {error.message}</p>
            )}
            <button onClick={() => refetch()} className="mt-2 min-h-7 rounded border border-line-2 px-2 py-1 text-txt transition-colors duration-quick hover:border-mint/60 hover:text-txt-hi">Réessayer</button>
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
          // Surface → §1 Identité (contenance cadastrale DGFiP).
          const tuileSurface = { v: f.surface_m2 != null ? fmtM2(f.surface_m2) : '—', vide: f.surface_m2 == null,
            i: 'Contenance cadastrale de la parcelle (DGFiP).' }
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
          const tuileExpo = {
            v: expo.isLoading ? '…' : (expoOrient && expoOrient !== 'plat' ? expoOrient : expoOrient === 'plat' ? 'Plat' : '—'),
            s: expoOrient && expoOrient !== 'plat' && expoData?.pente_moyenne_deg != null ? `pente ${nf(expoData.pente_moyenne_deg)} °`
              : expoOrient === 'plat' ? 'terrain quasi plat'
              : expo.isLoading ? 'calcul en cours' : 'relief non disponible',
            vide: !expoOrient,
            i: 'Orientation du versant de la parcelle (Nord, Sud-Est…) et sa pente moyenne, calculées sur le modèle d’altitude RGE ALTI (IGN), localement — sans ligne de vue. Remplace la « vue mer » (abandonnée : 55 h de calcul pour une donnée peu fiable, cf. rapport). « — » : relief non disponible sur la parcelle.' }
          // Taxe foncière → §7 Fiscalité (TFPB part communale, REI DGFiP).
          const tfpb = f.fiscalite?.tfpb_commune_pct
          const tuileTaxe = { v: tfpb != null ? `${nf(tfpb)} %` : '—', s: tfpb != null ? 'part communale' : 'taux non ingéré', vide: tfpb == null,
            i: 'Taux de taxe foncière (TFPB) voté par la commune — fichier REI (DGFiP). C’est la charge annuelle, que le bien soit gardé, loué ou porté. « — » : taux non ingéré pour cette commune.' }
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
            <div data-ia-tete>
              {iaOuvert === 'aucun' && (
                <div className="ia">
                  <Bouton onClick={() => setIaOuvert('question')} data-askbar-open niveau="secondaire" ton="ia" className="flex-1">
                    <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}><path d="M20 4H4v13h5l3 3 3-3h2z" /></svg>
                    Poser une question
                  </Bouton>
                  {/* RETOURS-11 T9 (03/09) — explication au survol retirée (plus de title). */}
                  <Bouton onClick={() => { setIaOuvert('synthese'); if (!syntheseM.data && !syntheseM.isPending) syntheseM.mutate() }}
                    data-synthese-ia niveau="secondaire" ton="ia" className="flex-1">
                    <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}><path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z" /></svg>
                    Synthèse IA
                  </Bouton>
                </div>
              )}
              {iaOuvert === 'question' && <AskBar idu={idu} zone={null} startOpen onClose={() => setIaOuvert('aucun')} />}
              {iaOuvert === 'synthese' && <SyntheseIAPanel data={syntheseM.data} pending={syntheseM.isPending} error={syntheseM.isError} onReplier={() => setIaOuvert('aucun')} />}
            </div>

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
              value={proprioSignal ? shorten(proprioSignal.detail).slice(0, 20) : (f.proprietaire_moral ? proprioType.slice(0, 18) : (f.surface_m2 != null ? fmtM2(f.surface_m2) : 'privé'))}
              micro={proprioPastilles.length ? <MicroPastilles items={proprioPastilles} /> : undefined}>
              <div className="flex flex-col gap-3">
                <ChiffreDissous l="Surface" t={tuileSurface} />
                {/* ⑤ PROPRIÉTÉ (relocalisée §1) — société (M43) + signaux vendeur. */}
                <div className="flex flex-col gap-2">
                {f.proprietaire_moral ? (
                  <div>
                    {/* RETOURS-23 Z3 — plus de card-elev : kicker + fait à plat. */}
                    <GroupLabel>Propriétaire (DGFiP)</GroupLabel>
                    <div className="mt-1 text-xs font-medium text-txt-hi">{f.proprietaire_moral.denomination ?? '—'}</div>
                    <div className="mt-0.5 flex items-center gap-3 text-[10.5px] text-txt-mut">
                      {f.proprietaire_moral.siren && <span className="font-mono">SIREN <Siren value={f.proprietaire_moral.siren} className="font-mono text-txt-mut" /></span>}
                      {f.proprietaire_moral.groupe_label && <span>{f.proprietaire_moral.groupe_label}</span>}
                    </div>
                    {/* RETOURS-11F3 F11 — carte d'identité publique (SIRENE) : activité, siège, création,
                        état actif — faits publics d'entreprise, jamais une personne. */}
                    {f.proprietaire_moral.identite && (
                      <div data-proprio-identite className="mt-1.5 flex flex-col gap-0.5 border-t border-bd/60 pt-1.5 text-[10.5px] text-txt-mut">
                        {f.proprietaire_moral.identite.activite && <div><span className="text-txt-dim">Activité </span><span className="text-txt">{f.proprietaire_moral.identite.activite}</span>{f.proprietaire_moral.identite.ape && <span className="ml-1 font-mono text-txt-dim">({f.proprietaire_moral.identite.ape})</span>}</div>}
                        {f.proprietaire_moral.identite.siege && <div><span className="text-txt-dim">Siège </span><span className="text-txt">{f.proprietaire_moral.identite.siege}</span></div>}
                        <div className="flex gap-3">
                          {f.proprietaire_moral.identite.date_creation && <span><span className="text-txt-dim">Créée </span>{f.proprietaire_moral.identite.date_creation}</span>}
                          {f.proprietaire_moral.identite.actif != null && <span className={f.proprietaire_moral.identite.actif ? 'text-mint' : 'text-st-ecartee'}>{f.proprietaire_moral.identite.actif ? 'active' : 'cessée'}</span>}
                        </div>
                        <div className="text-[9.5px] text-txt-dim italic">{f.proprietaire_moral.identite.source}</div>
                      </div>
                    )}
                    {/* RETOURS-11 F11 — lien vers l'Annuaire des entreprises (fiche INPI/INSEE publique). */}
                    {f.proprietaire_moral.siren && (
                      <a data-annuaire-entreprises target="_blank" rel="noreferrer noopener"
                        href={`https://annuaire-entreprises.data.gouv.fr/entreprise/${f.proprietaire_moral.siren}`}
                        className="mt-1 inline-block text-[10.5px] text-mint underline decoration-dotted">
                        Annuaire des entreprises ↗
                      </a>
                    )}
                    {f.proprietaire_moral.etat_societe && (
                      // M43 — fait public d'entreprise (état société) : on le DIT, on n'en déduit RIEN
                      // (pas de vigilance, pas de badge, pas de filtre). PM only ; jamais la personne.
                      <div className="mt-2 border-t border-bd/60 pt-1.5 text-[10.5px] text-txt-mut">
                        <span className="text-txt-hi">{f.proprietaire_moral.etat_societe.libelle}</span>
                        <span className="ml-1 text-txt-dim">
                          (Sourcé {f.proprietaire_moral.etat_societe.etats.map((e) => e.source).filter((s, i, a) => a.indexOf(s) === i).join(' / ')})
                        </span>
                        <div className="mt-0.5 text-[9.5px] text-txt-dim italic">{f.proprietaire_moral.etat_societe.note}</div>
                      </div>
                    )}
                    {/* M60 P1c — lien inline « voir le patrimoine » retiré : une seule entrée par outil,
                        la PORTE Scan patrimoine est au pied du tiroir (voir plus bas). */}
                  </div>
                ) : (
                  <FactNote>
                    Propriétaire : personne physique ou non recensé au fichier des personnes morales
                    (identité nominative : workflow SPF/CERFA, jamais automatisée).
                    {/* M70 point 7a — le lien texte SPF devient une PORTE-OUTIL en pied de tiroir
                        (voir plus bas). L'outil courrier (M09, pré-rempli sur la parcelle) est inchangé. */}
                  </FactNote>
                )}
                {proprioLines.length > 0 && <div className="flex flex-col gap-1">{proprioLines.map((l, i) => <Line key={i} line={l} hideWeight hideDate />)}</div>}
                {/* L1 (KF-2) — historique du propriétaire moral par millésime + diff constaté (hors
                    scoring). R6 : `pm` dit au composant si la parcelle a un propriétaire moral —
                    absence de timeline = ligne honnête (PM) ou silence justifié (PP). */}
                <ProprietaireHistorique h={f.proprietaire_historique} pm={!!f.proprietaire_moral} />
                {/* M125-2 — copropriété(s) RNIC rattachées (donnée réelle, cible bailleur/copro) */}
                {f.coproprietes && f.coproprietes.length > 0 && <CoproprietesBlock copros={f.coproprietes} />}
                {/* M60 P1c — PORTE en pied : Scan patrimoine PRÉ-REMPLI (SIREN du propriétaire). */}
                {f.proprietaire_moral?.siren && (
                  <PorteOutil ico="⌂" data="patrimoine" titre="Scan patrimoine du propriétaire"
                    sous={`Tout le foncier de ${f.proprietaire_moral.denomination ?? 'ce propriétaire'} · SIREN ${f.proprietaire_moral.siren}`}
                    onClick={() => { setM02Prefill(f.proprietaire_moral!.siren!); setModule('patrimoine') }} />
                )}
                {/* M70 point 7a — PORTE en pied : Courrier SPF (personne physique / non recensée). */}
                {!f.proprietaire_moral && (
                  <PorteOutil ico="✉" data="spf-letter" titre={CLIENT.fiche.export.spf}
                    sous="Courrier pré-rempli à envoyer au SPF pour identifier le propriétaire."
                    onClick={() => { setCourrierPrefill(idu); setModule('courriers') }} />
                )}
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
                <ChiffreDissous l="Pente" t={tuilePente} />
                <ChiffreDissous l="Exposition" t={tuileExpo} />
                {/* FICHE-RANGEMENT-3 Lot 5 — AZIMUT du versant (aspect_deg, MNT RGE ALTI) : le cap
                    précis derrière l'orientation lisible (0° = Nord, sens horaire). */}
                {expoData?.aspect_deg != null && (
                  <div data-terrain-azimut>
                    <FactRow label="Azimut du versant"
                      value={<>{nf(expoData.aspect_deg)} <small>° (0 = Nord, sens horaire)</small></>}
                      src="RGE ALTI (IGN) — MNT" />
                  </div>
                )}
                <TerrainDuBienBlock f={f} />
                <EquipementsBadges idu={idu} />
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
                {f.plu_fraicheur?.libelle && (
                  <div data-plu-fraicheur={f.plu_fraicheur.statut}>
                    <Vigilance tone={f.plu_fraicheur.statut === 'a_jour' ? 'mint' : 'creuser'}
                      title={<><span className="mr-1">{f.plu_fraicheur.statut === 'a_jour' ? '🕓' : '▲'}</span>{f.plu_fraicheur.document_servi || f.plu_fraicheur.libelle}</>}>
                      {f.plu_fraicheur.document_servi ? (
                        <>
                          {f.plu_fraicheur.fait_foi && (
                            <span className="block text-[10px] text-txt-dim">✓ {f.plu_fraicheur.fait_foi}</span>
                          )}
                          {f.plu_fraicheur.en_cours && (
                            /* M57-P1 (d) : a_jour → avertissement NEUTRE ; les autres statuts portent une
                               procédure RÉELLE → « En cours (non servi) » conservé. */
                            f.plu_fraicheur.statut === 'a_jour'
                              ? <span className="block text-[10px] text-txt-dim">{f.plu_fraicheur.en_cours}</span>
                              : <span className="block text-[10px] text-st-creuser">⏳ En cours (non servi) : {f.plu_fraicheur.en_cours}</span>
                          )}
                          {f.plu_fraicheur.action && (
                            <span className="block text-[10px] text-txt-mut">→ {f.plu_fraicheur.action}</span>
                          )}
                        </>
                      ) : (
                        f.plu_fraicheur.note && f.plu_fraicheur.statut !== 'a_jour'
                          ? <span className="block text-[10px] text-txt-dim">{f.plu_fraicheur.note}</span>
                          : null
                      )}
                    </Vigilance>
                  </div>
                )}
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
                {/* M60 P1c — PORTES en pied d'Urbanisme : les liens Annuaire PLU + lettre de zonage
                    REPRIS en forme porte (.porte-outil), accroches contextualisées (zone PLU). */}
                {/* M137-P — les 3 outils PLU fusionnés dans le hub « plu » : la porte Annuaire ouvre le
                    hub PRÉ-REMPLI sur l'Annuaire (pluPrefill : commune + zone servie). */}
                <PorteOutil ico="§" data="annuaire" titre="Annuaire PLU de la commune"
                  sous={reglesZone ? `Le règlement de la zone ${reglesZone} — articles, prescriptions` : 'Le règlement PLU de la commune'}
                  onClick={() => { setPluPrefillF({ insee: idu.slice(0, 5), zone: reglesZone ?? null }); setModule('plu') }} />
                {/* EXPORTS-2 lot 8 — « Lettre de vérification de zonage » supprimée (décision Vic
                    07/09) : la section 2 du Dossier couvre le zonage entièrement. */}
                {/* M70 déc. 9 — PORTE Vérif procédure PLU dans Urbanisme (grille terminale supprimée).
                    L'outil lit selectedIdu (préservé par setModule) → pré-rempli sur la parcelle. */}
                <PorteOutil ico="⚖" data="verif-procedure" titre="Vérif procédure PLU"
                  sous={reglesZone ? `Commune en procédure ? (zone ${reglesZone})` : 'La commune est-elle en procédure PLU ?'}
                  onClick={() => { setPluVueF('procedure'); setModule('plu') }} />
                {/* RTAA DOM (§4) — rappel réglementaire de conception, servi par le bilan (b.rtaa). */}
                <RtaaFromBilan idu={idu} />
                {/* Dispositifs et périmètres (§4) — ER / EBC / doc urba / DPU / PEB / SUP (SOURCES-1 lot 1). */}
                {f.dispositifs && <DispositifsBody d={f.dispositifs} />}
                {/* FICHE-RANGEMENT-2 Lot 1 — mixité sociale (SMS) : quota + seuil NON RENSEIGNÉS (non
                    extraits du règlement de zone GPU à ce jour ; cf. FICHE-RANGEMENT-1 lot 2, data absente). */}
                <div data-mixite>
                  <GroupLabel>Mixité sociale (LLS)</GroupLabel>
                  <FactRow label="Quota de logements sociaux" tone="mute" value="non renseigné" />
                  <FactRow label="Seuil de déclenchement" tone="mute" value="non renseigné" />
                  <FactNote>Servitude de mixité sociale — non extraite du règlement de zone GPU à ce jour (en attente).</FactNote>
                </div>
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
                <ChiffreDissous l="Taxe foncière" t={tuileTaxe} />
                {/* Fiscal & leviers (QPV / TVA / note taxe) — levier fiscal du bilan (§7). */}
                <FiscalLeviersBlock idu={idu} />
                {/* FICHE-1 lot 5 — taxe d'aménagement estimée + porte pour changer les hypothèses (§7). */}
                {f.taxe_amenagement && <TaxeAmenagementBlock t={f.taxe_amenagement} />}
                {f.taxe_amenagement && (
                  <PorteOutil ico="€" data="taxe-amenagement-outil" titre="Taxe d'aménagement"
                    sous="Changer les hypothèses (résidence principale, logement aidé, piscine, taux communal)"
                    onClick={() => { setParcelPrefill(idu); setModule('taxe-amenagement') }} />
                )}
                {/* M106 P3 — DISPOSITIFS TERRITORIAUX (ZFANG / FRR ex-ZRR) relocalisés §7 : attribut de
                    COMMUNE, états sourcés + lien texte. JAMAIS un chiffre fiscal (le fiscaliste tranche). */}
                {f.territoire_fiscal && (
                  <div className="flex flex-col gap-2.5" data-territoire-fiscal>
                    <GroupLabel>Dispositifs territoriaux</GroupLabel>
                    {/* RETOURS-23 Z3 — chaque dispositif est un fait à plat (titre · détail · source en
                        note). Le périmètre fin qui touche LA parcelle (QPV / bande TVA 500 m) garde un
                        filet gauche mint (marqueur, pas un cadre). Données/libellés/sources inchangés. */}
                    {(f.territoire_fiscal.perimetres ?? []).map((p) => (
                      <div key={p.libelle} data-fiche-perimetre className="border-l-2 border-mint pl-3">
                        <p className="text-[12px] font-semibold text-txt-hi">{p.libelle}{p.derive && <span className="ml-1.5 rounded bg-surface-2 px-1 py-px text-[9px] uppercase tracking-wide text-txt-dim">estimé</span>}</p>
                        <p className="mt-0.5 text-[11.5px] leading-snug text-txt">{p.detail}</p>
                        <FactNote>{p.source}</FactNote>
                      </div>
                    ))}
                    {([['ZFANG — zone franche d’activité', f.territoire_fiscal.zfang],
                       ['FRR — France Ruralités Revitalisation (ex-ZRR)', f.territoire_fiscal.frr]] as const)
                      .filter(([, a]) => !!a).map(([titre, a]) => (
                      <div key={titre}>
                        <p className="text-[12px] font-semibold text-txt-hi">{titre}</p>
                        <p className="mt-0.5 text-[11.5px] leading-snug text-txt">{a!.libelle}</p>
                        <FactNote>{a!.source_ref} · <a href={a!.lien} target="_blank" rel="noreferrer" className="underline hover:text-mint">voir le texte</a></FactNote>
                      </div>
                    ))}
                    {/* RETOURS-11F3 F10 — dispositifs valables sur TOUTE La Réunion (zonage B1, TVA DOM
                        8,5 % / 2,1 % LLS). Repères, jamais un calcul fiscal. */}
                    {(f.territoire_fiscal.dispositifs_dom ?? []).map((d) => (
                      <div key={d.libelle} data-dispositif-dom>
                        <p className="text-[12px] font-semibold text-txt-hi">{d.libelle}</p>
                        <p className="mt-0.5 text-[11.5px] leading-snug text-txt">{d.detail}</p>
                        <FactNote>{d.source}</FactNote>
                      </div>
                    ))}
                    {f.territoire_fiscal.avertissement && (
                      <FactNote>{f.territoire_fiscal.avertissement}</FactNote>
                    )}
                  </div>
                )}
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
                <ChiffreDissous l="SDP restante" t={tuileSdp} />
                {/* RETOURS-20 Z5 — l'alerte « délaissé » = une Vigilance (filet ambre). */}
                {faisa.data?.delaisse && <div data-delaisse><Vigilance title={faisa.data.delaisse.libelle} /></div>}
                {f.potentiel_transformation && <TransformationBlock pt={f.potentiel_transformation} />}
                {/* FICHE-PORTES-1 Lot 2 — porte « Densifier l'existant » (MR1) : à la suite de la SDP
                    consommée (potentiel de densification). Outil à la maille commune → contexte = la
                    commune de la parcelle. */}
                {f.commune && (
                  <PorteOutil ico="◫" data="renouvellement" titre="Densifier l'existant"
                    sous={`Le bâti en zone U de ${f.commune} qui peut porter davantage`}
                    onClick={() => { const st = useApp.getState(); st.setCommune(f.commune!); st.setCommunesFilter([f.commune!]); st.setModule('renouvellement') }} />
                )}
                <FaisabiliteTab idu={idu} />
                {/* GABARIT-2 — ligne « Gabarit réglementaire » : zone d'implantation / plafond /
                    hauteur (citée de §4) + mini-plan 2D, ou « Calcul incomplet » + motif. */}
                <GabaritLine idu={idu} />
              </div>
            </RefDrawer>

            {/* ⑪ SIMULATION — la charge foncière (bilan) + la Réhabilitation (Mode B, FICHE-RANGEMENT-3
                Lot 3 : rentrée DANS §11, plus un 12e tiroir) + les outils de projet (Faisabilité,
                Calculette, Assemblage). 11 tiroirs au total. */}
            <RefDrawer id="simulation" icon={IC.confiance} name="Simulation"
              context="charge foncière · réhabilitation · outils projet"
              value={<Badge ton="vert">bilan</Badge>}>
              <div className="flex flex-col gap-3">
                <BilanTab idu={idu} />
                {/* Réhabilitation (Mode B) — bloc inline (ModeBBody), plus un tiroir séparé. */}
                {f.mode_b?.indisponible
                  ? <BlocIndisponible titre="Réhabilitation (Mode B)" />
                  : f.mode_b?.disponible && <ModeBBody idu={idu} initial={f.mode_b} />}
                <PorteOutil ico="◱" data="faisabilite-outil" titre="Faisabilité"
                  sous={`La capacité constructible de ces ${fmtM2(f.surface_m2)} : SDP, hauteur PLU, calcul tracé`}
                  onClick={() => { setParcelPrefill(idu); setModule('programme') }} />
                <PorteOutil ico="▦" data="calculette" titre="Calculette foncière"
                  sous={`Ce terrain de ${fmtM2(f.surface_m2)} : SDP, prix de sortie, votre coût et marge`}
                  onClick={() => { setCalcPrefill(idu); setModule('calculette-fonciere') }} />
                <PorteOutil ico="⧉" data="assemblage-outil" titre="Assemblage"
                  sous={`Partir de ces ${fmtM2(f.surface_m2)} et agréger les parcelles contiguës`}
                  onClick={() => { setParcelPrefill(idu); setModule('assemblage') }} />
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
// M61 P1 — PANNEAU synthèse (plus un bouton) : pleine largeur, markdown rendu (renderRich), bouton
// « Replier ». La mutation est portée par la fiche (SyntheseIAPanel ne fait AUCUN appel) → replier
// puis rouvrir n'exécute rien. Les états en cours / erreur s'affichent aussi pleine largeur.
function SyntheseIAPanel({ data: d, pending, error, onReplier }: {
  data?: Awaited<ReturnType<typeof getExplain>>; pending: boolean; error: boolean; onReplier: () => void
}) {
  const box = { marginTop: 8, background: '#110d1b', border: '1px solid #372c58', borderRadius: 6, padding: '11px 14px' } as const
  const stub = d && !d.available
  const rs = d?.rules_summary
  return (
    <div data-synthese-ia-result style={box}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
        <p style={{ margin: 0, fontSize: 11, fontWeight: 600, color: '#c9b6f2', display: 'flex', alignItems: 'center', gap: 6 }}>
          {CLIENT.fiche.ia.synthese}
          {stub && <span data-synthese-stub style={{ fontSize: 9.5, fontWeight: 500, color: '#b7a3e6', border: '1px solid #47386e', borderRadius: 4, padding: '1px 5px' }}>repli</span>}
        </p>
        <button data-synthese-replier onClick={onReplier}
          style={{ background: 'none', border: '1px solid #372c58', borderRadius: 6, color: '#b7a3e6', fontSize: 11, padding: '2px 9px', cursor: 'pointer', flexShrink: 0 }}>Replier</button>
      </div>
      {pending ? (
        <p style={{ margin: '8px 0 0', color: '#c9b6f2', fontSize: 12 }}><span style={{ display: 'inline-block', width: 6, height: 6, marginRight: 8, borderRadius: 6, background: '#8a6ff0' }} className="animate-pulse" />{CLIENT.fiche.ia.syntheseEnCours}</p>
      ) : error ? (
        <p style={{ margin: '8px 0 0', color: '#E8695A', fontSize: 12 }}>{CLIENT.fiche.ia.syntheseErreur}</p>
      ) : (
        <>
          <div style={{ margin: '7px 0 0', fontSize: 12, lineHeight: 1.5, color: '#d8ccf5' }}>{renderRich((d?.available ? d.explanation : d?.message) ?? '')}</div>
          {stub && Array.isArray(rs) && rs.length > 0 && <ul style={{ margin: '6px 0 0', paddingLeft: 16, fontSize: 11.5, lineHeight: 1.5, color: '#c9b6f2' }}>{rs.map((r, i) => <li key={i}>{r}</li>)}</ul>}
          {stub && typeof rs === 'string' && rs && <div style={{ margin: '6px 0 0', fontSize: 11.5, lineHeight: 1.5, color: '#c9b6f2' }}>{renderRich(rs)}</div>}
          {stub && <p style={{ margin: '7px 0 0', fontSize: 10, color: '#8f80b8' }}>{CLIENT.fiche.ia.syntheseStub}</p>}
        </>
      )}
    </div>
  )
}


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


