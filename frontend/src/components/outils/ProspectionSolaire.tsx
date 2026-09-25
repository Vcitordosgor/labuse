/**
 * Outil « Prospection solaire » — données solaire/piscines de `parcel_solar` / `parcel_equipements`,
 * GELÉES au 11/07/2026 (PVGIS v5.3 SARAH3, RGE ALTI, Ortho Express RVB 20 cm 2025, détection FLAIR).
 * RETOURS-11F4 C6 : « BD ORTHO 20 cm 2025 » corrigé — le seul millésime 2025 servi au 974 par l'IGN est
 * l'Ortho Express RVB (GetTile vérifié) ; « BD ORTHO 2025 » n'existe pas au 974. RGPD :
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
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { getPiscinesAgregat, getPiscinesListe, getPiscinesPoints, getSolaireFiche,
  postPasUnePiscine, type PiscineItem, type SolaireFiche } from '../../lib/api'
import { fmtInt } from '../../lib/format'
import { TOKENS } from '../../lib/tokens'
import { useApp } from '../../store/useApp'
import { ParcelInput } from '../ParcelInput'
import { Squelette } from '../Loading'
import { ErrorState } from '../States'
import { ListPaginationFooter, usePagination } from '../ListPagination'
import { Siren } from '../shared/Siren'
import { Bouton } from '../ui/Bouton'
import { Case } from '../ui/Case'
import { Chip } from '../ui/Chip'
import { Retour } from '../ui/Retour'

// A1 — plus de date « gelée » en dur : le millésime affiché à l'écran est celui SERVI par l'endpoint
// (parcel_solar.source_millesime). Un seul millésime par écran, jamais deux dates contradictoires.
const SOURCES_PIED = 'Détection FLAIR sur ortho · PVGIS v5.3 SARAH3 · RGE ALTI'
const MOIS = ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D']
const num = (v: number | null | undefined, unit = '') => (v == null ? '—' : `${fmtInt(v)}${unit}`)

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
      className="hover-fill flex items-center gap-3 rounded-lg border border-line-2 bg-surface-2 px-3 py-3 text-left transition-colors duration-quick">
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
      {/* RECETTE-2 (S16) — description RACCOURCIE : elle débordait sur 3 lignes (la carte
          Ensoleillement en fait 2) ; le titre « Piscines » + l'icône disent déjà le sujet. */}
      <Carte k="piscines" ic="💧" titre="Piscines" desc="Pisciniste — rénovation, couverture, entretien" />
      <Carte k="ensoleillement" ic="☀️" titre="Ensoleillement" desc="Installateur PV — potentiel, orientation, toiture" />
      <p className="mt-auto text-[9.5px] leading-snug text-txt-dim">{SOURCES_PIED}</p>
    </div>
  )
}

function BackBar({ onBack, titre }: { onBack: () => void; titre: string }) {
  return (
    <div className="flex items-center justify-between gap-2">
      {/* OUTILS-2 (O2-2) — fil d'Ariane vers l'OUTIL (« Prospection solaire »), pas un concept interne. */}
      <Retour data-solaire-retour label="Prospection solaire" onClick={onBack} />
      <span className="text-[12px] font-medium text-txt-hi">{titre}</span>
    </div>
  )
}

// A2 — cellule propriétaire : PM = dénomination (+ SIREN public, cliquable Pappers) ; particulier
// JAMAIS nommé (même règle privacy que l'Assemblage).
function ProprioCell({ p }: { p: PiscineItem['proprio'] }) {
  if (p.type === 'personne_morale')
    return (
      <span className="text-txt">
        {p.denomination}{p.siren ? <> · <Siren value={p.siren} className="font-mono text-[10px] text-txt-dim" /></> : null}
      </span>
    )
  return <span className="italic text-txt-dim">particulier — non nommé</span>
}

