// DOCS-1 (Lot A) — LA CATÉGORIE « DOCUMENTS » : une PORTE, pas une donnée propre. Trois morceaux :
//   1. le CATALOGUE (grille 2×4) des 8 documents ;
//   2. la PORTE (fenêtre centrée) : on choisit la/les parcelle(s), on génère ;
//   3. la BIBLIOTHÈQUE « Mes documents » (remplie au Lot B — ici l'en-tête + l'état vide).
// Tout lit la fiche ou l'outil par les fonctions déjà servies. Aucun calcul au front, aucun chiffre
// décidé ici : la porte résout une parcelle (getFiche) et ouvre l'URL du générateur existant.
import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useApp } from '../../store/useApp'
import { Badge } from '../ui/Badge'
import { Bouton } from '../ui/Bouton'
import { Chip } from '../ui/Chip'
import { ParcelInput } from '../ParcelInput'
import { FinancierQuestionnaire } from '../fiche/FinancierQuestionnaire'
import {
  getFiche, getGabarit,
  docDossierUrl, docBilanUrl, docApporteurUrl, docPreDossierUrl, docGabaritUrl, docComparatifUrl, docEtudeZoneUrl,
  listerDocuments, enregistrerDocument, rafraichirDocument,
  type DocType, type DocGenereRow,
} from '../../lib/api'
import { fmtM2, iduComplet } from '../../lib/format'
import { CATALOGUE, type DocCatalogue } from './catalogue'

// l'URL du générateur d'une ligne de bibliothèque (régénération à la demande — « Ouvrir »).
function urlDocument(r: Pick<DocGenereRow, 'doc_type' | 'idus' | 'rayon_km'>): string | null {
  const i0 = r.idus[0]
  switch (r.doc_type) {
    case 'dossier': return i0 ? docDossierUrl(i0) : null
    case 'bilan': return i0 ? docBilanUrl(i0) : null
    case 'apporteur': return i0 ? docApporteurUrl(i0) : null
    case 'pre-dossier': return i0 ? docPreDossierUrl(i0) : null
    case 'gabarit': return i0 ? docGabaritUrl(i0) : null
    case 'comparatif': return r.idus.length >= 2 ? docComparatifUrl(r.idus) : null
    case 'etude-zone': return i0 ? docEtudeZoneUrl(i0, r.rayon_km ?? 2) : null
    default: return null
  }
}

// ── vignette : un glyphe sobre par carte (la DA finale les remappe ; ici distinct et net à 56×72). ──
function Vignette({ kind, bientot }: { kind: DocCatalogue['kind']; bientot?: boolean }) {
  return (
    <svg viewBox="0 0 56 72" className={`block h-[72px] w-[56px] rounded border ${bientot ? 'border-line-2 opacity-60' : 'border-line-2'}`} aria-hidden>
      <rect x="0" y="0" width="56" height="72" rx="4" className="fill-bg" />
      {kind === 'multi' ? (
        <>
          <rect className="fill-mint" x="8" y="8" width="16" height="3" />
          <rect className="fill-mint" x="31" y="8" width="9" height="3" />
          {[16, 22, 28, 34, 40, 46, 52].map((y) => (
            <g key={y}><rect className="fill-line-2" x="8" y={y} width="15" height="2" /><rect className="fill-line-2" x="31" y={y} width="9" height="2" /><rect className="fill-line-2" x="42" y={y} width="7" height="2" /></g>
          ))}
        </>
      ) : kind === 'zone' ? (
        <>
          <rect className="fill-mint" x="8" y="8" width="26" height="3" />
          <rect x="8" y="15" width="40" height="22" rx="1" fill="none" className="stroke-mint" strokeWidth="1.2" />
          <path d="M18 20l14-3 10 8-6 9-14 1-6-8z" className="fill-mint" opacity="0.4" />
          {[42, 47, 52, 57, 62].map((y) => <rect key={y} className="fill-line-2" x="8" y={y} width={y % 3 ? 40 : 30} height="2" />)}
        </>
      ) : (
        <>
          <rect className="fill-mint" x="8" y="8" width="24" height="3" />
          {[16, 21, 26].map((y) => <rect key={y} className="fill-line-2" x="8" y={y} width={y === 21 ? 34 : 40} height="2" />)}
          <rect x="8" y="33" width="40" height="18" rx="1" fill="none" className="stroke-mint" strokeWidth="1.2" />
          {[56, 61].map((y) => <rect key={y} className="fill-line-2" x="8" y={y} width={y === 56 ? 30 : 36} height="2" />)}
        </>
      )}
    </svg>
  )
}

