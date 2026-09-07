import { useQuery } from '@tanstack/react-query'
import { useState, type ReactNode } from 'react'
import { BPE_DOM, CINQUANTE_PAS_COLOR, EQUIP_META, LEGEND_ORDER, LEGEND_V2_ORDER, STATUT_META, TIER_V2_META, ZONE_FAM_META, ZONE_FAM_ORDER } from '../../lib/status'
import { PERMIS_LEGENDE } from '../../lib/permisEtats'
import { MAP_THEME } from '../../lib/mapTheme'
import { getMapLayer } from '../../lib/api'
import { TOKENS } from '../../lib/tokens'
import { useApp } from '../../store/useApp'
import { Tip } from '../Tip'
import { ChevronSection } from '../panel/ChevronSection'

// Correctif M5 : quand un run scoring v2 existe, la carte colore par le tier v2 — la légende suit.
export function useV2Actif(): boolean {
  const q = useQuery({
    queryKey: ['v2-actif'],
    queryFn: async () => (await fetch('/v2/modele')).ok,
    retry: false, staleTime: Infinity,
  })
  return q.data === true
}

// SECTEUR-1 (S4) — état repli/déplié + groupes ouverts MÉMORISÉS (localStorage).
const LEG_LS = 'labuse.legende'
function readLeg(): { open: boolean; groupes: Record<string, boolean> } {
  try { return { open: false, groupes: {}, ...JSON.parse(localStorage.getItem(LEG_LS) || '{}') } }
  catch { return { open: false, groupes: {} } }
}
function writeLeg(v: { open: boolean; groupes: Record<string, boolean> }) {
  try { localStorage.setItem(LEG_LS, JSON.stringify(v)) } catch { /* indisponible : la légende reste fonctionnelle */ }
}

/** SECTEUR-1 (S4) — chaque groupe de la légende est un accordéon. La note de SOURCE passe dans le « i »
 *  du groupe (« DEAL Réunion… »), jamais dans le corps de la légende. */
function Groupe({ titre, note, open, onToggle, children }: {
  titre: ReactNode; note?: string; open: boolean; onToggle: () => void; children: ReactNode
}) {
  return (
    <div data-legend-groupe className="border-t border-line py-1.5 first:border-t-0 first:pt-0">
      <button onClick={onToggle} aria-expanded={open}
        className="flex w-full items-center gap-1.5 text-left" title={open ? 'Replier' : 'Déplier'}>
        <span className="label-caps flex-1">{titre}</span>
        {note && (
          <Tip side="top" tip={note}>
            <span role="button" tabIndex={0} aria-label="Source"
              className="flex h-[13px] w-[13px] items-center justify-center rounded-full border border-line-2 text-[8px] font-bold text-txt-dim hover:border-mint hover:text-mint">i</span>
          </Tip>
        )}
        <ChevronSection open={open} />
      </button>
      {open && <div className="mt-1.5">{children}</div>}
    </div>
  )
}

