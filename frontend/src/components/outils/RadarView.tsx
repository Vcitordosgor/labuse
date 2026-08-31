// RADAR-CATÉGORIE (T1/T2/T3) — LA CATÉGORIE RADAR, plein écran : rail · panneau listing (434px) ·
// carte. Fidèle à la maquette docs/PIGE/maquette-radar-v2.html (écrans 1, 2, 3).
// LIGNE ROUGE (doctrine §2) : des FAITS et un LIEN, jamais le titre/texte/photo de l'annonce. Le
// mauve est réservé à l'IA — il n'apparaît nulle part ici. Couleurs = source unique (mint/amber tokens).
// Le back (pige/client.py) est réutilisé tel quel — aucune requête portail côté code (collecte 100 % humaine).
import { useQuery } from '@tanstack/react-query'
import { lazy, Suspense, useEffect, useMemo, useState } from 'react'
import { getMoi, getRadarBienDetail, getRadarBiens, getRadarDepotOuvert, radarClic, radarInteresse, radarSignaler,
  type RadarBienClient, type RadarCritere, type RadarFiltres } from '../../lib/api'
import { DepotAgence } from '../radar/DepotAgence'
import { AddressAutocomplete } from '../AddressAutocomplete'   // RETOURS-3 R13 — recherche adresse/IDU commune
import { CP_COMMUNES } from '../panel/FiltreLabuse'   // R2 — source unique des 24 communes
import { Declaratif } from './RadarDeclaratif'         // D2 — bloc déclaratif partagé (fiche + admin)
import { useApp } from '../../store/useApp'

// T6 — la carte est montée par RadarView (pour piloter le responsive) ; lazy comme dans App.
const MapView = lazy(() => import('../map/MapView').then((m) => ({ default: m.MapView })))

// T6 — mobile ≤ 767px : une seule vue à la fois (listing / carte / fiche, plein écran).
function useIsMobile(): boolean {
  const [m, setM] = useState(() => typeof window !== 'undefined' && window.matchMedia('(max-width: 767px)').matches)
  useEffect(() => {
    const mq = window.matchMedia('(max-width: 767px)')
    const on = () => setM(mq.matches)
    mq.addEventListener('change', on)
    return () => mq.removeEventListener('change', on)
  }, [])
  return m
}

const COMMUNES_24 = CP_COMMUNES.map(([, nom]) => nom).sort((a, b) => a.localeCompare(b, 'fr'))
// RADAR-DEPOT-2 D5 — pas d'« Appartement » : les copros sont collectées mais jamais servies comme
// annonces au client (elles n'existent que dans les signaux). Le tri se fait par est_copro, pas par type.
// OUTILS-3 (ajout Vic) — « Immeuble » retiré des filtres Radar (hors périmètre de la pige).
const TYPES = [['', 'Tous types'], ['maison', 'Maison'], ['terrain', 'Terrain']] as const
const TRIS = [['recentes', 'Plus récentes'], ['prix_asc', 'Prix croissant'], ['prix_desc', 'Prix décroissant'], ['anciennete', 'Ancienneté'], ['baisses', 'Baisses']] as const
const STATUT_LABEL: Record<string, string> = {
  active: 'EN VENTE', en_vente_longue: 'EN VENTE LONGUE', a_reverifier: 'À REVÉRIFIER',
  retiree: 'RETIRÉE', vendue: 'VENDUE', retiree_sans_vente: 'RETIRÉE',
}
const ET_LABEL: Record<string, string> = { source: 'SOURCÉ', estime: 'ESTIMÉ', absent: 'ABSENT' }
const fmtEur = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('fr-FR') + ' €')
const fmtDate = (iso: string | null) => (iso ? new Intl.DateTimeFormat('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric', timeZone: 'Indian/Reunion' }).format(new Date(iso)) : '—')

// ancienneté en jours (publication si connue, sinon saisie) — le pied de carte de la maquette
function joursDepuis(iso: string | null): number | null {
  if (!iso) return null
  const d = new Date(iso).getTime()
  if (Number.isNaN(d)) return null
  return Math.max(0, Math.floor((Date.now() - d) / 86_400_000))
}

// specs d'un bien selon son type — le corps de la carte de la maquette (« 620 m² de terrain », etc.)
function specsBien(b: RadarBienClient): string {
  const p: string[] = []
  if (b.faits.pieces) p.push(`${b.faits.pieces} pièces`)
  if (b.faits.surface_hab) p.push(`${b.faits.surface_hab} m² hab`)
  if (b.faits.surface_terrain) p.push(`${b.faits.surface_terrain} m² de terrain`)
  if (!b.faits.surface_hab && !b.faits.surface_terrain && b.faits.dpe_classe) p.push(`DPE ${b.faits.dpe_classe}`)
  else if (p.length && b.faits.dpe_classe && !b.faits.surface_terrain) p.push(`DPE ${b.faits.dpe_classe}`)
  return p.join(' · ') || '—'
}

