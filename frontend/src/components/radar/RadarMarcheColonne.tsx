// RADAR-2 (Lot 3) — LE MARCHÉ (colonne de droite de l'écran Radar). Pour la commune du filtre, ou toute
// l'île : 4 chiffres (demandé Radar vs acté DVF, écart), table par type, « ce qui a bougé · 30 j », et
// l'écart demandé/acté par commune (barres). Le prix acté vient du moteur DVF de la fiche commune (jamais
// recalculé à part) ; sous 30 annonces l'écart s'écrit « sous le seuil » (même règle que la fiche commune).
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import {
  getRadarBienVsMarche, getRadarMarcheTableau, radarClic,
  type RadarBienCmp, type RadarMarcheChiffre, type RadarMarcheTypeLigne,
} from '../../lib/api'
import { fmtCapture } from './RadarHub'
import { Squelette } from '../Loading'
import { ErrorState } from '../States'
import { Retour } from '../ui/Retour'

const fmt = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('fr-FR'))
const pct = (v: number | null | undefined) => (v == null ? null : `${v > 0 ? '+' : ''}${v} %`)
const TYPE_LABEL: Record<string, string> = { terrain: 'Terrain', maison: 'Maison', appartement: 'Appartement' }

function Chiffre({ surtitre, chiffre, unite, sous, sousSeuil }: {
  surtitre: string; chiffre: RadarMarcheChiffre | null; unite: string; sous: string; sousSeuil?: boolean
}) {
  const vide = !chiffre || chiffre.valeur == null || sousSeuil
  return (
    <div className="rounded-lg border border-line-2 bg-surface-2 px-4 py-3.5">
      <div className="font-mono text-[9.5px] uppercase tracking-[0.12em] text-txt-mut">{surtitre}</div>
      <div className="mt-1.5 text-[24px] font-bold tabular-nums text-txt-hi">
        {vide ? <span className="text-[15px] font-medium text-txt-dim">sous le seuil</span>
          : <>{fmt(chiffre!.valeur)}<span className="ml-0.5 text-[13px] font-normal text-txt-mut">{unite}</span></>}
      </div>
      <div className="mt-1 text-[11px] leading-snug text-txt-dim">{sous}</div>
    </div>
  )
}

function LigneType({ l }: { l: RadarMarcheTypeLigne }) {
  return (
    <tr className="border-b border-line-2 text-txt">
      <td className="py-2 pr-2">
        {TYPE_LABEL[l.type] ?? l.type}
        {l.type === 'appartement' && <span className="ml-1 block text-[9.5px] text-txt-dim">statistiques seules</span>}
      </td>
      <td className="text-right tabular-nums">{l.en_vente}</td>
      <td className="text-right tabular-nums">{l.demande_eur_m2 == null ? '—' : fmt(l.demande_eur_m2)}</td>
      <td className="text-right tabular-nums text-txt-mut">{l.acte_eur_m2 == null ? '—' : fmt(l.acte_eur_m2)}</td>
      <td className={`text-right tabular-nums ${l.ecart_pct != null && l.ecart_pct > 0 ? 'text-amber' : l.ecart_pct != null ? 'text-mint' : 'text-txt-dim'}`}>
        {l.ecart_sous_seuil || l.ecart_pct == null ? <span className="text-[10.5px]">sous le seuil</span> : pct(l.ecart_pct)}
      </td>
      <td className="text-right tabular-nums text-txt-mut">{l.sup_90j}</td>
      <td className="text-right tabular-nums text-txt-mut">{l.baisses_30j}</td>
    </tr>
  )
}

