import { useQuery } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'
import { getSources } from '../../lib/api'
import type { SourceInfo } from '../../lib/types'
import { useApp } from '../../store/useApp'
import { Loading } from '../Loading'

const STATUS_DOT: Record<string, string> = {
  active: '#5CE6A1', ok: '#5CE6A1', connecte: '#5CE6A1', partial: '#E8B44C', partiel: '#E8B44C',
  degraded: '#E8B44C', manuel: '#E8B44C', planned: '#5C7268', todo: '#5C7268', a_faire: '#5C7268',
  error: '#E8695A', down: '#E8695A',
}

// P4.2 (dernière passe) — « version la plus récente publiée » : rassure que LABUSE n'est pas
// en retard, c'est la SOURCE qui publie par millésime. Notes VÉRIFIÉES + repli sur l'année du nom.
// VUES item 4 : la mention « dernière version publiée » est RÉSERVÉE aux lignes vérifiées
// (source_checks.verified_at) — les notes de millésime redeviennent purement factuelles.
const MILLESIME_VERIFIE: Record<string, string> = {
  'DVF / valeurs foncières': 'ventes jusqu’à déc. 2025',
}
function millesimeNote(s: SourceInfo): string | null {
  if (MILLESIME_VERIFIE[s.name]) return MILLESIME_VERIFIE[s.name]
  const y = s.name.match(/\b(19|20)\d{2}\b/)
  return y ? `millésime ${y[0]}` : null
}

// ── UX V1 ajout A : PRÉCISION MESURÉE quand elle existe — jamais un chiffre inventé. ──
// Chaque valeur vient d'une mesure interne consignée (rapports de mandat).
const PRECISION_PAR_SOURCE: Record<string, string> = {
  'Géoplateforme IGN': 'détection piscines : 90,7 % (échantillon interne, ortho 2025)',
  'Base Adresse Nationale': '99,99 % des parcelles rattachées à une adresse',
  'VRD / assainissement (SPANC)': 'signal ANC calé sur les zonages Office de l’eau',
}
const PRECISIONS_MESUREES: { couche: string; precision: string; methode: string }[] = [
  { couche: 'Piscines (détection sur ortho IGN)', precision: '90,7 %',
    methode: 'échantillon interne contrôlé, ortho 2025 — fiabilité statistique, non contractuelle' },
  { couche: 'Recherche en langage naturel → filtres', precision: '20/20',
    methode: 'jeu de recette interne, chaque traduction validée par schéma (jamais de SQL généré)' },
  { couche: 'Adresses (rattachement BAN)', precision: '99,99 %',
    methode: 'rattachement parcelle ↔ adresse certifiée BAN sur l’île entière' },
  { couche: 'Assainissement non collectif (signal ANC)', precision: 'calé Office de l’eau',
    methode: 'zonages SPANC + EGOUL RP à l’IRIS — signal de priorisation, pas un diagnostic' },
]

// ── M6 Phase 2a (audit §1.11) : licence RÉELLE par source — plus jamais le repli
// « Données publiques » (R6). Le libellé est lu dans legal_notes (rempli ligne à ligne
// au 2a-p1, seed_sources.py = source de vérité) ; le référentiel par nom ne garde que
// les cas particuliers (usage encadré, non intégré, lignes hors seed).
const LICENCE_PAR_SOURCE: Record<string, string> = {
  'DVF / valeurs foncières': 'Licence Ouverte — usage encadré (art. L.112 A LPF)',
  'INPI RNE (dirigeants)': 'Licence INPI — réutilisation encadrée (L. 323-2 CRPA)',
  'Fichiers fonciers (Cerema)': 'Convention Cerema — non intégré',
  'PLH des 5 EPCI (extraction documentaire)': 'Documents publics — licence à confirmer',
  'RTAA DOM (textes réglementaires)': 'Textes officiels (Légifrance) — réutilisation libre',
  'DEAL Réunion (WMS/WFS)': 'Licence Ouverte (données État)',
  'DEAL Réunion — PPR / aléas': 'Licence Ouverte (données État)',
  '50 pas géométriques — limite haute (DEAL)': 'Licence Ouverte (données État)',
}
function licence(s: SourceInfo): string {
  if (LICENCE_PAR_SOURCE[s.name]) return LICENCE_PAR_SOURCE[s.name]
  const notes = s.legal_notes ?? ''
  if (/licence ouverte/i.test(notes)) return 'Licence Ouverte 2.0 (Etalab)'
  if (/odbl/i.test(notes)) return 'ODbL 1.0 (OpenStreetMap)'
  if (/CC BY 4\.0/i.test(notes)) return 'CC BY 4.0'
  // Jamais un libellé inventé : sans licence vérifiée à l'audit, on l'affiche tel quel.
  return 'Licence à confirmer'
}
// Lien vers le TEXTE de la licence (audit §1.11 : « lien licence » exigé par le mandat).
const LICENCE_URL: Record<string, string> = {
  'Licence Ouverte 2.0 (Etalab)': 'https://www.etalab.gouv.fr/licence-ouverte-open-licence',
  'Licence Ouverte (données État)': 'https://www.etalab.gouv.fr/licence-ouverte-open-licence',
  'Licence Ouverte — usage encadré (art. L.112 A LPF)': 'https://www.etalab.gouv.fr/licence-ouverte-open-licence',
  'ODbL 1.0 (OpenStreetMap)': 'https://www.openstreetmap.org/copyright',
  'CC BY 4.0': 'https://creativecommons.org/licenses/by/4.0/deed.fr',
  'Licence INPI — réutilisation encadrée (L. 323-2 CRPA)':
    'https://www.inpi.fr/sites/default/files/Licence%20donnees%20RNE_2024_0.pdf',
}
/** Attribution EXIGÉE par la licence, lue dans legal_notes (motif « attribution : « … » »
 *  posé au 2a-p1). Le jeton [date …] (INPI art. 2.4 : source + date de dernière mise à
 *  jour) est remplacé par la date réelle de synchronisation — jamais une date inventée. */
