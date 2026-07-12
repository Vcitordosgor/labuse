import { useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'
import { getSources } from '../../lib/api'
import { useApp } from '../../store/useApp'

/** Drawer « source » (exigence : jamais un cul-de-sac). S'ouvre PAR-DESSUS la fiche, qui reste
 *  montée — fermeture par ✕, clic-extérieur et Échap. Montre l'extrait (la ligne), sa date, sa
 *  référence tracée, et la carte d'identité de la source (statut, fraîcheur, doc). */
export function SourceDrawer() {
  const { sourceLine, closeSourceDrawer, openSources } = useApp()
  const sources = useQuery({ queryKey: ['sources'], queryFn: getSources, enabled: !!sourceLine })

  useEffect(() => {
    if (!sourceLine) return
    const h = (e: KeyboardEvent) => e.key === 'Escape' && closeSourceDrawer()
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [sourceLine, closeSourceDrawer])

  if (!sourceLine) return null
  const meta = sources.data?.find((s) => s.name === sourceLine.source)
  const trace = sourceLine.source_table && sourceLine.source_id != null
    ? `${sourceLine.source_table}#${sourceLine.source_id}` : null

  return (
    <>
      {/* clic-extérieur */}
      <div className="fixed inset-0 z-30 bg-black/40" onClick={closeSourceDrawer} />
      <aside className="fixed right-0 top-0 z-40 flex h-full w-[340px] max-w-full flex-col border-l border-line-2 bg-surface-2 shadow-2xl">
        <div className="flex shrink-0 items-start justify-between border-b border-line px-5 py-4">
          <div className="min-w-0">
            <p className="font-mono text-[10px] tracking-widest text-txt-dim">SOURCE</p>
            <h3 className="mt-1 text-sm font-medium leading-snug text-txt-hi">{sourceLine.source ?? 'Source interne LABUSE'}</h3>
          </div>
          <button onClick={closeSourceDrawer} className="shrink-0 text-txt-mut hover:text-txt-hi" title="Fermer (Échap)">✕</button>
        </div>

        <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-5">
          {/* l'extrait : ce que cette source dit de CETTE parcelle */}
          <div className="rounded-lg border border-line-2 bg-surface-3 p-3">
            <p className="font-mono text-[10px] tracking-widest text-txt-dim">EXTRAIT — {sourceLine.layer}</p>
            <p className="mt-1.5 text-xs leading-relaxed text-txt">{sourceLine.detail}</p>
            <div className="mt-2 flex items-center gap-3 text-[11px] text-txt-dim">
              {trace && <span className="font-mono" title="Référence de l'enregistrement source">{trace}</span>}
              {sourceLine.date && <span className="ml-auto font-mono" title="Date du fait">{sourceLine.date}</span>}
            </div>
          </div>

          {/* carte d'identité de la source */}
          {meta ? (
            <div className="flex flex-col gap-2 text-xs">
              {meta.provider && <Row k="Fournisseur" v={meta.provider} />}
              {meta.category && <Row k="Catégorie" v={meta.category} />}
              {meta.access_type && <Row k="Accès" v={meta.access_type} />}
              {meta.reliability_level && <Row k="Fiabilité" v={meta.reliability_level} />}
              <Row k="Synchronisée" v={meta.last_sync_at ? new Date(meta.last_sync_at).toLocaleDateString('fr-FR') : 'jamais'} />
              {meta.documentation_url && (
                <a href={meta.documentation_url} target="_blank" rel="noreferrer"
                  className="mt-1 text-[#5a7d6c] hover:text-mint hover:underline">Documentation officielle ↗</a>
              )}
            </div>
          ) : (
            <p className="text-[11px] leading-relaxed text-txt-dim">
              {sources.isLoading ? 'Chargement…'
                : 'Donnée calculée par LABUSE (couche interne) — pas de connecteur externe associé.'}
            </p>
          )}
        </div>

        <div className="shrink-0 border-t border-line px-5 py-3">
          <button
            onClick={() => { closeSourceDrawer(); openSources(sourceLine.source) }}
            className="w-full rounded-lg border border-line-2 py-1.5 text-xs text-txt hover:text-txt-hi"
          >
            Toutes les sources →
          </button>
        </div>
      </aside>
    </>
  )
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between gap-3 border-b border-[#141d17] pb-1.5">
      <span className="text-txt-dim">{k}</span>
      <span className="text-right text-txt">{v}</span>
    </div>
  )
}