// ════════════ carte d'un bien dans le listing (structure verrouillée de la maquette) ════════════
function CarteBien({ b, sel, onClick }: { b: RadarBienClient; sel: boolean; onClick: () => void }) {
  const ratt = b.rattachement.idu != null
  const j = joursDepuis(b.date_publication || b.date_saisie)
  const meta = [b.faits.particulier_pro === 'pro' ? 'Pro' : b.faits.particulier_pro === 'particulier' ? 'Particulier' : b.portail,
    j != null ? `${j} j` : null].filter(Boolean).join(' · ')
  return (
    <button data-radar-bien={b.bien_id} onClick={onClick}
      className={`relative grid grid-cols-[minmax(0,1fr)_auto] gap-x-3 rounded-xl border px-4 py-3 text-left transition-colors duration-quick ${
        sel ? 'border-mint/40 bg-mint/[0.06]' : 'border-line-2 bg-surface-2 hover:border-line-3'}`}>
      {sel && <span aria-hidden className="absolute -left-px bottom-2.5 top-2.5 w-[3px] rounded bg-mint" />}
      <div className="self-center truncate font-mono text-[11px] tracking-[0.05em]">
        <span className="font-bold text-mint">{(b.type_bien ?? '—').toUpperCase()}</span>
        <span className="text-txt-mut"> · {b.commune}</span>
      </div>
      <div className="self-center whitespace-nowrap text-right text-[16.5px] font-bold tabular-nums text-txt-hi">{fmtEur(b.faits.prix)}</div>
      <div className="col-span-2 mt-1.5 text-[12.5px] leading-snug text-txt-mut">{specsBien(b)}</div>
      <div className="col-span-2 mt-2.5 flex items-center gap-2 overflow-hidden">
        {ratt ? (
          <span className="flex shrink-0 items-center gap-1.5 rounded-full bg-mint/12 px-2.5 py-1 text-[11px] text-mint">
            <span className="h-1.5 w-1.5 rounded-full bg-mint" />Sur la carte
          </span>
        ) : (
          <span className="shrink-0 rounded-full border border-dashed border-line-3 px-2.5 py-1 text-[11px] text-txt-mut">Non localisé — voir l'annonce ↗</span>
        )}
        {b.baisse && <span className="shrink-0 rounded-md bg-mint/12 px-2 py-0.5 font-mono text-[10.5px] text-mint">baisse</span>}
        {/* RADAR-DEPOT-2 D4 — badge « sous le marché » : écart affiché/référentiel de zone, avec la
            référence utilisée. Attribut de l'annonce, jamais un verdict de valeur. */}
        {b.sous_le_marche?.sous_le_marche && (
          // F9 (OUTILS-3) — l'écart porte TOUJOURS sa référence (perimetre + €/m² + millésime DVF), au
          // survol de la pastille compacte comme en clair dans le détail. Jamais un « −19 % » orphelin.
          <span title={`réf. ${b.sous_le_marche.perimetre ?? 'zone'} ${b.sous_le_marche.referentiel_eur_m2} €/m²${b.sous_le_marche.millesime_dvf ? ` · ${b.sous_le_marche.millesime_dvf}` : ''} · annonce vs DVF`}
            className="shrink-0 rounded-md bg-mint/15 px-2 py-0.5 font-mono text-[10.5px] font-medium text-mint">Sous le marché · −{Math.abs(b.sous_le_marche.ecart_pct ?? 0)} %</span>
        )}
        {b.statut === 'en_vente_longue' && <span className="shrink-0 rounded-md bg-amber/12 px-2 py-0.5 font-mono text-[10.5px] text-amber">Vente longue</span>}
        {/* RADAR-RECETTE-1 D1c — un bien incohérent est MARQUÉ dans le flux (hors stats/veilles, non rattaché). */}
        {b.a_qualifier && <span className="shrink-0 rounded-md bg-st-ecartee/15 px-2 py-0.5 font-mono text-[10.5px] text-st-ecartee">à qualifier</span>}
        <span className="ml-auto min-w-0 truncate text-right text-[11px] text-txt-dim">{meta}</span>
      </div>
    </button>
  )
}

// ════════════ tuile « Étudier ce bien » (T3, écran 2) ════════════
function Tuile({ label, onClick, children }: { label: string; onClick: () => void; children: React.ReactNode }) {
  return (
    <button data-radar-tuile={label} onClick={onClick}
      className="flex items-center gap-2 overflow-hidden rounded-lg border border-line-2 bg-surface-2 px-2.5 py-2 text-left text-[11.5px] text-txt transition-colors duration-quick hover:border-mint/40">
      <span className="shrink-0 text-mint">{children}</span>
      <span className="truncate">{label}</span>
    </button>
  )
}

