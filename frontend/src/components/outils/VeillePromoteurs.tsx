// SECTEUR-1 (S3) + SECTEUR-2 (T2) — outil « Veille promoteurs » : ce que les promoteurs / bailleurs /
// SEM CONSTRUISENT (leurs OPÉRATIONS), pas leur patrimoine. Une opération = groupe de permis contigus,
// même propriétaire moral, même période (règle serveur). Chaque opération : un POINT sur la carte,
// promoteur, commune, logements, dates, état. Par promoteur : une frise par année + lien vers son Scan
// patrimoine (les deux se renvoient, ne se dupliquent pas). Chiffres = comptes SQL, millésime affiché.
import { useEffect, useMemo, useState } from 'react'
import { Siren } from '../shared/Siren'   // RETOURS-12 T2 — SIREN cliquable Pappers
import { useQuery } from '@tanstack/react-query'
import { getMoi, getProgrammes, getPromoteurFrise, getVeillePromoteurs, type OperationPromoteur } from '../../lib/api'
import { CP_COMMUNES } from '../panel/FiltreLabuse'
import { useApp } from '../../store/useApp'
import { Loading } from '../Loading'
import { iduComplet } from '../../lib/format'
import { AddressAutocomplete } from '../AddressAutocomplete'   // RETOURS-3 R4.2 — recherche adresse/IDU commune
import { CollecteProgrammes } from '../admin/Programmes'   // LOT S1 — geste admin discret réutilisant la collecte

const CAT_LABEL: Record<string, string> = { promoteur: 'Promoteur', bailleur: 'Bailleur social', sem: 'SEM' }

function Frise({ siren }: { siren: string }) {
  const q = useQuery({ queryKey: ['promoteur-frise', siren], queryFn: () => getPromoteurFrise(siren) })
  if (q.isLoading) return <Loading label="Frise…" className="text-[10px]" />
  const f = q.data
  if (!f) return null
  const maxLgt = Math.max(1, ...f.frise.map((a) => a.n_logements))
  return (
    <div className="mt-1.5 rounded-md border border-line-2 bg-surface-2 p-2 text-[11px]">
      <p className="text-txt-mut"><b className="text-txt">{f.n_operations}</b> opération{f.n_operations > 1 ? 's' : ''} · <b className="text-txt">{f.n_logements.toLocaleString('fr-FR')}</b> logements construits</p>
      {/* frise par année (opérations, logements) */}
      <div className="mt-1.5 flex flex-col gap-1">
        {f.frise.map((a) => (
          <div key={a.annee} className="flex items-center gap-2">
            <span className="w-9 shrink-0 tabular-nums text-txt-dim">{a.annee}</span>
            <span className="h-2.5 rounded-sm bg-mint/60" style={{ width: `${Math.round(100 * a.n_logements / maxLgt)}%`, minWidth: a.n_logements ? 6 : 0 }} />
            <span className="shrink-0 whitespace-nowrap text-[10px] text-txt-mut">{a.n_operations} op · {a.n_logements} lgt</span>
          </div>
        ))}
      </div>
      {/* PROMO-1 (P4) — les opérations qui portent un NOM de programme rattaché */}
      {f.operations.some((o) => o.programme) && (
        <div className="mt-2">
          <p className="text-[10px] font-medium text-txt-mut">Opérations nommées</p>
          {f.operations.filter((o) => o.programme).slice(0, 8).map((o, i) => (
            <p key={i} className="text-[10.5px] text-txt-dim">{o.annee ?? '—'} · <b className="text-txt">{o.programme!.nom}</b>{o.programme!.url && <> · <a href={o.programme!.url} target="_blank" rel="noreferrer" className="text-mint hover:underline">site →</a></>} <span className="text-txt-dim">({o.libelle})</span></p>
          ))}
        </div>
      )}
      {/* PROMO-1 (P3) — les programmes NON rattachés restent visibles ici : « publiés sur leur site » */}
      {f.programmes_publies.length > 0 && (
        <div className="mt-2 border-t border-line-2 pt-1.5">
          <p className="text-[10px] font-medium text-txt-mut">Publiés sur leur site <span className="text-txt-dim">(non rattachés à une opération)</span></p>
          {f.programmes_publies.slice(0, 12).map((p) => (
            <p key={p.id} className="text-[10.5px] text-txt-dim">
              <b className="text-txt">{p.nom}</b>{p.commune ? ` · ${p.commune}` : ''}{p.annee ? ` · ${p.annee}` : ''}
              {p.url && <> · <a href={p.url} target="_blank" rel="noreferrer" className="text-mint hover:underline">site →</a></>}
            </p>
          ))}
        </div>
      )}
      {/* renvoi vers Scan patrimoine (pas de duplication) */}
      <p className="mt-1.5 text-[10px] text-txt-dim">Patrimoine foncier détenu : <b className="text-txt-mut">{f.scan_patrimoine.n_parcelles.toLocaleString('fr-FR')}</b> parcelles (Scan patrimoine, même SIREN). {f.note}</p>
    </div>
  )
}

