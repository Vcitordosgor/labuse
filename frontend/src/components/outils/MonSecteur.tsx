// SECTEUR-1 (S1) + SECTEUR-2 (T1) — outil « Mon secteur » : une adresse / un IDU → les prix DU
// SECTEUR autour de la parcelle. UN SEUL moteur (sector_price / _ref_local, côté back) — la MÊME
// méthode que le « Marché et secteur » de la fiche (exclusion des 5 % extrêmes, rayon adaptatif jusqu'à
// n min, rayon effectif affiché). Grammaire visuelle = l'en-tête à 4 chiffres des fiches (.stats), les
// nombres ne se coupent jamais (tnum + whitespace-nowrap). Rien en dur : tout vient de /outils/mon-secteur.
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getMonSecteur, type LocalMed, type Distribution } from '../../lib/api'
import { ParcelInput } from '../ParcelInput'
import { fmtInt } from '../../lib/format'
import { Loading } from '../Loading'

function DistribNote({ d }: { d: Distribution | null | undefined }) {
  if (!d || !d.apres?.n) return null
  return (
    <p className="mt-1 text-[9.5px] leading-snug text-txt-dim">
      Méthode : {d.avant.n} vente{d.avant.n > 1 ? 's' : ''} → {d.apres.n} retenues
      {d.n_exclus_extremes > 0 ? ` · ${d.n_exclus_extremes} extrême${d.n_exclus_extremes > 1 ? 's' : ''} (5 %) exclus` : ' · aucun extrême à exclure'}
      {d.avant.min != null && d.avant.max != null && d.apres.min != null && d.apres.max != null
        ? ` · plage ${fmtInt(d.avant.min)}–${fmtInt(d.avant.max)} → ${fmtInt(d.apres.min)}–${fmtInt(d.apres.max)} €/m²` : ''}
    </p>
  )
}

// une CASE alignée, même grammaire que l'en-tête à 4 chiffres des fiches (.stats/.stat/.stat-l/.stat-v).
function Cell({ l, v, sub }: { l: string; v: string; sub?: string }) {
  return (
    <div className="stat min-w-0">
      <div className="stat-l">{l.toUpperCase()}</div>
      <div className={`stat-v tnum whitespace-nowrap${v === '—' ? ' vide' : ''}`}>{v}</div>
      {sub && <div className="mt-0.5 truncate text-[9.5px] text-txt-dim" title={sub}>{sub}</div>}
    </div>
  )
}

function typeCell(titre: string, m: LocalMed | null) {
  return <Cell l={titre} v={m ? `${fmtInt(m.eur_m2)} €/m²` : '—'}
    sub={m ? `${m.n} vente${(m.n ?? 0) > 1 ? 's' : ''}${m.millesime ? ` · ${m.millesime}` : ''}` : 'échantillon < 5'} />
}

