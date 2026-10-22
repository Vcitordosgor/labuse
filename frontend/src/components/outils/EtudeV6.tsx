// ETUDE-V6 (Lot A) — L'ÉTUDE DE FAISABILITÉ EN 3 ÉTAPES EXACTEMENT : ① Choix des parcelles · ② Type de
// projet · ③ Votre programme, puis « Analyser mon projet ». Récapitulatif à droite. AUCUNE CARTE dans le
// formulaire, aucun bouton « bientôt », aucune présélection de type ni de typologie. Aucun calcul ici :
// l'étape 1 est validée par POST /modules/etude/parcelles (faits + contiguïté + sources), et l'analyse
// par POST /modules/etude. Remplace la config de M22 dans l'overlay EtudeEcran. Le RÉSULTAT détaillé
// (« ce que le terrain accueille », variantes, facteurs limitants) est repris au Lot B ; ici, base servie.
import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { postEtude, postEtudeParcelles } from '../../lib/api'
import type { EtudeParcellesOut, EtudePayload } from '../../lib/api'
import { fmtInt, fmtDec } from '../../lib/format'
import { Bouton } from '../ui/Bouton'
import { Badge } from '../ui/Badge'
import { ParcelInput } from '../ParcelInput'
import { Chargement } from '../Loading'
import { PlanMasseSvg } from './PlanMasseSvg'

// Hypothèses de programme (mandat V6) : surface totale par logement, varangue incluse → intérieur indicatif.
// Jamais appelées SDP ni SHAB. Modifiables plus tard dans « Hypothèses » (Lot B).
const TYPES = ['T1', 'T2', 'T3', 'T4'] as const
type TypeKey = (typeof TYPES)[number]
const SURF: Record<TypeKey, { area: number; varangue: number }> = {
  T1: { area: 30, varangue: 6 }, T2: { area: 56, varangue: 9 },
  T3: { area: 70, varangue: 12 }, T4: { area: 80, varangue: 14 },
}

type ProjetKey = 'etudiante' | 'senior' | 'social' | 'lotissement'
const PROJETS: { key: ProjetKey; label: string; desc: string }[] = [
  { key: 'etudiante', label: 'Résidence étudiante', desc: 'Studios et petits logements pour étudiants' },
  { key: 'senior', label: 'Résidence senior', desc: 'Logements adaptés pour personnes âgées' },
  { key: 'social', label: 'Logement social', desc: 'Programme locatif social ou assimilé' },
  { key: 'lotissement', label: 'Lotissement', desc: 'Division foncière en lots destinés à bâtir' },
]
// Le moteur d'implantation ne connaît pour l'instant que le collectif ; la spécialisation par type
// (stationnement = Lot C, division = Lot D) suit. Lot A : les 3 types résidentiels passent en collectif.
const VERS_MOTEUR: Record<ProjetKey, string> = {
  etudiante: 'collectif', senior: 'collectif', social: 'collectif', lotissement: 'collectif',
}

const ETAPES = [
  { n: 1, titre: 'Choix des parcelles', sous: 'Assiette foncière' },
  { n: 2, titre: 'Type de projet', sous: 'Destination' },
  { n: 3, titre: 'Votre programme', sous: 'T1, T2, T3, T4' },
] as const

function statutCourt(s: string): string {
  if (s.startsWith('exploitable')) return 'Exploitable sous hypothèses'
  if (s === 'à compléter') return 'À compléter'
  if (s === 'ne tient pas') return 'Ne tient pas'
  return 'Simulation impossible'
}
function statutTon(s: string): 'vert' | 'ambre' | 'rouge' {
  if (s.startsWith('exploitable')) return 'vert'
  if (s === 'à compléter') return 'ambre'
  return 'rouge'
}

