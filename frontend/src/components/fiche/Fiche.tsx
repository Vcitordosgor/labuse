import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Tip } from '../Tip'
import { Siren } from '../shared/Siren'   // RETOURS-12 T2 — SIREN cliquable Pappers
import { useEffect, useMemo, useState, useRef, type ReactNode } from 'react'
import { addToPipeline, ajouterParcelle, ApiError, createProjet, getDossierStatut, getExplain, getFaisabilite, getFiche, getMoi, getPipelineForParcel, getPipelineMeta, getProjets, getWatch, is429, patchPipeline, pdfUrl, postSignalement, preDossierUrl, projetsPourParcelle, radarClic, toggleWatch } from '../../lib/api'
import { verdictMeta } from '../../lib/status'
import { fmtInt, fmtM2, fmtLibelleBrut, iduComplet } from '../../lib/format'
import { layerLabel } from '../../lib/layers'
import { Trace } from '../../lib/trace'
import { CLIENT } from '../../lib/strings'
import { Loading } from '../Loading'
import { AskBar, renderRich } from './AskBar'
import { cadastreGeoportailUrl, googleMapsUrl, pagesJaunes } from './liensExternes'
import { LogoCadastre, LogoPagesJaunes, LogoGoogleMaps } from './logosServices'
import { PourquoiPasTab } from './PourquoiPas'
import { ScoreV2Block } from './ScoreV2Block'
import { BlocIndisponible } from './BlocIndisponible'
import { CoproprietesBlock } from './CoproprietesBlock'
import { ProprietaireHistorique } from './ProprietaireHistorique'
import type { FicheLine, FicheZoneDestinations, IcdBlock, Onglet, ReglementPlu } from '../../lib/types'
import { DestinationBadge } from '../outils/DestinationSelect'   // DESTINATIONS-1 (X4.2) — pastille contour partagée
import { useApp } from '../../store/useApp'
import { GrilleOutils, OutilCase } from '../shared/GrilleOutils'   // PROJETS-V5 (E9) — grille d'outils partagée
import { REF, RENOUV, RENOUV_CODE_LABEL, IC, FicheAccordionCtx, RefDrawer, GroupLabel, MicroJauge, MicroPastilles, MicroTriple, RateLimit429, Line, EligibiliteReplie, icdColor, PorteOutil } from './primitives'
// RETOURS-11F4 (F5) — la section Constructibilité + sa machinerie vivent dans `constructibilite.tsx`.
// Fiche ré-exporte Calculette + FaisabiliteTab (consommés par EtudierBien / M22Programme / le test).
import { ConstructibiliteSection } from './constructibilite'
import { RisquesSection } from './risques'
import { MarcheSection } from './marche'
import { ReseauxSection } from './reseaux'
import { AutourSection } from './autour'
export { Calculette, FaisabiliteTab } from './constructibilite'
export type { CalcResult } from './constructibilite'


function IcdBlockView({ icd }: { icd: IcdBlock }) {
  const [open, setOpen] = useState(false)
  const color = icdColor(icd.bande)
  return (
    <div data-icd className="card-elev">
      {/* M70 décision 5 — plus de jauge ni de score chiffré (une seule jauge dans la fiche = l'ICD
          n'en est plus une : verdict qualitatif). La barre et le nombre {icd.score} sont retirés ;
          reste le verdict `icd.libelle` (« confiance haute »). Le détail (couches manquantes) déplie. */}
      <button onClick={() => setOpen((o) => !o)} className="flex w-full items-center gap-3 px-3 py-2.5"
        title="Confiance données : déplier le détail">
        <Tip tip="Complétude des couches de données pour cette parcelle — n'entre pas dans le score d'opportunité (P, calculé indépendamment)." className="shrink-0">
          <span className="text-left text-xs text-txt underline decoration-dotted decoration-line-2 underline-offset-4">Confiance données</span>
        </Tip>
        <span data-icd-verdict className="ml-auto shrink-0 rounded-full px-2 py-0.5 text-[10.5px] font-semibold"
          style={{ background: `${color}1f`, color }}>{icd.libelle}</span>
        <span className="shrink-0 text-txt-dim">{open ? '▾' : '▸'}</span>
      </button>
      {open && (
        <div className="border-t border-line-2 px-3 py-2">
          {/* M70 : le verdict `icd.libelle` est déjà dans l'en-tête — plus de doublon ici. */}
          {icd.manquants.length > 0 ? (
            <>
              <p className="label-caps mt-2 pb-1">Ce qui manque</p>
              <ul data-icd-manquants className="flex flex-col gap-0.5">
                {icd.manquants.map((m, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-[11px] text-txt-mut"><span className="text-st-ecartee">•</span>{m}</li>
                ))}
              </ul>
            </>
          ) : <p className="mt-2 text-[11px] text-txt-dim">Toutes les couches de données sont présentes pour cette parcelle.</p>}
          <p className="mt-2 text-[10px] leading-snug text-txt-dim">{icd.cloisonnement}</p>
        </div>
      )}
    </div>
  )
}

