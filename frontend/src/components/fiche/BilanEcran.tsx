// BILAN-1 Lot 3 / BILAN-2 — l'écran du bilan promoteur, calé sur l'Excel de la
// promotrice. Un moteur, deux portes.
// Doctrine : AUCUN calcul ici. Le front tient les saisies, les envoie au moteur
// (/bilan/{idu}/calcul) et affiche le résultat.
// BILAN-2 : CALCUL EN CONTINU — une case vide vaut 0, la marge et les totaux
// s'affichent dès la première saisie ; plus de « aucun chiffre tant qu'un poste
// reste à renseigner ». Un compteur discret « N lignes vides » informe, sans
// jamais bloquer. Les repères LABUSE restent cliquables à droite de la case et
// n'entrent dans le calcul qu'une fois adoptés.
import { useEffect, useMemo, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  getBilanModele, calculerBilan, genererBilan,
  docBilanUrl, docBilanExcelUrl, ApiError,
  type BilanModele, type BilanEntrees, type BilanResultat, type BilanSaisie, type BilanPoste,
} from '../../lib/api'
import { useOuvrirDocument } from '../../lib/ouvrirDocument'
import { empreinte, noterEditeur } from '../../lib/empreinteDoc'
import { Bouton } from '../ui/Bouton'
import { Badge } from '../ui/Badge'
import { Chargement } from '../Loading'

const fmtEur = (n: number | null | undefined) =>
  n == null ? '—' : `${Math.round(n).toLocaleString('fr-FR')} €`
const fmtPct = (n: number | null | undefined, d = 1) =>
  n == null ? '—' : `${(n * 100).toFixed(d).replace('.', ',')} %`
const fmtNum = (n: number | null | undefined) =>
  n == null ? '' : n.toLocaleString('fr-FR', { maximumFractionDigits: 2 })
// Unité « de nature » d'une assiette (m² · lots · €), comme le back (catalogue.assiette_unite).
const assietteUnite = (a: string | null): string | null =>
  a === 'terrain' || a === 'surface_taxable' || a === 'suv' ? 'm²'
    : a === 'lots' ? 'lots'
      : a == null || a === 'forfait' ? null : '€'
const fmtAssiette = (v: number | null | undefined, a: string | null, mode: string): string => {
  if (!v) return mode === 'forfait' ? 'forfait' : '—'
  const u = assietteUnite(a)
  return u == null || u === '€' ? fmtEur(v) : `${Math.round(v).toLocaleString('fr-FR')} ${u}`
}
const parseNum = (s: string): number | null => {
  if (!s.trim()) return null
  const n = parseFloat(s.replace(/\s/g, '').replace(',', '.'))
  return isNaN(n) ? null : n
}
const pctToRate = (s: string): number | null => {
  const v = parseNum(s)
  return v == null ? null : v / 100
}

