// M120 — LE PARCOURS PROJET : IDENTITÉ (nom · périmètre · budget · type · livraison) → CADRAGE
// (les facettes de la carte, RÉUTILISÉES via FiltreFacettes) → CRÉER = le run part UNE FOIS, la
// shortlist est figée et datée. Doctrine : un critère = un seul endroit (le périmètre et les
// facettes vivent dans le cadrage) ; le budget, le type et la date sont INFORMATIFS et l'écran le
// DIT (« indicatif — sans effet sur la sélection »). DA-PROJETS-v1 : une question à la fois en
// 24 px, progression en segments, clavier (Entrée avance, Échap ferme, Retour recule).
import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react'

import { createProjet, getProjetTypes, type Cadrage, type Identite, type ShortlistDiff, type TypeLogement } from '../../lib/api'
import { CP_COMMUNES } from '../panel/FiltreLabuse'
import { FiltreFacettes } from '../panel/FiltreFacettes'
import { FiltreProvider } from '../panel/filtreContext'
import { EMPTY_FILTERS, type Filters } from '../../store/useApp'

const MONO = 'ui-monospace, SFMono-Regular, Menlo, monospace'
const ETAPES = ['NOM', 'PÉRIMÈTRE', 'BUDGET', 'TYPE', 'CADRAGE', 'RÉCAPITULATIF']
const N = ETAPES.length

