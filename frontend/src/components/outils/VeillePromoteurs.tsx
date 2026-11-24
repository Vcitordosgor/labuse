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
import { Squelette } from '../Loading'
import { EmptyState } from '../States'
import { iduComplet, fmtDateSitadel } from '../../lib/format'
import { AddressAutocomplete } from '../AddressAutocomplete'   // RETOURS-3 R4.2 — recherche adresse/IDU commune
import { OwnerParcelles } from '../OwnerParcelles'   // RECHERCHE-2 Lot 2 — propriétaire → ses parcelles
import { Tip } from '../Tip'   // MINI-CORRECTIONS-2 (pt 18) — « i » (définition d'une opération)
import { CollecteProgrammes } from '../admin/Programmes'   // LOT S1 — geste admin discret réutilisant la collecte
import { Bouton } from '../ui/Bouton'
import { Chevron } from '../ui/Chevron'
import { Select } from '../ui/Select'   // U3 (RECETTE-OUTILS-4) — menu déroulant partagé

const CAT_LABEL: Record<string, string> = { promoteur: 'Promoteur', bailleur: 'Bailleur social', sem: 'SEM' }

function Frise({ siren }: { siren: string }) {
  const q = useQuery({ queryKey: ['promoteur-frise', siren], queryFn: () => getPromoteurFrise(siren) })
  if (q.isLoading) return <Squelette lignes={3} />
  const f = q.data
  if (!f) return null
  const maxLgt = Math.max(1, ...f.frise.map((a) => a.n_logements))
  return (
    <div className="mt-1.5 rounded-md border border-line-2 bg-surface-2 p-2 text-[11px]">
      {/* RETOURS-13 R29 — le chiffre DIT ce qu'il compte (parcelles encore possédées) ; l'activité
          de pétitionnaire (permis au nom de la société + filiales identifiées par la gérance INPI)
          complète — jamais un total gonflé sans méthode. */}
      {/* SCAN-FIX-1 (bloquant 2) — DEUX listes SÉPARÉES et NOMMÉES. */}
      <p data-frise-foncier className="text-txt-mut">
        <b className="text-txt-hi">Permis sur son foncier</b> : <b className="text-txt">{f.sur_son_foncier.n_operations}</b> opération{f.sur_son_foncier.n_operations > 1 ? 's' : ''} · <b className="text-txt">{f.sur_son_foncier.n_permis}</b> permis · <b className="text-txt">{f.sur_son_foncier.n_logements.toLocaleString('fr-FR')}</b> logements
        {f.sur_son_foncier.n_logements_dp > 0 && <span className="text-txt-dim"> ({f.sur_son_foncier.n_logements_dp} en déclaration préalable comptés à part)</span>}
        {f.sur_son_foncier.n_logements_annules > 0 && <span className="text-txt-dim"> ({f.sur_son_foncier.n_logements_annules} annulés exclus)</span>}
        {f.sur_son_foncier.part_petitionnaire_inconnu != null && <span className="text-txt-dim"> — pétitionnaire inconnu sur {f.sur_son_foncier.part_petitionnaire_inconnu}% de ces permis</span>}
      </p>
      <p data-frise-deposes className="mt-0.5 text-[10.5px] text-txt-mut">
        <b className="text-txt-hi">Permis qu'elle a déposés</b> (pétitionnaire) : <b className="text-txt">{f.deposes_petitionnaire.n_permis}</b> permis{f.deposes_petitionnaire.n_logements > 0 && <> · <b className="text-txt">{f.deposes_petitionnaire.n_logements.toLocaleString('fr-FR')}</b> logements</>}
        {(f.filiales_identifiees?.length ?? 0) > 0 && <> · +{f.filiales_identifiees.reduce((s, x) => s + x.n_permis, 0)} via {f.filiales_identifiees.length} filiale{f.filiales_identifiees.length > 1 ? 's' : ''} ({f.filiales_identifiees.map((x) => x.nom ?? x.siren).join(', ')})</>}
        {f.deposes_petitionnaire.n_permis === 0 && <span className="text-txt-dim"> — aucun pétitionnaire identifié dans l'open Sitadel</span>}
      </p>
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
  // Chaque opération (groupe promoteur) est un accordéon FERMÉ par défaut : on tient les sirens ouverts
  // dans un Set (vide au départ — aucun auto-déploiement). L'en-tête (nom + résumé + SIREN) reste visible ;
  // la liste des opérations/programmes n'apparaît qu'une fois déplié.
  const [openGroupes, setOpenGroupes] = useState<Set<string>>(new Set())
  const basculerGroupe = (k: string) => setOpenGroupes((prev) => {
    const next = new Set(prev)
    if (next.has(k)) next.delete(k); else next.add(k)
    return next
  })
  // RECHERCHE-2 Lot 2 — propriétaire choisi dans la barre « se positionner » → ses parcelles.
  const [veilleOwner, setVeilleOwner] = useState<{ siren: string; nom: string } | null>(null)
  // ADMIN-1 (AD3) — MODE STRICT : quand un propriétaire est choisi (Scan patrimoine embarqué + focusSiren),
  // on ne montre QUE ses opérations — aucun filtre commune/catégorie, aucun total de l'île, pas de champ
  // « se positionner ». RETOURS-15 B5 — l'exploration générale n'est plus un lien in-onglet (« Explorer
  // toutes les opérations → », retiré) : c'est la seconde PORTE de l'accueil de Scan patrimoine.
  const strict = !!(embedded && focusSiren)
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

  // RETOURS-15 B5 (P11) — le compteur de l'onglet « Construction » = le nombre d'OPÉRATIONS servies,
  // celui-là même que l'onglet AFFICHE (« N opérations »). Avant : opérations + programmes publiés →
  // un « (30) » qui ne correspondait ni aux 21 opérations listées ni aux permis (constat Vic). Un
  // seul chiffre, cohérent avec ce qu'on voit ; les programmes restent listés, sans gonfler le badge.
  const nOperations = d?.n_total ?? null
  useEffect(() => {
    if (!onCount) return
    onCount(nOperations)
  }, [onCount, nOperations])

  // ADMIN-1 (AD3) — sous-titre du mode strict : période RÉELLE des permis (plus ancienne année vue) +
  // millésime Sitadel. Aucun chiffre inventé : dérivé des opérations servies.
  const anneeDepuis = d ? Math.min(...(d.operations.map((o) => (o.date_min ? new Date(o.date_min).getFullYear() : NaN)).filter((y) => !Number.isNaN(y)) as number[]), Infinity) : Infinity
  const sel = 'h-8 rounded-md border border-line-2 bg-surface-1 px-2 text-[11.5px] text-txt'

  // RETOURS-12 O6 — UN PROPRIÉTAIRE MORAL = UNE CARTE. Le listing servait une carte PAR OPÉRATION, si
  // bien qu'un promoteur à plusieurs opérations (ex. CBO TERRITORIA) apparaissait plusieurs fois, chaque
  // carte répétant la même frise. On REGROUPE les opérations par SIREN : une carte par promoteur, ses
  // compteurs (permis, logements) = somme de SES opérations (même périmètre que la frise), ses opérations
  // listées dessous, ses programmes publiés dédoublonnés (une seule fois).
  const promoteurs = useMemo(() => {
    const m = new Map<string, {
      siren: string | null; denomination: string | null; categorie: string
      ops: OperationPromoteur[]; nb_logements: number; n_permis: number; radar: boolean
      programmes: NonNullable<OperationPromoteur['programme']>[]
    }>()
    for (const o of d?.operations ?? []) {
      const key = o.siren ?? `∅${o.denomination ?? ''}`
      const g = m.get(key) ?? { siren: o.siren, denomination: o.denomination, categorie: o.categorie,
        ops: [], nb_logements: 0, n_permis: 0, radar: false, programmes: [] }
      g.ops.push(o); g.nb_logements += o.nb_logements; g.n_permis += o.n_permis
      if (o.radar_cite) g.radar = true
      if (o.programme && !g.programmes.some((p) => p.nom === o.programme!.nom && p.url === o.programme!.url)) g.programmes.push(o.programme)
      m.set(key, g)
    }
    // ordre : plus d'opérations d'abord (les gros promoteurs en tête)
    return [...m.values()].sort((a, b) => b.ops.length - a.ops.length || b.nb_logements - a.nb_logements)
  }, [d])

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

  // MINI-CORRECTIONS-2 (pt 20) — onglet « Construction » (mode strict) À ZÉRO opération : on n'affiche
  // QUE « Aucune opération pour ce filtre. » (+ le geste admin). Pas de titre, pas de texte d'explication,
  // pas de compteur, pas de note de bas. `strictVide` gate ces éléments quand le propriétaire ciblé n'a
  // rien construit.
  const strictVide = strict && !!d && d.n_total === 0
  // SCAN-FIX-2 (A1) + SCAN-FIX-1 — notes du total : logements de DP et d'annulés comptés À PART, ops ambiguës.
  const notesLgt = d ? [
    d.n_logements_dp > 0 ? `${d.n_logements_dp.toLocaleString('fr-FR')} logement${d.n_logements_dp > 1 ? 's' : ''} de déclaration préalable comptés à part` : null,
    d.n_logements_annules > 0 ? `${d.n_logements_annules.toLocaleString('fr-FR')} logement${d.n_logements_annules > 1 ? 's' : ''} de permis annulés exclus` : null,
    d.n_operations_ambigues > 0 ? `${d.n_operations_ambigues} opération${d.n_operations_ambigues > 1 ? 's' : ''} à propriétaire ambigu` : null,
  ].filter(Boolean).join(' · ') : ''

  return (
    <div data-veille-promoteurs className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-1 text-[12.5px]">
      {/* MINI-CORRECTIONS-2 (pt 20) — titre + explication masqués quand l'onglet Construction est vide. */}
      {!strictVide && (
        <div>
          {/* SCAN-FIX-1 (bloquant 2) — plus de titre « ce qu'ils construisent » sur une attribution PAR LE
              FONCIER : le titre dit honnêtement que ce sont les permis SUR SON FONCIER (propriétaire du
              terrain), pas forcément déposés par elle. La frise sépare « déposés » vs « sur son foncier ». */}
          <h2 className="font-display text-base font-bold text-txt-hi">{strict ? 'Permis sur son foncier' : 'Veille promoteurs'}</h2>
          {/* RETOURS-23 (pt 15) — en mode général, la phrase générale est RETIRÉE (Vic). Sous-titre strict reste. */}
          {strict && <p className="mt-0.5 text-[11.5px] text-txt-mut">Opérations sur les parcelles dont ce propriétaire est le PROPRIÉTAIRE FONCIER (groupes de permis proches, même période) — pas nécessairement déposées par lui. Voir la frise pour « permis qu'il a déposés ».</p>}
        </div>
      )}

      {/* LOT S1 — geste ADMIN discret : collecter les programmes du promoteur courant depuis son site.
          Réservé au rôle admin (l'endpoint /admin/programmes/* garde exiger_admin côté serveur). Le SIREN
          est le propriétaire ciblé : il est pré-rempli et verrouillé dans la collecte. Jamais visible pour
          un non-admin. */}
      {admin && ownerSiren && (
        <div data-vp-collecte-admin className="rounded-lg border border-dashed border-line-2 bg-surface-2/40">
          <button data-vp-collecte-toggle onClick={() => setCollecteOuverte((v) => !v)}
            className="flex w-full items-center justify-between px-2.5 py-1.5 text-left text-[10.5px] text-txt-dim transition-colors hover:text-txt-mut">
            <span className="font-mono uppercase tracking-[0.14em]">Admin · collecter ses programmes depuis son site</span>
            <Chevron open={collecteOuverte} />
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
          {/* RETOURS-3 R4.2 — barre de recherche adresse/IDU (se positionner sur la carte).
              RECHERCHE-2 Lot 2 — + propriétaire/SIREN : un pick propriétaire déroule ses parcelles ;
              en choisir une recentre la carte et la sélectionne. */}
          <AddressAutocomplete placeholder="Propriétaire, adresse ou IDU"
            className="h-8 w-full rounded-md border border-line-2 bg-surface-1 px-2 text-[11.5px] text-txt placeholder:text-txt-dim focus:outline-none"
            grammaires={['adresse', 'cadastre', 'proprietaire', 'siren']}
            onPick={(it) => { if ((it.type === 'proprietaire' || it.type === 'siren') && it.siren) setVeilleOwner({ siren: it.siren, nom: it.label }) }}
            onSelect={(s2) => { if (s2.lon != null && s2.lat != null) setFlyTo({ center: [s2.lon, s2.lat], zoom: 16 }); if (s2.idu) select(s2.idu) }} />
          {veilleOwner && (
            <OwnerParcelles siren={veilleOwner.siren} nom={veilleOwner.nom}
              onPick={(idu, centre) => { if (centre) setFlyTo({ center: [centre.lon, centre.lat], zoom: 16 }); select(idu); setVeilleOwner(null) }}
              onChanger={() => setVeilleOwner(null)} />
          )}
          {/* MINI-CORRECTIONS-2 (pt 18, 2ᵉ passe) — Commune + Catégorie sur UNE ligne, MÊME largeur ; un
              petit LIBELLÉ au-dessus de chacune (« Commune », « Catégorie ») et « Toutes » comme valeur
              par défaut → plus aucun texte coupé (avant : « Toutes les comr » / « Toutes catégori »). */}
          <div className="grid grid-cols-2 gap-2">
            <label className="flex min-w-0 flex-col gap-1 text-[10.5px] text-txt-mut">
              Commune
              <Select data-vp-commune wrapClassName="w-full" value={commune} onChange={(e) => setCommune(e.target.value)} className={`${sel} w-full`}>
                <option value="">Toutes</option>
                {CP_COMMUNES.map(([, n]) => <option key={n} value={n}>{n}</option>)}
              </Select>
            </label>
            <label className="flex min-w-0 flex-col gap-1 text-[10.5px] text-txt-mut">
              Catégorie
              <Select data-vp-categorie wrapClassName="w-full" value={categorie} onChange={(e) => setCategorie(e.target.value)} className={`${sel} w-full`}>
                <option value="">Toutes</option>
                {(d?.categories ?? []).map((c) => <option key={c.cle} value={c.cle}>{c.label}</option>)}
              </Select>
            </label>
          </div>
          <label className="flex flex-col gap-1 text-[10.5px] text-txt-mut">
            Opérations déposées depuis
            <input data-vp-depuis type="date" value={depuis} onChange={(e) => setDepuis(e.target.value)} className={`${sel} w-full`} />
          </label>
        </>
      )}
      {q.isLoading && <Squelette lignes={6} className="mt-4" />}
      {d && (
        <>
          {strict
            ? (strictVide ? null : <>
                <p className="text-[12px] text-txt"><b>{d.n_total.toLocaleString('fr-FR')}</b> opération{d.n_total > 1 ? 's' : ''} · <b>{d.n_logements_total.toLocaleString('fr-FR')}</b> logements <span className="text-txt-mut">— construit ou en cours{Number.isFinite(anneeDepuis) ? `, permis depuis ${anneeDepuis}` : ''}{d.millesime ? ` · Sitadel au ${fmtDateSitadel(d.millesime)}` : ''}</span></p>
                {/* SCAN-FIX-2 (A1)/SCAN-FIX-1 (bloquants 3-4) — DP et annulés comptés à part ; ambiguës signalées ; plafond annoncé AUSSI en mode propriétaire. */}
                {notesLgt && <p className="text-[10px] leading-snug text-txt-dim">{notesLgt}</p>}
                {d.tronquee && <p className="text-[10px] leading-snug text-txt-dim">Les {d.plafond} premières sont affichées : affinez la recherche.</p>}
              </>)
            : <>
                {/* MINI-CORRECTIONS-2 (pt 18) — compteur « N opérations · N logements » sur UNE ligne + « i »
                    (définition réelle, étendue). SCAN-FIX-1 — annulés exclus + dits ; ambiguës signalées. */}
                <p className="flex items-center gap-1.5 text-[11px] text-txt-dim">
                  <span><b className="text-txt-mut">{d.n_total.toLocaleString('fr-FR')}</b> opérations · <b className="text-txt-mut">{d.n_logements_total.toLocaleString('fr-FR')}</b> logements</span>
                  <Tip garder tip={`${d.regle.phrase}.`}>
                    <span className="cursor-help rounded-full border border-line-2 px-1 text-[8px] leading-none text-txt-dim">i</span>
                  </Tip>
                </p>
                {notesLgt && <p className="text-[10px] leading-snug text-txt-dim">{notesLgt}</p>}
                {d.tronquee && <p className="text-[10px] leading-snug text-txt-dim">Les {d.plafond} premières sont affichées : affinez la recherche.</p>}
              </>}
          <div className="flex flex-col gap-1.5">
            {/* MINI-CORRECTIONS-2 (pt 20, 2ᵉ passe) — onglet Construction vide : JUSTE le texte, « et basta »
                (pas d'oiseau/illustration de l'EmptyState). L'exploration générale garde l'EmptyState. */}
            {promoteurs.length === 0 && (strict
              ? <p data-vp-vide className="px-6 py-10 text-center text-sm font-medium text-txt">Aucune opération pour ce filtre.</p>
              : <EmptyState title="Aucune opération pour ce filtre." />)}
            {/* RETOURS-12 O6 — UNE CARTE PAR PROMOTEUR (regroupée par SIREN). En-tête : nom + total permis
                + total logements (= somme de ses opérations, même périmètre que la frise). Ses opérations
                sont listées dessous ; ses programmes publiés une seule fois ; sa frise une seule fois. */}
            {promoteurs.map((g, i) => {
              const gkey = g.siren ?? `∅${i}`
              const ouvert = openGroupes.has(gkey)
              // SCAN-FIX-1 (pt 7) — compteurs de la carte = TOTAUX de la société (par_promoteur, calculé sur
              // TOUTES ses opérations), jamais la somme des seules opérations servies dans la page (≤ 200).
              const carte = (d.par_promoteur ?? []).find((c) => (c.siren ?? '') === (g.siren ?? ''))
              const nOps = carte?.n_operations ?? g.ops.length
              const nPermis = carte?.n_permis ?? g.n_permis
              const nLgt = carte?.nb_logements ?? g.nb_logements
              const nAnnules = carte?.nb_logements_annules ?? 0
              const nDp = carte?.nb_logements_dp ?? 0
              return (
              <div key={gkey} data-vp-promoteur data-vp-siren={g.siren ?? ''} className="flex flex-col gap-1 rounded-lg border border-line-2 bg-surface-2 p-2.5">
                {/* EN-TÊTE accordéon (toujours visible) : nom + résumé + SIREN + chevron. Fermé par défaut ;
                    un clic déplie/replie le détail. Le chevron fermé pointe à droite (charte Chevron). */}
                <button data-vp-promoteur-toggle onClick={() => basculerGroupe(gkey)}
                  aria-expanded={ouvert} className="flex w-full items-start justify-between gap-2 text-left">
                  <span className="flex min-w-0 flex-col gap-1">
                    <b className="truncate text-[12.5px] text-txt-hi">{g.denomination ?? '(propriétaire non nommé)'}</b>
                    <span className="text-[11px] text-txt-mut">{/* SCAN-FIX-1 (pt 7) — libellé justifié (SIRENE/DGFiP), « Promoteur » jamais par défaut sur le groupe 0. */}{carte?.categorie_label ?? CAT_LABEL[g.categorie] ?? g.categorie} · <b className="text-txt">{nOps}</b> opération{nOps > 1 ? 's' : ''} · <b className="text-txt">{nPermis}</b> permis · <b className="text-txt">{nLgt}</b> logement{nLgt > 1 ? 's' : ''}{nDp > 0 ? <span className="text-txt-dim"> · {nDp} en déclaration préalable</span> : null}{nAnnules > 0 ? <span className="text-txt-dim"> · {nAnnules} annulé{nAnnules > 1 ? 's' : ''} exclu{nAnnules > 1 ? 's' : ''}</span> : null}{carte?.ambigu ? <span className="text-st-creuser"> · propriétaire ambigu</span> : null}</span>
                    {g.siren && <span className="truncate font-mono text-[10px] text-txt-off">SIREN <Siren value={g.siren} className="font-mono text-txt-off" /></span>}
                    {g.radar && <span data-vp-radar-cite className="w-fit rounded bg-mint/12 px-1.5 py-px text-[9.5px] font-medium text-mint">annonce neuve Radar rattachée</span>}
                  </span>
                  <Chevron open={ouvert} className="mt-0.5" />
                </button>

                {ouvert && (
                  <>
                    {/* ses OPÉRATIONS (une sous-ligne chacune) — le détail sans répéter le nom du promoteur. */}
                    <div className="mt-0.5 flex flex-col gap-1 border-t border-line/60 pt-1">
                      {g.ops.map((o: OperationPromoteur, k) => (
                        <div key={k} data-vp-operation className="flex flex-col gap-0.5 rounded-md bg-surface-3 px-2 py-1">
                          {/* OUTILS-FIX-4 A3 — date Sit@del : année seule si seule l'année est connue (fmtDateSitadel),
                              plus jamais un « 01/01/2024 » qui ment sur la précision. A4 — le nombre nu final était
                              le CODE d'état Sit@del brut (etat_dau) : on affiche son LIBELLÉ servi (autorisé/achevé). */}
                          <span className="text-[10.5px] text-txt">{o.commune} · <b className="text-txt-hi">{o.nb_logements}</b> lgt · {o.n_permis} permis{o.date_max ? ` · ${fmtDateSitadel(o.date_max)}` : ''}{o.etat_libelle ? ` · ${o.etat_libelle}` : ''}</span>
                          {o.idus[0] && (
                            <button data-vp-parcelle onClick={() => select(iduComplet(o.idus[0]))}
                              className="block truncate text-left font-mono text-[10px] text-mint hover:underline">{o.idus[0]} →</button>
                          )}
                        </div>
                      ))}
                    </div>

                    {/* PROMO-1 (P4) — programmes rattachés (dédoublonnés) : FAIT (nom) + LIEN, jamais un visuel. */}
                    {g.programmes.map((p, k) => (
                      <div key={k} data-vp-programme className="mt-0.5 rounded-md border border-mint/25 bg-mint/[0.05] px-2 py-1 text-[11px]">
                        <b className="block truncate text-txt-hi">{p.nom}</b>
                        {p.url && <a data-vp-programme-lien href={p.url} target="_blank" rel="noreferrer" className="text-mint hover:underline">voir sur le site de {p.promoteur_nom ?? 'ce promoteur'} →</a>}
                      </div>
                    ))}

                    {/* RECETTE-OUTILS-2 (R20) — deux colonnes ÉGALES (grille 1fr 1fr) côte à côte.
                        RETOURS-23 (pt 16) — les libellés tiennent DANS leur cadre : plus de `whitespace-nowrap`
                        (qui débordait à largeur minimale, cartes imbriquées) → le texte passe À LA LIGNE,
                        centré, sans jamais sortir du bouton. */}
                    {g.siren && (
                      <div className="mt-1 grid grid-cols-2 gap-2 border-t border-line/60 pt-1.5">
                        <Bouton niveau="secondaire" ton="vert" data-vp-patrimoine onClick={() => voirPatrimoine(g.siren!)} className="w-full min-w-0 justify-center px-1 text-center text-[11px] leading-snug">Voir son patrimoine →</Bouton>
                        <Bouton niveau="secondaire" ton="vert" data-vp-frise onClick={() => setOpenSiren((s) => (s === g.siren ? null : g.siren))} className="w-full min-w-0 justify-center gap-1 px-1 text-center text-[11px] leading-snug">{openSiren === g.siren ? 'Masquer sa frise' : 'Sa frise'} <Chevron open={openSiren === g.siren} /></Bouton>
                      </div>
                    )}
                    {openSiren === g.siren && g.siren && <Frise siren={g.siren} />}
                  </>
                )}
              </div>
              )
            })}
          </div>
          {/* MINI-CORRECTIONS-2 (pt 20) — note de bas masquée quand l'onglet Construction est vide. */}
          {!strictVide && <p className="text-[10px] leading-snug text-txt-dim">{d.note}</p>}

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
