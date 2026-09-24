import { useEffect, useState } from 'react'
import { modPatrimoine } from '../lib/api'
import { fmtM2, iduCourt } from '../lib/format'

// RECHERCHE-2 Lot 2 — SOUS-PANNEAU PARTAGÉ « propriétaire → ses parcelles ». Quand une barre reçoit
// un pick PROPRIÉTAIRE/SIREN dans un contexte qui part d'une parcelle, on liste ses parcelles (mêmes
// données que Scan patrimoine : /modules/patrimoine, paginées par 200) et on laisse choisir. Le clic
// remonte l'IDU (et le centre géométrique quand la géométrie est servie) — l'appelant décide du geste
// (ParcelInput → onPick ; barres carte → recentrage/sélection). Un seul rendu, partout pareil.
const OWNER_PAGE = 200

type Parcelle = { idu: string; commune: string; surface_m2: number | null; geom?: unknown }

// Centre (bbox) d'une géométrie GeoJSON — pour recentrer une carte sur la parcelle choisie. null si absente.
function centreDeGeom(geom: unknown): { lon: number; lat: number } | null {
  if (!geom || typeof geom !== 'object') return null
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
  const walk = (a: unknown): void => {
    if (Array.isArray(a) && typeof a[0] === 'number') {
      minX = Math.min(minX, a[0] as number); maxX = Math.max(maxX, a[0] as number)
      minY = Math.min(minY, a[1] as number); maxY = Math.max(maxY, a[1] as number)
    } else if (Array.isArray(a)) { a.forEach(walk) }
  }
  walk((geom as { coordinates?: unknown }).coordinates)
  if (!Number.isFinite(minX)) return null
  return { lon: (minX + maxX) / 2, lat: (minY + maxY) / 2 }
}

export function OwnerParcelles({ siren, nom, onPick, onChanger }: {
  siren: string
  nom: string
  onPick: (idu: string, centre: { lon: number; lat: number } | null) => void
  onChanger?: () => void
}) {
  const [parcelles, setParcelles] = useState<Parcelle[]>([])
  const [total, setTotal] = useState(0)
  const [titre, setTitre] = useState(nom)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const charger = async (offset: number) => {
    setErr(null); setBusy(true)
    try {
      const p = await modPatrimoine(siren, OWNER_PAGE, offset) as { nom?: string; n_parcelles?: number; items?: Parcelle[] }
      const items = (p.items ?? []).map((i) => ({ idu: String(i.idu), commune: String(i.commune ?? ''), surface_m2: i.surface_m2 ?? null, geom: i.geom }))
      setTotal(p.n_parcelles ?? items.length)
      setParcelles((prev) => (offset === 0 ? items : [...prev, ...items]))
      if (p.nom) setTitre(p.nom)
      if (offset === 0 && (p.n_parcelles ?? 0) === 0) {
        setErr(`${nom || 'Ce propriétaire'} ne détient aucune parcelle à La Réunion dans les fichiers fonciers (DGFiP).`)
      }
    } catch {
      setErr('Patrimoine indisponible pour le moment — réessayez.')
    } finally { setBusy(false) }
  }

  useEffect(() => { setParcelles([]); setTotal(0); setTitre(nom); void charger(0) }, [siren]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div data-owner-parcelles className="flex flex-col gap-0.5 rounded-md border border-line-2 bg-surface-2 p-1.5">
      <div className="flex items-baseline justify-between gap-2 px-1 pb-0.5">
        <p className="min-w-0 truncate text-[10px] text-txt-dim">
          <span className="font-medium text-txt-hi">{titre}</span>
          {total > 0 && <> — {total} parcelle{total > 1 ? 's' : ''} — choisissez :</>}
        </p>
        {onChanger && (
          <button data-owner-changer onClick={onChanger}
            className="shrink-0 text-[10px] text-mint underline underline-offset-2 hover:text-mint/80">changer</button>
        )}
      </div>
      {err && <p data-owner-msg className="px-1 text-[10.5px] text-st-creuser">{err}</p>}
      {parcelles.map((p) => (
        <button key={p.idu} data-owner-parcelle onClick={() => onPick(p.idu, centreDeGeom(p.geom))}
          className="hover-fill flex items-baseline justify-between gap-2 rounded px-2 py-1 text-left text-[11px] text-txt transition-colors duration-quick">
          <span className="font-medium text-txt-hi">{p.commune}</span>
          <span className="flex items-baseline gap-2 text-[10px] text-txt-dim">
            <span>{fmtM2(p.surface_m2)}</span>
            <span className="font-mono">{iduCourt(p.idu)}</span>
          </span>
        </button>
      ))}
      {busy && <p className="px-2 py-1 text-[10px] text-txt-dim" aria-hidden>…</p>}
      {!busy && parcelles.length < total && (
        <button data-owner-plus onClick={() => void charger(parcelles.length)}
          className="rounded px-2 py-1 text-left text-[10.5px] text-mint hover:underline">
          voir {total - parcelles.length} de plus
        </button>
      )}
    </div>
  )
}
