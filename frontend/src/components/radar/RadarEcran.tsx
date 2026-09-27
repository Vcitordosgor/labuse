// RADAR-2 (Lot 2 + Lot 3) — L'ÉCRAN RADAR : liste des biens en vente (560 px, à gauche) + le marché
// (colonne de droite). PLUS DE CARTE, plus de légende ●/○, plus de marqueurs. Doctrine intacte : des
// FAITS et un LIEN, jamais le titre/texte/photo de l'annonce. Les appartements ne sont pas listés (ils
// comptent dans les chiffres du marché). Couleurs = tokens (mint/amber), le mauve reste réservé à l'IA.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import {
  creerRadarVeille, getRadarAlertes, getRadarBiens, radarClic,
  type RadarAlerte, type RadarBienClient, type RadarFiltres,
} from '../../lib/api'
import { CP_COMMUNES } from '../panel/FiltreLabuse'
import { trierCommunes } from '../../lib/communes'
import { useApp } from '../../store/useApp'
import { Squelette } from '../Loading'
import { EmptyState, ErrorState } from '../States'
import { Bouton } from '../ui/Bouton'
import { Retour } from '../ui/Retour'
import { RadarMarcheColonne } from './RadarMarcheColonne'

const COMMUNES_24 = trierCommunes(CP_COMMUNES.map(([, nom]) => nom), (n) => n)
const TYPES = [['', 'Tous'], ['terrain', 'Terrain'], ['maison', 'Maison']] as const
const VENDEURS = [['', 'Tous'], ['particulier', 'Particulier'], ['pro', 'Pro']] as const
const TRIS = [['recentes', 'Plus récentes'], ['prix_asc', 'Prix croissant'], ['prix_desc', 'Prix décroissant'],
  ['anciennete', 'Ancienneté'], ['baisses', 'Baisses']] as const

const fmtEur = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('fr-FR') + ' €')

function joursDepuis(iso: string | null): number | null {
  if (!iso) return null
  const d = new Date(iso).getTime()
  if (Number.isNaN(d)) return null
  return Math.max(0, Math.floor((Date.now() - d) / 86_400_000))
}

// specs du corps de la carte (« 4 pièces · 108 m² hab · 640 m² de terrain · 3 380 €/m² »)
function specsBien(b: RadarBienClient): string {
  const p: string[] = []
  if (b.faits.pieces) p.push(`${b.faits.pieces} pièce${b.faits.pieces > 1 ? 's' : ''}`)
  if (b.faits.surface_hab) p.push(`${b.faits.surface_hab} m² hab`)
  if (b.faits.surface_terrain) p.push(`${b.faits.surface_terrain} m² de terrain`)
  // €/m² : habitable pour le bâti, terrain pour un terrain (comme le marché)
  const surf = b.type_bien === 'terrain' ? b.faits.surface_terrain : (b.faits.surface_hab || b.faits.surface_terrain)
  if (b.faits.prix && surf) p.push(`${Math.round(b.faits.prix / surf).toLocaleString('fr-FR')} €/m²`)
  return p.join(' · ') || '—'
}

// ── une carte de bien dans la liste ──
function CarteBien({ b }: { b: RadarBienClient }) {
  const j = joursDepuis(b.date_publication || b.date_saisie)
  const nouveau = j != null && j < 2
  const vendeur = b.faits.particulier_pro === 'pro' ? 'Pro' : b.faits.particulier_pro === 'particulier' ? 'Particulier' : b.portail
  const ouvrir = () => { radarClic(b.bien_id, b.annonce_id).catch(() => {}); window.open(b.url_sortante, '_blank', 'noopener,noreferrer') }
  return (
    <div data-radar-bien={b.bien_id} className="rounded-lg border border-line-2 bg-surface-2 px-4 py-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 font-mono text-[11px] tracking-[0.04em]">
          <span className="font-bold text-mint">{(b.type_bien ?? '—').toUpperCase()}</span>
          <span className="text-txt-mut"> · {b.commune}{b.quartier ? ` · ${b.quartier}` : ''}</span>
        </div>
        <div className="shrink-0 whitespace-nowrap text-[16.5px] font-bold tabular-nums text-txt-hi">{fmtEur(b.faits.prix)}</div>
      </div>
      <div className="mt-1.5 text-[12.5px] leading-snug text-txt-mut">{specsBien(b)}</div>
      <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
        {nouveau && <span className="rounded-full bg-mint/12 px-2 py-0.5 text-[10.5px] font-medium text-mint">Nouveau</span>}
        {b.baisse && b.baisse_pct != null && (
          <span className="rounded-full bg-mint/12 px-2 py-0.5 text-[10.5px] font-medium text-mint">
            Baisse −{b.baisse_pct} %{b.ancien_prix != null && <span className="ml-1 text-txt-dim line-through">{fmtEur(b.ancien_prix)}</span>}
          </span>
        )}
        {j != null && j > 90 && <span className="rounded-full bg-amber/12 px-2 py-0.5 text-[10.5px] font-medium text-amber">En vente depuis {j} j</span>}
        {b.de_retour && <span className="rounded-full bg-amber/12 px-2 py-0.5 text-[10.5px] font-medium text-amber">De retour</span>}
        <a onClick={(e) => { e.preventDefault(); ouvrir() }} href={b.url_sortante} target="_blank" rel="noopener noreferrer"
          data-radar-portail className="ml-auto text-[12px] font-medium text-[#E7B008] underline decoration-[#E7B008]/40 underline-offset-2 hover:decoration-[#E7B008]">
          Voir l’annonce ↗
        </a>
      </div>
      <div className="mt-1 text-right text-[11px] text-txt-dim">{vendeur}{j != null ? ` · ${j} j` : ''}</div>
    </div>
  )
}

