/**
 * ÉTUDE DE ZONE · Z4 + ZONE-RECETTE — l'outil de chalandise (maquette, écran 2).
 *
 * DEUX entrées EXCLUSIVES (segmenté en tête) :
 *  · « Autour d'un point » → ParcelInput (SOCLE : adresse OU IDU) + temps de trajet + mode.
 *  · « Zone dessinée » → « Dessiner la zone » (polygone) ; temps/mode disparaissent (ils n'ont aucun
 *    sens sur un polygone). Basculer d'un onglet à l'autre efface le périmètre de l'autre.
 *
 * L'en-tête de résultat DÉSIGNE le périmètre réellement mesuré (jamais « à 10 min » sur un polygone).
 * Concurrents / actifs : trois états honnêtes (servie+0 / non couvert / indisponible), jamais un faux zéro.
 * Faits sourcés et datés — AUCUNE prévision de chiffre d'affaires.
 */
import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'

import { ParcelInput } from '../ParcelInput'
import { etudeZone, etudeZoneEntreprises, nafFamilles, nafSearch, parcelAt, type EtudeZoneInput } from '../../lib/api'
import type { EtudeZoneResult, NafFamille, NafOption, ZoneEntreprises } from '../../lib/types'
import { iduCourt } from '../../lib/format'
import { useApp } from '../../store/useApp'

const TEMPS = [5, 10, 15]

function nb(n: number | null | undefined): string {
  return n == null ? '—' : n.toLocaleString('fr-FR')
}
// F2 (OUTILS-4) — date de dernier traitement SIRENE (YYYY-MM-DD) → « MM/YYYY » lisible.
const majFr = (d: string | null | undefined): string | null => (d && d.length >= 7 ? `${d.slice(5, 7)}/${d.slice(0, 4)}` : null)

function tempsTxt(min: number | null, mode: 'pied' | 'voiture'): string {
  if (min == null) return 'dans la zone'
  return `${min} min${mode === 'pied' ? ' à pied' : ''}`
}

