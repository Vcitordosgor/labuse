// M54-EXPO-3 — « Mes veilles » : dessiner une zone (réutilise l'outil `zone` de MapView),
// enregistrer une veille (POST /watch-zones), lister/renommer/supprimer, voir les alertes
// dvf_in_zone (le kind permis a été retiré en EXPO-2 : la cloche le couvre déjà).
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { ackAlerte, createWatchZone, deleteWatchZone, getAlertes, getWatchZones, refreshAlertes, renameWatchZone } from '../../lib/api'
import { fmtInt } from '../../lib/format'
import { useApp } from '../../store/useApp'

export function VeillesPanel() {
  const qc = useQueryClient()
  const { setVeillesOpen, tool, setTool, zone, setZone, commune, select } = useApp()
  const [nom, setNom] = useState('')
  const [renId, setRenId] = useState<number | null>(null)
  const [renVal, setRenVal] = useState('')
  const zones = useQuery({ queryKey: ['watch-zones', commune], queryFn: getWatchZones })
  const alertes = useQuery({ queryKey: ['alertes', commune], queryFn: () => getAlertes(false) })
  const inval = () => { qc.invalidateQueries({ queryKey: ['watch-zones'] }); qc.invalidateQueries({ queryKey: ['alertes'] }) }
  const creer = useMutation({
    mutationFn: () => createWatchZone(nom.trim() || 'Zone de veille',
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
    <aside data-veilles-panel className="absolute right-0 top-0 z-30 flex h-full w-[340px] flex-col overflow-hidden border-l border-line bg-bg">
      <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
        <p className="label-caps">Mes veilles</p>
        <button onClick={() => { setVeillesOpen(false); if (drawing) setTool(null) }} className="text-txt-mut hover:text-txt" aria-label="Fermer">✕</button>
      </div>
      <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-3 text-[12px]">
        {/* CRÉER */}
        <div className="rounded-lg border border-line-2 bg-surface-2 p-3">
          <p className="text-[11px] font-medium text-txt">Nouvelle veille géographique</p>
          <p className="mt-0.5 text-[10.5px] leading-snug text-txt-dim">Dessinez une emprise sur la carte — on vous alerte des <b className="text-txt-mut">ventes DVF</b> qui y tombent.</p>
          {!commune && <p className="mt-1 text-[10.5px] text-st-creuser">Choisissez d’abord une commune (l’outil de dessin est désactivé sur toute l’île).</p>}
          {!zone && (
            <button data-veille-dessiner disabled={!commune} onClick={() => setTool(drawing ? null : 'zone')}
              className={`mt-2 w-full rounded-md border px-3 py-1.5 text-[11px] transition-colors disabled:opacity-40 ${drawing ? 'border-mint bg-mint/10 text-mint' : 'border-line-2 bg-surface-3 text-txt hover:border-mint/50'}`}>
              {drawing ? '✎ Dessin en cours — double-clic pour fermer' : '✎ Dessiner une zone de veille'}
            </button>
          )}
          {zone && (
            <div className="mt-2 flex flex-col gap-1.5">
              <p className="text-[10.5px] text-mint">Zone tracée ({zone.length} points). Nommez-la puis enregistrez.</p>
              <input autoFocus value={nom} onChange={(e) => setNom(e.target.value)} placeholder="Nom de la veille (ex. Centre-bourg)"
                className="w-full rounded-md border border-line-2 bg-surface-3 px-2 py-1.5 text-[12px] text-txt placeholder:text-txt-dim" />
              <div className="flex gap-1.5">
                <button data-veille-save disabled={creer.isPending} onClick={() => creer.mutate()}
                  className="flex-1 rounded-md bg-mint py-1.5 text-[11px] font-medium text-mint-ink hover:brightness-110 disabled:opacity-50">
                  {creer.isPending ? 'Enregistrement…' : 'Enregistrer la veille'}
                </button>
                <button onClick={() => setZone(null)} className="rounded-md border border-line-2 px-3 text-[11px] text-txt-mut hover:text-txt">Annuler</button>
              </div>
            </div>
          )}
          {creer.isSuccess && <p className="mt-1.5 text-[10.5px] text-mint">✓ Veille créée — {creer.data?.detected?.dvf_in_zone ?? 0} vente(s) DVF déjà détectée(s).</p>}
        </div>

        {/* ZONES */}
        <div>
          <p className="label-caps mb-1.5">Zones ({zones.data?.length ?? 0})</p>
          {zones.data && zones.data.length === 0 && <p className="px-1 text-[10.5px] text-txt-dim">Aucune zone pour l’instant.</p>}
          <div className="flex flex-col gap-1">
            {(zones.data ?? []).map((z) => (
              <div key={z.id} data-veille-zone className="rounded-md border border-line-2 bg-surface-3 px-2.5 py-1.5">
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
                    <button data-veille-del onClick={() => del.mutate(z.id)} title="Supprimer" className="shrink-0 text-[11px] text-txt-dim hover:text-st-ecartee">🗑</button>
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
          {alertes.data && alertes.data.length === 0 && <p className="px-1 text-[10.5px] text-txt-dim">Aucune nouveauté — les ventes DVF dans vos zones apparaîtront ici.</p>}
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
    </aside>
  )
}
