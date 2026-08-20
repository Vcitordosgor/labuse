// M104 — LA SECTION « SURVEILLANCE » : fusion Suivis + Secteurs + Critères (arbitrage 17/08/2026).
// Une entrée, trois volets — le mot « veille » est banni du vocabulaire servi (saturé, audit M104).
// LA BOUCLE EST DITE : ce qu'on surveille ici produit des alertes qui arrivent à la cloche et au
// brief du matin (raccordement M104 — plus de tuyau parallèle). Aucune régression : tout ce que
// permettaient les deux anciens panneaux (et l'encart cloche des recherches) reste possible ici.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { ackAlerte, createWatchZone, deleteSearch, deleteWatchZone, getAlertes, getSavedSearches, getSuivis, getWatchZones, refreshAlertes, renameWatchZone, saveSearch, veilleNL } from '../../lib/api'
import { filtersToHash } from '../../lib/filters'
import { fmtInt } from '../../lib/format'
import { EMPTY_FILTERS, useApp } from '../../store/useApp'

const VOLETS = [
  { key: 'parcelles', label: 'Parcelles' },
  { key: 'secteurs', label: 'Secteurs' },
  { key: 'criteres', label: 'Critères' },
] as const

export function SurveillancePanel() {
  const { setSurveillanceOpen, surveillanceVolet, openSurveillance, tool, setTool } = useApp()
  const drawing = tool === 'zone'
  return (
    <aside data-surveillance-panel className="absolute right-0 top-0 z-30 flex h-full w-[360px] flex-col overflow-hidden border-l border-line bg-bg">
      <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
        <p className="label-caps">Veille</p>
        <button onClick={() => { setSurveillanceOpen(false); if (drawing) setTool(null) }} className="text-txt-mut hover:text-txt" aria-label="Fermer">✕</button>
      </div>
      {/* LA BOUCLE, dite — pas devinée : surveiller → alertes → cloche + brief. */}
      <p data-surveillance-boucle className="border-b border-line bg-surface-2 px-4 py-2 text-[10.5px] leading-snug text-txt-mut">
        Ce que vous surveillez ici produit des alertes — elles arrivent <b className="text-txt">à la cloche</b> et
        au <b className="text-txt">brief du matin</b> (et par e-mail selon vos préférences).
      </p>
      <div className="flex shrink-0 gap-1 border-b border-line px-3 py-2">
        {VOLETS.map((v) => (
          <button key={v.key} data-volet={v.key} onClick={() => openSurveillance(v.key)}
            className={`rounded-full px-3 py-1 text-[11px] transition-colors duration-quick ${
              surveillanceVolet === v.key ? 'bg-mint/15 text-mint' : 'text-txt-mut hover:text-txt'}`}>
            {v.label}
          </button>
        ))}
      </div>
      <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-3 text-[12px]">
        {surveillanceVolet === 'parcelles' && <VoletParcelles />}
        {surveillanceVolet === 'secteurs' && <VoletSecteurs />}
        {surveillanceVolet === 'criteres' && <VoletCriteres />}
      </div>
    </aside>
  )
}

// ── Volet PARCELLES (ex-SuivisPanel M85-B, contenu inchangé — aucune régression) ──
function VoletParcelles() {
  const { select, setView, setSurveillanceOpen } = useApp()
  const q = useQuery({ queryKey: ['suivis'], queryFn: getSuivis })
  const suivis = q.data?.suivis ?? []
  const plafond = q.data?.plafond ?? 50
  return (
    <div data-volet-parcelles>
      <p className="label-caps mb-1.5">Parcelles suivies <span className="text-txt-dim">· {suivis.length}/{plafond}</span></p>
      {suivis.length === 0 && (
        <p className="p-1 text-[11.5px] leading-snug text-txt-dim">
          Aucune parcelle suivie. Ouvrez une fiche et cliquez sur la <b className="text-txt">cloche « Suivre »</b> —
          vous serez prévenu dès qu'elle change : vente, permis, procédure, zonage, classement.
        </p>
      )}
      {suivis.map((s) => (
        <button key={s.idu} data-suivi onClick={() => { setView('cartes'); select(s.idu); setSurveillanceOpen(false) }}
          className="mb-1 flex w-full flex-col items-start rounded-lg border border-line-2 px-3 py-2 text-left transition-colors duration-quick hover:border-mint/40">
          <span className="text-xs font-medium text-txt">
            {s.commune ?? 'Parcelle'} <span className="font-mono text-[10px] text-txt-dim">{s.idu.slice(8)}</span>
          </span>
          <span className="mt-0.5 text-[10.5px] text-txt-dim">
            {s.dernier_changement
              ? <>Dernier changement : <b className="text-txt-mut">{new Date(s.dernier_changement).toLocaleDateString('fr-FR')}</b></>
              : 'Aucun changement détecté depuis le suivi.'}
          </span>
        </button>
      ))}
    </div>
  )
}

