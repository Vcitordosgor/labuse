// OUTILS-5 (P3) — LE PARCOURS PROJET, v3 « rien n'est caché, tout est ordonné ».
// ÉCRAN 0 : deux portes — « Partir du vivier LABUSE » (le wizard cadre et verse le VIVIER ENTIER, classé)
// ou « Projet de zéro » (un dossier VIDE ; on y ajoute des parcelles depuis leurs fiches → Retenues).
// Wizard vivier : 5 étapes (NOM · PÉRIMÈTRE · CONTEXTE=budget+type fusionnés · CADRAGE · RÉCAP). La
// shortlist-limite disparaît des textes : le projet donne le vivier entier, ordonné par probabilité de
// mutation, les mieux classées d'abord. Budget/type restent INFORMATIFS (« sans effet sur la sélection »).
import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react'

import { AlgoExplainer, ScoringExplainer } from '../panel/LeftPanel'
import { createProjet, getCadrageCompteur, getProjetTypes, type Cadrage, type Identite, type TypeLogement } from '../../lib/api'
import { CP_COMMUNES } from '../panel/FiltreLabuse'
import { FiltreFacettes } from '../panel/FiltreFacettes'
import { FiltreProvider } from '../panel/filtreContext'
import { EMPTY_FILTERS, useApp, type Filters } from '../../store/useApp'

const MONO = 'ui-monospace, SFMono-Regular, Menlo, monospace'
const ETAPES = ['NOM', 'PÉRIMÈTRE', 'CONTEXTE', 'CADRAGE', 'RÉCAPITULATIF']
const N = ETAPES.length

const ACCENT_MINT = { c: '#4ADE80', bg: '#12291D', on: '#05140B' }
const ACCENT_IA = { c: '#B497F0', bg: '#1A1430', on: '#14091F' }