// ════════════ la fiche d'un bien — overlay flottant sur la carte (maquette écran 2) ════════════
// T6 — desktop : overlay 398px à droite. mobile : plein écran (inset-0).
function RadarFiche({ bienId, onClose, mobile }: { bienId: number; onClose: () => void; mobile?: boolean }) {
  const { data: b, isError } = useQuery({ queryKey: ['radar-bien', bienId], queryFn: () => getRadarBienDetail(bienId) })
  const [signale, setSignale] = useState(false)
  const [interesse, setInteresse] = useState(false)
  const st = useApp.getState
  const cadre = mobile
    ? 'absolute inset-0 z-40 flex flex-col overflow-hidden border-line-2 bg-surface-1'
    : 'absolute bottom-3.5 right-3.5 top-3.5 z-30 flex w-[398px] flex-col overflow-hidden rounded-2xl border border-line-2 bg-surface-1 shadow-elev-3'
  if (isError) return (
    <div className={`${cadre} p-4 text-[12px] text-txt-mut`}>
      Fiche indisponible — le serveur n’a pas répondu. <button onClick={onClose} className="text-mint hover:underline">fermer</button>
    </div>
  )
  if (!b || !b.bien_id) return (
    <div className={`${cadre} p-4 text-[12px] text-txt-dim`}>Chargement…</div>
  )
  const ratt = b.rattachement.niveau !== 'absent' && b.rattachement.idu != null
  const idu = b.rattachement.idu

  // les FAITS, étiquetés (Sourcé/Estimé/Absent) — l'étiquette suit le champ (b.etiquettes)
  const faits: [string, string, string | null][] = [
    ['Surface terrain', b.faits.surface_terrain ? `${b.faits.surface_terrain} m²` : '—', b.etiquettes.surface_terrain ?? null],
    ['Surface habitable', b.faits.surface_hab ? `${b.faits.surface_hab} m²` : '—', b.etiquettes.surface_hab ?? null],
    ['Pièces', b.faits.pieces?.toString() ?? '—', b.etiquettes.pieces ?? null],
    ['DPE', b.faits.dpe_classe ?? '—', b.etiquettes.dpe_classe ?? null],
    ['Vendeur', b.faits.particulier_pro ? (b.faits.particulier_pro === 'pro' ? 'Professionnel' : 'Particulier') : '—', b.etiquettes.particulier_pro ?? null],
    ['Parution', fmtDate(b.date_publication), b.date_publication ? 'source' : 'absent'],
  ]

  // mention de baisse + prix de parution (1er ancien connu) — sans invention
  const prixParution = b.historique_prix.length ? b.historique_prix[0].ancien : null
  const derniereBaisse = [...b.historique_prix].reverse().find((h) => (h.nouveau ?? 0) < (h.ancien ?? 0))
  // sparkline des prix (si ≥ 2 points) — polyline simple, jamais une fausse précision
  const spark = (() => {
    const pts = b.historique_prix.flatMap((h) => [h.ancien, h.nouveau]).filter((v): v is number => v != null)
    if (pts.length < 2) return null
    const min = Math.min(...pts), max = Math.max(...pts), span = max - min || 1
    const coords = pts.map((v, i) => `${4 + (i / (pts.length - 1)) * 104},${31 - ((v - min) / span) * 26}`).join(' ')
    return coords
  })()

  const ouvrirPortail = () => { radarClic(b.bien_id, b.annonce_id).catch(() => {}); window.open(b.url_sortante, '_blank', 'noopener,noreferrer') }
  // les 6 tuiles → l'outil réel, pré-rempli avec la parcelle rattachée (mappings vérifiés, cf. rapport)
  const outil = (fn: () => void) => { if (idu) fn() }
  const tuiles = idu ? [
    { label: 'Étudier le bien', ico: <IcoEtude />, go: () => { const s = st(); s.setCalcPrefill(idu); s.setModule('scoreur-adresse') } },
    { label: 'Remonter le temps', ico: <IcoTemps />, go: () => { const s = st(); if (b.coords) s.setFlyTo({ center: b.coords as [number, number], zoom: 16 }); s.setParcelPrefill(idu); s.setModule('temps') } },
    { label: 'Calculette foncière', ico: <IcoCalc />, go: () => { const s = st(); s.setCalcPrefill(idu); s.setModule('calculette-fonciere') } },
    { label: 'Taxe d\'aménagement', ico: <IcoTaxe />, go: () => { const s = st(); s.select(idu); s.setModule('taxe-amenagement') } },
    { label: 'Pièges & risques', ico: <IcoRisque />, go: () => { const s = st(); s.select(idu); s.setModule('risques') } },
    { label: 'Solaire', ico: <IcoSoleil />, go: () => { const s = st(); s.setSolairePrefill(idu); s.setModule('prospection-solaire') } },
  ] : []

  return (
    <div data-radar-fiche className={cadre}>
      <div className="shrink-0 border-b border-line-2 px-4 py-3">
        <div className="flex items-center justify-between font-mono text-[10.5px] tracking-[0.2em] text-txt-mut">
          <span>RADAR › BIEN</span>
          <button onClick={onClose} aria-label="Fermer" className="tracking-normal text-txt-dim hover:text-txt">✕</button>
        </div>
        <h4 className="mt-1.5 flex items-center gap-2 text-[17px] font-semibold text-txt-hi">
          <span className="truncate">{(b.type_bien ?? 'Bien')[0].toUpperCase()}{(b.type_bien ?? '').slice(1)} · {b.commune}</span>
          <span className="shrink-0 rounded-md bg-mint/12 px-2 py-0.5 font-mono text-[10px] tracking-wide text-mint">{STATUT_LABEL[b.statut] ?? b.statut}</span>
        </h4>
      </div>
      <div className="flex min-h-0 flex-1 flex-col gap-3.5 overflow-y-auto px-4 py-3.5">
        {/* 2. prix + baisse + sparkline */}
        <div className="grid grid-cols-[1fr_auto] items-end gap-x-3">
          <div className="text-[25px] font-bold tabular-nums text-txt-hi">{fmtEur(b.faits.prix)}
            {b.baisse && derniereBaisse && (
              <span className="mt-1 block text-[11.5px] font-normal leading-snug text-txt-mut">
                Baisse du {fmtDate(derniereBaisse.date)}{prixParution ? ` — affiché ${fmtEur(prixParution)} à la parution` : ''}
              </span>
            )}
          </div>
          {spark && (
            <svg viewBox="0 0 112 36" className="h-9 w-28"><polyline points={spark} fill="none" stroke="#4ADE80" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
          )}
        </div>
        {/* RADAR-DEPOT-2 D4 — écart au marché : constaté entre deux sources datées (prix affiché vs
            référentiel DVF de zone), jamais une estimation de valeur. Le badge « sous le marché » n'est
            que le cas où l'écart passe le seuil ; la référence utilisée est toujours nommée. */}
        {b.sous_le_marche && b.sous_le_marche.calculable !== null && (
          <div data-radar-sous-marche className={`rounded-xl border px-3 py-2 text-[11.5px] leading-snug ${
            b.sous_le_marche.sous_le_marche ? 'border-mint/30 bg-mint/[0.05] text-mint' : 'border-line-2 bg-surface-2 text-txt-mut'}`}>
            {b.sous_le_marche.calculable ? (
              <>
                {/* R2c — formulation non ambiguë : signe explicite (« +104,4 % » / « 2,04× »), jamais « (104,4 %) ». */}
                <b>{b.sous_le_marche.affiche_eur_m2} €/m²</b> affiché · {b.sous_le_marche.sous_le_marche ? 'sous le marché' : b.sous_le_marche.sens} · <span className="font-medium">{b.sous_le_marche.ecart_libelle}</span>
                <div className="mt-0.5 text-[10.5px] text-txt-dim">réf. {b.sous_le_marche.perimetre} {b.sous_le_marche.referentiel_eur_m2} €/m²{b.sous_le_marche.millesime_dvf ? ` · ${b.sous_le_marche.millesime_dvf}` : ''} (n={b.sous_le_marche.n_referentiel}){b.sous_le_marche.meme_type_reference === false ? ' · référence mixte (à défaut du même type)' : ''}</div>
              </>
            ) : (
              /* R2b — biais terrain : valeur majoritairement foncière → le €/m² habitable est affiché,
                 mais AUCUN verdict « sous/au-dessus » (jamais un faux positif structurel). */
              <>
                <b>{b.sous_le_marche.affiche_eur_m2} €/m²</b> affiché · <span className="text-txt-mut">pas de comparaison</span>
                <div className="mt-0.5 text-[10.5px] text-txt-dim">{b.sous_le_marche.motif}</div>
              </>
            )}
          </div>
        )}
        {/* 3. Voir l'annonce — juste sous le prix, visible sans scroller */}
        <a onClick={(e) => { e.preventDefault(); ouvrirPortail() }} href={b.url_sortante} target="_blank" rel="noopener noreferrer"
          data-radar-portail className="flex items-center justify-center gap-2 rounded-xl bg-mint py-3 text-[13.5px] font-semibold text-mint-on hover:brightness-110">
          Voir l’annonce sur {b.portail} ↗
        </a>
        {/* RADAR-VEILLE-1 (R3) — annonce DÉPOSÉE par l'agence : contenu confié (adresse abonnés-seuls,
            texte, photos) AFFICHÉ, et le bouton « Intéressé » qui transmet les coordonnées à l'agence
            (LABUSE ne s'interpose pas). Rien de tout ceci n'existe pour le collecté. */}
        {b.depose_par_agence && (
          <div data-radar-depose className="rounded-xl border border-viz-cyan/30 bg-viz-cyan/[0.05] px-3 py-2.5">
            <div className="mb-1 font-mono text-[10px] tracking-[0.2em] text-viz-cyan">DÉPOSÉE PAR L’AGENCE{b.agence_nom ? ` · ${b.agence_nom}` : ''}</div>
            {b.adresse_exacte && <p className="text-[11.5px] text-txt"><span className="text-txt-mut">Adresse (abonnés)</span> · {b.adresse_exacte}</p>}
            {b.description && <p className="mt-1 text-[11px] leading-snug text-txt-mut">{b.description}</p>}
            {b.photos.length > 0 && <p className="mt-1 text-[10.5px] text-txt-dim">{b.photos.length} photo(s) confiée(s) par l’agence</p>}
            <button data-radar-interesse disabled={interesse} onClick={() => radarInteresse(b.bien_id).then(() => setInteresse(true)).catch(() => {})}
              className="mt-2 w-full rounded-lg bg-mint py-2 text-[12.5px] font-semibold text-mint-on hover:brightness-110 disabled:opacity-60">
              {interesse ? '✓ L’agence a vos coordonnées' : 'Intéressé — être mis en relation'}
            </button>
          </div>
        )}
        {/* RADAR-RECETTE-1 D1c — bien À QUALIFIER : champs contradictoires. Visible mais marqué, motifs
            consultables ; hors statistiques, hors veilles, jamais rattaché (surface suspecte). */}
        {b.a_qualifier && (
          <div data-radar-aqualifier className="rounded-xl border border-st-ecartee/40 bg-st-ecartee/[0.06] px-3 py-2.5">
            <div className="mb-1 font-mono text-[10px] tracking-[0.2em] text-st-ecartee">À QUALIFIER — INCOHÉRENCE</div>
            <p className="mb-1.5 text-[11px] leading-snug text-txt-mut">
              Les champs de cette annonce se contredisent. Elle est écartée des statistiques, des veilles
              et du rattachement tant qu’elle n’est pas vérifiée.
            </p>
            <ul className="list-disc pl-4 text-[11px] leading-snug text-txt">
              {b.a_qualifier_motifs.map((m, i) => <li key={i}>{m}</li>)}
            </ul>
          </div>
        )}
        {/* 4. LES FAITS */}
        <div>
          <div className="mb-1.5 font-mono text-[10px] tracking-[0.2em] text-txt-mut">LES FAITS</div>
          <div className="overflow-hidden rounded-xl border border-line-2">
            {faits.map(([k, v, et], i) => (
              <div key={k} className={`grid grid-cols-[1fr_auto_auto] items-center gap-x-2.5 px-3 py-2 text-[12.5px] ${i ? 'border-t border-line-2' : ''}`}>
                <span className="text-txt-mut">{k}</span>
                <span className="whitespace-nowrap tabular-nums text-txt">{v}</span>
                <span className={`rounded font-mono text-[9px] tracking-[0.06em] px-1.5 py-0.5 ${et === 'source' ? 'bg-mint/12 text-mint' : et === 'estime' ? 'bg-amber/12 text-amber' : 'bg-surface-3 text-txt-dim'}`}>{ET_LABEL[et ?? 'absent'] ?? 'ABSENT'}</span>
              </div>
            ))}
          </div>
        </div>
        {/* RADAR-DEPOT-2 D2 — FAITS DÉCLARÉS dans l'annonce (page d'annonce individuelle) : zone PLU,
            drapeaux. Déclaratif VENDEUR, pas du calibré LABUSE — étiqueté comme tel, jamais confondu
            avec les faits sourcés. Aucun texte d'annonce n'est affiché, seulement des faits. */}
        {b.declaratif && <Declaratif d={b.declaratif} />}
        {/* 5 + 6 : réservés aux biens RATTACHÉS (pas de parcelle → pas d'outils) */}
        {ratt && idu && (
          <>
            <div>
              <div className="mb-1.5 flex items-center gap-2 font-mono text-[10px] tracking-[0.2em] text-txt-mut">
                PARCELLE RATTACHÉE
                {b.rattachement_humain && <span className="rounded bg-mint/15 px-1.5 py-0.5 tracking-normal text-mint">tranché à la main</span>}
              </div>
              <div className="grid grid-cols-[1fr_auto] items-center gap-x-2.5 rounded-xl border border-mint/30 bg-mint/[0.05] px-3 py-2.5">
                <span className="font-mono text-[12.5px] text-mint">{idu}</span>
                <button data-radar-parcelle onClick={() => { const s = st(); if (b.coords) s.setFlyTo({ center: b.coords as [number, number], zoom: 17 }); s.setView('cartes'); s.select(idu) }}
                  className="whitespace-nowrap rounded-lg border border-line-2 px-2.5 py-1.5 text-[11.5px] text-txt-mut hover:text-txt">Ouvrir la fiche parcelle →</button>
              </div>
              {/* RATTACHEMENT-V2 — POURQUOI cette parcelle tient : les critères indépendants qui ont convergé. */}
              {b.rattachement_criteres && b.rattachement_criteres.length > 0 && (
                <ul className="mt-1.5 flex flex-col gap-0.5 text-[10.5px] leading-snug text-txt-dim">
                  {b.rattachement_criteres.map((c: RadarCritere, i: number) => (
                    <li key={i}>✓ <span className="text-txt-mut">{c.critere}</span> — {c.valeur}</li>
                  ))}
                </ul>
              )}
            </div>
            <div>
              <div className="mb-1.5 font-mono text-[10px] tracking-[0.2em] text-txt-mut">ÉTUDIER CE BIEN</div>
              <div className="grid grid-cols-2 gap-1.5">
                {tuiles.map((t) => <Tuile key={t.label} label={t.label} onClick={() => outil(t.go)}>{t.ico}</Tuile>)}
              </div>
            </div>
          </>
        )}
        {/* RADAR-DEPOT-2 D3 — le client ne rattache JAMAIS (un rattachement erroné serait servi à tous).
            Sur une piste, le bloc est SOBRE : ni bouton, ni compte de candidates. Le rattachement est un
            geste ADMIN (écran d'instruction). */}
        {!ratt && b.rattachement_etat === 'piste' && (
          <div className="rounded-xl border border-line-2 bg-surface-2 px-3 py-2.5">
            <div className="mb-1 font-mono text-[10px] tracking-[0.2em] text-txt-mut">POSITION AU QUARTIER</div>
            <p className="text-[11px] leading-snug text-txt-mut">
              Plusieurs parcelles peuvent correspondre — la position servie est le quartier. Seul le lien
              vers la source est disponible.
            </p>
          </div>
        )}
        {!ratt && b.rattachement_etat !== 'piste' && (
          <p className="text-[11px] leading-snug text-txt-dim">Bien non rattaché à une parcelle — la position servie est le quartier ; seul le lien vers la source est disponible.</p>
        )}
        {/* 7. Signaler + note de doctrine */}
        <div className="flex flex-col gap-2 pt-0.5">
          <button disabled={signale} onClick={() => radarSignaler(bienId, 'annonce retirée / erreur').then(() => setSignale(true))}
            className="text-center text-[11.5px] text-txt-mut underline decoration-dotted hover:text-txt disabled:opacity-60">
            {signale ? 'Signalé — merci, Victor va vérifier' : 'Signaler — annonce retirée ou erreur'}
          </button>
          <p className="text-center text-[10px] leading-relaxed text-txt-dim">{b.depose_par_agence
            ? 'Annonce déposée par l’agence — elle en confie l’affichage (photos, texte, adresse aux abonnés).'
            : 'Faits extraits de l’annonce publique. Aucune photo ni texte d’annonce n’est conservé ou affiché.'}</p>
        </div>
      </div>
    </div>
  )
}

