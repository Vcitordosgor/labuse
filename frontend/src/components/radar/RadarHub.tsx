// RADAR-2 (Lot 1) — LE HUB RADAR plein écran, SANS carte. Un petit automate d'écrans (store.radarEcran) :
//   'portes'          → deux portes : Radar · Veille (résumé chiffré RÉEL de chacune)
//   'radar'           → l'écran Radar : liste (560 px) + marché (colonne de droite)
//   'veille'          → deux portes Veille : Le foncier · Les annonces + réglage du mail
//   'veille-foncier'  → les parcelles suivies
//   'veille-annonces' → les alertes Radar
// La Veille n'a plus d'entrée de rail ni de carte : on l'atteint par la porte « Veille » de ce hub.
import { useQuery } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { getRadarApercu } from '../../lib/api'
import { useApp } from '../../store/useApp'
import { Squelette } from '../Loading'
import { RadarEcran } from './RadarEcran'
import { VeilleAnnonces, VeilleFoncier, VeillePortes } from './VeilleEcrans'

// « 27/09 21 h 46 » (heure de La Réunion) — la dernière capture, telle que la maquette l'écrit.
export function fmtCapture(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  const p = new Intl.DateTimeFormat('fr-FR', {
    day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
    hour12: false, timeZone: 'Indian/Reunion',
  }).formatToParts(d)
  const g = (t: string) => p.find((x) => x.type === t)?.value ?? ''
  return `${g('day')}/${g('month')} ${g('hour')} h ${g('minute')}`
}

// ── En-tête d'un écran plein écran du hub (surtitre + titre + sous-titre), gabarit commun. ──
export function EcranTete({ surtitre, titre, sous, retour }: {
  surtitre: string; titre: string; sous?: ReactNode; retour?: ReactNode
}) {
  return (
    <div className="mb-6">
      {retour && <div className="mb-4">{retour}</div>}
      <div className="font-mono text-[10.5px] tracking-[0.2em] text-txt-mut">{surtitre}</div>
      <h1 className="mt-1.5 text-[28px] font-semibold leading-tight text-txt-hi">{titre}</h1>
      {sous && <p className="mt-1.5 text-[13px] leading-snug text-txt-mut">{sous}</p>}
    </div>
  )
}

// ── Une PORTE : grande carte cliquable (icône inversée au survol, charte DA §7). ──
export function PorteCard({ ic, titre, desc, resume, onClick, data }: {
  ic: ReactNode; titre: string; desc: string; resume: ReactNode; onClick: () => void; data?: string
}) {
  return (
    <button {...(data ? { [`data-${data}`]: true } : {})} onClick={onClick}
      className="porte group flex min-h-[220px] w-full flex-col rounded-lg border border-line-2 bg-surface-2 p-7 text-left">
      <span className="porte-ic mb-6 grid h-11 w-11 place-items-center rounded-md border border-mint/40 text-mint">{ic}</span>
      <div className="text-[20px] font-semibold text-txt-hi">{titre}</div>
      <p className="mt-2 text-[13px] leading-relaxed text-txt-mut">{desc}</p>
      <div className="mt-auto flex items-center justify-between pt-6 text-[12.5px]">
        <span className="text-txt-dim">{resume}</span>
        <span className="font-medium text-mint">Ouvrir →</span>
      </div>
    </button>
  )
}

// petites icônes des portes (viewBox 24, trait mint)
const IcoRadar = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
    <circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="4.5" /><circle cx="12" cy="12" r="1" fill="currentColor" />
    <path d="M12 3v3M21 12h-3" strokeLinecap="round" />
  </svg>
)
const IcoCloche = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round">
    <path d="M6 9a6 6 0 0 1 12 0c0 5 2 6 2 6H4s2-1 2-6z" /><path d="M10 20a2 2 0 0 0 4 0" strokeLinecap="round" />
  </svg>
)

// ── Les deux portes de tête : Radar · Veille (résumé chiffré RÉEL). ──
function PortesRadar() {
  const setRadarEcran = useApp((s) => s.setRadarEcran)
  const { data, isLoading } = useQuery({ queryKey: ['radar-apercu'], queryFn: getRadarApercu })
  const biens = data?.biens_en_vente ?? 0
  const suivis = data?.suivis_n ?? 0
  const alertes = data?.alertes_n ?? 0
  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto w-full max-w-[1060px] px-8 py-10">
        <EcranTete surtitre="RADAR" titre="Le marché en vente, et ce que vous surveillez" sous="Deux chemins." />
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
          <PorteCard data="radar-porte-radar" ic={<IcoRadar />} titre="Radar"
            desc="Les biens en vente sur les portails, et le marché de chaque commune : ce qui est demandé, ce qui se vend vraiment."
            resume={isLoading ? '…' : <>{biens} bien{biens > 1 ? 's' : ''} en vente · dernière capture {fmtCapture(data?.derniere_capture_at ?? null)}</>}
            onClick={() => setRadarEcran('radar')} />
          <PorteCard data="radar-porte-veille" ic={<IcoCloche />} titre="Veille"
            desc="Vos parcelles suivies et vos alertes sur les annonces. Soyez prévenu quand quelque chose bouge."
            resume={isLoading ? '…' : <>{suivis} parcelle{suivis > 1 ? 's' : ''} suivie{suivis > 1 ? 's' : ''} · {alertes} alerte{alertes > 1 ? 's' : ''}</>}
            onClick={() => setRadarEcran('veille')} />
        </div>
      </div>
    </div>
  )
}

export function RadarHub() {
  const ecran = useApp((s) => s.radarEcran)
  if (ecran === 'radar') return <RadarEcran />
  if (ecran === 'veille') return <VeillePortes />
  if (ecran === 'veille-foncier') return <VeilleFoncier />
  if (ecran === 'veille-annonces') return <VeilleAnnonces />
  return <PortesRadar />
}

// squelette partagé quand un sous-écran charge (évite un flash vide)
export function HubSquelette() {
  return <div className="mx-auto w-full max-w-[1060px] px-8 py-10"><Squelette lignes={6} /></div>
}