// RETOURS-4 S7 — « Ce qu'ils CONSTRUISENT », onglet 2 de la fusion Scan patrimoine. En mode `embedded`, le
// focus SIREN vient de `focusSiren` (partagé par la fusion) et le pont « voir son patrimoine » devient une
// BASCULE D'ONGLET (`onVoirPatrimoine`) au lieu de rouvrir un module.
export function VeillePromoteurs({ embedded, focusSiren, onVoirPatrimoine, onCount }: { embedded?: boolean; focusSiren?: string | null; onVoirPatrimoine?: (siren: string) => void; onCount?: (n: number | null) => void } = {}) {
  const select = useApp((s) => s.select)
  const setModuleMap = useApp((s) => s.setModuleMap)
  const setFlyTo = useApp((s) => s.setFlyTo)
  // RETOURS-3 R4.3 — pont Scan patrimoine → « Voir son patrimoine » (même SIREN, module M02).
  const setM02Prefill = useApp((s) => s.setM02Prefill)
  const setModule = useApp((s) => s.setModule)
  // RETOURS-3 R4.3 — pont Scan patrimoine → Veille : si un SIREN est ciblé, on ouvre sa frise d'emblée.
  const storeFocus = useApp((s) => s.veilleFocusSiren)
  const setVeilleFocusSiren = useApp((s) => s.setVeilleFocusSiren)
  const [commune, setCommune] = useState('')
  const [categorie, setCategorie] = useState('')
  const [depuis, setDepuis] = useState('')
  const [openSiren, setOpenSiren] = useState<string | null>(null)
  // ADMIN-1 (AD3) — MODE STRICT : quand un propriétaire est choisi (Scan patrimoine embarqué + focusSiren),
  // on ne montre QUE ses opérations — aucun filtre commune/catégorie, aucun total de l'île, pas de champ
  // « se positionner ». L'exploration générale reste accessible via « Explorer toutes les opérations → ».
  const [explorer, setExplorer] = useState(false)
  const strict = !!(embedded && focusSiren) && !explorer
  // pont entrant : ouvrir la frise du SIREN ciblé. Embarqué → `focusSiren` (fusion) ; autonome → store (consommé).
  const effFocus = embedded ? (focusSiren ?? null) : storeFocus
  useEffect(() => {
    if (effFocus) { setOpenSiren(effFocus); if (!embedded) setVeilleFocusSiren(null) }
  }, [effFocus, embedded, setVeilleFocusSiren])
  // pont sortant : embarqué → bascule d'onglet ; autonome → ouvre le module Scan patrimoine pré-rempli.
  const voirPatrimoine = (siren: string) => { if (embedded && onVoirPatrimoine) onVoirPatrimoine(siren); else { setM02Prefill(siren); setModule('patrimoine') } }
  const q = useQuery({
    queryKey: strict ? ['veille-promoteurs', 'siren', focusSiren] : ['veille-promoteurs', commune, categorie, depuis],
    queryFn: () => getVeillePromoteurs(strict
      ? { siren: focusSiren!, limit: 200 }
      : { commune: commune || undefined, categorie: categorie || undefined, depuis: depuis || undefined, limit: 200 }),
  })
  const d = q.data

  // LOT S1 — geste admin discret + programmes déjà collectés, uniquement quand un propriétaire est ciblé
  // (Scan patrimoine embarqué). Non-admin : ni le contrôle de collecte, ni rien qui ne soit déjà public.
  const moi = useQuery({ queryKey: ['moi'], queryFn: getMoi, staleTime: 3_600_000 })
  const admin = moi.data?.mode === 'compte' && moi.data.role === 'admin'
  const ownerSiren = embedded ? (focusSiren ?? null) : null
  const [collecteOuverte, setCollecteOuverte] = useState(false)
  const progs = useQuery({
    queryKey: ['programmes-admin', ownerSiren],
    queryFn: () => getProgrammes(ownerSiren!),
    enabled: !!ownerSiren,
  })

  // LOT S1 (compteur d'onglet réel) — le parent (Scan patrimoine) affiche « Ce qu'ils construisent (N) ».
  // N = opérations servies + programmes publiés collectés pour ce propriétaire. Remonté SEULEMENT quand
  // les deux chiffres sont connus (sinon null → le parent n'affiche pas de compteur, aucun chiffre inventé).
  const nOperations = d?.n_total ?? null
  const nProgrammes = progs.data?.n ?? (ownerSiren ? null : 0)
  useEffect(() => {
    if (!onCount) return
    onCount(nOperations == null || nProgrammes == null ? null : nOperations + nProgrammes)
  }, [onCount, nOperations, nProgrammes])

  // ADMIN-1 (AD3) — sous-titre du mode strict : période RÉELLE des permis (plus ancienne année vue) +
  // millésime Sitadel. Aucun chiffre inventé : dérivé des opérations servies.
  const anneeDepuis = d ? Math.min(...(d.operations.map((o) => (o.date_min ? new Date(o.date_min).getFullYear() : NaN)).filter((y) => !Number.isNaN(y)) as number[]), Infinity) : Infinity
  const sel = 'h-8 rounded-md border border-line-2 bg-surface-1 px-2 text-[11.5px] text-txt'

  // SECTEUR-2 (T2) — pousse les OPÉRATIONS localisées sur la carte (kind='operation', ambre / menthe si
  // citée par une annonce Radar). Nettoie au démontage (jamais un pin fantôme d'un autre outil).
  const extra = useMemo(() => ({
    type: 'FeatureCollection' as const,
    features: (d?.operations ?? []).filter((o) => o.lon != null && o.lat != null).map((o) => ({
      type: 'Feature' as const, geometry: { type: 'Point' as const, coordinates: [o.lon, o.lat] },
      // RETOURS-3 R4.1 — le popup carte a besoin des FAITS de l'opération (propriétaire moral, permis,
      // période, programme rattaché + lien). Props plates (strings/nums) pour la couche vectorielle.
      properties: { kind: 'operation', siren: o.siren, idu: o.idus[0] ?? null, radar_cite: o.radar_cite,
                    nb_logements: o.nb_logements, denomination: o.denomination ?? '', categorie: o.categorie ?? '',
                    n_permis: o.n_permis, commune: o.commune ?? '', libelle: o.libelle ?? '',
                    date_min: o.date_min ?? '', date_max: o.date_max ?? '',
                    prog_nom: o.programme?.nom ?? '', prog_url: o.programme?.url ?? '',
                    prog_promoteur: o.programme?.promoteur_nom ?? '' },
    })),
  }), [d])
  useEffect(() => { setModuleMap({ idus: [], extra }); return () => setModuleMap({ idus: [], extra: null }) }, [extra, setModuleMap])

  return (
    <div data-veille-promoteurs className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-1 text-[12.5px]">
      <div>
        <h2 className="font-display text-base font-bold text-txt-hi">{strict ? 'Ce qu\'ils construisent' : 'Veille promoteurs'}</h2>
        {strict
          ? <p className="mt-0.5 text-[11.5px] text-txt-mut">Uniquement les opérations de ce propriétaire (groupes de permis contigus, même période).</p>
          : <p className="mt-0.5 text-[11.5px] text-txt-mut">Ce que les promoteurs, bailleurs sociaux et SEM CONSTRUISENT : leurs opérations (groupes de permis d'un même propriétaire moral, sur des parcelles contiguës et une même période).{d?.millesime ? ` Données Sitadel au ${new Date(d.millesime).toLocaleDateString('fr-FR')}.` : ''}</p>}
      </div>

      {/* LOT S1 — geste ADMIN discret : collecter les programmes du promoteur courant depuis son site.
          Réservé au rôle admin (l'endpoint /admin/programmes/* garde exiger_admin côté serveur). Le SIREN
          est le propriétaire ciblé : il est pré-rempli et verrouillé dans la collecte. Jamais visible pour
          un non-admin. */}
      {admin && ownerSiren && (
        <div data-vp-collecte-admin className="rounded-lg border border-dashed border-line-2 bg-surface-2/40">
          <button data-vp-collecte-toggle onClick={() => setCollecteOuverte((v) => !v)}
            className="flex w-full items-center justify-between px-2.5 py-1.5 text-left text-[10.5px] text-txt-dim transition-colors hover:text-txt-mut">
            <span className="font-mono uppercase tracking-[0.14em]">Admin · collecter ses programmes depuis son site</span>
            <span className="text-txt-off">{collecteOuverte ? '▾' : '▸'}</span>
          </button>
          {collecteOuverte && (
            <div className="border-t border-line-2 p-2.5">
              <CollecteProgrammes sirenFixe={ownerSiren} nomFixe={d?.operations[0]?.denomination ?? undefined}
                onValide={() => progs.refetch()} />
            </div>
          )}
        </div>
      )}

      {/* ADMIN-1 (AD3) — en mode STRICT : pas de « se positionner », pas de filtres, pas de total d'île.
          L'exploration générale est à un clic (« Explorer toutes les opérations → »). */}
      {!strict && (
        <>
          {/* RETOURS-3 R4.2 — barre de recherche adresse/IDU (se positionner sur la carte). */}
          <AddressAutocomplete placeholder="Adresse, IDU… (se positionner sur la carte)"
            className="h-8 w-full rounded-md border border-line-2 bg-surface-1 px-2 text-[11.5px] text-txt placeholder:text-txt-dim focus:border-mint focus:outline-none"
            onSelect={(s2) => { if (s2.lon != null && s2.lat != null) setFlyTo({ center: [s2.lon, s2.lat], zoom: 16 }); if (s2.idu) select(s2.idu) }} />
          <div className="flex flex-wrap gap-2">
            <select data-vp-commune value={commune} onChange={(e) => setCommune(e.target.value)} className={sel}>
              <option value="">Toutes les communes</option>
              {CP_COMMUNES.map(([, n]) => <option key={n} value={n}>{n}</option>)}
            </select>
            <select data-vp-categorie value={categorie} onChange={(e) => setCategorie(e.target.value)} className={sel}>
              <option value="">Toutes catégories</option>
              {(d?.categories ?? []).map((c) => <option key={c.cle} value={c.cle}>{c.label}</option>)}
            </select>
            <input data-vp-depuis type="date" value={depuis} onChange={(e) => setDepuis(e.target.value)} className={sel} title="Déposées depuis…" />
          </div>
        </>
      )}
      {/* mode STRICT actif → lien vers l'exploration générale ; mode exploration (depuis un proprio) → retour. */}
      {embedded && focusSiren && (
        strict
          ? <button data-vp-explorer onClick={() => setExplorer(true)} className="w-fit text-[11.5px] text-mint underline underline-offset-2 hover:text-mint/80">Explorer toutes les opérations de l'île →</button>
          : <button data-vp-retour-proprio onClick={() => setExplorer(false)} className="w-fit text-[11.5px] text-mint underline underline-offset-2 hover:text-mint/80">← revenir à ce propriétaire</button>
      )}

      {q.isLoading && <Loading label="Regroupement des opérations…" className="mx-auto mt-4 text-xs" />}
      {d && (
        <>
          {strict
            ? <p className="text-[12px] text-txt"><b>{d.n_total.toLocaleString('fr-FR')}</b> opération{d.n_total > 1 ? 's' : ''} · <b>{d.n_logements_total.toLocaleString('fr-FR')}</b> logements <span className="text-txt-mut">— construit ou en cours{Number.isFinite(anneeDepuis) ? `, permis depuis ${anneeDepuis}` : ''}{d.millesime ? ` · Sitadel au ${new Date(d.millesime).toLocaleDateString('fr-FR')}` : ''}</span></p>
            : <>
                <p className="text-[11px] text-txt-dim"><b className="text-txt-mut">{d.n_total.toLocaleString('fr-FR')}</b> opérations · <b className="text-txt-mut">{d.n_logements_total.toLocaleString('fr-FR')}</b> logements · {d.n_servi} affichées{d.tronquee ? ` (plafond ${d.plafond})` : ''}</p>
                <p className="text-[10px] leading-snug text-txt-dim">{d.regle.phrase}.</p>
              </>}
          <div className="flex flex-col gap-1.5">
            {d.operations.length === 0 && <p className="text-[11.5px] text-txt-dim">Aucune opération pour ce filtre.</p>}
            {/* RETOURS-4 S5 — carte REMISE À PLAT : chaque valeur sur SA ligne, aucune ne se chevauche.
                Nom (ellipse, title complet) · faits (Type · permis · logements) · Commune · période ·
                IDU sur sa propre ligne monospace ellipse · SIREN discret · actions alignées en bas. */}
            {d.operations.map((o: OperationPromoteur, i) => (
              <div key={i} data-vp-operation className="flex flex-col gap-1 rounded-lg border border-line-2 bg-surface-2 p-2.5">
                <b className="truncate text-[12.5px] text-txt-hi" title={o.denomination ?? undefined}>{o.denomination ?? '(propriétaire non nommé)'}</b>
                <span className="text-[11px] text-txt-mut">{CAT_LABEL[o.categorie] ?? o.categorie} · <b className="text-txt">{o.n_permis}</b> permis · <b className="text-txt">{o.nb_logements}</b> logement{o.nb_logements > 1 ? 's' : ''}</span>
                <span className="text-[10.5px] text-txt-dim">{o.commune}{o.date_min && o.date_max && o.date_min !== o.date_max ? ` · ${new Date(o.date_min).toLocaleDateString('fr-FR')} → ${new Date(o.date_max).toLocaleDateString('fr-FR')}` : (o.date_max ? ` · ${new Date(o.date_max).toLocaleDateString('fr-FR')}` : '')}{o.etat ? ` · ${o.etat}` : ''}</span>
                {/* RETOURS-12 T5 — infobulle « Ouvrir la fiche parcelle » retirée : l'IDU + « → » en lien mint le dit déjà. */}
                {o.idus[0] && (
                  <button data-vp-parcelle onClick={() => select(iduComplet(o.idus[0]))}
                    className="block truncate text-left font-mono text-[10.5px] text-mint hover:underline">{o.idus[0]} →</button>
                )}
                {o.siren && <span className="truncate font-mono text-[10px] text-txt-off">SIREN <Siren value={o.siren} className="font-mono text-txt-off" /></span>}
                {o.radar_cite && <span data-vp-radar-cite className="w-fit rounded bg-mint/12 px-1.5 py-px text-[9.5px] font-medium text-mint">annonce neuve Radar rattachée</span>}

                {/* PROMO-1 (P4) — programme rattaché : un FAIT (nom) + un LIEN, jamais un visuel externe. */}
                {o.programme && (
                  <div data-vp-programme className="mt-0.5 rounded-md border border-mint/25 bg-mint/[0.05] px-2 py-1 text-[11px]">
                    <b className="block truncate text-txt-hi" title={o.programme.nom}>{o.programme.nom}</b>
                    {o.programme.url && <a data-vp-programme-lien href={o.programme.url} target="_blank" rel="noreferrer" className="text-mint hover:underline">voir sur le site de {o.programme.promoteur_nom ?? 'ce promoteur'} →</a>}
                  </div>
                )}

                {/* RETOURS-4 S5.2 — ACTIONS alignées en bas, chacune insécable (jamais de retour au milieu d'un libellé). */}
                {o.siren && (
                  <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-line/60 pt-1.5 text-[10.5px]">
                    <button data-vp-patrimoine onClick={() => voirPatrimoine(o.siren!)} className="whitespace-nowrap text-mint hover:underline" title="Tout son foncier — Scan patrimoine">voir son patrimoine →</button>
                    <button data-vp-frise onClick={() => setOpenSiren((s) => (s === o.siren ? null : o.siren))} className="whitespace-nowrap text-mint hover:underline">{openSiren === o.siren ? 'masquer sa frise' : 'sa frise ▾'}</button>
                  </div>
                )}
                {openSiren === o.siren && o.siren && <Frise siren={o.siren} />}
              </div>
            ))}
          </div>
          <p className="text-[10px] leading-snug text-txt-dim">{d.note}</p>

          {/* LOT S1 — programmes DÉJÀ collectés sur le site du promoteur (référentiel), scopés au SIREN
              courant. Un FAIT (nom · commune · année) + le rattachement à une opération quand connu +
              le lien externe. Aucun visuel du promoteur, comme partout ailleurs. */}
          {ownerSiren && (progs.data?.n ?? 0) > 0 && (
            <div data-vp-programmes-publies className="mt-1 rounded-lg border border-line-2 bg-surface-2 p-2.5">
              <p className="mb-1.5 text-[11px] font-medium text-txt-mut">Programmes publiés sur leur site <span className="text-txt-dim">({progs.data!.n})</span></p>
              <div className="flex flex-col gap-1">
                {progs.data!.programmes.map((p) => (
                  <div key={p.id} data-vp-programme-publie className="text-[10.5px] text-txt-dim">
                    <b className="text-txt">{p.url ? <a href={p.url} target="_blank" rel="noreferrer" className="text-mint hover:underline">{p.nom}</a> : p.nom}</b>
                    {p.commune ? ` · ${p.commune}` : ''}{p.annee ? ` · ${p.annee}` : ''}
                    {p.rattachement_mode
                      ? <span className="ml-1 text-mint">→ rattaché à {p.op_commune ?? '—'} {p.op_annee ?? ''}</span>
                      : <span className="ml-1 text-txt-off">· publié sur leur site</span>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