// résumé des critères d'une alerte (pour la liste « Mes alertes »)
function resumeAlerte(a: RadarAlerte): string {
  const c = a.criteria as Record<string, unknown>
  const bouts: string[] = []
  const communes = Array.isArray(c.communes) ? (c.communes as string[]) : []
  if (communes.length) bouts.push(communes.join(' · '))
  else if (a.commune) bouts.push(String(a.commune))
  if (c.type_bien) bouts.push(String(c.type_bien))
  if (c.surface_min) bouts.push(`≥ ${Number(c.surface_min)} m²`)
  if (c.prix_max) bouts.push(`≤ ${Number(c.prix_max).toLocaleString('fr-FR')} €`)
  if (c.particulier_only) bouts.push('particulier')
  return bouts.length ? bouts.join(' · ') : 'Tous les biens'
}

export function RadarEcran() {
  const setRadarEcran = useApp((s) => s.setRadarEcran)
  const radarPrefill = useApp((s) => s.radarPrefill)
  const setRadarPrefill = useApp((s) => s.setRadarPrefill)
  const qc = useQueryClient()
  const [f, setF] = useState<RadarFiltres>({})
  const [tri, setTri] = useState('recentes')
  const [plus, setPlus] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)

  // « Voir dans Radar » (depuis une alerte) : les critères de l'alerte arment la liste au montage.
  useEffect(() => {
    if (radarPrefill) { setF(radarPrefill as RadarFiltres); setRadarPrefill(null) }
    // montage seul : le store pose le prefill juste avant d'ouvrir l'écran.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ['radar-biens', f, tri], queryFn: () => getRadarBiens(f, tri) })
  const biens = useMemo(() => data?.biens ?? [], [data])
  const alertesQ = useQuery({ queryKey: ['radar-alertes'], queryFn: getRadarAlertes })
  const alertes = alertesQ.data?.alertes ?? []

  // « M'alerter sur ces critères » — crée une alerte à partir des filtres du moment.
  const alerter = useMutation({
    mutationFn: () => creerRadarVeille({
      commune: f.commune || undefined,
      type_bien: f.type_bien || undefined,
      prix_max: f.prix_max ?? undefined,
      prix_min: f.prix_min ?? undefined,
      surface_min: f.surface_terrain_min ?? undefined,
      particulier_only: f.particulier_pro === 'particulier' || undefined,
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['radar-alertes'] }); qc.invalidateQueries({ queryKey: ['radar-apercu'] }); setMsg('✓ Alerte créée — visible dans « Mes alertes ».') },
    onError: () => setMsg('Impossible de créer l’alerte.'),
  })

  const setNum = (k: keyof RadarFiltres, v: string) => setF((p) => ({ ...p, [k]: v === '' ? undefined : Number(v) }))
  const nTotal = data?.n_total ?? 0
  const selInput = 'h-8 rounded-md border border-line-2 bg-surface-1 px-2.5 text-[12.5px] text-txt focus:border-mint focus:outline-none'

  return (
    <div className="flex min-h-0 flex-1 overflow-hidden">
      {/* ── LISTE (560 px) ── */}
      <aside data-radar-panel className="flex w-[560px] shrink-0 flex-col overflow-hidden border-r border-line bg-surface-1">
        <div className="shrink-0 border-b border-line-2 px-6 pb-4 pt-5">
          <Retour label="Radar" data-radar-retour onClick={() => setRadarEcran('portes')} className="mb-3" />
          <div className="font-mono text-[10.5px] tracking-[0.2em] text-txt-mut">RADAR</div>
          <h1 className="mt-1 text-[22px] font-semibold text-txt-hi">Les biens en vente</h1>
          <p className="mt-1 text-[12.5px] leading-snug text-txt-mut">Repérés sur les portails. Des faits et un lien, jamais le contenu de l’annonce.</p>
        </div>

        {/* filtres */}
        <div className="shrink-0 border-b border-line-2 px-6 py-3.5">
          <div className="flex flex-wrap items-center gap-2">
            <select data-radar-commune value={f.commune ?? ''} onChange={(e) => setF((p) => ({ ...p, commune: e.target.value || undefined }))} className={`${selInput} min-w-[150px] flex-1`}>
              <option value="">Toutes les communes</option>
              {COMMUNES_24.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
            <input type="number" min={0} placeholder="Prix max" value={f.prix_max ?? ''} onChange={(e) => setNum('prix_max', e.target.value)} className={`${selInput} w-[110px]`} />
            <input type="number" min={0} placeholder="Surface min" value={f.surface_terrain_min ?? ''} onChange={(e) => setNum('surface_terrain_min', e.target.value)} className={`${selInput} w-[110px]`} />
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <Segment label="Type" value={f.type_bien ?? ''} onChange={(v) => setF((p) => ({ ...p, type_bien: v || undefined }))} options={TYPES} data="radar-type" />
            <Segment label="Vendeur" value={f.particulier_pro ?? ''} onChange={(v) => setF((p) => ({ ...p, particulier_pro: (v || undefined) as RadarFiltres['particulier_pro'] }))} options={VENDEURS} data="radar-vendeur" />
            <button data-radar-plus onClick={() => setPlus((v) => !v)} className={`h-8 rounded-md border px-3 text-[12px] transition-colors duration-quick ${plus ? 'border-mint text-mint' : 'border-line-2 text-txt hover:border-mint/50'}`}>Plus de filtres</button>
          </div>
          {plus && (
            <div className="mt-2 grid grid-cols-2 gap-2 rounded-md border border-line-2 bg-surface-2 p-2.5">
              <input type="number" min={0} placeholder="Prix min" value={f.prix_min ?? ''} onChange={(e) => setNum('prix_min', e.target.value)} className={`min-w-0 ${selInput}`} />
              <input type="number" min={0} placeholder="Surface max" value={f.surface_terrain_max ?? ''} onChange={(e) => setNum('surface_terrain_max', e.target.value)} className={`min-w-0 ${selInput}`} />
            </div>
          )}
          <div className="mt-2.5 flex items-center gap-2">
            <Bouton niveau="secondaire" ton="vert" data-radar-alerter disabled={alerter.isPending} onClick={() => alerter.mutate()}>
              <span className="inline-flex items-center gap-1.5">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinejoin="round"><path d="M6 9a6 6 0 0 1 12 0c0 5 2 6 2 6H4s2-1 2-6z" /><path d="M10 20a2 2 0 0 0 4 0" strokeLinecap="round" /></svg>
                M’alerter sur ces critères
              </span>
            </Bouton>
          </div>
          {msg && <p className="mt-1.5 text-[10.5px] text-txt-mut">{msg}</p>}
        </div>

        {/* compteur + tri */}
        <div className="flex shrink-0 items-center justify-between border-b border-line-2 px-6 py-3">
          <div className="text-[12.5px] text-txt-mut"><b className="text-[14px] font-semibold text-txt-hi">{nTotal}</b> bien{nTotal > 1 ? 's' : ''}</div>
          <select value={tri} onChange={(e) => setTri(e.target.value)} className="h-8 rounded-md border border-line-2 bg-surface-1 px-2.5 text-[12px] text-txt focus:border-mint focus:outline-none">
            {TRIS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>

        {/* liste */}
        <div className="flex min-h-0 flex-1 flex-col gap-2.5 overflow-y-auto px-4 py-3">
          {isLoading && <Squelette lignes={6} className="py-6" />}
          {isError && <ErrorState message="Les biens n’ont pas pu être chargés — le serveur n’a pas répondu." retry={() => refetch()} />}
          {!isLoading && !isError && biens.length === 0 && (
            <EmptyState title="Aucun bien ne correspond à ces filtres." hint="Élargissez la recherche." />
          )}
          {biens.map((b) => <CarteBien key={b.bien_id} b={b} />)}
        </div>

        {/* Mes alertes · N */}
        <div className="shrink-0 border-t border-line-2 bg-surface-2 px-6 py-3">
          <div className="mb-2 flex items-center justify-between">
            <span className="label-caps">Mes alertes <span className="text-txt-dim">· {alertes.length}</span></span>
            <button data-radar-gerer-alertes onClick={() => setRadarEcran('veille-annonces')} className="text-[11.5px] font-medium text-mint hover:underline">Gérer dans Veille</button>
          </div>
          {alertes.length === 0 ? (
            <p className="text-[11px] text-txt-dim">Aucune alerte. Réglez des filtres puis « M’alerter sur ces critères ».</p>
          ) : (
            <div className="flex flex-col gap-1.5">
              {alertes.slice(0, 4).map((a) => (
                <div key={a.id} data-radar-alerte className="flex items-center justify-between gap-2 rounded-md border border-line-2 bg-surface-1 px-3 py-1.5">
                  <span className="min-w-0 truncate text-[11.5px] text-txt">{a.nom || resumeAlerte(a)}</span>
                  <span className={`shrink-0 text-[11px] ${a.en_pause ? 'text-txt-dim' : a.nouveaux > 0 ? 'text-mint' : 'text-txt-dim'}`}>
                    {a.en_pause ? 'en pause' : a.nouveaux > 0 ? `${a.nouveaux} nouveau${a.nouveaux > 1 ? 'x' : ''}` : 'rien de neuf'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </aside>

      {/* ── LE MARCHÉ (colonne de droite) ── */}
      <RadarMarcheColonne commune={f.commune ?? null} />
    </div>
  )
}

// segment étiqueté (Type / Vendeur) — bascule mint, gabarit maquette
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