export function MonSecteur() {
  const [idu, setIdu] = useState<string | null>(null)
  const q = useQuery({ queryKey: ['mon-secteur', idu], queryFn: () => getMonSecteur(idu!), enabled: !!idu })
  const d = q.data
  const sb = d?.secteur_bati

  return (
    <div data-mon-secteur className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-1 text-[12.5px]">
      <div>
        <h2 className="font-display text-base font-bold text-txt-hi">Mon secteur</h2>
        <p className="mt-0.5 text-[11.5px] text-txt-mut">Les prix DU SECTEUR autour d'une parcelle — médiane locale DVF par type (5 % extrêmes exclus, rayon adaptatif), tendance 12 mois, annonces Radar dans le rayon. La même méthode que « Marché et secteur » de la fiche.</p>
      </div>
      <ParcelInput onPick={(i) => setIdu(i)} placeholder="Adresse ou IDU…" dataAttr="mon-secteur-input" />

      {q.isLoading && <Loading label="Analyse du secteur…" className="mx-auto mt-4 text-xs" />}
      {q.isError && <p className="text-[12px] text-st-ecartee">Parcelle inconnue ou erreur — réessayez.</p>}

      {d && (
        <>
          <div className="rounded-lg border border-line-2 bg-surface-1 px-3 py-2">
            <p className="text-[13px] font-medium text-txt-hi">{d.adresse ?? <span className="italic text-txt-dim">sans adresse — {d.commune}</span>}</p>
            <p className="font-mono text-[10.5px] text-txt-dim">{d.idu} · {d.commune}</p>
          </div>

          {/* BÂTI — bandeau à 4 chiffres (grammaire de l'en-tête de fiche) : les nombres ne se coupent jamais */}
          <div data-secteur-bati className="rounded-lg border border-mint/25 bg-mint/[0.05] p-2.5">
            <p className="label-caps mb-1.5 text-txt-dim">Prix du secteur — bâti</p>
            {sb ? (
              <>
                <div className="stats" data-secteur-bati-stats>
                  <Cell l="Bâti secteur" v={`${fmtInt(sb.median_eur_m2 ?? 0)} €/m²`} sub={sb.type_prix ?? undefined} />
                  <Cell l="Rayon" v={sb.rayon_m != null ? `${fmtInt(sb.rayon_m)} m` : '—'} sub={sb.commune_seule ? 'repli commune' : 'adaptatif'} />
                  <Cell l="Ventes" v={sb.n != null ? fmtInt(sb.n) : '—'} sub={sb.periode ? `${sb.periode[0]}–${sb.periode[1]}` : undefined} />
                  <Cell l="Tendance 12 m" v={sb.tendance_pct != null ? `${sb.tendance_pct > 0 ? '+' : ''}${sb.tendance_pct} %` : '—'} sub={sb.tendance ?? undefined} />
                </div>
                {/* l'écart avec la commune entière, expliqué en une ligne (le secteur n'est pas la commune) */}
                {sb.ecart_commune && (
                  <p data-secteur-ecart-commune className="mt-1.5 text-[11px] text-txt-mut">
                    {sb.ecart_commune.phrase}
                    {sb.ecart_commune.ecart_pct != null && (
                      <span className={`ml-1 font-medium ${sb.ecart_commune.ecart_pct < 0 ? 'text-mint' : 'text-amber'}`}>
                        {sb.ecart_commune.ecart_pct < 0 ? 'sous' : 'au-dessus de'} la commune
                      </span>
                    )}
                  </p>
                )}
                <DistribNote d={sb.distribution} />
              </>
            ) : <p className="mt-1 text-[12px] italic text-txt-dim">échantillon bâti insuffisant dans le rayon.</p>}
          </div>

          {/* PAR TYPE — cases alignées, mêmes cellules que le bandeau (jamais un nombre coupé) */}
          <div>
            <p className="label-caps mb-1 text-txt-dim">Médiane locale par type</p>
            <div className="stats" data-secteur-par-type>
              {typeCell('Maison', d.par_type.maison)}
              {typeCell('Appartement', d.par_type.appartement)}
              {typeCell('Terrain nu', d.par_type.terrain_nu)}
            </div>
          </div>

          {/* RADAR — annonces actives dans le rayon */}
          <div data-secteur-radar>
            <p className="label-caps mb-1 text-txt-dim">Annonces Radar dans le rayon · {d.annonces_radar.length}</p>
            {d.annonces_radar.length === 0 ? (
              <p className="text-[11.5px] text-txt-dim">Aucune annonce Radar rattachée dans un rayon de 1,5 km pour l'instant — l'outil s'enrichit à chaque dépôt.</p>
            ) : (
              <div className="flex flex-col gap-1">
                {d.annonces_radar.map((a, i) => (
                  <div key={i} className="flex items-center gap-2 rounded-md border border-line-2 bg-surface-2 px-2.5 py-1.5">
                    <span className="flex-1 text-[12px] text-txt">{a.type_bien} · {a.commune}{a.distance_m != null ? ` · ${a.distance_m} m` : ''}</span>
                    <span className="whitespace-nowrap font-mono text-[11.5px] text-txt-mut">{a.prix != null ? `${fmtInt(a.prix)} €` : '—'}{a.prix_m2_affiche != null ? ` · ${fmtInt(a.prix_m2_affiche)} €/m²` : ''}</span>
                    {a.ecart_pct != null && <span className={`whitespace-nowrap font-mono text-[11.5px] ${a.ecart_pct < 0 ? 'text-mint' : 'text-st-ecartee'}`}>{a.ecart_pct > 0 ? '+' : ''}{a.ecart_pct} %</span>}
                  </div>
                ))}
              </div>
            )}
          </div>

          <p className="text-[10.5px] leading-snug text-txt-dim">{d.sources.join(' · ')}. {d.note}</p>
        </>
      )}
    </div>
  )
}