/** `inline` : rendu dans le tiroir mobile « Couches » au lieu du coin de carte. */
export function Legend({ inline = false }: { inline?: boolean }) {
  const layers = useApp((s) => s.layers)
  const verdict = useApp((s) => s.verdict)
  const analyse = useApp((s) => s.filters.analyseLabuse)
  const peint = useApp((s) => s.mapPeint)
  const commune = useApp((s) => s.commune)
  const basemap = useApp((s) => s.basemap)
  const bpeDomains = useApp((s) => s.bpeDomains)
  const toggleBpeDomain = useApp((s) => s.toggleBpeDomain)
  const v2 = useV2Actif()
  const aleaActifHook = layers.alea_inondation || layers.alea_mvt
  const aleaQ = useQuery({ queryKey: ['layer', 'georisque_alea', commune], queryFn: () => getMapLayer('georisque_alea'), enabled: aleaActifHook })
  const transQ = useQuery({ queryKey: ['layer', 'transport_ligne'], queryFn: () => getMapLayer('transport_ligne'), enabled: layers.transport })
  const polesQ = useQuery({ queryKey: ['layer', 'pole_echange'], queryFn: () => getMapLayer('pole_echange'), enabled: layers.axes })
  const critereDerive = (polesQ.data?.features.find((f) => (f.properties as { subtype?: string; critere?: string }).critere)
    ?.properties as { critere?: string } | undefined)?.critere ?? 'arrêt desservi par de nombreuses lignes (dérivé GTFS)'
  const htQ = useQuery({ queryKey: ['layer', 'ligne_ht'], queryFn: () => getMapLayer('ligne_ht'), enabled: layers.lignes_ht })
  const qpvQ = useQuery({ queryKey: ['layer', 'qpv', commune], queryFn: () => getMapLayer('qpv'), enabled: layers.qpv })
  const anruQ = useQuery({ queryKey: ['layer', 'anru', commune], queryFn: () => getMapLayer('anru'), enabled: layers.anru })
  const tTheme = MAP_THEME[basemap === 'clair' ? 'clair' : 'sombre']
  const mill = (q: { data?: unknown }) => (q.data as { millesime_integration?: string } | undefined)?.millesime_integration
  const srcMill = (q: { data?: unknown }) => (q.data as { source_millesime?: string } | undefined)?.source_millesime
  const dISO = (m?: string) => (m ? m.split('-').reverse().join('/') : '')
  const fmtFraich = (q: { data?: unknown }) => {
    const sm = srcMill(q); const ing = mill(q)
    if (sm) return ` · millésime ${sm}${ing ? ` (ingéré le ${dISO(ing)})` : ''}`
    return ing ? ` · ingéré le ${dISO(ing)}` : ''
  }
  const [leg, setLeg] = useState(readLeg)
  const set = (v: typeof leg) => { setLeg(v); writeLeg(v) }

  const opinion = (verdict && analyse) || layers.couleurs_verdict
  const verdictPeint = opinion && peint.parcelles && !peint.zonage
  const zonagePeint = peint.zonage
  const equipPeint = peint.equipements
  const dispoActif = layers.qpv || layers.tva_primo || layers.anru || layers.zfang || layers.frr
  // SOURCES-1 lot 1 — contraintes du droit des sols (ER / EBC / DPU / PEB / SUP)
  const contraintesActif = layers.er || layers.ebc || layers.dpu || layers.peb || layers.sup || layers.bruit_route || layers.bruit_carte

  // SECTEUR-1 (S4) — les GROUPES actifs, dans l'ordre. Seuls ceux des couches actives apparaissent.
  const groupes: { id: string; titre: ReactNode; note?: string; body: ReactNode }[] = []
  // RETOURS-17 W3 — l'outil Permis peint des points colorés PAR ÉTAT : la légende dit les trois couleurs
  // (Récent vert · Dormant corail · Achevé/Autre gris), MÊME source que les pastilles du panneau.
  const moduleActif = useApp((s) => s.module)
  if (moduleActif === 'permis' || moduleActif === 'promesses') groupes.push({
    id: 'permis', titre: 'Permis (par état)',
    note: 'Achevé et Autre partagent le même gris ; le panneau les distingue par leur compte.',
    body: <div className="flex flex-col gap-1.5">{PERMIS_LEGENDE.map((e) => (
      <div key={e.key} data-legend-permis={e.key} className="flex items-center gap-2">
        <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: e.color }} />
        <span className="text-[11px] text-txt">{e.label}</span>
      </div>
    ))}</div>,
  })
  if (verdictPeint) groupes.push({
    id: 'verdict',
    titre: v2 ? 'Verdict · Classement servi' : 'Verdict · Classement historique',
    note: v2 ? 'Couleurs du classement servi (tiers Priorité → Écartée).' : 'Classement historique (repli) — le classement servi n\'est pas joignable sur cette vue.',
    body: (
      <div className="flex flex-col gap-1.5">
        {(v2 ? LEGEND_V2_ORDER : LEGEND_ORDER).map((t) => (
          <div key={t} className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full" style={{ background: v2 ? TIER_V2_META[t as keyof typeof TIER_V2_META].color : STATUT_META[t as keyof typeof STATUT_META].color }} />
            <span className="text-[11px] text-txt">{v2 ? TIER_V2_META[t as keyof typeof TIER_V2_META].label : STATUT_META[t as keyof typeof STATUT_META].label}</span>
          </div>
        ))}
      </div>
    ),
  })
  if (zonagePeint) groupes.push({
    id: 'zonage', titre: 'Zonage PLU (par type)',
    body: <div className="flex flex-col gap-1.5">{ZONE_FAM_ORDER.map((f) => (
      <div key={f} className="flex items-center gap-2"><span className="h-2 w-2 rounded-full" style={{ background: ZONE_FAM_META[f].color }} /><span className="text-[11px] text-txt">{ZONE_FAM_META[f].label}</span></div>
    ))}</div>,
  })
  // RETOURS-11 C5 (03/09) — la couche officielle brute du GPU (premier niveau) a SA légende.
  if (layers.zonage) groupes.push({
    id: 'zonage-gpu', titre: 'Limites officielles PLU (GPU brut)',
    note: 'Polygones bruts du document opposable (Géoportail de l’urbanisme), non rattachés au cadastre.',
    body: <div data-legend-zonage-gpu className="flex items-center gap-2"><span className="h-3 w-4 rounded-sm border" style={{ borderColor: '#5CE6A1', background: 'rgba(92,230,161,.12)' }} /><span className="text-[11px] text-txt">contour + aplat des zones du PLU officiel</span></div>,
  })
  if (layers.cinquante_pas) groupes.push({
    id: '50pas', titre: '50 pas géométriques',
    note: 'Réserve des 50 pas géométriques — bande de 81,20 m depuis le rivage (spécifique outre-mer).',
    body: <div data-legend-50pas className="flex items-center gap-2"><span className="h-0.5 w-4 rounded" style={{ background: CINQUANTE_PAS_COLOR }} /><span className="text-[11px] text-txt">50 pas géométriques</span></div>,
  })
  if (layers.znieff) groupes.push({
    id: 'znieff', titre: 'ZNIEFF — type I & II',
    note: 'Inventaire du patrimoine naturel (INPN/MNHN, 2025). Type I : secteur à fort intérêt, plus sensible ; type II : grand ensemble naturel. Contrainte (étude d\'impact, risque de recours), pas une interdiction. N\'entre pas dans le classement.',
    body: <div data-legend-znieff className="flex items-center gap-2"><span className="h-2.5 w-4 rounded-sm border" style={{ background: tTheme.znieff, opacity: tTheme.znieffOpacity + 0.35, borderColor: tTheme.znieff }} /><span className="text-[11px] text-txt">ZNIEFF — type I &amp; type II</span></div>,
  })
  if (layers.equipements_bpe) groupes.push({
    id: 'bpe', titre: 'Équipements (INSEE BPE)',
    note: 'Base Permanente des Équipements (INSEE, 2025), par domaine. Source distincte d\'OpenStreetMap — jamais fusionnée. Cliquez un domaine pour l\'afficher ou le masquer.',
    body: <div data-legend-bpe className="grid grid-cols-2 gap-x-2 gap-y-0.5">{BPE_DOM.map((d) => {
      const on = bpeDomains.includes(d.code)
      return (
        <button key={d.code} data-legend-bpe-dom={d.code} onClick={() => toggleBpeDomain(d.code)}
          className={`flex items-center gap-1.5 rounded px-1 py-0.5 text-left transition-opacity duration-quick ${on ? '' : 'opacity-35'}`}
          title={on ? 'Masquer ce domaine' : 'Afficher ce domaine'}>
          <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: d.color }} /><span className="truncate text-[10.5px] text-txt">{d.label}</span>
        </button>
      )
    })}</div>,
  })
  ;(['alea_inondation', 'alea_mvt'] as const).forEach((k) => { if (layers[k]) groupes.push({
    id: k, titre: k === 'alea_inondation' ? 'Aléa inondation' : 'Aléa mouvement de terrain',
    note: `DEAL Réunion — cartographie des aléas (exposition au phénomène, pas la règle du PPR)${fmtFraich(aleaQ)}`,
    /* RETOURS-13 R6 — la légende suit les CLASSES RÉELLEMENT SERVIES par le flux (dérivées des
       données à l'écran, jamais promises d'avance) : inondation faible/moyen/fort ; mouvement de
       terrain faible/moyen/élevé/très élevé — la classe LA PLUS GRAVE est ROUGE. */
    body: (() => {
      const sub = k === 'alea_inondation' ? 'inondation' : 'mouvement_terrain'
      const ramp = (k === 'alea_inondation' ? tTheme.aleaInondationRamp : tTheme.aleaMvtRamp) as unknown as Record<string, string>
      const ORDRE = ['faible', 'moyen', 'fort', 'eleve', 'tres_eleve'] as const
      const LAB: Record<string, string> = { faible: 'faible', moyen: 'moyen', fort: 'fort', eleve: 'élevé', tres_eleve: 'très élevé' }
      const servies = new Set((aleaQ.data?.features ?? [])
        .filter((f) => (f.properties as { subtype?: string }).subtype === sub)
        .map((f) => String((f.properties as { classe?: string; niveau?: string }).classe
          ?? (f.properties as { niveau?: string }).niveau ?? '')))
      const classes = ORDRE.filter((c) => servies.has(c))
      const shown = classes.length ? classes : (['faible', 'moyen', 'fort'] as unknown as typeof classes)
      return <div data-legend-alea={k} className="flex flex-wrap items-center gap-2">{shown.map((n) => (
        <span key={n} className="flex items-center gap-1"><span className="h-2.5 w-4 rounded-sm border" style={{ background: ramp[n], borderColor: ramp[n] }} /><span className="text-[10.5px] text-txt-dim">{LAB[n]}</span></span>
      ))}</div>
    })(),
  }) })
  if (layers.transport) groupes.push({
    id: 'transport', titre: 'Transport public',
    note: `GTFS : réseaux officiels de La Réunion (Licence Ouverte) · Papang : © les contributeurs d'OpenStreetMap (ODbL)${fmtFraich(transQ)}. Les pôles d'échange sont dans « Axes structurants ».`,
    body: <div data-legend-transport className="flex flex-col gap-1 text-[11px] text-txt">
      {([['Car Jaune', 'cars interurbains (Région)'], ['Citalis', 'bus du Nord (CINOR) — et le téléphérique Papang, en tireté'], ["Kar'Ouest", 'bus de l’Ouest (TCO)'], ['Alternéo', 'bus du Sud-Ouest (CIVIS)'], ['Estival', 'bus de l’Est (CIREST)'], ['Carsud', 'bus du Sud (CASUD)']] as const).map(([r, d]) => (
        <span key={r} className="flex items-center gap-2"><span className="h-0.5 w-4 shrink-0 rounded" style={{ background: tTheme.transportReseaux[r] }} /><span><b>{r}</b> — {d}</span></span>
      ))}
      {/* RETOURS-14 S7 — les arrêts sont dans la MÊME couche (fusion) : cliquables (nom + lignes + réseau). */}
      <span className="mt-1 flex items-center gap-2"><span className="h-2 w-2 shrink-0 rounded-full border border-[#0A0F0C]" style={{ background: tTheme.transportReseaux['Citalis'] }} />arrêt — cliquable (nom, lignes, réseau), visible en zoomant</span>
    </div>,
  })
  if (layers.axes) groupes.push({
    id: 'axes', titre: 'Axes structurants',
    note: 'Double face : accessibilité ET nuisances (bruit, pollution, recul le long des axes classés). Axes : BD TOPO IGN, importance 1-2 (Licence Ouverte) · pôles : © OpenStreetMap (ODbL).',
    body: <div data-legend-axes className="flex flex-col gap-1 text-[11px] text-txt">
      <span className="flex items-center gap-2"><span className="h-1 w-4 rounded" style={{ background: tTheme.axe }} />Axes structurants (route des Tamarins, nationales…)</span>
      <span className="flex items-center gap-2"><span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: tTheme.pole }} />pôle d’échange relevé (OSM — Sourcé)</span>
      <span className="flex items-center gap-2"><span className="h-2.5 w-2.5 shrink-0 rounded-full border-2" style={{ borderColor: tTheme.pole }} />pôle estimé — {critereDerive}</span>
    </div>,
  })
  // RETOURS-14 S9 — UNE couche « Lignes électriques » : deux styles, deux sources citées.
  if (layers.lignes_ht) groupes.push({
    id: 'ht', titre: 'Lignes électriques (HTA / HTB)',
    note: `HTA (moyenne tension ~15-20 kV, distribution) : EDF Réunion open data, LO 2.0, géométrie ~02/2020 republiée 16/10/2025 — tracé indicatif (sécurité publique), jamais une DT-DICT. HTB (63/90 kV, transport) : BD TOPO IGN (aérien, tension indiquée)${fmtFraich(htQ)}. Contrainte potentielle (servitudes, reculs) — à vérifier auprès d'EDF SEI.`,
    body: <div data-legend-ht className="flex flex-col gap-1 text-[11px] text-txt">
      <span className="flex items-center gap-2"><span className="h-[3px] w-4 rounded" style={{ background: tTheme.ht }} />haute tension HTB — trait épais tireté (BD TOPO IGN)</span>
      <span className="flex items-center gap-2"><span className="h-px w-4 rounded" style={{ background: tTheme.mt }} />moyenne tension HTA — trait fin (EDF Réunion open data)</span>
    </div>,
  })
  // RETOURS-14 S8 — « Stationnement allégé » : légende à TROIS entrées (zone · station · voie).
  if (layers.tcsp) groupes.push({
    id: 'tcsp', titre: 'Stationnement allégé — TCSP',
    note: 'Sur une parcelle à moins de 800 m d’une station de transport en commun en site propre (rayon à vol d’oiseau — la pastille fait 1,6 km de large), le PLU ne peut pas exiger plus d’une place de stationnement par logement (0,5 pour le logement social), si la desserte est de qualité. Moins de parking = plus de surface vendable, bilan plus léger. Un simple couloir bus ne compte pas. Source : code de l’urbanisme, art. L151-34 à 36 (loi 2025-1129) ; voies et stations relevées dans OpenStreetMap ; en travaux / en projet (Réunion Express, débat public jusqu’au 26/11/2026) : aucun tracé public, rien n’est dessiné à la main.',
    body: <div data-legend-tcsp className="flex flex-col gap-1 text-[11px] text-txt">
      <span className="flex items-center gap-2"><span className="h-2.5 w-4 shrink-0 rounded-sm border" style={{ background: tTheme.tcsp, opacity: 0.45, borderColor: tTheme.tcsp }} />zone 800 m — parcelles au stationnement allégé</span>
      <span className="flex items-center gap-2"><span className="h-2.5 w-2.5 shrink-0 rounded-full border border-[#0A0F0C]" style={{ background: tTheme.tcsp }} />station en service</span>
      <span className="flex items-center gap-2"><span className="h-1 w-4 rounded" style={{ background: tTheme.tcsp }} />voie en site propre</span>
    </div>,
  })
  // SOURCES-1 lot 1 — groupe « Contraintes » : chaque entrée avec sa couleur ; le « i » dit la
  // source (GPU), l'opposabilité et la couverture partielle (DPU non publié, Pierrefonds absent).
  if (contraintesActif) groupes.push({
    id: 'contraintes', titre: 'Contraintes',
    note: 'Servitudes et périmètres opposables des PLU, déposés au Géoportail de l’urbanisme (millésime = le PLU de chaque commune). DPU : une commune absente n’a pas publié son périmètre au GPU (pas une preuve d’absence). PEB : Roland-Garros servi, Pierrefonds non publié au GPU. SUP : T5/PT1/PT2 restreintes au téléchargement, AS1 non publiée pour le 974.',
    body: <div data-legend-contraintes className="flex flex-col gap-1.5 text-[11px] text-txt">
      {layers.er && <span className="flex items-center gap-2"><span className="h-2.5 w-4 shrink-0 rounded-sm border" style={{ background: tTheme.er, opacity: tTheme.erOpacity + 0.35, borderColor: tTheme.er }} />Emplacement réservé (déduit de l’emprise)</span>}
      {layers.ebc && <span className="flex items-center gap-2"><span className="h-2.5 w-4 shrink-0 rounded-sm border" style={{ background: tTheme.ebc, opacity: tTheme.ebcOpacity + 0.35, borderColor: tTheme.ebc }} />Espace boisé classé (L113-1 — construction interdite)</span>}
      {layers.dpu && <span className="flex items-center gap-2"><span className="h-2.5 w-4 shrink-0 rounded-sm border" style={{ background: tTheme.dpu, opacity: tTheme.dpuOpacity + 0.35, borderColor: tTheme.dpu }} />Droit de préemption urbain (pèse sur la vente)</span>}
      {layers.peb && <>
        <span className="flex items-center gap-2"><span className="h-2.5 w-4 shrink-0 rounded-sm border" style={{ background: tTheme.pebRamp.a, borderColor: tTheme.pebRamp.a, opacity: 0.8 }} />PEB zone A/B — habitations interdites (L112-10)</span>
        <span className="flex items-center gap-2"><span className="h-2.5 w-4 shrink-0 rounded-sm border" style={{ background: tTheme.pebRamp.c, borderColor: tTheme.pebRamp.c, opacity: 0.8 }} />PEB zone C — isolement acoustique renforcé</span>
        <span className="flex items-center gap-2"><span className="h-2.5 w-4 shrink-0 rounded-sm border" style={{ background: tTheme.pebRamp.d, borderColor: tTheme.pebRamp.d, opacity: 0.8 }} />PEB zone D — information</span>
      </>}
      {layers.sup && <span className="flex items-center gap-2"><span className="h-2.5 w-4 shrink-0 rounded-sm border" style={{ background: tTheme.sup, opacity: tTheme.supOpacity + 0.35, borderColor: tTheme.sup }} />Servitude d’utilité publique (catégorie au clic)</span>}
      {layers.dpf && <span className="flex items-center gap-2"><span className="h-0.5 w-4 shrink-0" style={{ background: tTheme.dpf }} />Domaine public fluvial (marchepied 3,25 m — L2131-2)</span>}
      {layers.bruit_route && <>
        <span className="flex items-center gap-2"><span className="h-2.5 w-4 shrink-0 rounded-sm border" style={{ background: tTheme.bruitRamp.cat1, borderColor: tTheme.bruitRamp.cat1, opacity: 0.85 }} />Classement sonore cat. 1-2 (bandes 250-300 m — isolement renforcé R571-32)</span>
        <span className="flex items-center gap-2"><span className="h-2.5 w-4 shrink-0 rounded-sm border" style={{ background: tTheme.bruitRamp.cat4, borderColor: tTheme.bruitRamp.cat4, opacity: 0.85 }} />Classement sonore cat. 3-5 (bandes 10-100 m)</span>
      </>}
      {layers.bruit_carte && <span className="flex items-center gap-2"><span className="h-2.5 w-4 shrink-0 rounded-sm border" style={{ background: tTheme.bruitCarte, opacity: tTheme.bruitCarteOpacity + 0.35, borderColor: tTheme.bruitCarte }} />Dépassement des valeurs limites (CBS 2022 — ≠ classement)</span>}
    </div>,
  })
  // SOURCES-1 lot 2 — groupe « Nature » : zones humides, espaces protégés, cultures déclarées.
  const natureActif = layers.zone_humide || layers.enp || layers.rpg
  if (natureActif) groupes.push({
    id: 'nature', titre: 'Nature',
    note: 'Zones humides : inventaires DEAL PAR SECTEURS (2003→2019) — l’absence d’inventaire n’est pas une preuve. Espaces protégés : INPN + compléments DEAL Carmen (Réserve marine, Ramsar, sites classés/inscrits). RPG : déclarations PAC (indication d’usage, pas une servitude).',
    body: <div data-legend-nature className="flex flex-col gap-1.5 text-[11px] text-txt">
      {layers.zone_humide && <span className="flex items-center gap-2"><span className="h-2.5 w-4 shrink-0 rounded-sm border" style={{ background: tTheme.zoneHumide, opacity: tTheme.zoneHumideOpacity + 0.35, borderColor: tTheme.zoneHumide }} />Zone humide inventoriée (loi sur l’eau — vigilance forte)</span>}
      {layers.enp && <span className="flex items-center gap-2"><span className="h-2.5 w-4 shrink-0 rounded-sm border" style={{ background: tTheme.enp, opacity: tTheme.enpOpacity + 0.35, borderColor: tTheme.enp }} />Espace naturel protégé (réserves/APB rédhibitoires)</span>}
      {layers.rpg && <span className="flex items-center gap-2"><span className="h-2.5 w-4 shrink-0 rounded-sm border" style={{ background: tTheme.rpg, opacity: tTheme.rpgOpacity + 0.35, borderColor: tTheme.rpg }} />Culture déclarée (RPG — canne : sole exploitée)</span>}
    </div>,
  })
  // SOURCES-1 lot 3 — groupe « Sols » : SIS (périmètres réglementaires) et CASIAS (inventaire).
  const solsActif = layers.sis || layers.casias
  if (solsActif) groupes.push({
    id: 'sols', titre: 'Sols (SIS / CASIAS)',
    note: 'SIS : secteurs d’information sur les sols (4 au 974) — étude de sols obligatoire au changement d’usage (L556-2), information écrite de l’acheteur/locataire obligatoire (L125-7). CASIAS : inventaire HISTORIQUE des activités industrielles — pas une pollution avérée.',
    body: <div data-legend-sols className="flex flex-col gap-1.5 text-[11px] text-txt">
      {layers.sis && <span className="flex items-center gap-2"><span className="h-2.5 w-4 shrink-0 rounded-sm border" style={{ background: tTheme.sis, opacity: tTheme.sisOpacity + 0.35, borderColor: tTheme.sis }} />Secteur d’information sur les sols (réglementaire)</span>}
      {layers.casias && <span className="flex items-center gap-2"><span className="h-2.5 w-2.5 shrink-0 rounded-full border" style={{ background: tTheme.casias, borderColor: tTheme.casias }} />Ancien site industriel (CASIAS — inventaire)</span>}
    </div>,
  })
  if (dispoActif) groupes.push({
    id: 'dispositifs', titre: 'Dispositifs et périmètres',
    note: 'ZFANG / FRR : maille COMMUNE entière (pas un périmètre fin). Bande TVA : périmètre dérivé des QPV (Estimé).',
    body: <div data-legend-dispositifs className="flex flex-col gap-1.5 text-[11px] text-txt">
      {layers.qpv && <span className="flex items-center gap-2"><span className="h-2.5 w-4 shrink-0 rounded-sm border" style={{ background: tTheme.qpv, opacity: tTheme.qpvOpacity + 0.35, borderColor: tTheme.qpv }} />QPV — quartier prioritaire{fmtFraich(qpvQ)}</span>}
      {layers.tva_primo && <span className="flex items-center gap-2"><span className="h-2.5 w-4 shrink-0 rounded-sm border" style={{ background: tTheme.tvaPrimo, opacity: tTheme.tvaPrimoOpacity + 0.35, borderColor: tTheme.tvaPrimo }} /><span>TVA réduite primo-accédant (QPV + 500 m) — <i className="text-txt-dim">dérivé</i></span></span>}
      {layers.anru && <span className="flex items-center gap-2"><span className="h-2.5 w-4 shrink-0 rounded-sm border" style={{ background: tTheme.anru, opacity: tTheme.anruOpacity + 0.35, borderColor: tTheme.anru }} />NPNRU / ANRU{fmtFraich(anruQ)}</span>}
      {layers.zfang && <><span data-legend-zfang-renforce className="flex items-center gap-2"><span className="h-2.5 w-4 shrink-0 rounded-sm border" style={{ background: tTheme.zfangRenforce, borderColor: tTheme.zfangRenforce }} />ZFANG renforcée — 6 communes de l’Est</span><span data-legend-zfang-standard className="flex items-center gap-2"><span className="h-2.5 w-4 shrink-0 rounded-sm border" style={{ backgroundColor: tTheme.zfangStandard, borderColor: tTheme.zfangStandard, backgroundImage: 'repeating-linear-gradient(45deg, rgba(0,0,0,.35) 0 1.5px, transparent 1.5px 4px)' }} />ZFANG standard — 18 communes</span></>}
      {layers.frr && <><span data-legend-frr-totalite className="flex items-center gap-2"><span className="h-2.5 w-4 shrink-0 rounded-sm border" style={{ background: tTheme.frrTotalite, borderColor: tTheme.frrTotalite }} />FRR totalité — 3 communes</span><span data-legend-frr-partie className="flex items-center gap-2"><span className="h-2.5 w-4 shrink-0 rounded-sm border" style={{ backgroundColor: tTheme.frrPartie, borderColor: tTheme.frrPartie, backgroundImage: 'repeating-linear-gradient(-45deg, rgba(0,0,0,.35) 0 1.5px, transparent 1.5px 4px)' }} />FRR en partie — 20 communes</span></>}
    </div>,
  })
  // SECTEUR-2b (U1) — prix du logement neuf (VEFA acté DVF), aplat commune, choropleth par tranche.
  // Rampe DISTINCTE (jaune → orange → magenta), hors du vert des statuts ; sous le seuil = hachure grise.
  if (layers.vefa_neuf) groupes.push({
    id: 'vefa_neuf', titre: 'Prix du logement neuf (VEFA)',
    note: 'Médiane du prix au m² bâti des ventes VEFA (« état futur d’achèvement ») réellement actées — geo-DVF (DGFiP), fenêtre 36 mois glissants, maille COMMUNE. Peinte là où au moins 10 ventes soutiennent la médiane ; sous ce seuil : hachure grise (« moins de 10 ventes »), jamais vide. CLIC sur une commune → détail (médiane, tendance 12 mois, répartition, offre engagée Sitadel). Le STOCK du neuf relève de l’ECLN (SDES, métropole seule) — hors champ La Réunion, jamais extrapolé.',
    body: <div data-legend-vefa className="flex flex-col gap-1 text-[11px] text-txt">
      {[['moins_4000', '#FDE047', '< 4 000 €/m²'], ['4000_4500', '#FB923C', '4 000–4 500 €/m²'],
        ['4500_5000', '#EA6D2A', '4 500–5 000 €/m²'], ['5000_5500', '#D6337A', '5 000–5 500 €/m²'],
        ['5500_plus', '#A21CAF', '≥ 5 500 €/m²']].map(([k, c, lab]) => (
        <span key={k} className="flex items-center gap-2"><span className="h-2.5 w-4 shrink-0 rounded-sm border" style={{ background: c, borderColor: c }} />{lab}</span>
      ))}
      <span data-legend-vefa-hachure className="flex items-center gap-2 text-txt-dim">
        <span className="h-2.5 w-4 shrink-0 rounded-sm border border-line-2" style={{ backgroundColor: '#3B4046', backgroundImage: 'repeating-linear-gradient(-45deg, #9AA0A6 0 1px, transparent 1px 4px)' }} />
        moins de 10 ventes (hachuré)</span>
    </div>,
  })
  if (layers.renouv) groupes.push({
    id: 'renouv', titre: 'Densifier l’existant',
    note: 'Parcelles occupées (bâties) en zone U/AU avec capacité résiduelle — potentiel de densification, pas une opportunité qualifiée.',
    body: <div data-legend-renouv className="flex items-center gap-2"><span className="h-2.5 w-4 rounded-sm" style={{ background: TOKENS.renouv, opacity: 0.7 }} /><span className="text-[11px] text-txt">Occupées, capacité résiduelle</span></div>,
  })
  if (equipPeint) groupes.push({
    id: 'equip', titre: 'Équipements (OSM)',
    body: <div data-legend-equip className="flex flex-col gap-0.5 text-[11px]">{EQUIP_META.map((e) => (
      <span key={e.key} className="flex items-center gap-1.5 text-txt-mut"><span className="text-[13px] leading-none">{e.emoji}</span>{e.label}</span>
    ))}</div>,
  })

  if (!groupes.length) return null

  // SECTEUR-1 (S4) — repliée par défaut, une seule ligne « Légende · N couches ▾ » ; le PREMIER groupe
  // s'ouvre par défaut, les autres repliés (état mémorisé).
  const grpOpen = (id: string, i: number) => leg.groupes[id] ?? (i === 0)
  const toggleGrp = (id: string) => set({ ...leg, groupes: { ...leg.groupes, [id]: !grpOpen(id, groupes.findIndex((g) => g.id === id)) } })

  // « N couches » = les couches ACTIVES à l'écran (ce que Vic voit cocher), pas le nombre de groupes.
  const nCouches = Object.values(layers).filter(Boolean).length
  const shell = inline ? 'rounded-xl bg-surface-2' : 'floating absolute bottom-4 right-4 hidden sm:block'
  return (
    <div data-legend className={`${shell} w-[240px]`}>
      <button data-legend-toggle onClick={() => set({ ...leg, open: !leg.open })} aria-expanded={leg.open}
        className="flex w-full items-center gap-2 px-3.5 py-2 text-left" title={leg.open ? 'Replier la légende' : 'Déplier la légende'}>
        <span className="label-caps flex-1">Légende <span className="text-txt-dim">· {nCouches} {nCouches > 1 ? 'couches' : 'couche'}</span></span>
        <ChevronSection open={leg.open} />
      </button>
      {leg.open && (
        <div data-legend-corps className="max-h-[35vh] overflow-y-auto border-t border-line px-3.5 py-2">
          {groupes.map((g, i) => (
            <Groupe key={g.id} titre={g.titre} note={g.note} open={grpOpen(g.id, i)} onToggle={() => toggleGrp(g.id)}>{g.body}</Groupe>
          ))}
        </div>
      )}
    </div>
  )
}
