import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useApp } from '../../store/useApp'
import { getMoteursConfig, postEtude } from '../../lib/api'
import type { EtudeIn, EtudePayload, EtudeScenario } from '../../lib/api'
import { fmtInt } from '../../lib/format'
import { Bouton } from '../ui/Bouton'
import { Badge } from '../ui/Badge'
import { Case } from '../ui/Case'
import { Reinitialiser } from '../ui/Reinitialiser'
import { EntreeParcelle } from './EntreeParcelle'
import { ErrorState } from '../States'

/** M22 · ÉTUDE DE FAISABILITÉ (IMPLANTATION-2) — l'étude de faisabilité EN LIGNE.
 *  Deux états : (1) configuration (assiette 1–8 parcelles, type, objectif, programme, stationnement)
 *  et (2) scénarios (jusqu'à 3 cartes, plan masse sur la carte, sections repliables). UN SEUL moteur,
 *  servi par POST /modules/etude. AUCUN CALCUL ICI : l'écran n'affiche que le payload de l'API et
 *  filtre le GeoJSON par couche cochée (affichage, pas calcul). Remplace l'ancien onglet Faisabilité
 *  porté dans l'outil ; le verrou « 17 outils » tient (même clé `programme`). */

const ASM_MAX_DEFAUT = 8
const TYPES = ['T2', 'T3', 'T4'] as const

type Objectif = 'equilibre' | 'plus_logements' | 'plus_surface' | 'plus_simple'
const OBJECTIFS: { key: Objectif; label: string }[] = [
  { key: 'equilibre', label: 'Équilibre' },
  { key: 'plus_logements', label: 'Plus de logements' },
  { key: 'plus_surface', label: 'Plus de surface habitable' },
  { key: 'plus_simple', label: 'Projet plus simple' },
]