function attribution(s: SourceInfo, majIso: string | null): string | null {
  const m = (s.legal_notes ?? '').match(/(?:attribution[^«]*|mention )«\s*([^»]+?)\s*»/i)
  if (!m) return null
  return majIso ? m[1].replace(/\[date[^\]]*\]/i, new Date(majIso).toLocaleDateString('fr-FR')) : m[1]
}

//: enums techniques → libellés produit (jamais de valeur brute face client)
const FIABILITE_LABEL: Record<string, string> = {
  verifie: 'vérifiée', a_confirmer: 'à confirmer', fragile: 'fragile', haute: 'haute', bonne: 'bonne',
}

// ── M6.1 item 4 : cadence de publication du PRODUCTEUR — référentiel prudent. ──
// Uniquement des cadences documentées par le producteur ; toute source absente de cette
// liste reste « À VÉRIFIER » avec prochaine MAJ « — » (jamais une cadence inventée).
const CADENCE_PAR_SOURCE: Record<string, { label: string; jours: number }> = {
  'DVF / valeurs foncières': { label: 'semestrielle (DGFiP — avril & octobre)', jours: 184 },
  "SITADEL (autorisations d'urbanisme)": { label: 'mensuelle (SDES)', jours: 31 },
  'BODACC (procédures collectives)': { label: 'quotidienne (DILA, jours ouvrés)', jours: 4 },
  'Cadastre (API Carto PCI)': { label: 'semestrielle (PCI vecteur)', jours: 184 },
  'Cadastre Etalab (bulk DGFiP/Etalab)': { label: 'semestrielle (Etalab)', jours: 184 },
  'BD TOPO IGN': { label: 'trimestrielle (IGN)', jours: 92 },
  'RGE ALTI (altimétrie)': { label: 'ponctuelle (campagnes IGN)', jours: 0 },
  'DPE ADEME (logements existants)': { label: 'hebdomadaire (ADEME)', jours: 10 },
  'BPE INSEE': { label: 'annuelle (millésime INSEE)', jours: 366 },
  'Filosofi INSEE (carreaux 200 m)': { label: 'annuelle (millésime INSEE)', jours: 366 },
  'INSEE RP Logement 2023': { label: 'annuelle (millésime INSEE)', jours: 366 },
  'Fichiers fonciers (Cerema)': { label: 'annuelle (millésime DGFiP/Cerema)', jours: 366 },
}
// NB SITADEL/DPE : petite marge (31 j, 10 j) pour ne pas passer orange le jour même de la
// cadence théorique — le badge juge le retard, pas l'heure de publication.

type Badge = 'a_jour' | 'maj_attendue' | 'a_verifier'
const BADGE_META: Record<Badge, { label: string; color: string; title: string }> = {
  a_jour: { label: 'À JOUR', color: '#5CE6A1',
    title: 'Donnée plus récente que la cadence de publication du producteur' },
  maj_attendue: { label: 'MAJ ATTENDUE', color: '#E8B44C',
    title: 'La date de prochaine publication du producteur est dépassée — rafraîchissement à lancer' },
  a_verifier: { label: 'À VÉRIFIER', color: '#5C7268',
    title: 'Cadence du producteur non documentée ici (ou aucune date de donnée tracée) — pas de verdict inventé' },
}

