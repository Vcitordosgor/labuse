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
import { useInfiniteQuery, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { getPiscinesAgregat, getPiscinesListe, getPiscinesParcelles, getSolaireFiche,
  postPasUnePiscine, type SolaireFiche } from '../../lib/api'
import { fmtInt } from '../../lib/format'
import { TOKENS } from '../../lib/tokens'
import { useApp } from '../../store/useApp'
import { EntreeParcelle, type SourceParcelle } from './EntreeParcelle'   // RECETTE-1 F2
import { Reinitialiser } from '../ui/Reinitialiser'   // RECETTE-1 F3
import { Squelette } from '../Loading'
import { ErrorState } from '../States'
import { Bouton } from '../ui/Bouton'
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

// ── MODE PISCINES (pisciniste) — RECETTE-1 H13.3 : ASSISTANT EN 2 ÉTAPES. Étape 1 « Périmètre »
// (toute l'île OU une commune, avec son compte) → étape 2 « Statut » (confirmées / à confirmer / les
// deux) → résultat : compte, CARTE EN PARCELLES COLORÉES (plus des points/gouttes), liste paginée par
// 50. Source UNIQUE fusionnée `piscines` (FLAIR ∪ CoSIA dédoublonnées, statut servie/à confirmer selon
// la précision MESURÉE par classe). « pas une piscine » (correction de donnée) conservé en ICÔNE.
type PiscStatut = 'servie' | 'a_confirmer' | 'tous'
const STATUT_LBL: Record<PiscStatut, string> = { servie: 'Confirmées', a_confirmer: 'À confirmer', tous: 'Confirmées + à confirmer' }

function ModePiscines({ onBack }: { onBack: () => void }) {
  const focusParcelle = useApp((s) => s.focusParcelle)
  const setModuleMap = useApp((s) => s.setModuleMap)
  const qc = useQueryClient()
  const [step, setStep] = useState<'perimetre' | 'statut' | 'resultat'>('perimetre')
  const [commune, setCommune] = useState<string | null>(null)   // null = toute l'île
  const [statut, setStatut] = useState<PiscStatut>('servie')
  const [pasPiscine, setPasPiscine] = useState<Set<string>>(new Set())
  const [carteBusy, setCarteBusy] = useState(false)

  // AGRÉGAT (île, les deux bandes) chargé une fois : alimente le compte des deux étapes (périmètre +
  // statut). confiance.haute = confirmées de l'île · confiance.incertaines = à confirmer de l'île.
  const agg = useQuery({ queryKey: ['piscines-agg'], queryFn: () => getPiscinesAgregat(null, 0, true), staleTime: 60_000 })

  // Comptes du PÉRIMÈTRE choisi (île = totaux confiance ; commune = sa ligne dans communes).
  const ileConf = agg.data?.confiance?.haute ?? 0
  const ileAConf = agg.data?.confiance?.incertaines ?? 0
  const cRow = commune ? agg.data?.communes.find((c) => c.commune === commune) : null
  const nbConf = commune ? (cRow?.confirmees ?? 0) : ileConf
  const nbAConf = commune ? (cRow?.a_confirmer ?? 0) : ileAConf
  const nbStatut = statut === 'servie' ? nbConf : statut === 'a_confirmer' ? nbAConf : nbConf + nbAConf

  const PAGE = 50
  const list = useInfiniteQuery({
    queryKey: ['piscines-liste', commune, statut],
    queryFn: ({ pageParam }) => getPiscinesListe({ commune, statut, limit: PAGE, offset: pageParam }),
    initialPageParam: 0,
    getNextPageParam: (last) => last.a_suite ? last.offset + last.n : undefined,
    staleTime: 60_000, enabled: step === 'resultat',
  })
  const signalerPasPiscine = async (idu: string) => {
    setPasPiscine((s) => new Set(s).add(idu))
    try { await postPasUnePiscine(idu) } finally {
      qc.invalidateQueries({ queryKey: ['piscines-agg'] }); qc.invalidateQueries({ queryKey: ['piscines-liste'] })
    }
  }
  const annulerPasPiscine = (idu: string) => setPasPiscine((s) => { const n = new Set(s); n.delete(idu); return n })
  const total = list.data?.pages[0]?.total ?? 0
  const items = (list.data?.pages.flatMap((p) => p.items) ?? []).filter((it) => !pasPiscine.has(it.idu))

  // Quitter l'outil / changer de périmètre-statut efface la couche carte.
  useEffect(() => () => setModuleMap({ idus: [], extra: null }), [setModuleMap])
  // Au résultat, poser les PARCELLES COLORÉES sur la carte (tout le périmètre) ; sinon l'effacer.
  useEffect(() => {
    if (step !== 'resultat') { setModuleMap({ idus: [], extra: null }); return }
    let vivant = true
    setCarteBusy(true)
    getPiscinesParcelles(commune, statut)
      .then((fc) => { if (vivant) setModuleMap({ idus: [], extra: fc, fit: true }) })   // cadrer sur le périmètre
      .finally(() => { if (vivant) setCarteBusy(false) })
    return () => { vivant = false }
  }, [step, commune, statut, setModuleMap])

  const SOURCE_LBL: Record<string, string> = { flair: 'FLAIR', cosia: 'CoSIA', 'flair+cosia': 'FLAIR+CoSIA' }
  const CompteBadge = ({ c, a }: { c: number; a: number }) => (
    <span className="tnum shrink-0 text-[11px] text-txt">
      <b style={{ color: TOKENS.mint }}>{fmtInt(c)}</b> conf.<span className="text-txt-dim"> · {fmtInt(a)} à conf.</span>
    </span>
  )

  // ── ÉTAPE 1 — PÉRIMÈTRE ──
  if (step === 'perimetre') {
    return (
      <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
        <BackBar onBack={onBack} titre="💧 Piscines" />
        <p className="text-[11px] font-medium text-txt-hi">Étape 1 · Périmètre</p>
        <p className="text-[10px] text-txt-mut">Toute l’île ou une commune — le compte est à côté.</p>
        {agg.isLoading && <Squelette bloc />}
        {agg.isError && <ErrorState message="Détection piscines momentanément indisponible." retry={() => agg.refetch()} />}
        {agg.data && (
          <div className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto">
            <button data-piscines-perim="ile" onClick={() => { setCommune(null); setStep('statut') }}
              className="hover-fill flex items-center justify-between gap-2 rounded-lg border px-3 py-2.5 text-left transition-colors duration-quick"
              style={{ borderColor: `${TOKENS.mint}4d`, background: `${TOKENS.mint}0f` }}>
              <b className="text-[12px] text-txt-hi">Toute l’île</b>
              <CompteBadge c={ileConf} a={ileAConf} />
            </button>
            {/* RECETTE-1 H13.1 — les 24 communes, chacune « N conf · N à conf » (plus de top-8 tronqué). */}
            {agg.data.communes.map((c) => (
              <button key={c.commune} data-piscines-perim={c.commune} onClick={() => { setCommune(c.commune); setStep('statut') }}
                className="hover-fill flex items-center justify-between gap-2 rounded-lg border border-line-2 bg-surface-3 px-3 py-1.5 text-left transition-colors duration-quick">
                <span className="text-[11px] text-txt">{c.commune}</span>
                <CompteBadge c={c.confirmees ?? c.n ?? 0} a={c.a_confirmer ?? 0} />
              </button>
            ))}
          </div>
        )}
        <div data-piscines-source className="text-[9px] leading-snug text-txt-dim">Source : IGN FLAIR et CoSIA, 2025</div>
      </div>
    )
  }

  // ── ÉTAPE 2 — STATUT ──
  if (step === 'statut') {
    const Choix = ({ v, n, desc }: { v: PiscStatut; n: number; desc: string }) => (
      <button data-piscines-statut={v} onClick={() => { setStatut(v); setStep('resultat') }}
        className="hover-fill flex items-center justify-between gap-2 rounded-lg border border-line-2 bg-surface-3 px-3 py-2.5 text-left transition-colors duration-quick">
        <span className="min-w-0">
          <b className="text-[12px] text-txt-hi">{STATUT_LBL[v]}</b>
          <span className="mt-0.5 block text-[10px] leading-snug text-txt-dim">{desc}</span>
        </span>
        <b className="tnum shrink-0 text-[15px]" style={{ color: v === 'a_confirmer' ? '#E0A94F' : TOKENS.mint }}>{fmtInt(n)}</b>
      </button>
    )
    return (
      <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
        <BackBar onBack={onBack} titre="💧 Piscines" />
        <Retour data-piscines-back-perim label="Changer le périmètre" onClick={() => setStep('perimetre')} />
        <p className="text-[11px] font-medium text-txt-hi">Étape 2 · Statut</p>
        <p className="text-[10px] text-txt-mut">Périmètre : <b className="text-txt">{commune ?? 'toute l’île'}</b></p>
        <Choix v="servie" n={nbConf} desc="Précision mesurée ≥ 85 % — servies par défaut" />
        <Choix v="a_confirmer" n={nbAConf} desc="Précision mesurée 30–60 % — à vérifier sur site" />
        <Choix v="tous" n={nbConf + nbAConf} desc="Les deux, colorées distinctement sur la carte" />
        <p className="mt-auto text-[9px] leading-snug text-txt-dim">Source : IGN FLAIR et CoSIA, 2025</p>
      </div>
    )
  }

  // ── RÉSULTAT — compte · carte (parcelles colorées) · liste paginée ──
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
      <BackBar onBack={onBack} titre="💧 Piscines" />
      <div className="flex items-center justify-between gap-2">
        <Retour data-piscines-back-statut label="Changer le statut" onClick={() => setStep('statut')} />
        <Reinitialiser onReset={() => { setCommune(null); setStatut('servie'); setPasPiscine(new Set()); setStep('perimetre') }} />
      </div>
      {/* Compte + légende des couleurs de la carte */}
      <div className="rounded-lg border px-3 py-2.5" style={{ borderColor: `${TOKENS.mint}4d`, background: `${TOKENS.mint}0f` }}>
        <div>
          <b data-piscines-total className="tnum text-2xl font-semibold" style={{ color: TOKENS.mint }}>{fmtInt(nbStatut)}</b>
          <span className="ml-2 text-[11px] text-txt-mut">piscines « {STATUT_LBL[statut].toLowerCase()} » {commune ? `à ${commune}` : 'à La Réunion'}</span>
        </div>
        {(statut === 'tous' || statut === 'servie') && (
          <span className="mr-3 mt-1 inline-flex items-center gap-1 text-[9.5px] text-txt-dim">
            <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: `${TOKENS.mint}66`, border: `1px solid ${TOKENS.mint}` }} />confirmées</span>
        )}
        {(statut === 'tous' || statut === 'a_confirmer') && (
          <span className="mt-1 inline-flex items-center gap-1 text-[9.5px] text-txt-dim">
            <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: '#E0A94F66', border: '1px solid #E0A94F' }} />à confirmer</span>
        )}
        {carteBusy && <span className="ml-2 text-[9.5px] text-txt-dim">· carte en cours…</span>}
      </div>

      {/* LISTE paginée : IDU · commune · source · statut · Fiche → · « pas une piscine » (icône).
          RECETTE-1 H13.4 — colonne m² par piscine RETIRÉE. H13.3 — tri commune puis section (serveur). */}
      {list.isLoading && <Squelette lignes={6} />}
      {list.isError && <ErrorState message="Liste momentanément indisponible." retry={() => list.refetch()} />}
      {list.data && (
        <>
          <div className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto">
            {items.map((it, i) => (
              <div key={`${it.idu}-${i}`} data-piscines-row role="button" tabIndex={0}
                onClick={() => focusParcelle(it.idu, { fiche: true })}
                className="hover-fill cursor-pointer rounded-lg border border-line-2 bg-surface-3 px-2.5 py-1.5 transition-colors duration-quick">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[11px] text-txt-hi">{it.idu.slice(8)}</span>
                  <span className="shrink-0 text-[10.5px] text-txt-mut">{it.commune}</span>
                  <span className="ml-auto shrink-0 rounded bg-surface-2 px-1 text-[8.5px] text-txt-dim">{SOURCE_LBL[it.source] ?? it.source}</span>
                  {it.statut === 'a_confirmer' && <span className="shrink-0 rounded bg-amber-500/15 px-1 text-[8.5px] font-medium text-amber-500">à confirmer</span>}
                  <span className="shrink-0 text-[10px] text-mint hover:underline">Fiche →</span>
                  {/* RECETTE-1 H13.3 — « pas une piscine » en ICÔNE (croix), plus un chip texte. */}
                  <button data-piscines-pas type="button" title="Signaler : pas une piscine"
                    aria-label="Signaler : pas une piscine"
                    onClick={(e) => { e.stopPropagation(); void signalerPasPiscine(it.idu) }}
                    className="shrink-0 rounded px-1 text-[12px] leading-none text-txt-dim transition-colors hover:bg-surface-2 hover:text-txt">✕</button>
                </div>
              </div>
            ))}
            {pasPiscine.size > 0 && (
              <div className="px-1 text-[9.5px] text-txt-dim">
                {fmtInt(pasPiscine.size)} retirée(s) cette session · <button className="text-mint hover:underline" onClick={() => [...pasPiscine].forEach(annulerPasPiscine)}>Annuler tout</button>
              </div>
            )}
          </div>
          <div className="flex shrink-0 items-center justify-between gap-2 pt-1">
            <span data-piscines-cap className="text-[10.5px] text-txt-dim">
              {fmtInt(items.length)} affichée(s) sur <b className="text-txt-mut">{fmtInt(total)}</b> — la carte montre tout le périmètre.
            </span>
            {list.hasNextPage && (
              <Bouton niveau="lien" data-piscines-voir-plus onClick={() => list.fetchNextPage()} disabled={list.isFetchingNextPage}>
                {list.isFetchingNextPage ? 'Chargement…' : `Voir plus (+${PAGE})`}
              </Bouton>
            )}
          </div>
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
  const selectedIdu = useApp((s) => s.selectedIdu)   // RECETTE-1 F1 — adopter un clic carte
  const [ficheIdu, setFicheIdu] = useState<string | null>(prefillIdu ?? selectedIdu ?? null)
  // RECETTE-1 (F2) — quelle entrée a désigné la parcelle (grise l'autre dans EntreeParcelle).
  // INVARIANT (comme Taxe/Gabarit) : source='carte' UNIQUEMENT quand la parcelle vient de selectedIdu
  // (sinon l'effet F1 la viderait au montage). Un prefill (tuile Solaire de la fiche) laisse source=null.
  const [source, setSource] = useState<SourceParcelle>(selectedIdu ? 'carte' : null)

  const fiche = useQuery({ queryKey: ['solaire-fiche', ficheIdu], queryFn: () => getSolaireFiche(ficheIdu!), enabled: !!ficheIdu, retry: false })

  // RECETTE-1 (F1) — un clic carte (selectedIdu) est adopté ; fermer la fiche (selectedIdu → null)
  // alors que la parcelle venait de la carte VIDE la fiche soleil.
  useEffect(() => {
    if (selectedIdu && selectedIdu !== ficheIdu) { setFicheIdu(selectedIdu); if (source == null) setSource('carte') }
    else if (selectedIdu == null && source === 'carte') { setFicheIdu(null); setSource(null) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedIdu])
  // RECETTE-1 (F3) — Réinitialiser : vide la fiche soleil + ferme la fiche parcelle + rend les deux entrées.
  const resetAll = () => { if (selectedIdu) select(null); setFicheIdu(null); setSource(null) }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
      <BackBar onBack={onBack} titre="☀️ Ensoleillement" />
      {/* RECETTE-1 (F3) — Réinitialiser dès qu'une parcelle est désignée. */}
      {ficheIdu && <div className="flex justify-end"><Reinitialiser onReset={resetAll} /></div>}
      {/* RECETTE-1 (F2) — EntreeParcelle : adresse/IDU OU clic carte, l'une grise l'autre. */}
      <EntreeParcelle source={source}
        onPick={(i, src) => { setSource(src); setFicheIdu(i) }} />
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
