import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { CINQUANTE_PAS_COLOR, EQUIP_META, LEGEND_ORDER, LEGEND_V2_ORDER, STATUT_META, TIER_V2_META, ZONE_FAM_META, ZONE_FAM_ORDER } from '../../lib/status'
import { MAP_THEME } from '../../lib/mapTheme'
import { getMapLayer } from '../../lib/api'
import { TOKENS } from '../../lib/tokens'
import { useApp } from '../../store/useApp'
import { Tip } from '../Tip'
import { ChevronSection } from '../panel/ChevronSection'

// Correctif M5 : quand un run scoring v2 existe, la carte colore par le tier v2 — la légende
// suit (mêmes couleurs que le verdict d'en-tête). Sans run (404/503), légende matrice legacy.
export function useV2Actif(): boolean {
  const q = useQuery({
    queryKey: ['v2-actif'],
    queryFn: async () => (await fetch('/v2/modele')).ok,
    retry: false, staleTime: Infinity,
  })
  return q.data === true
}

/** `inline` : rendu dans un flux (tiroir mobile) au lieu du coin de carte. Sous 640 px la
 *  légende flottante recouvrait le hero (item 1 UX V1) → elle vit dans le tiroir « Couches ».
 *
 *  M12 C6/C7 — UN SEUL panneau, plusieurs sections EMPILÉES (jamais superposées) :
 *   • Verdict (C7) : REPLIÉ PAR DÉFAUT, dépliable au clic (jamais supprimé — décision Vic) ;
 *   • Zonage PLU : visible dès qu'une des deux couches de colorisation est active ;
 *   • 50 pas géométriques ; Équipements (rapatriés de leur bloc flottant qui masquait le verdict).
 *  Le panneau est borné en hauteur et défile : les sections cohabitent sans déborder l'écran. */