function DocCard({ d, onOpen }: { d: DocCatalogue; onOpen: () => void }) {
  if (d.bientot) {
    // Comparables DVF — HORS mandat : carte présente, grisée à 40 %, « bientôt », non cliquable.
    return (
      <div aria-disabled className="grid cursor-not-allowed grid-cols-[56px_1fr] items-start gap-3 rounded-md border border-line bg-surface-1 p-3 opacity-40" title="Bientôt">
        <Vignette kind={d.kind} bientot />
        <div>
          <div className="flex flex-wrap items-center gap-2 text-[15px] font-semibold text-txt">
            {d.nom} <Badge ton="neutre">bientôt</Badge>
          </div>
          <div className="mt-1 text-[13px] text-txt-dim">{d.desc}</div>
        </div>
      </div>
    )
  }
  return (
    <button
      onClick={onOpen}
      className="group grid grid-cols-[56px_1fr] items-start gap-3 rounded-md border border-line bg-surface-1 p-3 text-left transition-colors duration-quick hover:border-mint hover:bg-mint focus-visible:border-mint focus-visible:bg-mint focus-visible:outline-none"
    >
      <Vignette kind={d.kind} />
      <div>
        <div className="flex flex-wrap items-center gap-2 text-[15px] font-semibold text-txt group-hover:text-mint-on">
          {d.nom}
          {d.formats.map((f) => (
            <span key={f} className="inline-flex h-[18px] items-center rounded-full border border-line-2 px-[7px] text-[11px] font-semibold text-txt-mut group-hover:border-mint-on group-hover:text-mint-on">{f}</span>
          ))}
        </div>
        <div className="mt-1 text-[13px] text-txt-dim group-hover:text-mint-on/80">{d.desc}</div>
      </div>
    </button>
  )
}

// ── la parcelle résolue (lit la fiche) : IDU, adresse+CP, zone + surface « à cheval ». ──
function ParcelleResolue({ idu, onFiche }: { idu: string; onFiche: () => void }) {
  const q = useQuery({ queryKey: ['fiche', idu], queryFn: () => getFiche(idu) })
  const f = q.data
  // zone dominante + part « à cheval » (comme la fiche) : la plus grande part des zones du règlement.
  const zones = f?.reglement_plu?.zones ?? []
  const dom = zones.reduce<{ zone: string; part: number } | null>((acc, z) => {
    const part = typeof z.part === 'number' ? z.part : null
    if (part == null) return acc
    return !acc || part > acc.part ? { zone: z.zone, part } : acc
  }, null)
  const zoneLib = f?.reglement_plu?.zone_famille || dom?.zone || null
  const surf = f?.surface_m2 ?? null
  const aCheval = !!f?.reglement_plu?.a_cheval && dom && dom.part < 1 && surf != null
  return (
    <div className="relative mt-2.5 grid gap-0.5 rounded-md border border-line-2 px-3 py-2.5">
      <div className="font-semibold text-txt">{iduComplet(idu)}</div>
      {q.isLoading ? (
        <div className="text-[13px] text-txt-dim">Résolution…</div>
      ) : (
        <>
          {(f?.adresse || f?.commune) && (
            <div className="text-[13px] text-txt-dim">{[f?.adresse, f?.commune].filter(Boolean).join(', ')}</div>
          )}
          {(zoneLib || surf != null) && (
            <div className="text-[13px] text-txt-dim">
              {[zoneLib, surf != null ? fmtM2(surf) : null].filter(Boolean).join(' · ')}
              {aCheval && dom ? ` dont ${fmtM2(surf! * dom.part)} en ${dom.zone}` : ''}
            </div>
          )}
        </>
      )}
      <button onClick={onFiche} className="absolute right-3 top-2.5 text-[13px] font-semibold text-amber hover:text-mint-on hover:rounded hover:bg-amber hover:px-1">Fiche →</button>
    </div>
  )
}

