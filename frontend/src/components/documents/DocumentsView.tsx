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
import { Chargement } from '../Loading'
import { ParcelInput } from '../ParcelInput'
import { usePiegeFocus } from '../../lib/usePiegeFocus'
// RECETTE-4 — DestinationSelect retiré de la fenêtre Docs Étude de zone (menu Activité supprimé).
import { BilanEcran } from '../fiche/BilanEcran'
import {
  getFiche, getGabarit,
  docDossierUrl, docBilanUrl, docBilanExcelUrl, docApporteurUrl, docPreDossierUrl, docGabaritUrl, docComparatifUrl, docEtudeZoneUrl,
  docAnalyseAnnonceUrl, docAnalyseAnnonceLienUrl,
  ETUDE_PDF_URL, etudePdfInit,
  listerDocuments, enregistrerDocument, rafraichirDocument,
  type DocType, type DocGenereRow, type EtudePdfIn,
} from '../../lib/api'
import { fmtDateNum, fmtM2, iduComplet } from '../../lib/format'
import { editeurDiffere } from '../../lib/empreinteDoc'
import { useOuvrirDocument } from '../../lib/ouvrirDocument'
import { supprimerDocument, getMoteursConfig } from '../../lib/api'
import { CATALOGUE, USAGES, type DocCatalogue } from './catalogue'

// l'URL du générateur d'une ligne de bibliothèque (régénération à la demande — « Ouvrir »).
function urlDocument(r: Pick<DocGenereRow, 'id' | 'doc_type' | 'idus' | 'rayon_km'>): string | null {
  const i0 = r.idus[0]
  switch (r.doc_type) {
    case 'dossier': return i0 ? docDossierUrl(i0) : null
    case 'bilan': return i0 ? docBilanUrl(i0, r.id) : null
    case 'apporteur': return i0 ? docApporteurUrl(i0) : null
    case 'pre-dossier': return i0 ? docPreDossierUrl(i0) : null
    case 'gabarit': return i0 ? docGabaritUrl(i0) : null
    case 'comparatif': return r.idus.length >= 2 ? docComparatifUrl(r.idus) : null
    case 'etude-zone': return i0 ? docEtudeZoneUrl(i0, r.rayon_km ?? 2) : null
    // ANNONCE-3 — seule l'entrée ADRESSE (IDU) est régénérable depuis « Mes documents » ; l'entrée
    // LIEN n'a pas d'objet LABUSE stable à mémoriser (elle n'est pas inscrite à la bibliothèque).
    case 'analyse-annonce': return i0 ? docAnalyseAnnonceUrl(i0) : null
    default: return null
  }
}


// ECRANS-NOV-1 §4 — une icône de document sobre, commune à toutes les cartes (comme la maquette).
function DocGlyphe() {
  return (
    <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth={1.7}
      strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M6.5 3.5h7L18 8v12.5H6.5z" /><path d="M13.5 3.5V8H18" /><path d="M9 12.5h6M9 15.5h4.5" />
    </svg>
  )
}