export function ParcoursProjet({ prefill, onVoir, onFermer, accent }: {
  prefill?: Record<string, unknown> | null
  onVoir: (projet: { id: number; nom: string }) => void
  onFermer: () => void
  accent?: 'mint' | 'ia'
  plein?: boolean
}) {
  const A = accent === 'ia' ? ACCENT_IA : ACCENT_MINT
  const pf = prefill || {}
  const setAlgoModale = useApp((s) => s.setAlgoModale)
  const algoModale = useApp((s) => s.algoModale)
  // OUTILS-5 (P3) — la PORTE : null = écran 0 (choix), 'vivier' = wizard, 'zero' = projet vide.
  const [porte, setPorte] = useState<null | 'vivier' | 'zero'>(null)
  const [etape, setEtape] = useState(0)
  const [nom, setNom] = useState('')
  const [ile, setIle] = useState(false)
  const [communes, setCommunes] = useState<string[]>(typeof pf.commune === 'string' ? [pf.commune] : [])
  const [budget, setBudget] = useState<string>(typeof pf.budget_eur === 'number' ? String(pf.budget_eur) : '')
  const [type, setType] = useState<string>('')
  const [cadrageFacettes, setCadrageFacettes] = useState<Filters>({ ...EMPTY_FILTERS })
  const [envoi, setEnvoi] = useState(false)
  const [erreur, setErreur] = useState<string | null>(null)
  const [cree, setCree] = useState<{ id: number; nom: string; existing?: boolean } | null>(null)
  const [types, setTypes] = useState<TypeLogement[]>([])
  const [vivierN, setVivierN] = useState<number | null>(null)   // OUTILS-5 (P3) — le VRAI compteur du vivier (récap)
  const rootRef = useRef<HTMLDivElement>(null)
  useEffect(() => { getProjetTypes().then((r) => setTypes(r.types)).catch(() => {}) }, [])
  useEffect(() => { if (etape === N - 1) rootRef.current?.focus() }, [etape])

  const nomEffectif = nom.trim() || (communes.length === 1 ? `Projet ${communes[0]}` : 'Nouveau projet')
  const perimetreLabel = ile || communes.length === 0 ? "toute l'île"
    : communes.length === 1 ? communes[0] : `${communes.length} communes`

  const binding = useMemo(() => ({
    filters: cadrageFacettes,
    setFilter: <K extends keyof Filters>(k: K, v: Filters[K]) =>
      setCadrageFacettes((c) => ({ ...c, [k]: v })),
  }), [cadrageFacettes])

  const cadrage: Cadrage = useMemo(() => {
    const c: Cadrage = {}
    for (const [k, v] of Object.entries(cadrageFacettes) as [keyof Filters, unknown][]) {
      const empty = v === null || v === false || (Array.isArray(v) && v.length === 0)
      if (!empty && k !== 'analyseLabuse') (c as Record<string, unknown>)[k] = v
    }
    if (!ile && communes.length) c.communes = communes
    else delete c.communes
    return c
  }, [cadrageFacettes, ile, communes])

  const identite: Identite = useMemo(() => ({
    ...(budget.trim() ? { budget_eur: parseInt(budget, 10) } : {}),
    ...(type ? { type_logement: type } : {}),
  }), [budget, type])

  // OUTILS-5 (P3) — au récap, on affiche le VRAI chiffre du vivier (le compteur du cadrage), pas
  // « N facettes ». Même moteur que la carte (getCadrageCompteur). Rafraîchi à l'arrivée sur le récap.
  useEffect(() => {
    if (porte !== 'vivier' || etape !== N - 1) return
    const ac = new AbortController()
    setVivierN(null)
    getCadrageCompteur(cadrage, ac.signal).then((r) => setVivierN(r.vivier ?? null)).catch(() => {})
    return () => ac.abort()
  }, [porte, etape, cadrage])

  const creer = async (deZero = false) => {
    setEnvoi(true); setErreur(null)
    try {
      const r = await createProjet(deZero
        ? { cadrage: {}, identite, nom: nom.trim() || undefined, de_zero: true }
        : { cadrage, identite, nom: nom.trim() || undefined })
      setCree({ id: r.projet.id, nom: r.projet.nom, existing: r.existing })
    } catch { setErreur('La création a échoué — réessayez.') }
    finally { setEnvoi(false) }
  }
  const avancer = () => { if (etape < N - 1) setEtape(etape + 1); else void creer() }
  const reculer = () => { if (etape > 0) setEtape(etape - 1); else setPorte(null) }
  const onKey = (e: KeyboardEvent) => {
    // sur le CADRAGE (étape 3), Entrée est laissée aux champs de facette.
    if (e.key === 'Enter' && etape !== 3 && porte === 'vivier') { e.preventDefault(); avancer() }
    else if (e.key === 'Escape') { e.preventDefault(); onFermer() }
  }

  // ── projet créé ──
  if (cree) {
    return (
      <div data-parcours-projet-cree style={{ background: '#0C1410', border: `.5px solid ${A.c}`, borderRadius: 12, padding: 24 }}>
        <p style={{ fontSize: 16, color: '#ECF5EF', margin: '0 0 8px' }}>
          Projet créé : <b>{cree.nom}</b>{cree.existing ? ' (il existait déjà)' : ''}.
        </p>
        {/* OUTILS-5 (P1) — plus de « shortlist figée » : le projet contient le VIVIER ENTIER, classé. */}
        <p data-cree-vivier style={{ fontSize: 13, color: '#8FA69A', margin: '0 0 16px' }}>
          Le vivier entier est dans le projet, classé par probabilité de mutation — rien n'est retiré, tout est ordonné.
        </p>
        <div style={{ display: 'flex', gap: 12 }}>
          <button data-projet-voir onClick={() => onVoir({ id: cree.id, nom: cree.nom })}
            style={{ padding: '9px 18px', background: A.c, color: A.on, borderRadius: 8, fontSize: 14, fontWeight: 500, border: 0, cursor: 'pointer' }}>Voir le projet →</button>
          <button onClick={onFermer} style={{ padding: '9px 18px', background: 'none', border: '.5px solid #1E2A23', color: '#8FA69A', borderRadius: 8, fontSize: 13, cursor: 'pointer' }}>Fermer</button>
        </div>
      </div>
    )
  }

  // ── ÉCRAN 0 : deux portes ──
  if (porte === null) {
    const Porte = ({ k, titre, desc, on }: { k: 'vivier' | 'zero'; titre: string; desc: string; on: boolean }) => (
      <button data-projet-porte={k} onClick={() => { setPorte(k); setEtape(0) }}
        style={{ textAlign: 'left', borderRadius: 12, padding: 18, cursor: 'pointer',
          border: on ? `.5px solid ${A.c}` : '.5px solid #2A3A31', background: on ? A.bg : 'transparent' }}>
        <b style={{ fontSize: 15, color: '#ECF5EF' }}>{titre}</b>
        <p style={{ fontSize: 12.5, color: '#8FA69A', marginTop: 4 }}>{desc}</p>
      </button>
    )
    return (
      <div data-parcours-projet-porte style={{ background: '#0C1410', border: `.5px solid ${A.c}`, borderRadius: 12, padding: 24 }}>
        <div style={{ fontFamily: MONO, fontSize: 11, letterSpacing: '.12em', color: A.c, marginBottom: 6 }}>NOUVEAU PROJET</div>
        <h2 style={{ fontSize: 22, fontWeight: 500, color: '#ECF5EF', margin: '0 0 16px' }}>Comment démarrer ?</h2>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <Porte k="vivier" on titre="Partir du vivier LABUSE"
            desc="Vous cadrez (périmètre, critères, signaux de vie) — le moteur verse toutes les parcelles correspondantes, classées par probabilité de mutation." />
          <Porte k="zero" on={false} titre="Projet de zéro"
            desc="Un dossier vide. Vous y ajoutez vos parcelles une à une, depuis leurs fiches (bouton « Projet »). Pour qui a déjà ses cibles." />
        </div>
        <div style={{ marginTop: 18, paddingTop: 14, borderTop: '.5px solid #1E2A23' }}>
          <button onClick={onFermer} style={{ fontSize: 13, color: '#6F8578', background: 'none', border: 0, cursor: 'pointer' }}>× Annuler</button>
        </div>
      </div>
    )
  }

  // ── PORTE « de zéro » : formulaire minimal (nom + contexte) → projet vide ──
  if (porte === 'zero') {
    return (
      <div data-parcours-projet-zero style={{ background: '#0C1410', border: `.5px solid ${A.c}`, borderRadius: 12, padding: 24 }}>
        <div style={{ fontFamily: MONO, fontSize: 11, letterSpacing: '.12em', color: A.c, marginBottom: 6 }}>PROJET DE ZÉRO</div>
        <h2 style={{ fontSize: 22, fontWeight: 500, color: '#ECF5EF', margin: '0 0 4px' }}>Un dossier vide.</h2>
        <p style={{ fontSize: 13.5, color: '#8FA69A', margin: '0 0 18px' }}>Nommez-le ; ajoutez vos parcelles depuis leurs fiches (bouton « Projet ») — elles arrivent dans <b style={{ color: '#C9DCD1' }}>Retenues</b>.</p>
        <input data-projet-nom autoFocus value={nom} onChange={(e) => setNom(e.target.value)} placeholder={`Ex. ${nomEffectif}`}
          style={{ width: '100%', height: 48, background: '#060A08', border: '.5px solid #2A3A31', borderRadius: 8, padding: '0 14px', fontSize: 18, color: '#ECF5EF', outline: 'none', marginBottom: 12 }} />
        <input data-projet-budget type="number" min="0" value={budget} onChange={(e) => setBudget(e.target.value)} placeholder="Budget foncier en € (facultatif, indicatif)"
          style={{ width: '100%', height: 44, background: '#060A08', border: '.5px solid #2A3A31', borderRadius: 8, padding: '0 14px', fontSize: 15, color: '#ECF5EF', outline: 'none' }} />
        {erreur && <p style={{ fontSize: 12, color: '#E0B341', margin: '12px 0 0' }}>{erreur}</p>}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: 18, marginTop: 18, borderTop: '.5px solid #1E2A23' }}>
          <button onClick={() => setPorte(null)} style={{ fontSize: 13, color: '#6F8578', background: 'none', border: 0, cursor: 'pointer' }}>← Retour</button>
          <button data-projet-creer-zero disabled={envoi} onClick={() => void creer(true)}
            style={{ padding: '9px 18px', background: A.c, color: A.on, borderRadius: 8, fontSize: 14, fontWeight: 500, border: 0, cursor: 'pointer', opacity: envoi ? 0.4 : 1 }}>{envoi ? 'Création…' : 'Créer le projet vide'}</button>
        </div>
      </div>
    )
  }

  const champ = { width: '100%', height: 52, background: '#060A08', border: '.5px solid #2A3A31', borderRadius: 8, padding: '0 16px', fontSize: 22, color: '#ECF5EF', outline: 'none' } as const
  const QUESTIONS = [
    ['Quel nom pour ce projet ?', 'Facultatif — un nom vous aide à le retrouver.'],
    ['Sur quel périmètre ?', 'Une ou plusieurs communes, ou toute l’île.'],
    ['Le contexte du projet', 'Indicatif — figure sur le projet et le PDF, sans effet sur la sélection.'],
    ['Affinez le cadrage.', 'Les mêmes critères que la carte. Chaque critère resserre le vivier — le reste arrive classé, les mieux d’abord.'],
    ['On récapitule.', 'Le vivier entier entre dans le projet, classé — rien n’est retiré, tout est ordonné.'],
  ]
  const noteInfo = (txt: string) => (
    <p style={{ fontSize: 12, color: '#6F8578', margin: '10px 0 0', display: 'flex', alignItems: 'center', gap: 6 }}>
      <span style={{ color: '#E0B341' }}>ⓘ</span>{txt}
    </p>
  )

  const trail: string[] = []
  if (etape > 0 && nom.trim()) trail.push(nomEffectif)
  if (etape > 1) trail.push(perimetreLabel)
  if (etape > 2 && (budget.trim() || type)) trail.push([budget.trim() ? `${parseInt(budget, 10).toLocaleString('fr-FR')} €` : null, type ? types.find((t) => t.cle === type)?.libelle ?? type : null].filter(Boolean).join(' · ') + ' (indic.)')

  return (
    <div data-parcours-projet ref={rootRef} tabIndex={-1} onKeyDown={onKey}
      style={{ background: '#0C1410', border: `.5px solid ${A.c}`, borderRadius: 12, padding: 24, outline: 'none' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <div style={{ fontFamily: MONO, fontSize: 11, letterSpacing: '.12em', color: A.c }}>NOUVEAU PROJET</div>
        <div data-parcours-step style={{ fontFamily: MONO, fontSize: 12, color: '#5F7267' }}>{etape + 1} / {N} · {ETAPES[etape]}</div>
      </div>
      <div data-parcours-progress style={{ display: 'flex', gap: 5, marginBottom: 28 }}>
        {ETAPES.map((_, i) => <i key={i} style={{ flex: 1, height: 2, background: i <= etape ? A.c : '#1E2A23' }} />)}
      </div>

      <h2 style={{ fontSize: 24, fontWeight: 500, color: '#ECF5EF', margin: '0 0 6px' }}>{QUESTIONS[etape][0]}</h2>
      <p style={{ fontSize: 14, color: '#8FA69A', margin: '0 0 24px' }}>{QUESTIONS[etape][1]}</p>

      {etape === 0 && (
        <div style={{ marginBottom: 28 }}>
          <input data-projet-nom autoFocus value={nom} onChange={(e) => setNom(e.target.value)}
            placeholder={`Ex. ${nomEffectif}`} style={champ} />
        </div>
      )}
      {etape === 1 && (
        <div style={{ marginBottom: 28 }}>
          <div style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
            <button data-projet-ile onClick={() => setIle(true)}
              style={{ padding: '9px 18px', borderRadius: 8, fontSize: 14, cursor: 'pointer', border: ile ? `.5px solid ${A.c}` : '.5px solid #1E2A23', background: ile ? A.bg : 'transparent', color: ile ? A.c : '#8FA69A' }}>Toute l’île</button>
            <button data-projet-communes-mode onClick={() => setIle(false)}
              style={{ padding: '9px 18px', borderRadius: 8, fontSize: 14, cursor: 'pointer', border: !ile ? `.5px solid ${A.c}` : '.5px solid #1E2A23', background: !ile ? A.bg : 'transparent', color: !ile ? A.c : '#8FA69A' }}>Communes précises</button>
          </div>
          {!ile && (
            <div data-projet-communes style={{ display: 'flex', flexWrap: 'wrap', gap: 6, maxHeight: 220, overflowY: 'auto' }}>
              {CP_COMMUNES.map(([cp, nomC]) => {
                const on = communes.includes(nomC)
                return (
                  <button key={cp} onClick={() => setCommunes(on ? communes.filter((x) => x !== nomC) : [...communes, nomC])}
                    title={nomC}
                    style={{ padding: '6px 12px', borderRadius: 999, fontSize: 12, cursor: 'pointer', border: on ? `.5px solid ${A.c}` : '.5px solid #1E2A23', background: on ? A.bg : '#080D0A', color: on ? A.c : '#8FA69A' }}>{nomC}</button>
                )
              })}
            </div>
          )}
        </div>
      )}
      {/* OUTILS-5 (P3) — CONTEXTE : budget + type FUSIONNÉS sur un écran, indicatifs. */}
      {etape === 2 && (
        <div data-projet-contexte style={{ marginBottom: 28 }}>
          <input data-projet-budget autoFocus type="number" min="0" value={budget} onChange={(e) => setBudget(e.target.value)}
            placeholder="Budget foncier en € (facultatif)" style={champ} />
          <div data-projet-type style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 12 }}>
            {types.map((t) => {
              const on = type === t.cle
              return (
                <button key={t.cle} onClick={() => setType(on ? '' : t.cle)}
                  style={{ padding: '9px 16px', borderRadius: 8, fontSize: 14, cursor: 'pointer', border: on ? `.5px solid ${A.c}` : '.5px solid #1E2A23', background: on ? A.bg : 'transparent', color: on ? A.c : '#8FA69A' }}>{t.libelle}</button>
              )
            })}
          </div>
          {noteInfo('Indicatif — figure sur le projet et le PDF, sans effet sur la sélection.')}
        </div>
      )}
      {etape === 3 && (
        <div data-projet-cadrage style={{ marginBottom: 28, maxHeight: '52vh', overflowY: 'auto' }}>
          <p style={{ fontSize: 12, color: '#6F8578', margin: '0 0 14px' }}>Périmètre : <b style={{ color: '#ECF5EF' }}>{perimetreLabel}</b> · modifiable à l’étape précédente.</p>
          {/* PROJETS-FIX F1 — le compteur vivant reçoit le PÉRIMÈTRE (étape séparée) → il compte ce que
              le projet servira, pas l'île entière. Wizard et « À trier » : même nombre par construction. */}
          <FiltreProvider value={binding}><FiltreFacettes compteurScope={{ communes: ile ? [] : communes }} /></FiltreProvider>
        </div>
      )}
      {etape === 4 && (
        <div data-projet-recap style={{ marginBottom: 28, border: '.5px solid #1E2A23', background: '#080D0A', borderRadius: 8, padding: '16px 18px' }}>
          <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 8, fontSize: 13, color: '#ECF5EF' }}>
            <li><span style={{ color: '#6F8578' }}>Périmètre : </span>{perimetreLabel}</li>
            {/* OUTILS-5 (P3) — le VRAI chiffre du vivier, classé (plus « N facettes ») + « pourquoi ? ». */}
            <li data-recap-vivier><span style={{ color: '#6F8578' }}>Vivier : </span>
              <b style={{ color: A.c }}>{vivierN != null ? `${vivierN.toLocaleString('fr-FR')} parcelles` : '…'}</b> classées par probabilité de mutation
              {' '}<button data-recap-pourquoi onClick={() => setAlgoModale('scoring')} style={{ color: A.c, background: 'none', border: 0, cursor: 'pointer', textDecoration: 'underline', fontSize: 12 }}>pourquoi ?</button>
            </li>
            {budget.trim() && <li><span style={{ color: '#6F8578' }}>Budget foncier : </span>{parseInt(budget, 10).toLocaleString('fr-FR')} € <em style={{ color: '#6F8578' }}>(indicatif)</em></li>}
            {type && <li><span style={{ color: '#6F8578' }}>Type : </span>{types.find((t) => t.cle === type)?.libelle ?? type} <em style={{ color: '#6F8578' }}>(indicatif)</em></li>}
          </ul>
        </div>
      )}

      {erreur && <p style={{ fontSize: 12, color: '#E0B341', margin: '0 0 12px' }}>{erreur}</p>}

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: 20, borderTop: '.5px solid #1E2A23' }}>
        <button data-projet-retour onClick={reculer} style={{ fontSize: 13, color: '#6F8578', background: 'none', border: 0, cursor: 'pointer' }}>
          ← Retour
        </button>
        <div style={{ display: 'flex', alignItems: 'center', gap: 18 }}>
          <span style={{ fontFamily: MONO, fontSize: 12, color: '#4A5C52' }}>↵ POUR CONTINUER</span>
          {etape < N - 1 ? (
            <button data-projet-suivant onClick={avancer}
              style={{ padding: '9px 18px', background: A.c, color: A.on, borderRadius: 8, fontSize: 14, fontWeight: 500, border: 0, cursor: 'pointer' }}>Continuer →</button>
          ) : (
            <button data-projet-creer disabled={envoi} onClick={() => void creer()}
              style={{ padding: '9px 18px', background: A.c, color: A.on, borderRadius: 8, fontSize: 14, fontWeight: 500, border: 0, cursor: 'pointer', opacity: envoi ? 0.4 : 1 }}>
              {envoi ? 'Création…' : 'Créer le projet'}</button>
          )}
        </div>
      </div>

      {trail.length > 0 && (
        <div data-parcours-trail style={{ marginTop: 20, paddingTop: 16, borderTop: '.5px solid #1E2A23', fontSize: 12, color: '#6F8578', display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          {trail.map((t, i) => (
            <span key={i} style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
              {i > 0 && <span style={{ color: '#2A3A31', marginRight: 4 }}>·</span>}
              <span style={{ color: A.c }}>✓</span>{t}
            </span>
          ))}
        </div>
      )}
      {/* OUTILS-5 (P2) — « pourquoi ? » (récap) ouvre LE composant d'explication de la carte. */}
      {algoModale === 'classement' && <AlgoExplainer onClose={() => setAlgoModale(null)} />}
      {algoModale === 'scoring' && <ScoringExplainer onClose={() => setAlgoModale(null)} />}
    </div>
  )
}
