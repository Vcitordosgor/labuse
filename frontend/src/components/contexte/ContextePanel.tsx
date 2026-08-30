import { useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'
import { getContexteCommune, modVelocite, motMarcheCommune, motRarete } from '../../lib/api'
import { TOKENS } from '../../lib/tokens'
import { useApp } from '../../store/useApp'
import { Loading } from '../Loading'
import { MarcheCommune } from '../outils/moteurs'

const fmt = (n: number | null | undefined) => (n == null ? '—' : Math.round(Number(n)).toLocaleString('fr-FR'))

// R4 — helpers transférés de l'ex-fiche-outil Communes (ligne libellé/valeur + format suffixé).
const fmtV = (v: unknown, s = '') => (v == null ? '—' : `${Number(v).toLocaleString('fr-FR')}${s}`)
function RowT({ lbl, val, strong }: { lbl: string; val: string; strong?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-2">
      <span className="min-w-0 text-txt-mut">{lbl}</span>
      <span className={`tnum shrink-0 ${strong ? 'font-semibold text-mint' : 'text-txt'}`}>{val}</span>
    </div>
  )
}

//: statut SRU → couleur + lecture métier (une phrase sobre — le ciblage de la promotrice)
const SRU_META: Record<string, { color: string; label: string; lecture: string }> = {
  carencee: { color: TOKENS.stEcartee, label: 'CARENCÉE',
    lecture: 'Commune en carence SRU : forte pression de production de logement social — les programmes avec part LLS y sont attendus (et souvent facilités).' },
  deficitaire: { color: TOKENS.stCreuser, label: 'DÉFICITAIRE',
    lecture: 'Sous l’objectif légal : la commune doit produire du logement social — un programme mixte y répond à une obligation réelle.' },
  exemptee: { color: TOKENS.txtMut, label: 'EXEMPTÉE 2023-2025',
    lecture: 'Soumise SRU mais exemptée d’obligations sur la période (décret) — pression de production sociale suspendue.' },
  conforme: { color: TOKENS.stChaude, label: 'CONFORME',
    lecture: 'Objectif SRU atteint — pas de pression réglementaire de rattrapage social.' },
}

function Source({ nom, url }: { nom?: string | null; url?: string | null }) {
  if (!nom) return null
  return (
    <p className="mt-1.5 text-[11px] leading-snug text-txt-dim">
      Source :{' '}
      {url ? <a href={url} target="_blank" rel="noreferrer" className="text-mint hover:underline">{nom} ↗</a> : nom}
    </p>
  )
}

function Bar({ parts }: { parts: { label: string; pct: number; color: string }[] }) {
  return (
    <div>
      <div className="flex h-1.5 overflow-hidden rounded-full bg-line">
        {parts.map((p) => <span key={p.label} style={{ width: `${p.pct}%`, background: p.color }} />)}
      </div>
      <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5">
        {parts.map((p) => (
          <span key={p.label} className="flex items-center gap-1 text-[11px] text-txt-mut">
            <span className="h-1.5 w-1.5 rounded-full" style={{ background: p.color }} />{p.label} {p.pct.toLocaleString('fr-FR')} %
          </span>
        ))}
      </div>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="border-b border-line px-5 py-4">
      <p className="label-caps mb-2">{title}</p>
      {children}
    </section>
  )
}

// K2 — une ligne de coordonnée mairie : valeur, lien optionnel, ou « Absent » (jamais inventé).
function MairieLigne({ label, val, href }: { label: string; val: string | null; href?: string }) {
  return (
    <div className="flex gap-2">
      <dt className="w-[74px] shrink-0 text-txt-dim">{label}</dt>
      <dd className="min-w-0 flex-1 break-words text-txt">
        {val == null
          ? <span className="text-txt-dim italic">Absent</span>
          : href
            ? <a href={href} target="_blank" rel="noreferrer" className="text-mint hover:underline">{val}</a>
            : val}
      </dd>
    </div>
  )
}

function fmtDateFr(iso: string): string {
  try {
    return new Intl.DateTimeFormat('fr-FR', { day: '2-digit', month: 'long', year: 'numeric' }).format(new Date(iso))
  } catch { return iso }
}

/** FICHE COMMUNE UNIQUE (RETOURS-1 R4, Vic) — l'ex-fiche de l'outil Communes a fusionné ICI :
 *  en plus du contexte officiel (SRU · ANRU · PLH · marché INSEE · QPV), le panneau porte les
 *  blocs transférés — MARCHÉ local (MarcheCommune, 9 lignes sourcées + signal), RARETÉ & ZAN,
 *  VÉLOCITÉ — et « Voir ses parcelles → ». Aucune de ces données n'entre dans le scoring. */
export function ContextePanel() {
  const { contexteCommune, setContexteCommune } = useApp()
  const q = useQuery({
    queryKey: ['contexte', contexteCommune],
    queryFn: () => getContexteCommune(contexteCommune!),
    enabled: !!contexteCommune,
  })
  // R4 — blocs transférés de l'ex-fiche-outil. Mêmes clés React Query que l'ex-CommuneFiche
  // (dédoublonnage, 0 fetch en plus quand l'outil a déjà chargé).
  const rar = useQuery({ queryKey: ['communes-rarete'], queryFn: motRarete, enabled: !!contexteCommune })
  const vel = useQuery({ queryKey: ['communes-velocite'], queryFn: () => modVelocite(), enabled: !!contexteCommune })
  const mar = useQuery({ queryKey: ['mu-marche', contexteCommune], queryFn: () => motMarcheCommune(contexteCommune!), enabled: !!contexteCommune })
  useEffect(() => {
    const h = (e: KeyboardEvent) => e.key === 'Escape' && setContexteCommune(null)
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [setContexteCommune])
  if (!contexteCommune) return null
  const d = q.data
  const r = (rar.data?.communes ?? []).find((c) => (c as Record<string, unknown>)['commune'] === contexteCommune) as Record<string, any> | undefined
  const v = (vel.data?.communes ?? []).find((c) => (c as Record<string, unknown>)['commune'] === contexteCommune) as Record<string, any> | undefined
  const homogene = vel.data?.['communes_homogenes'] as boolean | undefined
  const sig = mar.data?.['market_signal'] as Record<string, any> | undefined
  const sigLabel = sig?.['disponible'] ? String(sig['label']) : null
  const sigCol = sigLabel === 'favorable' ? TOKENS.mint : sigLabel === 'prudence' ? TOKENS.stEcartee : TOKENS.stCreuser

  return (
    <aside data-contexte-panel className="absolute right-0 top-0 z-30 flex h-full w-[420px] flex-col border-l border-line bg-surface-1 shadow-elev-3">
      <div className="flex shrink-0 items-center justify-between border-b border-line px-5 py-3">
        <div>
          <p className="label-caps text-txt-mut">Fiche commune</p>
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="font-display text-lg font-bold text-txt-hi">{contexteCommune}</h2>
            {sigLabel && (
              <span data-fiche-signal className="rounded-full border px-2 py-0.5 text-[10.5px] font-medium"
                style={{ color: sigCol, borderColor: `${sigCol}55`, background: `${sigCol}22` }}>
                signal : {sigLabel}
              </span>
            )}
          </div>
          {d?.epci && <p className="text-[10.5px] text-txt-mut">{d.epci} — {d.epci_nom}</p>}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {/* F6 (OUTILS-3) — on QUITTE l'analyse (Outils) pour l'EXPLORATION : bascule sur l'onglet
              CARTES (Couches + Filtres), commune posée comme périmètre actif. setView('cartes') ferme
              l'outil et la fiche ; `commune` (posée AVANT) survit à setView. */}
          <button data-communes-parcelles onClick={() => { const s = useApp.getState(); s.setCommune(contexteCommune); s.setView('cartes') }}
            title="Basculer sur la carte, filtrée sur cette commune"
            className="rounded-md border border-mint/50 bg-mint/15 px-2.5 py-1 text-[11px] font-medium text-mint transition-colors duration-quick hover:bg-mint/25">
            Voir ses parcelles →
          </button>
          <button onClick={() => setContexteCommune(null)} className="text-txt-dim hover:text-txt-hi" title="Fermer (Échap)" aria-label="Fermer">✕</button>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {q.isLoading && <div className="p-5"><Loading label="Chargement du contexte commune" className="text-xs" /></div>}
        {q.isError && <p className="p-5 text-xs text-st-ecartee">Erreur de chargement — réessayez.</p>}
        {d && (
          <>
            {/* M55-C point 1 (arbitrage Vic) : bandeau RNU générique en TÊTE de fiche — pour toute
                commune sans PLU opposable (source config/rnu_communes.yaml). Dit franchement pourquoi
                l'écran n'a pas de zonage : constructibilité au cas par cas (règles nationales). */}
            {d.rnu && (
              <div data-rnu-bandeau className="border-b border-line px-5 py-4">
                <div className="rounded-lg border border-st-creuser/40 bg-st-creuser/[0.10] px-3 py-2.5">
                  <p className="flex items-center gap-1.5 text-[12.5px] font-semibold text-st-creuser">
                    <span aria-hidden="true">⚑</span>{d.rnu.libelle}
                  </p>
                  <p className="mt-1 text-[11px] leading-relaxed text-txt">{d.rnu.detail}</p>
                </div>
              </div>
            )}
            {/* M83 C1 — LE FONCIER DE LA COMMUNE, EN TÊTE (c'est le produit). Points de calcul EXISTANTS
                réutilisés (M79 prix terrain nu / permis, agrégats bruts pour parcelles/surface/zonage/
                mutations) — aucun recalcul local. */}
            {d.foncier && (
              <Section title="LE FONCIER DE LA COMMUNE">
                <div className="mb-3 flex gap-5">
                  <div><p className="font-display text-lg font-bold text-txt-hi">{fmt(d.foncier.n_parcelles)}</p><p className="text-[11px] text-txt-dim">parcelles cadastrées</p></div>
                  {d.foncier.surface_ha != null && (
                    <div><p className="font-display text-lg font-bold text-txt-hi">{fmt(d.foncier.surface_ha)} ha</p><p className="text-[11px] text-txt-dim">surface cadastrée</p></div>
                  )}
                </div>
                {d.foncier.repartition_zonage && (() => {
                  const z = d.foncier.repartition_zonage; const t = z.total || 1
                  const pc = (n: number) => Math.round(1000 * n / t) / 10
                  return (
                    <div className="mb-3">
                      <p className="mb-1 flex items-center gap-1.5 text-[11px] text-txt-dim">Répartition par famille de zonage
                        <span className="rounded bg-mint/10 px-1 text-[9px] text-mint">Sourcé · zonage calibré</span></p>
                      <Bar parts={[
                        { label: 'U', pct: pc(z.U), color: TOKENS.mint },
                        { label: 'AU', pct: pc(z.AU), color: TOKENS.vizCyan },
                        { label: 'A', pct: pc(z.A), color: TOKENS.stCreuser },
                        { label: 'N', pct: pc(z.N), color: TOKENS.vizGreenDeep },
                      ]} />
                    </div>
                  )
                })()}
                <div className="mb-3 rounded-lg border border-line-2 bg-surface-3 px-3 py-2">
                  <p className="text-[11.5px] text-txt"><b>{fmt(d.foncier.classement.evaluees)}</b> parcelles évaluées au classement servi</p>
                  {d.foncier.classement.sans_zonage > 0 && (
                    <p className="mt-0.5 text-[11px] leading-snug text-txt-dim">dont <b className="text-st-creuser">{fmt(d.foncier.classement.sans_zonage)}</b> sans zonage publié — non classables ({d.foncier.classement.raison_sans_zonage}).</p>
                  )}
                </div>
                {d.foncier.prix_terrain_nu.par_zone && (
                  <div className="mb-3">
                    <p className="mb-1 flex flex-wrap items-center gap-1.5 text-[11px] text-txt-dim">Prix médian du terrain nu, par zone
                      {d.foncier.prix_terrain_nu.etiquette && <span className="rounded bg-mint/10 px-1 text-[9px] text-mint">{d.foncier.prix_terrain_nu.etiquette}</span>}</p>
                    <div className="flex gap-5">
                      {(['U', 'AU'] as const).map((fam) => {
                        const pz = d.foncier!.prix_terrain_nu.par_zone?.[fam]
                        if (!pz || !pz.calculable) return (
                          <div key={fam}><p className="font-display text-sm text-txt-mut">zone {fam} —</p><p className="text-[10.5px] text-txt-dim">échantillon insuffisant (&lt; {d.foncier!.prix_terrain_nu.seuil_n} ventes)</p></div>
                        )
                        return (
                          <div key={fam}>
                            <p className="font-display text-base font-bold text-txt-hi">{fmt(pz.median_eur_m2)} €/m²</p>
                            <p className="text-[10.5px] text-txt-dim">zone {fam} · {fmt(pz.n)} ventes{(pz.n ?? 0) < 5 ? ' (fragile)' : ''}</p>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}
                <div className="flex gap-5">
                  <div><p className="font-display text-lg font-bold text-txt-hi">{fmt(d.foncier.mutations_12m)}</p><p className="text-[11px] text-txt-dim">mutations (12 mois, DVF)</p></div>
                  <div><p className="font-display text-lg font-bold text-txt-hi">{fmt(d.foncier.permis_12m.n)}</p><p className="text-[11px] text-txt-dim">permis (12 mois, Sitadel)</p></div>
                </div>
                <p className="mt-1.5 text-[10.5px] leading-snug text-txt-dim">Prix terrain nu, mutations et permis : point de calcul Marché (M79) — DVF (actes) + Sitadel (autorisations, {d.foncier.permis_12m.reserve}).</p>
              </Section>
            )}
            {/* R4 — MARCHÉ local (transféré de l'ex-fiche-outil Communes, M137-Z) : les 9 lignes
                sourcées Prix / Dynamique / Offre / Loyer via MarcheCommune (mode embarqué). */}
            <Section title="MARCHÉ">
              {/* Réconciliation € ancien : ICI = prix LOCAL (secteur autour de la parcelle centrale,
                  appartements priorisés) ; le tableau des 24 communes = médiane COMMUNE ENTIÈRE.
                  Deux séries légitimes → un écart est normal, pas une erreur. */}
              <p className="mb-1 text-[10px] leading-snug text-txt-dim">
                Prix ancien = médiane <b>locale</b> (secteur autour de la parcelle centrale). Le tableau des
                24 communes affiche la médiane <b>commune entière</b> — les deux diffèrent normalement.
              </p>
              <MarcheCommune communeProp={contexteCommune} />
            </Section>

            {/* R4 — RARETÉ & ZAN (transféré, M137-Z) : le STOCK porte « foncier » ; « reste ZAN » =
                un droit à artificialiser, ESTIMÉ, jamais un droit à construire. */}
            <Section title="RARETÉ &amp; ZAN">
              {r ? (
                <div className="flex flex-col gap-0.5 text-[11px]">
                  <RowT lbl="Foncier repéré — stock de parcelles promues" val={fmtV(r['stock_opportunites_ha'], ' ha')} strong />
                  {r['pct_budget_consomme'] != null && (
                    <div className="mt-0.5 rounded-md bg-surface-3 px-2 py-1">
                      <div className="flex items-baseline gap-1.5">
                        <b className={`tnum text-[14px] ${(r['pct_budget_restant'] as number) < 0 ? 'text-st-ecartee' : 'text-st-creuser'}`}>{r['pct_budget_consomme']} %</b>
                        <span className="text-[10px] text-txt-mut">du budget ZAN consommé</span>
                        <span className={`ml-auto tnum text-[11px] ${(r['pct_budget_restant'] as number) < 0 ? 'text-st-ecartee' : 'text-txt'}`}>{r['pct_budget_restant']} % restant</span>
                      </div>
                      <p className="mt-0.5 text-[9px] leading-snug text-st-creuser"><b>Estimé</b> (règle -50 %, SAR non territorialisé) — <b>pas un droit à construire</b>.</p>
                    </div>
                  )}
                  <RowT lbl="Droit à artificialiser restant (ZAN, estimé)" val={fmtV(r['reste_zan_ha'], ' ha')} />
                  <RowT lbl="Budget ZAN 2021-31 (estimé)" val={fmtV(r['budget_zan_ha'], ' ha')} />
                  <RowT lbl="Rythme de consommation" val={fmtV(r['rythme_conso_ha_an'], ' ha/an')} />
                  <RowT lbl="Horizon d'épuisement de l'enveloppe ZAN" val={r['horizon_epuisement_ans'] == null ? 'non projetable' : `${r['horizon_epuisement_ans']} ans`} />
                  <p className="mt-1 text-[9.5px] leading-snug text-txt-dim">{rar.data?.caveat}</p>
                </div>
              ) : <p className="text-[11px] text-txt-dim">Donnée ENAF/ZAN indisponible pour cette commune.</p>}
            </Section>

            {/* R4 — VÉLOCITÉ administrative (transféré, M137-Z) : tranche p25-p75, homogénéité dite. */}
            <Section title="VÉLOCITÉ ADMINISTRATIVE">
              {v ? (
                <div className="text-[11px] text-txt">
                  <p>Délai d'instruction (dépôt → autorisation) :{' '}
                    <b className="tnum">{fmtV(v['delai_p25_mois'])} à {fmtV(v['delai_p75_mois'])} mois</b>{' '}
                    <span className="text-txt-dim">(tranche p25–p75, {fmtV(v['n_valide'])} dossiers)</span></p>
                  {homogene && <p className="mt-1 text-[9.5px] leading-snug text-txt-dim">{vel.data?.['note_homogeneite'] as string}</p>}
                </div>
              ) : <p className="text-[11px] text-txt-dim">Donnée délais indisponible pour cette commune.</p>}
            </Section>

            {/* K2 — COORDONNÉES DE LA MAIRIE (Annuaire de l'administration). Un champ absent affiche
                « Absent » (jamais inventé) ; la fraîcheur = date de relevé de l'annuaire. */}
            {d.mairie && (
              <Section title="MAIRIE">
                <dl className="space-y-1.5 text-[12px]">
                  <MairieLigne label="Adresse" val={[d.mairie.adresse, [d.mairie.code_postal, d.mairie.commune].filter(Boolean).join(' ')].filter(Boolean).join(', ') || null} />
                  <MairieLigne label="Téléphone" val={d.mairie.telephone} href={d.mairie.telephone ? `tel:${d.mairie.telephone.replace(/\s/g, '')}` : undefined} />
                  <MairieLigne label="E-mail" val={d.mairie.email} href={d.mairie.email ? `mailto:${d.mairie.email}` : undefined} />
                  <MairieLigne label="Site officiel" val={d.mairie.site_officiel} href={d.mairie.site_officiel ?? undefined} />
                  <MairieLigne label="Annuaire" val={d.mairie.url_annuaire ? 'Fiche service-public' : null} href={d.mairie.url_annuaire ?? undefined} />
                </dl>
                <p className="mt-2 text-[10.5px] leading-snug text-txt-dim">{d.mairie.source}{d.mairie.date_import ? ` · relevé le ${fmtDateFr(d.mairie.date_import)}` : ''}</p>
              </Section>
            )}
            {/* L1 (KF-2) — ACQUISITIONS PM RÉCENTES : le bloc a QUITTÉ cette fiche (RETOURS-1 R3,
                Vic) — il vit désormais dans l'outil Communes › « Acquisitions récentes », uniquement.
                Le payload `acquisitions_pm` reste servi par le back (réversible), non rendu ici. */}
            {/* M55-B point 4a (décision Vic) : le bloc « CLASSEMENT LABUSE » (compteurs de
                production — parcelles brûlantes/chaudes, propriétaires PM) est RETIRÉ de la fiche
                de CONTEXTE commune. Le client n'a pas à y voir nos compteurs internes ; cette fiche
                ne sert que du contexte officiel sourcé (SRU / NPNRU / PLH / marché INSEE / QPV). */}
            <Section title="SRU — LOGEMENT SOCIAL">
              {d.sru ? (() => {
                const m = SRU_META[d.sru.statut] ?? SRU_META.conforme
                return (
                  <>
                    <div className="rounded-lg border px-3 py-2" style={{ borderColor: `${m.color}55`, background: `${m.color}14` }}>
                      <span className="font-display text-[15px] font-bold" style={{ color: m.color }}>
                        SRU {Number(d.sru.taux_lls).toLocaleString('fr-FR')} %
                      </span>
                      <span className="ml-2 text-xs text-txt-mut">objectif {Number(d.sru.objectif_pct).toLocaleString('fr-FR')} %</span>
                      <span className="ml-2 rounded-full px-2 py-0.5 text-[11px] font-semibold" style={{ color: m.color, background: `${m.color}22` }}>{m.label}</span>
                      {Number(d.sru.prelevement_eur) > 0 && (
                        <p className="mt-1 text-[10.5px] text-txt-mut">Prélèvement 2025 : {fmt(d.sru.prelevement_eur)} €</p>
                      )}
                    </div>
                    <p className="mt-2 text-[11px] leading-relaxed text-txt">{m.lecture}</p>
                    <p className="mt-1 text-[11px] text-txt-dim">{fmt(d.sru.detail?.nb_lls)} LLS à l’inventaire · {d.sru.millesime}</p>
                    <Source nom={d.sru.source_nom} url={d.sru.source_url} />
                  </>
                )
              })() : <p className="text-xs text-txt-mut">Non disponible pour cette commune (source SRU DHUP).</p>}
            </Section>

            <Section title="RENOUVELLEMENT URBAIN — NPNRU">
              {d.anru.length > 0 ? (
                <>
                  {d.anru.map((a) => (
                    <div key={a.nom} className="mb-1.5 rounded-lg border border-line-2 bg-surface-3 px-3 py-2">
                      <span className="text-xs font-medium text-txt-hi">{a.nom}</span>
                      <span className="ml-2 rounded-full border border-line-2 bg-surface-3 px-2 py-0.5 text-[11px] font-medium text-txt-mut">intérêt {a.interet}</span>
                      <p className="mt-0.5 text-[11px] text-txt-dim">{a.code_qpv} · activer la couche « ANRU » sur la carte</p>
                    </div>
                  ))}
                  <Source nom={d.anru[0].source_nom} url={d.anru[0].source_url} />
                </>
              ) : <p className="text-xs text-txt-mut">Aucun périmètre NPNRU sur cette commune (8 quartiers d’intérêt national à La Réunion, aucun régional).</p>}
              <p className="mt-2 text-[11px] leading-snug text-txt-dim">{d.notes[0]}</p>
            </Section>

            <Section title={`PLH ${d.epci ?? ''} — PROGRAMME LOCAL DE L'HABITAT`}>
              {d.plh ? (
                <>
                  <div className="flex gap-4">
                    {d.plh.obj_logements_an != null && (
                      <div><p className="font-display text-lg font-bold text-txt-hi">{fmt(d.plh.obj_logements_an)}</p>
                        <p className="text-[11px] text-txt-dim">logements / an (objectif)</p></div>
                    )}
                    {d.plh.part_sociale_pct != null && (
                      <div><p className="font-display text-lg font-bold text-txt-hi">{Number(d.plh.part_sociale_pct).toLocaleString('fr-FR')} %</p>
                        <p className="text-[11px] text-txt-dim">part sociale visée</p></div>
                    )}
                  </div>
                  <p className="mt-1 text-[10.5px] text-txt-mut">{d.plh.periode} · {d.plh.statut}</p>
                  {(d.plh.refs ?? []).map((r: { doc: string; url?: string; page?: string | number }, i: number) => (
                    <p key={i} className="mt-0.5 text-[11px] text-txt-dim">
                      Réf. : {r.url ? <a className="text-mint hover:underline" href={r.url} target="_blank" rel="noreferrer">{r.doc} ↗</a> : r.doc}{r.page ? ` — p. ${r.page}` : ''}
                    </p>
                  ))}
                </>
              ) : (
                <p className="text-xs text-txt-mut">
                  Non disponible — PLH {d.epci ?? ''} non retrouvé en source publique vérifiable
                  (extraction documentaire : aucun chiffre n’est affiché sans sa référence).
                </p>
              )}
            </Section>

            <Section title="MARCHÉ LOGEMENT — INSEE RP 2023">
              {d.marche ? (
                <>
                  <div className="mb-2 flex gap-4">
                    <div><p className="font-display text-lg font-bold text-txt-hi">{fmt(d.marche.logements)}</p><p className="text-[11px] text-txt-dim">logements</p></div>
                    <div><p className="font-display text-lg font-bold text-txt-hi">{fmt(d.marche.vacants)}</p><p className="text-[11px] text-txt-dim">vacants ({d.marche.typologie?.vacance_pct?.toLocaleString?.('fr-FR') ?? d.marche.typologie?.vacance_pct} %)</p></div>
                  </div>
                  <div className="flex flex-col gap-2.5">
                    {/* M55-B point 4b : INSEE distingue 3 statuts d'occupation (propriétaire /
                        locataire / logé gratuitement). N'afficher que loc+prop laissait un reste
                        muet (~4 %) ; on nomme ce reste « logés gratuitement » (résiduel dérivé,
                        arrondi) pour que la barre somme à 100 et ne mente pas par omission. */}
                    {(() => {
                      const loc = Number(d.marche.locataires_pct)
                      const prop = Number(d.marche.proprietaires_pct)
                      const autres = Math.max(0, Math.round((100 - loc - prop) * 10) / 10)
                      return (
                        <Bar parts={[
                          { label: 'locataires', pct: loc, color: TOKENS.vizCyan },
                          { label: 'propriétaires', pct: prop, color: TOKENS.mint },
                          ...(autres >= 1 ? [{ label: 'logés gratuitement', pct: autres, color: TOKENS.txtMut }] : []),
                        ]} />
                      )
                    })()}
                    <Bar parts={[
                      { label: 'maisons', pct: Number(d.marche.maisons_pct), color: TOKENS.stSurveiller },
                      { label: 'appartements', pct: Number(d.marche.apparts_pct), color: TOKENS.vizCyan },
                    ]} />
                  </div>
                  {d.marche.typologie && (
                    <div className="mt-3">
                      <p className="mb-1 text-[11px] text-txt-dim" title={d.marche.typologie.libelle}>
                        Résidences principales par nombre de pièces (1 à 5+ pièces — approche la typologie)
                      </p>
                      <Bar parts={(['p1', 'p2', 'p3', 'p4', 'p5p'] as const).map((k, i) => {
                        const total = ['p1', 'p2', 'p3', 'p4', 'p5p'].reduce((s, kk) => s + (d.marche!.typologie[kk] ?? 0), 0) || 1
                        return { label: k === 'p5p' ? '5p+' : k.replace('p', '') + 'p',
                                 pct: Math.round(1000 * (d.marche!.typologie[k] ?? 0) / total) / 10,
                                 color: [TOKENS.vizGreenDeep, TOKENS.stSurveiller, TOKENS.mint, TOKENS.vizCyan, TOKENS.txtMut][i] }
                      })} />
                    </div>
                  )}
                  <Source nom={d.marche.source_nom} url={d.marche.source_url} />
                </>
              ) : <p className="text-xs text-txt-mut">Non disponible (INSEE RP).</p>}
            </Section>

            <Section title="QUARTIERS PRIORITAIRES — QPV (rappel)">
              {d.qpv.length > 0 ? (
                <p className="text-xs text-txt">{d.qpv.length} QPV (génération 2024) : {d.qpv.map((x) => x.nom).join(' · ')}</p>
              ) : <p className="text-xs text-txt-mut">Aucun QPV sur cette commune.</p>}
              <p className="mt-2 text-[11px] leading-snug text-txt-dim">{d.notes[1]}</p>
            </Section>
          </>
        )}
      </div>
    </aside>
  )
}
