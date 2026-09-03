// DESTINATIONS-1 (X5.3) — page « Destinations » : UNE page pour la question « sur quelles communes
// le verdict destination est-il calibré ? ». Tableau commune × état (calibrée le JJ/MM + millésime /
// à relire / RNU / non calibrée), lien vers le règlement LU, compteurs en tête. Lecture seule —
// la calibration elle-même vit dans config/plu_destinations (module unique plu.destinations).
import { useQuery } from '@tanstack/react-query'
import { getAdminDestinations, type AdminDestinationsCommune } from '../../lib/api'
import { Chip, Panel, PHead } from './AdminView'

const fmtJJMM = (d?: string | null) => {
  if (!d) return null
  try {
    return new Intl.DateTimeFormat('fr-FR', { day: '2-digit', month: '2-digit' }).format(new Date(d))
  } catch { return null }
}

// état → chip (pastille contour, mêmes tons que le reste de la Tour de contrôle) + libellé dit.
const ETATS: Record<AdminDestinationsCommune['etat'], { tone: 'ok' | 'warn' | 'off' | 'err'; label: string }> = {
  calibree: { tone: 'ok', label: 'calibrée' },
  a_relire: { tone: 'warn', label: 'à relire' },
  rnu: { tone: 'off', label: 'RNU' },
  non_calibree: { tone: 'off', label: 'non calibrée' },
}

function Compteur({ n, label, tone }: { n: number; label: string; tone: 'ok' | 'warn' | 'off' }) {
  const cls = { ok: 'text-mint', warn: 'text-amber', off: 'text-txt-mut' }[tone]
  return (
    <div className="rounded-xl border border-line bg-surface-2 px-4 py-3.5">
      <div className={`font-display text-2xl font-semibold ${n > 0 ? cls : 'text-txt-mut'}`}>{n}</div>
      <div className="mt-0.5 text-[11.5px] text-txt-mut">{label}</div>
    </div>
  )
}

export function DestinationsSection() {
  const q = useQuery({ queryKey: ['admin-destinations'], queryFn: getAdminDestinations })
  const d = q.data
  if (q.isError) return <div className="py-10 text-center text-xs text-st-ecartee">Indisponible — réessayez.</div>
  if (!d) return <div className="py-10 text-center text-xs text-txt-mut">Chargement…</div>
  return (
    <>
      {/* compteurs en tête — l'état du chantier de calibration, d'un coup d'œil */}
      <div className="mb-3.5 grid grid-cols-4 gap-3.5 max-[1100px]:grid-cols-2">
        <Compteur n={d.compte.calibree} label="calibrée(s)" tone="ok" />
        <Compteur n={d.compte.a_relire} label="à relire — nouvelle version de PLU servie" tone="warn" />
        <Compteur n={d.compte.rnu} label="RNU (règlement national)" tone="off" />
        <Compteur n={d.compte.non_calibree} label="non calibrée(s)" tone="off" />
      </div>

      <Panel>
        <PHead>Commune × état de calibration</PHead>
        <table className="w-full text-[12.5px]">
          <thead>
            <tr className="border-b border-line font-mono text-[10px] uppercase tracking-[0.12em] text-txt-dim">
              <th className="px-4 py-2 text-left font-medium">Commune</th>
              <th className="px-4 py-2 text-left font-medium">État</th>
              <th className="px-4 py-2 text-left font-medium">Millésime</th>
              <th className="px-4 py-2 text-left font-medium">Règlement</th>
            </tr>
          </thead>
          <tbody>
            {d.communes.map((c) => {
              const e = ETATS[c.etat] ?? ETATS.non_calibree
              const lu = fmtJJMM(c.lu_le)
              return (
                <tr key={c.insee} data-admin-destination={c.insee}
                  className="border-b border-line transition-colors duration-quick last:border-b-0 hover:bg-surface-3">
                  <td className="px-4 py-2.5">
                    <b className="text-txt">{c.commune}</b>
                    <span className="ml-1.5 font-mono text-[10px] text-txt-dim">{c.insee}</span>
                  </td>
                  <td className="px-4 py-2.5">
                    <Chip tone={e.tone}>{e.label}{c.etat === 'calibree' && lu ? ` le ${lu}` : ''}</Chip>
                    {c.etat === 'a_relire' && lu && <span className="ml-1.5 text-[10.5px] text-txt-dim">lue le {lu}</span>}
                    {c.note && <div className="mt-0.5 text-[10.5px] leading-snug text-txt-dim">{c.note}</div>}
                  </td>
                  <td className="px-4 py-2.5 font-mono text-[11px] text-txt-mut">{c.millesime ?? '—'}</td>
                  <td className="px-4 py-2.5">
                    {c.url
                      ? <a href={c.url} target="_blank" rel="noreferrer" className="text-[11.5px] text-mint hover:underline"
                          title={c.document ?? undefined}>règlement ↗</a>
                      : <span className="text-[11px] text-txt-dim" title={c.document ?? undefined}>{c.document ? 'document lu (sans lien)' : '—'}</span>}
                  </td>
                </tr>
              )
            })}
            {d.communes.length === 0 && (
              <tr><td colSpan={4} className="px-4 py-6 text-center text-xs text-txt-mut">Aucune commune au catalogue.</td></tr>
            )}
          </tbody>
        </table>
      </Panel>
      <p className="text-[10.5px] leading-snug text-txt-dim">
        Référentiel : {d.referentiel}. « À relire » = une nouvelle version du PLU est SERVIE,
        postérieure au document lu au calibrage (X5.2) — le verdict reste servi sur la version lue, daté.
      </p>
    </>
  )
}
