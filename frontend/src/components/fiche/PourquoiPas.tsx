import { useQuery } from '@tanstack/react-query'
import { getAntiFiche, type AntiFicheMotif } from '../../lib/api'
import { Loading } from '../Loading'

// R5 (O3) — ANTI-FICHE « Pourquoi pas ? » : les motifs d'écartement/vigilance de LA parcelle,
// hiérarchisés (RÉDHIBITOIRE puis VIGILANCE) tels que servis par l'API — lus dans la cascade
// déjà calculée, chacun sourcé. Une parcelle sans motif le dit ; rien n'est inventé.
function Motif({ m, hard = false }: { m: AntiFicheMotif; hard?: boolean }) {
  return (
    <div className="flex gap-2 rounded-lg border border-line-2 bg-surface-3 px-3 py-2 text-[11.5px] leading-snug">
      <span className={hard ? 'text-st-ecartee' : 'text-[#E8B44C]'}>{hard ? '✕' : '⚠'}</span>
      <div className="min-w-0">
        <span className="text-txt">{m.motif}</span>
        <span className="ml-1.5 text-[9.5px] text-txt-dim" title="Source du motif">· {m.source}</span>
      </div>
    </div>
  )
}

export function PourquoiPasTab({ idu }: { idu: string }) {
  const q = useQuery({ queryKey: ['anti-fiche', idu], queryFn: () => getAntiFiche(idu) })
  const d = q.data
  if (q.isLoading) return <Loading label="Lecture des motifs" className="text-xs" />
  if (q.isError || !d) return <p className="text-xs text-txt-dim">Motifs momentanément indisponibles.</p>
  return (
    <div data-pourquoi-pas className="flex flex-col gap-3">
      <div>
        <p className="text-[11.5px] leading-relaxed text-txt">{d.cadre}</p>
        <p className="mt-0.5 text-[11px] text-txt-mut">{d.synthese}</p>
      </div>
      {d.redhibitoire.length > 0 && (
        <div>
          <p className="mb-1.5 font-mono text-[10px] tracking-widest text-st-ecartee">
            RÉDHIBITOIRE ({d.n_redhibitoire})
          </p>
          <div className="flex flex-col gap-1.5">
            {d.redhibitoire.map((m, i) => <Motif key={`r${i}`} m={m} hard />)}
          </div>
        </div>
      )}
      {d.vigilance.length > 0 && (
        <div>
          <p className="mb-1.5 font-mono text-[10px] tracking-widest text-[#E8B44C]">
            VIGILANCE ({d.n_vigilance})
          </p>
          <div className="flex flex-col gap-1.5">
            {d.vigilance.map((m, i) => <Motif key={`v${i}`} m={m} />)}
          </div>
        </div>
      )}
      {d.redhibitoire.length === 0 && d.vigilance.length === 0 && (
        <p className="text-[11.5px] text-txt-mut">
          Aucun motif d'écartement ni point de vigilance relevé dans les couches analysées.
        </p>
      )}
      <p className="text-[9.5px] text-txt-dim">{d.avertissement}</p>
    </div>
  )
}
