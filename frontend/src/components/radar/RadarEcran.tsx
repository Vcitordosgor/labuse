// RADAR-2 (Lot 2/3 + retouches 2) — L'ÉCRAN RADAR : liste des biens en vente (560 px, à gauche) + le
// marché (colonne de droite). PLUS DE CARTE. En-tête léger (Retour + « N biens » + tri), filtres dans un
// accordéon (résumé sur une ligne fermé). PLUS de « M'alerter » ici (créer une alerte se fait dans Veille ·
// les annonces). Cliquer une annonce la sélectionne : un bloc « Ce bien » se glisse EN TÊTE de la colonne
// marché (qui bascule sur la commune de l'annonce) — une seule vue. FAITS et un LIEN, jamais le contenu.
import { useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useRef, useState } from 'react'
import { getRadarBiens, radarClic, type RadarBienClient, type RadarFiltres } from '../../lib/api'
import { CP_COMMUNES } from '../panel/FiltreLabuse'
import { trierCommunes } from '../../lib/communes'
import { useApp } from '../../store/useApp'
import { Squelette } from '../Loading'
import { EmptyState, ErrorState } from '../States'
import { Chevron } from '../ui/Chevron'
import { Retour } from '../ui/Retour'
import { RadarMarcheColonne } from './RadarMarcheColonne'

const COMMUNES_24 = trierCommunes(CP_COMMUNES.map(([, nom]) => nom), (n) => n)
const TYPES = [['', 'Tous'], ['terrain', 'Terrain'], ['maison', 'Maison']] as const
const VENDEURS = [['', 'Tous'], ['particulier', 'Particulier'], ['pro', 'Pro']] as const
const TRIS = [['recentes', 'Plus récentes'], ['prix_asc', 'Prix croissant'], ['prix_desc', 'Prix décroissant'],
  ['anciennete', 'Ancienneté'], ['baisses', 'Baisses']] as const
const TYPE_LABEL: Record<string, string> = { terrain: 'Terrain', maison: 'Maison' }

const fmtEur = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('fr-FR') + ' €')

function joursDepuis(iso: string | null): number | null {
  if (!iso) return null
  const d = new Date(iso).getTime()
  if (Number.isNaN(d)) return null
  return Math.max(0, Math.floor((Date.now() - d) / 86_400_000))
}

function specsBien(b: RadarBienClient): string {
  const p: string[] = []
  if (b.faits.pieces) p.push(`${b.faits.pieces} pièce${b.faits.pieces > 1 ? 's' : ''}`)
  if (b.faits.surface_hab) p.push(`${b.faits.surface_hab} m² hab`)
  if (b.faits.surface_terrain) p.push(`${b.faits.surface_terrain} m² de terrain`)
  const surf = b.type_bien === 'terrain' ? b.faits.surface_terrain : (b.faits.surface_hab || b.faits.surface_terrain)
  if (b.faits.prix && surf) p.push(`${Math.round(b.faits.prix / surf).toLocaleString('fr-FR')} €/m²`)
  return p.join(' · ') || '—'
}

// résumé des filtres actifs, sur une ligne (accordéon fermé)
function resumeFiltres(f: RadarFiltres): string {
  const b: string[] = []
  if (f.commune) b.push(f.commune)
  if (f.type_bien) b.push(TYPE_LABEL[f.type_bien] ?? f.type_bien)
  if (f.particulier_pro) b.push(f.particulier_pro === 'pro' ? 'Pro' : 'Particulier')
  if (f.surface_terrain_min != null) b.push(`≥ ${f.surface_terrain_min} m²`)
  if (f.surface_terrain_max != null) b.push(`≤ ${f.surface_terrain_max} m²`)
  if (f.prix_min != null) b.push(`≥ ${f.prix_min.toLocaleString('fr-FR')} €`)
  if (f.prix_max != null) b.push(`≤ ${f.prix_max.toLocaleString('fr-FR')} €`)
  return b.length ? b.join(' · ') : 'Tous les biens'
}