// M117 · gabarit 12 — accent THÉMÉ : MINT dans la section Projets, MAUVE dans le Copilote.
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
  const [etape, setEtape] = useState(0)
  const [nom, setNom] = useState('')
  const [ile, setIle] = useState(false)
  const [communes, setCommunes] = useState<string[]>(typeof pf.commune === 'string' ? [pf.commune] : [])
  const [budget, setBudget] = useState<string>(typeof pf.budget_eur === 'number' ? String(pf.budget_eur) : '')
  const [type, setType] = useState<string>('')
  // le CADRAGE local (les facettes) — un jeu de filtres complet, isolé du store de la carte.
  const [cadrageFacettes, setCadrageFacettes] = useState<Filters>({ ...EMPTY_FILTERS })
  const [envoi, setEnvoi] = useState(false)
  const [erreur, setErreur] = useState<string | null>(null)
  const [cree, setCree] = useState<{ id: number; nom: string; existing?: boolean; shortlist?: ShortlistDiff } | null>(null)
  const [types, setTypes] = useState<TypeLogement[]>([])
  const rootRef = useRef<HTMLDivElement>(null)
  useEffect(() => { getProjetTypes().then((r) => setTypes(r.types)).catch(() => {}) }, [])
  useEffect(() => { if (etape === N - 1) rootRef.current?.focus() }, [etape])

  const nomEffectif = nom.trim() || (communes.length === 1 ? `Projet ${communes[0]}` : 'Nouveau projet')
  const perimetreLabel = ile || communes.length === 0 ? "toute l'île"
    : communes.length === 1 ? communes[0] : `${communes.length} communes`

  // le binding partagé : FiltreFacettes écrit ICI (jamais dans le store de la carte).
  const binding = useMemo(() => ({
    filters: cadrageFacettes,
    setFilter: <K extends keyof Filters>(k: K, v: Filters[K]) =>
      setCadrageFacettes((c) => ({ ...c, [k]: v })),
  }), [cadrageFacettes])

  // le CADRAGE servi = les facettes + le périmètre (un seul endroit) ; budget/type/date = identité.
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

  const creer = async () => {
    setEnvoi(true); setErreur(null)
    try {
      const r = await createProjet({ cadrage, identite, nom: nom.trim() || undefined })
      setCree({ id: r.projet.id, nom: r.projet.nom, existing: r.existing, shortlist: r.shortlist })
    } catch { setErreur('La création a échoué — réessayez.') }
    finally { setEnvoi(false) }
  }
  const avancer = () => { if (etape < N - 1) setEtape(etape + 1); else void creer() }
  const reculer = () => { if (etape > 0) setEtape(etape - 1); else onFermer() }
  const onKey = (e: KeyboardEvent) => {
    // sur le CADRAGE (étape 4), Entrée est laissée aux champs de facette (ne pas avancer par mégarde).
    if (e.key === 'Enter' && etape !== 4) { e.preventDefault(); avancer() }
    else if (e.key === 'Escape') { e.preventDefault(); onFermer() }
  }

  // ── projet créé : la shortlist est figée ──
  if (cree) {
    const d = cree.shortlist
    return (
      <div data-parcours-projet-cree style={{ background: '#0C1410', border: `.5px solid ${A.c}`, borderRadius: 12, padding: 24 }}>
        <p style={{ fontSize: 16, color: '#ECF5EF', margin: '0 0 8px' }}>
          Projet créé : <b>{cree.nom}</b>{cree.existing ? ' (il existait déjà)' : ''}.
        </p>
        {d && <p data-cree-shortlist style={{ fontSize: 13, color: '#8FA69A', margin: '0 0 16px' }}>
          {/* M120-B — la shortlist se DIT : top-N du vivier, ou tout le vivier s'il tient sous le cap. */}
          {d.tronquee
            ? <>Shortlist figée : les <b style={{ color: A.c }}>{d.n_shortlist}</b> meilleures sur <b style={{ color: '#ECF5EF' }}>{d.vivier.toLocaleString('fr-FR')}</b> parcelles du vivier, classées par probabilité de mutation.</>
            : <>Shortlist figée : <b style={{ color: A.c }}>{d.n_shortlist}</b> parcelle{d.n_shortlist > 1 ? 's' : ''} — c’est tout le vivier figeable.</>}
        </p>}
        <div style={{ display: 'flex', gap: 12 }}>
          <button data-projet-voir onClick={() => onVoir({ id: cree.id, nom: cree.nom })}
            style={{ padding: '9px 18px', background: A.c, color: A.on, borderRadius: 8, fontSize: 14, fontWeight: 500, border: 0, cursor: 'pointer' }}>Voir le projet →</button>
          <button onClick={onFermer} style={{ padding: '9px 18px', background: 'none', border: '.5px solid #1E2A23', color: '#8FA69A', borderRadius: 8, fontSize: 13, cursor: 'pointer' }}>Fermer</button>
        </div>
      </div>
    )
  }

  const champ = { width: '100%', height: 52, background: '#060A08', border: '.5px solid #2A3A31', borderRadius: 8, padding: '0 16px', fontSize: 22, color: '#ECF5EF', outline: 'none' } as const
  const QUESTIONS = [
    ['Quel nom pour ce projet ?', 'Facultatif — un nom vous aide à le retrouver.'],
    ['Sur quel périmètre ?', 'Une ou plusieurs communes, ou toute l’île.'],
    ['Un budget foncier ?', 'Indicatif — il figure sur le projet, sans effet sur la sélection.'],
    ['Quel type de logement ?', 'Indicatif — le moteur ne distingue pas les parcelles par type.'],
    ['Affinez le cadrage.', 'Les mêmes critères que la carte. La shortlist sera figée sur ce cadrage.'],
    ['On récapitule.', 'Vérifiez avant de créer — le cadrage restera modifiable.'],
  ]
  const noteInfo = (txt: string) => (
    <p style={{ fontSize: 12, color: '#6F8578', margin: '10px 0 0', display: 'flex', alignItems: 'center', gap: 6 }}>
      <span style={{ color: '#E0B341' }}>ⓘ</span>{txt}
    </p>
  )

  const trail: string[] = []
  if (etape > 0 && nom.trim()) trail.push(nomEffectif)
  if (etape > 1) trail.push(perimetreLabel)
  if (etape > 2 && budget.trim()) trail.push(`budget ${parseInt(budget, 10).toLocaleString('fr-FR')} € (indic.)`)
  if (etape > 3 && type) trail.push(`${types.find((t) => t.cle === type)?.libelle ?? type} (indic.)`)

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
      {etape === 2 && (
        <div style={{ marginBottom: 28 }}>
          <input data-projet-budget autoFocus type="number" min="0" value={budget} onChange={(e) => setBudget(e.target.value)}
            placeholder="Budget foncier en € (facultatif)" style={champ} />
          {noteInfo('Indicatif — sans effet sur la sélection des parcelles.')}
        </div>
      )}
      {etape === 3 && (
        <div style={{ marginBottom: 28 }}>
          <div data-projet-type style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {types.map((t) => {
              const on = type === t.cle
              return (
                <button key={t.cle} onClick={() => setType(on ? '' : t.cle)}
                  style={{ padding: '9px 16px', borderRadius: 8, fontSize: 14, cursor: 'pointer', border: on ? `.5px solid ${A.c}` : '.5px solid #1E2A23', background: on ? A.bg : 'transparent', color: on ? A.c : '#8FA69A' }}>{t.libelle}</button>
              )
            })}
          </div>
          {noteInfo('Indicatif — le moteur ne distingue pas les parcelles par type de logement.')}
        </div>
      )}
      {etape === 4 && (
        <div data-projet-cadrage style={{ marginBottom: 28, maxHeight: '52vh', overflowY: 'auto' }}>
          <p style={{ fontSize: 12, color: '#6F8578', margin: '0 0 14px' }}>Périmètre : <b style={{ color: '#ECF5EF' }}>{perimetreLabel}</b> · modifiable à l’étape précédente.</p>
          <FiltreProvider value={binding}><FiltreFacettes /></FiltreProvider>
        </div>
      )}
      {etape === 5 && (
        <div data-projet-recap style={{ marginBottom: 28, border: '.5px solid #1E2A23', background: '#080D0A', borderRadius: 8, padding: '16px 18px' }}>
          <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 8, fontSize: 13, color: '#ECF5EF' }}>
            <li><span style={{ color: '#6F8578' }}>Nom : </span>{nomEffectif}</li>
            <li><span style={{ color: '#6F8578' }}>Périmètre : </span>{perimetreLabel}</li>
            <li><span style={{ color: '#6F8578' }}>Cadrage : </span>{Object.keys(cadrage).filter((k) => k !== 'communes').length} facette{Object.keys(cadrage).filter((k) => k !== 'communes').length > 1 ? 's' : ''} active{Object.keys(cadrage).filter((k) => k !== 'communes').length > 1 ? 's' : ''}</li>
            {budget.trim() && <li><span style={{ color: '#6F8578' }}>Budget foncier : </span>{parseInt(budget, 10).toLocaleString('fr-FR')} € <em style={{ color: '#6F8578' }}>(indicatif)</em></li>}
            {type && <li><span style={{ color: '#6F8578' }}>Type : </span>{types.find((t) => t.cle === type)?.libelle ?? type} <em style={{ color: '#6F8578' }}>(indicatif)</em></li>}
          </ul>
        </div>
      )}

      {erreur && <p style={{ fontSize: 12, color: '#E0B341', margin: '0 0 12px' }}>{erreur}</p>}

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: 20, borderTop: '.5px solid #1E2A23' }}>
        <button data-projet-retour onClick={reculer} style={{ fontSize: 13, color: '#6F8578', background: 'none', border: 0, cursor: 'pointer' }}>
          {etape === 0 ? '× Annuler' : '← Retour'}
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
    </div>
  )
}