export function Legend({ inline = false }: { inline?: boolean }) {
  const layers = useApp((s) => s.layers)
  const verdict = useApp((s) => s.verdict)
  const analyse = useApp((s) => s.filters.analyseLabuse)
  const peint = useApp((s) => s.mapPeint)
  const commune = useApp((s) => s.commune)
  const basemap = useApp((s) => s.basemap)
  const v2 = useV2Actif()
  // M106 : la légende des aléas dit le MILLÉSIME SERVI (jamais en dur) — même clé de requête
  // que la carte (React Query dédoublonne, aucun fetch supplémentaire) ; swatches à la teinte
  // du THÈME courant (mapTheme) pour que la légende corresponde à ce qui est peint.
  const aleaActifHook = layers.alea_inondation || layers.alea_mvt
  const aleaQ = useQuery({ queryKey: ['layer', 'georisque_alea', commune], queryFn: () => getMapLayer('georisque_alea'), enabled: aleaActifHook })
  const transQ = useQuery({ queryKey: ['layer', 'transport_ligne'], queryFn: () => getMapLayer('transport_ligne'), enabled: layers.transport })
  const polesQ = useQuery({ queryKey: ['layer', 'pole_echange'], queryFn: () => getMapLayer('pole_echange'), enabled: layers.transport })
  // le CRITÈRE du pôle dérivé voyage avec la donnée (config/transport.yaml) — jamais en dur ici
  const critereDerive = (polesQ.data?.features.find((f) => (f.properties as { subtype?: string; critere?: string }).critere)
    ?.properties as { critere?: string } | undefined)?.critere ?? 'arrêt desservi par de nombreuses lignes (dérivé GTFS)'
  const htQ = useQuery({ queryKey: ['layer', 'ligne_ht'], queryFn: () => getMapLayer('ligne_ht'), enabled: layers.lignes_ht })
  // M134 — dispositifs : millésime servi (React Query dédoublonne avec la carte, aucun fetch en plus)
  const qpvQ = useQuery({ queryKey: ['layer', 'qpv', commune], queryFn: () => getMapLayer('qpv'), enabled: layers.qpv })
  const anruQ = useQuery({ queryKey: ['layer', 'anru', commune], queryFn: () => getMapLayer('anru'), enabled: layers.anru })
  const tTheme = MAP_THEME[basemap === 'clair' ? 'clair' : 'sombre']
  const mill = (q: { data?: unknown }) => (q.data as { millesime_integration?: string } | undefined)?.millesime_integration
  const fmtMill = (m?: string) => (m ? ` · intégré le ${m.split('-').reverse().join('/')}` : '')
  const aleaMillesime = mill(aleaQ)
  // C7 : verdict REPLIÉ par défaut (libère la carte) — l'utilisateur le déplie s'il en a besoin.
  const [verdictOpen, setVerdictOpen] = useState(false)

  // M55-G point 10 — une légende n'existe que si ses couleurs sont À L'ÉCRAN (mapPeint, écrit
  // par la carte). Verdict : mode OPINION (analyse active ou couche « Verdict » cochée) ET
  // parcelles effectivement peintes ET pas recouvertes par le zonage. Mode factuel (P8) :
  // jamais. Carte île sans parcelles peintes (« Zoomez ou cliquez une commune… ») : jamais.
  const opinion = (verdict && analyse) || layers.couleurs_verdict
  const verdictPeint = opinion && peint.parcelles && !peint.zonage
  const zonagePeint = peint.zonage
  const equipPeint = peint.equipements
  // 50 pas / Renouvellement / aléas : GeoJSON sans minzoom — peints dès que la couche est active
  const aleaActif = aleaActifHook
  const dispoActif = layers.qpv || layers.tva_primo || layers.anru || layers.zfang || layers.frr   // M134
  const rien = !verdictPeint && !zonagePeint && !equipPeint && !layers.cinquante_pas && !layers.renouv
    && !aleaActif && !layers.transport && !layers.lignes_ht && !dispoActif
  if (rien) return null

  return (
    <div className={`${inline
      ? 'rounded-xl bg-surface-2 px-4 py-3'
      : 'floating absolute bottom-4 right-4 hidden max-h-[60vh] overflow-y-auto px-4 py-3 sm:block'}`}>
      {/* ── Verdict (repliable, replié par défaut — discret) ── */}
      {verdictPeint && (
        <>
          <button
            data-legend-verdict-toggle
            onClick={() => setVerdictOpen((o) => !o)}
            className="group flex w-full items-center justify-between gap-3 text-left"
            aria-expanded={verdictOpen}
            title={verdictOpen ? 'Replier la légende du verdict' : 'Déplier la légende du verdict'}
          >
            {/* M36 Lot A : étiquette de source VRAIE, sans jargon interne. Cas nominal = classement
                servi (tiers) ; le repli n'apparaît que si le classement servi est INJOIGNABLE
                (avant M36 il s'affichait aussi en dev à cause du proxy /v2 manquant). */}
            {v2 ? (
              <Tip block side="top" tip="Couleurs du classement servi (tiers Priorité → Écartée).">
                <span className="label-caps">Verdict · Classement servi</span>
              </Tip>
            ) : (
              <Tip block side="top" tip="Classement historique (repli) — le classement servi n'est pas joignable sur cette vue.">
                <span className="label-caps">Verdict · Classement historique</span>
              </Tip>
            )}
            <ChevronSection open={verdictOpen} />
          </button>
          {verdictOpen && (
            <div className="mt-2 flex flex-col gap-1.5">
              {v2
                ? LEGEND_V2_ORDER.map((t) => (
                    <div key={t} className="flex items-center gap-2">
                      <span className="h-2 w-2 rounded-full" style={{ background: TIER_V2_META[t].color }} />
                      <span className="text-[11px] text-txt">{TIER_V2_META[t].label}</span>
                    </div>
                  ))
                : LEGEND_ORDER.map((s) => (
                    <div key={s} className="flex items-center gap-2">
                      <span className="h-2 w-2 rounded-full" style={{ background: STATUT_META[s].color }} />
                      <span className="text-[11px] text-txt">{STATUT_META[s].label}</span>
                    </div>
                  ))}
            </div>
          )}
        </>
      )}

      {/* ── Zonage PLU par famille (C5) — seulement si le remplissage par famille est PEINT ── */}
      {zonagePeint && (
        <div data-legend-zonage className="mt-3 border-t border-line pt-2.5 first:mt-0 first:border-t-0 first:pt-0">
          <p className="label-caps mb-2">Zonage PLU (par type)</p>
          <div className="flex flex-col gap-1.5">
            {ZONE_FAM_ORDER.map((f) => (
              <div key={f} className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full" style={{ background: ZONE_FAM_META[f].color }} />
                <span className="text-[11px] text-txt">{ZONE_FAM_META[f].label}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── 50 pas géométriques ── */}
      {layers.cinquante_pas && (
        <div className="mt-3 border-t border-line pt-2.5 first:mt-0 first:border-t-0 first:pt-0">
          <Tip block side="top" tip="Réserve des 50 pas géométriques — bande de 81,20 m depuis le rivage (spécifique outre-mer)">
            <div data-legend-50pas className="flex items-center gap-2">
              <span className="h-0.5 w-4 rounded" style={{ background: CINQUANTE_PAS_COLOR }} />
              <span className="text-[11px] text-txt">50 pas géométriques</span>
            </div>
          </Tip>
        </div>
      )}

      {/* ── M106 : aléas DEAL séparés — gradation par niveau, source et millésime SERVIS ── */}
      {(['alea_inondation', 'alea_mvt'] as const).map((k) => layers[k] && (
        <div key={k} data-legend-alea={k} className="mt-3 border-t border-line pt-2.5 first:mt-0 first:border-t-0 first:pt-0">
          <p className="label-caps mb-2">{k === 'alea_inondation' ? 'Aléa inondation' : 'Aléa mouvement de terrain'}</p>
          <div className="flex items-center gap-2">
            {(['faible', 'moyen', 'fort'] as const).map((n) => (
              <span key={n} className="flex items-center gap-1">
                <span className="h-2.5 w-4 rounded-sm border" style={{
                  background: k === 'alea_inondation' ? tTheme.aleaInondation : tTheme.aleaMvt,
                  opacity: Math.min(1, tTheme.aleaOpacity[n] + 0.25),
                  borderColor: k === 'alea_inondation' ? tTheme.aleaInondation : tTheme.aleaMvt,
                }} />
                <span className="text-[10.5px] text-txt-dim">{n}</span>
              </span>
            ))}
          </div>
          <p className="mt-1 text-[10px] text-txt-dim">
            DEAL Réunion — cartographie des aléas (exposition au phénomène, pas la règle du PPR)
            {aleaMillesime ? ` · intégré le ${aleaMillesime.split('-').reverse().join('/')}` : ''}
          </p>
        </div>
      ))}

      {/* ── M106-B : transport public — LA COULEUR DIT LE RÉSEAU, LA FORME DIT LE TYPE.
          Légende lisible seule : les réseaux sont NOMMÉS, jamais un code interne. ── */}
      {layers.transport && (
        <div data-legend-transport className="mt-3 border-t border-line pt-2.5 first:mt-0 first:border-t-0 first:pt-0">
          <p className="label-caps mb-2">Transport public — un réseau, une couleur</p>
          <div className="flex flex-col gap-1 text-[11px] text-txt">
            {([['Car Jaune', 'cars interurbains (Région)'], ['Citalis', 'bus du Nord (CINOR) — et le téléphérique Papang, en tireté'],
               ["Kar'Ouest", 'bus de l’Ouest (TCO)'], ['Alternéo', 'bus du Sud-Ouest (CIVIS)'],
               ['Estival', 'bus de l’Est (CIREST)'], ['Carsud', 'bus du Sud (CASUD)']] as const).map(([r, d]) => (
              <span key={r} className="flex items-center gap-2">
                <span className="h-0.5 w-4 shrink-0 rounded" style={{ background: tTheme.transportReseaux[r] }} />
                <span><b>{r}</b> — {d}</span>
              </span>
            ))}
          </div>
          <p className="label-caps mb-1.5 mt-2.5">La forme dit le type</p>
          <div className="flex flex-col gap-1 text-[11px] text-txt">
            <span className="flex items-center gap-2"><span className="h-0.5 w-4 shrink-0 rounded bg-txt-mut" />tracé de ligne (couleur du réseau)</span>
            <span className="flex items-center gap-2"><span className="h-1.5 w-1.5 shrink-0 rounded-full bg-txt-mut" />arrêt (visible en zoomant)</span>
            <span className="flex items-center gap-2"><span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: tTheme.pole }} />pôle d’échange relevé sur le terrain (OSM — Sourcé)</span>
            <span className="flex items-center gap-2"><span className="h-2.5 w-2.5 shrink-0 rounded-full border-2" style={{ borderColor: tTheme.pole }} />pôle estimé — {critereDerive}</span>
          </div>
          <p className="mt-1.5 text-[10px] text-txt-dim">
            GTFS : réseaux officiels de La Réunion (Licence Ouverte) · pôles &amp; Papang : © les
            contributeurs d’OpenStreetMap (ODbL){fmtMill(mill(transQ))}
          </p>
        </div>
      )}

      {/* ── M106-B P3 : axes structurants (BD TOPO, hiérarchie IGN) ── */}
      {layers.axes && (
        <div data-legend-axes className="mt-3 border-t border-line pt-2.5 first:mt-0 first:border-t-0 first:pt-0">
          <Tip block side="top" tip="Double face : accessibilité ET nuisances (bruit, pollution, recul le long des axes classés). La fiche d'une parcelle donne la distance à l'axe le plus proche.">
            <div className="flex items-center gap-2">
              <span className="h-1 w-4 rounded" style={{ background: tTheme.axe }} />
              <span className="text-[11px] text-txt">Axes structurants (route des Tamarins, nationales…)</span>
            </div>
          </Tip>
          <p className="mt-1 text-[10px] text-txt-dim">BD TOPO IGN — hiérarchie officielle « importance » niveaux 1-2 (Licence Ouverte)</p>
        </div>
      )}

      {/* ── M106 P4 : lignes haute tension — une CONTRAINTE, tireté anthracite ── */}
      {layers.lignes_ht && (
        <div data-legend-ht className="mt-3 border-t border-line pt-2.5 first:mt-0 first:border-t-0 first:pt-0">
          <Tip block side="top" tip="Contrainte potentielle (servitudes, reculs) — la servitude I4 n'est pas cartographiée en donnée ouverte : à vérifier auprès du gestionnaire (EDF SEI).">
            <div className="flex items-center gap-2">
              <span className="h-0.5 w-4 rounded" style={{ background: tTheme.ht }} />
              <span className="text-[11px] text-txt">Lignes haute tension (aériennes, tension indiquée)</span>
            </div>
          </Tip>
          <p className="mt-1 text-[10px] text-txt-dim">BD TOPO IGN (Licence Ouverte){fmtMill(mill(htQ))}</p>
        </div>
      )}

      {/* ── M134 : Dispositifs et périmètres — deux familles (opérationnel chaud / fiscal froid) ;
          l'intensité d'un régime se lit à l'OPACITÉ (ZFANG renforcé, FRR totalité plus denses). ── */}
      {dispoActif && (
        <div data-legend-dispositifs className="mt-3 border-t border-line pt-2.5 first:mt-0 first:border-t-0 first:pt-0">
          <p className="label-caps mb-2">Dispositifs et périmètres</p>
          <div className="flex flex-col gap-1.5 text-[11px] text-txt">
            {layers.qpv && (
              <span className="flex items-center gap-2">
                <span className="h-2.5 w-4 shrink-0 rounded-sm border" style={{ background: tTheme.qpv, opacity: tTheme.qpvOpacity + 0.35, borderColor: tTheme.qpv }} />
                QPV — quartier prioritaire{fmtMill(mill(qpvQ))}
              </span>
            )}
            {layers.tva_primo && (
              <span className="flex items-center gap-2">
                <span className="h-2.5 w-4 shrink-0 rounded-sm border" style={{ background: tTheme.tvaPrimo, opacity: tTheme.tvaPrimoOpacity + 0.35, borderColor: tTheme.tvaPrimo }} />
                <span>TVA réduite primo-accédant (QPV + 500 m) — <i className="text-txt-dim">dérivé LABUSE</i></span>
              </span>
            )}
            {layers.anru && (
              <span className="flex items-center gap-2">
                <span className="h-2.5 w-4 shrink-0 rounded-sm border" style={{ background: tTheme.anru, opacity: tTheme.anruOpacity + 0.35, borderColor: tTheme.anru }} />
                NPNRU / ANRU — renouvellement urbain{fmtMill(mill(anruQ))}
              </span>
            )}
            {layers.zfang && (
              <span className="flex items-center gap-2">
                <span className="flex shrink-0 gap-0.5">
                  <span className="h-2.5 w-2.5 rounded-sm" style={{ background: tTheme.zfang, opacity: tTheme.zfangOpRenforce + 0.3 }} />
                  <span className="h-2.5 w-2.5 rounded-sm" style={{ background: tTheme.zfang, opacity: tTheme.zfangOpStandard + 0.3 }} />
                </span>
                ZFANG — zone franche (renforcé ▸ standard)
              </span>
            )}
            {layers.frr && (
              <span className="flex items-center gap-2">
                <span className="flex shrink-0 gap-0.5">
                  <span className="h-2.5 w-2.5 rounded-sm" style={{ background: tTheme.frr, opacity: tTheme.frrOpTotalite + 0.3 }} />
                  <span className="h-2.5 w-2.5 rounded-sm" style={{ background: tTheme.frr, opacity: tTheme.frrOpPartie + 0.3 }} />
                </span>
                FRR — France Ruralités (totalité ▸ en partie)
              </span>
            )}
          </div>
          <p className="mt-1.5 text-[10px] text-txt-dim">ZFANG / FRR : maille COMMUNE entière (pas un périmètre fin). Bande TVA : périmètre dérivé des QPV (Estimé).</p>
        </div>
      )}

      {/* ── M-RENOUV : segment Renouvellement (cuivre) ── */}
      {layers.renouv && (
        <div className="mt-3 border-t border-line pt-2.5 first:mt-0 first:border-t-0 first:pt-0">
          <Tip block side="top" tip="Parcelles occupées (bâties) en zone U/AU avec capacité restante — potentiel de renouvellement urbain, pas une opportunité qualifiée.">
            <div data-legend-renouv className="flex items-center gap-2">
              <span className="h-2.5 w-4 rounded-sm" style={{ background: TOKENS.renouv, opacity: 0.7 }} />
              <span className="text-[11px] text-txt">Renouvellement — occupées, potentiel de renouvellement</span>
            </div>
          </Tip>
        </div>
      )}

      {/* ── Équipements (C6 : rapatriée dans le panneau unique, ne recouvre plus le verdict) ── */}
      {equipPeint && (
        <div data-legend-equip className="mt-3 border-t border-line pt-2.5 first:mt-0 first:border-t-0 first:pt-0">
          <p className="label-caps mb-2">Équipements</p>
          <div className="flex flex-col gap-0.5 text-[11px]">
            {EQUIP_META.map((e) => (
              <span key={e.key} className="flex items-center gap-1.5 text-txt-mut">
                <span className="text-[13px] leading-none">{e.emoji}</span>{e.label}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
