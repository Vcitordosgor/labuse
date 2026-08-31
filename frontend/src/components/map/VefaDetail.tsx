// SECTEUR-2b (U1) — panneau de détail d'une commune de la couche VEFA (clic sur la carte). TOUT depuis
// les moteurs existants (/outils/vefa-neuf/{ref}), chaque chiffre avec son n ; sous le seuil par segment,
// le chiffre est ABSENT (jamais extrapolé). Aucune donnée en dur.
import { useQuery } from '@tanstack/react-query'
import { getVefaDetail } from '../../lib/api'
import { useApp } from '../../store/useApp'
import { fmtInt } from '../../lib/format'
import { Loading } from '../Loading'

export function VefaDetail() {
  const commune = useApp((s) => s.vefaCommune)
  const close = () => useApp.getState().setVefaCommune(null)
  const q = useQuery({ queryKey: ['vefa-detail', commune], queryFn: () => getVefaDetail(commune!), enabled: !!commune })
  if (!commune) return null
  const d = q.data

  return (
    <div data-vefa-detail className="floating absolute right-4 top-4 z-20 hidden max-h-[80vh] w-[290px] overflow-y-auto sm:block">
      <div className="flex items-center justify-between border-b border-line px-3.5 py-2">
        <span className="label-caps">Neuf VEFA — {commune}</span>
        <button data-vefa-close onClick={close} className="text-txt-dim hover:text-txt-hi" aria-label="Fermer">✕</button>
      </div>
      {q.isLoading && <Loading label="Détail…" className="mx-auto my-4 text-xs" />}
      {d && (
        <div className="flex flex-col gap-2.5 px-3.5 py-3 text-[12px]">
          {/* médiane €/m² VEFA (36 mois) + n */}
          {d.peinte && d.mediane_eur_m2 != null ? (
            <div>
              <p className="font-display text-xl font-bold text-txt-hi tnum">{fmtInt(d.mediane_eur_m2)} €/m²</p>
              <p className="text-[10.5px] text-txt-dim">médiane VEFA · {d.n_ventes} ventes · {d.fenetre_mois} mois</p>
              {d.tendance_12m ? (
                <p className="mt-0.5 text-[11px]">Tendance 12 mois : <b className={d.tendance_12m.pct < 0 ? 'text-st-ecartee' : 'text-mint'}>{d.tendance_12m.pct > 0 ? '+' : ''}{d.tendance_12m.pct} %</b> <span className="text-txt-dim">({d.tendance_12m.sens} · n={d.tendance_12m.n_12m})</span></p>
              ) : <p className="mt-0.5 text-[10.5px] italic text-txt-dim">tendance 12 mois : échantillon récent insuffisant</p>}
            </div>
          ) : (
            <p className="rounded-md bg-surface-3 px-2 py-1.5 text-[11px] text-txt-mut">Moins de {d.seuil} ventes VEFA sur {d.fenetre_mois} mois ({d.n_ventes}) — pas de médiane fiable (jamais extrapolée).</p>
          )}

          {/* répartition appartements / maisons */}
          <div className="border-t border-line-2 pt-2">
            <p className="text-[10px] font-medium text-txt-mut">Répartition (ventes VEFA)</p>
            <p className="text-[11px] text-txt">{d.repartition.appartements} appartement{d.repartition.appartements > 1 ? 's' : ''} · {d.repartition.maisons} maison{d.repartition.maisons > 1 ? 's' : ''}</p>
          </div>

          {/* médiane par taille — indisponible (pas de pièces dans DVF 974) */}
          <div className="border-t border-line-2 pt-2">
            <p className="text-[10px] font-medium text-txt-mut">Médiane par taille (T2/T3/T4)</p>
            <p data-vefa-par-taille className="text-[10.5px] italic text-txt-dim">{d.par_taille.motif}</p>
          </div>

          {/* offre engagée Sitadel (ce qui arrive en face) */}
          <div className="border-t border-line-2 pt-2">
            <p className="text-[10px] font-medium text-txt-mut">Offre engagée · {d.offre_engagee.mois} mois</p>
            <p className="text-[11px] text-txt"><b className="tnum">{d.offre_engagee.logements != null ? fmtInt(d.offre_engagee.logements) : '—'}</b> logements collectifs autorisés <span className="text-txt-dim">({d.offre_engagee.permis} permis)</span></p>
            <p className="text-[9.5px] text-txt-dim">Sitadel — l'offre qui arrive en face du marché acté.</p>
          </div>

          {/* lien fiche commune */}
          {d.commune && (
            <button data-vefa-fiche-commune onClick={() => { const st = useApp.getState(); st.setCommune(d.commune!); st.setContexteCommune(d.commune!) }}
              className="mt-1 flex w-full items-center justify-between rounded-md border border-line-2 bg-surface-2 px-2.5 py-2 text-[11.5px] text-txt transition-colors hover:border-mint/50">
              <span>Fiche commune — {d.commune}</span><span className="text-mint">→</span>
            </button>
          )}
          <p className="text-[9px] leading-snug text-txt-dim">{d.source}</p>
        </div>
      )}
    </div>
  )
}