// RETOURS-18 (pt 19 / maquette 4b) — ANCIEN FLUX rétabli : la carte ENTIÈRE est cliquable (clic → la
// fenêtre demande l'adresse). Icône + FLÈCHE en tête, titre sur une ligne, description sur EXACTEMENT
// DEUX lignes (cartes alignées) ; au survol, bordure verte. Plus de bouton « Générer » ni de badge « PDF ».
function DocCard({ d, onOpen }: { d: DocCatalogue; onOpen: () => void }) {
  // RETOURS-19 (pt 15) — plus de `h-full` : une carte SEULE dans sa colonne (« Étude de zone ») ne
  // s'étire plus à toute la hauteur de la colonne (les colonnes sont étirées par la grille) ; toutes
  // les cartes gardent la même taille, calée sur leur contenu (desc en 2 lignes fixes).
  return (
    // RETOURS-21 (pt 3) — survol = FOND VERT OPAQUE + texte/icônes SOMBRES (`.hover-fill`, comme les
    // autres survols de l'app), plus un simple contour vert. Le focus suit la règle unique (globale).
    <button onClick={onOpen}
      className="hover-fill group flex w-full flex-col gap-3 rounded-lg border border-line bg-surface-1 p-4 text-left transition-colors duration-quick">
      <div className="flex items-start justify-between">
        <span className="grid h-8 w-8 place-items-center rounded-md border border-line-2 text-mint transition-colors duration-quick">
          <DocGlyphe />
        </span>
        <span aria-hidden className="text-txt-faint transition-colors duration-quick">→</span>
      </div>
      <div className="min-w-0">
        <div className="text-[15px] font-semibold text-txt">{d.nom}</div>
        {/* exactement deux lignes : hauteur minimale fixée + line-clamp, pour que toutes les cartes s'alignent. */}
        <p className="mt-1 line-clamp-2 min-h-[2.4em] text-[13px] leading-snug text-txt-dim">{d.desc}</p>
      </div>
    </button>
  )
}

// ── la parcelle résolue (lit la fiche) : IDU, adresse+CP, zone + surface « à cheval ». ──
// RETOURS-17 — le lien « Fiche → » est RETIRÉ des fenêtres Docs (props onFiche/showFiche supprimées).
function ParcelleResolue({ idu }: { idu: string }) {
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
    </div>
  )
}