// ── Volet SECTEURS (ex-VeillesPanel M54-EXPO-3) — vocabulaire ALIGNÉ (« secteur », plus
// jamais « veille ») ; alertes : ventes DVF + permis + BODACC + zonage (M104). ──
function VoletSecteurs() {
  const qc = useQueryClient()
  const { tool, setTool, zone, setZone, commune, select } = useApp()
  const [nom, setNom] = useState('')
  const [renId, setRenId] = useState<number | null>(null)
  const [renVal, setRenVal] = useState('')
  const zones = useQuery({ queryKey: ['watch-zones', commune], queryFn: getWatchZones })
  const alertes = useQuery({ queryKey: ['alertes', commune], queryFn: () => getAlertes(false) })
  const inval = () => { qc.invalidateQueries({ queryKey: ['watch-zones'] }); qc.invalidateQueries({ queryKey: ['alertes'] }) }
  const creer = useMutation({
    mutationFn: () => createWatchZone(nom.trim() || 'Secteur surveillé',
      { type: 'Polygon', coordinates: [[...zone!, zone![0]]] }),
    onSuccess: () => { setZone(null); setNom(''); inval() },
  })
  const ren = useMutation({ mutationFn: () => renameWatchZone(renId!, renVal.trim()), onSuccess: () => { setRenId(null); inval() } })
  const del = useMutation({ mutationFn: (id: number) => deleteWatchZone(id), onSuccess: inval })
  const refr = useMutation({ mutationFn: () => refreshAlertes(), onSuccess: inval })
  const ack = useMutation({ mutationFn: (id?: number) => ackAlerte(id), onSuccess: inval })
  const drawing = tool === 'zone'
  const nonLues = (alertes.data ?? []).filter((a) => !a.acknowledged)
  return (
    <div data-volet-secteurs className="flex flex-col gap-3">
      {/* CRÉER */}
      <div className="rounded-lg border border-line-2 bg-surface-2 p-3">
        <p className="text-[11px] font-medium text-txt">Nouveau secteur surveillé</p>
        <p className="mt-0.5 text-[10.5px] leading-snug text-txt-dim">Dessinez une emprise sur la carte — on vous alerte des <b className="text-txt-mut">ventes, permis, procédures BODACC et changements de zonage</b> qui y surviennent.</p>
        {!commune && <p className="mt-1 text-[10.5px] text-st-creuser">Choisissez d’abord une commune (l’outil de dessin est désactivé sur toute l’île).</p>}
        {!zone && (
          <button data-secteur-dessiner disabled={!commune} onClick={() => setTool(drawing ? null : 'zone')}
            className={`mt-2 w-full rounded-md border px-3 py-1.5 text-[11px] transition-colors disabled:opacity-40 ${drawing ? 'border-mint bg-mint/10 text-mint' : 'border-line-2 bg-surface-3 text-txt hover:border-mint/50'}`}>
            {drawing ? '✎ Dessin en cours — double-clic pour fermer' : '✎ Dessiner un secteur'}
          </button>
        )}
        {zone && (
          <div className="mt-2 flex flex-col gap-1.5">
            <p className="text-[10.5px] text-mint">Secteur tracé ({zone.length} points). Nommez-le puis enregistrez.</p>
            <input autoFocus value={nom} onChange={(e) => setNom(e.target.value)} placeholder="Nom du secteur (ex. Centre-bourg)"
              className="w-full rounded-md border border-line-2 bg-surface-3 px-2 py-1.5 text-[12px] text-txt placeholder:text-txt-dim" />
            <div className="flex gap-1.5">
              <button data-secteur-save disabled={creer.isPending} onClick={() => creer.mutate()}
                className="flex-1 rounded-md bg-mint py-1.5 text-[11px] font-medium text-mint-ink hover:brightness-110 disabled:opacity-50">
                {creer.isPending ? 'Enregistrement…' : 'Enregistrer le secteur'}
              </button>
              <button onClick={() => setZone(null)} className="rounded-md border border-line-2 px-3 text-[11px] text-txt-mut hover:text-txt">Annuler</button>
            </div>
          </div>
        )}
        {creer.isSuccess && <p className="mt-1.5 text-[10.5px] text-mint">✓ Secteur créé — {creer.data?.detected?.dvf_in_zone ?? 0} vente(s) DVF déjà au dossier (l'historique reste ici : seuls les faits nouveaux notifient).</p>}
      </div>

      {/* SECTEURS */}
      <div>
        <p className="label-caps mb-1.5">Secteurs ({zones.data?.length ?? 0})</p>
        {zones.data && zones.data.length === 0 && <p className="px-1 text-[10.5px] text-txt-dim">Aucun secteur pour l’instant.</p>}
        <div className="flex flex-col gap-1">
          {(zones.data ?? []).map((z) => (
            <div key={z.id} data-secteur-zone className="rounded-md border border-line-2 bg-surface-3 px-2.5 py-1.5">
              {renId === z.id ? (
                <div className="flex gap-1">
                  <input autoFocus value={renVal} onChange={(e) => setRenVal(e.target.value)}
                    className="min-w-0 flex-1 rounded border border-line-2 bg-surface-2 px-1.5 py-0.5 text-[11px] text-txt" />
                  <button onClick={() => ren.mutate()} className="text-[11px] text-mint">✓</button>
                  <button onClick={() => setRenId(null)} className="text-[11px] text-txt-dim">✕</button>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <span className="min-w-0 flex-1 truncate text-[12px] text-txt">{z.name}</span>
                  {z.n_alertes > 0 && <span className="shrink-0 rounded-full bg-mint/15 px-1.5 text-[9.5px] text-mint">{z.n_alertes}</span>}
                  <button onClick={() => { setRenId(z.id); setRenVal(z.name) }} title="Renommer" className="shrink-0 text-[11px] text-txt-dim hover:text-txt">✎</button>
                  <button data-secteur-del onClick={() => del.mutate(z.id)} title="Supprimer" className="shrink-0 text-[11px] text-txt-dim hover:text-st-ecartee">🗑</button>
                </div>
              )}
              {z.area_m2 != null && <p className="mt-0.5 text-[9.5px] text-txt-dim">{fmtInt(z.area_m2)} m²</p>}
            </div>
          ))}
        </div>
      </div>

      {/* ALERTES */}
      <div>
        <div className="mb-1.5 flex items-center gap-2">
          <p className="label-caps">Nouveautés{nonLues.length ? ` · ${nonLues.length}` : ''}</p>
          <button data-alertes-refresh onClick={() => refr.mutate()} disabled={refr.isPending} className="text-[10.5px] text-mint hover:underline disabled:opacity-50">{refr.isPending ? '…' : 'Rafraîchir'}</button>
          {nonLues.length > 0 && <button onClick={() => ack.mutate(undefined)} className="ml-auto text-[10.5px] text-txt-mut hover:text-txt">tout marquer lu</button>}
        </div>
        {alertes.data && alertes.data.length === 0 && <p className="px-1 text-[10.5px] text-txt-dim">Aucune nouveauté — ventes, permis, procédures et zonage de vos secteurs apparaîtront ici.</p>}
        <div className="flex flex-col gap-1">
          {(alertes.data ?? []).map((a) => (
            <div key={a.id} data-alerte className={`rounded-md border px-2.5 py-1.5 ${a.acknowledged ? 'border-line-2 opacity-55' : 'border-mint/30 bg-mint/[0.05]'}`}>
              <div className="flex items-start gap-2">
                <button onClick={() => a.parcel_idu && select(a.parcel_idu)} className="min-w-0 flex-1 text-left text-[11.5px] text-txt hover:text-txt-hi">{a.label}</button>
                {!a.acknowledged && <button onClick={() => ack.mutate(a.id)} title="Marquer lu" className="shrink-0 text-[11px] text-txt-dim hover:text-mint">✓</button>}
              </div>
              <p className="mt-0.5 font-mono text-[9px] text-txt-dim">{(a.detected_at || '').slice(0, 10)}{a.zone_name ? ` · ${a.zone_name}` : ''}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Volet CRITÈRES (l'ex-encart cloche « Vos veilles — alertes sur mesure », déménagé M104) :
// recherches sauvegardées — à la bascule d'une parcelle qui matche, une alerte part. ──
function VoletCriteres() {
  const qc = useQueryClient()
  const { filters, zone, setFilters } = useApp()
  const [nomCritere, setNomCritere] = useState('')
  const [nlText, setNlText] = useState('')
  const [nlResume, setNlResume] = useState<string | null>(null)
  const [nlRefus, setNlRefus] = useState<string | null>(null)
  const criteres = useQuery({ queryKey: ['searches'], queryFn: getSavedSearches })
  const add = useMutation({ mutationFn: () => saveSearch(nomCritere, filtersToHash(filters, zone) || '#f=1'),
    onSuccess: () => { setNomCritere(''); qc.invalidateQueries({ queryKey: ['searches'] }) } })
  const del = useMutation({ mutationFn: deleteSearch, onSuccess: () => qc.invalidateQueries({ queryKey: ['searches'] }) })
  const nl = useMutation({
    mutationFn: () => veilleNL(nlText),
    onSuccess: (r) => {
      if (r.ok && r.filters) {
        setFilters({ ...EMPTY_FILTERS, ...(r.filters as Partial<typeof EMPTY_FILTERS>) })
        setNomCritere(nlText.trim().slice(0, 80))
        setNlResume(r.resume ?? null); setNlRefus(null)
      } else {
        setNlRefus(r.refus ?? 'Critère non déclenchable.'); setNlResume(null)
      }
    },
  })
  return (
    <div data-volet-criteres>
      <p className="label-caps">Critères enregistrés</p>
      <p className="mt-0.5 text-[10.5px] leading-snug text-txt-dim">Enregistrez une recherche : on vous alerte dès qu'une parcelle <b>bascule</b> et correspond à vos critères.</p>
      <div className="mt-2 flex gap-1.5">
        <input data-nl-critere value={nlText}
          onChange={(e) => { setNlText(e.target.value); setNlRefus(null) }}
          onKeyDown={(e) => { if (e.key === 'Enter' && nlText.trim().length >= 3) nl.mutate() }}
          placeholder="Décrivez : « les grandes parcelles à Saint-Paul qui deviennent chaudes »"
          className="min-w-0 flex-1 rounded border border-line-2 bg-surface-3 px-2 py-1 text-[11px] text-txt focus:border-mint focus:outline-none" />
        <button data-nl-go onClick={() => nlText.trim().length >= 3 && nl.mutate()} disabled={nlText.trim().length < 3 || nl.isPending}
          className="shrink-0 rounded border border-mint/50 px-2 text-[11px] text-mint transition-colors duration-quick hover:bg-mint/10 disabled:opacity-40">
          {nl.isPending ? '…' : 'Traduire'}</button>
      </div>
      {nlResume && (
        <p data-nl-resume className="mt-1 rounded-md border border-mint/40 bg-mint/[0.07] px-2 py-1 text-[10.5px] leading-snug text-mint">
          ✓ {nlResume} <span className="text-txt-dim">— vérifiez/ajustez les filtres, puis « + Critère ».</span>
        </p>
      )}
      {nlRefus && (
        <p data-nl-refus className="mt-1 rounded-md border border-st-creuser/40 bg-st-creuser/10 px-2 py-1 text-[10.5px] leading-snug text-st-creuser">{nlRefus}</p>
      )}
      {(criteres.data ?? []).map((v) => (
        <div key={v.id} className="mt-1.5 flex items-center gap-2 text-[11px]">
          <a href={'/socle/' + v.hash} className="min-w-0 flex-1 truncate text-txt hover:text-mint" title={v.hash}>{v.nom}</a>
          <button onClick={() => del.mutate(v.id)} aria-label="Supprimer le critère"
            className="flex h-5 w-5 items-center justify-center rounded-full text-txt-dim transition-colors duration-quick hover:bg-surface-3 hover:text-st-ecartee">×</button>
        </div>
      ))}
      {/* exemples = déclencheurs RÉELS uniquement (M16-B4, inchangé) */}
      <div className="mt-2 flex flex-wrap items-center gap-1">
        <span className="text-[10px] text-txt-dim">Suivre, par exemple :</span>
        <button data-critere-ex onClick={() => { setFilters({ ...EMPTY_FILTERS, tiers: ['chaude'] }); setNomCritere('Parcelles qui basculent en chaude') }}
          className="rounded-full border border-line-2 px-2 py-0.5 text-[10px] text-txt-mut transition-colors duration-quick hover:border-mint hover:text-mint">parcelles qui deviennent chaudes</button>
        <button data-critere-ex onClick={() => { setFilters({ ...EMPTY_FILTERS, evenement: true }); setNomCritere('Nouvelles procédures BODACC') }}
          className="rounded-full border border-line-2 px-2 py-0.5 text-[10px] text-txt-mut transition-colors duration-quick hover:border-mint hover:text-mint">nouvelle procédure BODACC</button>
      </div>
      <div className="mt-1.5 flex gap-1.5">
        <input value={nomCritere} onChange={(e) => setNomCritere(e.target.value)} placeholder="Nommez ce critère…"
          className="min-w-0 flex-1 rounded border border-line-2 bg-surface-3 px-2 py-1 text-[11px] text-txt focus:border-mint focus:outline-none" />
        <button onClick={() => nomCritere.trim() && add.mutate()} disabled={!nomCritere.trim()}
          className="rounded bg-mint px-2 text-[11px] font-medium text-mint-ink transition-[filter] duration-quick hover:brightness-110 disabled:opacity-40">+ Critère</button>
      </div>
    </div>
  )
}
