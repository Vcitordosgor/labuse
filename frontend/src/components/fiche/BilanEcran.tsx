// BILAN-1 Lot 3 — l'écran du bilan promoteur (maquette v2). Un moteur, deux portes.
// Doctrine : AUCUN calcul ici. Le front tient les saisies, les envoie au moteur
// (/bilan/{idu}/calcul) et affiche le résultat. On ne pré-remplit que le Sourcé ;
// les repères sont cliquables et n'entrent dans le calcul qu'une fois adoptés.
import { useEffect, useMemo, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  getBilanModele, calculerBilan, genererBilan, putBilanRatio,
  docBilanUrl, docBilanExcelUrl,
  type BilanModele, type BilanEntrees, type BilanResultat, type BilanSaisie, type BilanPoste,
} from '../../lib/api'
import { useOuvrirDocument } from '../../lib/ouvrirDocument'
import { Bouton } from '../ui/Bouton'
import { Badge } from '../ui/Badge'

const fmtEur = (n: number | null | undefined) =>
  n == null ? '—' : `${Math.round(n).toLocaleString('fr-FR')} €`
const fmtPct = (n: number | null | undefined, d = 1) =>
  n == null ? '—' : `${(n * 100).toFixed(d).replace('.', ',')} %`
const fmtNum = (n: number | null | undefined) =>
  n == null ? '' : n.toLocaleString('fr-FR', { maximumFractionDigits: 2 })
const parseNum = (s: string): number | null => {
  if (!s.trim()) return null
  const n = parseFloat(s.replace(/\s/g, '').replace(',', '.'))
  return isNaN(n) ? null : n
}
const pctToRate = (s: string): number | null => {
  const v = parseNum(s)
  return v == null ? null : v / 100
}

const ETAT_LABEL: Record<string, string> = {
  source: 'Sourcé', saisi: 'Saisi', repere: 'Repère pris',
  ratios: 'Mes ratios', sans_objet: 'Sans objet', a_renseigner: 'À renseigner',
}
const ETAT_TON: Record<string, 'vert' | 'neutre' | 'ambre'> = {
  source: 'vert', saisi: 'neutre', repere: 'neutre', ratios: 'neutre',
  sans_objet: 'neutre', a_renseigner: 'ambre',
}

function entreesInitiales(m: BilanModele): BilanEntrees {
  const postes: Record<string, BilanSaisie> = {}
  // Les ratios maison pré-remplissent (état « Mes ratios »), modifiables.
  for (const [pid, r] of Object.entries(m.ratios_compte)) {
    postes[pid] = { valeur: r.valeur, etat: 'ratios', tva: r.tva }
  }
  return {
    programme: { terrain: m.sourcee.terrain ?? null, surface_taxable: null, loyer: null },
    produits: [
      { libelle: 'Produit 1', lots: null, suv: null, prix_ttc_m2_suv: null, tva: null },
      { libelle: 'Produit 2', lots: null, suv: null, prix_ttc_m2_suv: null, tva: null },
    ],
    postes,
    mode: 'marge',
    marge_cible: null,
  }
}