// petites icônes des tuiles (trait mint, viewBox 24)
const IcoEtude = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M2 3h20v14H2z" /><path d="M8 21h8M12 17v4" /></svg>
const IcoTemps = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 3" /></svg>
const IcoCalc = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="4" y="2" width="16" height="20" rx="2" /><path d="M8 6h8M8 10h2M14 10h2M8 14h2M14 14h2" /></svg>
const IcoTaxe = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2 2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" /></svg>
const IcoRisque = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" /><path d="M12 9v4M12 17h.01" /></svg>
const IcoSoleil = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></svg>

// ════════════ LA CATÉGORIE — panneau (434px) + fiche overlay ════════════
export function RadarView() {
  const [f, setF] = useState<RadarFiltres>({})
  const [tri, setTri] = useState('recentes')
  const [bienOuvert, setBienOuvert] = useState<number | null>(null)
  const isMobile = useIsMobile()
  const [mobileVue, setMobileVue] = useState<'liste' | 'carte'>('liste')
  const setModuleMap = useApp((s) => s.setModuleMap)
  const setFlyTo = useApp((s) => s.setFlyTo)
  const radarToOpen = useApp((s) => s.radarToOpen)
  const setRadarToOpen = useApp((s) => s.setRadarToOpen)

  // SECTEUR-2b (U2) — le bouton « Publier une annonce » de l'en-tête ET le parcours 4 étapes vivent ICI,
  // dans l'écran Radar de l'app (plus dans la Tour de contrôle). Visibilité : ADMIN toujours (drapeau
  // fermé compris, avec la mention) ; CLIENTS seulement quand le DRAPEAU EST OUVERT (état public /ouvert).
  const moi = useQuery({ queryKey: ['moi'], queryFn: getMoi, staleTime: 3_600_000 })
  const estAdmin = moi.data == null || moi.data.mode !== 'compte' || moi.data.role === 'admin'
  const depotOuvert = useQuery({ queryKey: ['radar-depot-ouvert'], queryFn: getRadarDepotOuvert })
  const ouvert = depotOuvert.data?.ouvert === true
  const boutonVisible = estAdmin || ouvert            // client : seulement drapeau ouvert
  const drapeauFerme = estAdmin && !ouvert            // mention « invisible des clients » (admin, drapeau fermé)
  const [depotPanneau, setDepotPanneau] = useState(false)
  // RETOURS-3 R13 — la barre de filtres passe sur DEUX étages : une ligne visible (recherche · commune ·
  // type · bouton « Filtrer » compteur) + un TIROIR pour le reste, avec des pastilles d'actifs retirables.
  const [drawerOpen, setDrawerOpen] = useState(false)

  const { data, isLoading } = useQuery({ queryKey: ['radar-biens', f, tri], queryFn: () => getRadarBiens(f, tri) })
  const biens = useMemo(() => data?.biens ?? [], [data])

  // carte = rattachés SEULEMENT → pins (kind='radar', couleur par statut) poussés sur la carte existante
  useEffect(() => {
    const feats = biens.filter((b) => b.coords).map((b) => ({
      type: 'Feature', geometry: { type: 'Point', coordinates: b.coords },
      properties: { kind: 'radar', bien_id: b.bien_id, idu: b.rattachement.idu, statut: b.statut },
    }))
    setModuleMap({ idus: biens.filter((b) => b.rattachement.idu).map((b) => b.rattachement.idu as string),
      extra: { type: 'FeatureCollection', features: feats } })
    return () => setModuleMap({ idus: [], extra: null })
  }, [biens, setModuleMap])

  // clic sur un pin de la carte → ouvre la fiche du bien (idiome consommé-puis-reset)
  useEffect(() => {
    if (radarToOpen != null) { setBienOuvert(radarToOpen); setRadarToOpen(null) }
  }, [radarToOpen, setRadarToOpen])

  // Clic d'une carte du listing → sa FICHE (T3). Rattaché : la carte vole à la parcelle + fiche
  // complète. Non localisé : fiche qui s'arrête aux faits, avec le bouton portail (le seul chemin
  // sortant, logué) — T2 « non localisé → portail » est honoré par ce bouton, pas de carte.
  const ouvrir = (b: RadarBienClient) => {
    if (b.rattachement.idu && b.coords) setFlyTo({ center: b.coords as [number, number], zoom: 17 })
    ouvrirBien(b.bien_id)
  }
  const setNum = (k: keyof RadarFiltres, v: string) => setF((p) => ({ ...p, [k]: v === '' ? undefined : Number(v) }))

  const nTotal = data?.n_total ?? 0
  const nRatt = data?.n_rattaches ?? 0
  const aucunFiltre = !f.commune && !f.type_bien && f.prix_min == null && f.prix_max == null && f.surface_terrain_min == null && !f.rattache && !f.particulier_pro && !f.sous_marche

  const selInput = 'h-[35px] rounded-lg border border-line-2 bg-surface-1 px-2.5 text-[12.5px] text-txt focus:border-mint focus:outline-none'

  // RETOURS-3 R13 — les filtres du TIROIR (hors commune/type restés visibles) : pastilles + compteur du bouton.
  const actifs: { key: keyof RadarFiltres; label: string }[] = []
  if (f.prix_min != null) actifs.push({ key: 'prix_min', label: `Prix ≥ ${f.prix_min.toLocaleString('fr-FR')} €` })
  if (f.prix_max != null) actifs.push({ key: 'prix_max', label: `Prix ≤ ${f.prix_max.toLocaleString('fr-FR')} €` })
  if (f.surface_terrain_min != null) actifs.push({ key: 'surface_terrain_min', label: `Surface ≥ ${f.surface_terrain_min} m²` })
  if (f.rattache) actifs.push({ key: 'rattache', label: 'Rattachés' })
  if (f.particulier_pro) actifs.push({ key: 'particulier_pro', label: f.particulier_pro === 'pro' ? 'Pro' : 'Particulier' })
  if (f.sous_marche) actifs.push({ key: 'sous_marche', label: 'Sous le marché' })
  const nActifs = actifs.length
  const retirer = (k: keyof RadarFiltres) => setF((p) => { const n = { ...p }; delete n[k]; return n })
  // « Tout effacer » du tiroir : n'efface QUE les filtres du tiroir (commune/type restent dans la barre visible).
  const effacerFiltres = () => setF((p) => ({ commune: p.commune, type_bien: p.type_bien }))

  // T6 — ouvrir un bien sur mobile : la fiche prend le plein écran (on repart en vue liste dessous).
  const ouvrirBien = (id: number | null) => { setBienOuvert(id); if (isMobile) setMobileVue('liste') }
  const carteVisible = !isMobile || mobileVue === 'carte'

  return (
    <>
      <aside data-radar-panel className={`flex-col border-r border-line bg-surface-1 md:flex md:w-[434px] md:shrink-0 ${isMobile && mobileVue === 'carte' ? 'hidden' : 'flex w-full'}`}>
        {/* en-tête (wording maquette) */}
        <div className="shrink-0 border-b border-line-2 px-5 pb-4 pt-5">
          <div className="flex items-start justify-between gap-2">
            <div className="font-mono text-[10.5px] tracking-[0.2em] text-txt-mut">RADAR</div>
            {/* SECTEUR-2b (U2) — « Publier une annonce » : le bouton ET le parcours vivent ICI (écran Radar
                de l'app). Admin toujours ; clients seulement drapeau ouvert. Le clic déroule les 4 étapes
                DANS l'app (plus de saut vers la Tour de contrôle). */}
            {boutonVisible && (
              <button data-radar-publier onClick={() => setDepotPanneau((v) => !v)}
                className="shrink-0 rounded-md border border-mint/40 bg-mint/10 px-2.5 py-1 text-[11.5px] font-medium text-mint transition-colors hover:bg-mint/20"
                title={estAdmin ? "Déposer une page d'annonces" : 'Publier votre annonce'}>
                {depotPanneau ? '× Fermer le dépôt' : '+ Publier une annonce'}
              </button>
            )}
          </div>
          <h3 className="mt-1.5 text-[20px] font-semibold text-txt-hi">Les biens en vente</h3>
          <p className="mt-1.5 text-[12.5px] leading-snug text-txt-mut">Repérés sur les portails, rattachés à leur parcelle. Des faits et un lien — jamais le contenu de l’annonce.</p>
          {drapeauFerme && (
            <span data-radar-publier-drapeau className="mt-2 inline-block rounded bg-amber/12 px-1.5 py-0.5 text-[10px] font-medium text-amber">
              drapeau fermé — le dépôt reste invisible des clients
            </span>
          )}
          {/* le parcours 4 étapes, déroulé dans l'app sous l'en-tête */}
          {boutonVisible && depotPanneau && (
            <div className="mt-3"><DepotAgence drapeauFerme={drapeauFerme} onClose={() => setDepotPanneau(false)} /></div>
          )}
        </div>

        {/* RETOURS-3 R13 — barre VISIBLE, une seule ligne : recherche (composant commun) · commune · type ·
            bouton « Filtrer » portant le nombre de filtres actifs du tiroir. */}
        <div className="grid shrink-0 gap-2 border-b border-line-2 px-5 py-3.5">
          <div className="flex flex-wrap items-center gap-2">
            {/* recherche adresse/commune/IDU — positionne la carte sur l'adresse choisie (BAN + IDU) */}
            <AddressAutocomplete placeholder="Adresse, commune, IDU…"
              className="h-[35px] w-full min-w-0 flex-1 rounded-lg border border-line-2 bg-surface-1 px-2.5 text-[12.5px] text-txt placeholder:text-txt-dim focus:border-mint focus:outline-none"
              onSelect={(sel) => { if (sel.lon != null && sel.lat != null) setFlyTo({ center: [sel.lon, sel.lat], zoom: 15 }) }} />
            <select data-radar-commune value={f.commune ?? ''} onChange={(e) => setF((p) => ({ ...p, commune: e.target.value || undefined }))} className={selInput}>
              <option value="">Toute l’île</option>
              {COMMUNES_24.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
            <select value={f.type_bien ?? ''} onChange={(e) => setF((p) => ({ ...p, type_bien: e.target.value || undefined }))} className={selInput}>
              {TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
            <button data-radar-filtrer onClick={() => setDrawerOpen((o) => !o)}
              className={`flex h-[35px] shrink-0 items-center gap-1.5 rounded-lg border px-3 text-[12.5px] transition-colors duration-quick ${drawerOpen ? 'border-mint text-mint' : 'border-line-2 text-txt hover:border-mint/50'}`}>
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.1" strokeLinecap="round"><path d="M3.5 6h17M6.5 12h11M10 18h4" /></svg>
              Filtrer{nActifs > 0 && <span className="inline-flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-mint px-1 text-[10.5px] font-bold text-mint-on">{nActifs}</span>}
            </button>
          </div>

          {/* pastilles de filtres actifs (tiroir), chacune retirable + « tout effacer » */}
          {nActifs > 0 && (
            <div data-radar-actifs className="flex flex-wrap items-center gap-1.5">
              {actifs.map((a) => (
                <button key={a.key} onClick={() => retirer(a.key)}
                  className="inline-flex items-center gap-1.5 rounded-full border border-mint/40 bg-mint/[0.10] px-2.5 py-0.5 text-[11.5px] text-mint transition-colors duration-quick hover:bg-mint/20">
                  {a.label}<span className="text-mint/70">✕</span></button>
              ))}
              <button onClick={effacerFiltres} className="ml-0.5 text-[11.5px] text-txt-dim underline hover:text-txt">tout effacer</button>
            </div>
          )}

          {/* le TIROIR « Filtrer » : le reste des filtres, groupés par intitulé. R13.5 — le segment
              Tous/Rattachés RESTE (ce n'est PAS le filtre « non rattaché » retiré le 28/08 : il n'offre
              aucune option « non rattachés seuls », seulement Tous vs Rattachés). */}
          {drawerOpen && (
            <div data-radar-drawer className="mt-1 flex flex-col gap-3 rounded-xl border border-line-2 bg-surface-2 p-3">
              <div>
                <div className="mb-1.5 text-[11px] text-txt-mut">Prix et surface</div>
                <div className="grid grid-cols-3 gap-2">
                  <input type="number" min={0} placeholder="Prix min" value={f.prix_min ?? ''} onChange={(e) => setNum('prix_min', e.target.value)} className={`min-w-0 ${selInput}`} />
                  <input type="number" min={0} placeholder="Prix max" value={f.prix_max ?? ''} onChange={(e) => setNum('prix_max', e.target.value)} className={`min-w-0 ${selInput}`} />
                  <input type="number" min={0} placeholder="Surface min" value={f.surface_terrain_min ?? ''} onChange={(e) => setNum('surface_terrain_min', e.target.value)} className={`min-w-0 ${selInput}`} />
                </div>
              </div>
              <div>
                <div className="mb-1.5 text-[11px] text-txt-mut">Rattachement à la parcelle</div>
                <Segment value={f.rattache ?? ''} onChange={(v) => setF((p) => ({ ...p, rattache: (v || undefined) as RadarFiltres['rattache'] }))}
                  options={[['', 'Tous'], ['oui', 'Rattachés']]} data="radar-seg-ratt" />
              </div>
              <div>
                <div className="mb-1.5 text-[11px] text-txt-mut">Vendeur</div>
                <Segment value={f.particulier_pro ?? ''} onChange={(v) => setF((p) => ({ ...p, particulier_pro: (v || undefined) as RadarFiltres['particulier_pro'] }))}
                  options={[['', 'Tous'], ['particulier', 'Particulier'], ['pro', 'Pro']]} data="radar-seg-pp" />
              </div>
              <div>
                <div className="mb-1.5 text-[11px] text-txt-mut">Prix face au marché</div>
                {/* RADAR-DEPOT-2 D4 — attribut de l'annonce, pas un canal. */}
                <Segment value={f.sous_marche ?? ''} onChange={(v) => setF((p) => ({ ...p, sous_marche: (v || undefined) as RadarFiltres['sous_marche'] }))}
                  options={[['', 'Tous les prix'], ['oui', 'Sous le marché']]} data="radar-seg-sm" />
              </div>
              <div className="flex justify-end gap-2 border-t border-line-2 pt-2.5">
                <button onClick={effacerFiltres} className="rounded-lg border border-line-2 px-3 py-1.5 text-[12px] text-txt-mut hover:text-txt">Tout effacer</button>
                <button onClick={() => setDrawerOpen(false)} className="rounded-lg bg-mint px-3.5 py-1.5 text-[12px] font-semibold text-mint-on hover:brightness-110">Voir les biens</button>
              </div>
            </div>
          )}
        </div>

        {/* compteur + tri */}
        <div className="flex shrink-0 items-center justify-between border-b border-line-2 px-5 py-3">
          <div className="text-[12.5px] text-txt-mut"><b className="text-[14px] font-semibold text-txt-hi">{nTotal}</b> bien{nTotal > 1 ? 's' : ''} · <span className="text-mint">{nRatt} sur la carte</span></div>
          {/* RV2-V4 — le sélecteur de tri avait un fond BLANC (hors DA, pas de bg-surface) : aligné sur
              les autres contrôles de l'écran (fond sombre, bordure, texte). */}
          <select value={tri} onChange={(e) => setTri(e.target.value)}
            className="rounded-lg border border-line-2 bg-surface-1 px-2.5 py-1.5 text-[12px] text-txt focus:border-mint focus:outline-none">
            {TRIS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>

        {/* listing OU état vide */}
        <div className="flex min-h-0 flex-1 flex-col gap-2.5 overflow-y-auto px-3.5 py-3">
          {isLoading && <div className="py-6 text-center text-[12px] text-txt-dim">Chargement…</div>}
          {!isLoading && biens.length === 0 && aucunFiltre && (
            <div className="flex flex-1 flex-col items-center justify-center gap-3 px-6 py-8 text-center">
              <span className="grid h-[74px] w-[74px] place-items-center rounded-full border border-mint/30 bg-mint/[0.08] text-mint">
                <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="4.5" /><circle cx="12" cy="12" r="1" fill="currentColor" /><path d="M12 3v3M21 12h-3" /></svg>
              </span>
              <h5 className="text-[15.5px] font-semibold text-txt-hi">Le Radar démarre</h5>
              <p className="max-w-[34ch] text-[12.5px] leading-relaxed text-txt-mut">Les biens en vente arrivent au fil de la collecte, chaque jour. Le premier digest part dès qu’il y a du neuf à montrer.</p>
            </div>
          )}
          {!isLoading && biens.length === 0 && !aucunFiltre && (
            <div className="rounded-xl border border-dashed border-line-2 py-8 text-center text-[12px] text-txt-mut">Aucun bien ne correspond à ces filtres.<br />Élargissez la recherche.</div>
          )}
          {biens.map((b) => <CarteBien key={b.bien_id} b={b} sel={bienOuvert === b.bien_id} onClick={() => ouvrir(b)} />)}
        </div>
      </aside>

      {/* CARTE — desktop toujours ; mobile seulement en vue carte (montée/démontée pour éviter un
          canvas maplibre 0×0). Les pins radar sont repoussés par l'effet au remontage. */}
      {carteVisible && (
        <div className="relative flex min-w-0 flex-1">
          <Suspense fallback={<div className="flex-1 bg-bg" />}><MapView /></Suspense>
        </div>
      )}

      {/* T6 — bascule mobile listing ↔ carte (patron tiroir P3). Masquée quand une fiche est ouverte. */}
      {isMobile && bienOuvert == null && (
        <button data-radar-mobile-bascule onClick={() => setMobileVue((v) => (v === 'liste' ? 'carte' : 'liste'))}
          className="fixed bottom-5 left-1/2 z-40 -translate-x-1/2 rounded-full bg-mint px-5 py-2.5 text-[12.5px] font-semibold text-mint-on shadow-elev-3">
          {mobileVue === 'liste' ? 'Voir la carte' : 'Voir la liste'}
        </button>
      )}

      {bienOuvert != null && <RadarFiche bienId={bienOuvert} onClose={() => ouvrirBien(null)} mobile={isMobile} />}
    </>
  )
}

// segment (Tous / Rattachés · Tous / Particulier / Pro) — bascule mint, gabarit maquette
function Segment({ value, onChange, options, data }: { value: string; onChange: (v: string) => void; options: readonly (readonly [string, string])[]; data: string }) {
  return (
    <div data-seg={data} className="grid h-[35px] overflow-hidden rounded-lg border border-line-2" style={{ gridAutoFlow: 'column', gridAutoColumns: '1fr' }}>
      {options.map(([v, l], i) => (
        <button key={v || 'tous'} onClick={() => onChange(v)}
          className={`flex items-center justify-center whitespace-nowrap px-1.5 text-[12px] ${i ? 'border-l border-line-2' : ''} ${value === v ? 'bg-mint/12 font-medium text-mint' : 'text-txt-mut hover:text-txt'}`}>{l}</button>
      ))}
    </div>
  )
}