// G7 — l'état de chaque poste en PASTILLE : Sourcé (vert), Repère (jaune), Saisi, À renseigner
// (à la place des liens « Sans objet »). Une ligne vide porte « À renseigner ».
const ETAT_LABEL: Record<string, string> = {
  source: 'Sourcé', saisi: 'Saisi', repere: 'Repère', ratios: 'Mes ratios', a_renseigner: 'À renseigner',
}
// classes de la pastille par état (couleur portée directement, sans dépendre du Badge).
const ETAT_PASTILLE: Record<string, string> = {
  source: 'border-mint/50 bg-mint/15 text-mint',
  repere: 'border-amber/50 bg-amber/10 text-amber',
  ratios: 'border-line-2 bg-surface text-txt-mut',
  saisi: 'border-line-2 bg-surface text-txt',
  a_renseigner: 'border-line-2 bg-surface text-txt-dim',
}
// Pastille d'état (statut, lecture seule) : couleur + libellé.
function Pastille({ etat }: { etat: string }) {
  const label = ETAT_LABEL[etat] ?? etat
  return <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] ${ETAT_PASTILLE[etat] ?? ETAT_PASTILLE.a_renseigner}`}>{label}</span>
}
// Numérotation des blocs comme le modèle : TOTAL (1) … TOTAL (4).
const NUM_BLOC: Record<string, number> = { T: 1, C: 2, G: 3, V: 4 }

// IMPLANTATION-4 (LOT B) — le programme d'un scénario de l'Étude, pour pré-remplir le Bilan « depuis
// l'Étude » (logements par type + SDP). Seul ce chemin pré-remplit un nombre de logements ; l'ancien
// moteur ne le fait plus (produits à blanc par défaut).
export type BilanDepuisEtude = { ref?: string; logements: number; par_type?: Record<string, number>; sdp_m2: number; shab_m2?: number | null }

export function entreesInitiales(m: BilanModele, etude?: BilanDepuisEtude | null): BilanEntrees {
  const postes: Record<string, BilanSaisie> = {}
  // Les ratios maison pré-remplissent (état « Mes ratios »), modifiables.
  for (const [pid, r] of Object.entries(m.ratios_compte)) {
    postes[pid] = { valeur: r.valeur, etat: 'ratios', tva: r.tva }
  }
  const calendrier: Record<string, number | null> = {}
  for (const c of m.calendrier ?? []) calendrier[c.id] = c.defaut
  // « Depuis l'Étude » : SDP du scénario + logements (par type) comme 1er produit. Sinon tout à blanc.
  const parType = etude?.par_type ? Object.entries(etude.par_type).filter(([, n]) => n > 0).map(([t, n]) => `${t}×${n}`).join(' · ') : ''
  return {
    programme: {
      terrain: m.sourcee.terrain ?? null, surface_taxable: null, loyer: null,
      sdp: etude ? etude.sdp_m2 : null,
    },
    produits: etude
      ? [
          { libelle: parType ? `Logements · ${parType}` : 'Logements', lots: etude.logements, suv: etude.shab_m2 ?? null, prix_ttc_m2_suv: null, tva: null },
          { libelle: 'Produit 2', lots: null, suv: null, prix_ttc_m2_suv: null, tva: null },
        ]
      : [
          { libelle: 'Produit 1', lots: null, suv: null, prix_ttc_m2_suv: null, tva: null },
          { libelle: 'Produit 2', lots: null, suv: null, prix_ttc_m2_suv: null, tva: null },
        ],
    postes,
    mode: 'marge',
    marge_cible: null,
    calendrier,
  }
}

export function BilanEcran({ idu, onClose, onGenerated, depuisEtude }:
  { idu: string; onClose: () => void; onGenerated?: (docId: number) => void; depuisEtude?: BilanDepuisEtude | null }) {
  const { data: modele, isLoading, error } = useQuery({
    queryKey: ['bilan-modele', idu], queryFn: () => getBilanModele(idu), retry: false,
  })
  const [entrees, setEntrees] = useState<BilanEntrees | null>(null)
  const [res, setRes] = useState<BilanResultat | null>(null)
  // `rev` ne bouge QUE sur une mise à jour PROGRAMMATIQUE (repère, « Sans objet »,
  // vider, mémoriser, calendrier) : on re-monte alors les champs (non contrôlés)
  // pour qu'ils reflètent la nouvelle valeur. La saisie clavier ne bump pas → focus.
  const [rev, setRev] = useState(0)
  const bump = () => setRev((r) => r + 1)
  const [erreurGen, setErreurGen] = useState<string | null>(null)
  const [docId, setDocId] = useState<number | null>(null)
  const { ouvrir, enCours } = useOuvrirDocument(setErreurGen)
  const minuterie = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => { if (modele && !entrees) setEntrees(entreesInitiales(modele, depuisEtude)) }, [modele, entrees, depuisEtude])

  // Recalcul (débounce) : toute saisie repart au moteur ; jamais de calcul local.
  useEffect(() => {
    if (!entrees) return
    if (minuterie.current) clearTimeout(minuterie.current)
    minuterie.current = setTimeout(() => {
      calculerBilan(idu, entrees).then(setRes).catch(() => {})
      setDocId(null)  // toute modification invalide le document généré
      // CHASSE-DOCS-FIX-1 (Lot 5.1) — l'empreinte des hypothèses VIVANTES, pour que « Mes documents »
      // marque « Sources modifiées depuis » si l'on édite sans régénérer.
      noterEditeur('bilan', idu, entrees)
    }, 250)
    return () => { if (minuterie.current) clearTimeout(minuterie.current) }
  }, [entrees, idu])

  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [onClose])

  const majPoste = (id: string, patch: Partial<BilanSaisie>) =>
    setEntrees((e) => {
      if (!e) return e
      const prev: BilanSaisie = e.postes[id] ?? { valeur: null, etat: 'a_renseigner' }
      return { ...e, postes: { ...e.postes, [id]: { ...prev, ...patch } } }
    })
  const majPosteProg = (id: string, patch: Partial<BilanSaisie>) => { majPoste(id, patch); bump() }
  const majProduit = (i: number, patch: Partial<BilanEntrees['produits'][number]>) =>
    setEntrees((e) => e && ({ ...e, produits: e.produits.map((p, k) => k === i ? { ...p, ...patch } : p) }))
  const majProgramme = (patch: Partial<BilanEntrees['programme']>) =>
    setEntrees((e) => e && ({ ...e, programme: { ...e.programme, ...patch } }))
  const majCalendrier = (id: string, v: number | null) =>
    setEntrees((e) => e && ({ ...e, calendrier: { ...e.calendrier, [id]: v } }))

  const ligne = useMemo(() => {
    const m: Record<string, BilanResultat['lignes'][number]> = {}
    for (const l of res?.lignes ?? []) m[l.id] = l
    return m
  }, [res])
  const vrais = useMemo(() => {
    const m: Record<string, string> = {}
    for (const v of res?.vraisemblance ?? []) m[v.cible] = v.message
    return m
  }, [res])

  if (isLoading) return <Overlay onClose={onClose}><div className="p-6"><Chargement variant="bloc" label="Chargement du bilan…" /></div></Overlay>
  if (error || !modele || !entrees) return <Overlay onClose={onClose}><div className="p-6 text-amber">Bilan indisponible sur cette parcelle.</div></Overlay>

  const vides = res?.lignes_vides ?? 0

  // Doctrine (Vic) : pas de source publique, pas de repère. Seuls les repères
  // « registre » (source publique) qui se résolvent s'affichent.
  const reperePoste = (p: BilanPoste): { valeur: number; label: string } | null => {
    if (p.repere?.kind !== 'registre' || !p.repere.registre_id) return null
    const r = modele.reperes_publics[p.repere.registre_id]
    return r ? { valeur: r.valeur, label: r.label } : null
  }
  const adopterRepere = (p: BilanPoste) => {
    const r = reperePoste(p)
    if (r) majPosteProg(p.id, { valeur: r.valeur, etat: 'repere' })
  }

  // G7 — enregistre la recette du document (côté serveur) et rend le doc_id. Le message
  // « Connectez-vous à votre compte » NE S'AFFICHE PLUS à l'écran (décision G7) ; une erreur
  // d'enregistrement reste dite, mais jamais ce rappel d'auth.
  const assurerDoc = async (): Promise<number | null> => {
    if (docId != null) return docId
    try {
      const { doc_id } = await genererBilan(idu, entrees, empreinte(entrees))
      setDocId(doc_id)
      onGenerated?.(doc_id)
      return doc_id
    } catch (e) {
      const detail = e instanceof ApiError ? e.detail : undefined
      const auth = e instanceof ApiError && (e.status === 401 || /compte|connect|authenti/i.test(detail ?? ''))
      setErreurGen(auth ? null : (detail || 'Enregistrement impossible.'))
      return null
    }
  }
  const enregistrer = async () => { setErreurGen(null); await assurerDoc() }
  const exporterPdf = async () => {
    setErreurGen(null)
    const id = await assurerDoc()
    if (id != null) await ouvrir(docBilanUrl(idu, id), 'bilan')
  }
  const exporterExcel = async () => {
    setErreurGen(null)
    const id = await assurerDoc()
    if (id != null) await ouvrir(docBilanExcelUrl(idu, id), 'bilan-excel')
  }

  const suvTot = res?.produits_totaux.suv ?? null
  const lotsTot = res?.produits_totaux.lots ?? null
  const faisa = modele.reperes_publics['faisabilite'] ?? null
  const sitadel = modele.reperes_publics['sitadel'] ?? null

  // G7 — repères de l'en-tête et des tuiles.
  const nSource = (res?.lignes ?? []).filter((l) => l.etat === 'source').length
  const caNul = !res?.ca_ttc                               // G3 — pas de CA → exports grisés
  const totalPostes = (modele.blocs ?? []).reduce((n, b) => n + b.postes.length, 0)
  const nSections = (modele.blocs ?? []).length

  return (
    <Overlay onClose={onClose}>
      {/* ── En-tête collant : parcelle, Étude reliée, prix demandé · exports + enregistrer ── */}
      <div className="sticky top-0 z-10 flex h-14 items-center gap-4 border-b border-line bg-surface-2 px-5">
        <Bouton niveau="secondaire" ton="vert" onClick={onClose}>← Docs</Bouton>
        <div className="min-w-0 leading-tight">
          <div className="flex items-center gap-2 text-[15px] font-bold text-txt">
            <span>Bilan</span>
            <span className="text-txt-mut">{idu}</span>
            {modele.sourcee.commune && <span className="text-[12px] font-normal text-txt-mut">· {modele.sourcee.commune}</span>}
          </div>
          <div className="flex flex-wrap items-center gap-1.5 text-[12px] text-txt-mut">
            <span>Programme :</span>
            {depuisEtude
              ? <span className="text-txt">Étude reliée{depuisEtude.ref ? ` · scénario ${depuisEtude.ref}` : ''}</span>
              : <>
                  <span>aucune Étude reliée</span>
                  <button className="text-mint underline" onClick={onClose}>Choisir une Étude de faisabilité</button>
                </>}
            <span className="text-txt-dim">·</span>
            <span>Prix demandé : inconnu</span>
          </div>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <Bouton niveau="secondaire" ton="vert" disabled={caNul || !!enCours} onClick={exporterPdf}>Exporter en PDF</Bouton>
          <Bouton niveau="secondaire" ton="vert" disabled={caNul || !!enCours} onClick={exporterExcel}>Exporter en Excel</Bouton>
          <Bouton niveau="primaire" ton="vert" disabled={!!enCours} onClick={enregistrer}>
            {enCours ? <Chargement variant="inline" accent="courant" label="Enregistrement…" /> : 'Enregistrer'}
          </Bouton>
        </div>
      </div>

      {/* ── Ligne d'état sous l'en-tête ── */}
      <div className="border-b border-line bg-surface-1 px-5 py-2 text-[12px] text-txt-mut">
        {nSource} poste{nSource > 1 ? 's' : ''} pré-rempli{nSource > 1 ? 's' : ''} (sourcés) · {vides} à renseigner, comptés pour 0 ·
        {' '}les exports s'ouvrent dès que le programme et un prix de vente sont saisis.
      </div>

      <div className="grid gap-4 p-5">
        {/* Bandeau zone à cheval : partie non constructible (familles ≠ U/AU) */}
        {modele.sourcee.non_constructible_pct > 0 && (
          <div className="rounded-md border border-amber bg-surface-1 p-3 text-[13px]">
            <b className="text-amber">Parcelle à {fmtNum(modele.sourcee.non_constructible_pct)} % en zone non constructible (N/A)</b>
            <span className="text-txt"> : le programme ne peut porter que sur la partie constructible{modele.sourcee.constructible_m2 != null ? ` (${fmtNum(modele.sourcee.constructible_m2)} m²)` : ''}.</span>
            {modele.sourcee.zonage && <div className="mt-1 text-[12px] text-txt-mut">{modele.sourcee.zonage}</div>}
            {modele.sourcee.constructible_m2 != null && (
              <button className="mt-2 rounded-full border border-dashed border-amber px-2 py-0.5 text-[12px] text-amber hover:bg-amber hover:text-mint-on"
                onClick={() => { majProgramme({ terrain: modele.sourcee.constructible_m2 }); bump() }}>
                Utiliser {fmtNum(modele.sourcee.constructible_m2)} m² comme terrain
              </button>
            )}
          </div>
        )}

        {/* ── Cinq tuiles ── */}
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <Tuile titre="CA TTC programme" valeur={fmtEur(res?.ca_ttc)} sous={caNul ? 'programme à saisir' : `${lotsTot != null ? Math.round(lotsTot) : 0} lots`} />
          <Tuile titre="Dépenses TTC" valeur={fmtEur(res?.depenses_ttc)} sous={`${totalPostes} postes, ${nSections} sections`} />
          <Tuile titre="Résultat net" valeur={fmtEur(res?.resultat_net)} sous={`${fmtPct(res?.marge_pct)} du CA HT`} vert />
          <Tuile titre="Charge foncière max" valeur={fmtEur(res?.prix_max_terrain)} sous="à la marge visée" />
          {/* 5e tuile : Lecture (ma marge / prix max du terrain) */}
          <section className="grid content-start gap-2 rounded-md border border-line bg-surface-1 p-3">
            <div className="text-[11px] uppercase tracking-wide text-txt-dim">Lecture</div>
            <div className="flex flex-wrap gap-1">
              {(['marge', 'prix'] as const).map((mode) => (
                <button key={mode} onClick={() => setEntrees((e) => e && ({ ...e, mode }))}
                  className={`h-7 rounded-full border px-2 text-[12px] ${entrees.mode === mode ? 'border-mint bg-mint text-mint-on' : 'border-line-2 text-txt-mut'}`}>
                  {mode === 'marge' ? 'Ma marge à ce prix' : 'Prix max du terrain'}
                </button>
              ))}
            </div>
            {entrees.mode === 'prix' && (
              <span className="flex items-center gap-1 text-[12px] text-txt-mut">
                <input className="h-7 w-full rounded border border-line-2 bg-surface px-1.5 text-right tabular-nums text-[color:var(--ink)] placeholder:text-txt-mut"
                  defaultValue={entrees.marge_cible ?? ''} placeholder="marge visée"
                  onChange={(ev) => setEntrees((e) => e && ({ ...e, marge_cible: parseNum(ev.target.value) }))} />
                <span className="text-txt-dim">% CA&nbsp;HT</span>
              </span>
            )}
            {entrees.mode === 'marge' ? (
              <div><div className="text-[18px] font-bold leading-tight tabular-nums text-txt">{fmtEur(res?.resultat_net)}</div>
                <div className="text-[12px] text-txt-mut">{fmtPct(res?.marge_pct)} du CA HT</div></div>
            ) : entrees.marge_cible == null ? (
              <div className="text-[13px] font-semibold text-amber">Saisissez la marge visée</div>
            ) : (
              <div><div className="text-[18px] font-bold leading-tight tabular-nums text-txt">{fmtEur(res?.prix_max_terrain)}</div>
                <div className="text-[12px] text-txt-mut">{fmtEur(res?.prix_max_terrain_m2)}/m² de terrain</div></div>
            )}
            {vrais['marge'] && <div className="border-l-2 border-amber pl-2 text-[11px] text-amber">{vrais['marge']}</div>}
            {erreurGen && <p className="rounded border-l-2 border-amber bg-surface p-2 text-[11px] text-amber">{erreurGen}</p>}
          </section>
        </div>

        {/* ── Programme (table des produits) · Calendrier ── */}
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_300px]">
          <Carte titre="Programme" sous="une ligne par produit · libre, PLS, LLI">
            {/* données du programme (sourcées / repère), nécessaires au calcul des taxes et du SUV */}
            <div className="flex flex-wrap items-end gap-4 border-b border-line px-3.5 py-2.5 text-[12px]">
              <TeteChamp label="Terrain" unite="m²" value={entrees.programme.terrain} revKey={rev}
                source={modele.sourcee.terrain != null} onChange={(v) => majProgramme({ terrain: v })} />
              <TeteChamp label="Surface de plancher" unite="m²" value={entrees.programme.sdp} revKey={rev}
                repere={faisa ? { label: faisa.label, valeur: faisa.valeur } : null}
                onChange={(v) => majProgramme({ sdp: v })} onPick={(v) => { majProgramme({ sdp: v }); bump() }} />
              <TeteChamp label="Surface taxable" unite="m²" value={entrees.programme.surface_taxable} revKey={rev}
                onChange={(v) => majProgramme({ surface_taxable: v })} alerte={vrais['stax']} />
              <div className="text-txt-mut">SUV <b className="text-txt">{suvTot != null ? `${fmtNum(suvTot)} m²` : '—'}</b></div>
            </div>
            <table className="w-full text-[13px]">
              <thead><tr className="border-b border-line text-left text-txt-mut">
                <th className="p-2">Produit</th><th className="p-2 text-right">Lots</th><th className="p-2 text-right">SUV m²</th>
                <th className="p-2 text-right">Prix TTC / m²</th><th className="p-2 text-right">TVA</th><th className="p-2 text-right">CA TTC</th>
              </tr></thead>
              <tbody>
                {entrees.produits.map((p, i) => {
                  const dvf = modele.reperes_publics['dvf_neuf']
                  const caTtc = (p.suv ?? 0) * (p.prix_ttc_m2_suv ?? 0)
                  return (
                    <tr key={i} className="border-b border-line align-top">
                      <td className="p-2"><input className="w-32 rounded border border-line-2 bg-surface px-1.5 py-1 text-[color:var(--ink)] placeholder:text-txt-mut" defaultValue={p.libelle} onChange={(e) => majProduit(i, { libelle: e.target.value })} /></td>
                      <td className="p-2"><CellNum revKey={rev} value={p.lots} onChange={(v) => majProduit(i, { lots: v })} /></td>
                      <td className="p-2"><CellNum revKey={rev} value={p.suv} onChange={(v) => majProduit(i, { suv: v })} /></td>
                      <td className="p-2">
                        <CellNum revKey={rev} value={p.prix_ttc_m2_suv} onChange={(v) => majProduit(i, { prix_ttc_m2_suv: v })} />
                        {p.prix_ttc_m2_suv == null && dvf && (
                          <div className="mt-0.5 text-right text-[11px] text-txt-dim">
                            repère {dvf.label}{' '}
                            <button className="text-mint underline" onClick={() => { majProduit(i, { prix_ttc_m2_suv: dvf.valeur }); bump() }} title={dvf.source}>utiliser</button>
                          </div>
                        )}
                      </td>
                      <td className="p-2"><CellNum revKey={rev} value={p.tva == null ? null : p.tva * 100} onChange={(v) => majProduit(i, { tva: v == null ? null : v / 100 })} /></td>
                      <td className="p-2 text-right tabular-nums">{fmtEur(caTtc)}</td>
                    </tr>
                  )
                })}
                <tr className="font-semibold"><td className="p-2">Total</td>
                  <td className="p-2 text-right tabular-nums">{lotsTot != null ? Math.round(lotsTot) : ''}</td>
                  <td className="p-2 text-right tabular-nums">{suvTot != null ? fmtNum(suvTot) : ''}</td>
                  <td /><td /><td className="p-2 text-right tabular-nums">{fmtEur(res?.produits_totaux.ca_ttc)}</td>
                </tr>
              </tbody>
            </table>
            <div className="px-3.5 py-2.5">
              <button className="text-[12px] text-mint underline"
                onClick={() => setEntrees((e) => e && ({ ...e, produits: [...e.produits, { libelle: `Produit ${e.produits.length + 1}`, lots: null, suv: null, prix_ttc_m2_suv: null, tva: null }] }))}>
                + Ajouter un produit
              </button>
            </div>
          </Carte>

          {/* Calendrier compact */}
          <Carte titre="Calendrier" sous="en mois après le compromis">
            <table className="w-full text-[13px]">
              <tbody>
                {(modele.calendrier ?? []).map((c) => (
                  <tr key={c.id} className="border-b border-line last:border-0">
                    <td className="py-1 pl-3 text-txt-mut">{c.libelle}
                      {c.repere === 'sitadel' && sitadel && (
                        <div className="text-[11px] text-txt-dim">repère Sitadel ·{' '}
                          <button className="text-mint underline" title={sitadel.source}
                            onClick={() => { majCalendrier(c.id, (entrees.calendrier['depot_pc'] ?? 0) + Math.round(sitadel.valeur)); bump() }}>
                            {Math.round(sitadel.valeur)} mois
                          </button>
                        </div>
                      )}
                    </td>
                    <td className="py-1 pr-3 text-right">
                      <span className="inline-flex items-center gap-1">
                        <span className="text-[11px] text-txt-dim">J+</span>
                        <input key={rev} className="h-7 w-14 rounded border border-line-2 bg-surface px-1.5 text-right tabular-nums text-[color:var(--ink)] placeholder:text-txt-mut"
                          defaultValue={entrees.calendrier[c.id] ?? ''} placeholder="0"
                          onChange={(ev) => majCalendrier(c.id, parseNum(ev.target.value))} />
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Carte>
        </div>

        {/* ── Le tableau du bilan : 45 postes, 4 sections repliables ── */}
        <section className="overflow-hidden rounded-md border border-line bg-surface-1">
          <div className="flex flex-wrap items-center gap-2.5 border-b border-line px-3.5 py-3">
            <h2 className="text-[15px] font-semibold text-txt">Bilan</h2>
            <small className="font-normal text-txt-mut">{totalPostes} postes · une valeur par défaut seulement si elle est sûre et publique</small>
            <span className="ml-auto flex flex-wrap items-center gap-2 text-[11px]">
              <Pastille etat="source" /><Pastille etat="repere" /><Pastille etat="saisi" /><Pastille etat="a_renseigner" />
            </span>
          </div>
          <table className="w-full table-fixed text-[13px]">
            <colgroup>
              <col className="w-[26%]" /><col className="w-[16%]" /><col className="w-[16%]" />
              <col className="w-[11%]" /><col className="w-[10%]" /><col className="w-[11%]" /><col className="w-[10%]" />
            </colgroup>
            <thead><tr className="border-b border-line text-left text-txt-mut">
              <th className="p-2">Libellé</th><th className="p-2">Assiette</th><th className="p-2 text-right">Taux ou montant</th>
              <th className="p-2 text-right">HT</th><th className="p-2 text-right">TVA</th><th className="p-2 text-right">TTC</th><th className="p-2">État</th>
            </tr></thead>
            <tbody>
              {modele.blocs.map((b) => {
                const tot = res?.blocs.find((x) => x.id === b.id)
                return (
                  <BlocLignes key={b.id} bloc={b} tot={tot} entrees={entrees} ligne={ligne} rev={rev} vrais={vrais}
                    reperePoste={reperePoste} adopterRepere={adopterRepere} majPoste={majPoste} />
                )
              })}
            </tbody>
          </table>
          <Legende />
        </section>

        {/* ── Synthèse en pied ── */}
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <Tuile titre="Dépenses TTC" valeur={fmtEur(res?.depenses_ttc)} />
          <Tuile titre="Chiffre d'affaires TTC" valeur={fmtEur(res?.ca_ttc)} />
          <Tuile titre="TVA résiduelle" valeur={fmtEur(res?.tva_residuelle)} />
          <Tuile titre="Résultat net" valeur={fmtEur(res?.resultat_net)} sous={`${fmtPct(res?.marge_pct)} du CA HT`} vert />
          <Tuile titre="Cash-flow" valeur={fmtEur(res?.cash_flow)} />
        </div>

        <p className="text-center text-[11px] text-txt-dim">Document non contractuel · Données LABUSE au {(modele.sourcee as { donnees_au?: string }).donnees_au ?? '—'}</p>
      </div>
    </Overlay>
  )
}

// ── sous-composants ──────────────────────────────────────────────────────
function Overlay({ children, onClose }: { children: React.ReactNode; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 overflow-auto bg-bg" onClick={onClose}>
      <div className="mx-auto my-6 max-w-[1400px] rounded-lg border border-line bg-surface-1" onClick={(e) => e.stopPropagation()}>
        {children}
      </div>
    </div>
  )
}

function Carte({ titre, sous, children }: { titre: string; sous?: string; children: React.ReactNode }) {
  return (
    <section className="overflow-hidden rounded-md border border-line bg-surface-1">
      <h2 className="flex items-center gap-2.5 border-b border-line px-3.5 py-3 text-[15px] font-semibold text-txt">
        <span dangerouslySetInnerHTML={{ __html: titre }} />{sous && <small className="font-normal text-txt-mut">{sous}</small>}
      </h2>
      {children}
    </section>
  )
}

// G7 — tuile de synthèse (en-tête de l'écran). `vert` colore la valeur (Résultat net).
function Tuile({ titre, valeur, sous, vert }: { titre: string; valeur: string; sous?: string; vert?: boolean }) {
  return (
    <section className="grid content-start gap-1 rounded-md border border-line bg-surface-1 p-3">
      <div className="text-[11px] uppercase tracking-wide text-txt-dim">{titre}</div>
      <div className={`text-[18px] font-bold leading-tight tabular-nums ${vert ? 'text-mint' : 'text-txt'}`}>{valeur}</div>
      {sous && <div className="text-[12px] text-txt-mut">{sous}</div>}
    </section>
  )
}

// G7 — champ compact « donnée du programme » (Terrain / SDP / Surface taxable) : un seul composant,
// unité à l'intérieur, badge Sourcé ou repère cliquable.
function TeteChamp({ label, unite, value, source, repere, revKey, onChange, onPick, alerte }: {
  label: string; unite: string; value: number | null; source?: boolean; revKey?: number
  repere?: { label: string; valeur: number } | null; alerte?: string
  onChange: (v: number | null) => void; onPick?: (v: number | null) => void
}) {
  return (
    <label className="grid gap-0.5">
      <span className="inline-flex items-center gap-1.5 text-txt-mut">{label}{source && <Badge ton="vert">Sourcé</Badge>}</span>
      <span className="inline-flex items-center gap-1">
        <input key={revKey} className="h-7 w-24 rounded border border-line-2 bg-surface px-1.5 pr-7 text-right tabular-nums text-[color:var(--ink)] placeholder:text-txt-mut"
          defaultValue={value == null ? '' : fmtNum(value)} placeholder="0" onChange={(e) => onChange(parseNum(e.target.value))} />
        <span className="-ml-6 text-[11px] text-txt-dim">{unite}</span>
        {value == null && repere && (
          <button className="rounded-full border border-dashed border-line-2 px-1.5 text-[11px] text-txt-mut hover:bg-mint hover:text-mint-on"
            onClick={() => (onPick ?? onChange)(repere.valeur)} title={repere.label}>repère</button>
        )}
      </span>
      {alerte && <span className="text-[11px] text-amber">{alerte}</span>}
    </label>
  )
}

function CellNum({ value, onChange, revKey }: { value: number | null; onChange: (v: number | null) => void; revKey?: number }) {
  return (
    <input key={revKey} className="w-24 rounded border border-line-2 bg-surface px-1.5 py-1 text-right tabular-nums text-[color:var(--ink)] placeholder:text-txt-mut"
      defaultValue={value == null ? '' : fmtNum(value)} placeholder="0" onChange={(e) => onChange(parseNum(e.target.value))} />
  )
}

function BlocLignes({ bloc, tot, entrees, ligne, rev, vrais, reperePoste, adopterRepere, majPoste }: {
  bloc: BilanModele['blocs'][number]
  tot: BilanResultat['blocs'][number] | undefined
  entrees: BilanEntrees
  ligne: Record<string, BilanResultat['lignes'][number]>
  rev: number
  vrais: Record<string, string>
  reperePoste: (p: BilanPoste) => { valeur: number; label: string } | null
  adopterRepere: (p: BilanPoste) => void
  majPoste: (id: string, patch: Partial<BilanSaisie>) => void
}) {
  const n = NUM_BLOC[bloc.id]
  // G7 — première section ouverte, les autres repliées.
  const [ouvert, setOuvert] = useState(n === 1)
  const nSources = bloc.postes.filter((p) => (ligne[p.id]?.etat ?? entrees.postes[p.id]?.etat) === 'source').length
  return (
    <>
      {/* en-tête de section : « n · titre » · « N postes · N sourcés » · sous-total TTC */}
      <tr className="cursor-pointer bg-surface-2 hover:bg-surface-3" onClick={() => setOuvert((o) => !o)}>
        <td className="p-2" colSpan={7}>
          <div className="flex items-center gap-3">
            <span className="font-bold text-txt">{ouvert ? '▾' : '▸'} {n ? `${n} · ` : ''}{bloc.titre}</span>
            <span className="text-[12px] text-txt-mut">{bloc.postes.length} postes{nSources ? ` · ${nSources} sourcés` : ''}</span>
            <span className="ml-auto text-[12px] font-semibold tabular-nums text-txt-mut">TTC {fmtEur(tot?.ttc)}</span>
          </div>
        </td>
      </tr>
      {ouvert && bloc.postes.map((p) => {
        const s = entrees.postes[p.id] ?? { valeur: null, etat: 'a_renseigner' as const }
        const l = ligne[p.id]
        const rep = reperePoste(p)
        const unite = p.mode === 'pct' ? '%' : p.mode === 'unit' ? (p.unite ?? '') : '€'
        const vide = !!l?.manquant  // ligne vide (BILAN-2) : vaut 0, affichée à blanc
        const etat = vide ? 'a_renseigner' : (l?.etat ?? s.etat ?? 'a_renseigner')
        return (
          <tr key={p.id} className="border-b border-line">
            <td className="p-2">{p.libelle}{p.sub && <small className="block text-txt-dim"> {p.sub}</small>}
              {vrais[p.id] && <small className="block text-amber">{vrais[p.id]}</small>}</td>
            <td className="p-2 tabular-nums text-txt-mut">{fmtAssiette(l?.assiette_valeur, p.assiette, p.mode)}
              {p.besoin_assiette && (
                <input key={rev} className="ml-1 w-24 rounded border border-line-2 bg-surface px-1 py-0.5 text-right"
                  defaultValue={s.assiette_valeur ?? ''} placeholder="assiette"
                  onChange={(e) => majPoste(p.id, { assiette_valeur: parseNum(e.target.value) })} />
              )}
            </td>
            <td className="p-2 text-right">
              {/* un seul composant de champ, l'unité À L'INTÉRIEUR (G7) ; le repère reste cliquable dessous */}
              <span className="relative inline-block">
                <input key={rev} className="w-24 rounded border border-line-2 bg-surface px-1.5 py-1 pr-8 text-right tabular-nums"
                  defaultValue={s.valeur == null ? '' : fmtNum(s.valeur)} placeholder="0"
                  onChange={(e) => majPoste(p.id, { valeur: parseNum(e.target.value), etat: 'saisi' })} />
                <span className="pointer-events-none absolute right-1.5 top-1/2 -translate-y-1/2 text-[11px] text-txt-dim">{unite}</span>
              </span>
              {s.valeur == null && rep && (
                <div className="mt-0.5 text-[11px] text-txt-dim">repère{' '}
                  <button className="text-mint underline" onClick={() => adopterRepere(p)} title={rep.label}>utiliser</button>
                </div>
              )}
            </td>
            <td className="p-2 text-right tabular-nums text-txt">{vide ? <span className="text-txt-dim">—</span> : fmtEur(l?.ht)}</td>
            <td className="p-2 text-right tabular-nums">
              {p.tva === 'a_saisir'
                ? <input key={rev} className="w-14 rounded border border-line-2 bg-surface px-1 py-0.5 text-right"
                    defaultValue={s.tva == null ? '' : fmtNum(s.tva * 100)} placeholder="TVA %"
                    onChange={(e) => majPoste(p.id, { tva: pctToRate(e.target.value) })} />
                : (vide ? <span className="text-txt-dim">—</span> : fmtEur(l?.tva))}
            </td>
            <td className="p-2 text-right tabular-nums">{vide ? <span className="text-txt-dim">—</span> : fmtEur(l?.ttc)}</td>
            <td className="p-2"><Pastille etat={etat} /></td>
          </tr>
        )
      })}
      {/* sous-total du bloc : « Total n · Titre » comme le modèle */}
      <tr className="border-b-2 border-line font-semibold text-txt-mut">
        <td className="p-2" colSpan={3}>Total {n ? `${n} · ` : ''}{bloc.titre}</td>
        <td className="p-2 text-right tabular-nums">{fmtEur(tot?.ht)}</td>
        <td className="p-2 text-right tabular-nums">{fmtEur(tot?.tva)}</td>
        <td className="p-2 text-right tabular-nums">{fmtEur(tot?.ttc)}</td><td />
      </tr>
    </>
  )
}

function Legende() {
  // G4 — plus aucune mention de l'Excel côté client ; une case vide vaut 0, comptée pour 0.
  return (
    <div className="flex flex-wrap items-center gap-3.5 px-3.5 py-2.5 text-[12px] text-txt-mut">
      <span>Une case non renseignée est comptée pour 0 — la marge et les totaux s'affichent dès la première saisie.</span>
      <span><Pastille etat="source" /> donnée publique</span>
      <span><Pastille etat="repere" /> proposition, « utiliser » pour l'adopter</span>
      <span><Pastille etat="saisi" /> votre valeur</span>
      <span><Pastille etat="a_renseigner" /> non renseignée</span>
    </div>
  )
}