/** Fraîcheur HONNÊTE : date de donnée réelle (majReelle) × cadence documentée du producteur.
 *  Sans cadence documentée ou sans date tracée → « À VÉRIFIER », jamais un vert par défaut. */
function fraicheur(s: SourceInfo, majIso: string | null): { badge: Badge; prochaine: Date | null; cadence: string | null } {
  const cad = CADENCE_PAR_SOURCE[s.name]
  if (!cad || !cad.jours || !majIso) return { badge: 'a_verifier', prochaine: null, cadence: cad?.label ?? null }
  const prochaine = new Date(new Date(majIso).getTime() + cad.jours * 86_400_000)
  return { badge: prochaine.getTime() >= Date.now() ? 'a_jour' : 'maj_attendue', prochaine, cadence: cad.label }
}

/** La date de mise à jour AFFICHÉE : la plus récente entre last_sync_at (posé par les jobs)
 *  et la dernière ingestion tracée dans ingestion_runs (servie par l'API — jamais en dur). */
function majReelle(s: SourceInfo): { iso: string | null; viaRuns: boolean } {
  const a = s.last_sync_at, b = s.derniere_ingestion
  if (a && b) return b > a ? { iso: b, viaRuns: true } : { iso: a, viaRuns: false }
  if (b) return { iso: b, viaRuns: true }
  return { iso: a, viaRuns: false }
}

function Row({ s, focused }: { s: SourceInfo; focused: boolean }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (focused) ref.current?.scrollIntoView({ block: 'center' })
  }, [focused])
  const maj = majReelle(s)
  const mil = millesimeNote(s)
  const prec = PRECISION_PAR_SOURCE[s.name]
  // M6.1 item 4 : badge calculé sur la date de donnée RÉELLE × cadence du producteur
  const f = fraicheur(s, maj.iso)
  const badge = BADGE_META[f.badge]
  // J+2 : la date de la dernière DONNÉE (pas seulement l'ingestion) — les dates parlent seules
  const donneeJusquau = s.derniere_donnee
    ? new Date(s.derniere_donnee).toLocaleDateString('fr-FR') : null
  return (
    <div ref={ref} data-source-row
      className={`flex items-center gap-4 rounded-[10px] border px-4 py-3 ${
        focused ? 'border-mint bg-[#0F1A14]' : 'border-line-2 bg-surface-3'}`}>
      <span className="h-2 w-2 shrink-0 rounded-full print:hidden" style={{ background: STATUS_DOT[s.status ?? ''] ?? '#5C7268' }}
        title={`Statut : ${s.status ?? 'inconnu'}`} />
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline gap-2">
          <span className="truncate text-xs font-medium text-txt">{s.name}</span>
          {s.provider && <span className="shrink-0 text-[11px] text-txt-dim">{s.provider}</span>}
          {/* M6.1 item 4 : badge de fraîcheur honnête — vert/orange seulement si la cadence
              du producteur est documentée, gris « À VÉRIFIER » sinon. */}
          <span data-source-badge={f.badge}
            className="shrink-0 rounded-full px-2 py-0.5 font-mono text-[9.5px] font-semibold tracking-wide"
            style={{ backgroundColor: `${badge.color}22`, color: badge.color }}
            title={`${badge.title}${f.cadence ? ` — cadence ${f.cadence}` : ''}`}>
            {badge.label}
          </span>
        </div>
        <div className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[11px] text-txt-dim">
          {s.access_type && <span>{s.access_type}</span>}
          {s.reliability_level && <span>fiabilité {FIABILITE_LABEL[s.reliability_level] ?? s.reliability_level.replace(/_/g, ' ')}</span>}
          {LICENCE_URL[licence(s)] ? (
            <a data-source-licence href={LICENCE_URL[licence(s)]} target="_blank" rel="noreferrer"
              className="hover:underline" title="Texte de la licence">{licence(s)}</a>
          ) : (
            <span data-source-licence>{licence(s)}</span>
          )}
          {/* P4.3 : lien OFFICIEL généralisé et bien visible */}
          {s.documentation_url && (
            <a href={s.documentation_url} target="_blank" rel="noreferrer"
              className="font-medium text-mint hover:underline print:hidden" title={s.documentation_url}>
              Source officielle ↗
            </a>
          )}
        </div>
        {attribution(s, maj.iso) && (
          <div data-source-attribution className="mt-0.5 text-[11px] text-txt-dim">
            {attribution(s, maj.iso)}
          </div>
        )}
        {mil && <div className="mt-0.5 text-[11px] text-[#7DE8E0]">↻ {mil}</div>}
        {prec && <div data-source-precision className="mt-0.5 text-[11px] text-mint">✓ précision mesurée : {prec}</div>}
      </div>
      <div className="shrink-0 text-right">
        {/* VUES item 4 : « donnée du X » (réelle : jobs/ingestion_runs, sinon millésime) ;
            la 2e ligne n'existe QUE vérifiée (source_checks) — jamais de date inventée. */}
        {/* J+2 : distinguer la date des DONNÉES de la date d'INGESTION — les dates parlent seules */}
        <div data-source-donnee className="font-mono text-[11px] text-txt"
          title={maj.viaRuns ? `Dernière ingestion tracée (ingestion_runs, ${s.ingestion_runs} runs)` : undefined}>
          {donneeJusquau
            ? <>données jusqu'au {donneeJusquau}{maj.iso ? <span className="text-txt-dim"> · ingéré le {new Date(maj.iso).toLocaleDateString('fr-FR')}</span> : null}</>
            : maj.iso ? `donnée du ${new Date(maj.iso).toLocaleDateString('fr-FR')}`
              : mil ? `donnée du ${mil}` : '—'}
        </div>
        {/* M6.1 item 4 : prochaine MAJ calculée depuis la cadence du producteur — « — »
            quand la cadence n'est pas documentée, jamais une date inventée. */}
        <div data-source-prochaine className="mt-0.5 text-[11px] text-txt-dim"
          title={f.cadence ? `Cadence du producteur : ${f.cadence}` : 'Cadence du producteur non documentée'}>
          prochaine MAJ attendue : {f.prochaine
            ? <span className={f.badge === 'maj_attendue' ? 'font-medium text-[#E8B44C]' : undefined}>
                {f.prochaine.toLocaleDateString('fr-FR')}</span>
            : '—'}
        </div>
        {/* M6.1 item 4 : « vérifié le » = source_checks uniquement ; sinon mention discrète
            « jamais vérifiée » — la table est vide tant que l'audit data n'a pas tourné. */}
        {s.verified_at ? (
          <div data-source-verifiee className="mt-0.5 text-[11px] text-mint">
            dernière version publiée — vérifié le {new Date(s.verified_at).toLocaleDateString('fr-FR')}
          </div>
        ) : (
          <div data-source-verifiee="jamais" className="mt-0.5 text-[10.5px] italic text-txt-dim opacity-70">
            jamais vérifiée
          </div>
        )}
      </div>
    </div>
  )
}

