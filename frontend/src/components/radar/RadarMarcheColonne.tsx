// RADAR-2 (Lot 3) — LE MARCHÉ (colonne de droite de l'écran Radar). Pour la commune du filtre, ou toute
// l'île : 4 chiffres (demandé Radar vs acté DVF, écart), table par type, « ce qui a bougé · 30 j », et
// l'écart demandé/acté par commune (barres). Le prix acté vient du moteur DVF de la fiche commune (jamais
// recalculé à part) ; sous 30 annonces l'écart s'écrit « sous le seuil » (même règle que la fiche commune).
import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import {
  getRadarBienVsMarche, getRadarMarcheTableau, radarClic,
  type EcartNiveau, type RadarBienCmp, type RadarBienVsMarche, type RadarMarcheChiffre, type RadarMarcheTypeLigne,
} from '../../lib/api'
import { fmtCapture } from './RadarHub'
import { Squelette } from '../Loading'
import { ErrorState } from '../States'

const fmt = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('fr-FR'))
const pct = (v: number | null | undefined) => (v == null ? null : `${v > 0 ? '+' : ''}${v} %`)
const TYPE_LABEL: Record<string, string> = { terrain: 'Terrain', maison: 'Maison', appartement: 'Appartement' }
// RADAR-FIX-3 — couleur d'un écart selon son signe (au-dessus = ambre, sous = menthe).
const ecartCouleur = (v: number) => (v > 0 ? 'text-amber' : 'text-mint')

// RADAR-FIX-3 — rend un écart demandé/acté selon son PALIER, MÊME règle partout :
//   'normal'      → « +X % » coloré ;
//   'indicatif'   → « +X % » en GRIS + « indicatif · n = N » (5 à 29 annonces) ;
//   'insuffisant' → « sous le seuil » (< 5 annonces).
function EcartTexte({ pctv, niveau, n, taille = 'text-[10.5px]' }: {
  pctv: number | null; niveau: EcartNiveau; n: number; taille?: string
}) {
  if (niveau === 'insuffisant' || pctv == null) return <span className={taille}>sous le seuil</span>
  if (niveau === 'indicatif')
    return <span className={`${taille} text-txt-dim`}>{pct(pctv)} · indicatif · n = {n}</span>
  return <span className={`tabular-nums ${ecartCouleur(pctv)}`}>{pct(pctv)}</span>
}

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
      <td className="text-right tabular-nums">
        <EcartTexte pctv={l.ecart_pct} niveau={l.ecart_niveau} n={l.ecart_n} />
      </td>
      <td className="text-right tabular-nums text-txt-mut">{l.sup_90j}</td>
      <td className="text-right tabular-nums text-txt-mut">{l.baisses_30j}</td>
    </tr>
  )
}

