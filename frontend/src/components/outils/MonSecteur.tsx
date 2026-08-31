// SECTEUR-1 (S1) — outil « Mon secteur » : une adresse / un IDU → les prix DU SECTEUR autour de la
// parcelle (médiane locale DVF par type + tendance 12 mois + annonces Radar dans le rayon). Un seul
// moteur (sector_price / _ref_local, côté back) ; chaque chiffre porte son n et son millésime, absent
// sous le seuil. Rien en dur : tout vient de /outils/mon-secteur.
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getMonSecteur, type LocalMed } from '../../lib/api'
import { ParcelInput } from '../ParcelInput'
import { fmtInt } from '../../lib/format'
import { Loading } from '../Loading'

function Med({ titre, m }: { titre: string; m: LocalMed | null }) {
  return (
    <div className="rounded-lg border border-line-2 bg-surface-2 p-3">
      <p className="text-[11px] text-txt-mut">{titre}</p>
      {m ? (
        <>
          <p className="font-display text-lg font-bold text-txt-hi">{fmtInt(m.eur_m2)} €/m²</p>
          <p className="text-[10.5px] text-txt-dim">{m.perimetre} · {m.n} ventes{m.millesime ? ` · ${m.millesime}` : ''}</p>
        </>
      ) : (
        <p className="mt-1 text-[12px] italic text-txt-dim">échantillon insuffisant (&lt; 5 ventes)</p>
      )}
    </div>
  )
}

export function MonSecteur() {
  const [idu, setIdu] = useState<string | null>(null)
  const q = useQuery({ queryKey: ['mon-secteur', idu], queryFn: () => getMonSecteur(idu!), enabled: !!idu })
  const d = q.data

  return (
    <div data-mon-secteur className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-1 text-[12.5px]">
      <div>
        <h2 className="font-display text-base font-bold text-txt-hi">Mon secteur</h2>
        <p className="mt-0.5 text-[11.5px] text-txt-mut">Les prix DU SECTEUR autour d'une parcelle — médiane locale DVF par type, tendance 12 mois, annonces Radar dans le rayon. S'enrichit au fil des dépôts.</p>
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

          {/* BÂTI — le moteur « Marché et secteur » de la fiche parcelle */}
          <div data-secteur-bati className="rounded-lg border border-mint/25 bg-mint/[0.05] p-3">
            <p className="label-caps text-txt-dim">Prix du secteur — bâti</p>
            {d.secteur_bati ? (
              <>
                <p className="mt-1 font-display text-xl font-bold text-txt-hi">{fmtInt(d.secteur_bati.median_eur_m2)} €/m²</p>
                <p className="text-[11px] text-txt-mut">
                  {d.secteur_bati.type_prix} · {d.secteur_bati.n} ventes · rayon {d.secteur_bati.rayon_m} m
                  {d.secteur_bati.periode ? ` · ${d.secteur_bati.periode[0]}–${d.secteur_bati.periode[1]}` : ''}
                  {d.secteur_bati.commune_seule ? ' · repli commune' : ''}
                </p>
                {d.secteur_bati.tendance_pct != null && (
                  <p className="mt-1 text-[12px]">Tendance 12 mois : <b className={d.secteur_bati.tendance_pct < 0 ? 'text-st-ecartee' : 'text-mint'}>{d.secteur_bati.tendance_pct > 0 ? '+' : ''}{d.secteur_bati.tendance_pct} %</b> <span className="text-txt-dim">({d.secteur_bati.tendance})</span></p>
                )}
              </>
            ) : <p className="mt-1 text-[12px] italic text-txt-dim">échantillon bâti insuffisant dans le rayon.</p>}
          </div>

          {/* PAR TYPE — médiane locale (FICHE-COMMUNE-2 C5) */}
          <div className="grid grid-cols-3 gap-2">
            <Med titre="Maison" m={d.par_type.maison} />
            <Med titre="Appartement" m={d.par_type.appartement} />
            <Med titre="Terrain nu" m={d.par_type.terrain_nu} />
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
                    <span className="font-mono text-[11.5px] text-txt-mut">{a.prix != null ? `${fmtInt(a.prix)} €` : '—'}{a.prix_m2_affiche != null ? ` · ${fmtInt(a.prix_m2_affiche)} €/m²` : ''}</span>
                    {a.ecart_pct != null && <span className={`font-mono text-[11.5px] ${a.ecart_pct < 0 ? 'text-mint' : 'text-st-ecartee'}`}>{a.ecart_pct > 0 ? '+' : ''}{a.ecart_pct} %</span>}
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