// ── la porte (fenêtre centrée) : ✕ / Échap / clic hors fenêtre ferment. ──
function Porte({ d, onClose }: { d: DocCatalogue; onClose: () => void }) {
  const select = useApp((s) => s.select)
  const setView = useApp((s) => s.setView)
  const qc = useQueryClient()
  // enregistre la génération dans « Mes documents » (best-effort : la bibliothèque n'empêche jamais
  // de produire le PDF — un compte pilote/non connecté génère sans trace, sans erreur bloquante).
  const enregistrer = (doc_type: DocType, idusCible: string[], rayon_km?: number | null) => {
    enregistrerDocument({ doc_type, idus: idusCible, rayon_km: rayon_km ?? null })
      .then(() => qc.invalidateQueries({ queryKey: ['documents'] }))
      .catch(() => { /* non bloquant */ })
  }
  // variante parcelle / multi / zone
  const [idu, setIdu] = useState<string | null>(null)                // parcelle & zone
  const [idus, setIdus] = useState<(string | null)[]>([null, null, null])  // multi (2 à 3)
  const [rayon, setRayon] = useState(2)                              // zone : 1..20 km, défaut 2
  const [bilanOuvert, setBilanOuvert] = useState(false)

  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [onClose])

  const ouvrirFiche = (i: string) => { select(i); setView('cartes'); onClose() }

  // Gabarit : « Absent si calcul incomplet » — on interroge l'outil AVANT de proposer la génération.
  const gab = useQuery({
    queryKey: ['gabarit', idu], queryFn: () => getGabarit(idu!),
    enabled: d.key === 'gabarit' && !!idu, retry: false,
  })
  const gabaritBloque = d.key === 'gabarit' && !!idu && gab.data?.status === 'incomplete'

  const generer = () => {
    if (d.key === 'bilan') {
      // Exception assumée : ouvre l'écran d'hypothèses (qui génère), et l'inscrit dans Mes documents.
      if (idu) enregistrer('bilan', [idu])
      setBilanOuvert(true)
      return
    }
    if (!idu) return
    const url =
      d.key === 'dossier' ? docDossierUrl(idu)
      : d.key === 'apporteur' ? docApporteurUrl(idu)
      : d.key === 'pre-dossier' ? docPreDossierUrl(idu)
      : d.key === 'gabarit' ? docGabaritUrl(idu)
      : null
    if (url) { window.open(url, '_blank', 'noopener'); enregistrer(d.key as DocType, [idu]); onClose() }
  }

  const idusValides = idus.filter((x): x is string => !!x)
  const placeholder = 'Adresse, IDU ou référence (BW0917)'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[rgba(6,10,8,0.72)] p-4" onClick={onClose}>
      <div role="dialog" aria-modal="true" aria-label={d.nom}
        className="w-[420px] max-w-full rounded-md border border-line-2 bg-surface-1 p-4" onClick={(e) => e.stopPropagation()}>
        <header className="mb-3 flex items-center justify-between">
          <div className="text-[16px] font-bold text-txt">{d.nom}</div>
          <button aria-label="Fermer" onClick={onClose}
            className="grid h-8 w-8 place-items-center rounded-md text-txt-mut hover:bg-mint hover:text-mint-on">✕</button>
        </header>

        {/* ── variante parcelle (Dossier · Bilan · Apporteur · Pré-dossier PC · Gabarit) ── */}
        {d.kind === 'parcelle' && (
          <div>
            <div className="mb-2 font-semibold text-txt">Sur quelle parcelle ?</div>
            <ParcelInput placeholder={placeholder} withCarte={false} onPick={setIdu} autoFocus />
            {idu && <ParcelleResolue idu={idu} onFiche={() => ouvrirFiche(idu)} />}
            {gabaritBloque ? (
              <p className="my-3 border-l-2 border-amber pl-2.5 text-[13px] text-amber">
                Gabarit non calculable sur cette parcelle : donnée réglementaire manquante.
              </p>
            ) : (
              <p className="my-3 border-l-2 border-line-2 pl-2.5 text-[13px] text-txt-dim">{d.explication}</p>
            )}
            <Bouton niveau="primaire" ton="vert" className="w-full" disabled={!idu || gabaritBloque} onClick={generer}>
              {d.cta}
            </Bouton>
          </div>
        )}

        {/* ── variante 2–3 parcelles (Comparatif) ── */}
        {d.kind === 'multi' && (
          <div>
            <div className="mb-2 font-semibold text-txt">Quelles parcelles ? (2 à 3)</div>
            <div className="grid gap-2">
              <ParcelInput placeholder={placeholder} withCarte={false} autoFocus onPick={(i) => setIdus((a) => [i, a[1], a[2]])} />
              <ParcelInput placeholder={placeholder} withCarte={false} onPick={(i) => setIdus((a) => [a[0], i, a[2]])} />
              <ParcelInput placeholder="Troisième parcelle (facultatif)" withCarte={false} onPick={(i) => setIdus((a) => [a[0], a[1], i])} />
            </div>
            <p className="my-3 border-l-2 border-line-2 pl-2.5 text-[13px] text-txt-dim">{d.explication}</p>
            <Bouton niveau="primaire" ton="vert" className="w-full" disabled={idusValides.length < 2}
              onClick={() => { window.open(docComparatifUrl(idusValides), '_blank', 'noopener'); enregistrer('comparatif', idusValides); onClose() }}>
              {d.cta}
            </Bouton>
          </div>
        )}

        {/* ── variante zone (Étude de zone) : parcelle + rayon en km au −/+ (1..20, défaut 2) ── */}
        {d.kind === 'zone' && (
          <div>
            <div className="mb-2 font-semibold text-txt">Autour d’une parcelle</div>
            <ParcelInput placeholder={placeholder} withCarte={false} autoFocus onPick={setIdu} />
            {idu && <ParcelleResolue idu={idu} onFiche={() => ouvrirFiche(idu)} />}
            <div className="mb-2 mt-2 text-[13px] font-medium text-txt-mut">Rayon autour de la parcelle</div>
            <div className="flex items-center gap-2.5">
              <Bouton niveau="secondaire" ton="vert" icone aria-label="Réduire" disabled={rayon <= 1} onClick={() => setRayon((r) => Math.max(1, r - 1))}>−</Bouton>
              <div className="h-8 flex-1 rounded-md border border-line-2 text-center leading-8"><b className="text-txt">{rayon}</b> km</div>
              <Bouton niveau="secondaire" ton="vert" icone aria-label="Augmenter" disabled={rayon >= 20} onClick={() => setRayon((r) => Math.min(20, r + 1))}>+</Bouton>
            </div>
            <p className="my-3 border-l-2 border-line-2 pl-2.5 text-[13px] text-txt-dim">{d.explication}</p>
            <Bouton niveau="primaire" ton="vert" className="w-full" disabled={!idu}
              onClick={() => { if (idu) { window.open(docEtudeZoneUrl(idu, rayon), '_blank', 'noopener'); enregistrer('etude-zone', [idu], rayon); onClose() } }}>
              {d.cta}
            </Bouton>
          </div>
        )}
      </div>

      {/* Bilan (exception assumée) : l'écran d'hypothèses pré-rempli sur la parcelle, qui génère ensuite. */}
      {bilanOuvert && idu && (
        <div onClick={(e) => e.stopPropagation()}>
          <FinancierQuestionnaire idu={idu} onClose={() => { setBilanOuvert(false); onClose() }} />
        </div>
      )}
    </div>
  )
}