// ── M9 lot 4 — Potentiel de transformation (fond de l'ancien outil Mutabilité) ──
function ZoneDestinationsLigne({ d }: { d: FicheZoneDestinations }) {
  const [open, setOpen] = useState(false)
  // phrase seule (non calibrée / zone non lue) — dite telle quelle, rien à déplier
  if (d.phrase && !d.lignes?.length) {
    return <p data-fiche-destinations className="mt-1 text-[10.5px] text-txt-mut">Destinations · {d.phrase}</p>
  }
  const resume = [
    d.autorisees?.length ? `${d.autorisees.length} autorisée${d.autorisees.length > 1 ? 's' : ''} (${d.autorisees.slice(0, 3).join(', ')}${d.autorisees.length > 3 ? '…' : ''})` : null,
    d.interdites?.length ? `${d.interdites.length} interdite${d.interdites.length > 1 ? 's' : ''}` : null,
    d.sous_conditions?.length ? `${d.sous_conditions.length} sous condition` : null,
    d.seuil_commerce_m2 != null
      ? `commerce ≤ ${fmtInt(d.seuil_commerce_m2)} m²${d.seuil_commerce_type === 'emprise_sol' ? ' (emprise au sol)' : ''}` : null,
  ].filter(Boolean).join(' · ')
  return (
    <div data-fiche-destinations className="mt-1">
      <button onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-1.5 rounded px-1 py-0.5 text-left text-[10.5px] text-txt-mut transition-colors duration-quick hover:bg-surface-3 hover:text-txt">
        <span className="text-mint">{open ? '▾' : '▸'}</span>
        <span className="min-w-0 flex-1 truncate"><b className="text-txt">Destinations</b>{resume ? ` · ${resume}` : ''}</span>
      </button>
      {open && (
        <div className="mt-1 flex flex-col gap-1 border-l border-line-2 pl-2.5">
          {d.lignes!.map((l) => (
            <div key={l.sous_destination} className="flex items-start gap-2">
              <DestinationBadge etat={l.statut_effectif} />
              {/* la phrase SERVIE, telle quelle (libellé + verdict + article/page/millésime + CDAC) */}
              <span className="min-w-0 flex-1 text-[10.5px] leading-snug text-txt-mut">{l.phrase}</span>
            </div>
          ))}
          {(d.millesime || d.referentiel) && (
            <p className="text-[9.5px] leading-snug text-txt-dim">
              {d.millesime ? `PLU millésime ${d.millesime}` : ''}
              {d.millesime && d.referentiel ? ' · ' : ''}
              {d.referentiel ? `référentiel : ${d.referentiel}` : ''}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

// ── M9 lot 2 — Lien règlement PLU par zone ──────────────────────────────────
function ReglementPluBlock({ rp }: { rp: ReglementPlu }) {
  if (rp.indisponible) return <BlocIndisponible titre="Règlement PLU" />   // M125 — panne ≠ absence
  // M76 pt5 : plus de lien-module ici — l'Annuaire PLU passe par sa porte (tiroir Urbanisme).
  // M62-P1 (j) : la phrase d'explication (`note`) était répétée par zone alors qu'elle est
  // identique pour les deux → une seule fois, en gris, sous les lignes. Si les notes diffèrent,
  // on reste par zone (repli honnête).
  const notes = rp.zones.map((z) => z.note).filter(Boolean) as string[]
  const noteCommune = notes.length === rp.zones.length && notes.every((n) => n === notes[0]) ? notes[0] : null
  return (
    <div data-reglement-plu className="card-elev px-3 py-2.5">
      <p className="label-caps">Règlement PLU</p>
      {/* M62-P1 (j) : tout aligné à gauche, UNE ligne par zone — pastille + zone + liens
          (Voir l'article ↗ · Annuaire PLU →) sur la même ligne ; la phrase d'explication dessous,
          en gris, une seule fois si elle est identique pour les deux zones. */}
      <div className="mt-1.5 flex flex-col gap-1.5">
        {rp.zones.map((z, i) => (
          <div key={i}>
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-left">
              {/* CIRCUIT-2 lot 5.2 — la LETTRE DE ZONE porte l'étiquette de traçage (classe) */}
              <Trace id="zone_plu_famille">
                <span className="rounded-md bg-surface-3 px-1.5 py-0.5 font-mono text-[11px] text-txt">{z.zone}</span>
              </Trace>
              {z.url && <a data-plu-link href={z.url} target="_blank" rel="noreferrer" className="text-[11px] text-mint hover:underline">
                {z.calibree ? 'Voir l’article' : 'Voir le règlement'} ↗
              </a>}
              {/* M76 pt5 (arbitrage Vic) : lien violet « Annuaire PLU → » retiré — doublon de la porte
                  « Annuaire PLU de la commune » (grammaire officielle M60). Une action, une seule forme. */}
            </div>
            {/* RETOURS-11F3 F4 — le TABLEAU des règles de la zone AVEC leurs VALEURS (hauteur, emprise,
                reculs, pleine terre, stationnement), chacune avec sa source (article/page cliquable).
                Remplace la liste d'articles nue (« références sans valeurs » de l'audit O1). « non
                réglementé » (le PLU ne fixe pas de règle) et « à vérifier » sont dits, jamais comblés. */}
            {z.regles_valeurs && z.regles_valeurs.length > 0 ? (
              <ul className="mt-1 flex flex-col gap-0.5">
                {z.regles_valeurs.map((rv, j) => (
                  <li key={j} className="flex items-baseline gap-2 text-[10.5px]">
                    <span className="w-40 shrink-0 text-txt-dim">{rv.libelle}</span>
                    <span className={rv.etat === 'chiffre' || rv.etat === 'texte' ? 'font-medium text-txt' : 'italic text-txt-dim'}>
                      {rv.valeur}
                    </span>
                    {rv.reference && (rv.url
                      ? <a href={rv.url} target="_blank" rel="noreferrer" className="ml-auto shrink-0 text-txt-dim hover:text-mint hover:underline" title={rv.reference}>{rv.reference.split(',')[0].replace(/^Zone \S+ /, '').trim() || 'source'} ↗</a>
                      : <span className="ml-auto shrink-0 text-txt-dim" title={rv.reference}>{rv.reference.split(',')[0]}</span>)}
                  </li>
                ))}
              </ul>
            ) : z.articles.length > 0 && (
              <ul className="mt-1 flex flex-col gap-0.5">
                {z.articles.slice(0, 6).map((a, j) => (
                  <li key={j} className="text-[10.5px] text-txt-mut">
                    <a href={a.url ?? z.url ?? '#'} target="_blank" rel="noreferrer" className="hover:text-mint hover:underline" title={a.reference}>{a.reference}</a>
                  </li>
                ))}
              </ul>
            )}
            {/* DESTINATIONS-1 (X4.2) — la ligne « Destinations » de la zone (résumé + dépliable). */}
            {z.destinations && <ZoneDestinationsLigne d={z.destinations} />}
            {/* note par zone UNIQUEMENT si elles diffèrent (sinon rendue une fois plus bas) */}
            {z.note && !noteCommune && <p className="mt-0.5 text-[10px] text-txt-dim">{z.note}</p>}
          </div>
        ))}
      </div>
      {noteCommune && <p className="mt-1.5 text-[10px] leading-snug text-txt-dim">{noteCommune}</p>}
      <p className="mt-1.5 text-[10px] leading-snug text-txt-dim">{rp.disclaimer}</p>
    </div>
  )
}

// RETOURS-11 F2 — id de tiroir (RefDrawer) → libellé de section, pour tagger le signalement
// avec « la section ouverte » (jamais une clé technique à l'écran).
const SECTION_LABELS: Record<string, string> = {
  regles: 'Urbanisme',
  faisabilite: 'Constructibilité',
  'mode-b': 'Constructibilité',
  risques: 'Risques et protections',
  marche: 'Marché et secteur',
  reseaux: 'Réseaux et accès',
  autour: 'Autour de cette parcelle',
  dispositifs: 'Dispositifs territoriaux',
  proprio: 'Propriétaire',
  donnees: 'Données et méthode',
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
          className="rounded-md bg-mint px-3 py-1 text-xs font-medium text-mint-ink disabled:opacity-50">
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
      title={on ? CLIENT.fiche.suivreActif : CLIENT.fiche.suivre}>
      <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M10 5a2 2 0 1 1 4 0a7 7 0 0 1 4 6v3a4 4 0 0 0 2 3H4a4 4 0 0 0 2-3v-3a7 7 0 0 1 4-6" /><path d="M9 17v1a3 3 0 0 0 6 0v-1" /></svg>
    </button>
  )
}

// EXPRESS-01 · bouton « copier l'IDU » — copie la chaîne BRUTE 14 car. (sans espace),
// celle qu'on colle dans GPU/DVF/SIG. Style référence (bouton 31×31, retour visuel vert).
// M61 P5 — bouton « copier » discret, réutilisable (IDU + adresse). Libellés paramétrables.
function CopyIdu({ value, aria = 'Copier l’IDU', titre = 'Copier l’IDU (14 caractères, sans espace)', okTitre = 'IDU copié', dataAttr = 'idu' }: {
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
      style={{ border: 'none', background: 'none', padding: 2, display: 'flex', alignItems: 'center', justifyContent: 'center', color: ok ? 'var(--mint)' : 'var(--txt-ghost)', cursor: 'pointer', flexShrink: 0 }}
      title={ok ? okTitre : titre}>
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
        title={inPipe ? CLIENT.fiche.crmDedansTip : CLIENT.fiche.crmAjouterTip}
      >
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
          title="Retour terrain : que s’est-il passé après le contact ? (par compte, modifiable)"
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
        title={inProjet
          ? `Dans ${attaches.length > 1 ? `${attaches.length} projets` : `le projet « ${attaches[0].nom} »`} — rattacher à un autre`
          : 'Ajouter cette parcelle à un projet'}>
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
                  title={deja ? `Déjà dans « ${p.nom} » — ouvrir` : `Ajouter à « ${p.nom} » (→ Retenues)`}>
                  <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-mint" />
                  <span className="min-w-0 flex-1 truncate">{p.nom}</span>
                  <span className="shrink-0 font-mono text-[10px] text-txt-dim">{deja ? 'déjà ↗' : vivier(p).toLocaleString('fr-FR')}</span>
                </button>
              )
            })}
          </div>
          <div className="my-1.5 h-px bg-line/40" />
          <button data-projet-fiche-nouveau disabled={nouveau.isPending} onClick={() => nouveau.mutate()}
            className="hover-fill-amber flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-mint transition-colors duration-quick disabled:opacity-50"
            title="Créer un projet et y ajouter cette parcelle">
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

// EBC / ER (dette #10) — drapeaux d'INFORMATION dérivés des prescriptions PLU DÉJÀ calculées
// par la cascade (layer 'prescription_plu', libellés servis). Lecture seule : ne filtre, n'exclut
// ni ne pondère JAMAIS — le verdict et les scores restent ceux du run servi.
function prescriptionsInfo(lines: FicheLine[]): { ebc: { coverage: number | null } | null; ers: { num: string | null }[] } {
  let ebc: { coverage: number | null } | null = null
  const ers: { num: string | null }[] = []
  const vus = new Set<string>()
  for (const l of lines || []) {
    if (l.layer !== 'prescription_plu') continue
    const d = l.detail || ''
    if (d.startsWith('Espace boisé classé (EBC)')) {
      const m = d.match(/~\s*(\d+)\s*%/)
      const cov = m ? Number(m[1]) : null
      if (!ebc || (cov != null && (ebc.coverage == null || cov > ebc.coverage))) ebc = { coverage: cov }
    } else if (d.startsWith('Emplacement réservé')) {
      const m = d.match(/ER\s*n?°?\s*(\d+)/i) || d.match(/réservé\s*n?°?\s*(\d+)/i)
      const num = m ? m[1] : null
      const key = num ?? d.slice(0, 40)
      if (!vus.has(key)) { vus.add(key); ers.push({ num }) }
    }
  }
  return { ebc, ers }
}


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
  const setPluPrefillF = useApp((s) => s.setPluPrefill)    // M60 P1c — porte Annuaire PLU (insee+zone)
  const setPluVueF = useApp((s) => s.setPluVue)            // M137-P — porte directe vers une vue de l'outil PLU
  const modBlock = moduleFiche[idu]
  const sourceLine = useApp((s) => s.sourceLine)
  const calculette = useApp((s) => s.calculette)   // A6 : hypothèses courantes → reflétées dans le PDF
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
  const fq = ficheQuery.trim().toLowerCase()
  const ficheMatches = fq && f
    ? f.lines.filter((l) => `${l.layer} ${layerLabel(l.layer)} ${l.detail ?? ''} ${l.source ?? ''} ${l.result ?? ''}`.toLowerCase().includes(fq))
    : []

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
  const motifEcart = verdict?.label.includes(' — ') ? verdict.label.split(' — ').slice(1).join(' — ') : ecarteeMotif
  // M52 L2 — hiérarchie : l'essentiel (droit du sol + économie) s'ouvre à l'arrivée pour un tier
  // SERVABLE (verdict.tier ≠ null : brûlante/chaude/à-creuser/réserve). L'écartée simple n'ouvre
  // M55-L point 10 : `servable` (ex-pilote de defaultOpen des tiroirs Règles/Faisabilité) retiré —
  // l'accordéon est désormais tout fermé à l'ouverture (état initial légal), plus d'auto-ouverture.
  // M52 L3 — données ABSENTES, DITES (jamais approximées) : dérivées de nuls RÉELS du payload +
  // faits open-data connus. Chaque entrée est un fait vérifiable, pas une excuse vague.
  const donneesAbsentes: { quoi: string; pourquoi: string }[] = f ? [
    { quoi: 'Année de construction', pourquoi: 'non disponible en open data à la parcelle (ABSENTE)' },
    ...(!f.adresse ? [{ quoi: 'Adresse postale', pourquoi: 'parcelle non rattachée à une voie (BAN)' }] : []),
    ...(!f.proprietaire_moral ? [{ quoi: 'Identité du propriétaire', pourquoi: 'personne physique — non automatisée (workflow SPF/CERFA)' }] : []),
  ] : []
  const ongletLines = (o: Onglet) => f?.lines.filter((l) => l.onglet === o) ?? []
  // RETOURS-11F4 (F6/F7) : les lignes Risques ET Marché (marcheLines, prix de sortie, socio-éco)
  // vivent désormais dans `RisquesSection` / `MarcheSection`. `dvfSecteur` (prix terrain nu) reste
  // dérivé ici car l'ANALYSE d'en-tête l'affiche aussi (M137-G — nu SEUL, jamais moyenné au bâti).
  const dvfSecteur = f?.dvf_parcelle?.secteur?.find((s) => s.type_bien === 'terrain')
  // Proprio : le signal dominant s'il existe (gérant âgé, procédure…), sinon le type de
  // propriétaire. Jamais d'identité de personne physique (boussole).
  // RETOURS-11F F11 — 🔴 double en-tête : quand un propriétaire moral est connu (ex. « PACIFIC »),
  // une ligne cascade résiduelle « propriétaire inconnu / non renseigné » ne doit PLUS coexister
  // (deux affirmations contradictoires sur le même écran). On masque ces lignes-là dès qu'un PM est su.
  const proprioLines = ongletLines('proprio').filter((l) =>
    !(f?.proprietaire_moral && /inconnu|non renseign|non recens/i.test(l.detail ?? '')))
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
  // Dette #10 : drapeaux EBC / ER (information seule), dérivés des prescriptions PLU du run servi.
  const presc = f ? prescriptionsInfo(f.lines) : null

  // M56-B5 : conteneur fiche ramené de 440px (M55-L, +10 %) à 400px — sa largeur d'avant.
  // VALEUR UNIQUE ici (un critère, un seul endroit). `max-w-full` garde la fiche dans l'écran
  // aux petites largeurs (aucun débordement horizontal). Ne PAS toucher les tailles de texte
  // ni les paddings (calés en M56-B3 : panneau 14, .gr 10 vertical, .gr partagée).
  return (
    <FicheAccordionCtx.Provider value={accValue}>
    <aside className="fiche-v6 absolute right-0 top-0 z-10 flex h-full w-[400px] max-w-full flex-col border-l border-line shadow-2xl">
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
      {/* M56-B6 · DA-FICHE-v6 — EN-TÊTE en CARTE .head (identité + 4 chiffres) posée sur le fond
          de panneau plus sombre. Le CTA, le bandeau et les IA suivent SOUS la carte. */}
      <div style={{ padding: '14px 14px 0', flexShrink: 0 }}>
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
                        href={cadastreGeoportailUrl(f.coords)} title="Cadastre Géoportail">
                        <LogoCadastre />
                      </a>
                    )}
                    {pj.url && (
                      <a data-fiche-pj data-pj-commune-seule={pj.commune_seule || undefined} className="hbtn"
                        target="_blank" rel="noreferrer noopener" href={pj.url}
                        title={pj.commune_seule ? 'Pages Jaunes — commune' : 'Pages Jaunes'}>
                        <LogoPagesJaunes />
                      </a>
                    )}
                    {f.coords && (
                      <a data-maps-link className="hbtn" target="_blank" rel="noreferrer noopener"
                        href={googleMapsUrl(f.coords)} title="Google Maps (épingle sur la parcelle)">
                        <LogoGoogleMaps />
                      </a>
                    )}
                  </>
                )
              })()}
              <WatchButton idu={idu} />
              <button className="hbtn" onClick={() => setFicheSearchOpen((o) => { if (o) setFicheQuery(''); return !o })}
                style={ficheSearchOpen ? { borderColor: 'var(--mint)', color: 'var(--mint)' } : undefined}
                title="Rechercher dans cette fiche">
                <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"><circle cx="11" cy="11" r="6" /><path d="m20 20-3.5-3.5" /></svg>
              </button>
              <button className="hbtn" onClick={() => select(null)} title="Fermer la fiche">
                <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"><path d="M18 6 6 18" /><path d="m6 6 12 12" /></svg>
              </button>
            </div>
          </div>

          {/* RETOURS-15 U7 — ADRESSE en rangée PLEINE LARGEUR (moins l'icône copier) : une ligne
              tant que ça tient, ellipse avec l'adresse complète au survol (title) sinon. Elle ne
              partage plus sa largeur avec les logos/cloche. M61 P5 — copiable (user-select). */}
          <div className="addr addr-row" data-fiche-adresse>
            <span style={{ userSelect: 'text', minWidth: 0 }} title={f?.adresse ?? undefined}>{f?.adresse ?? CLIENT.fiche.adresseAbsente}</span>
            {f?.adresse && <CopyIdu value={f.adresse} aria="Copier l’adresse" titre="Copier l’adresse" okTitre="Adresse copiée" dataAttr="adresse" />}
            {!f?.adresse && (
              <Tip side="top" tip={CLIENT.fiche.adresseAbsenteInfo}>
                <span data-adresse-absente-i role="button" tabIndex={0} aria-label="Pourquoi l’adresse manque"
                  style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 14, height: 14, borderRadius: 999, border: '1px solid var(--line-3)', color: 'var(--txt-ghost)', fontSize: 9, fontWeight: 700, lineHeight: 1, cursor: 'help', verticalAlign: 'middle' }}>i</span>
              </Tip>
            )}
          </div>

        {/* RETOURS-11 F1 — les trois accès (Cadastre · Pages Jaunes · Google Maps) ont MONTÉ dans
            l'en-tête à côté de la cloche, en boutons-logos (voir .hbtns ci-dessus). Les anciennes
            pastilles pleines sur deux lignes sont retirées. */}

        {/* M55-O phase 2.1 — BANDEAU DE 4 CHIFFRES (toujours visible, factuel, aucun avis) :
            Surface · Zone · SDP disponible · Prix secteur €/m². Valeurs SERVIES (jamais en dur) ;
            une valeur absente → « — » (jamais un zéro trompeur ni un blanc muet). Habillage affiné
            en phase 3. */}
        {f && (() => {
          const cells: { l: string; v: string; i?: string }[] = [
            { l: 'Surface', v: fmtM2(f.surface_m2) },
            // M71 BLOC C — l'aveuglement se dit : zone absente = « Non publié au GPU » (jamais
            // un « — » muet). Saint-Philippe (RNU, bandeau f.rnu déjà affiché) + 91 rés. Saint-Leu.
            { l: 'Zone', v: reglesZone ?? 'Non publié au GPU' },
            // M56-B4 point 3 — un zéro n'est pas une absence : SDP nulle (non constructible) ou prix
            // nul = donnée sans objet → « — », jamais « 0 m² » / « 0 €/m² » présentés comme un résultat.
            { l: 'SDP dispo.', v: reglesSdp != null && reglesSdp > 0 ? `${fmtInt(reglesSdp)} m²` : '—' },
            // M137-G — « NU » : prix du TERRAIN NU seul (jamais du bâti). Libellé court (tenait sur
            // deux lignes en « Secteur · nu ») ; le « i » dit la méthode ET le cas vide (« — » =
            // aucune vente de terrain nu dans la section sur la période).
            { l: 'Nu',
              v: dvfSecteur?.mediane_prix_m2 != null && dvfSecteur.mediane_prix_m2 > 0 ? `${fmtInt(dvfSecteur.mediane_prix_m2)} €/m²` : '—',
              i: 'Médiane du prix du terrain nu au m² — ventes 2021-2025 (géo-DVF), sur la commune + la section cadastrale de la parcelle. Le bâti n’y entre jamais. « — » : aucune vente de terrain nu dans cette section sur la période.' },
          ]
          return (
            <div className="stats" data-bandeau-chiffres>
              {cells.map((c) => (
                <div className="stat" key={c.l}>
                  <div className="stat-l flex items-center gap-1">
                    {c.l.toUpperCase()}
                    {c.i && (
                      <Tip tip={c.i}>
                        <span role="button" tabIndex={0} aria-label={`Méthode : ${c.l}`}
                          className="flex h-[12px] w-[12px] shrink-0 items-center justify-center rounded-full border border-line-2 text-[7px] font-bold leading-none text-txt-dim hover:border-mint hover:text-mint">i</span>
                      </Tip>
                    )}
                  </div>
                  <div className={`stat-v${c.v === '—' ? ' vide' : ''}`}>{c.v}</div>
                </div>
              ))}
            </div>
          )
        })()}
        </div>{/* /.head — la carte d'en-tête (identité + 4 chiffres) est le SEUL bloc FIXE. */}
        {/* RETOURS-9 (Q8.1) — ONGLETS Analyse · Autour · Actions RETIRÉS : retour à la fiche UNIQUE qui
            défile. « Autour » est un tiroir de la fiche (et existe dans les outils) ; « Actions » (CRM/
            Projet/exports) vit déjà en pied de fiche. Plus rien à choisir : tout défile d'un seul tenant. */}
      </div>{/* M68 P1a — fin du wrapper FIXE (en-tête seul) : tout le reste défile. */}

      {/* M68 P1a — DÉFILEMENT UNIQUE : le bloc Analyse (CTA + carte verdict), la bannière RNU, les
          signaux, puis les tiroirs / actions / exports / mention légale vivent tous DANS ce conteneur
          `overflow-y-auto flex-1`. La fiche défile donc jusqu'au pied EN TOUTE circonstance (bloc
          Analyse absent / déplié / replié, synthèse ouverte, n'importe quel tiroir ouvert). Avant M68,
          le bloc Analyse était dans le wrapper flex-shrink:0 et affamait ce conteneur (cf. RAPPORT_M68).
          RETOURS-9 (Q8.1) — plus d'onglet : ce conteneur est le SEUL corps défilant de la fiche. */}
      <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto overflow-x-clip px-[14px] pb-4 pt-1">
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
            <button data-demander-analyse className="cta" onClick={() => revelerVerdict(idu)}
              title="Déployer le verdict, le score et « pourquoi »">
              {CLIENT.fiche.demanderAnalyse} →
            </button>
            {/* M62-P1 (i) : sous-titre « Le verdict, le score et "pourquoi" — à la demande » RETIRÉ,
                le bouton se suffit (P2). `demanderAnalyseSous` (strings.ts) devient 0-caller. */}
          </>
        )}
        {/* CARTE VERDICT — teintée selon le tier (verdict.color) ; la référence montre le cas Chaude. */}
        {f && verdict && verdictRevele && (
          // M61 P2 — le bloc Analyse est un TIROIR : en-tête cliquable (Analyse LABUSE + verdict au
          // repli + chevron), corps repliable. État par parcelle (analyseReplie), déplié par défaut,
          // INDÉPENDANT de l'accordéon exclusif des 7 tiroirs (aucun autre tiroir ne se ferme).
          <div data-verdict-card style={{ marginTop: 8, background: `${verdict.color}12`, border: `1px solid ${verdict.color}59`, borderRadius: 13, overflow: 'hidden' }}>
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
                  {v2Pilote && f.score_v2?.rang != null && (verdict.tier === 'brulante' || verdict.tier === 'chaude') && (
                    <span style={{ fontSize: 12, color: 'var(--lab)' }}>rang {f.score_v2.rang}</span>
                  )}
                  {verdictEcartee && (
                    <span data-ecartee-motif style={{ fontSize: 12, color: 'var(--lab)' }}>
                      · {ecarteeMotif} <button onClick={() => document.querySelector('[data-analyse-motifs]')?.scrollIntoView({ behavior: 'smooth', block: 'center' })} style={{ background: 'none', border: 0, padding: 0, color: '#E8695A', textDecoration: 'underline', cursor: 'pointer', fontSize: 12 }} title={CLIENT.fiche.ecarteeVoirTip}>{CLIENT.fiche.ecarteeVoir}</button>
                    </span>
                  )}
                </div>
              </div>
              {f.score_v2 != null && (
                <div style={{ textAlign: 'right', flexShrink: 0 }}>
                  {/* M135 — la MÊME fraction que la carte de tri (jamais un ×N). « — » = peu probable. */}
                  <p style={{ margin: 0, fontSize: 19, fontWeight: 500, color: signalEcarte ? '#8C7468' : verdict.color, lineHeight: 1 }}>{f.score_v2.fraction ?? '—'}</p>
                  <p style={{ margin: '3px 0 0', fontSize: 11, color: 'var(--lab)' }}>
                    {signalEcarte ? 'signal brut' : (f.score_v2.fraction ? 'sous 1 an' : 'peu probable')}
                    {f.score_v2.verbal?.info && (
                      <span title={f.score_v2.verbal.info} style={{ marginLeft: 4, cursor: 'help', borderBottom: '1px dotted #5f7568' }}>ⓘ</span>
                    )}
                  </p>
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
                {f.score_v2.verbal?.reglette_pct != null && (
                  <>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9.5, color: 'var(--txt-off)', marginBottom: 3 }}>
                      <span>moyenne</span><span>très forte</span>
                    </div>
                    <div style={{ position: 'relative', height: 7, borderRadius: 5, background: 'linear-gradient(90deg,#3a4d44,#6fb3d9 35%,#ffc266 70%,#ff7a59)' }}>
                      <i data-reglette style={{ position: 'absolute', top: -3, left: `${f.score_v2.verbal.reglette_pct}%`, width: 3, height: 13, background: '#fff', borderRadius: 2, boxShadow: '0 0 5px #000' }} />
                    </div>
                  </>
                )}
                {/* écartée/déclassée à signal fort : l'écartement PRIME — dit pourquoi la fréquence
                    est absente (doctrine étage 0 M5). Bordure « terre éteinte », pas de menthe. */}
                {signalEcarte && (
                  <p data-signal-ecarte style={{ margin: '9px 0 0', fontSize: 11, color: '#b9a898', borderLeft: '3px solid #8C7468', paddingLeft: 8 }}>
                    La parcelle porte {(multBase ?? 0) >= 4 ? 'un signal fort' : 'un signal au-dessus de la moyenne'}{f.score_v2.fraction ? <> ({f.score_v2.fraction} sous 1 an)</> : null} <b>mais elle est écartée</b>{motifEcart ? <> : {motifEcart.toLowerCase()}</> : null} — l’écartement prime. La fréquence par tier ne s’affiche pas.
                    <span title="Le signal est réel ; l’écartement (étage 0) prime sur le signal (doctrine M5). On montre le signal ET la raison de l’écart." style={{ marginLeft: 4, cursor: 'help', borderBottom: '1px dotted #5f7568' }}>ⓘ</span>
                  </p>
                )}
                {f.score_v2.verbal?.frequence && (
                  <p data-freq style={{ margin: '9px 0 0', fontSize: 11, color: 'var(--txt-dim)', borderLeft: '3px solid #5fd0a8', paddingLeft: 8 }}>
                    {f.score_v2.verbal.frequence.sous_moyenne
                      ? <>Fréquence de vente en dessous de la moyenne de l’île (potentiel de plus long terme).</>
                      : <>Parmi les parcelles de ce niveau, environ <b>{f.score_v2.verbal.frequence.sur_100} sur 100</b> ont été vendues en {f.score_v2.verbal.frequence.fenetre}, contre ~{f.score_v2.verbal.frequence.base_sur_100} sur 100 en moyenne.</>}
                    <span title={f.score_v2.verbal.frequence.source_dite} style={{ marginLeft: 4, cursor: 'help', borderBottom: '1px dotted #5f7568' }}>ⓘ</span>
                  </p>
                )}
                {(f.score_v2.pourquoi?.length ?? 0) > 0 && (
                  <details data-pourquoi style={{ marginTop: 8 }} open={verdict.tier === 'brulante' || verdict.tier === 'chaude' || signalEcarte}>
                    <summary style={{ cursor: 'pointer', fontSize: 11.5, color: '#a78bfa', fontWeight: 600 }}>{signalEcarte ? 'Pourquoi ce signal (avant l’écart)' : 'Pourquoi ce score'}</summary>
                    <ul style={{ margin: '6px 0 0', padding: 0, listStyle: 'none' }}>
                      {f.score_v2.pourquoi!.slice(0, 5).map((c, i) => (
                        <li key={i} style={{ padding: '3px 0', fontSize: 11.5, color: '#c9d6cf' }}>
                          <span style={{ color: c.signe === '-' ? '#8ba69a' : '#5fd0a8' }}>{c.signe === '-' ? '▽' : '▲'}</span>{' '}
                          {c.phrase || c.libelle}
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
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
          <div data-rnu-banner style={{ marginTop: 10, background: '#2a2213', border: '1px solid #4a3c20', borderRadius: 10, padding: '9px 12px' }}>
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
        <div className="flex shrink-0 items-center gap-2 border-b border-line bg-surface-2 px-5 py-2">
          <input autoFocus data-fiche-search value={ficheQuery} onChange={(e) => setFicheQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Escape' && (setFicheQuery(''), setFicheSearchOpen(false))}
            placeholder="Chercher dans cette fiche (risque, réseau, ICPE…)"
            className="min-w-0 flex-1 rounded-md border border-line-2 bg-surface-3 px-2.5 py-1 text-xs text-txt placeholder:text-txt-dim focus:border-mint focus:outline-none" />
          {fq && <span className="shrink-0 text-[11px] text-txt-mut">{ficheMatches.length} résultat{ficheMatches.length > 1 ? 's' : ''}</span>}
        </div>
      )}

      {/* M19 (réf. ordre) : la barre d'onglets est RETIRÉE — la fiche est une pile de tiroirs
          empilés, navigable au scroll ; plus de navigation par onglets. */}

      {/* M68 P1a — l'ancien conteneur de défilement est FUSIONNÉ dans celui ouvert après l'en-tête
          (plus haut) : un seul conteneur `overflow-y-auto flex-1` pour tout le corps de la fiche. */}
        {/* A6 : recherche active → on remplace les onglets par les lignes de la fiche qui matchent */}
        {fq && f && (
          <div data-fiche-search-results>
            <p className="label-caps mb-2">Dans cette fiche · « {ficheQuery.trim()} »</p>
            {ficheMatches.length === 0
              ? <p className="text-xs text-txt-dim">Aucune donnée de la fiche ne correspond.</p>
              : <div className="flex flex-col gap-1">{ficheMatches.map((l, i) => <Line key={i} line={l} />)}</div>}
          </div>
        )}
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
        {!fq && f && tab === 'synthese' && (() => {
          // micro-preuves (spec) dérivées des données déjà chargées
          const shorten = (s: string) => fmtLibelleBrut(s).replace(/\s*[—(].*$/, '').trim()
          const proprioPastilles = proprioLines.filter((l) => (l.weight ?? 0) > 0).slice(0, 3).map((l) => shorten(l.detail).slice(0, 26))
          // ALGO-1 item 2 : l'accent proprio ne dépend plus du Score V (retiré de l'affichage)
          const proprioAccent = !!proprioSignal
          // RETOURS-11F4 (F8) : viabValue/viabColor/viabConfirmee/viabContext vivent dans `ReseauxSection`.
          // M56-B6 · DA-FICHE-v6 « pas de % nu » : la couverture ICD vit dans le sous-titre du
          // tiroir « Données et méthode » (plus de valeur % nue à droite) — `confianceValue` retiré.
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
                  <button onClick={() => setIaOuvert('question')} data-askbar-open className="ia-btn">
                    <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}><path d="M20 4H4v13h5l3 3 3-3h2z" /></svg>
                    Poser une question
                  </button>
                  {/* RETOURS-11 T9 (03/09) — explication au survol retirée (plus de title). */}
                  <button onClick={() => { setIaOuvert('synthese'); if (!syntheseM.data && !syntheseM.isPending) syntheseM.mutate() }}
                    data-synthese-ia className="ia-btn">
                    <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}><path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z" /></svg>
                    Synthèse IA
                  </button>
                </div>
              )}
              {iaOuvert === 'question' && <AskBar idu={idu} zone={null} startOpen onClose={() => setIaOuvert('aucun')} />}
              {iaOuvert === 'synthese' && <SyntheseIAPanel data={syntheseM.data} pending={syntheseM.isPending} error={syntheseM.isError} onReplier={() => setIaOuvert('aucun')} />}
            </div>

            {/* M55-O phase 2.1c : Mode B unifié et rattaché à la Constructibilité (rendu unique plus
                bas). L'ancien rendu « remonté » pour la déclassée à signal fort est retiré. */}

            {/* M56-B4 point 2 — SIGNAUX de la parcelle (drapeaux EBC / ER, information seule),
                regroupés ici juste avant LE TERRAIN, jamais au milieu des actions. Micro-label
                « SIGNAUX » ; si un seul signal, la pastille reste seule mais à cette place. */}
            {presc && (presc.ebc || presc.ers.length > 0) && (
              <div data-signaux-parcelle>
                <GroupLabel first>Signaux</GroupLabel>
                <div data-prescriptions-badges style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {presc.ebc && (
                    <Tip tip="Espace boisé classé — information. Toute construction est interdite sur l’emprise boisée (Art. L113-1 CU). N’exclut pas la parcelle.">
                      <span data-badge-ebc className="pill-mint">
                        partiellement en EBC{presc.ebc.coverage != null ? ` (~${presc.ebc.coverage} %)` : ''}
                      </span>
                    </Tip>
                  )}
                  {presc.ers.map((er, i) => (
                    <Tip key={i} tip="Emplacement réservé — information. Emprise grevée au profit d’un projet public (servitude levable si l’ER est abandonné). N’exclut pas la parcelle.">
                      <span data-badge-er className="pill-amber">
                        emplacement réservé{er.num ? ` n°${er.num}` : ''}
                      </span>
                    </Tip>
                  ))}
                </div>
              </div>
            )}

            {/* M55-O phase 3.4 — GROUPE SILENCIEUX « LE TERRAIN » : Urbanisme · Constructibilité
                (+ Mode B) · Risques et protections. */}
            {/* M137-E — le Copilote embarqué « Demander au Copilote sur cette parcelle… » est RETIRÉ :
                la loupe (recherche intra-fiche) + « Poser une question » (AskBar) couvrent déjà le besoin. */}

            <GroupLabel>Le terrain</GroupLabel>

            {/* M56-B6 · DA-FICHE-v6 — plus de conteneur .gcard : chaque tiroir est une carte autonome. */}
            {/* ① URBANISME — droit du sol (PLU, procédure, zonage, traducteur, règlement). */}
            <RefDrawer id="regles" icon={IC.regles} name="Urbanisme"
              value={reglesGabarit}
              context={[reglesZone ? `zone ${reglesZone}` : reglesArticle ? `art. ${reglesArticle}` : 'zone non publiée au GPU', pctConsomme != null ? CLIENT.fiche.sdpConsommee(pctConsomme) : null].filter(Boolean).join(' · ')}
              micro={pctConsomme != null
                ? <MicroJauge pct={pctConsomme} label={CLIENT.fiche.sdpConsommee(pctConsomme)} tip={CLIENT.fiche.sdpConsommeeTip(reglesSdp ?? null)} />
                : <MicroJauge pct={0} label={[reglesZone ? `zone ${reglesZone}` : null, reglesArticle ? `art. ${reglesArticle}` : null].filter(Boolean).join(' · ') || 'PLU'} />}>
              <div className="flex flex-col gap-3">
                {/* M75 — obligation APER (ombrières PV, grand parking > 1 500 m²) : contrainte
                    réglementaire portant sur le terrain, INFORMATION. Libellé backend (mêmes mots
                    que les exports). « potentiellement concerné », jamais « soumis à ». */}
                {f.aper && (
                  <div data-aper className="rounded-lg border border-amber/40 bg-amber-bg px-3 py-2 text-[11px] leading-snug text-txt">
                    <span className="mr-1" aria-hidden>🅿</span>{f.aper.note}
                    <span className="ml-1 text-[10px] text-txt-dim">{f.aper.etat}.</span>
                  </div>
                )}
                {/* M32 §2 + M40 : source qui fait foi. Les 3 choses distinctes, jamais mélangées :
                    (1) quel document LABUSE sert · (2) qu'il fait foi à ce jour · (3) ce qui est en
                    cours et non servi. + action « vérifier en mairie ». Couleur d'alerte hors « à jour ». */}
                {f.plu_fraicheur?.libelle && (
                  <div data-plu-fraicheur={f.plu_fraicheur.statut}
                    className={`rounded-lg border px-3 py-2 text-[11px] leading-snug ${
                      f.plu_fraicheur.statut === 'a_jour'
                        ? 'border-line-2 text-txt-mut'
                        : 'border-st-creuser/40 bg-st-creuser/10 text-txt'}`}>
                    <span className="mr-1">{f.plu_fraicheur.statut === 'a_jour' ? '🕓' : '▲'}</span>
                    {f.plu_fraicheur.document_servi ? (
                      <>
                        <span>{f.plu_fraicheur.document_servi}</span>
                        {f.plu_fraicheur.fait_foi && (
                          <span className="block text-[10px] text-txt-dim mt-0.5">✓ {f.plu_fraicheur.fait_foi}</span>
                        )}
                        {f.plu_fraicheur.en_cours && (
                          /* M57-P1 (d) : a_jour → avertissement NEUTRE (générique : assertion de config,
                             pas une procédure), sans sablier ni « En cours (non servi) ». Les autres
                             statuts (annule_partiel / opposabilite_en_attente) portent une procédure
                             RÉELLE → cadre « En cours (non servi) » conservé. */
                          f.plu_fraicheur.statut === 'a_jour'
                            ? <span className="block text-[10px] text-txt-dim mt-0.5">{f.plu_fraicheur.en_cours}</span>
                            : <span className="block text-[10px] text-st-creuser mt-0.5">⏳ En cours (non servi) : {f.plu_fraicheur.en_cours}</span>
                        )}
                        {f.plu_fraicheur.action && (
                          <span className="block text-[10px] text-txt-mut mt-0.5">→ {f.plu_fraicheur.action}</span>
                        )}
                      </>
                    ) : (
                      <>{f.plu_fraicheur.libelle}
                        {f.plu_fraicheur.note && f.plu_fraicheur.statut !== 'a_jour' && (
                          <span className="block text-[10px] text-txt-dim mt-0.5">{f.plu_fraicheur.note}</span>
                        )}
                      </>
                    )}
                  </div>
                )}
                {/* M41 — Radar procédures PLU : stade + conséquences parcellaires servables
                    (veille AU ; sursis si armé). Jamais l'issue de la procédure. */}
                {f.radar_procedure?.indisponible && <BlocIndisponible titre="Radar procédures PLU" />}
                {f.radar_procedure?.synthese?.etat && (
                  <div data-radar-procedure className="rounded-lg border border-st-creuser/40 bg-st-creuser/10 px-3 py-2 text-[11px] leading-snug text-txt">
                    <span className="mr-1">📡</span>{f.radar_procedure.synthese.etat}
                    {f.radar_procedure.veille_au && (
                      <span className="block text-[10px] text-mint mt-1">Veille AU — {f.radar_procedure.veille_au}</span>
                    )}
                    {f.radar_procedure.sursis ? (
                      <span className="block text-[10px] text-st-ecartee mt-1">
                        Sursis à statuer — {f.radar_procedure.sursis.texte}
                        <span className="block text-txt-dim">{f.radar_procedure.sursis.base_legale}</span>
                      </span>
                    ) : (
                      <span className="block text-[10px] text-txt-dim mt-1">Sursis à statuer : non servi (débat PADD non constaté à ce jour).</span>
                    )}
                  </div>
                )}
                {/* M55-O phase 2.2 — la jauge « Qualité » (q_score) est RETIRÉE de la fiche : mesurée
                    non discriminante en M55-N (82,5 % à la base neutre 50). Seule « Confiance données »
                    (ICD, tiroir Données) reste. Le champ back q_score n'est PAS touché (consommé
                    ailleurs : App, Kanban, MapView, filtres…) — seul l'affichage fiche disparaît. */}
                <TraducteurBloc idu={idu} />
                {f.reglement_plu && <ReglementPluBlock rp={f.reglement_plu} />}
                {/* M55-O phase 2.1c : le potentiel de transformation (SDP consommée/résiduelle/
                    surélévation) DÉMÉNAGE vers « Constructibilité » — il relève de la capacité, pas
                    du droit du sol pur. */}
                {/* M55-O phase 2.1b : les contrôles PASS (« sans objet ») partent dans
                    « Vérifications d'éligibilité » (bloc Analyse) ; ici, seules les lignes PLU
                    substantielles (non-PASS) restent — fini le mur de lignes « sans objet ». */}
                {/* M57-P1 (Q4) : points signés RETIRÉS ici (hideWeight) — le fait, la source et la
                    date restent. « Pourquoi ce score » (bloc Analyse) garde ses contributions. */}
                {(() => { const rl = reglesLines.filter((l) => l.result !== 'PASS'); return rl.length > 0
                  ? <div className="flex flex-col gap-1">{rl.map((l, i) => <Line key={i} line={l} hideWeight hideDate />)}</div> : null })()}
                {/* M60 P1c — PORTES en pied d'Urbanisme : les liens Annuaire PLU + lettre de zonage
                    REPRIS en forme porte (.porte-outil), accroches contextualisées (zone PLU). */}
                {/* M137-P — les 3 outils PLU fusionnés dans le hub « plu » : la porte Annuaire ouvre le
                    hub PRÉ-REMPLI sur l'Annuaire (pluPrefill : commune + zone servie). */}
                <PorteOutil ico="§" data="annuaire" titre="Annuaire PLU de la commune"
                  sous={reglesZone ? `Le règlement de la zone ${reglesZone} — articles, prescriptions` : 'Le règlement PLU de la commune'}
                  onClick={() => { setPluPrefillF({ insee: idu.slice(0, 5), zone: reglesZone ?? null }); setModule('plu') }} />
                <PorteOutil ico="✉" data="lettre-zonage" titre="Lettre de vérification de zonage"
                  sous={reglesZone ? `PDF de vérification de zonage — zone ${reglesZone} de cette parcelle` : 'PDF de vérification de zonage'}
                  onClick={() => window.open(`/lettre-zonage/${idu}.pdf`, '_blank', 'noopener')} />
                {/* M70 déc. 9 — PORTE Vérif procédure PLU dans Urbanisme (grille terminale supprimée).
                    L'outil lit selectedIdu (préservé par setModule) → pré-rempli sur la parcelle. */}
                <PorteOutil ico="⚖" data="verif-procedure" titre="Vérif procédure PLU"
                  sous={reglesZone ? `Commune en procédure ? (zone ${reglesZone})` : 'La commune est-elle en procédure PLU ?'}
                  onClick={() => { setPluVueF('procedure'); setModule('plu') }} />
              </div>
            </RefDrawer>

            {/* ③ ÉCONOMIE — Constructibilité (capacité/bilan/calcul tracé) + Mode B. RETOURS-11F4 (F5) :
                la section entière vit dans sections `constructibilite.tsx` (auto-suffisante). */}
            <ConstructibiliteSection f={f} idu={idu} />

            {/* Risques et protections — clôt le groupe LE TERRAIN. RETOURS-11F4 (F6) : vigilances
                d'abord, « sans objet » repliés, SUP rapatriées, compteur vrai → module `risques.tsx`. */}
            <RisquesSection f={f} idu={idu} />

            {/* M55-O phase 3.4 — GROUPE SILENCIEUX « LE CONTEXTE » : Marché et secteur · Réseaux et
                accès · Propriétaire · Données et méthode. */}
            <GroupLabel>Le contexte</GroupLabel>

            {/* MARCHÉ — micro : sparkline + volume */}
            {/* M55-O phase 2.3 (incohérence 3) : le prix d'en-tête est étiqueté « terrain nu » — à
                distinguer du « prix de sortie bâti » (bilan) : deux métriques légitimes, jamais
                confondues (269-286 €/m² terrain vs ~2 000 €/m² bâti). */}
            {/* MARCHÉ — RETOURS-11F4 (F7) : recentré sur le PRIX (prix de sortie rapatrié ici, socio-éco
                et permis déménagés vers Autour) → module `marche.tsx`. */}
            <MarcheSection f={f} idu={idu} />

            {/* RÉSEAUX ET ACCÈS — RETOURS-11F4 (F8) : 4 blocs (Accès/Réseaux/Viabilisation/Axes),
                un seul verdict d'accès, permis & dépôts déménagés vers Autour → module `reseaux.tsx`. */}
            <ReseauxSection f={f} idu={idu} />

            {/* AUTOUR DE CETTE PARCELLE — RETOURS-11F4 (F9) : équipements (un moteur), socio-éco
                rapatrié de Marché, permis à proximité (un tableau), isochrone → module `autour.tsx`. */}
            <AutourSection f={f} idu={idu} />

            {/* M106 P3 — DISPOSITIFS TERRITORIAUX (ZFANG / FRR ex-ZRR) : attribut de COMMUNE,
                des états sourcés + lien vers le texte. JAMAIS un chiffre fiscal (ni taux, ni
                plafond, ni calcul) — le fiscaliste tranche, et la fiche le dit. */}
            {f.territoire_fiscal && (
              <RefDrawer id="territoire" icon={IC.marche} name="Dispositifs territoriaux"
                context={f.territoire_fiscal.commune}
                value={f.territoire_fiscal.zfang?.regime === 'renforce'
                  ? <span className="pill-mint">ZFANG renforcé</span> : f.territoire_fiscal.zfang ? 'ZFANG standard' : undefined}>
                <div className="flex flex-col gap-2.5" data-territoire-fiscal>
                  {/* M134 — les périmètres FINS qui touchent LA parcelle (QPV / bande TVA 500 m),
                      au-dessus des attributs de commune (ZFANG/FRR). Jamais un sigle nu. */}
                  {(f.territoire_fiscal.perimetres ?? []).map((p) => (
                    <div key={p.libelle} data-fiche-perimetre className="rounded-lg border border-mint/30 bg-mint/5 px-3 py-2">
                      <p className="text-[12px] font-semibold text-txt-hi">{p.libelle}{p.derive && <span className="ml-1.5 rounded bg-surface-2 px-1 py-px text-[9px] uppercase tracking-wide text-txt-dim">estimé</span>}</p>
                      <p className="mt-0.5 text-[11.5px] leading-snug text-txt">{p.detail}</p>
                      <p className="mt-0.5 text-[10.5px] text-txt-dim">{p.source}</p>
                    </div>
                  ))}
                  {([['ZFANG — zone franche d’activité', f.territoire_fiscal.zfang],
                     ['FRR — France Ruralités Revitalisation (ex-ZRR)', f.territoire_fiscal.frr]] as const)
                    .filter(([, a]) => !!a).map(([titre, a]) => (
                    <div key={titre}>
                      <p className="text-[12px] font-semibold text-txt-hi">{titre}</p>
                      <p className="mt-0.5 text-[11.5px] leading-snug text-txt">{a!.libelle}</p>
                      <p className="mt-0.5 text-[10.5px] text-txt-dim">
                        {a!.source_ref} · <a href={a!.lien} target="_blank" rel="noreferrer" className="underline hover:text-mint">voir le texte</a>
                      </p>
                    </div>
                  ))}
                  {/* RETOURS-11F3 F10 — dispositifs valables sur TOUTE La Réunion (zonage B1, TVA DOM
                      8,5 % / 2,1 % LLS), rapatriés de Constructibilité. Repères, jamais un calcul fiscal. */}
                  {(f.territoire_fiscal.dispositifs_dom ?? []).map((d) => (
                    <div key={d.libelle} data-dispositif-dom>
                      <p className="text-[12px] font-semibold text-txt-hi">{d.libelle}</p>
                      <p className="mt-0.5 text-[11.5px] leading-snug text-txt">{d.detail}</p>
                      <p className="mt-0.5 text-[10.5px] text-txt-dim">{d.source}</p>
                    </div>
                  ))}
                  {f.territoire_fiscal.avertissement && (
                    <p className="rounded-lg border border-line bg-surface-2 px-3 py-2 text-[10.5px] leading-snug text-txt-dim">
                      {f.territoire_fiscal.avertissement}
                    </p>
                  )}
                </div>
              </RefDrawer>
            )}

            {/* M55-O phase 2.1c : Mode B rendu une seule fois, rattaché à la Constructibilité (plus haut). */}

            {/* M55-O phase 2.1c : le tiroir « Contexte » (historique + voisinage) est ABSORBÉ dans
                « Marché et secteur » (hyper-local). Il ne vit plus en tiroir séparé. */}

            {/* ⑤ PROPRIÉTÉ — société (M43) + signaux vendeur. CARTE ACCENTUÉE VIOLETTE = le signal chaud. */}
            <RefDrawer id="proprio" icon={IC.proprio} name="Propriétaire" accent={proprioAccent}
              context={proprioSignal ? (f.proprietaire_moral ? proprioType : 'personne physique') : undefined}
              value={proprioSignal ? shorten(proprioSignal.detail).slice(0, 20) : (f.proprietaire_moral ? proprioType.slice(0, 18) : 'privé')}
              micro={proprioPastilles.length ? <MicroPastilles items={proprioPastilles} /> : undefined}>
              <div className="flex flex-col gap-2">
                {f.proprietaire_moral ? (
                  <div className="card-elev px-3 py-2.5">
                    <p className="label-caps">Propriétaire (DGFiP)</p>
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
                  <div className="card-elev px-3 py-2 text-[11px] text-txt-mut">
                    Propriétaire : personne physique ou non recensé au fichier des personnes morales
                    (identité nominative : workflow SPF/CERFA, jamais automatisée).
                    {/* M70 point 7a — le lien texte SPF devient une PORTE-OUTIL en pied de tiroir
                        (voir plus bas). L'outil courrier (M09, pré-rempli sur la parcelle) est inchangé. */}
                  </div>
                )}
                {proprioLines.length > 0 && <div className="flex flex-col gap-1">{proprioLines.map((l, i) => <Line key={i} line={l} hideWeight hideDate />)}</div>}
                {/* L1 (KF-2) — historique du propriétaire moral par millésime + diff constaté (hors
                    scoring). R6 : `pm` dit au composant si la parcelle a un propriétaire moral —
                    absence de timeline = ligne honnête (PM) ou silence justifié (PP). */}
                <ProprietaireHistorique h={f.proprietaire_historique} pm={!!f.proprietaire_moral} />
                {/* M125-2 — copropriété(s) RNIC rattachées (donnée réelle, cible bailleur/copro) */}
                {f.coproprietes && f.coproprietes.length > 0 && <CoproprietesBlock copros={f.coproprietes} />}
                {/* RADAR P3 (C3) — un bien du Radar en vente sur cette parcelle : discret, fait + lien. */}
                {f.radar_bien && (
                  <div data-radar-bien className="card-elev px-3 py-2.5">
                    <p className="label-caps">Radar — bien en vente</p>
                    <div className="mt-1 flex items-center gap-2 text-xs">
                      <b className="text-txt-hi">{f.radar_bien.prix != null ? f.radar_bien.prix.toLocaleString('fr-FR') + ' €' : '—'}</b>
                      {f.radar_bien.type_bien && <span className="text-txt-mut">{f.radar_bien.type_bien}</span>}
                      <span className="rounded-full bg-surface-3 px-1.5 text-[10px] text-txt-mut">
                        {f.radar_bien.statut === 'en_vente_longue' ? 'en vente longue' : 'en vente'}
                      </span>
                    </div>
                    <a href={f.radar_bien.url_sortante} target="_blank" rel="noopener noreferrer"
                      onClick={() => { radarClic(f.radar_bien!.bien_id).catch(() => {}) }}
                      className="mt-1.5 inline-block text-[11px] text-mint underline decoration-dotted">
                      Voir l’annonce sur {f.radar_bien.portail} ↗
                    </a>
                  </div>
                )}
                {/* FIX-FICHE F2 — bloc « DPE connu » RETIRÉ : la fiche premium (_q_v2_fiche, celle que
                    l'UI reçoit) ne sert JAMAIS `dpe_connu` (construit seulement par le builder legacy
                    `_build_fiche`), et la table `parcel_dpe` n'existe plus en base → le bloc ne pouvait
                    pas s'afficher. L'INTENTION M71 B1 (« DPE en info seule, sans effet sur le
                    classement ») reste tracée dans le builder legacy ; la ressusciter suppose de servir
                    `dpe_connu` en premium ET de rétablir `parcel_dpe` (décision Vic). */}
                {/* M60 P1c — PORTE en pied de Propriétaire : Scan patrimoine PRÉ-REMPLI (SIREN du
                    propriétaire). Accroche contextualisée (dénomination + SIREN), jamais générique. */}
                {f.proprietaire_moral?.siren && (
                  <PorteOutil ico="⌂" data="patrimoine" titre="Scan patrimoine du propriétaire"
                    sous={`Tout le foncier de ${f.proprietaire_moral.denomination ?? 'ce propriétaire'} · SIREN ${f.proprietaire_moral.siren}`}
                    onClick={() => { setM02Prefill(f.proprietaire_moral!.siren!); setModule('patrimoine') }} />
                )}
                {/* M70 point 7a — PORTE en pied de Propriétaire : Courrier SPF (personne physique /
                    non recensée). L'outil courrier (M09) s'ouvre pré-rempli sur la parcelle courante.
                    Une seule porte par outil (M60) : le courrier n'a de porte QUE dans ce tiroir. */}
                {!f.proprietaire_moral && (
                  <PorteOutil ico="✉" data="spf-letter" titre={CLIENT.fiche.export.spf}
                    sous="Courrier pré-rempli à envoyer au SPF pour identifier le propriétaire."
                    onClick={() => { setCourrierPrefill(idu); setModule('courriers') }} />
                )}
              </div>
            </RefDrawer>

            {/* M55-O phase 3.4 : « Risques et protections » remonte dans le groupe LE TERRAIN
                (rendu plus haut, après la Constructibilité). */}

            {/* M55-O phase 2.1b : les tiroirs « Renouvellement — pourquoi ce rang » et « Pourquoi
                pas ? » sont ABSORBÉS dans le bloc Analyse (carte verdict, plus haut). Ils ne vivent
                plus en tiroirs séparés. */}

            {/* ⑧ LES DONNÉES — dernier bloc de contenu (M52 L3). Sources RÉELLEMENT utilisées sur
                cette fiche (data_sources) + données ABSENTES dites + confiance (ICD, score P), flags,
                signaler. Zéro nouvelle donnée : tout vient de tables existantes ou de nuls dits. */}
            {/* M70 décision 5 — plus de « couverture {icd.score} % » (score nu) dans le sous-titre :
                la confiance est portée par le verdict qualitatif de l'ICD (bloc plus bas). */}
            <RefDrawer id="confiance" icon={IC.confiance} name="Données et méthode"
              context={f.data_sources?.length ? `${f.data_sources.length} sources` : undefined}
              value={<></>/* DA-FICHE-v6 « pas de % nu » : à droite, juste le chevron. */}>
              <div className="flex flex-col gap-3">
                {/* Sources utilisées sur cette fiche — nom · fournisseur · millésime · fiabilité. */}
                {f.data_sources && f.data_sources.length > 0 && (
                  <div data-data-sources>
                    <p className="label-caps mb-1.5">Sources utilisées sur cette fiche</p>
                    <div className="flex flex-col gap-1">
                      {f.data_sources.map((s, i) => {
                        // millésime affiché seulement s'il est une date propre (AAAA / AAAA-MM) — les
                        // notes longues (« révisions par commune… ») cassent la ligne, le détail vit ailleurs.
                        const mill = s.millesime && /^\d{4}(-\d{2})?$/.test(s.millesime) ? s.millesime : null
                        return (
                        <div key={i} className="flex items-baseline justify-between gap-3 border-b border-line/60 py-1.5 last:border-0">
                          <div className="min-w-0">
                            <span className="text-xs text-txt">{s.nom}</span>
                            {s.fournisseur && <span className="ml-1 text-[10.5px] text-txt-dim">· {s.fournisseur}</span>}
                          </div>
                          <div className="flex shrink-0 items-baseline gap-2 whitespace-nowrap text-[10.5px] text-txt-mut">
                            {mill && <span className="tnum">{mill}</span>}
                            {/* M70 décision 4 — couleurs honnêtes : « suivie » (cataloguée + radar) en
                                mint calme, le reste (estimée/déclarative) neutre.
                                RETOURS-11F F12 (doctrine 02/09) — « à confirmer » = licence à vérifier
                                CÔTÉ VIC, PAS une information client → la chip n'est plus rendue au client
                                (le client ne voit que « à jour / pas à jour » + date, ailleurs). */}
                            {s.fiabilite && s.fiabilite !== 'à confirmer' && (() => {
                              const bg = s.fiabilite === 'suivie' ? '#5CE6A122' : '#8A968F22'
                              const fg = s.fiabilite === 'suivie' ? '#5CE6A1' : '#8A968F'
                              return <span className="rounded-full px-1.5" style={{ background: bg, color: fg }}>{s.fiabilite}</span>
                            })()}
                          </div>
                        </div>
                      )})}
                    </div>
                  </div>
                )}
                {/* M70 décision 8 — le bloc du 3ᵉ terme de la doctrine (Sourcé/Estimé/ABSENT) est
                    CONSERVÉ (le retirer laisserait croire la fiche complète) mais REPLIÉ par défaut
                    et reformulé « Ce que LABUSE ne peut pas savoir sur cette parcelle ». */}
                {donneesAbsentes.length > 0 && (
                  <details data-donnees-absentes>
                    <summary className="label-caps cursor-pointer list-none select-none">
                      Ce que LABUSE ne peut pas savoir sur cette parcelle <span className="text-txt-dim">({donneesAbsentes.length})</span>
                    </summary>
                    <ul className="mt-1.5 flex flex-col gap-1">
                      {donneesAbsentes.map((a, i) => (
                        <li key={i} className="flex gap-2 text-[11px] leading-snug text-txt-mut">
                          <span aria-hidden className="text-txt-dim">○</span>
                          <span><span className="text-txt">{a.quoi}</span> — {a.pourquoi}</span>
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
                {/* RETOURS-7 Z6 — carte « Qualité de la mesure · commune » RETIRÉE de la fiche client :
                    métrologie interne (RR intra, base %, audit fold), illisible pour un promoteur. La
                    donnée `f.qualite_commune` reste servie par le back (disponible côté admin). */}
                {/* Confiance données (ICD) — jauge de confiance UNIQUE (M55-O 2.2). */}
                {f.icd && <IcdBlockView icd={f.icd} />}
                {/* M55-O phase 2.1b : ScoreV2Block (P + « pourquoi ce score ») DÉMÉNAGÉ dans le bloc
                    Analyse (carte verdict) — l'avis LABUSE est rassemblé, plus dans « Les données ». */}
                {/* M55-O phase 2.2 — le bloc « Signaux additionnels » (f.flags) est SUPPRIMÉ : ce sont
                    des redites des tiroirs dédiés (ABF → Risques, bâti/SDP → Constructibilité, PPR →
                    Risques). Chaque information n'apparaît qu'une fois. */}
                {/* RETOURS-11 F2 — « Signaler une erreur » a QUITTÉ « Données et méthode » : c'est
                    désormais le TOUT DERNIER bloc de la fiche (voir bas de fiche). */}
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
              <div className="sec"><span>EXPORTS</span><i /></div>
              {/* RETOURS-9 (Q8.3) — deux lignes de trois : PDF · Dossier · Finance / Argumentaire · Courrier · Pré-dossier PC. */}
              <GrilleOutils cols={3}>
                <OutilCase nom="PDF" href={pdfUrl(idu, calculette)} title={calculette ? 'PDF (avec votre charge foncière)' : 'Exporter la fiche en PDF'}
                  ic={<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" /><path d="M14 3v5h5" /><path d="M12 12v5" /><path d="m9.5 14.5 2.5 2.5 2.5-2.5" /></svg>} />
                <DossierTile idu={idu} />
                <BanquierButton idu={idu} />
                {/* RETOURS-8 (R7) — Cadastre a QUITTÉ les Exports : il vit désormais en tête de fiche
                    (trio Maps · Cadastre · Pages jaunes à côté de l'IDU). */}
                <OutilCase nom="Argumentaire" data-argumentaire title="Argumentaire de négociation (PDF) — avec les hypothèses de la calculette"
                  href={`/argumentaire/${idu}.pdf${calculette ? `?cout_construction_m2=${calculette.cout_construction_m2}&marge_frais_pct=${calculette.marge_frais_pct}${calculette.vrd_m2 != null ? `&vrd_m2=${calculette.vrd_m2}` : ''}${calculette.prix_demande_eur ? `&prix_demande_eur=${calculette.prix_demande_eur}` : ''}` : ''}`}
                  ic={<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /><path d="M8 9h8" /><path d="M8 13h5" /></svg>} />
                {/* RETOURS-8 (R7) — Maps a QUITTÉ les Exports : il vit en tête de fiche (trio près de l'IDU). */}
                <OutilCase nom={CLIENT.fiche.export.courrier} data-courrier-tile onClick={() => { setCourrierPrefill(idu); setModule('courriers') }} title={CLIENT.fiche.export.courrierTip}
                  ic={<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="5" width="18" height="14" rx="2" /><path d="m3 7 9 6 9-6" /></svg>} />
                <PreDossierTile idu={idu} />
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
  const box = { marginTop: 8, background: '#110d1b', border: '1px solid #372c58', borderRadius: 12, padding: '11px 14px' } as const
  const stub = d && !d.available
  const rs = d?.rules_summary
  return (
    <div data-synthese-ia-result style={box}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
        <p style={{ margin: 0, fontSize: 11, fontWeight: 600, color: '#c9b6f2', display: 'flex', alignItems: 'center', gap: 6 }}>
          {CLIENT.fiche.ia.synthese}
          {stub && <span data-synthese-stub style={{ fontSize: 9.5, fontWeight: 500, color: '#b7a3e6', border: '1px solid #47386e', borderRadius: 5, padding: '1px 5px' }}>repli</span>}
        </p>
        <button data-synthese-replier onClick={onReplier} title="Replier — revenir aux boutons"
          style={{ background: 'none', border: '1px solid #372c58', borderRadius: 7, color: '#b7a3e6', fontSize: 11, padding: '2px 9px', cursor: 'pointer', flexShrink: 0 }}>Replier</button>
      </div>
      {pending ? (
        <p style={{ margin: '8px 0 0', color: '#c9b6f2', fontSize: 12 }}><span style={{ display: 'inline-block', width: 6, height: 6, marginRight: 8, borderRadius: 9, background: '#8a6ff0' }} className="animate-pulse" />{CLIENT.fiche.ia.syntheseEnCours}</p>
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
function BanquierButton({ idu }: { idu: string }) {
  const [etat, setEtat] = useState<'idle' | 'encours' | 'pret' | 'erreur'>('idle')
  const timer = useRef<number | null>(null)
  useEffect(() => () => { if (timer.current) window.clearTimeout(timer.current) }, [])
  useEffect(() => { setEtat('idle'); if (timer.current) window.clearTimeout(timer.current) }, [idu])
  const url = `/dossier-banquier/${idu}.pdf`
  const poll = async () => {
    try {
      const r = await fetch(`/dossier-banquier/${idu}/statut`)
      const d = await r.json()
      if (d.etat === 'pret') { setEtat('pret'); return }
      if (d.etat === 'erreur') { setEtat('erreur'); return }
    } catch { setEtat('erreur'); return }
    timer.current = window.setTimeout(poll, 1500)
  }
  const lancer = async () => {
    try {
      const r = await fetch(`/dossier-banquier/${idu}/prepare`, { method: 'POST' })
      const d = await r.json()
      if (d.etat === 'pret') { window.open(url, '_blank', 'noreferrer'); setEtat('pret'); return }
      setEtat('encours'); timer.current = window.setTimeout(poll, 1500)
    } catch { setEtat('erreur') }
  }
  // C6 · « Financier » (ex-Banquier) — rendu en tuile .exp (DA-FICHE-v6).
  const icon = <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="6" width="18" height="12" rx="2" /><circle cx="12" cy="12" r="2.5" /></svg>
  if (etat === 'pret') return (
    <OutilCase nom={CLIENT.fiche.export.banquierPret} ic={icon} href={url} title="Note de financement prête — ouvrir le PDF" />
  )
  if (etat === 'encours') return (
    <OutilCase nom={CLIENT.fiche.export.banquierEnCours} ic={icon} disabled title="Préparation en cours…" />
  )
  return (
    <OutilCase nom={etat === 'erreur' ? CLIENT.fiche.export.banquierErreur : CLIENT.fiche.export.finance} ic={icon}
      onClick={lancer} data-banquier-btn title={etat === 'erreur' ? 'Génération impossible — réessayer' : CLIENT.fiche.export.banquierTip} />
  )
}


/** BLOC B · S45 — Traducteur PLU (variante B, verdict Vic) : bloc dépliable de l'onglet
 *  Règles. Sourcé = article calibré, Estimé = générique.
 *  M76 pt4 : le bloc ne s'affiche QUE s'il a quelque chose à dire — masqué entièrement quand aucune
 *  règle n'est traduisible pour la zone (ex. zones A/N non constructibles, 152 638 parcelles). Le
 *  fetch est donc AVANCÉ (déterministe, pas d'IA sur `{}`) pour connaître `regles_appliquees` avant
 *  de rendre : plus de bloc qui s'affiche pour annoncer son propre vide. */
function TraducteurBloc({ idu }: { idu: string }) {
  const [open, setOpen] = useState(false)
  const q = useQuery({
    queryKey: ['traducteur', idu],
    queryFn: async () => {
      const r = await fetch(`/traducteur-plu/${idu}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
      if (!r.ok) throw new Error(`traducteur ${r.status}`)
      return r.json() as Promise<{
        ok: boolean; zone: string | null; zone_calibree: boolean
        regles_appliquees: { regle: string; valeur: string; source: string }[]
        reglement: { url: string | null; note: string | null }
      }>
    },
    enabled: true, staleTime: 300_000,
  })
  const d = q.data
  // M76 pt4 — tant qu'on ne sait pas OU rien à traduire → aucun bloc (jamais « Aucune règle traduite »).
  if (!d || d.regles_appliquees.length === 0) return null
  return (
    <div data-traducteur className="mb-3 rounded-lg border border-violet/30 bg-violet/[0.06] px-3 py-2">
      <button data-traducteur-toggle onClick={() => setOpen((o) => !o)}
        className="flex min-h-7 w-full items-center justify-between gap-2 text-left">
        {/* M62-P1 (j) : casse NORMALE (plus de capitales `label-caps`) — « Demander à l'IA de traduire le PLU ». */}
        <span className="text-[11px] font-medium tracking-normal normal-case text-violet">✦ Demander à l'IA de traduire le PLU</span>
        <span className="text-[11px] text-txt-dim">{open ? 'replier ▴' : 'déplier ▾'}</span>
      </button>
      {open && (
        <div className="mt-2">
          {/* M55-N point 9 (décision Vic) : <AvisIA/> RETIRÉ du traducteur — la traduction de règles
              PLU est une LECTURE FACTUELLE (rien à « juger »), la mise en garde IA y était hors-sujet.
              Les surfaces IA GÉNÉRATIVES la conservent (Synthèse/explication, « Une question ? »,
              recherche IA, entretien, copilote, restitution). */}
          {/* M76 pt4 — d est garanti chargé + non vide (sinon le bloc entier est masqué au-dessus) :
              plus de rendu de chargement/erreur/vide (« Aucune règle traduite » supprimé). */}
          <div className="flex flex-wrap items-center gap-1.5">
            {d.zone && <span className="rounded-full border border-violet/50 px-2 py-0.5 text-[10px] font-semibold text-violet">zone {d.zone}</span>}
            {!d.zone_calibree && (
              <span className="rounded-full border border-st-creuser/40 bg-st-creuser/10 px-2 py-0.5 text-[10px] text-st-creuser">
                zone non calibrée — valeurs génériques (Estimé)</span>
            )}
          </div>
          <div className="mt-1.5 space-y-1">
            {d.regles_appliquees.map((r, i) => (
              <div key={i} className="flex items-baseline gap-2 text-[11.5px]">
                <span className="min-w-0 flex-1 text-txt">{r.regle}</span>
                <b className="tnum text-txt-hi">{r.valeur}</b>
                <span className="shrink-0 rounded-full border border-st-creuser/40 bg-st-creuser/10 px-1.5 text-[8.5px] font-medium text-st-creuser"
                  title={r.source}>{d.zone_calibree ? 'Sourcé' : 'Estimé'}</span>
              </div>
            ))}
          </div>
          <p className="mt-1.5 text-[10px] leading-snug text-txt-dim">
            La référence opposable reste le règlement écrit{d.reglement?.url ? <> — <a className="text-mint hover:underline" href={d.reglement.url} target="_blank" rel="noreferrer">l'ouvrir ↗</a></> : ''}.
          </p>
        </div>
      )}
    </div>
  )
}