export function EtudeV6({ initialIdus, onClose }: { initialIdus?: string[]; onClose?: () => void }) {
  const [step, setStep] = useState<1 | 2 | 3>(1)
  const [sel, setSel] = useState<string[]>(initialIdus ?? [])
  const [projet, setProjet] = useState<ProjetKey | null>(null)
  const [nb, setNb] = useState<Record<TypeKey, number>>({ T1: 0, T2: 0, T3: 0, T4: 0 })

  // Étape 1 : validation de l'assiette (faits + contiguïté + sources). Rejouée à chaque changement de sel.
  const valide = useQuery({
    queryKey: ['etude-parcelles', sel.join(',')],
    queryFn: () => postEtudeParcelles(sel),
    enabled: sel.length > 0,
    staleTime: 60_000,
  })
  const v: EtudeParcellesOut | undefined = valide.data

  // Analyse (étape finale) : un seul appel moteur, on bascule vers le résultat.
  const analyse = useMutation({
    mutationFn: () => postEtude({
      idus: sel,
      type_projet: projet ? VERS_MOTEUR[projet] : 'collectif',
      programme: { mode: 'saisi', lignes: TYPES.filter((t) => nb[t] > 0).map((t) => ({ type: t, nombre: nb[t], surface_m2: SURF[t].area })) },
    }),
  })
  const resultat: EtudePayload | undefined = analyse.data

  const totalLogts = TYPES.reduce((s, t) => s + nb[t], 0)
  const surfaceProg = TYPES.reduce((s, t) => s + nb[t] * SURF[t].area, 0)
  const surfaceVar = TYPES.reduce((s, t) => s + nb[t] * SURF[t].varangue, 0)
  const surfaceInt = surfaceProg - surfaceVar

  const contiguOk = sel.length > 0 && !!v?.contiguite.ok
  const peutContinuer1 = contiguOk && !valide.isFetching
  const peutAnalyser = contiguOk && !!projet && totalLogts > 0

  function reset() { setStep(1); setSel([]); setProjet(null); setNb({ T1: 0, T2: 0, T3: 0, T4: 0 }); analyse.reset() }
  function ajouter(idu: string) { setSel((xs) => (xs.includes(idu) || xs.length >= 8 ? xs : [...xs, idu])) }
  function retirer(idu: string) { setSel((xs) => xs.filter((x) => x !== idu)) }

  // ── RÉSULTAT (base Lot A — enrichi au Lot B) ──────────────────────────────────────────────────
  if (resultat) {
    const sc = resultat.scenarios[0]
    return (
      <div className="flex min-h-full flex-col">
        <Entete onClose={onClose} onReset={() => { analyse.reset() }} resetLabel="← Modifier le programme" />
        <div className="grid flex-1 gap-4 p-4 lg:grid-cols-[320px_1fr]">
          <aside className="flex flex-col gap-3">
            <div className="rounded-lg border border-line-2 bg-surface-2 p-3">
              <div className="flex items-center justify-between">
                <b className="text-[13px]">{sc ? `Scénario ${sc.ref} · ${sc.forme}` : 'Aucun scénario'}</b>
                <Badge ton={statutTon(resultat.statut_global)}>{statutCourt(resultat.statut_global)}</Badge>
              </div>
              {sc && <p className="mt-1 text-[12px] text-txt-mut">{fmtInt(sc.resume.logements)} logements · {fmtInt(sc.resume.places)} places</p>}
              {resultat.message && <p className="mt-2 text-[11px] text-amber">{resultat.message}</p>}
            </div>
            <p className="text-[10.5px] leading-snug text-txt-dim">
              Pré-faisabilité indicative, à faire confirmer par un architecte. Ni étude d'architecte, ni preuve de conformité.
              Le détail « ce que le terrain accueille », les variantes et les facteurs limitants arrivent au lot suivant.
            </p>
          </aside>
          <section className="flex flex-col gap-4">
            {sc && (
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <Chiffre v={fmtInt(sc.resume.logements)} l="logements" />
                <Chiffre v={fmtInt(sc.resume.places)} l="places dessinées" />
                <Chiffre v={`${fmtDec(sc.resume.sdp_m2)} m²`} l="SDP du scénario" />
                <Chiffre v={`${fmtDec(resultat.terrain.contenance_totale_m2)} m²`} l="terrain" />
              </div>
            )}
            {sc?.geojson && (
              <div className="rounded-lg border border-line-2 bg-surface-2 p-3">
                <p className="mb-2 text-[11px] font-semibold text-txt">Plan masse — scénario {sc.ref}</p>
                <PlanMasseSvg fc={sc.geojson} svg={sc.planche_svg} groupesCaches={[]} />
              </div>
            )}
          </section>
        </div>
      </div>
    )
  }

  // ── WIZARD (3 étapes) ─────────────────────────────────────────────────────────────────────────
  return (
    <div className="flex min-h-full flex-col">
      <Entete onClose={onClose} onReset={reset} resetLabel="↻ Recommencer" />
      <div className="px-4 pt-4">
        <p className="text-[10px] font-semibold uppercase tracking-wide text-mint">Outil de pré-faisabilité</p>
        <h1 className="mt-1 font-display text-[clamp(22px,3vw,34px)] font-bold leading-tight text-txt-hi">Votre projet. Les possibilités du terrain.</h1>
        <p className="mt-1 max-w-[640px] text-[12.5px] text-txt-mut">Trois étapes pour définir votre opération. LABUSE confronte ensuite votre programme aux capacités et contraintes à étudier.</p>
      </div>

      <div className="grid grid-cols-1 gap-2 px-4 pt-4 sm:grid-cols-3">
        {ETAPES.map((e) => {
          const on = e.n === step
          const fait = e.n < step
          return (
            <button key={e.n} type="button" onClick={() => { if (e.n < step) setStep(e.n as 1 | 2 | 3) }}
              className={`flex items-center gap-2.5 rounded-lg border px-3 py-2.5 text-left transition-colors duration-quick ${
                on ? 'border-mint bg-mint-bg' : fait ? 'border-line-2 hover:border-mint/50' : 'border-line-2 opacity-70'} ${e.n < step ? 'cursor-pointer' : 'cursor-default'}`}>
              <span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded text-[12px] font-bold ${on || fait ? 'bg-mint text-mint-on' : 'bg-surface-3 text-txt-dim'}`}>{e.n}</span>
              <span><b className="block text-[12.5px] text-txt-hi">{e.titre}</b><small className="text-[10.5px] text-txt-dim">{e.sous}</small></span>
            </button>
          )
        })}
      </div>

      <div className="grid flex-1 gap-4 p-4 lg:grid-cols-[1fr_340px]">
        <div className="rounded-lg border border-line-2 bg-surface-2 p-4">
          {step === 1 && <EtapeParcelles sel={sel} v={v} chargement={valide.isFetching} erreur={valide.error} onAjouter={ajouter} onRetirer={retirer} />}
          {step === 2 && <EtapeType projet={projet} onChoisir={setProjet} />}
          {step === 3 && <EtapeProgramme nb={nb} setNb={setNb} totalLogts={totalLogts} surfaceProg={surfaceProg} surfaceVar={surfaceVar} surfaceInt={surfaceInt} lotissement={projet === 'lotissement'} />}
        </div>
        <Recap sel={sel} v={v} projet={projet} totalLogts={totalLogts} surfaceProg={surfaceProg} surfaceVar={surfaceVar} />
      </div>

      <PiedEtape
        step={step}
        peutContinuer1={peutContinuer1} peutAnalyser={peutAnalyser}
        enAnalyse={analyse.isPending} erreurAnalyse={analyse.error}
        onPrec={() => setStep((s) => (s > 1 ? ((s - 1) as 1 | 2 | 3) : s))}
        onSuiv={() => setStep((s) => (s < 3 ? ((s + 1) as 1 | 2 | 3) : s))}
        onAnalyser={() => analyse.mutate()}
        projetChoisi={!!projet}
      />
    </div>
  )
}

// ── En-tête (Fermer / Recommencer) ───────────────────────────────────────────────────────────────
function Entete({ onClose, onReset, resetLabel }: { onClose?: () => void; onReset: () => void; resetLabel: string }) {
  return (
    <header className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
      <div className="flex items-center gap-3">
        {onClose && <Bouton niveau="secondaire" onClick={onClose}>← Fermer</Bouton>}
        <div><b className="block text-[14px] text-txt-hi">Étude de faisabilité</b><small className="text-[10.5px] text-txt-dim">Pré-faisabilité foncière · La Réunion</small></div>
      </div>
      <Bouton niveau="secondaire" onClick={onReset}>{resetLabel}</Bouton>
    </header>
  )
}

function Chiffre({ v, l }: { v: string; l: string }) {
  return (
    <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2.5">
      <div className="font-display text-[24px] font-bold leading-none text-txt-hi">{v}</div>
      <div className="mt-1 text-[10.5px] text-txt-dim">{l}</div>
    </div>
  )
}

// ── Étape 1 — Parcelles ──────────────────────────────────────────────────────────────────────────
function EtapeParcelles({ sel, v, chargement, erreur, onAjouter, onRetirer }: {
  sel: string[]; v?: EtudeParcellesOut; chargement: boolean; erreur: unknown
  onAjouter: (idu: string) => void; onRetirer: (idu: string) => void
}) {
  return (
    <div>
      <EnTetePanneau n="01" titre="Choisissez votre terrain" sous="Une ou plusieurs parcelles (1 à 8). Elles doivent être contiguës pour constituer une même assiette foncière." />
      <label className="mb-1 block text-[9px] uppercase tracking-wide text-txt-dim">Référence de parcelle — adresse, IDU ou référence cadastrale</label>
      <div className="max-w-[560px]">
        <ParcelInput dataAttr="etude-v6-parcelle" withCarte={false} onPick={onAjouter} placeholder="Adresse, IDU ou référence (ex. 97404000AW0099)" />
      </div>
      <p className="mt-1.5 text-[10.5px] text-txt-dim">Aucune carte dans le formulaire : la sélection se fait par recherche.</p>

      <div className="mt-3 flex items-center justify-between">
        <b className="text-[12px] text-txt">Parcelles sélectionnées</b>
        <span className="text-[11px] text-txt-dim">{sel.length}/8</span>
      </div>
      {sel.length === 0 && <p className="mt-1.5 text-[11.5px] text-txt-dim">Ajoutez une référence pour commencer.</p>}

      {sel.length > 0 && chargement && !v && <div className="mt-2"><Chargement /></div>}
      {!!erreur && <p className="mt-2 text-[11.5px] text-coral">{(erreur as Error).message}</p>}

      {v?.parcelles && (
        <div className="mt-2 flex flex-col gap-2">
          {v.parcelles.map((p) => (
            <div key={p.idu} data-etude-parcelle-row className="rounded-md border border-line-2 bg-surface-1 px-3 py-2">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <b className="font-mono text-[12px] text-txt-hi">{p.reference}</b>
                  <span className="text-[11px] text-txt-mut">{p.commune}</span>
                  {p.zone_plu && <Badge ton="neutre">{p.zone_plu}</Badge>}
                  {p.qualite_geometrique === 'irrégulière' && <Badge ton="ambre">géométrie irrégulière</Badge>}
                </div>
                <button type="button" onClick={() => onRetirer(p.idu)} className="text-[12px] text-txt-dim hover:text-coral" aria-label={`Retirer ${p.reference}`}>×</button>
              </div>
              <div className="mt-1 flex flex-wrap gap-x-4 gap-y-0.5 text-[10.5px] text-txt-dim">
                <span>Contenance <b className="text-txt">{p.contenance_cadastrale_m2 != null ? `${fmtDec(p.contenance_cadastrale_m2)} m²` : '—'}</b></span>
                <span>Surface réelle <b className="text-txt">{p.surface_reelle_m2 != null ? `${fmtDec(p.surface_reelle_m2)} m²` : '—'}</b></span>
                {p.ecart_m2 != null && <span>Écart {p.ecart_m2 > 0 ? '+' : ''}{fmtDec(p.ecart_m2)} m²</span>}
              </div>
            </div>
          ))}

          {/* Union + contiguïté */}
          <div className={`rounded-md border px-3 py-2 ${v.contiguite.ok ? 'border-mint/40 bg-mint-bg' : 'border-coral/50 bg-coral/10'}`}>
            <b className="text-[12px] text-txt-hi">{v.union.nb_parcelles} parcelle{v.union.nb_parcelles > 1 ? 's' : ''} · {v.union.surface_reelle_m2 != null ? `${fmtDec(v.union.surface_reelle_m2)} m²` : '—'}</b>
            {v.contiguite.ok ? (
              <p className="mt-0.5 text-[10.5px] text-txt-mut">
                Contiguës, assiette fusionnée · périmètre {v.union.perimetre_m != null ? `${fmtDec(v.union.perimetre_m)} m` : '—'} · aire cadastrale {fmtDec(v.union.aire_cadastrale_m2)} m²{v.union.ecart_m2 != null ? ` (écart ${v.union.ecart_m2 > 0 ? '+' : ''}${fmtDec(v.union.ecart_m2)} m²)` : ''}
              </p>
            ) : (
              <p className="mt-0.5 text-[11px] font-medium text-coral">{v.contiguite.message}</p>
            )}
          </div>

          <Signaux v={v} />
          <Sources v={v} />
        </div>
      )}
    </div>
  )
}

function Signaux({ v }: { v: EtudeParcellesOut }) {
  const s = v.signaux
  const items: string[] = []
  if (s.communes_differentes) items.push(`Communes différentes : ${s.communes_differentes.join(', ')}.`)
  if (s.zones_differentes) items.push(`Zones PLU différentes : ${s.zones_differentes.join(', ')} — chaque sous-secteur a son règlement.`)
  if (s.ravine_traversante) items.push('Une ravine recoupe l\'assiette (à vérifier : emprise, recul, PPR).')
  if (s.proprietaires_presumes) items.push(`${s.proprietaires_presumes} propriétaire(s) présumé(s) (personnes morales en base) — la contiguïté ne prouve pas la maîtrise foncière.`)
  if (!items.length) return null
  return (
    <div className="rounded-md border border-amber/40 bg-amber-bg px-3 py-2">
      <b className="text-[11px] text-amber">À signaler (sans conclure sur la constructibilité)</b>
      <ul className="mt-1 list-disc pl-4 text-[10.5px] text-txt-mut">{items.map((t) => <li key={t}>{t}</li>)}</ul>
    </div>
  )
}

function Sources({ v }: { v: EtudeParcellesOut }) {
  const c = v.sources.cadastre, p = v.sources.plu
  if (!c && !p) return null
  return (
    <p className="text-[9.5px] leading-snug text-txt-dim">
      {c && <>Géométrie &amp; contenance : {c.source}{c.derniere_synchro ? ` · maj ${c.derniere_synchro}` : ''}. </>}
      {p && <>Zone PLU : {p.source}.</>}
    </p>
  )
}

// ── Étape 2 — Type de projet ─────────────────────────────────────────────────────────────────────
function EtapeType({ projet, onChoisir }: { projet: ProjetKey | null; onChoisir: (k: ProjetKey) => void }) {
  return (
    <div>
      <EnTetePanneau n="02" titre="Quel type de projet ?" sous="Sélectionnez la destination de votre opération." />
      <div className="grid gap-2.5 sm:grid-cols-2">
        {PROJETS.map((pr) => {
          const on = pr.key === projet
          return (
            <button key={pr.key} type="button" data-etude-type={pr.key} onClick={() => onChoisir(pr.key)}
              className={`rounded-lg border px-3.5 py-3 text-left transition-colors duration-quick ${on ? 'border-mint bg-mint-bg' : 'border-line-2 hover:border-mint/50'}`}>
              <b className="block text-[13px] text-txt-hi">{pr.label}</b>
              <small className="text-[11px] text-txt-dim">{pr.desc}</small>
            </button>
          )
        })}
      </div>
      {projet && (
        <div className="mt-3 rounded-md border border-line-2 bg-surface-1 px-3 py-2">
          <div className="flex items-center gap-2">
            <b className="text-[11.5px] text-txt">Stationnement PLU</b>
            <Badge ton="ambre">à vérifier</Badge>
          </div>
          <p className="mt-1 text-[10.5px] text-txt-mut">
            LABUSE recherchera les prescriptions de stationnement applicables à la parcelle et à cette catégorie
            (commune, zone, article et version du règlement), ainsi que les plafonds nationaux éventuels sous condition
            d'éligibilité. La règle détaillée est servie dans le résultat.
            {projet === 'lotissement' && ' Lotissement : division foncière — les obligations portent sur les futures constructions des lots.'}
          </p>
        </div>
      )}
    </div>
  )
}

// ── Étape 3 — Programme ──────────────────────────────────────────────────────────────────────────
function EtapeProgramme({ nb, setNb, totalLogts, surfaceProg, surfaceVar, surfaceInt, lotissement }: {
  nb: Record<TypeKey, number>; setNb: (f: (n: Record<TypeKey, number>) => Record<TypeKey, number>) => void
  totalLogts: number; surfaceProg: number; surfaceVar: number; surfaceInt: number; lotissement: boolean
}) {
  const set = (t: TypeKey, val: number) => setNb((n) => ({ ...n, [t]: Math.max(0, Math.min(200, val)) }))
  return (
    <div>
      <EnTetePanneau n="03" titre="Combien de logements souhaitez-vous ?" sous="Indiquez simplement le nombre de T1, T2, T3 et T4." />
      {lotissement && (
        <div className="mb-3 rounded-md border border-amber/40 bg-amber-bg px-3 py-2 text-[10.5px] text-txt-mut">
          <b className="text-amber">Lotissement</b> — la composition des logements est informative : la faisabilité dépendra d'abord de la division en lots et des voiries à dessiner.
        </div>
      )}
      <div className="flex flex-col gap-2">
        {TYPES.map((t) => (
          <div key={t} className="flex items-center gap-3 rounded-md border border-line-2 bg-surface-1 px-3 py-2">
            <span className="w-8 font-mono text-[13px] font-bold text-txt-hi">{t}</span>
            <div className="flex-1">
              <b className="text-[12px] text-txt">{SURF[t].area} m²</b>
              <small className="ml-2 text-[10px] text-txt-dim">dont {SURF[t].varangue} m² de varangue · {SURF[t].area - SURF[t].varangue} m² intérieur indicatif</small>
            </div>
            <div className="flex items-center gap-1">
              <button type="button" onClick={() => set(t, nb[t] - 1)} aria-label={`Retirer un ${t}`} className="flex h-7 w-7 items-center justify-center rounded border border-line-2 text-txt hover:border-mint/60">−</button>
              <input type="number" min={0} max={200} inputMode="numeric" aria-label={`Nombre de ${t}`} data-etude-count={t}
                value={nb[t]} onChange={(e) => set(t, parseInt(e.target.value || '0', 10))}
                className="w-14 rounded border border-line-2 bg-surface-2 px-2 py-1 text-center text-[12px] text-txt-hi" />
              <button type="button" onClick={() => set(t, nb[t] + 1)} aria-label={`Ajouter un ${t}`} className="flex h-7 w-7 items-center justify-center rounded border border-line-2 text-txt hover:border-mint/60">+</button>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-3 flex items-center justify-between rounded-md border border-line-2 bg-surface-1 px-3 py-2">
        <div>
          <b className="text-[12.5px] text-txt-hi">{fmtInt(totalLogts)} logement{totalLogts > 1 ? 's' : ''} au programme</b>
          <p className="text-[10.5px] text-txt-dim">dont {fmtDec(surfaceVar)} m² de varangues · {fmtDec(surfaceInt)} m² d'intérieur indicatif</p>
        </div>
        <div className="text-right">
          <b className="font-display text-[20px] text-txt-hi">{fmtDec(surfaceProg)} m²</b>
          <p className="text-[10px] text-txt-dim">surface du programme</p>
        </div>
      </div>
      <p className="mt-2 text-[10px] text-txt-dim">Ces surfaces sont des hypothèses de programme (varangue comprise). La surface de plancher réglementaire (SDP) sera calculée séparément par le moteur — jamais confondue avec ces m².</p>
    </div>
  )
}

function EnTetePanneau({ n, titre, sous }: { n: string; titre: string; sous: string }) {
  return (
    <div className="mb-3 flex items-start gap-2.5">
      <span className="flex h-7 shrink-0 items-center rounded bg-mint-bg px-2 font-mono text-[11px] font-bold text-mint">{n}</span>
      <div><h2 className="text-[16px] font-bold text-txt-hi">{titre}</h2><p className="text-[11px] text-txt-dim">{sous}</p></div>
    </div>
  )
}

// ── Récapitulatif ────────────────────────────────────────────────────────────────────────────────
function Recap({ sel, v, projet, totalLogts, surfaceProg, surfaceVar }: {
  sel: string[]; v?: EtudeParcellesOut; projet: ProjetKey | null
  totalLogts: number; surfaceProg: number; surfaceVar: number
}) {
  const surfaceTerrain = v?.union.surface_reelle_m2
  const projetLabel = projet ? PROJETS.find((p) => p.key === projet)!.label : 'À choisir'
  return (
    <aside className="flex h-fit flex-col gap-0 rounded-lg border border-line-2 bg-surface-2 p-3">
      <p className="text-[9px] font-semibold uppercase tracking-wide text-mint">Récapitulatif</p>
      <div className="mt-2 rounded-md border border-line-2 bg-surface-1 px-3 py-2.5">
        <p className="text-[10.5px] text-txt-dim">Terrain sélectionné</p>
        <div className="font-display text-[26px] font-bold leading-none text-txt-hi">{surfaceTerrain != null ? fmtDec(surfaceTerrain) : '0'} <span className="text-[15px]">m²</span></div>
        <p className="mt-0.5 text-[10.5px] text-txt-dim">{sel.length} parcelle{sel.length > 1 ? 's' : ''}</p>
      </div>
      <Ligne l="Projet" v={projetLabel} />
      <Ligne l="Logements demandés" v={fmtInt(totalLogts)} />
      <Ligne l="Surface du programme" v={`${fmtDec(surfaceProg)} m²`} sous={surfaceVar > 0 ? `dont ${fmtDec(surfaceVar)} m² varangues` : undefined} />
      <Ligne l="Stationnement PLU" v="Non vérifié" ton="ambre" />
    </aside>
  )
}
function Ligne({ l, v, sous, ton }: { l: string; v: string; sous?: string; ton?: 'ambre' }) {
  return (
    <div className="flex items-center justify-between border-t border-line-2 py-2">
      <div><span className="text-[11.5px] text-txt-mut">{l}</span>{sous && <p className="text-[9.5px] text-txt-dim">{sous}</p>}</div>
      <b className={`text-[12px] ${ton === 'ambre' ? 'text-amber' : 'text-txt-hi'}`}>{v}</b>
    </div>
  )
}

// ── Pied d'étape (navigation + action) ───────────────────────────────────────────────────────────
function PiedEtape({ step, peutContinuer1, peutAnalyser, enAnalyse, erreurAnalyse, onPrec, onSuiv, onAnalyser, projetChoisi }: {
  step: 1 | 2 | 3; peutContinuer1: boolean; peutAnalyser: boolean; enAnalyse: boolean; erreurAnalyse: unknown
  onPrec: () => void; onSuiv: () => void; onAnalyser: () => void; projetChoisi: boolean
}) {
  const TITRES = ['', 'Une ou plusieurs parcelles', 'Une destination claire', 'Votre programme, votre choix']
  const TEXTES = ['',
    'Le regroupement est refusé si les parcelles sont séparées.',
    'Le stationnement sera vérifié selon la commune, la zone et le régime juridique.',
    'L\'analyse explique la réserve estimée ou le dépassement, sans annoncer une conformité non prouvée.']
  const suivBloque = step === 1 ? !peutContinuer1 : step === 2 ? !projetChoisi : false
  const raison = step === 1 && !peutContinuer1 ? 'Sélectionnez des parcelles contiguës pour continuer.'
    : step === 2 && !projetChoisi ? 'Choisissez un type de projet pour continuer.' : ''
  return (
    <div className="mx-4 mb-4 mt-2 rounded-lg border border-line-2 bg-surface-2 px-4 py-3">
      <div className="flex items-center justify-between gap-3">
        <div>
          <b className="text-[12.5px] text-txt-hi">{TITRES[step]}</b>
          <p className="text-[10.5px] text-txt-dim">{TEXTES[step]}</p>
          {raison && <p className="mt-0.5 text-[10.5px] text-amber">{raison}</p>}
          {!!erreurAnalyse && <p className="mt-0.5 text-[10.5px] text-coral">{(erreurAnalyse as Error).message}</p>}
        </div>
        <div className="flex items-center gap-2">
          {step > 1 && <Bouton niveau="secondaire" onClick={onPrec}>← Retour</Bouton>}
          {step < 3 && <Bouton niveau="primaire" onClick={onSuiv} disabled={suivBloque}>Continuer →</Bouton>}
          {step === 3 && <Bouton niveau="primaire" onClick={onAnalyser} disabled={!peutAnalyser || enAnalyse}>{enAnalyse ? 'Analyse…' : 'Analyser mon projet →'}</Bouton>}
        </div>
      </div>
    </div>
  )
}

export default EtudeV6
