import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { getContexteCommune, modVelocite, motMarcheCommune, motRarete } from '../../lib/api'
import { TOKENS } from '../../lib/tokens'
import { useApp } from '../../store/useApp'
import { Loading } from '../Loading'

const fmt = (n: number | null | undefined) => (n == null ? '—' : Math.round(Number(n)).toLocaleString('fr-FR'))
const fmtV = (v: unknown, s = '') => (v == null ? '—' : `${Number(v).toLocaleString('fr-FR')}${s}`)
const fmtDec = (n: number | null | undefined, s = '') => (n == null ? '—' : `${Number(n).toLocaleString('fr-FR', { maximumFractionDigits: 1 })}${s}`)

function RowT({ lbl, val, strong }: { lbl: string; val: string; strong?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-2 py-0.5">
      <span className="min-w-0 text-txt-mut">{lbl}</span>
      <span className={`tnum shrink-0 text-right ${strong ? 'font-semibold text-mint' : 'text-txt'}`}>{val}</span>
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
    <p className="mt-2 text-[10.5px] leading-snug text-txt-dim">
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

// OUTILS-6 C4 — l'accordéon. Son état ouvert/fermé est MÉMORISÉ d'une fiche à l'autre (localStorage,
// par identifiant de section) : un client retrouve ses sections de prédilection. `dot` = pastille de
// signal (couleur), `cle` = le chiffre-clé porté SUR LA LIGNE FERMÉE (on lit l'essentiel sans ouvrir).
const ACC_LS = 'labuse.fiche.acc'
function readAcc(id: string, def: boolean): boolean {
  try { const o = JSON.parse(localStorage.getItem(ACC_LS) || '{}'); return typeof o[id] === 'boolean' ? o[id] : def }
  catch { return def }
}
function writeAcc(id: string, v: boolean) {
  try { const o = JSON.parse(localStorage.getItem(ACC_LS) || '{}'); o[id] = v; localStorage.setItem(ACC_LS, JSON.stringify(o)) }
  catch { /* localStorage indisponible — l'accordéon reste fonctionnel, sans mémoire */ }
}
function Acc({ id, title, cle, dot, defaultOpen, children }: {
  id: string; title: string; cle?: string; dot?: string; defaultOpen?: boolean; children: React.ReactNode
}) {
  const [open, setOpen] = useState(() => readAcc(id, !!defaultOpen))
  return (
    <details data-acc={id} open={open} className="border-b border-line"
      onToggle={(e) => { const o = (e.currentTarget as HTMLDetailsElement).open; setOpen(o); writeAcc(id, o) }}>
      <summary className="flex cursor-pointer list-none items-center gap-2 px-5 py-3 text-[13.5px] font-semibold text-txt-hi [&::-webkit-details-marker]:hidden">
        <span className="h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: dot || TOKENS.mint }} />
        {title}
        {cle && <span data-acc-cle className="ml-auto pr-1 font-mono text-[11px] font-normal text-txt-mut">{cle}</span>}
        <span className={`text-txt-dim transition-transform ${cle ? '' : 'ml-auto'}`} aria-hidden>›</span>
      </summary>
      <div className="px-5 pb-4 pt-1">{children}</div>
    </details>
  )
}

// K2 — une ligne de coordonnée mairie : valeur, lien optionnel, ou « Absent » (jamais inventé).
function MairieLigne({ label, val, href }: { label: string; val: string | null; href?: string }) {
  return (
    <div className="flex gap-2">
      <dt className="w-[74px] shrink-0 text-txt-dim">{label}</dt>
      <dd className="min-w-0 flex-1 break-words text-txt">
        {val == null ? <span className="italic text-txt-dim">Absent</span>
          : href ? <a href={href} target="_blank" rel="noreferrer" className="text-mint hover:underline">{val}</a> : val}
      </dd>
    </div>
  )
}

function fmtDateFr(iso: string): string {
  try { return new Intl.DateTimeFormat('fr-FR', { day: '2-digit', month: 'long', year: 'numeric' }).format(new Date(iso)) }
  catch { return iso }
}

// OUTILS-6 C6 — ouvrir un outil AVEC LA COMMUNE DÉJÀ SÉLECTIONNÉE (jamais un formulaire vide). On pose la
// commune (filtre global lu par la plupart des outils) puis on ouvre le module et on ferme la fiche.
function ouvrirOutil(commune: string, insee: string | null, quoi: string) {
  const s = useApp.getState()
  s.setCommune(commune)
  s.setCommunesFilter([commune])
  if (quoi === 'plu') { if (insee) s.setPluPrefill({ insee, zone: null }); s.setModule('plu') }
  else if (quoi === 'radar') { s.openRadar() }
  else if (quoi === 'communes') { s.setModule('communes'); s.setCommunesTableOpen(true) }
  else { s.setModule(quoi) }
  s.setContexteCommune(null)
}

function OutilLigne({ ic, nom, sous, onClick }: { ic: string; nom: string; sous: string; onClick: () => void }) {
  return (
    <button data-passerelle onClick={onClick}
      className="flex w-full items-center gap-3 border-b border-line py-2.5 text-left last:border-b-0 hover:bg-surface-2">
      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-line bg-surface-2 text-[13px] text-mint">{ic}</span>
      <span className="min-w-0 flex-1">
        <b className="block text-[13px] font-semibold text-txt-hi">{nom}</b>
        <span className="block text-[11.5px] text-txt-mut">{sous}</span>
      </span>
      <span className="text-mint">→</span>
    </button>
  )
}

function Shortcut({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button data-passerelle onClick={onClick}
      className="mt-3 inline-block rounded-lg border border-mint/30 px-2.5 py-1 text-[11.5px] text-mint hover:bg-mint/10">
      {label} →
    </button>
  )
}

/** FICHE COMMUNE (OUTILS-6) — un en-tête qui décide + des accordéons ordonnés selon la question d'un
 *  promoteur (constat → action → contexte). Chaque section porte son chiffre-clé sur la ligne fermée, sa
 *  ligne de sources datées, et — quand c'est utile — une passerelle vers l'outil pré-rempli sur la commune.
 *  Un seul moteur, une seule donnée : tout vient du payload `getContexteCommune` (aucun chiffre en dur). */
export function ContextePanel() {
  const { contexteCommune, setContexteCommune } = useApp()
  const q = useQuery({ queryKey: ['contexte', contexteCommune], queryFn: () => getContexteCommune(contexteCommune!), enabled: !!contexteCommune })
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
  const sig = mar.data?.['market_signal'] as Record<string, any> | undefined
  const sigLabel = sig?.['disponible'] ? String(sig['label']) : null
  const sigCol = sigLabel === 'favorable' ? TOKENS.mint : sigLabel === 'prudence' ? TOKENS.stEcartee : TOKENS.stCreuser
  // tendance / liquidité : lues sur les lignes du MÊME moteur Marché commune (build_marche_commune)
  const marLignes = (mar.data?.['lignes'] ?? []) as Record<string, any>[]
  const ligneMar = (cle: string) => marLignes.find((l) => l['cle'] === cle)?.['valeurs'] as Record<string, any> | undefined
  const tend = ligneMar('tendance_12m')
  const commune = contexteCommune
  const insee = d?.insee ?? null

  return (
    <aside data-contexte-panel className="absolute right-0 top-0 z-30 flex h-full w-[420px] flex-col border-l border-line bg-surface-1 shadow-elev-3">
      <div className="flex shrink-0 items-start justify-between border-b border-line px-5 py-3">
        <div className="min-w-0">
          <p className="label-caps text-txt-mut">Fiche commune</p>
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="font-display text-lg font-bold text-txt-hi">{commune}</h2>
            {sigLabel && (
              <span data-fiche-signal className="rounded-full border px-2 py-0.5 text-[10.5px] font-medium"
                style={{ color: sigCol, borderColor: `${sigCol}55`, background: `${sigCol}22` }}>signal : {sigLabel}</span>
            )}
          </div>
          {d?.epci && <p className="text-[10.5px] text-txt-mut">{d.epci} — {d.epci_nom}</p>}
          {d?.foncier && (
            <p className="mt-0.5 text-[10.5px] text-txt-dim">{fmt(d.foncier.surface_ha)} ha · {fmt(d.foncier.n_parcelles)} parcelles</p>
          )}
        </div>
        <button onClick={() => setContexteCommune(null)} className="shrink-0 text-txt-dim hover:text-txt-hi" title="Fermer (Échap)" aria-label="Fermer">✕</button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {q.isLoading && <div className="p-5"><Loading label="Chargement de la fiche commune" className="text-xs" /></div>}
        {q.isError && <p className="p-5 text-xs text-st-ecartee">Erreur de chargement — réessayez.</p>}
        {d && (
          <>
            {/* EN-TÊTE PERMANENT — les quatre chiffres qui décident d'y aller ou non + les deux gestes. */}
            <div className="border-b border-line bg-surface-2/40 px-5 py-3">
              <div className="grid grid-cols-2 gap-x-4 gap-y-2.5">
                <div><p className="font-display text-[17px] font-bold text-txt-hi">{fmt(d.foncier?.prix_terrain_nu?.par_zone?.['U']?.median_eur_m2)} €/m²</p><p className="text-[10.5px] text-txt-dim">terrain nu zone U</p></div>
                <div><p className="font-display text-[17px] font-bold text-txt-hi">{fmt(d.comparable?.ancien_median_eur_m2)} €/m²</p><p className="text-[10.5px] text-txt-dim">ancien médian (commune)</p></div>
                <div><p className={`font-display text-[17px] font-bold ${(r?.['horizon_epuisement_ans'] ?? 99) < 6 ? 'text-st-ecartee' : 'text-txt-hi'}`}>{r?.['horizon_epuisement_ans'] == null ? '—' : `${fmtDec(r['horizon_epuisement_ans'])} ans`}</p><p className="text-[10.5px] text-txt-dim">avant épuisement du ZAN</p></div>
                <div><p className="font-display text-[17px] font-bold text-txt-hi">{v ? `${fmtV(v['delai_p25_mois'])}–${fmtV(v['delai_p75_mois'])} mois` : (d.comparable?.delai_median_mois != null ? `${fmtDec(d.comparable.delai_median_mois)} mois` : '—')}</p><p className="text-[10.5px] text-txt-dim">délai d'instruction</p></div>
              </div>
              <div className="mt-3 flex gap-2">
                {/* « Voir ses parcelles » — comportement OUTILS-4 inchangé (liste filtrée + regard LABUSE). */}
                <button data-communes-parcelles onClick={() => {
                  const s = useApp.getState()
                  s.setView('cartes'); s.setCommune(commune); s.setCommunesFilter([commune])
                  s.setFilter('analyseLabuse', true); s.setVerdict(true)
                }} className="flex-1 rounded-md border border-mint/50 bg-mint/15 px-2.5 py-1.5 text-[12px] font-medium text-mint hover:bg-mint/25">Voir ses parcelles →</button>
                <button data-communes-comparer onClick={() => ouvrirOutil(commune, insee, 'communes')}
                  className="flex-1 rounded-md border border-line px-2.5 py-1.5 text-[12px] font-medium text-txt hover:bg-surface-2">Comparer</button>
              </div>
            </div>

            {d.rnu && (
              <div data-rnu-bandeau className="border-b border-line px-5 py-3">
                <div className="rounded-lg border border-st-creuser/40 bg-st-creuser/[0.10] px-3 py-2.5">
                  <p className="flex items-center gap-1.5 text-[12.5px] font-semibold text-st-creuser"><span aria-hidden>⚑</span>{d.rnu.libelle}</p>
                  <p className="mt-1 text-[11px] leading-relaxed text-txt">{d.rnu.detail}</p>
                </div>
              </div>
            )}

            {/* 1 · LE FONCIER (ouvert) — qu'y a-t-il ici ? */}
            {d.foncier && (
              <Acc id="foncier" title="Le foncier" defaultOpen cle={`${fmt(d.foncier.stock_opportunites.ha)} ha repérés`}>
                <div className="mb-3 flex gap-5">
                  <div><p className="font-display text-lg font-bold text-txt-hi">{fmt(d.foncier.n_parcelles)}</p><p className="text-[11px] text-txt-dim">parcelles<i className="block not-italic text-[10px]">{fmt(d.foncier.surface_ha)} ha</i></p></div>
                  <div><p className="font-display text-lg font-bold text-txt-hi">{fmt(d.foncier.stock_opportunites.n)}</p><p className="text-[11px] text-txt-dim">stock foncier repéré<i className="block not-italic text-[10px]">{fmt(d.foncier.stock_opportunites.ha)} ha promus</i></p></div>
                </div>
                {d.densifiables?.parcelles != null && (
                  <div className="mb-3 flex gap-5">
                    <div><p className="font-display text-lg font-bold text-txt-hi">{fmt(d.densifiables.parcelles)}</p><p className="text-[11px] text-txt-dim">densifiables<i className="block not-italic text-[10px]">capacité résiduelle</i></p></div>
                    {d.densifiables.sdp_residuelle_m2 != null && <div><p className="font-display text-lg font-bold text-txt-hi">{fmt(Math.round(d.densifiables.sdp_residuelle_m2 / 1e6 * 10) / 10)} M m²</p><p className="text-[11px] text-txt-dim">SDP résiduelle théorique</p></div>}
                  </div>
                )}
                {d.foncier.repartition_zonage && (() => {
                  const f = d.foncier!.repartition_zonage!.familles
                  return (
                    <div className="mb-2">
                      <p className="mb-1 flex items-center gap-1.5 text-[11px] text-txt-dim">Répartition du zonage <span className="text-txt-mut">(parts de surface)</span>
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
                {d.foncier.prix_terrain_nu.par_zone && (
                  <div className="mt-3 flex gap-5">
                    {(['U', 'AU'] as const).map((fam) => {
                      const pz = d.foncier!.prix_terrain_nu.par_zone?.[fam]
                      return pz?.calculable
                        ? <div key={fam}><p className="font-display text-base font-bold text-txt-hi">{fmt(pz.median_eur_m2)} €/m²</p><p className="text-[10.5px] text-txt-dim">terrain nu zone {fam} · {fmt(pz.n)} ventes</p></div>
                        : <div key={fam}><p className="font-display text-sm text-txt-mut">zone {fam} —</p><p className="text-[10.5px] text-txt-dim">&lt; {d.foncier!.prix_terrain_nu.seuil_n} ventes</p></div>
                    })}
                  </div>
                )}
                <Shortcut label="Densifier l'existant — cette commune" onClick={() => ouvrirOutil(commune, insee, 'renouvellement')} />
                <Source nom={`Cadastre DGFiP · zonage PLU · ${d.densifiables?.source ?? 'analyse LABUSE'}`} />
              </Acc>
            )}

            {/* 2 · LE MARCHÉ (ouvert) — ça vaut combien, ça bouge ? */}
            <Acc id="marche" title="Le marché" defaultOpen dot={sigCol}
              cle={tend?.['pct'] != null ? `${Number(tend['pct']) > 0 ? '+' : ''}${fmtDec(tend['pct'])} % / 12 mois` : undefined}>
              <div className="flex flex-col gap-0.5 text-[12px]">
                <RowT lbl="Ancien médian (commune entière)" val={`${fmt(d.comparable?.ancien_median_eur_m2)} €/m²`} strong />
                <RowT lbl="Neuf (prix de sortie)" val={`${fmt(d.comparable?.neuf_eur_m2)} €/m²`} />
                {d.foncier?.prix_terrain_nu.par_zone && (
                  <RowT lbl="Terrain nu (U / AU)" val={`${fmt(d.foncier.prix_terrain_nu.par_zone['U']?.median_eur_m2)} · ${fmt(d.foncier.prix_terrain_nu.par_zone['AU']?.median_eur_m2)} €/m²`} />
                )}
                {d.loyer && <RowT lbl={`Loyer médian${d.loyer.type ? ` (${d.loyer.type})` : ''}`} val={`${fmtDec(d.loyer.median_eur_m2)} €/m²`} />}
                {tend?.['pct'] != null && <RowT lbl="Tendance 12 mois" val={`${Number(tend['pct']) > 0 ? '+' : ''}${fmtDec(tend['pct'])} %`} />}
                <RowT lbl="Mutations (12 mois, DVF)" val={fmt(d.foncier?.mutations_12m)} />
              </div>
              <Source nom={`DVF — médiane commune entière (même moteur que le comparateur)${d.loyer ? ` · ${d.loyer.source}` : ''}`} />
            </Acc>

            {/* 3 · LE MARCHÉ DES ANNONCES (Radar) — qu'est-ce qui est en vente maintenant ? */}
            {d.marche_annonces && (
              <Acc id="annonces" title="Le marché des annonces" dot={TOKENS.stSurveiller}
                cle={d.marche_annonces.sous_seuil ? `${d.marche_annonces.biens} bien(s)` : `${d.marche_annonces.biens} biens${d.marche_annonces.ecart_demande_acte_pct != null ? ` · ${d.marche_annonces.ecart_demande_acte_pct > 0 ? '+' : ''}${fmtDec(d.marche_annonces.ecart_demande_acte_pct)} %` : ''}`}>
                {d.marche_annonces.sous_seuil ? (
                  <p className="text-[12px] text-txt-mut">Trop peu d'annonces relevées pour un signal fiable ({d.marche_annonces.biens} bien(s), seuil {d.marche_annonces.seuil_n}). Le Radar affine la couverture au fil des relevés.</p>
                ) : (
                  <>
                    <div className="flex flex-col gap-0.5 text-[12px]">
                      <RowT lbl="Biens en vente" val={fmt(d.marche_annonces.biens)} />
                      <RowT lbl="Prix demandé médian" val={`${fmt(d.marche_annonces.prix_demande_median_eur_m2)} €/m²`} />
                      {d.marche_annonces.ecart_demande_acte_pct != null && (
                        <RowT lbl="Écart demandé / acté" strong
                          val={`${d.marche_annonces.ecart_demande_acte_pct > 0 ? '+' : ''}${fmtDec(d.marche_annonces.ecart_demande_acte_pct)} %`} />
                      )}
                    </div>
                    <p className="mt-1.5 text-[10.5px] leading-snug text-txt-dim">L'écart demandé/acté est la marge de négociation du moment — le signal exclusif LABUSE.</p>
                    <Shortcut label="Voir les annonces dans le Radar" onClick={() => ouvrirOutil(commune, insee, 'radar')} />
                  </>
                )}
                <Source nom={d.marche_annonces.source} />
              </Acc>
            )}

            {/* 4 · CONSTRUIRE ICI — combien de temps, combien de permis passent ? */}
            <Acc id="construire" title="Construire ici" cle={`${fmt(d.permis_bloc.permis_12m)} permis / 12 mois`}>
              <div className="flex flex-col gap-0.5 text-[12px]">
                <RowT lbl="Permis autorisés (12 mois)" val={`${fmt(d.permis_bloc.permis_12m)}${d.permis_bloc.permis_5a != null ? ` · ${fmt(d.permis_bloc.permis_5a)} sur 5 ans` : ''}`} strong />
                {d.permis_bloc.delai_median_mois != null && <RowT lbl="Délai d'instruction médian" val={`${fmtDec(d.permis_bloc.delai_median_mois)} mois`} />}
                {d.permis_bloc.logements_12m != null && <RowT lbl="Offre engagée" val={`${fmt(d.permis_bloc.logements_12m)} logts / 12 mois`} />}
                <RowT lbl="Permis au point mort" val={fmt(d.permis_bloc.point_mort)} />
              </div>
              <Shortcut label="Ouvrir Permis — cette commune" onClick={() => ouvrirOutil(commune, insee, 'permis')} />
              <Source nom={d.permis_bloc.source} />
            </Acc>

            {/* 5 · LA RÈGLE & LES CONTRAINTES — qu'est-ce qui m'en empêche ? */}
            <Acc id="regle" title="La règle & les contraintes" dot={TOKENS.stEcartee}
              cle={`ZAN ${r?.['horizon_epuisement_ans'] == null ? '—' : `${fmtDec(r['horizon_epuisement_ans'])} ans`} · SRU ${d.sru ? (SRU_META[d.sru.statut]?.label ?? d.sru.statut).toLowerCase() : '—'}`}>
              {/* PLU — le document d'urbanisme enfin nommé (statut CALCULÉ, jamais en dur) */}
              <div className="mb-2 rounded-lg border border-line-2 bg-surface-3 px-3 py-2">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-[12px] text-txt-mut">PLU</span>
                  <span className="text-[12.5px] font-semibold" style={{ color: d.plu_statut.statut === 'RNU' ? TOKENS.stCreuser : TOKENS.mint }}>
                    {d.plu_statut.statut}{d.plu_statut.date_reglement ? ` · ${d.plu_statut.date_reglement}` : ''}
                  </span>
                </div>
                {d.plu_statut.libelle && <p className="mt-0.5 text-[10.5px] text-txt-dim">{d.plu_statut.libelle}</p>}
                {d.plu_statut.recherche_verbatim && (
                  <button data-passerelle onClick={() => ouvrirOutil(commune, insee, 'plu')} className="mt-1 text-[11px] text-mint hover:underline">Chercher dans le règlement →</button>
                )}
              </div>
              {r && (
                <div className="mb-2 flex flex-col gap-0.5 text-[12px]">
                  <RowT lbl="Budget ZAN restant (estimé)" val={fmtV(r['reste_zan_ha'], ' ha')} />
                  <RowT lbl="Rythme de consommation" val={fmtV(r['rythme_conso_ha_an'], ' ha/an')} />
                </div>
              )}
              {d.sru && (() => {
                const m = SRU_META[d.sru.statut] ?? SRU_META.conforme
                return (
                  <div className="mb-2 rounded-lg border px-3 py-2" style={{ borderColor: `${m.color}55`, background: `${m.color}14` }}>
                    <span className="font-display text-[14px] font-bold" style={{ color: m.color }}>SRU {Number(d.sru.taux_lls).toLocaleString('fr-FR')} %</span>
                    <span className="ml-2 text-[11px] text-txt-mut">objectif {Number(d.sru.objectif_pct).toLocaleString('fr-FR')} %</span>
                    <span className="ml-2 rounded-full px-2 py-0.5 text-[10.5px] font-semibold" style={{ color: m.color, background: `${m.color}22` }}>{m.label}</span>
                    <p className="mt-1 text-[11px] leading-relaxed text-txt">{m.lecture}</p>
                  </div>
                )
              })()}
              {d.plh && (
                <div className="mb-2 flex flex-col gap-0.5 text-[12px]">
                  <RowT lbl={`PLH ${d.epci ?? ''} — objectif`} val={d.plh.obj_logements_an != null ? `${fmt(d.plh.obj_logements_an)} logts/an` : '—'} />
                  {d.plh.part_sociale_pct != null && <RowT lbl="Part sociale visée" val={`${Number(d.plh.part_sociale_pct).toLocaleString('fr-FR')} %`} />}
                </div>
              )}
              <div className="flex flex-col gap-0.5 text-[12px]">
                <RowT lbl="NPNRU" val={d.anru.length > 0 ? `${d.anru.length} périmètre(s)` : 'aucun'} />
                <RowT lbl="QPV" val={d.qpv.length > 0 ? `${d.qpv.length} quartier(s)` : 'aucun'} />
              </div>
              {d.qpv.length > 0 && <p className="mt-1 text-[10.5px] leading-snug text-txt-dim">{d.qpv.map((x) => x.nom).join(' · ')}</p>}
              <Source nom={`${d.plu_statut.source ?? 'GPU'} · inventaire SRU · PLH · ANCT`} />
            </Acc>

            {/* 6 · LES RISQUES — qu'est-ce qui peut faire échouer ? */}
            <Acc id="risques" title="Les risques" dot={TOKENS.stEcartee}
              cle={d.risques.ppr_pct != null ? `PPR sur ${fmtDec(d.risques.ppr_pct)} %` : (d.risques.parc_national ? 'Parc National' : undefined)}>
              <div className="flex flex-col gap-0.5 text-[12px]">
                <RowT lbl="PPR (risque naturel)" val={d.risques.ppr_pct != null ? `${fmtDec(d.risques.ppr_pct)} % des parcelles` : '—'} />
                <RowT lbl="Mouvement de terrain" val={d.risques.mouvement_terrain_pct != null ? `${fmtDec(d.risques.mouvement_terrain_pct)} %` : '—'} />
                <RowT lbl="Arrêtés CatNat" val={fmt(d.risques.catnat_arretes)} />
                <RowT lbl="Aire d'adhésion Parc National" val={d.risques.parc_national ? 'oui' : 'non'} />
              </div>
              <Source nom={d.risques.source} />
            </Acc>

            {/* 7 · POPULATION & LOGEMENT — pour qui je construis ? */}
            <Acc id="population" title="Population & logement"
              cle={d.population.logements != null ? `${fmt(d.population.logements)} logts${d.population.vacance_pct != null ? ` · ${fmtDec(d.population.vacance_pct)} % vacants` : ''}` : undefined}>
              <div className="mb-2 flex flex-col gap-0.5 text-[12px]">
                {d.population.habitants != null && <RowT lbl="Habitants · ménages" val={`${fmt(d.population.habitants)} · ${fmt(d.population.menages)}`} />}
                {d.population.niveau_vie_moyen_eur != null && <RowT lbl="Niveau de vie moyen" val={`${fmt(d.population.niveau_vie_moyen_eur)} €/an`} />}
                {d.population.logements != null && <RowT lbl="Logements" val={`${fmt(d.population.logements)}${d.population.vacants != null ? ` · ${fmt(d.population.vacants)} vacants (${fmtDec(d.population.vacance_pct)} %)` : ''}`} />}
              </div>
              {d.marche && (
                <div className="flex flex-col gap-2.5">
                  {(() => {
                    const loc = Number(d.marche.locataires_pct); const prop = Number(d.marche.proprietaires_pct)
                    const autres = Math.max(0, Math.round((100 - loc - prop) * 10) / 10)
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
              <Shortcut label="Étude de zone — analyser un point ici" onClick={() => ouvrirOutil(commune, insee, 'etude-zone')} />
              <Source nom={d.population.source} />
            </Acc>

            {/* 8 · CONTINUER AVEC UN OUTIL (ouvert) — la fiche n'est plus un cul-de-sac. */}
            <Acc id="outils" title="Continuer avec un outil" defaultOpen cle="pré-remplis sur la commune">
              <OutilLigne ic="§" nom="PLU" sous={`règlement${d.plu_statut.date_reglement ? ` ${d.plu_statut.date_reglement}` : ''} · recherche verbatim`} onClick={() => ouvrirOutil(commune, insee, 'plu')} />
              <OutilLigne ic="◎" nom="Étude de zone" sous="qui vit, qui travaille, qui concurrence — depuis un point" onClick={() => ouvrirOutil(commune, insee, 'etude-zone')} />
              <OutilLigne ic="⊞" nom="Comparer aux 24 communes" sous={`${commune} mise en regard, ligne surlignée`} onClick={() => ouvrirOutil(commune, insee, 'communes')} />
              {d.outils.permis_en_cours > 0 && <OutilLigne ic="⌂" nom="Permis" sous={`${fmt(d.outils.permis_en_cours)} en cours · ${fmt(d.outils.permis_point_mort)} au point mort`} onClick={() => ouvrirOutil(commune, insee, 'permis')} />}
              {d.outils.densifiables > 0 && <OutilLigne ic="▦" nom="Densifier l'existant" sous={`${fmt(d.outils.densifiables)} parcelles à capacité résiduelle`} onClick={() => ouvrirOutil(commune, insee, 'renouvellement')} />}
              {d.outils.radar_biens > 0 && <OutilLigne ic="◉" nom="Radar" sous={`${fmt(d.outils.radar_biens)} biens en vente dans la commune`} onClick={() => ouvrirOutil(commune, insee, 'radar')} />}
              {d.outils.scan_pm > 0 && <OutilLigne ic="☰" nom="Scan patrimoine" sous={`${fmt(d.outils.scan_pm)} parcelles détenues par une personne morale`} onClick={() => ouvrirOutil(commune, insee, 'patrimoine')} />}
              {d.outils.solaire_piscines > 0 && <OutilLigne ic="☀" nom="Prospection solaire" sous={`${fmt(d.outils.solaire_piscines)} piscines détectées · potentiel PV`} onClick={() => ouvrirOutil(commune, insee, 'prospection-solaire')} />}
              <p className="mt-2 text-[10.5px] leading-snug text-txt-dim">Chaque outil s'ouvre avec {commune} déjà sélectionnée — jamais un formulaire vide à re-remplir.</p>
            </Acc>

            {/* 9 · CONTACTS & DÉMARCHES */}
            {d.mairie && (
              <Acc id="contacts" title="Contacts & démarches" cle="mairie · urbanisme">
                <dl className="space-y-1.5 text-[12px]">
                  <MairieLigne label="Adresse" val={[d.mairie.adresse, [d.mairie.code_postal, d.mairie.commune].filter(Boolean).join(' ')].filter(Boolean).join(', ') || null} />
                  <MairieLigne label="Téléphone" val={d.mairie.telephone} href={d.mairie.telephone ? `tel:${d.mairie.telephone.replace(/\s/g, '')}` : undefined} />
                  <MairieLigne label="E-mail" val={d.mairie.email} href={d.mairie.email ? `mailto:${d.mairie.email}` : undefined} />
                  <MairieLigne label="Site officiel" val={d.mairie.site_officiel} href={d.mairie.site_officiel ?? undefined} />
                  <MairieLigne label="Annuaire" val={d.mairie.url_annuaire ? 'Fiche service-public' : null} href={d.mairie.url_annuaire ?? undefined} />
                </dl>
                <p className="mt-2 text-[10.5px] leading-snug text-txt-dim">{d.mairie.source}{d.mairie.date_import ? ` · relevé le ${fmtDateFr(d.mairie.date_import)}` : ''}</p>
              </Acc>
            )}
          </>
        )}
      </div>
    </aside>
  )
}
