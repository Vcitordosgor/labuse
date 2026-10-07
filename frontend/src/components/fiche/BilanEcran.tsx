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

// Pastilles d'état (BILAN-2) : plus d'« À renseigner » orange par ligne — une
// ligne vide ne porte pas de pastille (elle est juste comptée en haut).
const ETAT_LABEL: Record<string, string> = {
  source: 'Sourcé', saisi: 'Saisi', repere: 'Repère pris',
  ratios: 'Mes ratios', sans_objet: 'Sans objet',
}
const ETAT_TON: Record<string, 'vert' | 'neutre'> = {
  source: 'vert', saisi: 'neutre', repere: 'neutre', ratios: 'neutre', sans_objet: 'neutre',
}
// Numérotation des blocs comme le modèle : TOTAL (1) … TOTAL (4).
const NUM_BLOC: Record<string, number> = { T: 1, C: 2, G: 3, V: 4 }

function entreesInitiales(m: BilanModele): BilanEntrees {
  const postes: Record<string, BilanSaisie> = {}
  // Les ratios maison pré-remplissent (état « Mes ratios »), modifiables.
  for (const [pid, r] of Object.entries(m.ratios_compte)) {
    postes[pid] = { valeur: r.valeur, etat: 'ratios', tva: r.tva }
  }
  const calendrier: Record<string, number | null> = {}
  for (const c of m.calendrier ?? []) calendrier[c.id] = c.defaut
  return {
    programme: { terrain: m.sourcee.terrain ?? null, surface_taxable: null, loyer: null, sdp: null },
    produits: [
      { libelle: 'Produit 1', lots: null, suv: null, prix_ttc_m2_suv: null, tva: null },
      { libelle: 'Produit 2', lots: null, suv: null, prix_ttc_m2_suv: null, tva: null },
    ],
    postes,
    mode: 'marge',
    marge_cible: null,
    calendrier,
  }
}