// ── MODE PISCINES (pisciniste) — PISCINES-2 : la stat d'abord, puis carte + LISTE actionnable ──
// Source UNIQUE fusionnée `piscines` (FLAIR ∪ CoSIA dédoublonnées, statut servie/à confirmer/écartée
// selon la précision MESURÉE par classe). L'outil sert à repérer les bassins À ÉQUIPER (chauffage
// solaire, couverture, PAC, entretien) et à écrire à leurs occupants. Aucune notion de « potentiel
// solaire » (hors sujet). Le seul geste de sortie = « Écrire aux occupants → » (Courrier).
const PISC_SURF_MIN = [
  { v: 0, label: 'toutes' }, { v: 15, label: '≥ 15 m²' }, { v: 25, label: '≥ 25 m²' }, { v: 40, label: '≥ 40 m²' },
]
function ModePiscines({ onBack }: { onBack: () => void }) {
  const select = useApp((s) => s.select)
  const setModuleMap = useApp((s) => s.setModuleMap)
  const setModule = useApp((s) => s.setModule)
  const setCourrierPrefillIdus = useApp((s) => s.setCourrierPrefillIdus)
  const pushOutilRetour = useApp((s) => s.pushOutilRetour)
  const qc = useQueryClient()
  const [commune, setCommune] = useState<string | null>(null)
  const [montre, setMontre] = useState(false)
  // statut : « servie » par défaut (précision mesurée ≥ 85 %) ; la bascule ajoute « à confirmer ».
  const [inclureAConfirmer, setInclureAConfirmer] = useState(false)
  const [surfMin, setSurfMin] = useState(0)
  const [proprio, setProprio] = useState<'tous' | 'pm' | 'pp'>('tous')
  const [sel, setSel] = useState<Set<string>>(new Set())   // sélection → Courrier « à l'occupant »
  const [pasPiscine, setPasPiscine] = useState<Set<string>>(new Set())

  const agg = useQuery({ queryKey: ['piscines-agg', commune, inclureAConfirmer], queryFn: () => getPiscinesAgregat(commune, 0, inclureAConfirmer), staleTime: 60_000 })
  const list = useQuery({
    queryKey: ['piscines-liste', commune, inclureAConfirmer, surfMin, proprio],
    queryFn: () => getPiscinesListe({ commune, statut: inclureAConfirmer ? 'tous' : 'servie', surfMin, proprio }),
    staleTime: 60_000, enabled: montre,
  })
  const signalerPasPiscine = async (idu: string) => {
    setPasPiscine((s) => new Set(s).add(idu))
    setSel((s) => { const n = new Set(s); n.delete(idu); return n })
    try { await postPasUnePiscine(idu) } finally {
      qc.invalidateQueries({ queryKey: ['piscines-agg'] }); qc.invalidateQueries({ queryKey: ['piscines-liste'] })
    }
  }
  const annulerPasPiscine = (idu: string) => setPasPiscine((s) => { const n = new Set(s); n.delete(idu); return n })

  const items = (list.data?.items ?? []).filter((it) => !pasPiscine.has(it.idu))
  const page = usePagination(items.length)
  const [carteBusy, setCarteBusy] = useState(false)
  const [carteAffichee, setCarteAffichee] = useState(false)
  useEffect(() => () => setModuleMap({ idus: [], extra: null }), [setModuleMap])
  useEffect(() => { setCarteAffichee(false); setModuleMap({ idus: [], extra: null }) }, [commune, setModuleMap])
  const voirCarte = async () => {
    if (carteAffichee) { setModuleMap({ idus: [], extra: null }); setCarteAffichee(false); return }
    setCarteBusy(true)
    try { setModuleMap({ idus: [], extra: await getPiscinesPoints(commune, 0, inclureAConfirmer) }); setCarteAffichee(true) }
    finally { setCarteBusy(false) }
  }
  const idusCourrier = [...sel].filter((idu) => !pasPiscine.has(idu))
  const ecrireOccupants = () => {
    setCourrierPrefillIdus(idusCourrier); setModule('courriers')
    pushOutilRetour({ module: 'prospection-solaire', label: 'Prospection solaire' })
  }
  const SOURCE_LBL: Record<string, string> = { flair: 'FLAIR', cosia: 'CoSIA', 'flair+cosia': 'FLAIR+CoSIA' }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
      <BackBar onBack={onBack} titre="💧 Piscines — à équiper" />
      <p className="text-[10.5px] leading-snug text-txt-mut">
        Les bassins détectés, à <b className="text-txt">équiper</b> : chauffage solaire, couverture / volet,
        pompe à chaleur, entretien. Repérez-les par commune, puis <b className="text-txt">écrivez à leurs occupants</b>.
      </p>
      {commune && (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
          <Retour data-piscines-reset label="Toute l’île" onClick={() => setCommune(null)} />
        </div>
      )}

      {/* SYNTHÈSE — total (servie) + par commune */}
      {agg.isLoading && <Squelette bloc />}
      {agg.isError && <ErrorState message="Détection piscines momentanément indisponible." retry={() => agg.refetch()} />}
      {agg.data && (
        <div className="rounded-lg border px-3 py-2.5" style={{ borderColor: `${TOKENS.mint}4d`, background: `${TOKENS.mint}0f` }}>
          <div className="text-[10px] text-txt-dim">Piscines détectées — {commune ?? 'toute l’île'}</div>
          <div className="mt-0.5"><b data-piscines-total className="tnum text-2xl font-semibold" style={{ color: TOKENS.mint }}>{fmtInt(agg.data.total)}</b>
            <span className="ml-2 text-[9.5px] text-txt-dim">source fusionnée · à confirmer sur site</span></div>
          {agg.data.confiance && (
            <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-[10px]">
              <span className="text-txt-dim">Statut <b className="text-txt-mut">servie</b> (précision ≥ 85 %) par défaut.</span>
              <button data-piscines-toggle-aconfirmer onClick={() => setInclureAConfirmer((v) => !v)}
                className="rounded border px-1.5 py-0.5 font-medium transition-colors duration-quick hover:brightness-110"
                style={inclureAConfirmer
                  ? { borderColor: `${TOKENS.mint}66`, color: TOKENS.mint, background: `${TOKENS.mint}12` }
                  : { borderColor: 'var(--line-2)', color: 'var(--txt-mut)' }}>
                {inclureAConfirmer ? '✓ à confirmer incluses' : `inclure à confirmer (+${fmtInt(agg.data.confiance.incertaines)})`}
              </button>
              {(agg.data.corrigees ?? 0) > 0 && (
                <span className="text-txt-dim">· {fmtInt(agg.data.corrigees ?? 0)} retirée(s) « pas une piscine »</span>
              )}
            </div>
          )}
          <div data-piscines-source className="mt-1 text-[9px] leading-snug text-txt-dim">{agg.data.source}</div>
          {!commune && agg.data.communes.length > 0 && (
            <div className="mt-2 flex flex-col gap-0.5">
              {agg.data.communes.slice(0, 8).map((c) => (
                <div key={c.commune} className="flex items-baseline justify-between gap-2 text-[11px]">
                  <Bouton niveau="lien" onClick={() => setCommune(c.commune)}>{c.commune}</Bouton>
                  <span className="tnum text-txt">{fmtInt(c.n)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* FILTRES pisciniste : surface min · propriétaire PM/PP */}
      {agg.data && (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[11px] text-txt-mut">
          <label className="flex items-center gap-1.5">Surface
            <select data-piscines-surf-min value={surfMin} onChange={(e) => setSurfMin(Number(e.target.value))}
              className="h-8 rounded-md border border-line-2 bg-surface-3 px-2 text-txt focus:border-mint focus:outline-none">
              {PISC_SURF_MIN.map((o) => <option key={o.v} value={o.v}>{o.label}</option>)}
            </select>
          </label>
          <label className="flex items-center gap-1.5">Propriétaire
            <select data-piscines-proprio value={proprio} onChange={(e) => setProprio(e.target.value as 'tous' | 'pm' | 'pp')}
              className="h-8 rounded-md border border-line-2 bg-surface-3 px-2 text-txt focus:border-mint focus:outline-none">
              <option value="tous">tous</option><option value="pm">personne morale</option><option value="pp">particulier</option>
            </select>
          </label>
        </div>
      )}

      {agg.data && !montre && (
        <Bouton niveau="primaire" ton="vert" data-piscines-voir onClick={() => setMontre(true)} className="shrink-0">
          Voir les parcelles
        </Bouton>
      )}
      {agg.data && montre && (
        <button data-solaire-carte data-carte-affichee={carteAffichee ? '1' : '0'} onClick={voirCarte} disabled={carteBusy}
          className="rounded-lg border py-1.5 text-center text-[11px] font-medium transition-colors duration-quick hover:brightness-110"
          style={carteAffichee
            ? { borderColor: `${TOKENS.mint}66`, color: 'var(--txt-mut)', background: 'transparent' }
            : { borderColor: `${TOKENS.mint}66`, color: TOKENS.mint, background: `${TOKENS.mint}12` }}>
          {carteBusy ? '💧 Chargement…' : carteAffichee ? 'Masquer sur la carte' : `💧 Voir sur la carte (${fmtInt(agg.data.total)})`}
        </button>
      )}

      {/* LISTE : parcelle · commune · surface bassin · source · statut · propriétaire · sélection + chip */}
      {list.isLoading && <Squelette lignes={6} />}
      {list.data && (
        <>
          <div className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto">
            {items.slice(0, page.shown).map((it, i) => (
              <div key={`${it.idu}-${i}`} data-piscines-row
                className="rounded-lg border border-line-2 bg-surface-3 px-2.5 py-1.5">
                <div className="flex items-center gap-2">
                  <Case data-piscines-sel aria-label="Sélectionner"
                    checked={sel.has(it.idu)}
                    onChange={() => setSel((s) => { const n = new Set(s); n.has(it.idu) ? n.delete(it.idu) : n.add(it.idu); return n })} />
                  <span className="cursor-pointer font-mono text-[11px] text-txt-hi hover:text-mint" onClick={() => select(it.idu)}>{it.idu.slice(8)}</span>
                  <span className="ml-auto tnum text-[11px] text-txt">{it.surface_m2 == null ? '—' : `${fmtInt(it.surface_m2)} m²`}</span>
                </div>
                <div className="mt-0.5 flex flex-wrap items-center gap-1.5 pl-6 text-[10.5px]">
                  <span className="shrink-0 text-txt-mut">{it.commune}</span>
                  <span className="text-txt-dim">·</span>
                  <span className="min-w-0 flex-1 truncate"><ProprioCell p={it.proprio} /></span>
                  <span className="shrink-0 rounded bg-surface-2 px-1 text-[8.5px] text-txt-dim">{SOURCE_LBL[it.source] ?? it.source}</span>
                  {it.statut === 'a_confirmer' && <span className="shrink-0 rounded bg-amber-500/15 px-1 text-[8.5px] font-medium text-amber-500">à confirmer</span>}
                  <Chip data-piscines-pas ton="neutre" className="shrink-0"
                    onClick={(e) => { e.stopPropagation(); void signalerPasPiscine(it.idu) }}>pas une piscine</Chip>
                </div>
              </div>
            ))}
            {pasPiscine.size > 0 && (
              <div className="px-1 text-[9.5px] text-txt-dim">
                {fmtInt(pasPiscine.size)} retirée(s) cette session · <button className="text-mint hover:underline" onClick={() => [...pasPiscine].forEach(annulerPasPiscine)}>Annuler tout</button>
              </div>
            )}
          </div>
          <ListPaginationFooter shown={Math.min(page.shown, items.length)} total={items.length} onMore={page.more}>
            {list.data.total > items.length && (
              <span data-piscines-cap className="text-[10.5px] text-txt-dim">
                {fmtInt(items.length)} sur <b className="text-txt-mut">{fmtInt(list.data.total)}</b> — la carte les montre toutes.
              </span>
            )}
          </ListPaginationFooter>
          {/* SEUL geste de sortie : Courrier « à l'occupant » (81 % des propriétaires sont des particuliers non nommés). */}
          <Bouton niveau="secondaire" ton="vert" data-piscines-courrier disabled={idusCourrier.length === 0}
            onClick={ecrireOccupants} className="shrink-0">
            ✉ Écrire aux occupants ({idusCourrier.length}) →
          </Bouton>
        </>
      )}
      <p className="text-[9.5px] leading-snug text-txt-dim">Source unique fusionnée FLAIR ∪ CoSIA (IGN 20 cm 2025) · propriétaire DGFiP</p>
    </div>
  )
}

// ── MODE ENSOLEILLEMENT — barre unique → fiche soleil « Ma parcelle » ──
// O13a (RETOURS-11) — l'onglet « Top parcelles » (classement) est retiré : l'installateur PV part
// d'UNE parcelle désignée, pas d'une liste globale. Reste la barre unique (SOCLE) → fiche soleil.
function ModeEnsoleillement({ onBack, prefillIdu }: { onBack: () => void; prefillIdu?: string | null }) {
  const select = useApp((s) => s.select)
  const [ficheIdu, setFicheIdu] = useState<string | null>(prefillIdu ?? null)

  const fiche = useQuery({ queryKey: ['solaire-fiche', ficheIdu], queryFn: () => getSolaireFiche(ficheIdu!), enabled: !!ficheIdu, retry: false })

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
      <BackBar onBack={onBack} titre="☀️ Ensoleillement" />
      {/* BARRE UNIQUE (SOCLE) → FICHE SOLEIL */}
      <ParcelInput dataAttr="solaire-idu" placeholder="Adresse, IDU ou référence (BW0917)" onPick={setFicheIdu} />
      {ficheIdu && fiche.isLoading && <Squelette lignes={4} />}
      {ficheIdu && fiche.isError && <ErrorState message="Parcelle introuvable — vérifiez l’IDU." retry={() => fiche.refetch()} />}
      {ficheIdu && fiche.data && <FicheSoleil f={fiche.data} onOpen={() => select(ficheIdu)} />}
      {!ficheIdu && <p className="text-[11px] text-txt-mut">Saisissez une parcelle pour sa fiche soleil (potentiel, toiture, profil mensuel).</p>}
      {/* GEOPF-3 — la couche « Contraintes EnR près des habitations » (loi APER) est superposable sur
          la carte (groupe Énergie) : périmètres réglementaires liés aux habitations. */}
      <p data-solaire-enr-habitation className="text-[9.5px] leading-snug text-txt-dim">
        💡 Couche carte « Contraintes EnR près des habitations » (loi APER) disponible dans le groupe
        <b className="text-txt-mut"> Énergie</b> du panneau Couches.
      </p>
      <p className="mt-auto text-[9.5px] leading-snug text-txt-dim">{SOURCES_PIED}</p>
    </div>
  )
}

// OUTILS-S1 (Lot A) — chaque fait porte sa provenance, MÊME vocabulaire que la fiche : « Sourcé »
// (mesuré/relevé : emprise BD TOPO, pente RGE ALTI/LiDAR) vs « Estimé » (modélisé : potentiel PVGIS,
// dimensionnement, azimut d'enveloppe, nature de toit interprétée).
function ProvTag({ t }: { t: 'Sourcé' | 'Estimé' }) {
  const src = t === 'Sourcé'
  return (
    <span className={`rounded px-1 text-[8px] font-medium ${src ? 'bg-mint/15 text-mint' : 'bg-amber-500/15 text-amber-500'}`}>{t}</span>
  )
}
function KPI({ k, v, u, prov }: { k: string; v: string; u?: string; prov?: 'Sourcé' | 'Estimé' }) {
  return (
    <div className="rounded bg-surface-2 px-2 py-1">
      <div className="flex items-center justify-between gap-1">
        <span className="text-[9px] text-txt-dim">{k}</span>
        {prov && <ProvTag t={prov} />}
      </div>
      <div className="text-[13px] font-semibold text-txt">{v}{u && <span className="ml-1 text-[9px] font-normal text-txt-dim">{u}</span>}</div>
    </div>
  )
}

// RETOURS-12 O7 — PHOTO AÉRIENNE DU TOIT : vignette ortho IGN (WMS GetMap) centrée sur la parcelle,
// ~60 m de côté. Nord en haut (ortho standard) ; la rosace ci-dessous porte l'aiguille de l'azimut.
function orthoUrl(lon: number, lat: number): string {
  const d = 0.00030   // ~33 m de demi-côté
  const bbox = `${lat - d},${lon - d},${lat + d},${lon + d}`   // WMS 1.3.0 · EPSG:4326 = lat,lon
  return 'https://data.geopf.fr/wms-r/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap'
    + '&LAYERS=ORTHOIMAGERY.ORTHOPHOTOS&STYLES=&CRS=EPSG:4326&FORMAT=image/jpeg'
    + `&WIDTH=480&HEIGHT=320&BBOX=${bbox}`
}

// RETOURS-12 O7 — ROSACE d'orientation : cardinaux (N/S/E/O, N en haut) + aiguille sur l'azimut RÉEL
// du bâti (0° = Nord, sens horaire). Sans azimut, la rosace montre les cardinaux sans aiguille.
function Rosace({ azimut }: { azimut: number | null }) {
  const rad = azimut == null ? null : (azimut * Math.PI) / 180
  return (
    <svg viewBox="0 0 60 60" className="pointer-events-none absolute right-1.5 top-1.5 h-14 w-14">
      <circle cx="30" cy="30" r="18" fill="rgba(7,16,9,.5)" stroke="#fff" strokeWidth="1" />
      <text x="30" y="15" textAnchor="middle" fontSize="8" fontWeight="700" fill="#fff">N</text>
      <text x="30" y="53" textAnchor="middle" fontSize="7" fill="#fff">S</text>
      <text x="48" y="33" textAnchor="middle" fontSize="7" fill="#fff">E</text>
      <text x="12" y="33" textAnchor="middle" fontSize="7" fill="#fff">O</text>
      {rad != null && (
        <line x1="30" y1="30" x2={30 + 15 * Math.sin(rad)} y2={30 - 15 * Math.cos(rad)}
          stroke="#4ADE80" strokeWidth="2.2" strokeLinecap="round" />
      )}
    </svg>
  )
}

// FICHE SOLEIL — potentiel (unité), toiture, orientation, PROFIL MENSUEL (12 barres), limites.
function FicheSoleil({ f, onOpen }: { f: SolaireFiche; onOpen: () => void }) {
  if (!f.ok) return <ErrorState message={f.message ?? 'Données solaires indisponibles'} />
  const pm = f.prod_mensuel ?? []
  const max = Math.max(...pm, 1)
  // A6 — dimensionnement SERVI PAR LE BACK (plus de calcul métier au front) : puissance installable
  // (kWc) et production annuelle sont lues telles quelles ; le ratio kWc/m² est servi et écrit à l'écran.
  const kwc = f.kwc ?? null
  const prodAn = f.prod_annuel ?? null
  const kwcParM2 = f.kwc_par_m2   // hypothèse (kWc/m²) écrite à côté du résultat
  return (
    <div data-solaire-fiche className="rounded-lg border px-3 py-2.5" style={{ borderColor: `${TOKENS.mint}55` }}>
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-[11px] text-txt">{f.idu}</span>
        <span className="text-[10px] text-txt-dim">{f.commune}{f.classement ? ` · ${f.classement}` : ''}</span>
      </div>
      <div className="mt-2 grid grid-cols-2 gap-1.5">
        <KPI k="Potentiel" v={num(f.productible)} u="kWh/kWc/an" prov="Estimé" />
        <KPI k="Toiture (emprise)" v={num(f.toit_m2, ' m²')} prov="Sourcé" />
        {/* A6 — puissance installable + production annuelle SERVIES par le back ; ratio kWc/m² écrit ci-dessous. */}
        <KPI k="Puissance installable" v={kwc == null ? '—' : String(kwc).replace('.', ',')} u="kWc" prov="Estimé" />
        <KPI k="Production annuelle" v={num(prodAn)} u="kWh/an" prov="Estimé" />
        {/* orientation = azimut DU BÂTI (Estimé), pas une orientation « optimale » (non calculée) ;
            l'inclinaison optimale n'est pas servie par la V1 → non affichée (jamais inventée). */}
        <KPI k="Orientation du bâti" v={f.azimut == null ? '—' : `${f.azimut}°`} prov="Estimé" />
        {/* RETOURS-14 S11 — nature du toit DANS la grille des faits (visible sans clic), servie
            seulement au-dessus du seuil de confiance (LiDAR) ; « non déterminée (LiDAR) » sinon. */}
        <KPI k="Nature du toit" v={f.toiture ? f.toiture.libelle_court : '—'} prov="Estimé" />
        <KPI k="Pente du terrain" v={f.pente == null ? '—' : `${f.pente}°`} prov="Sourcé" />
        <KPI k="Pente du toit (médiane)" v={f.toiture?.pente_mediane_deg == null ? '—' : `${String(f.toiture.pente_mediane_deg).replace('.', ',')}°`} prov="Sourcé" />
      </div>
      {/* A6 — l'hypothèse de dimensionnement (ratio kWc/m²) est ÉCRITE à côté du résultat, servie de la config. */}
      {kwcParM2 != null && kwc != null && (
        <p data-solaire-kwc-hyp className="mt-1 text-[9px] leading-snug text-txt-dim">
          Puissance installable = emprise toit × {String(kwcParM2).replace('.', ',')} kWc/m² (hypothèse) ; production annuelle = puissance × potentiel PVGIS.
        </p>
      )}
      {f.toiture && (
        <p data-solaire-toiture className="mt-1.5 text-[9px] leading-snug text-txt-dim">
          Nature du toit : {f.toiture.statut} — {f.toiture.methode}
        </p>
      )}
      {/* RETOURS-12 O7 — PHOTO DU TOIT (ortho IGN) + ROSACE alignée sur l'azimut réel du bâti. */}
      {f.lon != null && f.lat != null && (
        <div data-solaire-photo className="mt-2">
          <div className="relative overflow-hidden rounded-lg border border-line-2">
            <img src={orthoUrl(f.lon, f.lat)} alt="Vue aérienne du toit (ortho IGN)"
              className="block h-36 w-full object-cover" loading="lazy" />
            <Rosace azimut={f.azimut ?? null} />
          </div>
          <p className="mt-1 text-[9px] leading-snug text-txt-dim">
            Photo aérienne (ortho IGN) — rosace alignée sur l'orientation du bâti{f.azimut != null ? ` (${f.azimut}°, Estimé)` : ' (orientation non estimée)'}.
            La lecture LiDAR de la toiture (ci-dessus) se vérifie sur cette photo.
            « Pente du terrain » ci-dessus = pente moyenne du sol (RGE ALTI), pas la pente du toit.
          </p>
        </div>
      )}
      {/* GEOPF-3 — FILTRE D'EXCLUSION EnR AU SOL (loi APER) : la parcelle est dans une zone exclue
          (Parc national, réserve naturelle) → un projet solaire AU SOL y est exclu ; la TOITURE reste possible. */}
      {f.enr_au_sol_exclu && (
        <div data-solaire-enr-exclu className="mt-1.5 rounded px-2 py-1 text-[10px] leading-snug"
          style={{ background: 'rgba(214,69,80,.12)', color: '#D64550' }}>
          ⛔ Zone d'exclusion EnR au sol{f.enr_sol_exclu_zone ? ` — ${f.enr_sol_exclu_zone}` : ''} (loi APER) :
          <b> projet solaire au sol exclu</b> ici. Le solaire <b>en toiture</b> reste possible.
        </div>
      )}
      {/* O13b — croisement piscine sur la parcelle (champ déjà servi par la fiche) : signal métier
          (climatisation / bassin à chauffer). Surface piscine NON affichée (mesure aérienne fausse, O12a). */}
      {f.piscine && (
        <div data-solaire-piscine className="mt-1.5 rounded px-2 py-1 text-[10px]" style={{ background: `${TOKENS.mint}12`, color: TOKENS.mint }}>
          💧 Piscine détectée sur la parcelle
        </div>
      )}
      {pm.length === 12 && (
        <>
          <p className="mt-2 text-[9px] text-txt-dim">Profil mensuel (kWh/kWc · maille PVGIS){f.mois_optimal ? ` · pic en ${MOIS[f.mois_optimal - 1]}` : ''}</p>
          <div className="mt-0.5 flex h-14 items-end gap-0.5">
            {pm.map((v, i) => (
              <div key={i} data-solaire-bar className="flex-1 rounded-t" aria-label={`${MOIS[i]} : ${fmtInt(v)} kWh/kWc`}
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
      {/* A1 — explication en clair : l'inclinaison est le PARAMÈTRE RÉEL du calcul PVGIS (servi de la
          config), plus un « 65° » recopié en dur. Plein nord = aspect 180° (hémisphère sud). */}
      <p className="mt-1 text-[9px] leading-snug text-txt-dim">
        En clair : le potentiel est calculé sur un carré d’environ 400 m de côté (une même valeur pour toutes les parcelles du carré), pour des panneaux exposés plein nord{f.inclinaison_deg != null ? ` et inclinés à ${f.inclinaison_deg}°` : ''} — le paramétrage du modèle PVGIS pour La Réunion.
      </p>
      <Bouton niveau="lien" data-solaire-fiche-ouvrir onClick={onOpen} className="mt-1">Ouvrir la fiche complète →</Bouton>
    </div>
  )
}