function CarteBien({ b, sel, onClick, selRef }: {
  b: RadarBienClient; sel: boolean; onClick: () => void; selRef: React.RefObject<HTMLButtonElement>
}) {
  const j = joursDepuis(b.date_publication || b.date_saisie)
  // FRONT-CHIFFRES-2 (F14) — les DÉCISIONS de badge sont servies (le front ne les recalcule plus) :
  // `nouveau` à plat (seuil back SEUIL_NOUVEAU_J), « en vente longue » sur le `statut` du cycle back
  // (seuil SEUIL_VENTE_LONGUE_J). `j` ne sert plus qu'à AFFICHER l'ancienneté (présentation).
  const nouveau = b.nouveau
  const enVenteLongue = b.statut === 'en_vente_longue'
  const vendeur = b.faits.particulier_pro === 'pro' ? 'Pro' : b.faits.particulier_pro === 'particulier' ? 'Particulier' : b.portail
  const ouvrir = () => { radarClic(b.bien_id, b.annonce_id).catch(() => {}); window.open(b.url_sortante, '_blank', 'noopener,noreferrer') }
  // RADAR-FIX-3 — l'annonce ouverte dans « Ce bien » porte l'ÉTAT ACTIF de la charte (fond vert, encre
  // sombre `mint-on`) ; les puces et l'encre secondaire basculent aussi en sombre pour rester lisibles.
  const puce = sel ? 'bg-mint-on/15 text-mint-on' : ''
  return (
    <button ref={sel ? selRef : undefined} data-radar-bien={b.bien_id} data-radar-bien-actif={sel || undefined} onClick={onClick}
      className={`w-full rounded-lg border px-4 py-3 text-left transition-colors duration-quick ${
        sel ? 'border-mint bg-mint text-mint-on' : 'border-line-2 bg-surface-2 hover:border-line-3'}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 font-mono text-[11px] tracking-[0.04em]">
          <span className={`font-bold ${sel ? 'text-mint-on' : 'text-mint'}`}>{(b.type_bien ?? '—').toUpperCase()}</span>
          <span className={sel ? 'text-mint-on/70' : 'text-txt-mut'}> · {b.commune}{b.quartier ? ` · ${b.quartier}` : ''}</span>
        </div>
        <div className={`shrink-0 whitespace-nowrap text-[16.5px] font-bold tabular-nums ${sel ? 'text-mint-on' : 'text-txt-hi'}`}>{fmtEur(b.faits.prix)}</div>
      </div>
      <div className={`mt-1.5 text-[12.5px] leading-snug ${sel ? 'text-mint-on/80' : 'text-txt-mut'}`}>{specsBien(b)}</div>
      <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
        {nouveau && <span className={`rounded-full px-2 py-0.5 text-[10.5px] font-medium ${sel ? puce : 'bg-mint/12 text-mint'}`}>Nouveau</span>}
        {b.baisse && b.baisse_pct != null && (
          <span className={`rounded-full px-2 py-0.5 text-[10.5px] font-medium ${sel ? puce : 'bg-mint/12 text-mint'}`}>
            Baisse −{b.baisse_pct} %{b.ancien_prix != null && <span className={`ml-1 line-through ${sel ? 'text-mint-on/60' : 'text-txt-dim'}`}>{fmtEur(b.ancien_prix)}</span>}
          </span>
        )}
        {enVenteLongue && <span className={`rounded-full px-2 py-0.5 text-[10.5px] font-medium ${sel ? puce : 'bg-amber/12 text-amber'}`}>En vente{j != null ? ` depuis ${j} j` : ' longue'}</span>}
        {b.de_retour && <span className={`rounded-full px-2 py-0.5 text-[10.5px] font-medium ${sel ? puce : 'bg-amber/12 text-amber'}`}>De retour</span>}
        <a onClick={(e) => { e.stopPropagation(); e.preventDefault(); ouvrir() }} href={b.url_sortante} target="_blank" rel="noopener noreferrer"
          data-radar-portail className={`ml-auto text-[12px] font-medium underline underline-offset-2 ${sel ? 'text-mint-on decoration-mint-on/50 hover:decoration-mint-on' : 'text-[#E7B008] decoration-[#E7B008]/40 hover:decoration-[#E7B008]'}`}>
          Voir l’annonce ↗
        </a>
      </div>
      <div className={`mt-1 text-right text-[11px] ${sel ? 'text-mint-on/70' : 'text-txt-dim'}`}>{vendeur}{j != null ? ` · ${j} j` : ''}</div>
    </button>
  )
}

export function RadarEcran() {
  const setRadarEcran = useApp((s) => s.setRadarEcran)
  const radarPrefill = useApp((s) => s.radarPrefill)
  const setRadarPrefill = useApp((s) => s.setRadarPrefill)
  const [f, setF] = useState<RadarFiltres>({})
  const [tri, setTri] = useState('recentes')
  const [filtresOpen, setFiltresOpen] = useState(false)
  const [selBien, setSelBien] = useState<number | null>(null)
  // RADAR-FIX-3 — la liste défile jusqu'à l'annonce ouverte dans « Ce bien » (sélection toujours visible).
  const selRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (radarPrefill) { setF(radarPrefill as RadarFiltres); setRadarPrefill(null) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (selBien != null) selRef.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }, [selBien])

  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ['radar-biens', f, tri], queryFn: () => getRadarBiens(f, tri) })
  const biens = useMemo(() => data?.biens ?? [], [data])

  const setNum = (k: keyof RadarFiltres, v: string) => setF((p) => ({ ...p, [k]: v === '' ? undefined : Number(v) }))
  const nTotal = data?.n_total ?? 0
  const nActifs = [f.commune, f.type_bien, f.particulier_pro, f.prix_min, f.prix_max, f.surface_terrain_min, f.surface_terrain_max].filter((v) => v != null && v !== '').length
  const selInput = 'h-8 rounded-md border border-line-2 bg-surface-1 px-2.5 text-[12.5px] text-txt focus:border-mint focus:outline-none'

  return (
    <div className="flex min-h-0 flex-1 overflow-hidden">
      {/* ── LISTE (560 px) ── */}
      <aside data-radar-panel className="flex w-[560px] shrink-0 flex-col overflow-hidden border-r border-line bg-surface-1">
        {/* en-tête léger : Retour · « N biens » · tri, sur une ligne */}
        <div className="flex shrink-0 items-center gap-3 border-b border-line-2 px-6 py-3.5">
          <Retour label="Radar" data-radar-retour onClick={() => setRadarEcran('portes')} />
          <div className="text-[12.5px] text-txt-mut"><b className="text-[14px] font-semibold text-txt-hi">{nTotal}</b> bien{nTotal > 1 ? 's' : ''}</div>
          <select value={tri} onChange={(e) => setTri(e.target.value)} className="ml-auto h-8 rounded-md border border-line-2 bg-surface-1 px-2.5 text-[12px] text-txt focus:border-mint focus:outline-none">
            {TRIS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>

        {/* accordéon « Filtres » (fermé par défaut, résumé sur une ligne) */}
        <div className="shrink-0 border-b border-line-2 px-6 py-3">
          <button data-radar-filtres-toggle onClick={() => setFiltresOpen((v) => !v)} className="group flex w-full items-center gap-2 text-left">
            <Chevron open={filtresOpen} />
            <span className="text-[12.5px] font-medium text-txt">Filtres</span>
            {nActifs > 0 && <span className="inline-flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-mint px-1 text-[10.5px] font-bold text-mint-on">{nActifs}</span>}
            {!filtresOpen && <span className="ml-1 min-w-0 flex-1 truncate text-[11.5px] text-txt-dim">{resumeFiltres(f)}</span>}
          </button>
          {filtresOpen && (
            <div className="mt-3 flex flex-col gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <select data-radar-commune value={f.commune ?? ''} onChange={(e) => setF((p) => ({ ...p, commune: e.target.value || undefined }))} className={`${selInput} min-w-[150px] flex-1`}>
                  <option value="">Toutes les communes</option>
                  {COMMUNES_24.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
                <input type="number" min={0} placeholder="Prix max" value={f.prix_max ?? ''} onChange={(e) => setNum('prix_max', e.target.value)} className={`${selInput} w-[110px]`} />
                <input type="number" min={0} placeholder="Surface min" value={f.surface_terrain_min ?? ''} onChange={(e) => setNum('surface_terrain_min', e.target.value)} className={`${selInput} w-[110px]`} />
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Segment label="Type" value={f.type_bien ?? ''} onChange={(v) => setF((p) => ({ ...p, type_bien: v || undefined }))} options={TYPES} data="radar-type" />
                <Segment label="Vendeur" value={f.particulier_pro ?? ''} onChange={(v) => setF((p) => ({ ...p, particulier_pro: (v || undefined) as RadarFiltres['particulier_pro'] }))} options={VENDEURS} data="radar-vendeur" />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <input type="number" min={0} placeholder="Prix min" value={f.prix_min ?? ''} onChange={(e) => setNum('prix_min', e.target.value)} className={`min-w-0 ${selInput}`} />
                <input type="number" min={0} placeholder="Surface max" value={f.surface_terrain_max ?? ''} onChange={(e) => setNum('surface_terrain_max', e.target.value)} className={`min-w-0 ${selInput}`} />
              </div>
            </div>
          )}
        </div>

        {/* liste */}
        <div className="flex min-h-0 flex-1 flex-col gap-2.5 overflow-y-auto px-4 py-3">
          {isLoading && <Squelette lignes={6} className="py-6" />}
          {isError && <ErrorState message="Les biens n’ont pas pu être chargés — le serveur n’a pas répondu." retry={() => refetch()} />}
          {!isLoading && !isError && biens.length === 0 && (
            <EmptyState title="Aucun bien ne correspond à ces filtres." hint="Élargissez la recherche." />
          )}
          {biens.map((b) => <CarteBien key={b.bien_id} b={b} sel={selBien === b.bien_id} selRef={selRef} onClick={() => setSelBien((s) => (s === b.bien_id ? null : b.bien_id))} />)}
        </div>
      </aside>

      {/* ── colonne de droite : TOUJOURS le marché (de la commune du filtre, ou de la commune de l'annonce
          sélectionnée) ; quand une annonce est sélectionnée, un bloc « Ce bien » s'insère en tête. ── */}
      <RadarMarcheColonne commune={f.commune ?? null} bienId={selBien} onCloseBien={() => setSelBien(null)} />
    </div>
  )
}

function Segment({ label, value, onChange, options, data }: {
  label: string; value: string; onChange: (v: string) => void; options: readonly (readonly [string, string])[]; data: string
}) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-[11px] text-txt-dim">{label}</span>
      <div data-seg={data} className="flex h-8 overflow-hidden rounded-md border border-line-2">
        {options.map(([v, l], i) => (
          <button key={v || 'tous'} data-seg-opt={v || 'tous'} onClick={() => onChange(v)}
            className={`flex items-center justify-center whitespace-nowrap px-2.5 text-[12px] ${i ? 'border-l border-line-2' : ''} ${value === v ? 'bg-mint/12 font-medium text-mint' : 'text-txt-mut hover:text-txt'}`}>{l}</button>
        ))}
      </div>
    </div>
  )
}