export function BilanEcran({ idu, onClose, onGenerated }:
  { idu: string; onClose: () => void; onGenerated?: (docId: number) => void }) {
  const { data: modele, isLoading, error } = useQuery({
    queryKey: ['bilan-modele', idu], queryFn: () => getBilanModele(idu), retry: false,
  })
  const [entrees, setEntrees] = useState<BilanEntrees | null>(null)
  const [res, setRes] = useState<BilanResultat | null>(null)
  const [erreurGen, setErreurGen] = useState<string | null>(null)
  const [docId, setDocId] = useState<number | null>(null)
  const { ouvrir, enCours } = useOuvrirDocument(setErreurGen)
  const minuterie = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => { if (modele && !entrees) setEntrees(entreesInitiales(modele)) }, [modele, entrees])

  // Recalcul (débounce) : toute saisie repart au moteur ; jamais de calcul local.
  useEffect(() => {
    if (!entrees) return
    if (minuterie.current) clearTimeout(minuterie.current)
    minuterie.current = setTimeout(() => {
      calculerBilan(idu, entrees).then(setRes).catch(() => {})
      setDocId(null)  // toute modification invalide le document généré
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
  const majProduit = (i: number, patch: Partial<BilanEntrees['produits'][number]>) =>
    setEntrees((e) => e && ({ ...e, produits: e.produits.map((p, k) => k === i ? { ...p, ...patch } : p) }))
  const majProgramme = (patch: Partial<BilanEntrees['programme']>) =>
    setEntrees((e) => e && ({ ...e, programme: { ...e.programme, ...patch } }))

  const ligne = useMemo(() => {
    const m: Record<string, BilanResultat['lignes'][number]> = {}
    for (const l of res?.lignes ?? []) m[l.id] = l
    return m
  }, [res])

  if (isLoading) return <Overlay onClose={onClose}><div className="p-6 text-txt-mut">Chargement du bilan…</div></Overlay>
  if (error || !modele || !entrees) return <Overlay onClose={onClose}><div className="p-6 text-amber">Bilan indisponible sur cette parcelle.</div></Overlay>

  const complet = !!res?.complet
  const prog = res ? `${res.postes_renseignes} / ${res.total_postes} postes` : ''

  const adopterRepere = (p: BilanPoste) => {
    if (!p.repere) return
    if (p.repere.kind === 'ratio_place' && p.repere.valeur != null) {
      majPoste(p.id, { valeur: p.repere.valeur, etat: 'repere' })
    } else if (p.repere.kind === 'registre' && p.repere.registre_id) {
      const r = modele.reperes_publics[p.repere.registre_id]
      if (r) majPoste(p.id, { valeur: r.valeur, etat: 'repere' })
    }
  }
  const reperePoste = (p: BilanPoste): { valeur: number; label: string } | null => {
    if (!p.repere) return null
    if (p.repere.kind === 'ratio_place' && p.repere.valeur != null)
      return { valeur: p.repere.valeur, label: `repère ${fmtNum(p.repere.valeur)} ${p.mode === 'pct' ? '%' : (p.unite ?? '')}`.trim() }
    if (p.repere.kind === 'registre' && p.repere.registre_id) {
      const r = modele.reperes_publics[p.repere.registre_id]
      return r ? { valeur: r.valeur, label: r.label } : null  // pas de source → pas de pastille
    }
    return null
  }

  const generer = async () => {
    setErreurGen(null)
    try {
      const { doc_id } = await genererBilan(idu, entrees)
      setDocId(doc_id)
      onGenerated?.(doc_id)
      await ouvrir(docBilanUrl(idu, doc_id), 'bilan')
    } catch (e) {
      const d = (e as { detail?: { message?: string } })?.detail
      setErreurGen(d?.message ?? 'Génération impossible — un poste reste à renseigner.')
    }
  }

  return (
    <Overlay onClose={onClose}>
      <div className="flex h-14 items-center gap-3 border-b border-line bg-surface-2 px-5">
        <Bouton niveau="secondaire" ton="vert" onClick={onClose}>← Fermer</Bouton>
        <div className="leading-tight">
          <div className="text-[16px] font-bold text-txt">Bilan · {idu}</div>
          {modele.sourcee.commune && <div className="text-[12px] text-txt-mut">{modele.sourcee.commune}</div>}
        </div>
        <div className="ml-auto flex gap-2">
          {complet && docId != null && (
            <a href={docBilanExcelUrl(idu, docId)} className="inline-flex h-8 items-center rounded-md border border-mint px-3 text-[13px] font-semibold text-mint hover:bg-mint hover:text-mint-on">Excel</a>
          )}
          <Bouton niveau="primaire" ton="vert" disabled={!complet || !!enCours} onClick={generer}>
            {enCours ? 'Génération…' : 'Générer le bilan'}
          </Bouton>
        </div>
      </div>

      <div className="grid grid-cols-[320px_minmax(0,1fr)] items-start gap-5 p-5">
        {/* colonne latérale */}
        <aside className="sticky top-5 grid gap-3.5">
          <section className="rounded-md border border-line bg-surface-1 p-3.5">
            <h3 className="mb-2.5 text-[13px] font-semibold text-txt-mut">Que voulez-vous savoir ?</h3>
            <div className="flex flex-wrap gap-1.5">
              {(['marge', 'prix'] as const).map((mode) => (
                <button key={mode} onClick={() => setEntrees((e) => e && ({ ...e, mode }))}
                  className={`h-8 rounded-full border px-3 text-[13px] ${entrees.mode === mode ? 'border-mint bg-mint text-mint-on' : 'border-line-2 text-txt-mut'}`}>
                  {mode === 'marge' ? 'Ma marge à ce prix' : 'Le prix max du terrain'}
                </button>
              ))}
            </div>
            {entrees.mode === 'prix' && (
              <label className="mt-2.5 grid gap-1 text-[12px] text-txt-mut">Marge visée
                <span className="flex items-center gap-2">
                  <input className={`h-8 w-full rounded-md border bg-surface px-2.5 text-right tabular-nums ${entrees.marge_cible == null ? 'border-amber' : 'border-line-2'}`}
                    defaultValue={entrees.marge_cible ?? ''} placeholder="à saisir"
                    onChange={(ev) => setEntrees((e) => e && ({ ...e, marge_cible: parseNum(ev.target.value) }))} />
                  <span className="min-w-[44px] text-[12px] text-txt-dim">% CA HT</span>
                </span>
              </label>
            )}
          </section>

          <section className="rounded-md border border-line bg-surface-1 p-3.5">
            <div className="text-[12px] text-txt-mut">{entrees.mode === 'marge' ? 'Résultat net' : 'Prix maximum du terrain'}</div>
            {!complet ? (
              <>
                <div className="text-[15px] font-semibold text-amber">{res ? `${res.manquants.length} poste${res.manquants.length > 1 ? 's' : ''} à renseigner` : '…'}</div>
                <div className="mt-1.5 text-[13px] text-txt-mut">Aucun chiffre n'est calculé sur un bilan incomplet.</div>
              </>
            ) : entrees.mode === 'marge' ? (
              <>
                <div className="text-[26px] font-bold leading-none tabular-nums text-txt">{fmtEur(res!.resultat_net)}</div>
                <div className="mt-1.5 text-[13px] text-txt-mut">{fmtPct(res!.marge_pct)} du CA HT</div>
              </>
            ) : entrees.marge_cible == null ? (
              <div className="text-[15px] font-semibold text-amber">Saisissez la marge visée</div>
            ) : (
              <>
                <div className="text-[26px] font-bold leading-none tabular-nums text-txt">{fmtEur(res!.prix_max_terrain)}</div>
                <div className="mt-1.5 text-[13px] text-txt-mut">{fmtEur(res!.prix_max_terrain_m2)}/m² de terrain</div>
              </>
            )}
            <div className="mt-2.5 h-1.5 overflow-hidden rounded-full bg-line">
              <div className="h-full bg-mint" style={{ width: res ? `${Math.round((res.postes_renseignes / Math.max(1, res.total_postes)) * 100)}%` : '0%' }} />
            </div>
            <div className="mt-1 text-[12px] text-txt-mut">{prog}</div>
          </section>

          {res?.ratios && (
            <section className="rounded-md border border-line bg-surface-1 p-3.5">
              <h3 className="mb-2 text-[13px] font-semibold text-txt-mut">Ratios</h3>
              <table className="w-full text-[13px]">
                <tbody>
                  {res.ratios.map(([k, v]) => (
                    <tr key={k}><td className="py-0.5 text-txt-mut">{k}</td><td className="py-0.5 text-right tabular-nums text-txt">{v}</td></tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}
          {erreurGen && <p className="rounded-md border-l-2 border-amber bg-surface-1 p-2.5 text-[12px] text-amber">{erreurGen}</p>}
        </aside>

        {/* corps */}
        <main className="grid gap-4">
          {/* Programme */}
          <Carte titre="Programme" sous="ce qui fixe les assiettes">
            <div className="grid grid-cols-2 gap-x-6 gap-y-2 p-3 md:grid-cols-3">
              <ChampNum label="Terrain (m²)" value={entrees.programme.terrain} source={modele.sourcee.terrain != null}
                onChange={(v) => majProgramme({ terrain: v })} />
              <ChampTexte label="Zonage au PLU" value={modele.sourcee.zonage ?? '—'} source />
              <ChampNum label="Surface taxable (m²)" value={entrees.programme.surface_taxable}
                onChange={(v) => majProgramme({ surface_taxable: v })} />
              <ChampNum label="Loyer (€/m² SUV)" value={entrees.programme.loyer}
                onChange={(v) => majProgramme({ loyer: v })} />
              {modele.sourcee.prix_achat_dvf && (
                <ChampTexte label="Dernier prix DVF (info)" value={fmtEur(modele.sourcee.prix_achat_dvf.valeur)} source />
              )}
            </div>
          </Carte>

          {/* Produits */}
          <Carte titre="Produits" sous="une ligne par produit (libre · PLS · LLI)">
            <table className="w-full text-[13px]">
              <thead><tr className="border-b border-line text-left text-txt-mut">
                <th className="p-2">Produit</th><th className="p-2 text-right">Lots</th><th className="p-2 text-right">SUV m²</th>
                <th className="p-2 text-right">Prix TTC/m²</th><th className="p-2 text-right">TVA %</th><th className="p-2 text-right">CA TTC</th>
              </tr></thead>
              <tbody>
                {entrees.produits.map((p, i) => {
                  const dvf = modele.reperes_publics['dvf_neuf']
                  const caTtc = p.suv != null && p.prix_ttc_m2_suv != null ? p.suv * p.prix_ttc_m2_suv : null
                  return (
                    <tr key={i} className="border-b border-line">
                      <td className="p-2"><input className="w-32 rounded border border-line-2 bg-surface px-1.5 py-1" defaultValue={p.libelle} onChange={(e) => majProduit(i, { libelle: e.target.value })} /></td>
                      <td className="p-2"><CellNum value={p.lots} onChange={(v) => majProduit(i, { lots: v })} /></td>
                      <td className="p-2"><CellNum value={p.suv} onChange={(v) => majProduit(i, { suv: v })} /></td>
                      <td className="p-2">
                        <CellNum value={p.prix_ttc_m2_suv} onChange={(v) => majProduit(i, { prix_ttc_m2_suv: v })} />
                        {p.prix_ttc_m2_suv == null && dvf && (
                          <button className="ml-1 rounded-full border border-dashed border-line-2 px-1.5 text-[11px] text-txt-mut hover:bg-mint hover:text-mint-on"
                            onClick={() => majProduit(i, { prix_ttc_m2_suv: dvf.valeur })} title={dvf.source}>{dvf.label}</button>
                        )}
                      </td>
                      <td className="p-2"><CellNum value={p.tva == null ? null : p.tva * 100} onChange={(v) => majProduit(i, { tva: v == null ? null : v / 100 })} /></td>{/* saisie en %, stockée en taux */}
                      <td className="p-2 text-right tabular-nums">{fmtEur(caTtc)}</td>
                    </tr>
                  )
                })}
                <tr className="font-semibold"><td className="p-2">Total</td>
                  <td className="p-2 text-right tabular-nums">{res?.produits_totaux.lots ?? ''}</td>
                  <td className="p-2 text-right tabular-nums">{res?.produits_totaux.suv ?? ''}</td>
                  <td /><td /><td className="p-2 text-right tabular-nums">{fmtEur(res?.produits_totaux.ca_ttc)}</td>
                </tr>
              </tbody>
            </table>
          </Carte>

          {/* Bilan par blocs */}
          <Carte titre="Bilan" sous="les repères n'entrent dans le calcul que si vous les cliquez">
            <table className="w-full text-[13px]">
              <thead><tr className="border-b border-line text-left text-txt-mut">
                <th className="p-2">Libellé</th><th className="p-2">Assiette</th><th className="p-2 text-right">Taux</th>
                <th className="p-2 text-right">HT</th><th className="p-2 text-right">TVA</th><th className="p-2 text-right">TTC</th><th className="p-2">État</th>
              </tr></thead>
              <tbody>
                {modele.blocs.map((b) => {
                  const tot = res?.blocs.find((x) => x.id === b.id)
                  return (
                    <BlocLignes key={b.id} bloc={b} tot={tot} entrees={entrees} ligne={ligne}
                      reperePoste={reperePoste} adopterRepere={adopterRepere} majPoste={majPoste} />
                  )
                })}
                {/* Synthèse */}
                <tr className="bg-surface-2 font-semibold"><td className="p-2" colSpan={3}>Dépenses totales</td>
                  <td className="p-2 text-right tabular-nums">{fmtEur(res?.depenses_ht)}</td>
                  <td className="p-2 text-right tabular-nums">{fmtEur(res?.depenses_tva)}</td>
                  <td className="p-2 text-right tabular-nums">{fmtEur(res?.depenses_ttc)}</td><td /></tr>
                <tr className="font-semibold"><td className="p-2" colSpan={3}>Chiffre d'affaires</td>
                  <td className="p-2 text-right tabular-nums">{fmtEur(res?.ca_ht)}</td>
                  <td className="p-2 text-right tabular-nums">{fmtEur(res?.ca_tva)}</td>
                  <td className="p-2 text-right tabular-nums">{fmtEur(res?.ca_ttc)}</td><td /></tr>
                <tr><td className="p-2" colSpan={5}>TVA résiduelle</td>
                  <td className="p-2 text-right tabular-nums">{fmtEur(res?.tva_residuelle)}</td><td /></tr>
                <tr className="text-[15px] font-bold"><td className="p-2" colSpan={3}>Résultat net</td>
                  <td className="p-2 text-right tabular-nums text-mint">{complet ? fmtEur(res!.resultat_net) : ''}</td>
                  <td className="p-2 text-right tabular-nums" colSpan={2}>{complet ? `${fmtPct(res!.marge_pct)} du CA HT` : ''}</td><td /></tr>
                <tr><td className="p-2" colSpan={3}>Cash flow</td>
                  <td className="p-2 text-right tabular-nums">{complet ? fmtEur(res!.cash_flow) : ''}</td><td colSpan={3} /></tr>
              </tbody>
            </table>
            <Legende />
          </Carte>
        </main>
      </div>
    </Overlay>
  )
}

// ── sous-composants ──────────────────────────────────────────────────────
function Overlay({ children, onClose }: { children: React.ReactNode; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 overflow-auto bg-[rgba(6,10,8,0.92)]" onClick={onClose}>
      <div className="mx-auto my-6 max-w-[1500px] rounded-lg border border-line bg-surface" onClick={(e) => e.stopPropagation()}>
        {children}
      </div>
    </div>
  )
}

function Carte({ titre, sous, children }: { titre: string; sous?: string; children: React.ReactNode }) {
  return (
    <section className="overflow-hidden rounded-md border border-line bg-surface-1">
      <h2 className="flex items-center gap-2.5 border-b border-line px-3.5 py-3 text-[15px] font-semibold text-txt">
        {titre}{sous && <small className="font-normal text-txt-mut">{sous}</small>}
      </h2>
      {children}
    </section>
  )
}

function ChampNum({ label, value, source, onChange }: { label: string; value: number | null; source?: boolean; onChange: (v: number | null) => void }) {
  return (
    <label className="grid gap-1 text-[12px] text-txt-mut">{label}
      <input className={`h-8 rounded-md border bg-surface px-2.5 text-right tabular-nums ${value == null ? 'border-amber' : 'border-line-2'}`}
        defaultValue={value ?? ''} placeholder="à saisir" onChange={(e) => onChange(parseNum(e.target.value))} />
      {source && <Badge ton="vert">Sourcé</Badge>}
    </label>
  )
}
function ChampTexte({ label, value, source }: { label: string; value: string; source?: boolean }) {
  return (
    <div className="grid gap-1 text-[12px] text-txt-mut">{label}
      <div className="flex h-8 items-center text-[13px] text-txt">{value}</div>
      {source && <Badge ton="vert">Sourcé</Badge>}
    </div>
  )
}
function CellNum({ value, onChange }: { value: number | null; onChange: (v: number | null) => void }) {
  return (
    <input className={`w-24 rounded border bg-surface px-1.5 py-1 text-right tabular-nums ${value == null ? 'border-amber' : 'border-line-2'}`}
      defaultValue={value == null ? '' : fmtNum(value)} placeholder="—" onChange={(e) => onChange(parseNum(e.target.value))} />
  )
}

function BlocLignes({ bloc, tot, entrees, ligne, reperePoste, adopterRepere, majPoste }: {
  bloc: BilanModele['blocs'][number]
  tot: BilanResultat['blocs'][number] | undefined
  entrees: BilanEntrees
  ligne: Record<string, BilanResultat['lignes'][number]>
  reperePoste: (p: BilanPoste) => { valeur: number; label: string } | null
  adopterRepere: (p: BilanPoste) => void
  majPoste: (id: string, patch: Partial<BilanSaisie>) => void
}) {
  const [ouvert, setOuvert] = useState(true)
  return (
    <>
      <tr className="cursor-pointer bg-surface-2 font-bold hover:bg-mint hover:text-mint-on" onClick={() => setOuvert((o) => !o)}>
        <td className="p-2" colSpan={3}>{ouvert ? '▾' : '▸'} {bloc.titre} {tot && !tot.complet && <Badge ton="ambre">{tot.manquants} à renseigner</Badge>}</td>
        <td className="p-2 text-right tabular-nums">{tot?.complet ? fmtEur(tot.ht) : ''}</td>
        <td className="p-2 text-right tabular-nums">{tot?.complet ? fmtEur(tot.tva) : ''}</td>
        <td className="p-2 text-right tabular-nums">{tot?.complet ? fmtEur(tot.ttc) : ''}</td><td />
      </tr>
      {ouvert && bloc.postes.map((p) => {
        const s = entrees.postes[p.id] ?? { valeur: null, etat: 'a_renseigner' as const }
        const l = ligne[p.id]
        const rep = reperePoste(p)
        const unite = p.mode === 'pct' ? '%' : p.mode === 'unit' ? (p.unite ?? '') : '€'
        const estSansObjet = s.etat === 'sans_objet'
        return (
          <tr key={p.id} className="border-b border-line">
            <td className="p-2">{p.libelle}{p.sub && <small className="block text-txt-dim"> {p.sub}</small>}</td>
            <td className="p-2 tabular-nums text-txt-mut">{l?.assiette_valeur != null ? fmtEur(l.assiette_valeur) : (p.mode === 'forfait' ? 'forfait' : '—')}
              {p.besoin_assiette && !estSansObjet && (
                <input className="ml-1 w-24 rounded border border-amber bg-surface px-1 py-0.5 text-right"
                  defaultValue={s.assiette_valeur ?? ''} placeholder="assiette"
                  onChange={(e) => majPoste(p.id, { assiette_valeur: parseNum(e.target.value) })} />
              )}
            </td>
            <td className="p-2 text-right">
              {estSansObjet ? <span className="text-txt-dim">—</span> : (
                <span className="inline-flex items-center gap-1">
                  <input className={`w-20 rounded border bg-surface px-1.5 py-1 text-right tabular-nums ${s.valeur == null ? 'border-amber' : 'border-line-2'}`}
                    defaultValue={s.valeur == null ? '' : fmtNum(s.valeur)} placeholder="à saisir"
                    onChange={(e) => majPoste(p.id, { valeur: parseNum(e.target.value), etat: 'saisi' })} />
                  <span className="text-[11px] text-txt-dim">{unite}</span>
                </span>
              )}
            </td>
            <td className="p-2 text-right tabular-nums">{fmtEur(l?.ht)}</td>
            <td className="p-2 text-right tabular-nums">
              {p.tva === 'a_saisir' && !estSansObjet
                ? <input className={`w-14 rounded border bg-surface px-1 py-0.5 text-right ${s.tva == null ? 'border-amber' : 'border-line-2'}`}
                    defaultValue={s.tva == null ? '' : fmtNum(s.tva * 100)} placeholder="TVA %"
                    onChange={(e) => majPoste(p.id, { tva: pctToRate(e.target.value) })} />
                : fmtEur(l?.tva)}
            </td>
            <td className="p-2 text-right tabular-nums">{fmtEur(l?.ttc)}</td>
            <td className="p-2">
              <div className="flex flex-wrap items-center gap-1.5">
                <Badge ton={ETAT_TON[s.etat] ?? 'ambre'}>{ETAT_LABEL[s.etat] ?? 'À renseigner'}</Badge>
                {s.valeur == null && !estSansObjet && rep && (
                  <button className="rounded-full border border-dashed border-line-2 px-1.5 text-[11px] text-txt-mut hover:bg-mint hover:text-mint-on"
                    onClick={() => adopterRepere(p)}>{rep.label}</button>
                )}
                {s.valeur == null && !estSansObjet && (
                  <button className="text-[11px] text-txt-mut underline" onClick={() => majPoste(p.id, { valeur: null, etat: 'sans_objet' })}>Sans objet</button>
                )}
                {s.etat === 'saisi' && s.valeur != null && (
                  <button className="text-[11px] text-mint underline"
                    onClick={() => { void putBilanRatio(p.id, s.valeur!, s.tva ?? null); majPoste(p.id, { etat: 'ratios' }) }}>Mémoriser</button>
                )}
                {(s.valeur != null || estSansObjet) && (
                  <button className="text-[11px] text-txt-mut underline" title="Vider"
                    onClick={() => majPoste(p.id, { valeur: null, etat: 'a_renseigner' })}>↺</button>
                )}
              </div>
            </td>
          </tr>
        )
      })}
    </>
  )
}

function Legende() {
  return (
    <div className="flex flex-wrap items-center gap-3.5 px-3.5 py-2.5 text-[12px] text-txt-mut">
      <span><Badge ton="vert">Sourcé</Badge> donnée publique</span>
      <span><span className="rounded-full border border-dashed border-line-2 px-1.5">repère</span> proposition, cliquez pour l'adopter</span>
      <span><Badge ton="neutre">Saisi</Badge> votre valeur</span>
      <span><Badge ton="neutre">Mes ratios</Badge> mémorisé</span>
      <span><Badge ton="neutre">Sans objet</Badge> 0 volontaire</span>
      <span><Badge ton="ambre">À renseigner</Badge></span>
    </div>
  )
}
