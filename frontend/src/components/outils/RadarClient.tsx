// RADAR (pige) · P3 C2+C3 — l'écran CLIENT : filtres + carte (rattachés seuls) + listing (tout, avec
// pastille) + fiche d'un bien. LIGNE ROUGE : des FAITS et un LIEN, jamais le titre/texte/photo de
// l'annonce. Le mauve est réservé à l'IA — il n'apparaît nulle part ici. Couleurs = source unique.
import { useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import {
  creerRadarVeille, getRadarBienDetail, getRadarBiens, radarClic, radarSignaler,
  type RadarBienClient, type RadarFiltres,
} from '../../lib/api'
import { useApp } from '../../store/useApp'
import { RadarMarche } from './RadarMarche'

const TYPES = [['', 'Tous types'], ['maison', 'Maison'], ['appartement', 'Appartement'], ['terrain', 'Terrain'], ['immeuble', 'Immeuble']] as const
const TRIS = [['recentes', 'Plus récentes'], ['prix_asc', 'Prix ↑'], ['prix_desc', 'Prix ↓'], ['anciennete', 'Ancienneté'], ['baisses', 'Baisses']] as const
const STATUT_LABEL: Record<string, string> = {
  active: 'En vente', en_vente_longue: 'En vente longue', a_reverifier: 'À revérifier',
  retiree: 'Retirée', vendue: 'Vendue', retiree_sans_vente: 'Retirée sans vente',
}
const NIV_LABEL: Record<string, string> = { source: 'Sourcé', estime: 'Estimé', absent: 'Non rattachée' }
const fmtEur = (v: number | null) => (v == null ? '—' : v.toLocaleString('fr-FR') + ' €')
const fmtDate = (iso: string | null) => (iso ? new Intl.DateTimeFormat('fr-FR', { day: '2-digit', month: '2-digit', year: '2-digit', timeZone: 'Indian/Reunion' }).format(new Date(iso)) : '—')

// pastille rattaché / non localisé (libellé court et clair — choix rapporté)
function Pastille({ ratt }: { ratt: boolean }) {
  return (
    <span className={`shrink-0 rounded-full px-1.5 py-0.5 text-[9.5px] font-medium ${ratt ? 'bg-mint/12 text-mint' : 'bg-line-2 text-txt-dim'}`}>
      {ratt ? 'sur la carte' : 'non localisé'}
    </span>
  )
}

function ouvrirPortail(b: { bien_id: number; url_sortante: string; annonce_id: number | null }) {
  radarClic(b.bien_id, b.annonce_id).catch(() => {})   // clic sortant logué (usage), jamais bloquant
  window.open(b.url_sortante, '_blank', 'noopener,noreferrer')
}

// ── C3 — fiche d'un bien ──
function BienFiche({ bienId, onBack }: { bienId: number; onBack: () => void }) {
  const { data: b, isError } = useQuery({ queryKey: ['radar-bien', bienId], queryFn: () => getRadarBienDetail(bienId) })
  const [signale, setSignale] = useState(false)
  // RETOURS-1 R9 — même défaut que l'onglet Marché : une erreur non lue = « Chargement… » éternel.
  if (isError) return (
    <div className="p-4 text-[12px] text-txt-mut">
      Fiche indisponible — le serveur n’a pas répondu.{' '}
      <button onClick={onBack} className="text-mint hover:underline">‹ retour</button>
    </div>
  )
  if (!b || !b.bien_id) return <div className="p-4 text-[12px] text-txt-mut">Chargement…</div>
  const ratt = b.rattachement.niveau !== 'absent'
  const faits: [string, string][] = [
    ['Prix', fmtEur(b.faits.prix)], ['Type', b.type_bien ?? '—'],
    ['Pièces', b.faits.pieces?.toString() ?? '—'],
    ['Surface hab.', b.faits.surface_hab ? `${b.faits.surface_hab} m²` : '—'],
    ['Terrain', b.faits.surface_terrain ? `${b.faits.surface_terrain} m²` : '—'],
    ['DPE', b.faits.dpe_classe ?? '—'], ['Vendeur', b.faits.particulier_pro ?? '—'],
  ]
  return (
    <div className="flex flex-col gap-3 p-3">
      <button onClick={onBack} className="self-start text-[11px] text-txt-mut hover:text-txt">← retour à la liste</button>
      <div className="flex items-center gap-2">
        <span className="text-[15px] font-medium text-txt-hi">{b.commune}</span>
        <span className="rounded-full bg-surface-3 px-2 py-0.5 text-[10px] text-txt-mut">{STATUT_LABEL[b.statut] ?? b.statut}</span>
        {b.baisse && <span className="rounded-full bg-amber/15 px-2 py-0.5 text-[10px] text-amber">baisse de prix</span>}
      </div>
      <div className="grid grid-cols-2 gap-1.5">
        {faits.map(([k, v]) => {
          const clef = k === 'Prix' ? 'prix' : k === 'Surface hab.' ? 'surface_hab' : k === 'Terrain' ? 'surface_terrain' : k === 'DPE' ? 'dpe_classe' : k === 'Pièces' ? 'pieces' : k === 'Vendeur' ? 'particulier_pro' : 'type'
          const et = b.etiquettes[clef]
          return (
            <div key={k} className="rounded-md bg-surface-2 px-2 py-1 text-[12px] text-txt">
              <span className="font-mono text-[9px] uppercase tracking-wider text-txt-dim">{k}</span>{' '}
              <b className="font-medium">{v}</b>
              {et && v !== '—' && <span className="ml-1 text-[9px] text-txt-dim">· {et === 'source' ? 'Sourcé' : et === 'estime' ? 'Estimé' : 'Absent'}</span>}
            </div>
          )
        })}
      </div>

      {/* rattachement (Sourcé / Estimé avec candidates / Non rattachée) */}
      <div className="rounded-md border border-line-2 px-2.5 py-2 text-[11.5px]">
        <span className="font-mono text-[9px] uppercase tracking-wider text-txt-dim">Parcelle</span>{' '}
        <b className={b.rattachement.niveau === 'source' ? 'text-mint' : b.rattachement.niveau === 'estime' ? 'text-amber' : 'text-txt-dim'}>
          {NIV_LABEL[b.rattachement.niveau]}
        </b>
        {b.rattachement.idu && <span className="ml-1 font-mono text-txt-mut">{b.rattachement.idu}</span>}
        {b.rattachement.confiance != null && <span className="ml-1 text-txt-dim">confiance {Math.round(b.rattachement.confiance * 100)} %</span>}
        {b.rattachement.niveau === 'estime' && <div className="mt-0.5 text-[10.5px] text-txt-dim">parcelle probable — à confirmer, jamais un point faussement sûr.</div>}
      </div>

      {/* historique de prix (liste datée ; sparkline si le volume s'y prête) */}
      {b.historique_prix.length > 0 && (
        <div className="rounded-md border border-line-2 px-2.5 py-2">
          <span className="font-mono text-[9px] uppercase tracking-wider text-txt-dim">Historique de prix</span>
          <div className="mt-1 flex flex-col gap-0.5 text-[11px]">
            {b.historique_prix.map((h, i) => (
              <div key={i} className="flex items-center gap-2">
                <span className="font-mono text-[10px] text-txt-dim">{fmtDate(h.date)}</span>
                <span className="text-txt-mut">{fmtEur(h.ancien)}</span>
                <span className="text-txt-dim">→</span>
                <span className={(h.nouveau ?? 0) < (h.ancien ?? 0) ? 'text-amber' : 'text-txt'}>{fmtEur(h.nouveau)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="text-[10.5px] text-txt-dim">
        {b.fraicheur_source === 'publication' ? 'Publiée' : 'Saisie'} le {fmtDate(b.date_publication || b.date_saisie)}
      </div>

      {/* SEUL chemin vers la source : gros bouton (clic sortant logué) */}
      <a onClick={(e) => { e.preventDefault(); ouvrirPortail(b) }} href={b.url_sortante} target="_blank" rel="noopener noreferrer"
        className="rounded-lg bg-mint px-4 py-2.5 text-center text-[13px] font-medium text-mint-on">
        Voir l’annonce sur {b.portail} ↗
      </a>
      {!ratt && <p className="text-[10.5px] text-txt-dim">Bien non rattaché à une parcelle — seul le lien vers la source est disponible.</p>}

      <button disabled={signale} onClick={() => radarSignaler(bienId, 'annonce retirée / erreur').then(() => setSignale(true))}
        className="text-[11px] text-txt-mut underline decoration-dotted hover:text-txt disabled:opacity-60">
        {signale ? 'Signalé — merci, Victor va vérifier' : 'Signaler : annonce retirée / erreur'}
      </button>
    </div>
  )
}

// ── C2 — filtres + listing (la carte est alimentée en pins par un effet) ──
export function RadarClient() {
  const [f, setF] = useState<RadarFiltres>({})
  const [tri, setTri] = useState('recentes')
  const [bienOuvert, setBienOuvert] = useState<number | null>(null)
  const [onglet, setOnglet] = useState<'annonces' | 'marche'>('annonces')
  const [veilleOk, setVeilleOk] = useState(false)
  const setModuleMap = useApp((s) => s.setModuleMap)
  const setFlyTo = useApp((s) => s.setFlyTo)
  const select = useApp((s) => s.select)
  const radarToOpen = useApp((s) => s.radarToOpen)
  const setRadarToOpen = useApp((s) => s.setRadarToOpen)

  const { data, isLoading } = useQuery({ queryKey: ['radar-biens', f, tri], queryFn: () => getRadarBiens(f, tri) })
  // mémoïsé sur `data` : sans ça, `?? []` crée un nouveau tableau à chaque rendu → l'effet setModuleMap
  // boucle (React #185). Ref stable tant que la donnée ne change pas.
  const biens = useMemo(() => data?.biens ?? [], [data])

  // carte = rattachés SEULEMENT → pins poussés sur la carte existante (kind='radar', couleur par statut).
  useEffect(() => {
    const feats = biens.filter((b) => b.coords).map((b) => ({
      type: 'Feature', geometry: { type: 'Point', coordinates: b.coords },
      properties: { kind: 'radar', bien_id: b.bien_id, idu: b.rattachement.idu, statut: b.statut },
    }))
    setModuleMap({ idus: biens.filter((b) => b.rattachement.idu).map((b) => b.rattachement.idu as string),
                   extra: { type: 'FeatureCollection', features: feats } })
    return () => setModuleMap({ idus: [], extra: null })
  }, [biens, setModuleMap])

  // clic sur un pin de la carte → ouvre la fiche du bien (idiome consommé-puis-reset).
  useEffect(() => {
    if (radarToOpen != null) { setBienOuvert(radarToOpen); setRadarToOpen(null) }
  }, [radarToOpen, setRadarToOpen])

  const ouvrirListe = (b: RadarBienClient) => {
    if (b.rattachement.idu && b.coords) {
      setFlyTo({ center: b.coords, zoom: 17 }); select(b.rattachement.idu); setBienOuvert(b.bien_id)
    } else {
      ouvrirPortail(b)   // non rattaché → directement le portail (nouvel onglet, clic logué)
    }
  }

  const setNum = (k: keyof RadarFiltres, v: string) => setF((p) => ({ ...p, [k]: v === '' ? undefined : Number(v) }))
  const communes = useMemo(() => [...new Set(biens.map((b) => b.commune))].sort(), [biens])

  if (bienOuvert != null) return <BienFiche bienId={bienOuvert} onBack={() => setBienOuvert(null)} />

  // onglets Annonces / Marché (l'onglet Marché n'a pas besoin des pins)
  const Onglets = (
    <div className="flex gap-1 px-3 pt-3">
      {(['annonces', 'marche'] as const).map((o) => (
        <button key={o} onClick={() => setOnglet(o)}
          className={`rounded-md px-3 py-1 text-[12px] ${onglet === o ? 'bg-mint/12 font-medium text-mint' : 'text-txt-mut hover:text-txt'}`}>
          {o === 'annonces' ? 'Annonces' : 'Marché'}
        </button>
      ))}
    </div>
  )
  if (onglet === 'marche') return <div className="flex flex-col">{Onglets}<RadarMarche /></div>

  return (
    <div className="flex flex-col">
      {Onglets}
      <div className="flex flex-col gap-3 p-3">
      <p className="text-[11.5px] text-txt-mut">Les biens en vente vus par Victor — des faits et un lien vers la source. Aucune photo ni texte d’annonce.</p>

      {/* filtres */}
      <div className="flex flex-col gap-2 rounded-lg border border-line-2 bg-surface-2 p-2.5">
        <div className="grid grid-cols-2 gap-1.5">
          <select value={f.commune ?? ''} onChange={(e) => setF((p) => ({ ...p, commune: e.target.value || undefined }))}
            className="rounded-md border border-line-2 bg-surface-1 px-2 py-1 text-[11.5px] text-txt">
            <option value="">Toutes communes</option>
            {communes.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <select value={f.type_bien ?? ''} onChange={(e) => setF((p) => ({ ...p, type_bien: e.target.value || undefined }))}
            className="rounded-md border border-line-2 bg-surface-1 px-2 py-1 text-[11.5px] text-txt">
            {TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
          <input type="number" placeholder="prix min" value={f.prix_min ?? ''} onChange={(e) => setNum('prix_min', e.target.value)}
            className="min-w-0 rounded-md border border-line-2 bg-surface-1 px-2 py-1 text-[11.5px] text-txt" />
          <input type="number" placeholder="prix max" value={f.prix_max ?? ''} onChange={(e) => setNum('prix_max', e.target.value)}
            className="min-w-0 rounded-md border border-line-2 bg-surface-1 px-2 py-1 text-[11.5px] text-txt" />
        </div>
        <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
          {(['', 'oui', 'non'] as const).map((r) => (
            <button key={r || 'ind'} onClick={() => setF((p) => ({ ...p, rattache: r || undefined }))}
              className={`rounded-md border px-2 py-1 ${(f.rattache ?? '') === r ? 'border-mint/50 text-mint' : 'border-line-2 text-txt-mut'}`}>
              {r === '' ? 'Rattaché : indifférent' : r === 'oui' ? 'Rattaché' : 'Non rattaché'}
            </button>
          ))}
          {(['particulier', 'pro'] as const).map((pp) => (
            <button key={pp} onClick={() => setF((p) => ({ ...p, particulier_pro: p.particulier_pro === pp ? undefined : pp }))}
              className={`rounded-md border px-2 py-1 ${f.particulier_pro === pp ? 'border-mint/50 text-mint' : 'border-line-2 text-txt-mut'}`}>{pp}</button>
          ))}
        </div>
      </div>

      {/* veille : suivre ces critères → alerte de fin de journée (P4) */}
      <button onClick={() => creerRadarVeille({ ...f, evenements: ['nouvelle', 'baisse', 'retour'] }).then(() => setVeilleOk(true))}
        className="self-start text-[11px] text-mint underline decoration-dotted hover:opacity-80">
        {veilleOk ? '✓ Veille créée — vous serez alerté en fin de journée' : '＋ Être alerté sur ces critères (veille)'}
      </button>

      {/* compteur + tri */}
      <div className="flex items-center gap-2 text-[11.5px]">
        <b className="text-txt-hi">{data?.n_total ?? 0}</b> <span className="text-txt-mut">bien{(data?.n_total ?? 0) > 1 ? 's' : ''}</span>
        <span className="text-txt-dim">· {data?.n_rattaches ?? 0} sur la carte</span>
        <select value={tri} onChange={(e) => setTri(e.target.value)} className="ml-auto rounded-md border border-line-2 bg-surface-1 px-2 py-1 text-[11px] text-txt">
          {TRIS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
      </div>

      {/* listing — TOUT, avec pastille */}
      <div className="flex flex-col gap-1.5">
        {isLoading && <div className="py-6 text-center text-[12px] text-txt-dim">Chargement…</div>}
        {!isLoading && biens.length === 0 && (
          <div className="rounded-lg border border-dashed border-line-2 py-8 text-center text-[12px] text-txt-mut">
            Aucun bien ne correspond à ces filtres.<br />Élargissez la recherche.
          </div>
        )}
        {biens.map((b) => (
          <button key={b.bien_id} onClick={() => ouvrirListe(b)}
            className="flex flex-col gap-1 rounded-lg border border-line-2 bg-surface-1 p-2.5 text-left hover:border-mint/30">
            <div className="flex items-center gap-2">
              <span className="text-[13px] font-medium text-txt-hi">{fmtEur(b.faits.prix)}</span>
              <span className="text-[11px] text-txt-mut">{b.type_bien}</span>
              {b.baisse && <span className="rounded-full bg-amber/15 px-1.5 text-[9.5px] text-amber">baisse</span>}
              <Pastille ratt={!!b.rattachement.idu} />
            </div>
            <div className="flex items-center gap-2 text-[11px] text-txt-mut">
              <span>{b.commune}</span>
              {b.faits.surface_hab && <span>· {b.faits.surface_hab} m²</span>}
              {b.faits.surface_terrain && <span>· terrain {b.faits.surface_terrain} m²</span>}
              <span className="ml-auto font-mono text-[9.5px] text-txt-dim">{b.portail}</span>
            </div>
          </button>
        ))}
      </div>
      </div>
    </div>
  )
}