// ── la porte (fenêtre centrée) : ✕ / Échap / clic hors fenêtre ferment. ──
// ECRANS-NOV-1 §4 — la porte ne sert plus QUE les documents à saisie SUPPLÉMENTAIRE (Comparatif :
// d'autres parcelles ; Étude de zone : un rayon). `initialIdu` amorce ces saisies avec la parcelle
// déjà choisie en haut de l'écran (on n'a plus à la re-saisir).
function Porte({ d, onClose, initialIdu }: { d: DocCatalogue; onClose: () => void; initialIdu?: string | null }) {
  // FIX-NU3-2 (M-A04) — piège de focus + Échap + restitution au déclencheur sur la modale « document ».
  const dialogRef = useRef<HTMLDivElement | null>(null)
  usePiegeFocus(true, dialogRef, onClose)
  const ouvrirEtude = useApp((s) => s.ouvrirEtude)   // IMPLANTATION-4 (LOT A) — la carte Étude ouvre l'overlay
  const qc = useQueryClient()
  // enregistre la génération dans « Mes documents » (best-effort : la bibliothèque n'empêche jamais
  // de produire le PDF — un compte pilote/non connecté génère sans trace, sans erreur bloquante).
  const enregistrer = (doc_type: DocType, idusCible: string[], rayon_km?: number | null) => {
    enregistrerDocument({ doc_type, idus: idusCible, rayon_km: rayon_km ?? null })
      .then(() => qc.invalidateQueries({ queryKey: ['documents'] }))
      .catch(() => { /* non bloquant */ })
  }
  // variante parcelle / multi / zone — amorcées par la parcelle déjà choisie (ECRANS-NOV-1 §4).
  const [idu, setIdu] = useState<string | null>(initialIdu ?? null)                // parcelle & zone
  const [idus, setIdus] = useState<(string | null)[]>([initialIdu ?? null, null, null])  // multi (2 à 3)
  const [rayon, setRayon] = useState(2)                              // zone : rayon servi, défaut 2
  const [lien, setLien] = useState('')                               // ANNONCE-3 : lien d'annonce (variante annonce)
  const [surfaceHab, setSurfaceHab] = useState('')                   // ESTIMER-PRECISION-1 : surface habitable facultative (variante adresse)
  // RECETTE-4 — menu Activité (sous-destination) retiré de l'Étude de zone (Docs incluse).
  // CHASSE-DONNEES-FIX-1 (suite 2, E-77) — rayons SERVIS (config/moteurs.yaml), plus la liste 1..20 en dur.
  const cfgMot = useQuery({ queryKey: ['moteurs-config'], queryFn: getMoteursConfig, staleTime: 3600_000 })
  const rayonsServis = cfgMot.data?.rayons_etude_zone ?? [0.5, 1, 2, 5]
  const [bilanOuvert, setBilanOuvert] = useState(false)
  // DOCS-FIX-1 (P3/P4) — ouverture propre (fetch + blob + attente + erreur FR), comme le Bilan :
  // plus de window.open qui laisse l'onglet blanc puis affiche du JSON. L'erreur est rendue INLINE
  // dans la porte (modèle FinancierQuestionnaire) ; la porte reste ouverte tant qu'il y a une erreur.
  const { ouvrir, enCours, erreur, progres } = useOuvrirDocument()

  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [onClose])


  // Gabarit : « Absent si calcul incomplet » — on interroge l'outil AVANT de proposer la génération.
  const gab = useQuery({
    queryKey: ['gabarit', idu], queryFn: () => getGabarit(idu!),
    enabled: d.key === 'gabarit' && !!idu, retry: false,
  })
  const gabaritBloque = d.key === 'gabarit' && !!idu && gab.data?.status === 'incomplete'

  // RETOURS-17 — nom du fichier exporté : « <IDU> — <Nom du document>.<ext> » (ex. « 97411000BZ1065
  // — Estimation.pdf »). Le pré-dossier est un ZIP ; le reste des portes ci-dessous est en PDF.
  const extDoc = d.key === 'pre-dossier' ? 'zip' : 'pdf'
  const nomExport = (i: string) => `${iduComplet(i)} — ${d.fichier ?? d.nom}.${extDoc}`

  const generer = async () => {
    if (d.key === 'bilan') {
      // Exception assumée : ouvre l'écran d'hypothèses (qui génère). DOCS-FIX-1 (P7) — le Bilan n'est
      // PLUS inscrit ici (à l'ouverture, même si on annule) : il l'est après GÉNÉRATION réelle, via
      // le callback onGenerated du questionnaire (plus d'entrée « fantôme » qui renverrait 422).
      setBilanOuvert(true)
      return
    }
    if (!idu) return
    // IMPLANTATION-4 (LOT A) — la 9e carte n'exporte plus directement un PDF : elle OUVRE l'écran d'étude
    // complet (overlay M22 + carte intégrée), sur le modèle du Bilan. L'utilisateur configure, choisit son
    // scénario, PUIS « Générer le PDF » depuis l'écran (qui archive côté serveur). Même composant, même API.
    if (d.key === 'etude-faisabilite') {
      ouvrirEtude([idu]); onClose()
      return
    }
    const url =
      d.key === 'dossier' ? docDossierUrl(idu)
      : d.key === 'apporteur' ? docApporteurUrl(idu)
      : d.key === 'pre-dossier' ? docPreDossierUrl(idu)
      : d.key === 'gabarit' ? docGabaritUrl(idu)
      : null
    if (!url) return
    // DOCS-FIX-1 (P3/P4) — on n'inscrit dans « Mes documents » et on ne ferme la porte qu'au SUCCÈS ;
    // sur erreur la porte reste ouverte et affiche le message (plus de ligne pour un doc jamais produit).
    if (await ouvrir(url, d.key, undefined, nomExport(idu))) { enregistrer(d.key as DocType, [idu]); onClose() }
  }

  const idusValides = idus.filter((x): x is string => !!x)
  const placeholder = 'Adresse, IDU ou référence (BW0917)'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[rgba(6,10,8,0.72)] p-4" onClick={onClose}>
      <div ref={dialogRef} role="dialog" aria-modal="true" aria-label={d.nom}
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
            {idu && <ParcelleResolue idu={idu} />}
            {gabaritBloque ? (
              <p className="my-3 border-l-2 border-amber pl-2.5 text-[13px] text-amber">
                Gabarit non calculable sur cette parcelle : donnée réglementaire manquante.
              </p>
            ) : d.explication ? (
              <p className="my-3 border-l-2 border-line-2 pl-2.5 text-[13px] text-txt-dim">{d.explication}</p>
            ) : <div className="my-3" />}
            {erreur && <p className="my-3 border-l-2 border-amber pl-2.5 text-[13px] text-amber">{erreur}</p>}
            <Bouton niveau="primaire" ton="vert" className="w-full" disabled={!idu || gabaritBloque || !!enCours} onClick={generer}>
              {enCours ? <Chargement variant="inline" accent="courant" label="Génération…" /> : d.cta}
            </Bouton>
            {/* NU5-FIX-1 (C-F11) — barre de progression VISIBLE pendant la génération (le Dossier met
                ~14 s) : estimation fondée sur le temps écoulé, jamais un simple spinner figé. */}
            {enCours && (
              <div className="mt-2" aria-hidden>
                <div className="h-1 w-full overflow-hidden rounded-full bg-surface-3">
                  <div className="h-full rounded-full bg-mint transition-[width] duration-200"
                       style={{ width: `${progres}%` }} />
                </div>
                <p className="mt-1 text-[11px] text-txt-mut">Génération du document en cours…</p>
              </div>
            )}
          </div>
        )}

        {/* ── variante 2–3 parcelles (Comparatif) ── */}
        {d.kind === 'multi' && (
          <div>
            {/* RETOURS-17 — « (2 à 3) » → « (jusqu'à 3) » ; le 3ᵉ champ porte le MÊME libellé que les deux autres. */}
            <div className="mb-2 font-semibold text-txt">Quelles parcelles ? (jusqu’à 3)</div>
            <div className="grid gap-2">
              <ParcelInput placeholder={placeholder} withCarte={false} autoFocus onPick={(i) => setIdus((a) => [i, a[1], a[2]])} />
              <ParcelInput placeholder={placeholder} withCarte={false} onPick={(i) => setIdus((a) => [a[0], i, a[2]])} />
              <ParcelInput placeholder={placeholder} withCarte={false} onPick={(i) => setIdus((a) => [a[0], a[1], i])} />
            </div>
            {d.explication && <p className="my-3 border-l-2 border-line-2 pl-2.5 text-[13px] text-txt-dim">{d.explication}</p>}
            {erreur && <p className="my-3 border-l-2 border-amber pl-2.5 text-[13px] text-amber">{erreur}</p>}
            {/* RETOURS-18 (pt 20) — marge NORMALE entre le dernier champ et le bouton (sans explication,
                le bouton collait au 3ᵉ champ). */}
            <Bouton niveau="primaire" ton="vert" className="mt-3 w-full" disabled={idusValides.length < 2 || !!enCours}
              onClick={async () => { if (await ouvrir(docComparatifUrl(idusValides), 'comparatif', undefined, `${idusValides.map(iduComplet).join(', ')} — ${d.fichier ?? d.nom}.pdf`)) { enregistrer('comparatif', idusValides); onClose() } }}>
              {enCours ? <Chargement variant="inline" accent="courant" label="Génération…" /> : d.cta}
            </Bouton>
          </div>
        )}

        {/* ── variante zone (Étude de zone) : parcelle + rayon en km au −/+ (1..20, défaut 2) ── */}
        {d.kind === 'zone' && (
          <div>
            <div className="mb-2 font-semibold text-txt">Autour d’une parcelle</div>
            <ParcelInput placeholder={placeholder} withCarte={false} autoFocus onPick={setIdu} />
            {idu && <ParcelleResolue idu={idu} />}
            <div className="mb-2 mt-2 text-[13px] font-medium text-txt-mut">Rayon autour de la parcelle</div>
            {/* CHASSE-DONNEES-FIX-1 (E-77) — rayons SERVIS (discrets), plus un stepper 1..20 divergent du back. */}
            <div className="flex items-center gap-1.5">
              {rayonsServis.map((r) => (
                <Bouton key={r} niveau={rayon === r ? 'primaire' : 'secondaire'} ton="vert"
                  aria-pressed={rayon === r} onClick={() => setRayon(r)}>{String(r).replace('.', ',')} km</Bouton>
              ))}
            </div>
            {/* RECETTE-4 — le menu « Activité (destination) » est retiré de la fenêtre Docs Étude de zone
                (comme de l'outil et du PDF). */}
            {d.explication && <p className="my-3 border-l-2 border-line-2 pl-2.5 text-[13px] text-txt-dim">{d.explication}</p>}
            {erreur && <p className="my-3 border-l-2 border-amber pl-2.5 text-[13px] text-amber">{erreur}</p>}
            <Bouton niveau="primaire" ton="vert" className="w-full" disabled={!idu || !!enCours}
              onClick={async () => { if (idu && await ouvrir(docEtudeZoneUrl(idu, rayon), 'etude-zone', undefined, nomExport(idu))) { enregistrer('etude-zone', [idu], rayon); onClose() } }}>
              {enCours ? <Chargement variant="inline" accent="courant" label="Génération…" /> : d.cta}
            </Bouton>
          </div>
        )}

        {/* ── ANNONCE-3 — variante annonce (Analyse d'annonce) : une adresse OU un lien, comme l'outil.
            Adresse → rapport parcelle (/analyse-annonce/{idu}.pdf), inscrit à « Mes documents » (IDU
            stable). Lien → rapport commune (/analyse-annonce.pdf?url=…), Radar d'abord puis fetch côté
            serveur, le même message d'échec qu'à l'outil (pas d'inscription : pas d'objet stable). ── */}
        {d.kind === 'annonce' && (
          <div>
            <div className="mb-2 font-semibold text-txt">Une adresse</div>
            <ParcelInput placeholder={placeholder} withCarte={false} autoFocus onPick={setIdu} />
            {idu && <ParcelleResolue idu={idu} />}
            {/* ESTIMER-PRECISION-1 — surface habitable facultative : si renseignée, le total du rapport
                l'utilise (« surface saisie »), à l'identique de l'écran de l'outil (écran == PDF == Doc). */}
            {idu && (
              <div className="mt-2 flex items-center gap-2">
                <label className="text-[13px] text-txt-dim" htmlFor="doc-surface-hab">Surface habitable (m²)</label>
                <input id="doc-surface-hab" type="number" min={1} step={1} inputMode="numeric"
                  className="h-9 w-24 rounded-md border border-line-2 bg-surface-3 px-2 text-[13px] text-txt-hi placeholder:text-txt-mut focus:outline-none"
                  placeholder="facultatif" value={surfaceHab} onChange={(e) => setSurfaceHab(e.target.value)} />
              </div>
            )}
            <Bouton niveau="primaire" ton="vert" className="mt-2 w-full" disabled={!idu || !!enCours}
              onClick={async () => { const sh = surfaceHab.trim() ? Math.round(Number(surfaceHab)) : null; const shv = sh != null && Number.isFinite(sh) && sh > 0 ? sh : null; if (idu && await ouvrir(docAnalyseAnnonceUrl(idu, shv), 'analyse-annonce', undefined, nomExport(idu))) { enregistrer('analyse-annonce', [idu]); onClose() } }}>
              {enCours === 'analyse-annonce' ? <Chargement variant="inline" accent="courant" label="Génération…" /> : d.cta}
            </Bouton>
            <div className="my-3 flex items-center gap-2 text-[13px] text-txt-mut">
              <span className="h-px flex-1 bg-line-2" />OU<span className="h-px flex-1 bg-line-2" />
            </div>
            <div className="mb-2 font-semibold text-txt">Un lien d’annonce</div>
            <input
              className="h-10 w-full rounded-md border border-line-2 bg-surface-3 px-3 text-[13px] text-txt-hi placeholder:text-txt-mut focus:outline-none"
              placeholder="https://www.leboncoin.fr/ventes_immobilieres/…"
              value={lien} onChange={(e) => setLien(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && lien.trim() && !enCours) void ouvrir(docAnalyseAnnonceLienUrl(lien.trim()), 'analyse-annonce', undefined, `${d.fichier ?? d.nom}.pdf`).then((ok) => { if (ok) onClose() }) }}
            />
            {d.explication && <p className="my-3 border-l-2 border-line-2 pl-2.5 text-[13px] text-txt-dim">{d.explication}</p>}
            {erreur && <p className="my-3 border-l-2 border-amber pl-2.5 text-[13px] text-amber">{erreur}</p>}
            <Bouton niveau="secondaire" ton="vert" className="w-full" disabled={!lien.trim() || !!enCours}
              onClick={async () => { if (await ouvrir(docAnalyseAnnonceLienUrl(lien.trim()), 'analyse-annonce', undefined, `${d.fichier ?? d.nom}.pdf`)) onClose() }}>
              {enCours ? <Chargement variant="inline" accent="courant" label="Génération…" /> : 'Générer depuis le lien'}
            </Bouton>
          </div>
        )}
      </div>

      {/* Bilan (exception assumée) : le bilan promoteur pré-rempli sur la parcelle (BILAN-1). Il
          s'enregistre lui-même dans « Mes documents » via /bilan/{idu}/generer ; on se contente de
          rafraîchir la liste (plus d'inscription en double ni d'entrée fantôme). */}
      {bilanOuvert && idu && (
        <div onClick={(e) => e.stopPropagation()}>
          <BilanEcran idu={idu} onGenerated={() => qc.invalidateQueries({ queryKey: ['documents'] })}
            onClose={() => { setBilanOuvert(false); onClose() }} />
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
  { label: 'Étude de zone', type: 'etude-zone' }, { label: 'Étude de faisabilité', type: 'etude-faisabilite' },
  { label: 'Estimer un bien', type: 'analyse-annonce' },   // RECETTE-4 — libellé (type interne inchangé)
]
// FIX-NU3-2 (I-TPS-04) — « Document généré le … » en heure de La Réunion (le dérivé getDate()/getMonth()
// local rendait J-1 à l'ouest d'UTC). Un seul formateur pour toute l'app (lib/format, fuseau figé).
const dateFr = (iso: string) => fmtDateNum(iso)

function sur(r: DocGenereRow): string {
  if (r.doc_type === 'etude-zone') return `Rayon ${r.rayon_km ?? 2} km autour de ${iduComplet(r.idus[0] ?? '')}`
  if (r.doc_type === 'comparatif' || r.doc_type === 'etude-faisabilite') return r.idus.join(' · ')
  return iduComplet(r.idus[0] ?? '')
}

// IMPLANTATION-3 — la recette d'une Étude de faisabilité = la config archivée (POST), jamais une URL GET.
function etudeInitDe(r: DocGenereRow): RequestInit | null {
  const cfg = (r.hypotheses as { config?: EtudePdfIn } | null)?.config
  return cfg ? etudePdfInit(cfg) : null
}

function LigneDoc({ r, onChange }: { r: DocGenereRow; onChange: () => void }) {
  const setToast = useApp((s) => s.setToast)
  const ouvrirEtude = useApp((s) => s.ouvrirEtude)   // ETUDE-FIABLE-1 (LOT B2) — rouvrir l'ÉCRAN sur la révision
  // DOCS-FIX-1 (P3/P4) — ouverture propre (fetch + blob) ; l'erreur part au toast produit (« une
  // action ne tombe jamais dans le vide ») plutôt que d'ouvrir un onglet blanc puis du JSON brut.
  const { ouvrir: ouvrirDoc, enCours } = useOuvrirDocument(setToast)
  const [confirmSuppr, setConfirmSuppr] = useState(false)
  const busy = enCours === String(r.id)
  // RETOURS-17 — nom du fichier exporté depuis « Mes documents » : « <IDU> — <Nom du document>.<ext> ».
  const nomRow = (ext: string) => {
    const idus = (r.idus ?? []).filter(Boolean).map(iduComplet)
    return `${idus.length ? `${idus.join(', ')} — ` : ''}${r.document}.${ext}`
  }
  const nomPdf = () => nomRow(r.doc_type === 'pre-dossier' ? 'zip' : 'pdf')
  const ouvrir = () => {
    // ETUDE-FIABLE-1 (LOT B2) — ROUVRIR une étude = afficher sa RÉVISION à l'écran (sans recalcul : l'écran
    // relit la révision via la config archivée). Repli PDF si la config n'est pas archivée (anciens docs).
    if (r.doc_type === 'etude-faisabilite') {
      const cfg = (r.hypotheses as { config?: EtudePdfIn } | null)?.config
      if (cfg?.idus?.length) { ouvrirEtude(cfg.idus, cfg as unknown as Record<string, unknown>); return }
      const i = etudeInitDe(r); if (i) void ouvrirDoc(ETUDE_PDF_URL, String(r.id), i, nomPdf()); return
    }
    const u = urlDocument(r); if (u) void ouvrirDoc(u, String(r.id), undefined, nomPdf())
  }
  const regenerer = async () => {
    if (r.doc_type === 'etude-faisabilite') {
      const i = etudeInitDe(r); if (i && await ouvrirDoc(ETUDE_PDF_URL, String(r.id), i, nomPdf())) rafraichirDocument(r.id).then(onChange).catch(() => {}); return
    }
    const u = urlDocument(r); if (u && await ouvrirDoc(u, String(r.id), undefined, nomPdf())) rafraichirDocument(r.id).then(onChange).catch(() => {})
  }
  // DOCS-FIX-1 (P6) — « Supprimer » : la route DELETE et supprimerDocument existaient, mais AUCUN
  // bouton ne les appelait. Deux temps (Supprimer → Confirmer) pour éviter la suppression accidentelle.
  const supprimer = () => {
    supprimerDocument(r.id)
      .then(() => { setToast('Document retiré de « Mes documents ».'); onChange() })
      .catch(() => setToast('Suppression échouée — réessayez.'))
  }
  // RETOURS-16 (point 5) — `shrink-0` + `whitespace-nowrap` : chaque bouton garde sa taille et son
  // libellé sur une ligne ; combiné au conteneur `flex-nowrap` + colonne élargie, les 4 boutons
  // (Ouvrir/Excel/Régénérer/Supprimer) restent sur UNE SEULE LIGNE, alignés à droite, sur toute ligne.
  const btn = 'h-[26px] shrink-0 whitespace-nowrap px-[9px] text-[12px]'
  // CHASSE-DOCS-FIX-1 (Lot 5.1) — « Sources modifiées depuis » s'allume AUSSI quand l'éditeur (Bilan/
  // Étude) a changé ses saisies depuis la génération : on compare l'empreinte STOCKÉE AVEC LE DOCUMENT
  // (serveur, `hypotheses._empreinte` — cross-poste) à l'empreinte de l'éditeur vivant (local).
  const empServeur = (r.hypotheses as { _empreinte?: string } | null)?._empreinte
  const modifie = r.etat !== 'a_jour' || editeurDiffere(r.doc_type, r.idus?.[0] ?? null, empServeur)
  // CHASSE-DOCS-FIX-1 — survol DISCRET (fond légèrement éclairci) : l'aplat vert vif rendait « Ouvrir »
  // (bouton vert) invisible et le badge illisible. Boutons et badge gardent leurs couleurs.
  return (
    <tr className="group border-b border-line hover:bg-surface-3">
      <td className="h-11 px-2.5 align-middle">{dateFr(r.created_at)}</td>
      <td className="px-2.5">{r.document}</td>
      <td className="truncate px-2.5">{sur(r)}{r.commune ? <span className="text-txt-dim"> · {r.commune}</span> : null}</td>
      <td className="px-2.5">{r.projet || <span className="text-txt-dim">—</span>}</td>
      <td className="px-2.5">
        {modifie
          ? <Badge ton="ambre">Sources modifiées depuis</Badge>
          : <Badge ton="vert">À jour</Badge>}
      </td>
      <td className="px-2.5">
        {/* RETOURS-16 (point 5, remplace CHASSE-DOCS-FIX-1) — les boutons d'une ligne restent sur UNE
            SEULE LIGNE, alignés à droite (`flex-nowrap justify-end`), quelle que soit la ligne. La
            colonne actions est élargie (colgroup, 320 px) pour tenir les 4 boutons sans chevaucher le
            badge « Sources modifiées depuis » (colonne distincte, place conservée). */}
        <div className="flex flex-nowrap justify-end gap-1.5">
          <Bouton niveau="secondaire" ton="vert" className={btn} disabled={busy} onClick={ouvrir}>{busy ? <Chargement variant="inline" accent="courant" label="Ouverture…" /> : 'Ouvrir'}</Bouton>
          {/* Excel : seulement sur les lignes Bilan ET si l'export existe (sinon absent, pas grisé). */}
          {r.doc_type === 'bilan' && r.excel && r.idus[0] && (
            <Bouton niveau="secondaire" ton="vert" className={btn} disabled={busy}
              onClick={() => void ouvrirDoc(docBilanExcelUrl(r.idus[0], r.id), `xls-${r.id}`, undefined, nomRow('xlsx'))}>Excel</Bouton>
          )}
          {modifie && (
            <Bouton niveau="secondaire" ton="vert" className={btn} disabled={busy} onClick={regenerer}>Régénérer</Bouton>
          )}
          {confirmSuppr ? (
            <>
              <Bouton niveau="primaire" ton="danger" className={btn} onClick={supprimer}>Confirmer</Bouton>
              <Bouton niveau="lien" ton="vert" className={btn} onClick={() => setConfirmSuppr(false)}>Annuler</Bouton>
            </>
          ) : (
            <Bouton niveau="secondaire" ton="danger" className={btn} onClick={() => setConfirmSuppr(true)}>Supprimer</Bouton>
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
            {/* RETOURS-16 (point 5) — colonne actions élargie 270 → 320 px : les 4 boutons tiennent
                sur une seule ligne sans rogner le badge « Sources modifiées depuis » (col. 190 px). */}
            <col style={{ width: '110px' }} /><col style={{ width: '150px' }} /><col /><col style={{ width: '160px' }} /><col style={{ width: '190px' }} /><col style={{ width: '320px' }} />
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
  // RETOURS-18 (pt 19) — ANCIEN FLUX : plus de barre « parcelle choisie une fois » en haut ni de
  // phrase d'intro. La carte ENTIÈRE ouvre la fenêtre (Porte) qui demande l'adresse/la parcelle.
  const [porte, setPorte] = useState<DocCatalogue | null>(null)
  const ouvrirEtude = useApp((s) => s.ouvrirEtude)
  return (
    <div className="min-w-0 flex-1 overflow-y-auto bg-bg">
      <div className="mx-auto max-w-[1400px] px-6 pb-12 pt-6">
        <h1 className="mb-6 text-[22px] font-bold text-txt">Documents</h1>
        {/* QUATRE COLONNES par usage (4b) ; « Mes documents » reste en dessous (inchangé). */}
        <div className="grid grid-cols-4 gap-4 max-[1100px]:grid-cols-2">
          {USAGES.map((u) => (
            <div key={u.key} className="flex flex-col gap-3">
              <h2 className="label-caps text-[11px] text-txt-dim">{u.titre}</h2>
              {CATALOGUE.filter((d) => d.usage === u.key).map((d) => (
                // IMPLANTATION-4 — l'Étude de faisabilité ouvre directement l'écran d'étude (assiette vide à
                // composer) ; les autres ouvrent leur fenêtre (Porte) qui demande la parcelle/l'adresse.
                <DocCard key={d.key} d={d}
                  onOpen={() => (d.key === 'etude-faisabilite' ? ouvrirEtude([]) : setPorte(d))} />
              ))}
            </div>
          ))}
        </div>
        <Bibliotheque />
      </div>
      {porte && <Porte d={porte} onClose={() => setPorte(null)} />}
    </div>
  )
}
