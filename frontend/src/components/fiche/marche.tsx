/**
 * fiche/marche.tsx — RETOURS-11F4 (découpe de Fiche.tsx, section F7).
 * « Marché et secteur », recentrée sur le PRIX (cible F7 + doctrine F0 « un fait, une section ») :
 *  - terrain nu secteur (valeur d'en-tête), bâti secteur par type (marcheLines), neuf VEFA commune,
 *  - PRIX DE SORTIE bâti secteur (fait UNIQUE ici ; la Constructibilité y renvoie, cf. F5),
 *  - ventes < 100 m (voisinage proche) — le nombre de PERMIS en est retiré (les permis vivent dans
 *    « Autour », un seul tableau, F0),
 *  - le contexte SOCIO-ÉCO (Filosofi + parc social) et l'historique permis de la parcelle DÉMÉNAGENT
 *    vers « Autour de cette parcelle » (F0) — Marché ne porte plus que du prix.
 * Auto-suffisante : re-dérive dvfSecteur + marcheLines depuis `f` ; bilan via queryKey ['bilan',idu].
 */
import { useQuery } from '@tanstack/react-query'
import { getFaisabilite } from '../../lib/api'
import { fmtInt } from '../../lib/format'
import type { Fiche } from '../../lib/types'
import { EMPTY_FILTERS, useApp } from '../../store/useApp'
import { IC, RefDrawer, MicroSpark, Line, PorteOutil, GroupLabel, FactRow, FactNote } from './primitives'