// Couches activables du plan masse → `kind` du GeoJSON servi. Parcelle/voie/assiette TOUJOURS visibles.
const ALWAYS = new Set(['parcelle', 'voie', 'assiette'])
const COUCHES: { key: string; label: string; kinds: string[]; defaut: boolean }[] = [
  { key: 'batiments', label: 'Bâtiments', kinds: ['batiment_emprise'], defaut: true },
  { key: 'modules', label: 'Modules logements', kinds: ['module', 'noyau', 'coursive'], defaut: false },
  { key: 'places', label: 'Places', kinds: ['place'], defaut: true },
  { key: 'allees', label: 'Allées', kinds: ['allee'], defaut: true },
  { key: 'acces', label: 'Accès', kinds: ['acces'], defaut: true },
  { key: 'reculs', label: 'Reculs', kinds: ['zone'], defaut: true },
  { key: 'ppr', label: 'PPR', kinds: ['ppr_rouge', 'ppr_bleue'], defaut: true },
  { key: 'libres', label: 'Espaces libres', kinds: ['espace_libre'], defaut: true },
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

export function M22() {
  const { msel, setMsel, setModuleMap, parcelPrefill, setParcelPrefill, select } = useApp()
  const cfgMot = useQuery({ queryKey: ['moteurs-config'], queryFn: getMoteursConfig, staleTime: 3600_000 })
  const ASM_MAX = cfgMot.data?.assemblage_max_ecran ?? ASM_MAX_DEFAUT

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

  const run = useMutation({ mutationFn: (body: EtudeIn) => postEtude(body) })
  const data: EtudePayload | undefined = run.data
  const scenarios = data?.scenarios ?? []
  const actif: EtudeScenario | undefined = scenarios[Math.min(tab, Math.max(0, scenarios.length - 1))]

  // ouvrir l'Étude FERME la fiche en cours (le clic-carte compose l'assiette, cf. MapView programme).
  useEffect(() => { select(null) }, [])  // eslint-disable-line react-hooks/exhaustive-deps
  // porte fiche/Assemblage → Étude : la parcelle amorce l'assiette (idiome parcelPrefill).
  useEffect(() => {
    if (parcelPrefill) { setMsel([parcelPrefill]); setParcelPrefill(null) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [parcelPrefill])

  const ajouter = (idu: string) => {
    const i = idu.trim().toUpperCase()
    if (!i || msel.includes(i)) return
    if (msel.length >= ASM_MAX) { setMax8(true); return }
    setMax8(false); setMsel([...msel, i])
  }
  // garde-fou : un clic-carte (MapView programme) pousse dans msel → on plafonne aussi côté store.
  useEffect(() => {
    if (msel.length > ASM_MAX) { setMsel(msel.slice(0, ASM_MAX)); setMax8(true) }
    // toute modification de l'assiette PÉRIME les scénarios : on revient à l'état configuration.
    run.reset()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [msel])
  // quitter l'outil VIDE son état (assiette + plan masse), comme l'Assemblage (GB-010).
  useEffect(() => () => { setMsel([]); setModuleMap({ idus: [], extra: null }) }, [])  // eslint-disable-line react-hooks/exhaustive-deps

  // ── carte : plan masse (état 2) filtré par couche cochée, sinon surbrillance de l'assiette ──
  const wantFit = useRef(false)
  useEffect(() => { wantFit.current = true }, [data, tab])
  useEffect(() => {
    if (!actif) { setModuleMap({ idus: msel, extra: null }); return }
    const kinds = new Set<string>()
    COUCHES.forEach((c) => { if (couches[c.key]) c.kinds.forEach((k) => kinds.add(k)) })
    const fc = {
      type: 'FeatureCollection',
      features: actif.geojson.features.filter((f) => {
        const k = (f.properties as { kind?: string } | null)?.kind ?? ''
        return ALWAYS.has(k) || kinds.has(k)
      }),
    }
    setModuleMap({ idus: [], extra: fc, fit: wantFit.current })
    wantFit.current = false
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, tab, couches, msel])

  const corpsBody = (): EtudeIn => {
    const body: EtudeIn = { idus: msel, objectif }
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
    setMsel([]); setMax8(false); run.reset(); setTab(0); setCouches(COUCHES_DEFAUT)
    setObjectif('equilibre'); setProgMode('propose')
    setLignes({ T2: { nombre: '', surface: '' }, T3: { nombre: '', surface: '' }, T4: { nombre: '', surface: '' } })
    setHyp({ profondeur_m: '', coef: '', surfaces: { T2: '', T3: '', T4: '' } })
  }
  const revenirLabuse = () => {
    setHyp({ profondeur_m: '', coef: '', surfaces: { T2: '', T3: '', T4: '' } })
    run.mutate({ idus: msel, objectif, ...(progMode === 'saisi' ? { programme: corpsBody().programme } : {}) })
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto pr-0.5">
      {(msel.length > 0 || data) && (
        <div className="flex justify-end"><Reinitialiser onReset={resetAll} label="Nouvelle étude" /></div>)}
      <p className="text-[11px] leading-relaxed text-txt-mut">
        Ce que le terrain peut recevoir en collectif, dessiné et contrôlé — pré-faisabilité, jamais « conforme ».
      </p>

      {/* ───────── ÉTAT 1 — CONFIGURATION ───────── */}
      {!data && (
        <>
          <Lbl>Terrain — 1 à {ASM_MAX} parcelles contiguës</Lbl>
          <EntreeParcelle source={null} onPick={(i) => ajouter(i)} />
          <div className="flex flex-wrap gap-1">
            {msel.map((i) => (
              <button key={i} data-etude-chip onClick={() => { setMsel(msel.filter((x) => x !== i)); setMax8(false) }}
                className="min-h-7 rounded-full border border-mint/60 px-2 py-0.5 font-mono text-[11px] text-mint transition-colors duration-quick hover:bg-mint/10">
                {i.slice(8)} ×
              </button>
            ))}
            {msel.length === 0 && <span className="text-[11px] text-txt-dim">aucune parcelle — saisissez ou cliquez la carte</span>}
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
            disabled={msel.length === 0 || run.isPending}
            onClick={() => { setTab(0); run.mutate(corpsBody()) }}>
            {run.isPending ? 'Génération…' : 'Générer les scénarios'}
          </Bouton>
          {run.isError && <ErrorState message="L'étude a échoué — réessayez." retry={() => run.mutate(corpsBody())} />}
        </>
      )}

      {/* ───────── ÉTAT 2 — SCÉNARIOS ───────── */}
      {data && (
        <>
          <p className="text-[10px] text-txt-dim">
            {msel.map((i) => i.slice(8)).join(' · ')} · collectif · {OBJECTIFS.find((o) => o.key === data.entrees.objectif)?.label.toLowerCase()} · aérien
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
                      ['m² SDP', fmtInt(actif.resume.sdp_m2)]].map(([lbl, val]) => (
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
                      s={`ratio SHAB/SDP ${actif.programme.ratio_shab_sdp ?? '—'}`} />
                  </Section>

                  <Section titre="Distribution par niveau">
                    {actif.distribution_niveaux.map((d) => (
                      <Ligne key={d.niveau} l={`Niveau ${d.niveau}`}
                        v={Object.entries(d.par_type).map(([t, n]) => `${t} ×${n}`).join(' · ') || '—'}
                        s={`SDP ${fmtInt(d.sdp_m2)} m²`} />
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

                  <button data-etude-gabarit onClick={() => { if (msel[0]) { useApp.getState().setParcelPrefill(msel[0]) } ; useApp.getState().setModule('gabarit') }}
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
}

function Section({ titre, children }: { titre: string; children: React.ReactNode }) {
  return (
    <details className="border-t border-line-2 pt-1">
      <summary className="cursor-pointer text-[11px] font-semibold text-txt">{titre}</summary>
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
      <input inputMode="decimal" value={val} placeholder={String(defaut)} onChange={(e) => onChange(e.target.value)}
        className="w-20 rounded border border-line-2 bg-surface px-1.5 py-1 text-right text-[11px]" />
    </div>
  )
}