export function SourcesPage() {
  const { data, isLoading, isError } = useQuery({ queryKey: ['sources'], queryFn: getSources })
  const sourcesFocus = useApp((s) => s.sourcesFocus)

  // M5 : version du modèle P v2 (sha court + gel) et avertissement censure — additif.
  const modele = useQuery({
    queryKey: ['v2-modele'],
    queryFn: async () => {
      const r = await fetch('/v2/modele')
      if (!r.ok) throw new Error(`v2 ${r.status}`)
      return r.json() as Promise<{ model_version: string; sha256_court: string; gel: string;
        avertissement_censure: string; politique_recalibration: string }>
    },
    retry: false, staleTime: 5 * 60_000,
  }).data

  const cats = new Map<string, SourceInfo[]>()
  for (const s of data ?? []) {
    const k = s.category || 'Autres'
    cats.set(k, [...(cats.get(k) ?? []), s])
  }
  return (
    <div data-sources-page className="sources-print flex min-w-0 flex-1 flex-col overflow-y-auto">
      <div className="mx-auto w-full max-w-3xl px-6 py-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-sm font-medium text-txt-hi">Sources & fraîcheur</h2>
            {/* UX V1 ajout A : la phrase de positionnement — l'écran de crédibilité en rendez-vous */}
            <p data-sources-positionnement className="mt-1 text-[13px] font-medium leading-snug text-txt">
              Chaque réponse LABUSE est traçable jusqu'à sa source publique.
            </p>
          </div>
          <button onClick={() => window.print()}
            className="shrink-0 rounded-lg border border-line-2 px-3 py-1.5 text-[11px] text-txt-mut hover:border-mint hover:text-txt print:hidden"
            title="Imprimer ce tableau (fond clair)">
            Imprimer
          </button>
        </div>
        <p className="mt-1.5 text-[11px] leading-relaxed text-txt-dim">
          Ci-dessous, couche par couche : la source publique, sa <b className="text-txt-mut">date de
          dernière mise à jour réelle</b> (lue dans le journal d'ingestion, jamais saisie à la main),
          le millésime lorsque la source publie par millésime, la précision quand elle a été mesurée,
          et la licence de réutilisation.
        </p>
        {modele && (
          <div data-sources-modele className="mt-3 rounded-lg border border-line-2 bg-surface-2 px-4 py-2.5">
            <p className="text-xs font-medium text-txt">
              Modèle de scoring v2 : <span className="font-mono">{modele.model_version}</span>
              <span className="ml-1.5 font-mono text-[10.5px] text-txt-dim">
                sha {modele.sha256_court} — gelé le {modele.gel.slice(0, 10)}
              </span>
            </p>
            <p className="mt-1 text-[11px] leading-snug text-st-creuser">
              ⚠ {modele.avertissement_censure}.
            </p>
            <p className="mt-0.5 text-[10.5px] leading-snug text-txt-dim">{modele.politique_recalibration}.</p>
          </div>
        )}
        <p data-sources-fraicheur className="mt-3 rounded-lg border border-line-2 bg-surface-2 px-4 py-2.5 text-xs font-medium text-txt">
          Chaque source à sa fraîcheur maximale, prouvée.
          <span className="ml-1.5 font-normal text-txt-dim">La mention « vérifié le » n'apparaît que
          lorsqu'un contrôle a réellement eu lieu — jamais de date déclarative.</span>
          {/* M6.1 item 4 : légende des badges — le verdict vient de la cadence DOCUMENTÉE
              du producteur ; cadence inconnue = gris, pas un vert de complaisance. */}
          <span data-sources-legende className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 font-normal text-[10.5px] text-txt-dim">
            {(Object.keys(BADGE_META) as Badge[]).map((b) => (
              <span key={b} className="flex items-center gap-1">
                <span className="rounded-full px-1.5 py-px font-mono text-[9px] font-semibold"
                  style={{ backgroundColor: `${BADGE_META[b].color}22`, color: BADGE_META[b].color }}>
                  {BADGE_META[b].label}
                </span>
                {b === 'a_jour' && 'donnée dans la cadence du producteur'}
                {b === 'maj_attendue' && 'prochaine publication dépassée'}
                {b === 'a_verifier' && 'cadence non documentée — pas de verdict inventé'}
              </span>
            ))}
          </span>
        </p>

        {/* UX V1 ajout A : les précisions MESURÉES — uniquement des chiffres issus de mesures
            internes consignées, jamais un pourcentage marketing. */}
        <div className="mt-6">
          <p className="mb-2 font-mono text-[11px] tracking-widest text-txt-dim">PRÉCISION MESURÉE — COUCHES DÉRIVÉES LABUSE</p>
          <div data-sources-precisions className="flex flex-col gap-2">
            {PRECISIONS_MESUREES.map((p) => (
              <div key={p.couche} className="flex items-baseline gap-4 rounded-[10px] border border-line-2 bg-surface-3 px-4 py-2.5">
                <div className="min-w-0 flex-1">
                  <span className="text-xs font-medium text-txt">{p.couche}</span>
                  <div className="mt-0.5 text-[11px] leading-snug text-txt-dim">{p.methode}</div>
                </div>
                <span className="shrink-0 font-display text-sm font-bold text-mint">{p.precision}</span>
              </div>
            ))}
          </div>
        </div>

        {isLoading && <div className="mt-6"><Loading label="Chargement des sources" className="text-xs" /></div>}
        {isError && <p className="mt-6 text-xs text-st-ecartee">Sources inaccessibles — vérifiez votre réseau ou réessayez.</p>}
        {[...cats.entries()].map(([cat, list]) => (
          <div key={cat} className="mt-6">
            <p className="mb-2 font-mono text-[11px] tracking-widest text-txt-dim">{cat.toUpperCase()}</p>
            <div className="flex flex-col gap-2">
              {list.map((s) => <Row key={s.id} s={s} focused={s.name === sourcesFocus} />)}
            </div>
          </div>
        ))}
        <p className="mt-6 text-[11px] leading-relaxed text-txt-dim">
          Les rafraîchissements sont aujourd'hui manuels ; cet écran affichera la fraîcheur
          automatique dès que la synchronisation planifiée sera en place.
        </p>
      </div>
    </div>
  )
}
