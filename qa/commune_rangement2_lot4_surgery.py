# COMMUNE-RANGEMENT-2 lot 4 — chirurgie : remplace le corps de rendu de ContextePanel (en-tête +
# 19 cartes en 3 groupes) par le bandeau 6 chiffres (3×3) + 3 raccourcis + 10 cartes en 5 groupes
# (maquette v1). Splice entre deux ancres stables ; le haut du fichier (imports/helpers) et le pied
# restent intacts.
import io, sys
f = "frontend/src/components/contexte/ContextePanel.tsx"
src = open(f).read()

ANCHOR_START = "          <>\n"
ANCHOR_END = "            {/* FICHE-COMMUNE-2 (C1) — pied :"
i = src.index(ANCHOR_START) + len(ANCHOR_START)
j = src.index(ANCHOR_END)

NEW = r'''            {/* ── EN-TÊTE (maquette v1) — bandeau 6 chiffres en 3×3 + 3 raccourcis. Pas de rang comparatif. ── */}
            <div className="border-b border-line bg-surface-2/40 px-5 py-3">
              <div data-bandeau-chiffres className="grid grid-cols-3 gap-2">
                {[
                  { v: `${fmt(d.foncier?.n_parcelles)}`, n: 'Parcelles', s: 'Cadastre' },
                  { v: d.population?.habitants != null ? `${fmt(d.population.habitants)}` : '—', n: 'Habitants', s: 'INSEE' },
                  { v: `${fmt(d.permis_bloc?.permis_12m)}`, n: 'Permis / an', s: 'SITADEL' },
                  { v: d.comparable?.ancien_median_eur_m2 != null ? `${fmt(d.comparable.ancien_median_eur_m2)} €/m²` : '—', n: 'Prix ancien', s: 'DVF' },
                  { v: tendPct != null ? `${Number(tendPct) > 0 ? '+' : ''}${fmtDec(tendPct)} %` : '—', n: 'Tendance 12 m', s: 'DVF' },
                  { v: d.plu_statut?.statut ?? '—', n: 'État du PLU', s: 'GPU · Sudocuh' },
                ].map((c) => (
                  <div key={c.n} className="rounded-lg bg-surface-3 px-2.5 py-1.5">
                    <p className="tnum font-display text-[14px] font-bold leading-tight text-txt-hi">{c.v}</p>
                    <p className="mt-0.5 text-[9.5px] uppercase tracking-[0.04em] text-txt-mut">{c.n}</p>
                    <p className="text-[9px] text-txt-dim">{c.s}</p>
                  </div>
                ))}
              </div>
              {/* Action principale conservée (DA) : voir les parcelles de la commune. */}
              <button data-communes-parcelles onClick={() => {
                const s = useApp.getState()
                s.setView('cartes'); s.setCommune(commune); s.setCommunesFilter([commune])
                s.setFilter('analyseLabuse', true); s.setVerdict(true)
                s.openListing()
              }} className="mt-3 w-full rounded-md border border-mint bg-mint px-2.5 py-2 text-[12.5px] font-semibold text-mint-ink transition-[filter] duration-quick hover:brightness-110">Voir ses parcelles →</button>
              {/* Trois raccourcis : PLU · Communes · Étude de zone — commune déjà en contexte. */}
              <div data-raccourcis className="mt-2 grid grid-cols-3 gap-2">
                <button data-raccourci-plu onClick={() => ouvrirOutil(commune, insee, 'plu')}
                  className="rounded-lg border border-line-2 border-l-2 border-l-mint px-2.5 py-1.5 text-left text-[12px] font-medium text-txt-mut transition-colors duration-quick hover:border-mint hover:text-txt-hi">PLU<span className="block text-[10px] font-normal text-txt-dim">règlement</span></button>
                <button data-communes-comparer onClick={() => ouvrirOutil(commune, insee, 'communes')}
                  className="rounded-lg border border-line-2 border-l-2 border-l-mint px-2.5 py-1.5 text-left text-[12px] font-medium text-txt-mut transition-colors duration-quick hover:border-mint hover:text-txt-hi">Communes<span className="block text-[10px] font-normal text-txt-dim">les 24</span></button>
                <button data-communes-etude-zone onClick={() => ouvrirOutil(commune, insee, 'etude-zone')}
                  className="rounded-lg border border-line-2 border-l-2 border-l-mint px-2.5 py-1.5 text-left text-[12px] font-medium text-txt-mut transition-colors duration-quick hover:border-mint hover:text-txt-hi">Étude de zone<span className="block text-[10px] font-normal text-txt-dim">autour d'un point</span></button>
              </div>
              {signauxNommes.length > 0 && (
                <div data-fiche-signaux className="mt-3">
                  <p className="label-caps text-txt-dim">Signaux</p>
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    {signauxNommes.map((s) => {
                      const col = s.ton === 'rouge' ? TOKENS.stEcartee : TOKENS.stCreuser
                      return (
                        <span key={s.code} data-fiche-signal={s.code}
                          className="rounded-md border px-2 py-0.5 text-[11px] font-medium"
                          style={{ color: col, borderColor: `${col}55`, background: `${col}1a` }}>{s.libelle}</span>
                      )
                    })}
                  </div>
                </div>
              )}
            </div>

            {d.rnu && (
              <div data-rnu-bandeau className="border-b border-line px-5 py-3">
                <div className="rounded-lg border border-st-creuser/40 bg-st-creuser/[0.10] px-3 py-2.5">
                  <p className="flex items-center gap-1.5 text-[12.5px] font-semibold text-st-creuser"><span aria-hidden>⚑</span>{d.rnu.libelle}</p>
                  <p className="mt-1 text-[11px] leading-relaxed text-txt">{d.rnu.detail}</p>
                </div>
              </div>
            )}

            {/* ── 5 GROUPES · 10 CARTES (maquette v1). Les 70 lignes des 19 cartes d'avant, redistribuées
                par NATURE d'information. La grammaire LigneCarte (accordéon mémorisé) reste. ── */}
            <div className="px-5 pt-3">

              {/* ═══ LE TERRITOIRE ═══ */}
              <GroupeLabel>Le territoire</GroupeLabel>

              <LigneCarte id="identite" ic="I" titre="Identité"
                sous={`${d.epci ?? ''}${d.population?.quartiers ? ` · ${d.population.quartiers.n_iris} IRIS` : ''}`}
                val={insee ?? undefined}>
                <div className="flex flex-col gap-0.5 text-[12px]">
                  <RowT lbl="Intercommunalité" val={d.epci ? `${d.epci}${d.epci_nom ? ` — ${d.epci_nom}` : ''}` : '—'} />
                  {d.population?.quartiers && (
                    <RowT lbl={`Par quartier (${d.population.quartiers.n_iris} IRIS)`}
                      val={`vacance ${fmtDec(d.population.quartiers.vacance_min_pct)} → ${fmtDec(d.population.quartiers.vacance_max_pct)} % (méd. ${fmtDec(d.population.quartiers.vacance_mediane_pct)} %)`} />
                  )}
                </div>
                {d.mairie && (
                  <div className="mt-2 border-t border-line pt-2">
                    <dl className="space-y-1.5 text-[12px]">
                      <MairieLigne label="Adresse" val={[d.mairie.adresse, [d.mairie.code_postal, d.mairie.commune].filter(Boolean).join(' ')].filter(Boolean).join(', ') || null} />
                      <MairieLigne label="Téléphone" val={d.mairie.telephone} href={d.mairie.telephone ? `tel:${d.mairie.telephone.replace(/\s/g, '')}` : undefined} />
                      <MairieLigne label="E-mail" val={d.mairie.email} href={d.mairie.email ? `mailto:${d.mairie.email}` : undefined} />
                      <MairieLigne label="Site officiel" val={d.mairie.site_officiel} href={d.mairie.site_officiel ?? undefined} />
                      <MairieLigne label="Annuaire" val={d.mairie.url_annuaire ? 'Fiche service-public' : null} href={d.mairie.url_annuaire ?? undefined} />
                    </dl>
                    <p className="mt-2 text-[10.5px] leading-snug text-txt-dim">{d.mairie.source}{d.mairie.date_import ? ` · relevé le ${fmtDateFr(d.mairie.date_import)}` : ''}</p>
                    <ContactsMairie insee={insee} commune={commune} />
                  </div>
                )}
                <Source nom="INSEE · IGN contours IRIS · Annuaire de l'administration" />
              </LigneCarte>

              <LigneCarte id="population" chiffre="habitants_n" ic="P" titre="Population et logement" defaultOpen
                sous={`${d.population.logements != null ? `${fmt(d.population.logements)} logts` : ''}${d.population.vacance_pct != null ? ` · ${fmtDec(d.population.vacance_pct)} % vacants` : ''} · INSEE`}
                val={d.population.habitants != null ? `${fmt(d.population.habitants)} hab.` : null}>
                <div className="mb-2 flex flex-col gap-0.5 text-[12px]">
                  {d.population.habitants != null && <RowT lbl="Habitants · ménages" val={`${fmt(d.population.habitants)} · ${fmt(d.population.menages)}`} />}
                  {d.population.niveau_vie_moyen_eur != null && <RowT lbl="Niveau de vie moyen" val={`${fmt(d.population.niveau_vie_moyen_eur)} €/an`} />}
                  {d.population.logements != null && <RowT lbl="Logements" val={`${fmt(d.population.logements)}${d.population.vacants != null ? ` · ${fmt(d.population.vacants)} vacants (${fmtDec(d.population.vacance_pct)} %)` : ''}`} />}
                  {d.parc_social?.logements != null && <RowT lbl="Parc social (RPLS)" val={`${fmt(d.parc_social.logements)} logts${d.parc_social.construct_median != null ? ` · constr. médiane ${d.parc_social.construct_median}` : ''}`} />}
                </div>
                {d.marche && (
                  <div className="mb-2 flex flex-col gap-2.5">
                    {(() => {
                      const loc = Number(d.marche.locataires_pct); const prop = Number(d.marche.proprietaires_pct)
                      const autres = (d.marche as any).autres_loges_pct != null
                        ? Number((d.marche as any).autres_loges_pct)
                        : Math.max(0, Math.round((100 - loc - prop) * 10) / 10)
                      return <Bar parts={[
                        { label: 'locataires', pct: loc, color: TOKENS.vizCyan },
                        { label: 'propriétaires', pct: prop, color: TOKENS.mint },
                        ...(autres >= 1 ? [{ label: 'logés gratuitement', pct: autres, color: TOKENS.txtMut }] : []),
                      ]} />
                    })()}
                    <Bar parts={[
                      { label: 'maisons', pct: Number(d.marche.maisons_pct), color: TOKENS.stSurveiller },
                      { label: 'appartements', pct: Number(d.marche.apparts_pct), color: TOKENS.vizCyan },
                    ]} />
                  </div>
                )}
                {/* Parc social / SRU — taux et objectif (maquette : « Parc social RPLS, taux SRU, objectif »). */}
                {d.sru && (() => {
                  const m = SRU_META[d.sru.statut] ?? SRU_META.conforme
                  return (
                    <div className="rounded-lg border px-3 py-2" style={{ borderColor: `${m.color}55`, background: `${m.color}14` }}>
                      <span className="font-display text-[13px] font-bold" style={{ color: m.color }}>SRU {Number(d.sru.taux_lls).toLocaleString('fr-FR')} %</span>
                      <span className="ml-2 text-[11px] text-txt-mut">objectif {Number(d.sru.objectif_pct).toLocaleString('fr-FR')} %{d.sru.detail?.nb_lls != null ? ` · ${fmt(d.sru.detail.nb_lls)} LLS` : ''}</span>
                      <p className="mt-1 text-[11px] leading-relaxed text-txt">{m.lecture}</p>
                    </div>
                  )
                })()}
                <Source nom={`${d.population.source}${d.parc_social ? ` · ${d.parc_social.source}` : ''} · Inventaire SRU (DHUP)`} />
              </LigneCarte>

              {/* ═══ LE MARCHÉ ═══ */}
              <GroupeLabel>Le marché</GroupeLabel>

              <LigneCarte id="marche" chiffre="prix_ancien_median_eur_m2" ic="↗" titre="Prix" defaultOpen
                sous={`ancien ${fmt(d.comparable?.ancien_median_eur_m2)} · neuf ${fmt(d.comparable?.neuf_eur_m2)} €/m²`}
                val={tendPct != null ? `${Number(tendPct) > 0 ? '+' : ''}${fmtDec(tendPct)} %` : null}
                ton={tendPct != null && Number(tendPct) < 0 ? 'rouge' : 'vert'}>
                <div className="flex flex-col gap-0.5 text-[12px]">
                  <RowT lbl="Ancien médian (commune entière)" val={`${fmt(d.comparable?.ancien_median_eur_m2)} €/m²`} strong />
                  <RowT lbl="Neuf VEFA (prix de sortie)" val={`${fmt(d.comparable?.neuf_eur_m2)} €/m²`} />
                  <RowT lbl="Neuf observé (ventes récentes)" val={d.prix_neuf_observe?.eur_m2 != null ? `${fmt(d.prix_neuf_observe.eur_m2)} €/m²` : '—'} />
                  {tendPct != null && <RowT lbl="Tendance 12 mois" val={`${Number(tendPct) > 0 ? '+' : ''}${fmtDec(tendPct)} %`} />}
                </div>
                {d.foncier?.prix_terrain_nu.par_zone && (
                  <div className="mt-2 flex gap-5 border-t border-line pt-2">
                    {(['U', 'AU'] as const).map((fam) => {
                      const pz = d.foncier!.prix_terrain_nu.par_zone?.[fam]
                      return pz?.calculable
                        ? <div key={fam}><p className="font-display text-base font-bold text-txt-hi">{fmt(pz.median_eur_m2)} €/m²</p><p className="text-[10.5px] text-txt-dim">terrain nu zone {fam} · {fmt(pz.n)} ventes</p></div>
                        : <div key={fam}><p className="font-display text-sm text-txt-mut">zone {fam} —</p><p className="text-[10.5px] text-txt-dim">&lt; {d.foncier!.prix_terrain_nu.seuil_n} ventes</p></div>
                    })}
                  </div>
                )}
                {d.loyer && (
                  <div className="mt-2 flex flex-col gap-0.5 border-t border-line pt-2 text-[12px]">
                    <RowT lbl={`Loyer médian${d.loyer.type ? ` (${d.loyer.type})` : ''}`} val={`${fmtDec(d.loyer.median_eur_m2)} €/m²`} strong />
                  </div>
                )}
                <Source nom={`DVF — médiane commune entière · terrain nu par zone PLU${d.loyer ? ` · ${d.loyer.source}` : ''}`} />
              </LigneCarte>

              {/* Activité — TOUJOURS présente ; sans annonce Radar, elle le dit. */}
              {(() => {
                const ma = d.marche_annonces
                const vide = !ma || ma.sous_seuil
                return (
                <LigneCarte id="annonces" chiffre="annonces_actives_n" ic="◉" titre="Activité"
                  sous={`${fmt(d.foncier?.mutations_12m)} mutations/12m${ma ? ` · ${fmt(ma.biens)} biens en vente` : ''}`}
                  val={ma && !ma.sous_seuil && ma.ecart_demande_acte_pct != null ? `${ma.ecart_demande_acte_pct > 0 ? '+' : ''}${fmtDec(ma.ecart_demande_acte_pct)} %` : null}
                  ton={ma?.ecart_demande_acte_pct != null && ma.ecart_demande_acte_pct < 0 ? 'vert' : undefined}>
                  <div className="flex flex-col gap-0.5 text-[12px]">
                    <RowT lbl="Mutations (12 mois, DVF)" val={fmt(d.foncier?.mutations_12m)} />
                  </div>
                  {vide ? (
                    <p data-annonces-sans-objet className="mt-1 text-[12px] text-txt-mut">Pas d'annonce repérée sur cette commune{ma ? ` (${ma.biens} bien(s), seuil ${ma.seuil_n})` : ''}. Le Radar affine la couverture au fil des relevés.</p>
                  ) : (
                    <>
                      <div className="flex flex-col gap-0.5 text-[12px]">
                        <RowT lbl="Biens en vente" val={fmt(ma!.biens)} />
                        <RowT lbl="Prix demandé médian" val={`${fmt(ma!.prix_demande_median_eur_m2)} €/m²`} />
                        {ma!.ecart_demande_acte_pct != null && (
                          <RowT lbl="Écart demandé / acté" strong val={`${ma!.ecart_demande_acte_pct > 0 ? '+' : ''}${fmtDec(ma!.ecart_demande_acte_pct)} %`} />
                        )}
                      </div>
                      <Shortcut label="Voir les annonces dans le Radar" onClick={() => ouvrirOutil(commune, insee, 'radar')} />
                    </>
                  )}
                  <Source nom={`DVF (mutations)${ma ? ` · ${ma.source}` : ' · Radar LABUSE'}`} />
                </LigneCarte>
                )
              })()}

              {/* ═══ LA CONSTRUCTION ═══ */}
              <GroupeLabel>La construction</GroupeLabel>

              <LigneCarte id="construire" chiffre="permis_12m_n" ic="▤" titre="Permis et rythme"
                sous={`${fmt(d.permis_bloc.permis_12m)} permis / 12 mois${d.permis_bloc.logements_12m != null ? ` · ${fmt(d.permis_bloc.logements_12m)} logts` : ''}`}
                val={d.permis_bloc.delai_median_mois != null ? `${fmtDec(d.permis_bloc.delai_median_mois)} mois` : null}>
                <div className="flex flex-col gap-0.5 text-[12px]">
                  <RowT lbl="Permis autorisés (12 mois)" val={`${fmt(d.permis_bloc.permis_12m)}${d.permis_bloc.permis_5a != null ? ` · ${fmt(d.permis_bloc.permis_5a)} sur 5 ans` : ''}`} strong />
                  {d.permis_bloc.delai_median_mois != null && <RowT lbl="Délai d'instruction médian" val={`${fmtDec(d.permis_bloc.delai_median_mois)} mois`} />}
                  {d.permis_bloc.logements_12m != null && <RowT lbl="Offre engagée" val={`${fmt(d.permis_bloc.logements_12m)} logts / 12 mois`} />}
                  <RowT lbl="Permis dormants" val={fmt(d.permis_bloc.point_mort)} />
                </div>
                <Shortcut label="Ouvrir Permis — cette commune" onClick={() => ouvrirOutil(commune, insee, 'permis')} />
                <Source nom={d.permis_bloc.source} />
              </LigneCarte>

              <LigneCarte id="foncier" chiffre="n_parcelles_commune" ic="◫" titre="Foncier et rareté"
                sous={`${fmt(d.foncier?.stock_opportunites.n)} parcelles promues${r?.['horizon_epuisement_ans'] != null ? ` · ZAN ${fmtDec(r['horizon_epuisement_ans'])} ans` : ''}`}
                val={d.foncier ? `${fmt(d.foncier.stock_opportunites.ha)} ha` : null} ton="orange">
                {d.foncier && (
                  <>
                    <div className="mb-3 flex gap-5">
                      <div><p className="font-display text-lg font-bold text-txt-hi">{fmt(d.foncier.n_parcelles)}</p><p className="text-[11px] text-txt-dim">parcelles<i className="block not-italic text-[10px]">{fmt(d.foncier.surface_ha)} ha</i></p></div>
                      <div><p className="font-display text-lg font-bold text-txt-hi">{fmt(d.foncier.stock_opportunites.n)}</p><p className="text-[11px] text-txt-dim">stock foncier repéré<i className="block not-italic text-[10px]">{fmt(d.foncier.stock_opportunites.ha)} ha promus</i></p></div>
                    </div>
                    {d.densifiables?.parcelles != null && (
                      <div className="mb-2 flex gap-5">
                        <div><p className="font-display text-lg font-bold text-txt-hi">{fmt(d.densifiables.parcelles)}</p><p className="text-[11px] text-txt-dim">densifiables<i className="block not-italic text-[10px]">capacité résiduelle</i></p></div>
                        {d.densifiables.sdp_residuelle_m2 != null && <div><p className="font-display text-lg font-bold text-txt-hi">{fmt(Math.round(d.densifiables.sdp_residuelle_m2 / 1e6 * 10) / 10)} M m²</p><p className="text-[11px] text-txt-dim">SDP résiduelle théorique</p></div>}
                      </div>
                    )}
                  </>
                )}
                <div className="flex flex-col gap-0.5 border-t border-line pt-2 text-[12px]">
                  <RowT lbl="Consommation NAF (budget ZAN consommé)" val={r?.['pct_budget_consomme'] != null ? `${fmtDec(r['pct_budget_consomme'])} %${r?.['budget_zan_ha'] != null ? ` de ${fmtV(r['budget_zan_ha'], ' ha')}` : ''}` : '—'} />
                  <RowT lbl="Budget ZAN restant (estimé)" val={fmtV(r?.['reste_zan_ha'], ' ha')} />
                  <RowT lbl="Rythme de consommation" val={fmtV(r?.['rythme_conso_ha_an'], ' ha/an')} />
                  <RowT lbl="Horizon d'épuisement" val={r?.['horizon_epuisement_ans'] != null ? `${fmtDec(r['horizon_epuisement_ans'])} ans` : '—'} strong />
                </div>
                <Shortcut label="Densifier l'existant — cette commune" onClick={() => ouvrirOutil(commune, insee, 'renouvellement')} />
                <Source nom={`Cadastre DGFiP · ${d.densifiables?.source ?? 'analyse LABUSE'} · Consommation ENAF Cerema (estimé)`} />
              </LigneCarte>

              {/* ═══ LES RÈGLES ═══ */}
              <GroupeLabel>Les règles</GroupeLabel>

              <LigneCarte id="regle-plu" chiffre="statut_plu" ic="§" titre="Urbanisme"
                sous={`PLU ${d.plu_statut.statut}${d.plu_statut.date_reglement ? ` · ${d.plu_statut.date_reglement}` : ''}`}
                val={d.plu_statut.statut} badge ton={d.plu_statut.statut === 'RNU' ? 'orange' : 'vert'}>
                <p className="text-[12px] leading-relaxed text-txt">
                  {d.plu_statut.statut === 'RNU' ? "Pas de PLU opposable : c'est le Règlement National d'Urbanisme qui s'applique."
                    : d.plu_statut.statut === 'à jour' ? `Le PLU est opposable${d.plu_statut.date_reglement ? ` (approuvé le ${d.plu_statut.date_reglement})` : ''}.`
                      : `Document local — ${d.plu_statut.statut}${d.plu_statut.date_reglement ? ` · ${d.plu_statut.date_reglement}` : ''}.`}
                </p>
                {d.foncier?.repartition_zonage && (() => {
                  const f = d.foncier.repartition_zonage.familles
                  return (
                    <div className="mt-2 border-t border-line pt-2">
                      <p className="mb-1 flex items-center gap-1.5 text-[11px] text-txt-dim">Zones du PLU <span className="text-txt-mut">(parts de surface)</span>
                        <span className="rounded bg-mint/10 px-1 text-[9px] text-mint">{d.foncier!.repartition_zonage!.total_ha.toLocaleString('fr-FR')} ha</span></p>
                      <Bar parts={[
                        { label: 'U', pct: f.U.pct, color: TOKENS.mint },
                        { label: 'AU', pct: f.AU.pct, color: TOKENS.vizCyan },
                        { label: 'A', pct: f.A.pct, color: TOKENS.stCreuser },
                        { label: 'N', pct: f.N.pct, color: TOKENS.vizGreenDeep },
                      ]} />
                    </div>
                  )
                })()}
                <div className="mt-2 flex flex-col gap-0.5 border-t border-line pt-2 text-[12px]">
                  {d.plh ? (
                    <>
                      <RowT lbl={`PLH ${d.epci ?? ''} — objectif`} val={d.plh.obj_logements_an != null ? `${fmt(d.plh.obj_logements_an)} logts/an` : '—'} />
                      {d.plh.part_sociale_pct != null && <RowT lbl="Part sociale visée" val={`${Number(d.plh.part_sociale_pct).toLocaleString('fr-FR')} %`} />}
                    </>
                  ) : (
                    <p data-plh-sans-objet className="text-[12px] text-txt-mut">Aucun programme local de l'habitat recensé pour l'intercommunalité {d.epci ?? ''}.</p>
                  )}
                </div>
                <button data-voir-plu onClick={() => ouvrirOutil(commune, insee, 'plu')} className="mt-2 text-[11.5px] text-mint hover:underline">Voir le PLU →</button>
                <Source nom={`${d.plu_statut.source ?? 'GPU'} · Zonage PLU (GPU) · PLH (EPCI)`} />
              </LigneCarte>

              {/* Fiscalité et dispositifs — taxes + zonages + QPV/ORT (creux dits). */}
              {(() => {
                const o = d.ort
                const horsOrt = !o || o.statut === 'hors'
                const aucunQpv = d.qpv.length === 0 && d.anru.length === 0
                return (
                <LigneCarte id="fiscalite" chiffre="tfpb_taux_pct" ic="₣" titre="Fiscalité et dispositifs"
                  sous={`${d.fiscalite?.tfpb_commune_pct != null ? `TFPB ${fmtDec(d.fiscalite.tfpb_commune_pct)} %` : 'taxes'}${d.zonage_abc ? ` · zone ${d.zonage_abc.zone}` : ''}`}
                  val={horsOrt ? null : (o!.statut === 'acv' ? 'ACV' : o!.statut === 'pvd' ? 'PVD' : 'ORT')}>
                  {d.fiscalite && (
                    <div className="flex flex-col gap-0.5 text-[12px]">
                      <RowT lbl="TFPB commune" val={d.fiscalite.tfpb_commune_pct != null ? `${fmtDec(d.fiscalite.tfpb_commune_pct)} %` : '—'} strong />
                      <RowT lbl="TFPB intercommunalité" val={d.fiscalite.tfpb_epci_pct != null ? `${fmtDec(d.fiscalite.tfpb_epci_pct)} %` : '—'} />
                      <RowT lbl="TFPNB commune (non bâti)" val={d.fiscalite.tfpnb_commune_pct != null ? `${fmtDec(d.fiscalite.tfpnb_commune_pct)} %` : '—'} />
                      <RowT lbl="TFPNB intercommunalité" val={d.fiscalite.tfpnb_epci_pct != null ? `${fmtDec(d.fiscalite.tfpnb_epci_pct)} %` : '—'} />
                      <RowT lbl="TEOM (taux plein)" val={d.fiscalite.teom_pct != null ? `${fmtDec(d.fiscalite.teom_pct)} %` : '—'} />
                    </div>
                  )}
                  {d.fiscalite?.perime && (
                    <p data-fiscalite-perime className="mt-1 text-[11px] text-st-creuser">Donnée ingérée il y a plus d'un an — à rafraîchir (fichier REI annuel).</p>
                  )}
                  <div className="mt-2 flex flex-col gap-0.5 border-t border-line pt-2 text-[12px]">
                    <RowT lbl="Classe de la commune" val={d.zonage_abc ? `zone ${d.zonage_abc.zone}` : 'non déterminée'} />
                    {d.zfang_frr && <RowT lbl="ZFANG" val={d.zfang_frr.zfang.regime === 'renforce' ? 'Régime renforcé' : 'Régime standard'} />}
                    {d.zfang_frr && <RowT lbl="FRR" val={d.zfang_frr.frr.classement === 'totalite' ? 'Classée en totalité' : d.zfang_frr.frr.classement === 'partie' ? 'Classée en partie (les Hauts)' : 'Hors dispositif'} />}
                    <RowT lbl="Dispositif" val={horsOrt ? 'hors ORT' : (o!.statut === 'acv' ? 'Action Cœur de Ville' : o!.statut === 'pvd' ? 'Petites Villes de Demain' : 'ORT (autre commune signataire)')} />
                    <RowT lbl="QPV" val={aucunQpv ? 'aucun' : `${d.qpv.length} quartier(s)`} />
                    <RowT lbl="NPNRU" val={d.anru.length > 0 ? `${d.anru.length} périmètre(s)` : 'aucun'} />
                  </div>
                  {(horsOrt || aucunQpv) && (
                    <p data-fiscalite-sans-objet className="mt-1.5 text-[11px] text-txt-dim">{[aucunQpv ? 'Aucun quartier prioritaire' : null, horsOrt ? 'hors ORT' : null].filter(Boolean).join(' · ')} — dit, jamais une carte absente.</p>
                  )}
                  <Source nom="DGFiP REI · DHUP (zonage A/B/C) · territoire_fiscal (ZFANG/FRR) · DGALN (ORT) · ANCT (QPV/NPNRU)" />
                </LigneCarte>
                )
              })()}

              {/* ═══ LE CADRE DE VIE ═══ */}
              <GroupeLabel>Le cadre de vie</GroupeLabel>

              <LigneCarte id="risques" chiffre="ppr_pct" ic="⚠" titre="Risques et contraintes"
                sous="PPR · mouvement de terrain · CatNat"
                val={d.risques.ppr_pct != null ? `${fmtDec(d.risques.ppr_pct)} % en PPR` : (d.risques.parc_national ? 'Parc National' : null)}
                badge={d.risques.ppr_pct != null} ton="orange">
                <div className="flex flex-col gap-0.5 text-[12px]">
                  <RowT lbl="PPR (risque naturel)" val={d.risques.ppr_pct != null ? `${fmtDec(d.risques.ppr_pct)} % des parcelles` : '—'} />
                  <RowT lbl="Mouvement de terrain" val={d.risques.mouvement_terrain_pct != null ? `${fmtDec(d.risques.mouvement_terrain_pct)} %` : '—'} />
                  <RowT lbl="Arrêtés CatNat" val={fmt(d.risques.catnat_arretes)} />
                  {d.risques.catnat_detail?.length ? (
                    <div className="ml-2 flex flex-col gap-0.5 border-l border-line pl-2">
                      {d.risques.catnat_detail.slice(0, 6).map((a, i) => (
                        <RowT key={a.code_national ?? i} lbl={a.type_peril}
                          val={[a.date_debut && a.date_fin ? `${a.date_debut} → ${a.date_fin}` : (a.date_arrete ?? ''),
                                a.code_national].filter(Boolean).join(' · ')} />
                      ))}
                      {d.risques.catnat_arretes > 6 ? (
                        <div className="text-[11px] text-txt-dim">et {d.risques.catnat_arretes - 6} autre{d.risques.catnat_arretes - 6 > 1 ? 's' : ''}…</div>
                      ) : null}
                    </div>
                  ) : null}
                  {d.risques.azi_tri && (d.risques.azi_tri.azi?.length || d.risques.azi_tri.tri?.length) ? (
                    <RowT lbl="Inondation (AZI / TRI)"
                      val={[...(d.risques.azi_tri.azi ?? []).map((x: { libelle?: string }) => `AZI ${x.libelle ?? ''}`),
                            ...(d.risques.azi_tri.tri ?? []).map((x: { libelle?: string }) => `TRI ${x.libelle ?? ''}`)].join(' · ')} />
                  ) : d.risques.azi_tri ? (
                    <RowT lbl="Inondation (AZI / TRI)" val="aucun document recensé (GASPAR)" />
                  ) : null}
                  <RowT lbl="Aire d'adhésion Parc National" val={d.risques.parc_national ? 'oui' : 'non'} />
                </div>
                <Source nom={d.risques.source} />
              </LigneCarte>

              <LigneCarte id="equipements" ic="⌘" titre="Équipements et desserte"
                sous="services, transport, réseaux"
                val={undefined}>
                <p className="text-[12px] leading-relaxed text-txt-mut">Équipements (écoles, santé, commerces), transport public, trafic, fibre, assainissement et productible
                  solaire de la commune se lisent au plus près dans l'Étude de zone (autour d'un point).</p>
                <Shortcut label="Étude de zone — habitants, emplois, concurrents" onClick={() => ouvrirOutil(commune, insee, 'etude-zone')} />
                <Source nom="BPE INSEE · GTFS PAN · OSM · Arcep · INSEE RP · PVGIS (via Étude de zone)" />
              </LigneCarte>

              <button data-voir-plus-outils onClick={() => { const s = useApp.getState(); s.setContexteCommune(null); s.toggleOutils() }}
                className="mt-2 text-[11.5px] text-mint transition-colors duration-quick hover:underline">Voir tous les outils →</button>
            </div>

'''

out = src[:i] + NEW + src[j:]
open(f, "w").write(out)
print("surgery done — lignes:", out.count(chr(10)) + 1)
