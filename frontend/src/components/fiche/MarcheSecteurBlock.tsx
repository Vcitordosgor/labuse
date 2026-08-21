/**
 * M125-2 — Contexte socio-économique du secteur (Filosofi 200 m au centroïde + parc social RPLS
 * de la commune). Contexte informatif, HORS scoring. Chaque sous-bloc porte SON millésime (daté,
 * jamais un millésime unique). Rendu seulement si au moins une source est présente.
 */
import type { MarcheSecteur } from '../../lib/types'

function eur(n: number | null): string {
  return n == null ? '—' : `${Math.round(n).toLocaleString('fr-FR')} €`
}

export function MarcheSecteurBlock({ ms }: { ms: MarcheSecteur }) {
  const f = ms.filosofi_200m
  const r = ms.rpls_commune
  if (!f && !r) return null
  const partProp = f && f.men > 0 ? Math.round((100 * f.men_prop) / f.men) : null
  return (
    <div data-marche-secteur className="card-elev px-3 py-2.5">
      <span className="text-xs font-medium text-txt-hi">Contexte socio-économique (secteur)</span>
      <div className="mt-2 flex flex-col gap-1.5">
        {f && (
          <div className="text-[11px] leading-snug text-txt">
            <p>
              Niveau de vie médian <b className="font-medium text-txt-hi">{eur(f.nivvie_moyen_eur)}</b>
              {partProp != null && <span className="text-txt-mut"> · {partProp} % propriétaires</span>}
              {f.taux_pauvrete_pct != null && <span className="text-txt-mut"> · pauvreté {f.taux_pauvrete_pct} %</span>}
            </p>
            <p className="text-[10px] text-txt-dim">{f.millesime}</p>
          </div>
        )}
        {r && (
          <div className="text-[11px] leading-snug text-txt">
            <p>
              Parc social <b className="font-medium text-txt-hi">{r.nb_logements.toLocaleString('fr-FR')}</b> logements
              {r.pct_qpv != null && <span className="text-txt-mut"> · {r.pct_qpv} % en QPV</span>}
            </p>
            <p className="text-[10px] text-txt-dim">{r.millesime}</p>
          </div>
        )}
      </div>
      <p className="mt-2 text-[10.5px] leading-snug text-txt-dim">Contexte informatif — hors scoring.</p>
    </div>
  )
}
