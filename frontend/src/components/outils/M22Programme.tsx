import { useEffect, useMemo, useRef, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useApp } from '../../store/useApp'
import { getMoteursConfig, postEtude, ETUDE_PDF_URL, etudePdfInit, ApiError } from '../../lib/api'
import type { EtudeIn, EtudePayload, EtudeScenario } from '../../lib/api'
import { fmtInt, fmtDec } from '../../lib/format'
import { Bouton } from '../ui/Bouton'
import { Badge } from '../ui/Badge'
import { Case } from '../ui/Case'
import { Reinitialiser } from '../ui/Reinitialiser'
import { EntreeParcelle } from './EntreeParcelle'
import { ParcelInput } from '../ParcelInput'
import { ErrorState } from '../States'
import { Chargement } from '../Loading'
import { useOuvrirDocument } from '../../lib/ouvrirDocument'
import { PlanMasseSvg } from './PlanMasseSvg'

/** M22 · ÉTUDE DE FAISABILITÉ — l'étude de faisabilité EN LIGNE. Deux états : (1) configuration
 *  (assiette 1–8 parcelles, type, objectif, programme, stationnement) et (2) scénarios (jusqu'à 3
 *  cartes, plan masse sur la carte, sections repliables). UN SEUL moteur, servi par POST /modules/etude.
 *  AUCUN CALCUL ICI : l'écran n'affiche que le payload de l'API et filtre le GeoJSON par couche cochée.
 *
 *  IMPLANTATION-4 — l'Étude a QUITTÉ les Outils : elle vit dans un overlay Docs (EtudeEcran), et depuis
 *  la suite v4 elle n'a PLUS DE CARTE. En mode `embedded`, le MÊME composant tourne avec (1) une sélection
 *  LOCALE (il ne touche plus au `msel` global, partagé avec l'Assemblage), (2) la MISE EN PAGE de la
 *  maquette v4 (plein écran, en-tête ← Fermer / Réinitialiser, état 1 = configuration centrée, état 2 =
 *  scénarios à gauche + chiffres clés + PLAN MASSE DESSINÉ au centre (PlanMasseSvg, plus de carte) +
 *  sections repliables dessous), (3) un pont « Bilan de ce scénario » (onBilan) et sa fermeture (onClose).
 *  Hors `embedded`, le comportement historique (une colonne, carte globale via setModuleMap) est intact —
 *  les tests Etude.test.tsx le rendent ainsi. Aucun second calcul : le plan masse réutilise `actif.geojson`. */

const ASM_MAX_DEFAUT = 8
const TYPES = ['T2', 'T3', 'T4'] as const

type Objectif = 'equilibre' | 'plus_logements' | 'plus_surface' | 'plus_simple'
const OBJECTIFS: { key: Objectif; label: string }[] = [
  { key: 'equilibre', label: 'Équilibre' },
  { key: 'plus_logements', label: 'Plus de logements' },
  { key: 'plus_surface', label: 'Plus de surface habitable' },
  { key: 'plus_simple', label: 'Projet plus simple' },
]

// Couches activables de la PLANCHE (maquette) → GROUPE `<g id>` du SVG serveur, + `kinds` du GeoJSON
// pour le plan schématique de repli. Parcelle/voie/assiette/zone/espaces libres/accès toujours visibles.
const ALWAYS = new Set(['parcelle', 'voie', 'assiette', 'zone', 'espace_libre', 'acces'])
const COUCHES: { key: string; label: string; groupe: string; kinds: string[]; defaut: boolean }[] = [
  { key: 'batiment', label: 'Bâtiment', groupe: 'g-batiment', kinds: ['batiment_emprise', 'noyau', 'coursive'], defaut: true },
  { key: 'modules', label: 'Modules', groupe: 'g-modules', kinds: ['module'], defaut: false },
  { key: 'places', label: 'Places', groupe: 'g-places', kinds: ['place'], defaut: true },
  { key: 'allee', label: 'Allée', groupe: 'g-allee', kinds: ['allee'], defaut: true },
  { key: 'cotes', label: 'Cotes', groupe: 'g-cotes', kinds: [], defaut: true },
  { key: 'voisins', label: 'Voisins', groupe: 'g-voisins', kinds: [], defaut: true },
  { key: 'ppr', label: 'PPR', groupe: 'g-ppr', kinds: ['ppr_rouge', 'ppr_bleue'], defaut: true },
]
const COUCHES_DEFAUT = Object.fromEntries(COUCHES.map((c) => [c.key, c.defaut])) as Record<string, boolean>

function statutCourt(s: string): string {
  if (s.startsWith('exploitable')) return 'Exploitable'
  if (s === 'à compléter') return 'À compléter'
  if (s === 'ne tient pas') return 'Ne tient pas'
  return 'Simulation impossible'
}
function statutTon(s: string): 'vert' | 'ambre' | 'rouge' {
  if (s.startsWith('exploitable')) return 'vert'
  if (s === 'à compléter') return 'ambre'
  return 'rouge'
}

/** Pilule segmentée (maquette .seg). Une option `bientot` est grisée, non cliquable. */
function Seg<T extends string>({ value, onChange, options }: {
  value: T; onChange: (v: T) => void
  options: { key: T; label: string; bientot?: boolean }[]
}) {
  return (
    <div className="flex flex-wrap gap-1">
      {options.map((o) => {
        const on = o.key === value
        if (o.bientot) return (
          <span key={o.key} className="cursor-not-allowed rounded border border-dashed border-line-2 px-2 py-1 text-[10px] text-txt-dim">
            {o.label} · bientôt
          </span>
        )
        return (
          <button key={o.key} type="button" onClick={() => onChange(o.key)}
            className={`rounded border px-2 py-1 text-[10.5px] transition-colors duration-quick ${
              on ? 'border-mint bg-mint font-semibold text-mint-on' : 'border-line-2 text-txt-mut hover:border-mint/60'}`}>
            {o.label}
          </button>
        )
      })}
    </div>
  )
}

const Lbl = ({ children, aide }: { children: React.ReactNode; aide?: string }) => (
  <p className="mt-2 flex items-center gap-1 text-[9px] uppercase tracking-wide text-txt-dim">
    {children}
    {aide && <span title={aide} className="cursor-help text-txt-dim">ⓘ</span>}
  </p>
)