// ── bibliothèque « Mes documents » — la liste de ce que le compte a généré, régénérable. ──
// Les chips filtrent par type ; « Tous » (dernier à droite) est l'état par défaut.
const FILTRES: { label: string; type: DocType | null }[] = [
  { label: 'Dossier', type: 'dossier' }, { label: 'Bilan', type: 'bilan' },
  { label: 'Apporteur', type: 'apporteur' }, { label: 'Pré-dossier PC', type: 'pre-dossier' },
  { label: 'Gabarit', type: 'gabarit' }, { label: 'Comparatif', type: 'comparatif' },
  { label: 'Étude de zone', type: 'etude-zone' },
]
const dateFr = (iso: string) => { const d = new Date(iso); return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}/${d.getFullYear()}` }

function sur(r: DocGenereRow): string {
  if (r.doc_type === 'etude-zone') return `Rayon ${r.rayon_km ?? 2} km autour de ${iduComplet(r.idus[0] ?? '')}`
  if (r.doc_type === 'comparatif') return r.idus.join(' · ')
  return iduComplet(r.idus[0] ?? '')
}

function LigneDoc({ r, onChange }: { r: DocGenereRow; onChange: () => void }) {
  const ouvrir = () => { const u = urlDocument(r); if (u) window.open(u, '_blank', 'noopener') }
  const regenerer = () => { ouvrir(); rafraichirDocument(r.id).then(onChange).catch(() => {}) }
  return (
    <tr className="group border-b border-line hover:bg-mint hover:text-mint-on">
      <td className="h-11 px-2.5 align-middle">{dateFr(r.created_at)}</td>
      <td className="px-2.5">{r.document}</td>
      <td className="truncate px-2.5">{sur(r)}{r.commune ? <span className="text-txt-dim group-hover:text-mint-on/75"> · {r.commune}</span> : null}</td>
      <td className="px-2.5">{r.projet || <span className="text-txt-dim group-hover:text-mint-on/75">—</span>}</td>
      <td className="px-2.5">
        {r.etat === 'a_jour'
          ? <Badge ton="vert">À jour</Badge>
          : <Badge ton="ambre">Sources modifiées depuis</Badge>}
      </td>
      <td className="px-2.5">
        <div className="flex justify-end gap-1.5">
          <Bouton niveau="secondaire" ton="vert" className="h-[26px] px-[9px] text-[12px]" onClick={ouvrir}>Ouvrir</Bouton>
          {/* Excel : seulement sur les lignes Bilan ET si l'export existe (sinon absent, pas grisé). */}
          {r.doc_type === 'bilan' && r.excel && (
            <Bouton niveau="secondaire" ton="vert" className="h-[26px] px-[9px] text-[12px]" onClick={ouvrir}>Excel</Bouton>
          )}
          {r.etat === 'modifie' && (
            <Bouton niveau="secondaire" ton="vert" className="h-[26px] px-[9px] text-[12px]" onClick={regenerer}>Régénérer</Bouton>
          )}
        </div>
      </td>
    </tr>
  )
}

function Bibliotheque() {
  const qc = useQueryClient()
  const [actif, setActif] = useState<DocType | null>(null)   // null = « Tous »
  const [limite, setLimite] = useState(200)
  const q = useQuery({ queryKey: ['documents', limite], queryFn: () => listerDocuments(limite) })
  const data = q.data
  const rows = (data?.documents ?? []).filter((r) => actif == null || r.doc_type === actif)
  const refresh = () => qc.invalidateQueries({ queryKey: ['documents'] })
  return (
    <section className="mt-8">
      <div className="mb-3 flex flex-wrap items-center gap-3.5">
        <h2 className="text-[18px] font-semibold text-txt">Mes documents</h2>
        <span className="text-txt-dim">{data?.total ?? 0}</span>
        <div className="ml-auto flex flex-wrap gap-1.5">
          {FILTRES.map((c) => (
            <Chip key={c.label} on={actif === c.type} onClick={() => setActif(c.type)}>{c.label}</Chip>
          ))}
          {/* chip « Tous » dernier à droite (règle gravée). */}
          <Chip on={actif == null} onClick={() => setActif(null)}>Tous</Chip>
        </div>
      </div>

      {rows.length === 0 ? (
        <div className="mt-4 rounded-md border border-dashed border-line-2 p-6 text-center text-txt-dim">
          <b className="mb-1 block text-txt">Aucun document pour l’instant</b>
          Choisissez un document ci-dessus, puis une parcelle. Chaque document généré apparaît ici.
        </div>
      ) : (
        <table className="w-full table-fixed border-collapse">
          <colgroup>
            <col style={{ width: '110px' }} /><col style={{ width: '150px' }} /><col /><col style={{ width: '160px' }} /><col style={{ width: '190px' }} /><col style={{ width: '210px' }} />
          </colgroup>
          <thead>
            <tr className="border-b border-line text-left text-[12px] font-semibold text-txt-mut">
              <th className="px-2.5 py-2">Généré le</th><th className="px-2.5 py-2">Document</th><th className="px-2.5 py-2">Sur</th><th className="px-2.5 py-2">Projet</th><th className="px-2.5 py-2">État</th><th />
            </tr>
          </thead>
          <tbody className="text-[13px]">
            {rows.map((r) => <LigneDoc key={r.id} r={r} onChange={refresh} />)}
          </tbody>
        </table>
      )}

      {/* Sous 200 lignes tout s'affiche ; au-delà, « voir 200 de plus ». */}
      {(data?.reste ?? 0) > 0 && (
        <div className="mt-3 text-center">
          <Bouton niveau="secondaire" ton="vert" onClick={() => setLimite((l) => l + 200)}>
            Voir 200 de plus ({data!.reste} restants)
          </Bouton>
        </div>
      )}
    </section>
  )
}

export function DocumentsView() {
  const [porte, setPorte] = useState<DocCatalogue | null>(null)
  // fermeture propre si l'on quitte la vue pendant qu'une porte est ouverte.
  const mounted = useRef(true)
  useEffect(() => () => { mounted.current = false }, [])
  return (
    <div className="min-w-0 flex-1 overflow-y-auto bg-bg">
      <div className="mx-auto max-w-[1400px] px-6 pb-12 pt-6">
        <h1 className="mb-1 text-[22px] font-bold text-txt">Documents</h1>
        <p className="mb-5 max-w-[64ch] text-txt-dim">
          Huit documents, tous produits depuis les données de la fiche parcelle. Choisissez le document, puis la parcelle, et générez.
        </p>
        <div className="grid grid-cols-4 gap-3 max-[1100px]:grid-cols-2">
          {CATALOGUE.map((d) => (
            <DocCard key={d.key} d={d} onOpen={() => setPorte(d)} />
          ))}
        </div>
        <Bibliotheque />
      </div>
      {porte && <Porte d={porte} onClose={() => setPorte(null)} />}
    </div>
  )
}