export function BilanEcran({ idu, onClose, onGenerated }:
  { idu: string; onClose: () => void; onGenerated?: (docId: number) => void }) {
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
  const ratioMap = useMemo(() => {
    const m: Record<string, string> = {}
    for (const [k, v] of res?.ratios ?? []) m[k] = v
    return m
  }, [res])

  if (isLoading) return <Overlay onClose={onClose}><div className="p-6 text-txt-mut">Chargement du bilan…</div></Overlay>
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

  const generer = async () => {
    setErreurGen(null)
    try {
      const { doc_id } = await genererBilan(idu, entrees)
      setDocId(doc_id)
      onGenerated?.(doc_id)
      await ouvrir(docBilanUrl(idu, doc_id), 'bilan')
    } catch (e) {
      const d = (e as { detail?: { message?: string } })?.detail
      setErreurGen(d?.message ?? 'Génération impossible.')
    }
  }

  const suvTot = res?.produits_totaux.suv ?? null
  const lotsTot = res?.produits_totaux.lots ?? null
  const faisa = modele.reperes_publics['faisabilite'] ?? null
  const sitadel = modele.reperes_publics['sitadel'] ?? null

  return (
    <Overlay onClose={onClose}>
      <div className="sticky top-0 z-10 flex h-14 items-center gap-3 border-b border-line bg-surface-2 px-5">
        <Bouton niveau="secondaire" ton="vert" onClick={onClose}>← Fermer</Bouton>
        <div className="leading-tight">
          <div className="text-[16px] font-bold text-txt">Bilan · {idu}</div>
          {modele.sourcee.commune && <div className="text-[12px] text-txt-mut">{modele.sourcee.commune}</div>}
        </div>
        {/* compteur discret « N lignes vides » — information, jamais bloquant */}
        <span className="ml-3 text-[12px] text-txt-mut" title="Comme dans l'Excel, une case vide vaut 0.">
          {vides === 0 ? 'Toutes les lignes sont renseignées' : `${vides} ligne${vides > 1 ? 's' : ''} vide${vides > 1 ? 's' : ''}`}
        </span>
        <div className="ml-auto flex gap-2">
          {docId != null && (
            <a href={docBilanExcelUrl(idu, docId)} className="inline-flex h-8 items-center rounded-md border border-mint px-3 text-[13px] font-semibold text-mint hover:bg-mint hover:text-mint-on">Excel</a>
          )}
          <Bouton niveau="primaire" ton="vert" disabled={!!enCours} onClick={generer}>
            {enCours ? 'Génération…' : 'Générer le bilan'}
          </Bouton>
        </div>
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

        {/* ── Tête : ratios & programme · calendrier · résultat (ordre de l'Excel) ── */}
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_300px]">
          {/* Ratios & données du programme */}
          <Carte titre="Ratios &amp; programme" sous="dans l'ordre de l'Excel">
            <table className="w-full text-[13px]">
              <tbody>
                <TeteInput label="Terrain" unite="m²" value={entrees.programme.terrain} revKey={rev}
                  source={modele.sourcee.terrain != null} onChange={(v) => majProgramme({ terrain: v })} />
                <TeteInput label="Surface de plancher" unite="m²" value={entrees.programme.sdp} revKey={rev}
                  repere={faisa ? { label: faisa.label, valeur: faisa.valeur } : null}
                  onChange={(v) => majProgramme({ sdp: v })} onPick={(v) => { majProgramme({ sdp: v }); bump() }} />
                <TeteInput label="Surface taxable" unite="m²" value={entrees.programme.surface_taxable} revKey={rev}
                  repere={faisa ? { label: faisa.label, valeur: faisa.valeur } : null}
                  onChange={(v) => majProgramme({ surface_taxable: v })} onPick={(v) => { majProgramme({ surface_taxable: v }); bump() }}
                  alerte={vrais['stax']} />
                <TeteCalc label="SUV" value={suvTot != null ? `${fmtNum(suvTot)} m²` : '—'} />
                <TeteCalc label="Coût const. m² SUV HT" value={ratioMap['Coût const. m² SUV HT'] ?? '—'} alerte={vrais['cout_const']} />
                <TeteCalc label="Prix moyen m² SUV HT" value={ratioMap['Prix moyen au m² SUV HT'] ?? '—'} />
                <TeteCalc label="Net promoteur m² SUV TTC" value={ratioMap['Net promoteur m² SUV TTC'] ?? '—'} />
                <TeteCalc label="CA TTC programme" value={fmtEur(res?.ca_ttc)} />
                <TeteCalc label="Renta nette / CA HT" value={fmtPct(res?.marge_pct)} />
                <TeteCalc label="Nombre de lots" value={lotsTot != null ? String(Math.round(lotsTot)) : '—'} />
              </tbody>
            </table>
          </Carte>

          {/* Calendrier prévisionnel */}
          <Carte titre="Calendrier prévisionnel" sous="Compromis → Livraison, en J+n">
            <table className="w-full text-[13px]">
              <tbody>
                {(modele.calendrier ?? []).map((c) => (
                  <tr key={c.id} className="border-b border-line last:border-0">
                    <td className="py-1 pl-3 text-txt-mut">{c.libelle}</td>
                    <td className="py-1 pr-3 text-right">
                      <span className="inline-flex items-center gap-1">
                        <span className="text-[11px] text-txt-dim">J+</span>
                        <input key={rev} className="h-7 w-16 rounded border border-line-2 bg-surface px-1.5 text-right tabular-nums"
                          defaultValue={entrees.calendrier[c.id] ?? ''} placeholder="0"
                          onChange={(ev) => majCalendrier(c.id, parseNum(ev.target.value))} />
                        <span className="text-[11px] text-txt-dim">mois</span>
                      </span>
                      {c.repere === 'sitadel' && sitadel && (
                        <button className="ml-1 rounded-full border border-dashed border-line-2 px-1.5 text-[11px] text-txt-mut hover:bg-mint hover:text-mint-on"
                          title={sitadel.source}
                          onClick={() => { majCalendrier(c.id, (entrees.calendrier['depot_pc'] ?? 0) + Math.round(sitadel.valeur)); bump() }}>
                          Sitadel {Math.round(sitadel.valeur)} mois
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Carte>

          {/* Résultat + sens (marge / prix max terrain) */}
          <section className="grid content-start gap-3 rounded-md border border-line bg-surface-1 p-3.5">
            <div className="flex flex-wrap gap-1.5">
              {(['marge', 'prix'] as const).map((mode) => (
                <button key={mode} onClick={() => setEntrees((e) => e && ({ ...e, mode }))}
                  className={`h-8 rounded-full border px-3 text-[13px] ${entrees.mode === mode ? 'border-mint bg-mint text-mint-on' : 'border-line-2 text-txt-mut'}`}>
                  {mode === 'marge' ? 'Ma marge à ce prix' : 'Le prix max du terrain'}
                </button>
              ))}
            </div>
            {entrees.mode === 'prix' && (
              <label className="grid gap-1 text-[12px] text-txt-mut">Marge visée
                <span className="flex items-center gap-2">
                  <input className="h-8 w-full rounded-md border border-line-2 bg-surface px-2.5 text-right tabular-nums"
                    defaultValue={entrees.marge_cible ?? ''} placeholder="à saisir"
                    onChange={(ev) => setEntrees((e) => e && ({ ...e, marge_cible: parseNum(ev.target.value) }))} />
                  <span className="min-w-[44px] text-[12px] text-txt-dim">% CA HT</span>
                </span>
              </label>
            )}
            <div>
              <div className="text-[12px] text-txt-mut">{entrees.mode === 'marge' ? 'Résultat net' : 'Prix maximum du terrain'}</div>
              {entrees.mode === 'marge' ? (
                <>
                  <div className="text-[26px] font-bold leading-none tabular-nums text-txt">{fmtEur(res?.resultat_net)}</div>
                  <div className="mt-1.5 text-[13px] text-txt-mut">{fmtPct(res?.marge_pct)} du CA HT</div>
                </>
              ) : entrees.marge_cible == null ? (
                <div className="text-[15px] font-semibold text-amber">Saisissez la marge visée</div>
              ) : (
                <>
                  <div className="text-[26px] font-bold leading-none tabular-nums text-txt">{fmtEur(res?.prix_max_terrain)}</div>
                  <div className="mt-1.5 text-[13px] text-txt-mut">{fmtEur(res?.prix_max_terrain_m2)}/m² de terrain</div>
                </>
              )}
            </div>
            {vrais['marge'] && <div className="border-l-2 border-amber pl-2 text-[12px] text-amber">{vrais['marge']}</div>}
            {erreurGen && <p className="rounded-md border-l-2 border-amber bg-surface p-2.5 text-[12px] text-amber">{erreurGen}</p>}
          </section>
        </div>

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
                const caTtc = (p.suv ?? 0) * (p.prix_ttc_m2_suv ?? 0)
                return (
                  <tr key={i} className="border-b border-line">
                    <td className="p-2"><input className="w-32 rounded border border-line-2 bg-surface px-1.5 py-1" defaultValue={p.libelle} onChange={(e) => majProduit(i, { libelle: e.target.value })} /></td>
                    <td className="p-2"><CellNum revKey={rev} value={p.lots} onChange={(v) => majProduit(i, { lots: v })} /></td>
                    <td className="p-2"><CellNum revKey={rev} value={p.suv} onChange={(v) => majProduit(i, { suv: v })} /></td>
                    <td className="p-2">
                      <span className="inline-flex items-center gap-1">
                        <CellNum revKey={rev} value={p.prix_ttc_m2_suv} onChange={(v) => majProduit(i, { prix_ttc_m2_suv: v })} />
                        {p.prix_ttc_m2_suv == null && dvf && (
                          <button className="rounded-full border border-dashed border-line-2 px-1.5 text-[11px] text-txt-mut hover:bg-mint hover:text-mint-on"
                            onClick={() => { majProduit(i, { prix_ttc_m2_suv: dvf.valeur }); bump() }} title={dvf.source}>{dvf.label}</button>
                        )}
                      </span>
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
        </Carte>

        {/* ── Le tableau unique du bilan ── */}
        <Carte titre="Bilan" sous="les repères n'entrent dans le calcul que si vous les cliquez">
          <table className="w-full table-fixed text-[13px]">
            <colgroup>
              <col className="w-[28%]" /><col className="w-[16%]" /><col className="w-[16%]" />
              <col className="w-[12%]" /><col className="w-[11%]" /><col className="w-[12%]" /><col className="w-[5%]" />
            </colgroup>
            <thead><tr className="border-b border-line text-left text-txt-mut">
              <th className="p-2">Libellé</th><th className="p-2">Assiette</th><th className="p-2 text-right">Taux</th>
              <th className="p-2 text-right">HT</th><th className="p-2 text-right">TVA</th><th className="p-2 text-right">TTC</th><th className="p-2">État</th>
            </tr></thead>
            <tbody>
              {modele.blocs.map((b) => {
                const tot = res?.blocs.find((x) => x.id === b.id)
                return (
                  <BlocLignes key={b.id} bloc={b} tot={tot} entrees={entrees} ligne={ligne} rev={rev} vrais={vrais}
                    reperePoste={reperePoste} adopterRepere={adopterRepere} majPoste={majPoste} majPosteProg={majPosteProg} />
                )
              })}
              {/* Synthèse : CA et marge en bas */}
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
                <td className="p-2 text-right tabular-nums text-mint">{fmtEur(res?.resultat_net)}</td>
                <td className="p-2 text-right tabular-nums" colSpan={2}>{fmtPct(res?.marge_pct)} du CA HT</td><td /></tr>
              <tr><td className="p-2" colSpan={3}>Cash flow</td>
                <td className="p-2 text-right tabular-nums">{fmtEur(res?.cash_flow)}</td><td colSpan={3} /></tr>
            </tbody>
          </table>
          <Legende />
        </Carte>
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

// Ligne de tête éditable (Terrain / SDP / Surface taxable) : repère à droite.
function TeteInput({ label, unite, value, source, repere, revKey, onChange, onPick, alerte }: {
  label: string; unite: string; value: number | null; source?: boolean; revKey?: number
  repere?: { label: string; valeur: number } | null; alerte?: string
  onChange: (v: number | null) => void; onPick?: (v: number | null) => void
}) {
  return (
    <tr className="border-b border-line">
      <td className="py-1 pl-3 text-txt-mut">{label}{source && <Badge ton="vert">Sourcé</Badge>}</td>
      <td className="py-1 pr-3 text-right">
        <span className="inline-flex items-center gap-1">
          <input key={revKey} className="h-7 w-24 rounded border border-line-2 bg-surface px-1.5 text-right tabular-nums"
            defaultValue={value == null ? '' : fmtNum(value)} placeholder="0" onChange={(e) => onChange(parseNum(e.target.value))} />
          <span className="text-[11px] text-txt-dim">{unite}</span>
          {value == null && repere && (
            <button className="rounded-full border border-dashed border-line-2 px-1.5 text-[11px] text-txt-mut hover:bg-mint hover:text-mint-on"
              onClick={() => (onPick ?? onChange)(repere.valeur)} title={repere.label}>repère</button>
          )}
        </span>
        {alerte && <div className="text-[11px] text-amber">{alerte}</div>}
      </td>
    </tr>
  )
}
// Ligne de tête calculée (lecture seule).
function TeteCalc({ label, value, alerte }: { label: string; value: string; alerte?: string }) {
  return (
    <tr className="border-b border-line last:border-0">
      <td className="py-1 pl-3 text-txt-mut">{label}{alerte && <small className="block text-amber">{alerte}</small>}</td>
      <td className={`py-1 pr-3 text-right tabular-nums font-semibold ${alerte ? 'text-amber' : 'text-txt'}`}>{value}</td>
    </tr>
  )
}

function CellNum({ value, onChange, revKey }: { value: number | null; onChange: (v: number | null) => void; revKey?: number }) {
  return (
    <input key={revKey} className="w-24 rounded border border-line-2 bg-surface px-1.5 py-1 text-right tabular-nums"
      defaultValue={value == null ? '' : fmtNum(value)} placeholder="0" onChange={(e) => onChange(parseNum(e.target.value))} />
  )
}

function BlocLignes({ bloc, tot, entrees, ligne, rev, vrais, reperePoste, adopterRepere, majPoste, majPosteProg }: {
  bloc: BilanModele['blocs'][number]
  tot: BilanResultat['blocs'][number] | undefined
  entrees: BilanEntrees
  ligne: Record<string, BilanResultat['lignes'][number]>
  rev: number
  vrais: Record<string, string>
  reperePoste: (p: BilanPoste) => { valeur: number; label: string } | null
  adopterRepere: (p: BilanPoste) => void
  majPoste: (id: string, patch: Partial<BilanSaisie>) => void
  majPosteProg: (id: string, patch: Partial<BilanSaisie>) => void
}) {
  const [ouvert, setOuvert] = useState(true)
  const n = NUM_BLOC[bloc.id]
  return (
    <>
      <tr className="cursor-pointer bg-surface-2 font-bold hover:bg-mint hover:text-mint-on" onClick={() => setOuvert((o) => !o)}>
        <td className="p-2" colSpan={7}>{ouvert ? '▾' : '▸'} {n ? `(${n}) ` : ''}{bloc.titre}</td>
      </tr>
      {ouvert && bloc.postes.map((p) => {
        const s = entrees.postes[p.id] ?? { valeur: null, etat: 'a_renseigner' as const }
        const l = ligne[p.id]
        const rep = reperePoste(p)
        const unite = p.mode === 'pct' ? '%' : p.mode === 'unit' ? (p.unite ?? '') : '€'
        const estSansObjet = s.etat === 'sans_objet'
        const vide = !!l?.manquant  // ligne vide (BILAN-2) : vaut 0, affichée à blanc
        const etatLabel = ETAT_LABEL[s.etat]
        return (
          <tr key={p.id} className="border-b border-line">
            <td className="p-2">{p.libelle}{p.sub && <small className="block text-txt-dim"> {p.sub}</small>}
              {vrais[p.id] && <small className="block text-amber">{vrais[p.id]}</small>}</td>
            <td className="p-2 tabular-nums text-txt-mut">{l?.assiette_valeur ? fmtEur(l.assiette_valeur) : (p.mode === 'forfait' ? 'forfait' : '—')}
              {p.besoin_assiette && !estSansObjet && (
                <input key={rev} className="ml-1 w-24 rounded border border-line-2 bg-surface px-1 py-0.5 text-right"
                  defaultValue={s.assiette_valeur ?? ''} placeholder="assiette"
                  onChange={(e) => majPoste(p.id, { assiette_valeur: parseNum(e.target.value) })} />
              )}
            </td>
            <td className="p-2 text-right">
              {estSansObjet ? <span className="text-txt-dim">—</span> : (
                <span className="inline-flex items-center justify-end gap-1">
                  <input key={rev} className="w-20 rounded border border-line-2 bg-surface px-1.5 py-1 text-right tabular-nums"
                    defaultValue={s.valeur == null ? '' : fmtNum(s.valeur)} placeholder="0"
                    onChange={(e) => majPoste(p.id, { valeur: parseNum(e.target.value), etat: 'saisi' })} />
                  <span className="text-[11px] text-txt-dim">{unite}</span>
                  {/* repère LABUSE, cliquable À DROITE de la case (n'entre qu'au clic) */}
                  {s.valeur == null && rep && (
                    <button className="rounded-full border border-dashed border-line-2 px-1.5 text-[11px] text-txt-mut hover:bg-mint hover:text-mint-on"
                      onClick={() => adopterRepere(p)} title={rep.label}>repère</button>
                  )}
                </span>
              )}
            </td>
            <td className="p-2 text-right tabular-nums text-txt">{vide ? <span className="text-txt-dim">—</span> : fmtEur(l?.ht)}</td>
            <td className="p-2 text-right tabular-nums">
              {p.tva === 'a_saisir' && !estSansObjet
                ? <input key={rev} className="w-14 rounded border border-line-2 bg-surface px-1 py-0.5 text-right"
                    defaultValue={s.tva == null ? '' : fmtNum(s.tva * 100)} placeholder="TVA %"
                    onChange={(e) => majPoste(p.id, { tva: pctToRate(e.target.value) })} />
                : (vide ? <span className="text-txt-dim">—</span> : fmtEur(l?.tva))}
            </td>
            <td className="p-2 text-right tabular-nums">{vide ? <span className="text-txt-dim">—</span> : fmtEur(l?.ttc)}</td>
            <td className="p-2">
              <div className="flex flex-wrap items-center gap-1.5">
                {etatLabel && <Badge ton={ETAT_TON[s.etat] ?? 'neutre'}>{etatLabel}</Badge>}
                {s.valeur == null && !estSansObjet && (
                  <button className="text-[11px] text-txt-mut underline" onClick={() => majPosteProg(p.id, { valeur: null, etat: 'sans_objet' })}>Sans objet</button>
                )}
                {s.etat === 'saisi' && s.valeur != null && (
                  <button className="text-[11px] text-mint underline"
                    onClick={() => { void putBilanRatio(p.id, s.valeur!, s.tva ?? null); majPosteProg(p.id, { etat: 'ratios' }) }}>Mémoriser</button>
                )}
                {(s.valeur != null || estSansObjet) && (
                  <button className="text-[11px] text-txt-mut underline" title="Vider"
                    onClick={() => majPosteProg(p.id, { valeur: null, etat: 'a_renseigner' })}>↺</button>
                )}
              </div>
            </td>
          </tr>
        )
      })}
      {/* sous-total du bloc : « TOTAL (n) » comme le modèle */}
      <tr className="border-b-2 border-line font-semibold text-txt-mut">
        <td className="p-2" colSpan={3}>{n ? `TOTAL (${n})` : 'Total'} — {bloc.titre}</td>
        <td className="p-2 text-right tabular-nums">{fmtEur(tot?.ht)}</td>
        <td className="p-2 text-right tabular-nums">{fmtEur(tot?.tva)}</td>
        <td className="p-2 text-right tabular-nums">{fmtEur(tot?.ttc)}</td><td />
      </tr>
    </>
  )
}

function Legende() {
  return (
    <div className="flex flex-wrap items-center gap-3.5 px-3.5 py-2.5 text-[12px] text-txt-mut">
      <span>Comme dans l'Excel, une case vide vaut 0 — la marge et les totaux s'affichent dès la première saisie.</span>
      <span><Badge ton="vert">Sourcé</Badge> donnée publique</span>
      <span><span className="rounded-full border border-dashed border-line-2 px-1.5">repère</span> proposition, cliquez pour l'adopter</span>
      <span><Badge ton="neutre">Saisi</Badge> votre valeur</span>
      <span><Badge ton="neutre">Mes ratios</Badge> mémorisé</span>
      <span><Badge ton="neutre">Sans objet</Badge> 0 volontaire</span>
    </div>
  )
}