/** Programme d'un scénario, passé au pont « Bilan de ce scénario » (logements par type + SDP). */
export type EtudeProgramme = { ref: string; logements: number; par_type: Record<string, number>; sdp_m2: number; shab_m2?: number | null }

export function M22({ embedded = false, initialIdus, onBilan, onClose }: {
  embedded?: boolean
  initialIdus?: string[]
  onBilan?: (prog: EtudeProgramme) => void
  onClose?: () => void
} = {}) {
  const { msel, setMsel, setModuleMap, parcelPrefill, setParcelPrefill, select } = useApp()
  const cfgMot = useQuery({ queryKey: ['moteurs-config'], queryFn: getMoteursConfig, staleTime: 3600_000 })
  const ASM_MAX = cfgMot.data?.assemblage_max_ecran ?? ASM_MAX_DEFAUT

  // Sélection : LOCALE en mode embedded (overlay Docs — ne touche pas au msel global de l'Assemblage) ;
  // sinon le msel du store (carte globale, clic-carte, idiome historique).
  const [selLocal, setSelLocal] = useState<string[]>(embedded ? (initialIdus ?? []) : [])
  const sel = embedded ? selLocal : msel
  const setSel = embedded ? setSelLocal : setMsel

  // configuration (état 1)
  const [objectif, setObjectif] = useState<Objectif>('equilibre')
  const [progMode, setProgMode] = useState<'propose' | 'saisi'>('propose')
  const [lignes, setLignes] = useState<Record<string, { nombre: string; surface: string }>>(
    { T2: { nombre: '', surface: '' }, T3: { nombre: '', surface: '' }, T4: { nombre: '', surface: '' } })
  // hypothèses modifiables (état 2) — surcharges, vides = valeurs LABUSE
  const [hyp, setHyp] = useState<{ profondeur_m: string; coef: string; surfaces: Record<string, string> }>(
    { profondeur_m: '', coef: '', surfaces: { T2: '', T3: '', T4: '' } })
  // scénarios (état 2)
  const [tab, setTab] = useState(0)
  const [couches, setCouches] = useState<Record<string, boolean>>(COUCHES_DEFAUT)
  const [max8, setMax8] = useState(false)
  // « Modifier » (embedded) : revient à la configuration (état 1) SANS jeter les scénarios déjà servis
  // — « Générer » les régénère. Hors embedded, l'état 1/2 reste piloté par la seule présence de `data`.
  const [editing, setEditing] = useState(false)

  const run = useMutation({ mutationFn: (body: EtudeIn) => postEtude(body) })
  // export PDF du SCÉNARIO AFFICHÉ (porte 1) : POST /modules/etude/pdf avec la config courante + le
  // scénario sélectionné. Le PDF lit la même réponse que l'écran (jamais un 2e calcul).
  const pdf = useOuvrirDocument()
  const data: EtudePayload | undefined = run.data
  const scenarios = data?.scenarios ?? []
  const actif: EtudeScenario | undefined = scenarios[Math.min(tab, Math.max(0, scenarios.length - 1))]

  // Message d'erreur de génération : une entrée refusée (400, ex. « parcelles non contiguës ») affiche
  // le motif EXACT du moteur, SANS bouton réessayer (relancer la même assiette échouerait pareil) ; une
  // panne quelconque garde le message générique + réessayer.
  const erreur400 = run.error instanceof ApiError && run.error.status === 400 ? run.error.detail : null
  const erreurMsg = erreur400 ?? "L'étude a échoué — réessayez."

  // GeoJSON du plan masse filtré par couche cochée (affichage, PAS un calcul) — réutilisé par la carte
  // intégrée (embedded) OU poussé à la carte globale (setModuleMap, hors embedded).
  const planFc = useMemo(() => {
    if (!actif) return null
    const kinds = new Set<string>()
    COUCHES.forEach((c) => { if (couches[c.key]) c.kinds.forEach((k) => kinds.add(k)) })
    return {
      type: 'FeatureCollection' as const,
      features: actif.geojson.features.filter((f) => {
        const k = (f.properties as { kind?: string } | null)?.kind ?? ''
        return ALWAYS.has(k) || kinds.has(k)
      }),
    }
  }, [actif, couches])

  // Planche serveur (SVG « façon archi ») : groupes `<g id="g-…">` à masquer selon les couches décochées.
  const groupesCaches = useMemo(
    () => COUCHES.filter((c) => !couches[c.key]).map((c) => c.groupe),
    [couches])

  // ouvrir l'Étude FERME la fiche en cours (le clic-carte compose l'assiette) — seulement hors overlay.
  useEffect(() => { if (!embedded) select(null) }, [])  // eslint-disable-line react-hooks/exhaustive-deps
  // porte fiche/Assemblage → Étude (mode carte globale) : la parcelle amorce l'assiette (parcelPrefill).
  // En embedded, l'assiette est amorcée par initialIdus (sélection locale) — pas de parcelPrefill.
  useEffect(() => {
    if (!embedded && parcelPrefill) { setMsel([parcelPrefill]); setParcelPrefill(null) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [parcelPrefill])

  const ajouter = (idu: string) => {
    const i = idu.trim().toUpperCase()
    if (!i || sel.includes(i)) return
    if (sel.length >= ASM_MAX) { setMax8(true); return }
    setMax8(false); setSel([...sel, i])
  }
  // garde-fou : un clic-carte (MapView programme) pousse dans msel → on plafonne aussi côté store.
  // Toute modification de l'assiette PÉRIME les scénarios : on revient à l'état configuration.
  useEffect(() => {
    if (sel.length > ASM_MAX) { setSel(sel.slice(0, ASM_MAX)); setMax8(true) }
    run.reset()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sel])
  // quitter l'outil VIDE son état (carte globale) — seulement hors overlay (embedded : sélection locale,
  // rien à nettoyer dans le store).
  useEffect(() => () => { if (!embedded) { setMsel([]); setModuleMap({ idus: [], extra: null }) } }, [])  // eslint-disable-line react-hooks/exhaustive-deps

  // ── carte GLOBALE (hors embedded) : plan masse filtré, sinon surbrillance de l'assiette ──
  const wantFit = useRef(false)
  useEffect(() => { wantFit.current = true }, [data, tab])
  useEffect(() => {
    if (embedded) return   // en overlay, c'est PlanMasseSvg qui dessine planFc — jamais la carte de fond
    if (!actif) { setModuleMap({ idus: sel, extra: null }); return }
    setModuleMap({ idus: [], extra: planFc, fit: wantFit.current })
    wantFit.current = false
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, tab, couches, sel, planFc])

  const corpsBody = (): EtudeIn => {
    const body: EtudeIn = { idus: sel, objectif }
    if (progMode === 'saisi') {
      const ls = TYPES.map((t) => ({ type: t, nombre: parseInt(lignes[t].nombre || '0', 10) || 0,
                                     surface_m2: parseFloat(lignes[t].surface || '0') || undefined }))
        .filter((l) => l.nombre > 0)
      body.programme = { mode: 'saisi', lignes: ls }
    }
    const surf: Record<string, number> = {}
    TYPES.forEach((t) => { const v = parseFloat(hyp.surfaces[t] || ''); if (v > 0) surf[t] = v })
    const h: EtudeIn['hypotheses'] = {}
    if (parseFloat(hyp.profondeur_m || '') > 0) h!.profondeur_m = parseFloat(hyp.profondeur_m)
    if (parseFloat(hyp.coef || '') > 0) h!.coef_plancher_habitable = parseFloat(hyp.coef)
    if (Object.keys(surf).length) h!.surfaces = surf
    if (Object.keys(h!).length) body.hypotheses = h
    return body
  }

  const resetAll = () => {
    setSel([]); setMax8(false); run.reset(); setTab(0); setCouches(COUCHES_DEFAUT); setEditing(false)
    setObjectif('equilibre'); setProgMode('propose')
    setLignes({ T2: { nombre: '', surface: '' }, T3: { nombre: '', surface: '' }, T4: { nombre: '', surface: '' } })
    setHyp({ profondeur_m: '', coef: '', surfaces: { T2: '', T3: '', T4: '' } })
  }
  const revenirLabuse = () => {
    setHyp({ profondeur_m: '', coef: '', surfaces: { T2: '', T3: '', T4: '' } })
    run.mutate({ idus: sel, objectif, ...(progMode === 'saisi' ? { programme: corpsBody().programme } : {}) })
  }

  // pont « Bilan de ce scénario » (embedded) : programme du scénario affiché (logements par type + SDP).
  const ouvrirBilanScenario = () => {
    if (!actif || !onBilan) return
    onBilan({ ref: actif.ref, logements: actif.resume.logements, par_type: actif.programme.par_type,
              sdp_m2: actif.resume.sdp_m2, shab_m2: actif.programme.shab_estimee_m2 })
  }

  // ── contenu (commun aux deux modes) ─────────────────────────────────────
  const contenu = (
    <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto pr-0.5">
      {(sel.length > 0 || data) && (
        <div className="flex justify-end"><Reinitialiser onReset={resetAll} label="Nouvelle étude" /></div>)}
      <p className="text-[11px] leading-relaxed text-txt-mut">
        Ce que le terrain peut recevoir en collectif : implantation dessinée, capacité et contrôles des règles du PLU.
      </p>

      {/* ───────── ÉTAT 1 — CONFIGURATION ───────── */}
      {!data && (
        <>
          <Lbl>Terrain — 1 à {ASM_MAX} parcelles contiguës</Lbl>
          <EntreeParcelle source={null} onPick={(i) => ajouter(i)} />
          <div className="flex flex-wrap gap-1">
            {sel.map((i) => (
              <button key={i} data-etude-chip onClick={() => { setSel(sel.filter((x) => x !== i)); setMax8(false) }}
                className="min-h-7 rounded-full border border-mint/60 px-2 py-0.5 font-mono text-[11px] text-mint transition-colors duration-quick hover:bg-mint/10">
                {i.slice(8)} ×
              </button>
            ))}
            {sel.length === 0 && <span className="text-[11px] text-txt-dim">aucune parcelle — saisissez ou cliquez la carte</span>}
          </div>
          {max8 && <p className="text-[10.5px] text-st-creuser">{ASM_MAX} parcelles maximum.</p>}

          <Lbl>Type de projet</Lbl>
          <Seg value="collectif" onChange={() => {}}
            options={[{ key: 'collectif', label: 'Collectif' },
                      { key: 'maisons', label: 'Maisons groupées', bientot: true },
                      { key: 'lotissement', label: 'Lotissement', bientot: true }]} />

          <Lbl aide="L'objectif oriente le choix du meilleur scénario (répartition, hauteur, forme).">Objectif</Lbl>
          <Seg value={objectif} onChange={setObjectif} options={OBJECTIFS} />

          <Lbl aide="« LABUSE propose » : le moteur teste des répartitions et garde la meilleure pour l'objectif. « Je saisis » : il cherche une implantation qui contient votre programme, ou dit pourquoi ça ne tient pas.">Programme</Lbl>
          <Seg value={progMode} onChange={setProgMode}
            options={[{ key: 'propose', label: 'LABUSE propose' }, { key: 'saisi', label: 'Je saisis mon programme' }]} />
          {progMode === 'saisi' && (
            <div className="flex flex-col gap-1.5 rounded-lg border border-line-2 bg-surface-2 px-2.5 py-2">
              {TYPES.map((t) => (
                <div key={t} className="flex items-center gap-2 text-[11px]">
                  <span className="w-6 font-mono text-txt-mut">{t}</span>
                  <input inputMode="numeric" placeholder="nombre" value={lignes[t].nombre}
                    onChange={(e) => setLignes({ ...lignes, [t]: { ...lignes[t], nombre: e.target.value } })}
                    className="w-16 rounded border border-line-2 bg-surface px-1.5 py-1 text-[11px]" />
                  <input inputMode="numeric" placeholder="m² moy." value={lignes[t].surface}
                    onChange={(e) => setLignes({ ...lignes, [t]: { ...lignes[t], surface: e.target.value } })}
                    className="w-20 rounded border border-line-2 bg-surface px-1.5 py-1 text-[11px]" />
                </div>
              ))}
            </div>
          )}

          <Lbl>Stationnement</Lbl>
          <Seg value="aerien" onChange={() => {}}
            options={[{ key: 'aerien', label: 'Aérien' }, { key: 'ouvrage', label: 'En ouvrage', bientot: true }]} />

          <Lbl>Terrain étudié</Lbl>
          <Seg value="libere" onChange={() => {}}
            options={[{ key: 'libere', label: 'Terrain libéré' }, { key: 'bati', label: 'En gardant le bâti', bientot: true }]} />

          <Bouton niveau="primaire" ton="vert" data-etude-generer className="mt-3 w-full"
            disabled={sel.length === 0 || run.isPending}
            onClick={() => { setTab(0); run.mutate(corpsBody()) }}>
            {run.isPending ? 'Génération…' : 'Générer les scénarios'}
          </Bouton>
          {run.isError && <ErrorState message={erreurMsg} retry={erreur400 ? undefined : () => run.mutate(corpsBody())} />}
        </>
      )}

      {/* ───────── ÉTAT 2 — SCÉNARIOS ───────── */}
      {data && (
        <>
          <p className="text-[10px] text-txt-dim">
            {sel.map((i) => i.slice(8)).join(' · ')} · collectif · {OBJECTIFS.find((o) => o.key === data.entrees.objectif)?.label.toLowerCase()} · aérien
          </p>

          {scenarios.length === 0 ? (
            <div className="rounded-lg border border-st-ecartee/50 bg-st-ecartee/[0.09] px-3 py-2.5 text-[11.5px] leading-snug text-st-ecartee">
              <b>{statutCourt(data.statut_global)}.</b> {data.message}
            </div>
          ) : (
            <>
              <Lbl>Scénarios trouvés</Lbl>
              {scenarios.map((s, i) => (
                <button key={s.ref} data-etude-carte onClick={() => setTab(i)}
                  className={`rounded-lg border px-2.5 py-2 text-left transition-colors duration-quick ${
                    i === tab ? 'border-mint bg-mint/[0.08]' : 'border-line-2 hover:border-mint/50'}`}>
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-semibold">{s.ref} · {s.forme.replace('_', ' ')}</span>
                    <Badge ton={statutTon(s.statut_etude)}>{statutCourt(s.statut_etude)}</Badge>
                  </div>
                  <div className="mt-0.5 text-[10.5px] text-txt">{s.resume.logements} logements · {s.niveaux_label} · {s.resume.places} places</div>
                  <div className="mt-0.5 text-[9.5px] text-txt-dim">
                    Contrôles : {s.controles_compte.reussi} réussis · {s.controles_compte.echoue} échoués · {s.controles_compte.non_effectue} non effectués
                  </div>
                </button>
              ))}

              {actif && (
                <>
                  {/* onglets A/B/C du plan masse */}
                  {scenarios.length > 1 && (
                    <div className="mt-1 flex gap-1">
                      {scenarios.map((s, i) => (
                        <button key={s.ref} onClick={() => setTab(i)}
                          className={`rounded border px-2.5 py-1 text-[11px] ${i === tab ? 'border-mint bg-mint font-semibold text-mint-on' : 'border-line-2 text-txt-mut'}`}>
                          {s.ref}
                        </button>
                      ))}
                    </div>
                  )}

                  {/* 3 chiffres clés */}
                  <div className="mt-1 grid grid-cols-3 gap-1.5">
                    {[['logements', actif.resume.logements], ['places dessinées', actif.resume.places],
                      ['m² SDP du scénario', fmtInt(actif.resume.sdp_m2)]].map(([lbl, val]) => (
                      <div key={lbl} className="rounded border border-line-2 px-1 py-1.5 text-center">
                        <b className="block text-[15px] text-txt">{val}</b>
                        <span className="text-[8.5px] text-txt-dim">{lbl}</span>
                      </div>
                    ))}
                  </div>

                  {/* couches activables du plan masse */}
                  <details className="border-t border-line-2 pt-1">
                    <summary className="cursor-pointer text-[10px] font-semibold text-txt-mut">Couches du plan masse</summary>
                    <div className="mt-1 grid grid-cols-2 gap-x-2 gap-y-1">
                      {COUCHES.map((c) => (
                        <Case key={c.key} label={<span className="text-[10.5px]">{c.label}</span>} checked={couches[c.key]}
                          onChange={(e) => setCouches({ ...couches, [c.key]: (e.target as HTMLInputElement).checked })} />
                      ))}
                    </div>
                  </details>

                  <Section titre="Programme">
                    <Ligne l="Répartition" v={Object.entries(actif.programme.par_type).map(([t, n]) => `${t} ×${n}`).join(' · ')}
                      s={data.entrees.programme_mode === 'saisi' ? 'Projet saisi' : 'Estimé · choisie par le moteur, modifiable'} />
                    {actif.programme.mixite_applicable && (
                      <Ligne l="Logements aidés imposés" v={`${actif.programme.logements_aides_imposes}`} s="Sourcé · PLU mixité" />)}
                    <Ligne l="SHAB estimée" v={`${fmtInt(actif.programme.shab_estimee_m2)} m²`}
                      s={`ratio SHAB/SDP ${fmtDec(actif.programme.ratio_shab_sdp, 2)}`} />
                  </Section>

                  <Section titre="Distribution par niveau">
                    {actif.distribution_niveaux.map((d) => (
                      <Ligne key={d.niveau} l={`Niveau ${d.niveau}`}
                        v={Object.entries(d.par_type).map(([t, n]) => `${t} ×${n}`).join(' · ') || '—'}
                        s={`SDP du scénario ${fmtInt(d.sdp_m2)} m²`} />
                    ))}
                  </Section>

                  <Section titre="Stationnement et accès">
                    <Ligne l="Places dessinées · imposées"
                      v={`${actif.stationnement.places} · ${actif.stationnement.places_imposees ?? '—'}`}
                      s={actif.stationnement.note?.raison ?? 'Estimé · place 2,5 × 5 m, allée 5 m'} />
                    {actif.stationnement.acces && (
                      <Ligne l="Accès véhicule" v={`à ${actif.stationnement.acces.distance_angle_m} m d'un angle`} s={actif.stationnement.acces.note} />)}
                  </Section>

                  <Section titre={`Contrôles (${actif.controles_compte.reussi} réussis · ${actif.controles_compte.non_effectue} non effectués)`}>
                    {actif.controles.map((c) => (
                      <div key={c.nom} className="border-b border-surface py-1 text-[10.5px]">
                        <span className={c.resultat === 'Réussi' ? 'font-semibold text-mint' : c.resultat === 'Échoué' ? 'font-semibold text-st-ecartee' : 'text-txt-dim'}>
                          {c.resultat}
                        </span>
                        <span className="text-txt"> · {c.nom}</span>
                        {c.resultat === 'Réussi' && c.citation && (
                          <span title={c.citation} className="ml-1 cursor-help text-txt-dim">ⓘ</span>)}
                      </div>
                    ))}
                  </Section>

                  <Section titre="Hypothèses modifiables">
                    <HypLigne l="Profondeur de bâtiment (m)" val={hyp.profondeur_m}
                      defaut={data.hypotheses.profondeur_m}
                      onChange={(v) => setHyp({ ...hyp, profondeur_m: v })} />
                    {TYPES.map((t) => (
                      <HypLigne key={t} l={`Surface moyenne ${t} (m²)`} val={hyp.surfaces[t]}
                        defaut={data.hypotheses.surfaces[t]}
                        onChange={(v) => setHyp({ ...hyp, surfaces: { ...hyp.surfaces, [t]: v } })} />
                    ))}
                    <HypLigne l="Plancher → habitable" val={hyp.coef} defaut={data.hypotheses.coef_plancher_habitable}
                      onChange={(v) => setHyp({ ...hyp, coef: v })} />
                    <div className="mt-2 flex gap-1.5">
                      <Bouton niveau="secondaire" ton="vert" className="flex-1" disabled={run.isPending}
                        onClick={() => run.mutate(corpsBody())}>Recalculer</Bouton>
                      <Bouton niveau="lien" ton="vert" onClick={revenirLabuse}>Valeurs LABUSE</Bouton>
                    </div>
                  </Section>

                  {/* pont « Bilan de ce scénario » (embedded) : ouvre le Bilan pré-rempli AVEC le programme
                      du scénario affiché (logements par type + SDP), étiqueté « depuis l'Étude ». */}
                  {embedded && onBilan && (
                    <Bouton niveau="secondaire" ton="vert" data-etude-bilan className="mt-2 w-full"
                      disabled={!actif} onClick={ouvrirBilanScenario}>
                      Bilan de ce scénario →
                    </Bouton>
                  )}

                  {/* porte 1 : exporter le SCÉNARIO AFFICHÉ (config courante + onglet actif) en PDF
                      « Étude de faisabilité ». Même document que la 9e carte Docs. */}
                  <Bouton niveau={embedded ? 'primaire' : 'secondaire'} ton="vert" data-etude-pdf className="mt-2 w-full"
                    disabled={!!pdf.enCours}
                    onClick={() => pdf.ouvrir(ETUDE_PDF_URL, 'etude-pdf',
                      etudePdfInit({ ...corpsBody(), scenario_ref: actif.ref }))}>
                    {pdf.enCours ? <Chargement variant="inline" accent="courant" label="Génération…" />
                      : (embedded ? 'Générer le PDF ↓' : 'Étude de faisabilité (PDF) ↓')}
                  </Bouton>
                  {pdf.erreur && <p className="text-[10.5px] text-st-creuser">{pdf.erreur}</p>}

                  <button data-etude-gabarit onClick={() => { if (sel[0]) { useApp.getState().setParcelPrefill(sel[0]) } ; useApp.getState().setModule('gabarit') }}
                    className="mt-1 self-start text-[11px] text-txt-dim underline decoration-txt-dim/40 underline-offset-2 transition-colors duration-quick hover:text-mint">
                    Voir en 3D dans le gabarit →
                  </button>
                </>
              )}
            </>
          )}
        </>
      )}
    </div>
  )

  // Hors overlay (Outils historique) : une seule colonne, la carte est celle de fond.
  if (!embedded) return contenu

  // ── Overlay Docs (maquette v4, plein écran, SANS carte) ──────────────────────────────────────
  // En-tête ← Fermer / Réinitialiser ; état 1 = configuration centrée ; état 2 = scénarios à gauche,
  // chiffres clés + PLAN MASSE DESSINÉ (PlanMasseSvg) au centre, sections repliables sur deux colonnes.
  const refsCourts = sel.map((i) => i.slice(8))
  const objActuel = data ? data.entrees.objectif : objectif
  const objLbl = OBJECTIFS.find((o) => o.key === objActuel)?.label ?? 'Équilibre'
  const etat2 = !!data && !editing
  const sub = etat2
    ? `${refsCourts.join('-')} · Collectif · ${objLbl} · Aérien · Terrain libéré`
    : `${refsCourts.length ? refsCourts.join(' · ') : 'Nouvelle étude'}${data?.entrees.commune ? ` — ${data.entrees.commune}` : ''}`

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {/* en-tête : ← Fermer (gauche) · titre + Modifier · Réinitialiser (droite) */}
      <div className="sticky top-0 z-10 flex shrink-0 items-center gap-3 border-b border-line bg-surface-2 px-5 py-3">
        <Bouton niveau="secondaire" ton="vert" onClick={() => onClose?.()}>← Fermer</Bouton>
        <div className="min-w-0 leading-tight">
          <div className="text-[16px] font-bold text-txt">Étude de faisabilité</div>
          <div className="truncate text-[12px] text-txt-mut">
            {sub}
            {etat2 && (
              <button onClick={() => setEditing(true)}
                className="ml-2 text-mint underline decoration-mint/40 underline-offset-2">Modifier</button>
            )}
          </div>
        </div>
        <div className="flex-1" />
        <Reinitialiser onReset={resetAll} />
      </div>

      {/* ───────── ÉTAT 1 — CONFIGURATION (centrée) ───────── */}
      {!etat2 && (
        <div className="mx-auto w-full max-w-[760px] overflow-y-auto px-6 py-8">
          <p className="mb-6 text-[13px] text-txt-mut">
            Ce que le terrain peut recevoir en collectif : implantation dessinée, capacité et contrôles des règles du PLU.
          </p>

          <div className="mb-6">
            <Lbl>Terrain — 1 à {ASM_MAX} parcelles contiguës</Lbl>
            <ParcelInput dataAttr="etude-parcelle" withCarte={false} onPick={(i) => ajouter(i)}
              placeholder="Ajouter une parcelle : adresse, IDU ou référence (AW0451)" />
            <div className="mt-2 flex flex-wrap gap-1">
              {sel.map((i) => (
                <button key={i} data-etude-chip onClick={() => { setSel(sel.filter((x) => x !== i)); setMax8(false) }}
                  className="min-h-7 rounded-full border border-mint/60 px-2 py-0.5 font-mono text-[11px] text-mint transition-colors duration-quick hover:bg-mint/10">
                  {i.slice(8)} ×
                </button>
              ))}
              {sel.length === 0 && <span className="text-[11px] text-txt-dim">aucune parcelle — saisissez une référence ci-dessus</span>}
            </div>
            {max8 && <p className="mt-1 text-[10.5px] text-st-creuser">{ASM_MAX} parcelles maximum.</p>}
            <p className="mt-2 text-[11.5px] text-txt-mut">
              Pour choisir les parcelles sur la carte, passez par{' '}
              <button onClick={() => useApp.getState().setModule('assemblage')}
                className="text-mint underline decoration-mint/40 underline-offset-2">l'outil Assemblage</button>.
            </p>
            <div className="mt-3 grid grid-cols-3 gap-2">
              <div className="rounded-lg border border-line bg-surface-2 px-3 py-2">
                <b className="block text-[15px] text-txt">{sel.length} parcelle{sel.length > 1 ? 's' : ''}</b>
                <span className="text-[11px] text-txt-dim">{sel.length > 1 ? 'Contiguës, assiette fusionnée' : 'Assiette'}</span>
              </div>
              {data && (<>
                <div className="rounded-lg border border-line bg-surface-2 px-3 py-2">
                  <b className="block text-[15px] text-txt">{fmtInt(data.terrain.contenance_totale_m2)} m²</b>
                  <span className="text-[11px] text-txt-dim">Contenance cadastrale</span>
                </div>
                <div className="rounded-lg border border-line bg-surface-2 px-3 py-2">
                  <b className="block text-[15px] text-txt">{data.entrees.zone}</b>
                  <span className="text-[11px] text-txt-dim">Zone PLU</span>
                </div>
              </>)}
            </div>
          </div>

          <div className="mb-6">
            <Lbl>Type de projet</Lbl>
            <Seg value="collectif" onChange={() => {}}
              options={[{ key: 'collectif', label: 'Collectif' },
                        { key: 'maisons', label: 'Maisons groupées', bientot: true },
                        { key: 'lotissement', label: 'Lotissement', bientot: true }]} />
          </div>

          <div className="mb-6">
            <Lbl aide="L'objectif oriente le choix du meilleur scénario (répartition, hauteur, forme).">Objectif</Lbl>
            <Seg value={objectif} onChange={setObjectif} options={OBJECTIFS} />
          </div>

          <div className="mb-6">
            <Lbl aide="« LABUSE propose » : le moteur teste des répartitions et garde la meilleure pour l'objectif. « Je saisis » : il cherche une implantation qui contient votre programme, ou dit pourquoi ça ne tient pas.">Programme</Lbl>
            <Seg value={progMode} onChange={setProgMode}
              options={[{ key: 'propose', label: 'LABUSE propose' }, { key: 'saisi', label: 'Je saisis mon programme' }]} />
            {progMode === 'saisi' && (
              <div className="mt-2 flex flex-col gap-1.5 rounded-lg border border-line-2 bg-surface-2 px-2.5 py-2">
                {TYPES.map((t) => (
                  <div key={t} className="flex items-center gap-2 text-[11px]">
                    <span className="w-6 font-mono text-txt-mut">{t}</span>
                    <input inputMode="numeric" placeholder="nombre" value={lignes[t].nombre}
                      onChange={(e) => setLignes({ ...lignes, [t]: { ...lignes[t], nombre: e.target.value } })}
                      className="w-16 rounded border border-line-2 bg-surface px-1.5 py-1 text-[11px]" />
                    <input inputMode="numeric" placeholder="m² moy." value={lignes[t].surface}
                      onChange={(e) => setLignes({ ...lignes, [t]: { ...lignes[t], surface: e.target.value } })}
                      className="w-20 rounded border border-line-2 bg-surface px-1.5 py-1 text-[11px]" />
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="mb-6">
            <Lbl>Stationnement</Lbl>
            <Seg value="aerien" onChange={() => {}}
              options={[{ key: 'aerien', label: 'Aérien' }, { key: 'ouvrage', label: 'En ouvrage', bientot: true }]} />
          </div>

          <div className="mb-6">
            <Lbl>Terrain étudié</Lbl>
            <Seg value="libere" onChange={() => {}}
              options={[{ key: 'libere', label: 'Terrain libéré' }, { key: 'bati', label: 'En gardant le bâti', bientot: true }]} />
          </div>

          <Bouton niveau="primaire" ton="vert" data-etude-generer className="w-full"
            disabled={sel.length === 0 || run.isPending}
            onClick={() => { setTab(0); setEditing(false); run.mutate(corpsBody()) }}>
            {run.isPending ? 'Génération…' : 'Générer les scénarios'}
          </Bouton>
          {run.isError && <div className="mt-2"><ErrorState message={erreurMsg} retry={erreur400 ? undefined : () => run.mutate(corpsBody())} /></div>}
        </div>
      )}

      {/* ───────── ÉTAT 2 — SCÉNARIOS ───────── */}
      {etat2 && (scenarios.length === 0 ? (
        <div className="p-6">
          <div className="rounded-lg border border-st-ecartee/50 bg-st-ecartee/[0.09] px-4 py-3 text-[12px] leading-snug text-st-ecartee">
            <b>{statutCourt(data!.statut_global)}.</b> {data!.message}
          </div>
        </div>
      ) : (
        <div className="grid min-h-0 flex-1 grid-cols-[330px_1fr] overflow-hidden">
          {/* colonne gauche — scénarios (deux statuts) + actions du scénario */}
          <aside className="flex flex-col gap-2 overflow-y-auto border-r border-line bg-surface-2 p-4">
            {scenarios.map((s, i) => (
              <button key={s.ref} data-etude-carte onClick={() => setTab(i)}
                className={`rounded-lg border px-3 py-2.5 text-left transition-colors duration-quick ${
                  i === tab ? 'border-mint bg-mint/[0.08]' : 'border-line-2 hover:border-mint/50'}`}>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[12px] font-semibold">{s.ref} · {s.forme.replace('_', ' ')}</span>
                  <Badge ton={statutTon(s.statut_etude)}>{statutCourt(s.statut_etude)}</Badge>
                </div>
                <div className="mt-1 text-[12px] text-txt">{s.resume.logements} logements · {s.resume.places} places</div>
                <div className="mt-0.5 text-[10.5px] text-txt-dim">
                  {s.controles_compte.reussi} réussis · {s.controles_compte.echoue} échoués · {s.controles_compte.non_effectue} non effectués
                </div>
              </button>
            ))}

            <h4 className="mt-3 text-[10px] font-semibold uppercase tracking-wide text-txt-dim">Ce scénario</h4>
            <div className="flex flex-col gap-2">
              <Bouton niveau="primaire" ton="vert" data-etude-pdf disabled={!!pdf.enCours || !actif}
                onClick={() => actif && pdf.ouvrir(ETUDE_PDF_URL, 'etude-pdf', etudePdfInit({ ...corpsBody(), scenario_ref: actif.ref }))}>
                {pdf.enCours ? <Chargement variant="inline" accent="courant" label="Génération…" /> : 'Générer le PDF ↓'}
              </Bouton>
              {onBilan && (
                <Bouton niveau="secondaire" ton="vert" data-etude-bilan disabled={!actif} onClick={ouvrirBilanScenario}>
                  Bilan de ce scénario →
                </Bouton>
              )}
              <Bouton niveau="secondaire" ton="vert" data-etude-gabarit disabled={!actif}
                onClick={() => { if (sel[0]) useApp.getState().setParcelPrefill(sel[0]); useApp.getState().setModule('gabarit') }}>
                Voir en 3D dans le gabarit →
              </Bouton>
            </div>
            {pdf.erreur && <p className="text-[10.5px] text-st-creuser">{pdf.erreur}</p>}
            <p className="mt-3 border-t border-line pt-3 text-[11px] leading-snug text-txt-dim">
              Pré-faisabilité indicative, à faire confirmer par un architecte. Ni étude d'architecte, ni preuve de conformité.
            </p>
          </aside>

          {/* centre — 4 chiffres clés + plan masse dessiné + sections repliables */}
          <section className="flex min-h-0 flex-col gap-3 overflow-y-auto p-5">
            {actif && (<>
              <div className="grid grid-cols-4 gap-2">
                <Key v={String(actif.resume.logements)} l="logements"
                  em={Object.entries(actif.programme.par_type).map(([t, n]) => `${t} ×${n}`).join(' · ')} />
                <Key v={String(actif.resume.places)} l="places dessinées"
                  em={`/ ${actif.stationnement.places_imposees ?? '—'} imposées`} />
                <Key v={`${fmtInt(actif.resume.sdp_m2)} m²`} l="SDP du scénario" />
                <Key v={actif.niveaux_label} l="niveaux" />
              </div>

              <div className="rounded-lg border border-line bg-surface-2 p-3">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <b className="text-[12px] text-txt">Plan masse — scénario {actif.ref}</b>
                  <div className="flex flex-wrap gap-1">
                    {COUCHES.map((c) => (
                      <button key={c.key} data-etude-couche={c.key}
                        onClick={() => setCouches({ ...couches, [c.key]: !couches[c.key] })}
                        className={`rounded-full border px-2.5 py-0.5 text-[11px] transition-colors duration-quick ${
                          couches[c.key] ? 'border-mint text-txt' : 'border-line-2 text-txt-dim'}`}>
                        {c.label}
                      </button>
                    ))}
                  </div>
                </div>
                <PlanMasseSvg fc={planFc} svg={actif.planche_svg} groupesCaches={groupesCaches} />
                {/* la planche serveur porte SA propre légende ; on ne montre celle-ci qu'en repli schématique. */}
                {!actif.planche_svg && (
                  <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-txt-dim">
                    <Leg c="transparent" b="#DC2626" dash>Limite des parcelles</Leg>
                    <Leg c="#E8EDEA">Bâtiment</Leg>
                    <Leg c="#0F1311" b="#8A948E">Place 2,5 × 5 m</Leg>
                    <Leg c="#2E3631">Allée</Leg>
                    <Leg c="#F59E0B">Accès</Leg>
                  </div>
                )}
              </div>

              <div className="grid grid-cols-2 gap-2">
                <Section titre="Programme" sous={data!.entrees.programme_mode === 'saisi' ? 'Projet saisi' : 'LABUSE propose'} open>
                  <Ligne l="Répartition" v={Object.entries(actif.programme.par_type).map(([t, n]) => `${t} ×${n}`).join(' · ')}
                    s={data!.entrees.programme_mode === 'saisi' ? 'Projet saisi' : 'Estimé · choisi par le moteur, modifiable'} />
                  {actif.programme.mixite_applicable && (
                    <Ligne l="Logements aidés imposés" v={`${actif.programme.logements_aides_imposes}`} s="Sourcé · PLU mixité" />)}
                  <Ligne l="SHAB estimée" v={`${fmtInt(actif.programme.shab_estimee_m2)} m²`}
                    s={`ratio SHAB/SDP ${fmtDec(actif.programme.ratio_shab_sdp, 2)}`} />
                </Section>

                <Section titre="Contrôles"
                  sous={`${actif.controles_compte.reussi} réussis · ${actif.controles_compte.non_effectue} non effectués`} open>
                  {actif.controles.map((c) => (
                    <div key={c.nom} className="flex items-center justify-between gap-2 border-b border-line py-1.5 text-[11px] last:border-0">
                      <span className="text-txt-mut">{c.nom}</span>
                      <span className={c.resultat === 'Réussi' ? 'font-semibold text-mint'
                        : c.resultat === 'Échoué' ? 'font-semibold text-st-ecartee' : 'text-txt-dim'}>
                        {c.resultat}
                        {c.resultat === 'Réussi' && c.citation && (
                          <span title={c.citation} className="ml-1 cursor-help text-txt-dim">ⓘ</span>)}
                      </span>
                    </div>
                  ))}
                </Section>

                <Section titre="Distribution par niveau" sous={`${actif.distribution_niveaux.length} niveaux`}>
                  {actif.distribution_niveaux.map((d) => (
                    <Ligne key={d.niveau} l={`Niveau ${d.niveau}`}
                      v={Object.entries(d.par_type).map(([t, n]) => `${t} ×${n}`).join(' · ') || '—'}
                      s={`SDP du scénario ${fmtInt(d.sdp_m2)} m²`} />
                  ))}
                </Section>

                <Section titre="Stationnement et accès" sous={`${actif.stationnement.places} places`}>
                  <Ligne l="Places dessinées · imposées"
                    v={`${actif.stationnement.places} · ${actif.stationnement.places_imposees ?? '—'}`}
                    s={actif.stationnement.note?.raison ?? 'Estimé · place 2,5 × 5 m, allée 5 m'} />
                  {actif.stationnement.acces && (
                    <Ligne l="Accès véhicule" v={`à ${actif.stationnement.acces.distance_angle_m} m d'un angle`} s={actif.stationnement.acces.note} />)}
                </Section>

                <Section titre="Hypothèses modifiables" sous="modifiables">
                  <HypLigne l="Profondeur de bâtiment (m)" val={hyp.profondeur_m} defaut={data!.hypotheses.profondeur_m}
                    onChange={(v) => setHyp({ ...hyp, profondeur_m: v })} />
                  {TYPES.map((t) => (
                    <HypLigne key={t} l={`Surface moyenne ${t} (m²)`} val={hyp.surfaces[t]} defaut={data!.hypotheses.surfaces[t]}
                      onChange={(v) => setHyp({ ...hyp, surfaces: { ...hyp.surfaces, [t]: v } })} />
                  ))}
                  <HypLigne l="Plancher → habitable" val={hyp.coef} defaut={data!.hypotheses.coef_plancher_habitable}
                    onChange={(v) => setHyp({ ...hyp, coef: v })} />
                  <div className="mt-2 flex gap-1.5">
                    <Bouton niveau="secondaire" ton="vert" className="flex-1" disabled={run.isPending}
                      onClick={() => run.mutate(corpsBody())}>Recalculer</Bouton>
                    <Bouton niveau="lien" ton="vert" onClick={revenirLabuse}>Valeurs LABUSE</Bouton>
                  </div>
                </Section>

                {data!.regles.lignes.length > 0 && (
                  <Section titre="Règles et sources" sous={`PLU ${data!.regles.zone}`}>
                    {data!.regles.lignes.map((r) => (
                      <div key={r.nom} className="flex items-start justify-between gap-2 border-b border-line py-1.5 text-[11px] last:border-0">
                        <span className="text-txt-mut">{r.nom}</span>
                        <span className="text-right font-semibold text-txt">
                          {r.valeur != null ? `${r.valeur}${r.unite ? ` ${r.unite}` : ''}` : 'non modélisée'}
                          {r.article && (
                            <span className="block text-[9px] font-normal text-txt-dim">{r.article}{r.page_pdf ? ` · p.${r.page_pdf}` : ''}</span>)}
                        </span>
                      </div>
                    ))}
                  </Section>
                )}
              </div>
            </>)}
          </section>
        </div>
      ))}
    </div>
  )
}

/** Un chiffre clé (état 2) : valeur en gros, libellé, détail optionnel (ex. répartition par type). */
function Key({ v, l, em }: { v: string; l: string; em?: string }) {
  return (
    <div className="rounded-lg border border-line bg-surface-2 px-3 py-2.5">
      <b className="block text-[22px] font-bold leading-none text-txt">{v}</b>
      <span className="mt-1 block text-[11.5px] text-txt-dim">{l}</span>
      {em && <span className="mt-0.5 block text-[10.5px] text-txt-dim">{em}</span>}
    </div>
  )
}

/** Entrée de légende du plan masse (pastille + libellé). */
function Leg({ c, b, dash, children }: { c: string; b?: string; dash?: boolean; children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <i aria-hidden className="inline-block h-2.5 w-3 rounded-sm"
        style={{ background: c, border: b ? `${dash ? '1.5px dashed' : '1px solid'} ${b}` : undefined }} />
      {children}
    </span>
  )
}

function Section({ titre, sous, open, children }: { titre: string; sous?: string; open?: boolean; children: React.ReactNode }) {
  return (
    <details open={open} className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2">
      <summary className="flex cursor-pointer items-center gap-2 text-[11px] font-semibold text-txt">
        {titre}{sous && <small className="font-normal text-txt-dim">{sous}</small>}
      </summary>
      <div className="mt-1">{children}</div>
    </details>
  )
}

function Ligne({ l, v, s }: { l: string; v: string; s?: string }) {
  return (
    <div className="border-b border-surface py-1">
      <div className="text-[9px] text-txt-dim">{l}</div>
      <div className="text-[11px] font-semibold text-txt">{v}</div>
      {s && <div className="text-[9px] text-txt-dim">{s}</div>}
    </div>
  )
}

function HypLigne({ l, val, defaut, onChange }: { l: string; val: string; defaut: number; onChange: (v: string) => void }) {
  return (
    <div className="flex items-center justify-between gap-2 border-b border-surface py-1">
      <span className="text-[10.5px] text-txt-mut">{l}</span>
      <input inputMode="decimal" value={val} placeholder={fmtDec(defaut, 2)} onChange={(e) => onChange(e.target.value)}
        className="w-20 rounded border border-line-2 bg-surface px-1.5 py-1 text-right text-[11px]" />
    </div>
  )
}
