/**
 * Outil « Prospection solaire » — données solaire/piscines de `parcel_solar` / `parcel_equipements`,
 * GELÉES au 11/07/2026 (PVGIS v5.3 SARAH3, RGE ALTI, BD ORTHO 20 cm 2025, détection FLAIR). RGPD :
 * aucune donnée nominative — des parcelles et des caractéristiques, jamais des personnes.
 *
 * Mandat SOLAIRE (refonte 13 outils) — DEUX MÉTIERS, DEUX ENTRÉES (fini l'écran unique illisible) :
 *   • 💧 Piscines (pisciniste) : la STAT d'abord (compteur île + par commune), carte, listing.
 *   • ☀️ Ensoleillement (installateur PV) : critères + barre unique (SOCLE) → FICHE SOLEIL (potentiel
 *     avec unité, toiture, orientation, PROFIL MENSUEL 12 barres, limites affichées).
 * Écartées MASQUÉES par défaut dans les listes (option « les inclure »). Garde-fou : aucun recalcul —
 * présentation + requêtes d'agrégats (nouveaux endpoints /prospection-piscines et .../parcelle/{idu}
 * = lecture seule de données gelées).
 */
import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { getPiscinesAgregat, getPiscinesPoints, getProspectionSolaire, getSolaireFiche, prospectionSolaireCsvUrl,
  type SolaireFiche, type SolaireFiltres, type SolaireItem } from '../../lib/api'
import { fmtInt } from '../../lib/format'
import { verdictMeta } from '../../lib/status'
import { TOKENS } from '../../lib/tokens'
import { useApp } from '../../store/useApp'
import { ParcelInput } from '../ParcelInput'
import { Loading } from '../Loading'
import { ErrorState } from '../States'
import { CommuneScope } from './ModulePanel'

const SOURCES_PIED = 'Détection FLAIR sur ortho · PVGIS v5.3 SARAH3 · RGE ALTI · données gelées 11/07/2026'
const MOIS = ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D']
const POTENTIELS = [[0, 'Tous'], [1300, '≥ 1 300'], [1400, '≥ 1 400'], [1500, '≥ 1 500']] as const
const SURFACES = [[0, 'Toutes'], [20, '≥ 20 m²'], [40, '≥ 40 m²'], [60, '≥ 60 m²']] as const
const num = (v: number | null | undefined, unit = '') => (v == null ? '—' : `${fmtInt(v)}${unit}`)
// Écartée = verdict du run servi ; on l'exclut par défaut des listes (le tri par potentiel ne doit
// plus être noyé d'Écartées, mandat).
const isEcartee = (it: SolaireItem) => it.etage0 || it.classement === 'Écartée'

function Verdict({ it }: { it: SolaireItem }) {
  const v = verdictMeta(null, it.tier_v2, it.etage0)
  return <span className="rounded-full px-1.5 py-0.5 text-[10px] font-medium" style={{ background: `${v.color}22`, color: v.color }}>{v.label}</span>
}

// pied « Écartées masquées · les inclure » partagé par les deux listings
function EcarteesFooter({ hidden, nHidden, onToggle }: { hidden: boolean; nHidden: number; onToggle: () => void }) {
  if (nHidden <= 0 && hidden) return null
  return (
    <div className="flex items-center gap-2 border-t border-line pt-1.5 text-[10px] text-txt-dim">
      <span>{hidden ? `${fmtInt(nHidden)} écartée${nHidden > 1 ? 's' : ''} masquée${nHidden > 1 ? 's' : ''}` : 'écartées incluses'}</span>
      <button data-solaire-ecartees onClick={onToggle} className="text-mint hover:underline">{hidden ? 'les inclure' : 'les masquer'}</button>
    </div>
  )
}

