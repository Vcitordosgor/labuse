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
import { useMutation } from '@tanstack/react-query'

import { ParcelInput } from '../ParcelInput'
import { etudeZone, etudeZonePdfUrl, nafSearch, type EtudeZoneInput } from '../../lib/api'
import type { EtudeZoneResult, NafOption } from '../../lib/types'
import { iduCourt } from '../../lib/format'
import { useApp } from '../../store/useApp'

const TEMPS = [5, 10, 15]

function nb(n: number | null | undefined): string {
  return n == null ? '—' : n.toLocaleString('fr-FR')
}
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

  // RELANCER — toute modification d'entrée réarme « Analyser » : on efface le résultat périmé.
  useEffect(() => { mut.reset() /* eslint-disable-next-line react-hooks/exhaustive-deps */ },
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
    for (const c of res.concurrents?.items ?? []) feats.push({ type: 'Feature', geometry: { type: 'Point', coordinates: [c.lon, c.lat] }, properties: { kind: 'zone-concurrent', siret: c.siret } })
    setModuleMap({ idus: [], extra: { type: 'FeatureCollection', features: feats } })
    if (res.origine) setFlyTo({ center: [res.origine.lon, res.origine.lat], zoom: 13 })
  }, [res, setModuleMap, setFlyTo])
  useEffect(() => () => setModuleMap({ idus: [], extra: null }), [setModuleMap])

  const pretA = entree === 'polygone' ? !!geomFromDrawn : !!cible

  const nouvelleEtude = () => {
    setCible(null); setNaf(null); setNafQuery(''); setZone(null); setTool(null)
    setModuleMap({ idus: [], extra: null }); mut.reset()
  }

  const exportPdf = () => {
    if (!res?.zone_disponible) return
    const body: EtudeZoneInput = { minutes, mode, naf: naf?.code ?? null }
    if (entree === 'polygone' && geomFromDrawn) { body.geom = geomFromDrawn; body.titre = 'Zone dessinée' }
    else if (cible) { body.idu = cible.idu; body.titre = cible.label }
    fetch(etudeZonePdfUrl, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      .then(async (r) => { if (!r.ok) return; const b = await r.blob(); const u = URL.createObjectURL(b); window.open(u, '_blank'); setTimeout(() => URL.revokeObjectURL(u), 60_000) })
      .catch(() => {})
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

      {/* ACTIVITÉ (NAF) — commun aux deux entrées */}
      <div className="relative">
        <input value={naf ? naf.label : nafQuery}
          onChange={(e) => { setNaf(null); setNafQuery(e.target.value) }}
          placeholder="Activité étudiée (ex. « boulangerie »)"
          className="w-full rounded-lg border border-line-2 bg-surface-2 px-2.5 py-1.5 text-[12px] text-txt outline-none focus:border-mint/60" />
        {naf && <button onClick={() => { setNaf(null); setNafQuery('') }} className="absolute right-2 top-1.5 text-[11px] text-txt-dim hover:text-txt">×</button>}
        {nafOpts.length > 0 && (
          <div className="absolute z-20 mt-1 max-h-52 w-full overflow-y-auto rounded-lg border border-line-2 bg-surface-1 shadow-lg">
            {nafOpts.map((o) => (
              <button key={o.code} onClick={() => { setNaf(o); setNafOpts([]) }}
                className="flex w-full items-center justify-between gap-2 px-2.5 py-1.5 text-left text-[11.5px] text-txt hover:bg-mint/10">
                <span className="truncate">{o.label}</span><span className="shrink-0 font-mono text-[10px] text-txt-dim">{o.code}</span>
              </button>
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
              <Stat v={res.population?.revenu_median_eur != null ? `${nb(res.population.revenu_median_eur)} €` : '—'} k="revenu médian / an" est />
              <ActifsStat res={res} />
            </div>
          )}

          {/* CONCURRENTS — trois états honnêtes, jamais un faux zéro */}
          {naf && <Concurrents res={res} />}

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

          <div className="flex gap-2">
            <button onClick={exportPdf} className="flex-1 rounded-lg border border-mint/40 px-3 py-1.5 text-[11.5px] font-medium text-mint hover:bg-mint/10">Exporter le PDF ↓</button>
            <button onClick={nouvelleEtude} className="flex-1 rounded-lg border border-line-2 px-3 py-1.5 text-[11.5px] font-medium text-txt-mut hover:border-mint/40 hover:text-txt">Nouvelle étude</button>
          </div>
          {res.note && <p className="text-[9.5px] leading-snug text-txt-dim">{res.note}</p>}
        </div>
      )}
    </div>
  )
}

// « actifs y travaillent » — MOBPRO : non couvert (source vide) dit tel quel, jamais un « — » muet.
function ActifsStat({ res }: { res: EtudeZoneResult }) {
  if (res.emplois_couverture === 'non_couverte') {
    return (
      <div className="rounded-lg border border-line-2 bg-surface-2 px-2.5 py-2">
        <div className="text-[11px] font-medium text-txt-mut">non couvert</div>
        <div className="mt-0.5 text-[10px] text-txt-mut">actifs y travaillent <span className="text-txt-dim">(MOBPRO non ingéré)</span></div>
      </div>
    )
  }
  const total = (res.emplois ?? []).reduce((a, e) => a + e.actifs_lieu_travail, 0)
  return <Stat v={res.emplois && res.emplois.length ? nb(total) : '—'} k="actifs y travaillent" />
}

function Concurrents({ res }: { res: EtudeZoneResult }) {
  const c = res.concurrents
  const cov = c?.couverture
  return (
    <div>
      <SectionTitle>{`Concurrents dans la zone${cov === 'servie' ? ` — ${c!.n}` : ''}`}{cov === 'servie' && res.habitants_par_concurrent != null && <span className="ml-1 font-normal normal-case tracking-normal text-txt-mut">· {nb(res.habitants_par_concurrent)} hab./concurrent</span>}</SectionTitle>
      {cov === 'non_couverte' && (
        <p className="text-[11px] text-txt-mut">Non couvert par la base — le répertoire SIRENE des établissements n’est pas encore ingéré.</p>
      )}
      {cov === 'erreur' && (
        <p className="text-[11px] text-txt-mut">Indisponible — la requête concurrents n’a pas abouti.</p>
      )}
      {cov === 'servie' && (c!.items.length === 0 ? (
        <p className="text-[11px] text-txt-mut">Aucun établissement de cette activité dans la zone <span className="text-txt-dim">(source SIRENE{c!.millesime ? ` · ${c!.millesime}` : ''})</span>.</p>
      ) : (
        <div className="flex flex-col gap-1">
          {c!.items.slice(0, 8).map((x) => (
            <div key={x.siret} className="flex items-center justify-between gap-2 text-[11.5px]">
              <span className="truncate text-txt">{x.nom} <span className="font-mono text-[10px] text-txt-dim">{x.naf}</span></span>
              <span className="shrink-0 font-mono text-[11px] text-txt-hi">{tempsTxt(x.temps_min, res.mode)}</span>
            </div>
          ))}
          {c!.items.length > 8 && <span className="text-[10.5px] text-txt-dim">+ {c!.items.length - 8} autres…</span>}
        </div>
      ))}
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