export function RadarMarcheColonne({ commune }: { commune: string | null }) {
  // portée du marché : la commune du filtre, ou toute l'île (bascule locale).
  const [ile, setIle] = useState(false)
  const scope = commune && !ile ? commune : null
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['radar-marche-tableau', scope], queryFn: () => getRadarMarcheTableau(scope || undefined),
  })

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-7 py-6">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <div className="font-mono text-[10.5px] tracking-[0.2em] text-txt-mut">LE MARCHÉ</div>
          <h2 className="mt-1 text-[20px] font-semibold text-txt-hi">
            {scope ?? 'Toute l’île'} · ce qui est demandé, ce qui se vend
          </h2>
        </div>
        {commune && (
          <div className="flex shrink-0 overflow-hidden rounded-full border border-line-2">
            <button data-marche-scope-commune onClick={() => setIle(false)} className={`px-3 py-1 text-[12px] ${!ile ? 'bg-mint text-mint-on font-medium' : 'text-txt-mut hover:text-txt'}`}>{commune}</button>
            <button data-marche-scope-ile onClick={() => setIle(true)} className={`px-3 py-1 text-[12px] ${ile ? 'bg-mint text-mint-on font-medium' : 'text-txt-mut hover:text-txt'}`}>Toute l’île</button>
          </div>
        )}
      </div>

      {isLoading && <Squelette lignes={8} />}
      {isError && <ErrorState message="Le marché n’a pas pu être chargé." retry={() => refetch()} />}
      {data && (
        <>
          {/* 4 chiffres (maisons) */}
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Chiffre surtitre="Prix demandé · maisons" chiffre={data.prix_demande_median_eur_m2} unite="€/m²"
              sous={`médiane · ${data.prix_demande_median_eur_m2.n} annonce${data.prix_demande_median_eur_m2.n > 1 ? 's' : ''}`} />
            <Chiffre surtitre="Prix acté · maisons" chiffre={data.prix_acte_median_eur_m2} unite="€/m²"
              sous={`médiane DVF · 12 mois · ${data.prix_acte_median_eur_m2.n} vente${data.prix_acte_median_eur_m2.n > 1 ? 's' : ''}`} />
            <div className="rounded-lg border border-line-2 bg-surface-2 px-4 py-3.5">
              <div className="font-mono text-[9.5px] uppercase tracking-[0.12em] text-txt-mut">Écart demandé / acté</div>
              <div className="mt-1.5 text-[24px] font-bold tabular-nums">
                {data.ecart_sous_seuil || data.ecart_demande_acte_pct == null
                  ? <span className="text-[15px] font-medium text-txt-dim">sous le seuil</span>
                  : <span className={data.ecart_demande_acte_pct > 0 ? 'text-amber' : 'text-mint'}>{pct(data.ecart_demande_acte_pct)}</span>}
              </div>
              <div className="mt-1 text-[11px] leading-snug text-txt-dim">
                {data.ecart_sous_seuil ? `sous ${data.seuil_ecart_n} annonces` : 'marge de négociation probable'}
              </div>
            </div>
            <div className="rounded-lg border border-line-2 bg-surface-2 px-4 py-3.5">
              <div className="font-mono text-[9.5px] uppercase tracking-[0.12em] text-txt-mut">Biens en vente</div>
              <div className="mt-1.5 text-[24px] font-bold tabular-nums text-txt-hi">{data.biens_en_vente}</div>
              <div className="mt-1 text-[11px] leading-snug text-txt-dim">dont {data.biens_sup_90j} depuis plus de 90 j</div>
            </div>
          </div>

          {/* table par type */}
          <div className="mt-5 rounded-lg border border-line-2 bg-surface-2 px-4 py-3">
            <div className="mb-1.5 label-caps">Par type de bien</div>
            <table className="w-full border-collapse text-[12px]">
              <thead>
                <tr className="border-b border-line-3 font-mono text-[9px] uppercase tracking-wider text-txt-dim">
                  <th className="py-1 text-left">Type</th><th className="text-right">En vente</th>
                  <th className="text-right">Demandé €/m²</th><th className="text-right">Acté €/m² (DVF)</th>
                  <th className="text-right">Écart</th><th className="text-right">&gt; 90 j</th><th className="text-right">Baisses 30 j</th>
                </tr>
              </thead>
              <tbody>{data.par_type.map((l) => <LigneType key={l.type} l={l} />)}</tbody>
            </table>
          </div>

          <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-2">
            {/* ce qui a bougé · 30 j */}
            <div className="rounded-lg border border-line-2 bg-surface-2 px-4 py-3">
              <div className="mb-2 label-caps">Ce qui a bougé · 30 jours</div>
              <div className="grid grid-cols-4 gap-2 text-center">
                {([['nouvelles', data.bouge_30j.nouvelles], ['baisses', data.bouge_30j.baisses],
                   ['retirées', data.bouge_30j.retirees], ['de retour', data.bouge_30j.de_retour]] as const).map(([lab, n]) => (
                  <div key={lab}>
                    <div className="text-[20px] font-bold tabular-nums text-txt-hi">{n}</div>
                    <div className="text-[10.5px] text-txt-dim">{lab}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* écart demandé / acté par commune */}
            <div className="rounded-lg border border-line-2 bg-surface-2 px-4 py-3">
              <div className="mb-2 label-caps">Écart demandé / acté · maisons, par commune</div>
              {data.ecart_par_commune.length === 0 ? (
                <p className="text-[11px] text-txt-dim">Aucune commune n’atteint le seuil de {data.seuil_ecart_n} annonces.</p>
              ) : (
                <div className="flex flex-col gap-1.5">
                  {data.ecart_par_commune.map((e) => {
                    const w = Math.min(100, Math.abs(e.ecart_pct) * 2.2)
                    return (
                      <div key={e.commune} className="flex items-center gap-2 text-[11.5px]">
                        <span className="w-[92px] shrink-0 truncate text-txt-mut">{e.commune}</span>
                        <span className="h-2.5 rounded-full bg-amber" style={{ width: `${w}%`, minWidth: 6 }} />
                        <span className="ml-auto shrink-0 tabular-nums text-amber">{pct(e.ecart_pct)}</span>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>

          {/* pied de colonne */}
          <p className="mt-5 text-[10.5px] leading-relaxed text-txt-dim">
            Prix demandés : annonces collectées sur les portails, dernière capture le {fmtCapture(data.derniere_capture_at)}.
            Prix actés : DVF (DGFiP){data.millesime_dvf ? ` — ${data.millesime_dvf}` : ''}. Sous {data.seuil_ecart_n} biens,
            l’écart n’est pas calculé. Les appartements comptent dans les chiffres mais ne sont pas listés.
          </p>
        </>
      )}
    </div>
  )
}

// ══════════════ CE BIEN FACE À SON MARCHÉ (colonne de droite quand une annonce est sélectionnée) ══════════════
const TYPE_MOT: Record<string, string> = { terrain: 'terrains', maison: 'maisons', appartement: 'appartements' }

// une ligne de comparaison : la médiane (demandée/actée) + l'écart du bien, ou « sous le seuil ».
function LigneCmp({ titre, cmp }: { titre: string; cmp: RadarBienCmp }) {
  return (
    <div className="flex items-center justify-between border-b border-line-2 py-2 last:border-0">
      <span className="text-[12px] text-txt-mut">{titre}</span>
      {cmp.sous_seuil || cmp.median == null ? (
        <span className="text-[11.5px] text-txt-dim">sous le seuil ({cmp.n})</span>
      ) : (
        <span className="text-[12.5px] tabular-nums text-txt">
          {fmt(cmp.median)} €/m²
          {cmp.ecart_pct != null && (
            <span className={`ml-2 font-medium ${cmp.ecart_pct > 0 ? 'text-amber' : 'text-mint'}`}>{pct(cmp.ecart_pct)}</span>
          )}
        </span>
      )}
    </div>
  )
}

export function BienVsMarche({ bienId, onBack }: { bienId: number; onBack: () => void }) {
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ['radar-bien-vs-marche', bienId], queryFn: () => getRadarBienVsMarche(bienId) })
  const baisses = (data?.historique_prix ?? []).filter((h) => (h.nouveau ?? 0) < (h.ancien ?? 0))
  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-7 py-6">
      <div className="mb-4">
        <Retour label={data?.commune ? `Le marché de ${data.commune}` : 'Le marché'} data-bien-retour onClick={onBack} />
      </div>
      <div className="font-mono text-[10.5px] tracking-[0.2em] text-txt-mut">RADAR › CE BIEN</div>
      <h2 className="mt-1 text-[20px] font-semibold text-txt-hi">Ce bien face à son marché</h2>

      {isLoading && <div className="mt-4"><Squelette lignes={6} /></div>}
      {isError && <div className="mt-4"><ErrorState message="Comparaison indisponible." retry={() => refetch()} /></div>}
      {data && data.introuvable && <p className="mt-4 text-[12px] text-txt-dim">Ce bien n’est plus servi.</p>}
      {data && !data.introuvable && (
        <>
          <div className="mt-4 flex items-end gap-3">
            <div className="text-[26px] font-bold tabular-nums text-txt-hi">{data.eur_m2 != null ? `${fmt(data.eur_m2)} €/m²` : '—'}</div>
            <div className="pb-1 text-[12.5px] text-txt-mut">{data.prix != null ? `${fmt(data.prix)} €` : ''}{data.type_bien ? ` · ${data.type_bien}` : ''}</div>
          </div>

          <div className="mt-4 rounded-lg border border-line-2 bg-surface-2 px-4 py-3">
            <div className="mb-1 label-caps">Son €/m² face au marché · {data.commune} · {TYPE_MOT[data.type_bien ?? ''] ?? 'même type'}</div>
            <LigneCmp titre="Médiane demandée (Radar)" cmp={data.demande} />
            <LigneCmp titre="Médiane actée (DVF)" cmp={data.acte} />
          </div>

          <div className="mt-4 rounded-lg border border-line-2 bg-surface-2 px-4 py-3">
            <div className="mb-1 label-caps">Ancienneté</div>
            <div className="flex items-center justify-between py-1">
              <span className="text-[12px] text-txt-mut">En vente depuis</span>
              <span className="text-[12.5px] tabular-nums text-txt">{data.anciennete_j != null ? `${data.anciennete_j} j` : '—'}</span>
            </div>
            <div className="flex items-center justify-between py-1">
              <span className="text-[12px] text-txt-mut">Médiane de la commune</span>
              {data.anciennete_sous_seuil || data.anciennete_mediane_j == null
                ? <span className="text-[11.5px] text-txt-dim">sous le seuil ({data.anciennete_n})</span>
                : <span className="text-[12.5px] tabular-nums text-txt">{data.anciennete_mediane_j} j</span>}
            </div>
          </div>

          <div className="mt-4 rounded-lg border border-line-2 bg-surface-2 px-4 py-3">
            <div className="mb-1 label-caps">Historique des prix</div>
            {baisses.length === 0 ? (
              <p className="text-[11.5px] text-txt-dim">Aucune baisse ni retour enregistré.</p>
            ) : (
              <div className="flex flex-col gap-1.5">
                {baisses.map((h, i) => (
                  <div key={i} className="flex items-center justify-between text-[12px]">
                    <span className="text-txt-mut">{h.date ? new Date(h.date).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: '2-digit' }) : '—'}</span>
                    <span className="tabular-nums text-txt"><span className="text-txt-dim line-through">{fmt(h.ancien ?? 0)} €</span> → {fmt(h.nouveau ?? 0)} €</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <a onClick={(e) => { e.preventDefault(); radarClic(bienId).catch(() => {}); window.open(data.url_sortante, '_blank', 'noopener,noreferrer') }}
            href={data.url_sortante} target="_blank" rel="noopener noreferrer"
            data-bien-portail className="mt-4 inline-flex text-[13px] font-medium text-[#E7B008] underline decoration-[#E7B008]/40 underline-offset-2 hover:decoration-[#E7B008]">
            Voir l’annonce ↗
          </a>
        </>
      )}
    </div>
  )
}