export function ProspectionSolaire() {
  const [mode, setMode] = useState<'piscines' | 'ensoleillement' | null>(null)
  // RADAR-CATÉGORIE (T3) — la tuile « Solaire » de la fiche d'un bien pré-remplit l'IDU de la
  // parcelle rattachée : on ouvre DIRECTEMENT le mode ensoleillement sur cette parcelle (fiche soleil).
  const solairePrefill = useApp((s) => s.solairePrefill)
  const setSolairePrefill = useApp((s) => s.setSolairePrefill)
  const [prefillIdu, setPrefillIdu] = useState<string | null>(null)
  useEffect(() => {
    if (solairePrefill) { setPrefillIdu(solairePrefill); setMode('ensoleillement'); setSolairePrefill(null) }
  }, [solairePrefill, setSolairePrefill])
  if (mode === 'piscines') return <ModePiscines onBack={() => setMode(null)} />
  if (mode === 'ensoleillement') return <ModeEnsoleillement onBack={() => setMode(null)} prefillIdu={prefillIdu} />
  return <EntreeSolaire onChoose={setMode} />
}

// ── ÉCRAN D'ENTRÉE — deux cartes ──
function EntreeSolaire({ onChoose }: { onChoose: (m: 'piscines' | 'ensoleillement') => void }) {
  const Carte = ({ k, ic, titre, desc }: { k: 'piscines' | 'ensoleillement'; ic: string; titre: string; desc: string }) => (
    <button data-solaire-mode={k} onClick={() => onChoose(k)}
      className="flex items-center gap-3 rounded-lg border border-line-2 bg-surface-2 px-3 py-3 text-left transition-colors duration-quick hover:border-mint/50 hover:bg-surface-3">
      <span className="text-xl">{ic}</span>
      <span className="min-w-0 flex-1">
        <b className="text-[13px] text-txt">{titre}</b>
        <span className="mt-0.5 block text-[10.5px] leading-snug text-txt-dim">{desc}</span>
      </span>
      <span className="text-txt-dim">→</span>
    </button>
  )
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2">
      <p className="text-[11px] text-txt-mut">Deux métiers, deux entrées.</p>
      <Carte k="piscines" ic="💧" titre="Piscines" desc="Pisciniste — parcelles avec piscine détectée : rénovation, couverture, entretien" />
      <Carte k="ensoleillement" ic="☀️" titre="Ensoleillement" desc="Installateur PV — potentiel, orientation, toiture" />
      <p className="mt-auto text-[9.5px] leading-snug text-txt-dim">{SOURCES_PIED}</p>
    </div>
  )
}

function BackBar({ onBack, titre }: { onBack: () => void; titre: string }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <button data-solaire-retour onClick={onBack} className="text-[11px] text-mint hover:underline">‹ Deux métiers</button>
      <span className="text-[12px] font-medium text-txt-hi">{titre}</span>
    </div>
  )
}