export function EtudeZone() {
  const setModuleMap = useApp((s) => s.setModuleMap)
  const setTool = useApp((s) => s.setTool)
  const drawnZone = useApp((s) => s.zone)          // polygone dessiné [lng,lat][]
  const setZone = useApp((s) => s.setZone)
  const setFlyTo = useApp((s) => s.setFlyTo)

  const [entree, setEntree] = useState<'point' | 'polygone'>('point')
  const [cible, setCible] = useState<{ idu: string; label: string } | null>(null)
  const [mode, setMode] = useState<'voiture' | 'pied'>('voiture')
  const [minutes, setMinutes] = useState(10)

  const [nafQuery, setNafQuery] = useState('')
  const [naf, setNaf] = useState<NafOption | null>(null)
  const [nafOpts, setNafOpts] = useState<NafOption[]>([])
  useEffect(() => {
    if (naf || nafQuery.trim().length < 2) { setNafOpts([]); return }
    let alive = true
    const t = setTimeout(() => { nafSearch(nafQuery).then((r) => alive && setNafOpts(r.resultats)).catch(() => {}) }, 220)
    return () => { alive = false; clearTimeout(t) }
  }, [nafQuery, naf])
  // C4 — déroulé PARCOURABLE par familles (chargé à la 1re ouverture), pour choisir sans savoir quoi taper
  const [parcourir, setParcourir] = useState(false)
  const [familles, setFamilles] = useState<NafFamille[] | null>(null)
  const [famOuverte, setFamOuverte] = useState<string | null>(null)
  useEffect(() => {
    if (parcourir && familles == null) nafFamilles().then((r) => setFamilles(r.familles)).catch(() => {})
  }, [parcourir, familles])
  const choisirNaf = (o: NafOption) => { setNaf(o); setNafOpts([]); setNafQuery(''); setParcourir(false) }

  const geomFromDrawn = useMemo(() => {
    if (!drawnZone || drawnZone.length < 3) return null
    return { type: 'Polygon' as const, coordinates: [[...drawnZone, drawnZone[0]]] }
  }, [drawnZone])

  const mut = useMutation<EtudeZoneResult, Error, void>({
    mutationFn: () => {
      const body: EtudeZoneInput = { minutes, mode, naf: naf?.code ?? null }
      if (entree === 'polygone' && geomFromDrawn) { body.geom = geomFromDrawn; body.titre = 'Zone dessinée' }
      else if (cible) { body.idu = cible.idu; body.titre = cible.label }
      return etudeZone(body)
    },
  })
  const res = mut.data

  // F3 (OUTILS-4) — « Toutes les entreprises de la zone » : ouvert à la demande, MÊME emprise que
  // l'étude (sans NAF). Chargé une fois par zone ; réinitialisé quand l'entrée change.
  const [entOpen, setEntOpen] = useState(false)
  const entBody = (): EtudeZoneInput => {
    const b: EtudeZoneInput = { minutes, mode }
    if (entree === 'polygone' && geomFromDrawn) b.geom = geomFromDrawn
    else if (cible) b.idu = cible.idu
    return b
  }
  const entQ = useQuery({
    queryKey: ['zone-entreprises', entree, cible?.idu, minutes, mode, !!geomFromDrawn],
    queryFn: () => etudeZoneEntreprises(entBody()), enabled: entOpen && !!res?.zone_disponible,
  })

  // RELANCER — toute modification d'entrée réarme « Analyser » : on efface le résultat périmé.
  useEffect(() => { mut.reset(); setEntOpen(false) /* eslint-disable-next-line react-hooks/exhaustive-deps */ },
    [entree, cible, naf, minutes, mode, geomFromDrawn])

  // basculer d'onglet efface le périmètre de l'AUTRE entrée
  const choisirEntree = (e: 'point' | 'polygone') => {
    if (e === entree) return
    if (e === 'point') { setZone(null); setTool(null) }        // on quitte le polygone
    else { setCible(null) }                                    // on quitte le point
    setEntree(e)
  }

  // pousse la zone sur la carte : anneaux d'isochrone + point d'origine + concurrents (ambre). Nettoie en sortie.
  useEffect(() => {
    if (!res?.zone_disponible) return
    const feats: unknown[] = []
    for (const b of res.bandes ?? []) feats.push({ type: 'Feature', geometry: b.geom, properties: { kind: 'zone-iso' } })
    if ((!res.bandes || res.bandes.length === 0) && res.geom) feats.push({ type: 'Feature', geometry: res.geom, properties: { kind: 'zone-iso' } })
    if (res.origine && res.entree === 'point') feats.push({ type: 'Feature', geometry: { type: 'Point', coordinates: [res.origine.lon, res.origine.lat] }, properties: { kind: 'zone-origin' } })
    // F8 (OUTILS-3) — la pastille concurrent porte de quoi se rendre CLIQUABLE (popup : nom, activité,
    // date de création, lien parcelle). L'activité lisible (naf_label) est portée par le bloc concurrents.
    for (const c of res.concurrents?.items ?? []) feats.push({ type: 'Feature', geometry: { type: 'Point', coordinates: [c.lon, c.lat] },
      properties: { kind: 'zone-concurrent', siret: c.siret, nom: c.nom, annee: c.annee_creation ?? '', activite: res.concurrents?.naf_label ?? res.concurrents?.naf ?? '', lon: c.lon, lat: c.lat } })
    // F3 — quand « Toutes les entreprises » est ouvert, ses établissements deviennent des pastilles
    // cliquables (même popup que les concurrents). Comptes exacts en liste, pastilles plafonnées.
    if (entOpen && entQ.data) {
      for (const f of entQ.data.familles) for (const e of f.etablissements) feats.push({ type: 'Feature',
        geometry: { type: 'Point', coordinates: [e.lon, e.lat] },
        properties: { kind: 'zone-concurrent', siret: e.siret, nom: e.nom, annee: e.annee_creation ?? '', activite: e.naf_label ?? e.naf ?? '', lon: e.lon, lat: e.lat } })
    }
    setModuleMap({ idus: [], extra: { type: 'FeatureCollection', features: feats } })
    if (res.origine) setFlyTo({ center: [res.origine.lon, res.origine.lat], zoom: 13 })
  }, [res, entOpen, entQ.data, setModuleMap, setFlyTo])
  // LOT F — au DÉMONTAGE de l'outil (← Outils, changement d'outil, de catégorie ou de route), on efface
  // l'emprise de travail : la carte redevient nette, le pointillé ne survit pas. Couvre TOUTES les
  // sorties (toggleOutils comme setModule). Les veilles enregistrées (serveur) ne sont pas touchées.
  useEffect(() => () => { setModuleMap({ idus: [], extra: null }); setZone(null); setTool(null) },
    [setModuleMap, setZone, setTool])

  const pretA = entree === 'polygone' ? !!geomFromDrawn : !!cible

  const nouvelleEtude = () => {
    setCible(null); setNaf(null); setNafQuery(''); setZone(null); setTool(null)
    setModuleMap({ idus: [], extra: null }); mut.reset()
  }

  const enTete = res?.zone_disponible
    ? (res.entree === 'polygone'
        ? `La zone dessinée — ${nb(res.surface_ha)} ha`
        : `La zone à ${res.minutes} min ${res.mode === 'voiture' ? 'en voiture' : 'à pied'}${res.adresse ? ` — depuis ${res.adresse}` : ''}`)
    : ''

  return (
    <div data-etude-zone className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto pr-1">
      {/* SEGMENTÉ — deux entrées exclusives */}
      <div className="flex gap-1 rounded-lg border border-line-2 bg-surface-2 p-0.5">
        {([['point', 'Autour d’un point'], ['polygone', 'Zone dessinée']] as const).map(([e, lbl]) => (
          <button key={e} onClick={() => choisirEntree(e)}
            className={`flex-1 rounded-md px-2 py-1 text-[11px] font-medium transition-colors duration-quick ${entree === e ? 'bg-mint/15 text-txt-hi' : 'text-txt-mut hover:text-txt'}`}>{lbl}</button>
        ))}
      </div>

      {entree === 'point' ? (
        <>
          <ParcelInput dataAttr="zone-point" placeholder="Adresse ou IDU (ex. 12 rue…, ou 97415…)"
            withCarte onPick={(idu) => setCible({ idu, label: iduCourt(idu) })} />
          {cible && <div className="text-[10.5px] text-txt-mut">Point : {cible.label}</div>}
          {/* TEMPS + MODE (n'ont de sens QUE sur un point) */}
          <div className="flex gap-1 rounded-lg border border-line-2 bg-surface-2 p-0.5">
            {TEMPS.map((t) => (
              <button key={t} onClick={() => setMinutes(t)}
                className={`flex-1 rounded-md px-2 py-1 text-[11px] font-medium ${minutes === t ? 'bg-mint/15 text-txt-hi' : 'text-txt-mut hover:text-txt'}`}>{t} min</button>
            ))}
          </div>
          <div className="flex gap-1 rounded-lg border border-line-2 bg-surface-2 p-0.5">
            {(['voiture', 'pied'] as const).map((mo) => (
              <button key={mo} onClick={() => setMode(mo)}
                className={`flex-1 rounded-md px-2 py-1 text-[11px] font-medium ${mode === mo ? 'bg-mint/15 text-txt-hi' : 'text-txt-mut hover:text-txt'}`}>{mo === 'voiture' ? 'Voiture' : 'À pied'}</button>
            ))}
          </div>
        </>
      ) : (
        <>
          <button onClick={() => setTool('zone')}
            className="w-full rounded-lg border border-mint/40 bg-mint/10 px-3 py-2 text-[12px] font-medium text-mint hover:bg-mint/15">
            ✏️ Dessiner la zone
          </button>
          <div className="text-[10.5px] text-txt-mut">
            {geomFromDrawn ? `Polygone dessiné (${drawnZone!.length} sommets)` : 'Aucune zone tracée — cliquez « Dessiner la zone », posez les sommets, Entrée pour valider.'}
          </div>
        </>
      )}

      {/* ACTIVITÉ (NAF) — deux entrées : frappe libre avec propositions, OU déroulé par familles.
          Référentiel = nomenclature NAF complète (« notaire », « pharmacie », « garage »… résolvent). */}
      <div>
        <div className="relative">
          <input value={naf ? naf.label : nafQuery}
            onChange={(e) => { setNaf(null); setNafQuery(e.target.value) }}
            placeholder="Activité étudiée (ex. « notaire », « pharmacie »)"
            className="w-full rounded-lg border border-line-2 bg-surface-2 px-2.5 py-1.5 text-[12px] text-txt outline-none focus:border-mint/60" />
          {naf && <button onClick={() => { setNaf(null); setNafQuery('') }} className="absolute right-2 top-1.5 text-[11px] text-txt-dim hover:text-txt">×</button>}
          {nafOpts.length > 0 && (
            <div className="absolute z-20 mt-1 max-h-52 w-full overflow-y-auto rounded-lg border border-line-2 bg-surface-1 shadow-lg">
              {nafOpts.map((o) => (
                <button key={o.code} onClick={() => choisirNaf(o)}
                  className="flex w-full items-center justify-between gap-2 px-2.5 py-1.5 text-left text-[11.5px] text-txt hover:bg-mint/10">
                  <span className="truncate">{o.label}</span><span className="shrink-0 font-mono text-[10px] text-txt-dim">{o.code}</span>
                </button>
              ))}
            </div>
          )}
        </div>
        <button onClick={() => setParcourir((v) => !v)}
          className="mt-1 text-[10.5px] text-txt-dim underline decoration-txt-dim/40 underline-offset-2 hover:text-mint">
          {parcourir ? 'masquer les familles' : 'parcourir par famille d’activité'}
        </button>
        {parcourir && (
          <div className="mt-1 max-h-64 overflow-y-auto rounded-lg border border-line-2 bg-surface-1">
            {familles == null ? (
              <p className="px-2.5 py-2 text-[11px] text-txt-dim">Chargement…</p>
            ) : familles.map((f) => (
              <div key={f.section} className="border-b border-line-2 last:border-b-0">
                <button onClick={() => setFamOuverte((s) => (s === f.section ? null : f.section))}
                  className="flex w-full items-center justify-between gap-2 px-2.5 py-1.5 text-left text-[11.5px] font-medium text-txt hover:bg-mint/10">
                  <span className="truncate">{f.nom}</span>
                  <span className="shrink-0 text-[10px] text-txt-dim">{f.activites.length}</span>
                </button>
                {famOuverte === f.section && (
                  <div className="bg-surface-2/40">
                    {f.activites.map((o) => (
                      <button key={o.code} onClick={() => choisirNaf(o)}
                        className="flex w-full items-center justify-between gap-2 px-3 py-1 text-left text-[11px] text-txt-mut hover:bg-mint/10 hover:text-txt">
                        <span className="truncate">{o.label}</span><span className="shrink-0 font-mono text-[9.5px] text-txt-dim">{o.code}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <button onClick={() => mut.mutate()} disabled={!pretA || mut.isPending}
        className={`rounded-lg px-3 py-2 text-[12px] font-medium ${pretA && !mut.isPending ? 'bg-mint/20 text-txt-hi hover:bg-mint/30' : 'bg-surface-2 text-txt-dim'}`}>
        {mut.isPending ? 'Calcul de la zone…' : 'Analyser la zone'}
      </button>

      {/* RÉSULTATS */}
      {res && !res.zone_disponible && (
        <div data-zone-indisponible className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11px] leading-snug text-txt-mut">
          Zone atteignable indisponible — {res.detail ?? 'le service d’isochrones IGN n’a pas répondu'}.
          <span className="text-txt-dim"> Aucun cercle approximatif n’est affiché à la place.</span>
        </div>
      )}

      {res?.zone_disponible && (
        <div className="flex flex-col gap-3">
          <SectionTitle>{enTete}</SectionTitle>
          {res.population?.inhabitee ? (
            <p className="text-[11px] text-txt-mut">Zone peu ou pas habitée (aucun carreau INSEE peuplé).</p>
          ) : (
            <div className="grid grid-cols-2 gap-2">
              <Stat v={nb(res.population?.habitants)} k="habitants" />
              <Stat v={nb(res.population?.menages)} k="ménages" />
              <Stat v={res.population?.revenu_median_eur != null ? `${nb(res.population.revenu_median_eur)} €` : '—'}
                k={res.population?.revenu_majorite_imputee
                  ? `revenu médian / an · valeur approchée (${nb(res.population.revenu_impute_n)}/${nb(res.population.revenu_carreaux_n)} carreaux)`
                  : 'revenu médian / an'} est />
              <ActifsStat res={res} />
            </div>
          )}

          {/* CONCURRENTS — trois états honnêtes, jamais un faux zéro */}
          {naf && <Concurrents res={res} />}

          {/* F3 (OUTILS-4) — TOUTES les entreprises de la zone, groupées par famille (à la demande). */}
          {res.emplois_couverture === 'servie' && (res.emplois?.n_etablissements ?? 0) > 0 && (
            <ToutesEntreprises total={res.emplois!.n_etablissements} open={entOpen} setOpen={setEntOpen}
              data={entQ.data} loading={entQ.isFetching} error={entQ.isError} />
          )}

          {res.generateurs_flux && res.generateurs_flux.length > 0 && (
            <div>
              <SectionTitle>Générateurs de flux</SectionTitle>
              <div className="flex flex-col gap-1">
                {res.generateurs_flux.map((g, i) => (
                  <div key={i} className="flex items-center justify-between gap-2 text-[11.5px]">
                    <span className="truncate text-txt">{g.label}</span><span className="shrink-0 font-mono text-[10px] text-txt-dim">{g.source}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {res.marche && (
            <div>
              <SectionTitle>Marché immobilier de la zone</SectionTitle>
              <div className="grid grid-cols-2 gap-2">
                <Stat v={nb(res.marche.ventes_12m)} k="ventes / 12 mois" />
                <Stat v={res.marche.prix_m2_median_bati != null ? `${nb(res.marche.prix_m2_median_bati)} €` : '—'} k="médian €/m² bâti" />
                <Stat v={nb(res.marche.annonces_actives)} k="annonces actives" />
                <Stat v={nb(res.marche.permis_36m)} k="permis / 36 mois" />
              </div>
            </div>
          )}

          {/* LOT 5 — trafic RN traversant/bordant la zone (véhicules/jour, dernier comptage par route) */}
          {res.trafic?.couverte && (
            <div>
              <SectionTitle>Trafic routes nationales</SectionTitle>
              {res.trafic.axes.length === 0 ? (
                <p className="text-[11px] text-txt-mut">Aucun axe national dans la zone.</p>
              ) : (
                <div className="flex flex-col gap-1">
                  {res.trafic.axes.slice(0, 5).map((a, i) => (
                    <div key={i} className="flex items-center justify-between gap-2 text-[11.5px]">
                      <span className="text-txt">{a.route} <span className="text-txt-dim">· {a.annee}</span></span>
                      <span className="shrink-0 font-mono text-[11px] text-txt-hi">{nb(a.tmja)} véh./j</span>
                    </div>
                  ))}
                  <span className="text-[9.5px] text-txt-dim">Trafic véhicules sur routes nationales (Région Réunion) — pas un flux piéton.</span>
                </div>
              )}
            </div>
          )}

          {/* LOT 7 — contraintes commerciales : les zones PLU recouvertes (tableau ZONE / PART / DOCUMENT) */}
          {res.contraintes_plu && res.contraintes_plu.zones.length > 0 && (
            <div>
              <SectionTitle>Zones PLU de la zone</SectionTitle>
              <div className="flex flex-col gap-1">
                {res.contraintes_plu.zones.slice(0, 6).map((z, i) => (
                  <div key={i} className="flex items-center justify-between gap-2 text-[11.5px]">
                    <span className="truncate text-txt">{z.zone} <span className="text-txt-mut">· {z.commune ?? ''}</span></span>
                    <span className="shrink-0 font-mono text-[11px] text-txt-hi">{z.part_pct}%</span>
                  </div>
                ))}
              </div>
              {res.contraintes_plu.cdac_vigilance && <p className="mt-1 text-[9.5px] leading-snug text-txt-dim">{res.contraintes_plu.cdac_vigilance}</p>}
            </div>
          )}

          {/* LOT 8 — La zone de demain : signal DATÉ (logements autorisés 36 mois + zones AU), jamais une projection */}
          {res.zone_demain && ((res.zone_demain.logements_autorises_36m ?? 0) > 0 || (res.zone_demain.au_zones_n ?? 0) > 0) && (
            <div>
              <SectionTitle>La zone de demain</SectionTitle>
              <div className="grid grid-cols-2 gap-2">
                <Stat v={nb(res.zone_demain.logements_autorises_36m)} k="logements autorisés / 36 mois" />
                <Stat v={res.zone_demain.au_zones_n ? `${nb(res.zone_demain.au_zones_n)} · ${nb(res.zone_demain.au_zones_ha)} ha` : '—'} k="zones AU (à urbaniser)" />
              </div>
              <p className="mt-1 text-[9.5px] leading-snug text-txt-dim">Signal daté (Sitadel · PLU) — une urbanisation programmée, jamais une projection de population.</p>
            </div>
          )}

          {/* RECETTE-2 LOT C1 : le bouton « Exporter le PDF » est retiré. */}
          <button onClick={nouvelleEtude} className="w-full rounded-lg border border-line-2 px-3 py-1.5 text-[11.5px] font-medium text-txt-mut hover:border-mint/40 hover:text-txt">Nouvelle étude</button>
          {res.note && <p className="text-[9.5px] leading-snug text-txt-dim">{res.note}</p>}
        </div>
      )}
    </div>
  )
}

// LOT 2 — « postes salariés déclarés dans la zone » : FOURCHETTE (tranches d'effectif SIRENE), jamais
// un point ni « actifs y travaillent » (qui décrit autre chose). Les établissements sans tranche
// renseignée sont dits à part. Non couvert (SIRENE vide) dit tel quel, jamais un « — » muet.
function ActifsStat({ res }: { res: EtudeZoneResult }) {
  if (res.emplois_couverture === 'non_couverte') {
    return (
      <div className="rounded-lg border border-line-2 bg-surface-2 px-2.5 py-2">
        <div className="text-[11px] font-medium text-txt-mut">non couvert</div>
        <div className="mt-0.5 text-[10px] text-txt-mut">postes salariés <span className="text-txt-dim">· pas encore servi sur LABUSE</span></div>
      </div>
    )
  }
  const e = res.emplois
  const fourchette = e ? `${nb(e.postes_min)}–${nb(e.postes_max)}${e.postes_max_ouvert ? '+' : ''}` : '—'
  return (
    <div className="rounded-lg border border-line-2 bg-surface-2 px-2.5 py-2">
      <div className="text-[13px] font-semibold text-txt-hi">{fourchette}</div>
      <div className="mt-0.5 text-[10px] text-txt-mut">postes salariés déclarés dans la zone
        {e && e.n_sans_tranche > 0 && <span className="text-txt-dim"> · {nb(e.n_sans_tranche)} étab. sans effectif renseigné</span>}</div>
    </div>
  )
}

function Concurrents({ res }: { res: EtudeZoneResult }) {
  const c = res.concurrents
  const cov = c?.couverture
  const { setView, select } = useApp()
  // A3-bis (OUTILS-2) — cliquable vers la parcelle : le concurrent porte sa position (lon/lat) ;
  // on résout la parcelle à ce point (parcelAt) et on ouvre sa fiche sur la carte. Rien si hors parcelle.
  const ouvrirParcelle = async (lon: number, lat: number) => {
    try {
      const { idu } = await parcelAt(lon, lat)
      if (idu) { setView('cartes'); select(idu) }
    } catch { /* pas de parcelle à ce point — on ne fait rien */ }
  }
  return (
    <div>
      {/* F2 (OUTILS-4) — « déclarés au registre » : on ne dit jamais que ce sont les concurrents RÉELS,
          seulement ceux déclarés actifs au registre SIRENE (une fermeture non signalée peut y traîner). */}
      <SectionTitle>{`Concurrents déclarés au registre${cov === 'servie' ? ` — ${c!.n}` : ''}`}{cov === 'servie' && res.habitants_par_concurrent != null && <span className="ml-1 font-normal normal-case tracking-normal text-txt-mut">· {nb(res.habitants_par_concurrent)} hab./concurrent</span>}</SectionTitle>
      {/* F1 (OUTILS-3) — activité LISIBLE (le code NAF passe en second plan / survol). */}
      {cov === 'servie' && (c!.naf_label || c!.naf) && (
        <p className="mt-0.5 text-[10.5px] text-txt-mut" title={`code NAF ${c!.naf}`}>{c!.naf_label ?? c!.naf} <span className="font-mono text-[9px] text-txt-dim">{c!.naf}</span></p>
      )}
      {/* F8 — légende courte des pastilles carte (cliquables). */}
      {cov === 'servie' && c!.items.length > 0 && (
        <p className="mt-0.5 flex items-center gap-1.5 text-[10px] text-txt-dim">
          <span className="h-[8px] w-[8px] shrink-0 rounded-full" style={{ background: '#E0A94F' }} />
          pastilles orange sur la carte — cliquez pour le détail et la parcelle.
        </p>
      )}
      {cov === 'non_couverte' && (
        // RECETTE-2 LOT C2 : vocabulaire client — pas de « répertoire SIRENE / ingéré » (tuyauterie).
        <p className="text-[11px] text-txt-mut">Non couvert · le registre des établissements n’est pas encore servi sur LABUSE.</p>
      )}
      {cov === 'erreur' && (
        <p className="text-[11px] text-txt-mut">Indisponible — la requête concurrents n’a pas abouti.</p>
      )}
      {cov === 'servie' && (c!.items.length === 0 ? (
        <p className="text-[11px] text-txt-mut">Aucun établissement de cette activité dans la zone.</p>
      ) : (
        <div className="flex flex-col gap-1">
          {c!.items.slice(0, 8).map((x) => (
            // A3-bis + F2 — « enseigne · depuis AAAA · déclaré actif · mis à jour MM/YYYY », cliquable.
            <button key={x.siret} type="button" onClick={() => ouvrirParcelle(x.lon, x.lat)}
              className="flex items-start justify-between gap-2 rounded-md px-1 py-0.5 text-left text-[11.5px] transition-colors duration-quick hover:bg-surface-3">
              <span className="min-w-0 flex-1">
                <span className="block truncate text-txt">{x.nom}
                  {x.annee_creation != null && <span className="text-txt-dim"> · depuis {x.annee_creation}</span>}</span>
                {/* F2 — fraîcheur DÉCLARATIVE par établissement + alerte au-delà du seuil (backend). */}
                <span className="block text-[9.5px] text-txt-dim">
                  déclaré actif{majFr(x.date_maj) ? ` · mis à jour ${majFr(x.date_maj)}` : ''}
                  {x.maj_ancienne && <span className="text-cp-amber"> · registre ancien — vérifier sur place</span>}
                </span>
              </span>
              <span className="shrink-0 font-mono text-[11px] text-txt-hi">{tempsTxt(x.temps_min, res.mode)}</span>
            </button>
          ))}
          {c!.items.length > 8 && <span className="text-[10.5px] text-txt-dim">+ {c!.items.length - 8} autres…</span>}
        </div>
      ))}
      {/* F1 — MILLÉSIME toujours affiché (fraîcheur de la source) + pourquoi certains noms manquent. */}
      {cov === 'servie' && (
        <p className="mt-1 text-[9.5px] leading-snug text-txt-dim">
          Source {c!.millesime || 'SIRENE (INSEE)'}. Une fermeture très récente peut ne pas encore y figurer.
          {c!.items.some((x) => !x.diffusible) && ' Certains noms sont masqués à la demande de l’établissement (diffusion INSEE restreinte).'}
        </p>
      )}
    </div>
  )
}

// F3 (OUTILS-4) — « Toutes les entreprises de la zone » : structure économique lisible d'un coup d'œil
// (familles + comptes exacts), dépliable pour creuser. Familles/comptes servis par le backend (source
// unique naf_nomenclature) — rien en dur ici.
function ToutesEntreprises({ total, open, setOpen, data, loading, error }: {
  total: number; open: boolean; setOpen: (v: boolean) => void
  data?: ZoneEntreprises; loading: boolean; error: boolean
}) {
  const { setView, select } = useApp()
  const [ouvertes, setOuvertes] = useState<Set<string>>(new Set())
  const ouvrirParcelle = async (lon: number, lat: number) => {
    try { const { idu } = await parcelAt(lon, lat); if (idu) { setView('cartes'); select(idu) } } catch { /* rien */ }
  }
  const toggleFam = (s: string) => setOuvertes((prev) => { const n = new Set(prev); if (n.has(s)) n.delete(s); else n.add(s); return n })
  return (
    <div>
      <button data-zone-entreprises-toggle onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between gap-2 rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-left text-[12px] transition-colors duration-quick hover:border-mint/40">
        <span className="text-txt">Toutes les entreprises de la zone <b className="text-txt-hi">({nb(total)})</b></span>
        <span className="text-mint">{open ? '▾' : '▸'}</span>
      </button>
      {open && (
        <div className="mt-1.5 flex flex-col gap-1">
          {loading && <p className="text-[11px] text-txt-mut">Chargement des entreprises…</p>}
          {error && <p className="text-[11px] text-st-ecartee">Indisponible — réessayez.</p>}
          {data?.familles.map((f) => (
            <div key={f.section} className="overflow-hidden rounded-md border border-line-2 bg-surface-1">
              <button data-zone-famille={f.section} onClick={() => toggleFam(f.section)}
                className="flex w-full items-center justify-between gap-2 px-2.5 py-1.5 text-left text-[11.5px] hover:bg-surface-2">
                <span className="min-w-0 truncate text-txt">{f.nom}</span>
                <span className="shrink-0 font-mono text-[11px] text-txt-hi">{nb(f.n)} <span className="text-txt-dim">{ouvertes.has(f.section) ? '▾' : '▸'}</span></span>
              </button>
              {ouvertes.has(f.section) && (
                <div className="flex flex-col gap-0.5 border-t border-line-2 px-2 py-1">
                  {f.etablissements.map((e) => (
                    <button key={e.siret} onClick={() => ouvrirParcelle(e.lon, e.lat)}
                      className="flex items-start rounded px-1 py-0.5 text-left text-[11px] transition-colors duration-quick hover:bg-surface-3">
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-txt">{e.nom}{e.annee_creation != null && <span className="text-txt-dim"> · depuis {e.annee_creation}</span>}</span>
                        <span className="block truncate text-[9px] text-txt-dim">{e.naf_label ?? e.naf}{majFr(e.date_maj) ? ` · maj ${majFr(e.date_maj)}` : ''}</span>
                      </span>
                    </button>
                  ))}
                  {f.n > f.charges && <p className="px-1 text-[9.5px] text-txt-dim">+ {nb(f.n - f.charges)} autres — aperçu plafonné</p>}
                </div>
              )}
            </div>
          ))}
          {data && <p className="mt-0.5 text-[9.5px] leading-snug text-txt-dim">Établissements actifs au registre · Source {data.millesime ?? 'SIRENE (INSEE)'} · pastilles cliquables sur la carte.</p>}
        </div>
      )}
    </div>
  )
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <div className="font-mono text-[9.5px] uppercase tracking-[0.18em] text-txt-dim">{children}</div>
}
function Stat({ v, k, est }: { v: string; k: string; est?: boolean }) {
  return (
    <div className="rounded-lg border border-line-2 bg-surface-2 px-2.5 py-2">
      <div className="flex items-center gap-1.5 text-[13px] font-semibold text-txt-hi">
        <span>{v}</span>
        {est && <span className="rounded bg-mint/12 px-1 py-px font-mono text-[8px] uppercase tracking-wide text-mint">estimé</span>}
      </div>
      <div className="mt-0.5 text-[10px] text-txt-mut">{k}</div>
    </div>
  )
}