export function MarcheSection({ f, idu }: { f: Fiche; idu: string }) {
  const setModule = useApp((s) => s.setModule)
  const setParcelPrefill = useApp((s) => s.setParcelPrefill)
  const setFlyTo = useApp((s) => s.setFlyTo)
  const select = useApp((s) => s.select)
  const faisa = useQuery({ queryKey: ['bilan', idu], queryFn: () => getFaisabilite(idu), enabled: !!f })
  // SECTEUR = prix du TERRAIN NU SEUL (dvf_marche `bati_m2=0`) — jamais moyenné avec le bâti (M137-G).
  const dvfSecteur = f.dvf_parcelle?.secteur?.find((s) => s.type_bien === 'terrain')
  const marcheLines = f.lines.filter((l) => l.onglet === 'marche')
  const mb = faisa.data?.marche
  const horizon = mb?.fraicheur?.horizon_libelle || mb?.dvf_couverture?.libelle
  const contexte = (dvfSecteur?.n_ventes ? `${dvfSecteur.n_ventes} vente${dvfSecteur.n_ventes > 1 ? 's' : ''} secteur` : 'comparables DVF') + (horizon ? ` · DVF — ${horizon}` : '')
  return (
    <RefDrawer id="marche" icon={IC.marche} name="Marché et secteur"
      context={contexte}
      value={dvfSecteur?.mediane_prix_m2 != null ? `${fmtInt(dvfSecteur.mediane_prix_m2)} €/m²` : '—'}
      micro={<MicroSpark label={contexte} />}>
      {marcheLines.length
        ? <div className="flex flex-col gap-1">{marcheLines.map((l, i) => <Line key={i} line={l} hideWeight hideDate />)}</div>
        : <p className="text-xs text-txt-dim">Aucun signal sur cet onglet.</p>}
      {/* RETOURS-11F4 F7/F0 — PRIX DE SORTIE bâti secteur : le fait vit ICI (la Constructibilité y renvoie).
          Même moteur que le bilan (`marche.median`). Sous le seuil : dit tel quel, jamais un chiffre inventé.
          RETOURS-20 Z1·03 — plus de boîte : FactRow (valeur mono à droite), méthode en FactNote. */}
      {mb?.median != null && (
        <div data-prix-sortie>
          <FactRow label="Prix de sortie — bâti secteur" value={<>{fmtInt(Number(mb.median))} <small>€/m²</small></>} />
          <FactNote>{mb.type_prix}, {mb.n} ventes ≤ {Math.round(mb.radius_m)} m (rayon adaptatif) · fiabilité {mb.fiabilite}{mb.tendance ? ` · tendance ${mb.tendance}` : ''}{horizon ? ` · DVF — ${horizon}` : ''}</FactNote>
        </div>
      )}
      {/* NEUF (VEFA) commune — grandeur nommée, effectif, fenêtre ; sous le seuil : « échantillon insuffisant ». */}
      {(() => { const nv = f.dvf_parcelle?.neuf_vefa
        return nv ? (
          <div data-fiche-neuf-vefa>
            {nv.effectif_suffisant && nv.mediane_prix_m2_bati != null ? (
              <FactRow label="Neuf (VEFA) — commune" value={<>{fmtInt(nv.mediane_prix_m2_bati)} <small>€/m² bâti</small></>}
                src={<>{nv.n} ventes / {nv.fenetre_ans} ans</>} />
            ) : (
              <FactRow label="Neuf (VEFA) — commune" tone="mute" value={nv.insuffisant_libelle} />
            )}
            <FactNote>{nv.grandeur} · {nv.reserve}</FactNote>
          </div>
        ) : null })()}
      {/* signal de marché condensé (DVF actes + Sitadel) — jamais un mot nu. */}
      {(() => { const sig = (f as unknown as { market_signal?: Record<string, any> }).market_signal
        return sig?.disponible ? (
          <div data-fiche-market-signal>
            <GroupLabel>Signal de marché : {sig.label}</GroupLabel>
            {(sig.composantes as Record<string, any>[]).map((c, i) => (
              <FactRow key={i} label={<>{c.sens} {c.cle}</>} value={c.valeur} />
            ))}
            <FactNote>{sig.source} · outil « Marché » pour le détail commune</FactNote>
          </div>
        ) : null })()}
      {/* Ventes < 100 m (proximité) — RETOURS-11F4 F7/F0 : le NOMBRE DE PERMIS est retiré ici (les permis
          à proximité vivent dans « Autour », un seul tableau). Marché ne garde que les VENTES. */}
      {f.voisinage_proche && !f.voisinage_proche.indisponible && f.voisinage_proche.ventes_dvf > 0 && (
        <div data-voisinage-proche>
          <GroupLabel>📍 Ventes à moins de 100 m</GroupLabel>
          <FactRow label={<>Ventes <span className="text-txt-dim">(&lt; 100 m, 36 mois)</span></>}
            value={<>{f.voisinage_proche.ventes_dvf} <small>vente(s)</small></>}
            src={f.voisinage_proche.honnetete} />
          {(f.voisinage_proche.prix_median_eur || f.voisinage_proche.prix_note) && (
            <FactRow label="Prix médian"
              value={f.voisinage_proche.prix_median_eur ? <>~{Math.round(f.voisinage_proche.prix_median_eur / 1000)} <small>k€</small></> : f.voisinage_proche.prix_note}
              tone={f.voisinage_proche.prix_median_eur ? undefined : 'mute'} />
          )}
        </div>
      )}
      {/* PORTES — Voir marché commune, Taxe, secteur opportunités, Comparer, Remonter le temps. */}
      {f.commune && (
        <PorteOutil ico="↗" data="marche" titre={`Voir le marché de ${f.commune}`}
          sous="La fiche commune complète — marché (9 lignes sourcées), rareté et horizon ZAN, rythme d’instruction"
          onClick={() => { const st = useApp.getState(); st.setCommune(f.commune!); st.setContexteCommune(f.commune!) }} />
      )}
      <PorteOutil ico="€" data="taxe-amenagement" titre="Taxe d'aménagement"
        sous={`Estimation détaillée pour un projet ici${f.commune ? ` (${f.commune})` : ''} — barème officiel daté, taux jamais inventés`}
        onClick={() => setModule('taxe-amenagement')} />
      {f.secteur_opportunites && f.secteur_opportunites.n > 0 && f.commune && (
        <button data-secteur-opp
          onClick={() => {
            const st = useApp.getState()
            st.setFilters({ ...EMPTY_FILTERS, communes: [f.commune!], tiers: ['brulante', 'chaude'] })
            st.setCommune(f.commune!)
            if (f.coords) st.setFlyTo({ center: f.coords, zoom: 16 })
            st.setView('cartes'); select(null)
          }}
          className="porte-outil"
          title={`Voir les ${f.secteur_opportunites.n} parcelles Priorité ou À suivre de la section ${f.secteur_opportunites.section} sur la carte`}>
          <span className="po-ico">◈</span>
          <span style={{ minWidth: 0 }}>
            <span className="po-t block">
              <b className="tnum text-mint">{f.secteur_opportunites.n}</b> parcelle{f.secteur_opportunites.n > 1 ? 's' : ''}{' '}
              <b>Priorité</b> ou <b>À suivre</b> dans cette section
              <span className="text-txt-dim"> (n° {f.secteur_opportunites.section.slice(8)})</span></span>
          </span>
          <span className="po-arrow">→</span>
        </button>
      )}
      <PorteOutil ico="⇄" data="comparer" titre="Comparer des parcelles"
        sous="Cette parcelle chargée — ajoutez-en d'autres à comparer"
        onClick={() => { const st = useApp.getState(); st.openCompare(); st.addToCompare(idu) }} />
      {f.coords && (
        <PorteOutil ico="◷" data="temps" titre="Remonter le temps"
          sous="Ce terrain de 1950 à aujourd'hui (curseur avant/après)"
          onClick={() => { setParcelPrefill(idu); setFlyTo({ center: f.coords, zoom: 18 }); setModule('temps') }} />
      )}
    </RefDrawer>
  )
}