function Select({ value, onChange, options, label }: { value: number; onChange: (v: number) => void; options: readonly (readonly [number, string])[]; label: string }) {
  return (
    <label className="flex items-center gap-1 text-[10.5px] text-txt-mut">{label}
      <select value={value} onChange={(e) => onChange(Number(e.target.value))}
        className="rounded border border-line-2 bg-surface-3 px-1.5 py-0.5 text-txt focus:border-mint focus:outline-none">
        {options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </select>
    </label>
  )
}

// ── MODE PISCINES — la stat d'abord, puis carte + listing ──
// LOT8 (OUTILS-FINALE) : le mode Piscines IGNORE le classement (toutes les piscines listées, pas de
// pied « écartées ») ; PAS de sélecteur Périmètre (toute l'île d'office, la ventilation par commune
// reste dans le bloc stats, cliquable pour drill) ; tableau 3 colonnes (Parcelle · Piscine · Commune).
function ModePiscines({ onBack }: { onBack: () => void }) {
  const select = useApp((s) => s.select)
  const setModuleMap = useApp((s) => s.setModuleMap)
  const [commune, setCommune] = useState<string | null>(null)
  const [surfMin, setSurfMin] = useState(0)

  const agg = useQuery({ queryKey: ['piscines-agg', commune, surfMin], queryFn: () => getPiscinesAgregat(commune, surfMin), staleTime: 60_000 })
  const filtres: SolaireFiltres = { commune, piscine: 'oui', piscineSurfMin: surfMin }
  const list = useQuery({ queryKey: ['piscines-list', commune, surfMin], queryFn: () => getProspectionSolaire(filtres), staleTime: 60_000 })

  const items = list.data?.items ?? []   // aucune exclusion « écartée » : le pisciniste veut TOUTES les piscines
  const [carteBusy, setCarteBusy] = useState(false)
  useEffect(() => () => setModuleMap({ idus: [], extra: null }), [setModuleMap])
  // LOT8b — « Voir sur la carte » = TOUTES les piscines en marqueurs (pas le listing capé à 500) :
  // on charge les points GeoJSON et on les pose dans module-extra (couche module-pts, kind='piscine').
  const voirCarte = async () => {
    setCarteBusy(true)
    try { setModuleMap({ idus: [], extra: await getPiscinesPoints(commune, surfMin) }) }
    finally { setCarteBusy(false) }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
      <BackBar onBack={onBack} titre="💧 Piscines" />
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
        <Select label="Surface piscine" value={surfMin} onChange={setSurfMin} options={SURFACES} />
        {commune && <button data-piscines-reset onClick={() => setCommune(null)} className="text-[10.5px] text-mint hover:underline">‹ toute l’île</button>}
      </div>

      {/* LA STAT D'ABORD */}
      {agg.isLoading && <Loading label="Comptage des piscines…" />}
      {agg.isError && <ErrorState message="Détection piscines momentanément indisponible." />}
      {agg.data && (
        <div className="rounded-lg border px-3 py-2.5" style={{ borderColor: `${TOKENS.mint}4d`, background: `${TOKENS.mint}0f` }}>
          <div className="text-[10px] text-txt-dim">Piscines détectées — {commune ?? 'toute l’île'}</div>
          <div className="mt-0.5"><b data-piscines-total className="tnum text-2xl font-semibold" style={{ color: TOKENS.mint }}>{fmtInt(agg.data.total)}</b>
            <span className="ml-2 text-[9.5px] text-txt-dim">détection ortho/IA · à confirmer sur site</span></div>
          {/* LOT8a — le SEUIL de rétention est écrit à l'écran (des détections plus incertaines sont exclues) */}
          <div data-piscines-source className="mt-1 text-[9px] leading-snug text-txt-dim">{agg.data.source}</div>
          {!commune && agg.data.communes.length > 0 && (
            <div className="mt-2 flex flex-col gap-0.5">
              {agg.data.communes.slice(0, 8).map((c) => (
                <div key={c.commune} className="flex items-baseline justify-between gap-2 text-[11px]">
                  <button onClick={() => setCommune(c.commune)} className="text-txt-mut hover:text-mint">{c.commune}</button>
                  <span className="tnum text-txt">{fmtInt(c.n)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <button data-solaire-carte onClick={voirCarte} disabled={carteBusy}
        className="rounded-lg border py-1.5 text-center text-[11px] font-medium transition-colors duration-quick hover:brightness-110 disabled:opacity-50"
        style={{ borderColor: `${TOKENS.mint}66`, color: TOKENS.mint, background: `${TOKENS.mint}12` }}>
        {carteBusy ? '💧 Chargement…' : `💧 Voir sur la carte${agg.data ? ` (${fmtInt(agg.data.total)})` : ''}`}
      </button>

      {/* LISTING piscines — 3 colonnes, aucun scroll horizontal (Classement + Toiture retirés, LOT8c) */}
      {list.isLoading && <Loading label="Parcelles…" />}
      {list.data && (
        <div className="min-h-0 flex-1 overflow-y-auto">
          <table className="w-full text-[11px]">
            <thead className="sticky top-0 bg-surface-2 text-left text-[10px] uppercase tracking-wide text-txt-dim">
              <tr><th className="px-2 py-1.5">Parcelle</th>
                <th className="px-2 py-1.5 text-right">Piscine ~m²</th><th className="px-2 py-1.5">Commune</th></tr>
            </thead>
            <tbody>
              {items.map((it) => (
                <tr key={it.idu} data-piscines-row className="cursor-pointer border-t border-line hover:bg-surface-2" onClick={() => select(it.idu)}>
                  <td className="px-2 py-1.5 font-mono text-txt">{it.idu}</td>
                  <td className="px-2 py-1.5 text-right" style={{ color: TOKENS.mint }}>{it.piscine_m2 == null ? 'détectée' : `~${fmtInt(it.piscine_m2)} m²`}</td>
                  <td className="px-2 py-1.5 text-txt-mut">{it.commune}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="text-[9.5px] leading-snug text-txt-dim">{SOURCES_PIED}</p>
    </div>
  )
}

// ── MODE ENSOLEILLEMENT — critères + barre unique → fiche soleil + listing ──
function ModeEnsoleillement({ onBack, prefillIdu }: { onBack: () => void; prefillIdu?: string | null }) {
  const select = useApp((s) => s.select)
  const [commune, setCommune] = useState<string | null>(null)
  const [potMin, setPotMin] = useState(0)
  const [inclure, setInclure] = useState(false)
  const [ficheIdu, setFicheIdu] = useState<string | null>(prefillIdu ?? null)

  const filtres: SolaireFiltres = { commune, potentielMin: potMin, sort: 'potentiel' }
  const list = useQuery({ queryKey: ['ens-list', commune, potMin], queryFn: () => getProspectionSolaire(filtres), staleTime: 60_000 })
  const fiche = useQuery({ queryKey: ['solaire-fiche', ficheIdu], queryFn: () => getSolaireFiche(ficheIdu!), enabled: !!ficheIdu, retry: false })

  const items = list.data?.items ?? []
  const visibles = inclure ? items : items.filter((it) => !isEcartee(it))
  const nHidden = items.length - items.filter((it) => !isEcartee(it)).length

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
      <BackBar onBack={onBack} titre="☀️ Ensoleillement" />
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
        <CommuneScope commune={commune} onChange={setCommune} />
        <Select label="Potentiel" value={potMin} onChange={setPotMin} options={POTENTIELS} />
      </div>

      {/* BARRE UNIQUE (SOCLE) → FICHE SOLEIL */}
      <ParcelInput dataAttr="solaire-idu" placeholder="Adresse ou IDU — la fiche soleil de la parcelle" onPick={setFicheIdu} />
      {ficheIdu && fiche.isLoading && <p className="text-[11px] text-txt-mut">Fiche soleil…</p>}
      {ficheIdu && fiche.isError && <p className="text-[11px] text-st-ecartee">Parcelle introuvable — vérifiez l’IDU.</p>}
      {ficheIdu && fiche.data && <FicheSoleil f={fiche.data} onOpen={() => select(ficheIdu)} />}

      {/* LISTING ensoleillement */}
      {list.isLoading && <Loading label="Prospection solaire…" />}
      {list.isError && <ErrorState message="Données solaires momentanément indisponibles." />}
      {list.data && (
        <>
          <a data-solaire-csv href={prospectionSolaireCsvUrl(filtres)} download className="self-start text-[11px] font-medium text-mint hover:underline">↓ Exporter (CSV)</a>
          <div className="min-h-0 flex-1 overflow-y-auto">
            <table className="w-full text-[11px]">
              <thead className="sticky top-0 bg-surface-2 text-left text-[10px] uppercase tracking-wide text-txt-dim">
                <tr><th className="px-2 py-1.5">Parcelle</th><th className="px-2 py-1.5">Classement</th>
                  <th className="px-2 py-1.5 text-right">Potentiel</th><th className="px-2 py-1.5 text-right">Pente</th>
                  <th className="px-2 py-1.5 text-right">Orient.</th><th className="px-2 py-1.5 text-right">Toiture</th></tr>
              </thead>
              <tbody>
                {visibles.map((it) => (
                  <tr key={it.idu} data-ens-row className="cursor-pointer border-t border-line hover:bg-surface-2" onClick={() => setFicheIdu(it.idu)}>
                    <td className="px-2 py-1.5 font-mono text-txt">{it.idu}</td>
                    <td className="px-2 py-1.5"><Verdict it={it} /></td>
                    <td className="px-2 py-1.5 text-right font-medium" style={{ color: TOKENS.mint }}>{num(it.productible)}</td>
                    <td className="px-2 py-1.5 text-right text-txt-mut">{it.pente == null ? '—' : `${it.pente}°`}</td>
                    <td className="px-2 py-1.5 text-right text-txt-mut">{it.azimut == null ? '—' : `${it.azimut}°`}</td>
                    <td className="px-2 py-1.5 text-right text-txt-mut">{num(it.toit_m2, ' m²')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="-mt-1 text-[9px] text-txt-dim">Potentiel en <b>kWh/kWc/an</b> (productible spécifique PVGIS). Cliquez une ligne pour sa fiche soleil.</p>
          <EcarteesFooter hidden={!inclure} nHidden={nHidden} onToggle={() => setInclure((v) => !v)} />
        </>
      )}
      <p className="text-[9.5px] leading-snug text-txt-dim">{SOURCES_PIED}</p>
    </div>
  )
}

function KPI({ k, v, u }: { k: string; v: string; u?: string }) {
  return (
    <div className="rounded bg-surface-2 px-2 py-1">
      <div className="text-[9px] text-txt-dim">{k}</div>
      <div className="text-[13px] font-semibold text-txt">{v}{u && <span className="ml-1 text-[9px] font-normal text-txt-dim">{u}</span>}</div>
    </div>
  )
}

// FICHE SOLEIL — potentiel (unité), toiture, orientation, PROFIL MENSUEL (12 barres), limites.
function FicheSoleil({ f, onOpen }: { f: SolaireFiche; onOpen: () => void }) {
  if (!f.ok) return <p className="rounded-lg bg-surface-2 px-3 py-2 text-[11px] leading-snug text-txt-dim">{f.message ?? 'Aucune donnée solaire pour cette parcelle.'}</p>
  const pm = f.prod_mensuel ?? []
  const max = Math.max(...pm, 1)
  return (
    <div data-solaire-fiche className="rounded-lg border px-3 py-2.5" style={{ borderColor: `${TOKENS.mint}55` }}>
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-[11px] text-txt">{f.idu}</span>
        <span className="text-[10px] text-txt-dim">{f.commune}{f.classement ? ` · ${f.classement}` : ''}</span>
      </div>
      <div className="mt-2 grid grid-cols-2 gap-1.5">
        <KPI k="Potentiel" v={num(f.productible)} u="kWh/kWc/an" />
        <KPI k="Toiture (emprise)" v={num(f.toit_m2, ' m²')} />
        {/* orientation = azimut DU BÂTI (Estimé), pas une orientation « optimale » (non calculée) ;
            l'inclinaison optimale n'est pas servie par la V1 → non affichée (jamais inventée). */}
        <KPI k="Orientation du bâti" v={f.azimut == null ? '—' : `${f.azimut}°`} />
        <KPI k="Pente terrain" v={f.pente == null ? '—' : `${f.pente}°`} />
      </div>
      {pm.length === 12 && (
        <>
          <p className="mt-2 text-[9px] text-txt-dim">Profil mensuel (kWh/kWc · maille PVGIS){f.mois_optimal ? ` · pic en ${MOIS[f.mois_optimal - 1]}` : ''}</p>
          <div className="mt-0.5 flex h-14 items-end gap-0.5">
            {pm.map((v, i) => (
              <div key={i} data-solaire-bar className="flex-1 rounded-t" title={`${MOIS[i]} : ${fmtInt(v)} kWh/kWc`}
                style={{ height: `${Math.max(4, Math.round((v / max) * 100))}%`, background: i + 1 === f.mois_optimal ? TOKENS.mint : `${TOKENS.mint}55` }} />
            ))}
          </div>
          <div className="flex gap-0.5 text-[8px] text-txt-dim">{MOIS.map((m, i) => <span key={i} className="flex-1 text-center">{m}</span>)}</div>
        </>
      )}
      {/* LOT9a — HONNÊTETÉ de la maille : le productible (annuel ET mensuel) est servi à la MAILLE
          PVGIS (~400 m), pas mesuré au toit → des parcelles voisines partagent la même valeur. On le
          DIT, pas de fausse précision parcellaire. */}
      <p className="mt-1.5 text-[9px] leading-snug text-txt-dim">
        Productible estimé à la <b className="text-txt-mut">maille PVGIS (~400 m)</b> — commun aux parcelles voisines, pas une mesure au toit. · Ombrage de proximité (bâti, arbres) non modélisé · panneaux existants non détectés — vérif photo aérienne avant démarchage.{f.millesime ? ` · ${f.millesime}` : ''}
      </p>
      <button data-solaire-fiche-ouvrir onClick={onOpen} className="mt-1 text-[11px] font-medium text-mint hover:underline">Ouvrir la fiche complète →</button>
    </div>
  )
}