export function RadarMarcheColonne({ commune, bienId, onCloseBien }: {
  commune: string | null; bienId?: number | null; onCloseBien?: () => void
}) {
  const [ile, setIle] = useState(false)
  // RADAR-2 (retouches 2) — une seule vue : quand une annonce est sélectionnée, on récupère d'abord son
  // marché (pour connaître SA commune) ; le marché de la colonne bascule alors sur cette commune.
  const bien = useQuery({
    queryKey: ['radar-bien-vs-marche', bienId], queryFn: () => getRadarBienVsMarche(bienId!),
    enabled: bienId != null,
  })
  const bienData = bienId != null && bien.data && !bien.data.introuvable ? bien.data : null
  useEffect(() => { if (bienId != null) setIle(false) }, [bienId])

  // portée du marché : SA commune si une annonce est sélectionnée, sinon la commune du filtre (bascule île).
  const scopeCommune = bienData?.commune ?? commune
  const scope = scopeCommune && !ile ? scopeCommune : null
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['radar-marche-tableau', scope], queryFn: () => getRadarMarcheTableau(scope || undefined),
  })

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-7 py-6">
      {/* ── CE BIEN — inséré en tête de colonne, au-dessus des 4 chiffres, quand une annonce est choisie ── */}
      {bienId != null && <CeBienBloc loading={bien.isLoading} error={bien.isError} bien={bienData} onClose={onCloseBien} />}

      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <div className="font-mono text-[10.5px] tracking-[0.2em] text-txt-mut">LE MARCHÉ</div>
          <h2 className="mt-1 text-[20px] font-semibold text-txt-hi">
            {scope ?? 'Toute l’île'} · ce qui est demandé, ce qui se vend
          </h2>
        </div>
        {scopeCommune && (
          <div className="flex shrink-0 overflow-hidden rounded-full border border-line-2">
            <button data-marche-scope-commune onClick={() => setIle(false)} className={`px-3 py-1 text-[12px] ${!ile ? 'bg-mint text-mint-on font-medium' : 'text-txt-mut hover:text-txt'}`}>{scopeCommune}</button>
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
              sous={`médiane DVF${data.prix_acte_median_eur_m2.periode ? ` · ${data.prix_acte_median_eur_m2.periode}` : ''} · ${data.prix_acte_median_eur_m2.n} vente${data.prix_acte_median_eur_m2.n > 1 ? 's' : ''}`} />
            <div className="rounded-lg border border-line-2 bg-surface-2 px-4 py-3.5">
              <div className="font-mono text-[9.5px] uppercase tracking-[0.12em] text-txt-mut">Écart demandé / acté</div>
              <div className="mt-1.5 text-[24px] font-bold tabular-nums">
                {data.ecart_niveau === 'insuffisant' || data.ecart_demande_acte_pct == null
                  ? <span className="text-[15px] font-medium text-txt-dim">sous le seuil</span>
                  : <span className={data.ecart_niveau === 'indicatif' ? 'text-txt-dim' : ecartCouleur(data.ecart_demande_acte_pct)}>{pct(data.ecart_demande_acte_pct)}</span>}
              </div>
              <div className="mt-1 text-[11px] leading-snug text-txt-dim">
                {data.ecart_niveau === 'insuffisant' ? `sous ${data.seuil_indicatif_n} annonces`
                  : data.ecart_niveau === 'indicatif' ? `indicatif · n = ${data.ecart_n}`
                  : 'marge de négociation probable'}
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
                <p className="text-[11px] text-txt-dim">Aucune commune n’atteint {data.seuil_indicatif_n} annonces maisons en vente.</p>
              ) : (
                <div className="flex flex-col gap-1.5">
                  {/* RADAR-FIX-3 — maison contre maison (même calcul que le tableau) ; barre ambre si
                      au-dessus, menthe si sous, GRISE si indicatif (5–29 annonces) ; le n est affiché. */}
                  {data.ecart_par_commune.map((e) => {
                    const w = Math.min(100, Math.abs(e.ecart_pct) * 2.2)
                    const gris = e.niveau === 'indicatif'
                    const barre = gris ? 'bg-line-3' : e.ecart_pct > 0 ? 'bg-amber' : 'bg-mint'
                    const txt = gris ? 'text-txt-dim' : ecartCouleur(e.ecart_pct)
                    return (
                      <div key={e.commune} className="flex items-center gap-2 text-[11.5px]">
                        <span className="w-[92px] shrink-0 truncate text-txt-mut">{e.commune}</span>
                        <span className={`h-2.5 rounded-full ${barre}`} style={{ width: `${w}%`, minWidth: 6 }} />
                        <span className={`ml-auto shrink-0 tabular-nums ${txt}`}>
                          {pct(e.ecart_pct)}{gris && <span className="ml-1 text-[10px] text-txt-dim">· n = {e.n}</span>}
                        </span>
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
            Prix actés : DVF (DGFiP){data.millesime_dvf ? ` — ${data.millesime_dvf}` : ''}. L’écart est « indicatif »
            de {data.seuil_indicatif_n} à {data.seuil_ecart_n - 1} annonces, ferme à {data.seuil_ecart_n}, « sous le seuil » en deçà.
            Les appartements comptent dans les chiffres mais ne sont pas listés.
          </p>
        </>
      )}
    </div>
  )
}

// ══════════════ CE BIEN (bloc compact, en tête de la colonne marché quand une annonce est choisie) ══════════════
const TYPE_MOT: Record<string, string> = { terrain: 'terrains', maison: 'maisons', appartement: 'appartements' }

// un écart du bien vs une médiane (demandée/actée), sur une ligne. RADAR-FIX-3 — MÊME palier que le
// tableau : « +12 % » coloré (normal), gris « +12 % · indicatif · n=… » (5–29), « sous le seuil » (<5).
function EcartInline({ label, cmp }: { label: string; cmp: RadarBienCmp }) {
  return (
    <span className="text-txt-mut">
      {label}{' '}
      {cmp.niveau === 'insuffisant' || cmp.median == null
        ? <span className="text-txt-dim">sous le seuil</span>
        : cmp.ecart_pct == null
          ? <span className="tabular-nums text-txt">{fmt(cmp.median)} €/m²</span>
          : cmp.niveau === 'indicatif'
            ? <span className="text-txt-dim">{pct(cmp.ecart_pct)} · indicatif · n = {cmp.n}</span>
            : <span className={`font-medium ${ecartCouleur(cmp.ecart_pct)}`}>{pct(cmp.ecart_pct)}</span>}
    </span>
  )
}

// le bloc « Ce bien » : €/m², prix, écart vs demandé/acté (commune + type), ancienneté, historique en une
// ligne, « Voir l'annonce ↗ », croix pour fermer. Compact : il coiffe la colonne, ne la remplace pas.
function CeBienBloc({ loading, error, bien, onClose }: {
  loading: boolean; error: boolean; bien: RadarBienVsMarche | null; onClose?: () => void
}) {
  const baisses = (bien?.historique_prix ?? []).filter((h) => (h.nouveau ?? 0) < (h.ancien ?? 0))
  const der = baisses[baisses.length - 1]
  const histLigne = baisses.length === 0
    ? 'aucune baisse enregistrée'
    : `${baisses.length} baisse${baisses.length > 1 ? 's' : ''}${der ? ` · ${fmt(der.ancien)} → ${fmt(der.nouveau)} €` : ''}`
  return (
    <div data-ce-bien className="mb-4 rounded-lg border border-mint/40 bg-mint/[0.05] px-4 py-3.5">
      <div className="flex items-start justify-between gap-3">
        <div className="font-mono text-[9.5px] uppercase tracking-[0.14em] text-mint">Ce bien</div>
        <button data-ce-bien-fermer aria-label="Fermer" onClick={onClose}
          className="-mr-1 -mt-1 grid h-6 w-6 place-items-center rounded text-txt-dim hover:text-txt">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M5 5l14 14M19 5L5 19" /></svg>
        </button>
      </div>
      {loading && <div className="mt-2"><Squelette lignes={2} /></div>}
      {error && <p className="mt-2 text-[11.5px] text-txt-dim">Comparaison indisponible.</p>}
      {!loading && !error && bien == null && <p className="mt-2 text-[11.5px] text-txt-dim">Ce bien n’est plus servi.</p>}
      {bien && (
        <>
          <div className="mt-1 flex flex-wrap items-end gap-x-2">
            <span className="text-[22px] font-bold tabular-nums text-txt-hi">{bien.eur_m2 != null ? `${fmt(bien.eur_m2)} €/m²` : '—'}</span>
            <span className="pb-0.5 text-[12px] text-txt-mut">{bien.prix != null ? `${fmt(bien.prix)} €` : ''}{bien.type_bien ? ` · ${TYPE_LABEL[bien.type_bien] ?? bien.type_bien}` : ''}</span>
          </div>
          <div className="mt-2 text-[9.5px] uppercase tracking-wide text-txt-dim">Écart · {bien.commune} · {TYPE_MOT[bien.type_bien ?? ''] ?? 'même type'}</div>
          <div className="mt-0.5 flex flex-wrap gap-x-4 gap-y-1 text-[11.5px]">
            <EcartInline label="vs demandé" cmp={bien.demande} />
            <EcartInline label="vs acté" cmp={bien.acte} />
          </div>
          <div className="mt-1.5 text-[11px] leading-snug text-txt-dim">
            {bien.anciennete_j != null ? `En vente depuis ${bien.anciennete_j} j` : 'Ancienneté inconnue'}
            {bien.anciennete_mediane_j != null && !bien.anciennete_sous_seuil ? ` · médiane commune ${bien.anciennete_mediane_j} j` : ''}
            {' · '}{histLigne}
          </div>
          <a onClick={(e) => { e.preventDefault(); radarClic(bien.bien_id).catch(() => {}); window.open(bien.url_sortante, '_blank', 'noopener,noreferrer') }}
            href={bien.url_sortante} target="_blank" rel="noopener noreferrer"
            data-ce-bien-portail className="mt-2 inline-flex text-[12px] font-medium text-[#E7B008] underline decoration-[#E7B008]/40 underline-offset-2 hover:decoration-[#E7B008]">
            Voir l’annonce ↗
          </a>
        </>
      )}
    </div>
  )
}
