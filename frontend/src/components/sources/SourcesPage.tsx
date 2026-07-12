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

// Licence : lue dans legal_notes quand la base la porte, sinon référentiel vérifié par famille.
const LICENCE_PAR_SOURCE: Record<string, string> = {
  'OpenStreetMap / Overpass': 'ODbL — attribution OSM',
  'Parkings OSM (loi APER)': 'ODbL — attribution OSM',
  'PVGIS (Commission européenne)': 'Données CE — réutilisation libre',
  'INPI RNE (dirigeants)': 'Réutilisation encadrée INPI',
  'Fichiers fonciers (Cerema)': 'Convention Cerema (usage interne)',
  'DVF / valeurs foncières': 'Licence Ouverte — usage encadré (R112 A-3 LPF)',
}
function licence(s: SourceInfo): string {
  const notes = s.legal_notes ?? ''
  if (/licence ouverte/i.test(notes)) return 'Licence Ouverte (Etalab)'
  if (/odbl/i.test(notes)) return 'ODbL — attribution OSM'
  if (LICENCE_PAR_SOURCE[s.name]) return LICENCE_PAR_SOURCE[s.name]
  return 'Données publiques'
}

//: enums techniques → libellés produit (jamais de valeur brute face client)
const FIABILITE_LABEL: Record<string, string> = {
  verifie: 'vérifiée', a_confirmer: 'à confirmer', fragile: 'fragile', haute: 'haute', bonne: 'bonne',
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
        </div>
        <div className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[11px] text-txt-dim">
          {s.access_type && <span>{s.access_type}</span>}
          {s.reliability_level && <span>fiabilité {FIABILITE_LABEL[s.reliability_level] ?? s.reliability_level.replace(/_/g, ' ')}</span>}
          <span data-source-licence>{licence(s)}</span>
          {/* P4.3 : lien OFFICIEL généralisé et bien visible */}
          {s.documentation_url && (
            <a href={s.documentation_url} target="_blank" rel="noreferrer"
              className="font-medium text-mint hover:underline print:hidden" title={s.documentation_url}>
              Source officielle ↗
            </a>
          )}
        </div>
        {mil && <div className="mt-0.5 text-[11px] text-[#7DE8E0]">↻ {mil}</div>}
        {prec && <div data-source-precision className="mt-0.5 text-[11px] text-mint">✓ précision mesurée : {prec}</div>}
      </div>
      <div className="shrink-0 text-right">
        {/* VUES item 4 : « donnée du X » (réelle : jobs/ingestion_runs, sinon millésime) ;
            la 2e ligne n'existe QUE vérifiée (source_checks) — jamais de date inventée. */}
        <div data-source-donnee className="font-mono text-[11px] text-txt"
          title={maj.viaRuns ? `Dernière ingestion tracée (ingestion_runs, ${s.ingestion_runs} runs)` : undefined}>
          {maj.iso ? `donnée du ${new Date(maj.iso).toLocaleDateString('fr-FR')}`
            : mil ? `donnée du ${mil}` : '—'}
        </div>
        {s.verified_at && (
          <div data-source-verifiee className="mt-0.5 text-[11px] text-mint">
            dernière version publiée — vérifié le {new Date(s.verified_at).toLocaleDateString('fr-FR')}
          </div>
        )}
      </div>
    </div>
  )
}

export function SourcesPage() {
  const { data, isLoading, isError } = useQuery({ queryKey: ['sources'], queryFn: getSources })
  const sourcesFocus = useApp((s) => s.sourcesFocus)

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
        <p data-sources-fraicheur className="mt-3 rounded-lg border border-line-2 bg-surface-2 px-4 py-2.5 text-xs font-medium text-txt">
          Chaque source à sa fraîcheur maximale, prouvée.
          <span className="ml-1.5 font-normal text-txt-dim">La mention « vérifié le » n'apparaît que
          lorsqu'un contrôle a réellement eu lieu — jamais de date déclarative.</span>
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
