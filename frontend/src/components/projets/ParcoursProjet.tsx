// M113 · Phase 3 → M114 · Phase 1 — LE PARCOURS PROJET GUIDÉ, refondu d'après DA-PROJETS-v1 (font
// foi). UNE question à la fois en 24 px, barre de progression en 5 segments (mint pour les faits),
// compteur « 3 / 5 · PROGRAMME » en mono, cadre mint (seul bloc encadré = la tâche active). Clavier :
// Entrée valide et avance, Échap ferme, Retour revient (« ↵ POUR CONTINUER » en mono discret). Le fil
// des réponses déjà données reste en bas, en petit, avec une coche mint. La commune vient du
// RÉFÉRENTIEL (/communes), jamais du texte libre. Le Copilote ne crée plus jamais directement : il
// ouvre CE formulaire, prérempli de ce qu'il a compris. Même composant côté section Projets.
import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react'
import { createProjet, getCommunes, type CommuneInfo, type FicheProjet } from '../../lib/api'

type Mode = 'logements' | 'surface'
const MONO = 'ui-monospace, SFMono-Regular, Menlo, monospace'
const ETAPES = ['NOM', 'COMMUNE', 'PROGRAMME', 'CRITÈRES', 'RÉCAPITULATIF']

// M117 · gabarit 12 — l'accent est THÉMÉ : MINT dans la section Projets (défaut), MAUVE dans le
// Copilote (surface IA). Le composant est partagé ; seul l'accent change.
const ACCENT_MINT = { c: '#4ADE80', bg: '#12291D', on: '#05140B' }
const ACCENT_IA = { c: '#B497F0', bg: '#1A1430', on: '#14091F' }

export function ParcoursProjet({ prefill, onVoir, onFermer, accent }: {
  prefill?: Record<string, unknown> | null
  onVoir: (projet: { id: number; nom: string }) => void   // « Voir le projet → » (mécanique M107-B)
  onFermer: () => void
  accent?: 'mint' | 'ia'                                   // Projets = mint (défaut) · Copilote = ia (mauve)
  plein?: boolean                                          // page Projets : occupe l'écran (layout géré au-dessus)
}) {
  const A = accent === 'ia' ? ACCENT_IA : ACCENT_MINT   // M117 — accent thémé (mauve dans le Copilote)
  const [communes, setCommunes] = useState<CommuneInfo[]>([])
  useEffect(() => { getCommunes().then(setCommunes).catch(() => {}) }, [])

  const pf = prefill || {}
  const [nom, setNom] = useState('')
  const [commune, setCommune] = useState<string>(typeof pf.commune === 'string' ? pf.commune : '')
  const [mode, setMode] = useState<Mode>('logements')
  const [logements, setLogements] = useState<string>(typeof pf.programme_logements === 'number' ? String(pf.programme_logements) : '')
  const [surface, setSurface] = useState<string>('')
  const [budget, setBudget] = useState<string>(typeof pf.budget_eur === 'number' ? String(pf.budget_eur) : '')
  const [criteres, setCriteres] = useState<string>('')

  const [etape, setEtape] = useState(0)
  const [envoi, setEnvoi] = useState(false)
  const [erreur, setErreur] = useState<string | null>(null)
  const [cree, setCree] = useState<{ id: number; nom: string; existing?: boolean } | null>(null)
  const rootRef = useRef<HTMLDivElement>(null)
  // les étapes à champ ont un autofocus (le keydown remonte au conteneur) ; l'étape RÉCAP n'a pas
  // de champ → on focalise le conteneur pour qu'Entrée y déclenche la création (clavier sans souris).
  useEffect(() => { if (etape === 4) rootRef.current?.focus() }, [etape])

  const progNum = mode === 'logements' ? parseInt(logements || '0', 10) : parseInt(surface || '0', 10)
  const progLabel = progNum > 0 ? (mode === 'logements' ? `${progNum} logements` : `${progNum} m² de plancher`) : null
  const nomEffectif = nom.trim() || (commune ? `Projet ${commune}` : 'Nouveau projet')

  const fiche: FicheProjet = useMemo(() => ({
    type_programme: 'logements',
    ampleur: mode === 'logements' ? { logements: progNum || undefined } : { sdp_m2: progNum || undefined },
    perimetre: { mode: 'communes', communes: commune ? [commune] : [] },
    ...(budget.trim() ? { budget_foncier_eur: parseInt(budget, 10) } : {}),
    ...(criteres.trim() ? { criteres_libres: criteres.trim() } : {}),
  }), [mode, progNum, commune, budget, criteres])

  const peutAvancer = etape === 0 ? true : etape === 1 ? !!commune : etape === 2 ? progNum > 0 : true

  const creer = async () => {
    setEnvoi(true); setErreur(null)
    try {
      const r = await createProjet({ fiche, nom: nom.trim() || undefined })
      setCree({ id: r.projet.id, nom: r.projet.nom, existing: r.existing })
    } catch { setErreur('La création a échoué — vérifiez la commune et le programme, puis réessayez.') }
    finally { setEnvoi(false) }
  }
  const avancer = () => { if (etape < 4) { if (peutAvancer) setEtape(etape + 1) } else void creer() }
  const reculer = () => { if (etape > 0) setEtape(etape - 1); else onFermer() }
  const onKey = (e: KeyboardEvent) => {
    if (e.key === 'Enter') { e.preventDefault(); avancer() }
    else if (e.key === 'Escape') { e.preventDefault(); onFermer() }
  }

  // ── projet créé : « Voir le projet → » (ouvre CE projet) ──
  if (cree) {
    return (
      <div data-parcours-projet-cree style={{ background: '#0C1410', border: `.5px solid ${A.c}`, borderRadius: 12, padding: 24 }}>
        <p style={{ fontSize: 16, color: '#ECF5EF', margin: '0 0 16px' }}>
          Projet créé : <b>{cree.nom}</b>{cree.existing ? ' (il existait déjà)' : ''}.
        </p>
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
    ['Sur quelle commune ?', 'Depuis le référentiel des communes — jamais une saisie libre.'],
    ['Quel est le programme ?', 'Nombre de logements, ou surface de plancher cible.'],
    ['Des critères particuliers ?', 'Budget foncier, contraintes — facultatif.'],
    ['On récapitule.', 'Vérifiez avant de créer — vous pourrez tout rouvrir ensuite.'],
  ]

  // le fil des réponses déjà données (coche mint) — steps franchis, valeurs non vides.
  const trail: string[] = []
  if (etape > 0 && (nom.trim() || commune)) trail.push(nomEffectif)
  if (etape > 1 && commune) trail.push(commune)
  if (etape > 2 && progLabel) trail.push(progLabel)
  if (etape > 3 && budget.trim()) trail.push(`budget ${parseInt(budget, 10).toLocaleString('fr-FR')} €`)

  return (
    <div data-parcours-projet ref={rootRef} tabIndex={-1} onKeyDown={onKey}
      style={{ background: '#0C1410', border: `.5px solid ${A.c}`, borderRadius: 12, padding: 24, outline: 'none' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <div style={{ fontFamily: MONO, fontSize: 11, letterSpacing: '.12em', color: A.c }}>NOUVEAU PROJET</div>
        <div data-parcours-step style={{ fontFamily: MONO, fontSize: 12, color: '#5F7267' }}>{etape + 1} / 5 · {ETAPES[etape]}</div>
      </div>
      {/* barre de progression — 5 segments (mint pour les faits) */}
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
          <select data-projet-commune autoFocus value={commune} onChange={(e) => setCommune(e.target.value)} style={champ}>
            <option value="">— choisir une commune —</option>
            {communes.map((c) => <option key={c.insee} value={c.commune}>{c.commune}</option>)}
          </select>
        </div>
      )}
      {etape === 2 && (
        <div style={{ marginBottom: 28 }}>
          <div style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
            {(['logements', 'surface'] as Mode[]).map((m) => (
              <button key={m} data-projet-mode={m} onClick={() => setMode(m)}
                style={{ padding: '9px 18px', borderRadius: 8, fontSize: 14, cursor: 'pointer',
                  border: mode === m ? `.5px solid ${A.c}` : '.5px solid #1E2A23',
                  background: mode === m ? A.bg : 'transparent', color: mode === m ? A.c : '#8FA69A' }}>
                {m === 'logements' ? 'Logements' : 'Surface de plancher'}
              </button>
            ))}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <input data-projet-programme autoFocus type="number" min="1"
              value={mode === 'logements' ? logements : surface}
              onChange={(e) => (mode === 'logements' ? setLogements : setSurface)(e.target.value)}
              placeholder={mode === 'logements' ? 'Ex. 13' : 'Ex. 2000'} style={{ ...champ, flex: 1 }} />
            <span style={{ fontSize: 14, color: '#6F8578' }}>{mode === 'logements' ? 'logements' : 'm² de plancher'}</span>
          </div>
        </div>
      )}
      {etape === 3 && (
        <div style={{ marginBottom: 28, display: 'flex', flexDirection: 'column', gap: 14 }}>
          <input data-projet-budget autoFocus type="number" min="0" value={budget} onChange={(e) => setBudget(e.target.value)}
            placeholder="Budget foncier en € (facultatif)" style={champ} />
          <input data-projet-criteres value={criteres} onChange={(e) => setCriteres(e.target.value)}
            placeholder="Critères libres (facultatif)" style={{ ...champ, fontSize: 16 }} />
        </div>
      )}
      {etape === 4 && (
        <div data-projet-recap style={{ marginBottom: 28, border: '.5px solid #1E2A23', background: '#080D0A', borderRadius: 8, padding: '16px 18px' }}>
          <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 8, fontSize: 13, color: '#ECF5EF' }}>
            <li><span style={{ color: '#6F8578' }}>Nom : </span>{nomEffectif}</li>
            <li><span style={{ color: '#6F8578' }}>Commune : </span>{commune || <em style={{ color: '#E0B341' }}>à choisir</em>}</li>
            <li><span style={{ color: '#6F8578' }}>Programme : </span>{progLabel || <em style={{ color: '#E0B341' }}>à renseigner</em>}</li>
            {budget.trim() && <li><span style={{ color: '#6F8578' }}>Budget foncier : </span>{parseInt(budget, 10).toLocaleString('fr-FR')} €</li>}
            {criteres.trim() && <li><span style={{ color: '#6F8578' }}>Critères : </span>{criteres.trim()}</li>}
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
          {etape < 4 ? (
            <button data-projet-suivant disabled={!peutAvancer} onClick={avancer}
              style={{ padding: '9px 18px', background: A.c, color: A.on, borderRadius: 8, fontSize: 14, fontWeight: 500, border: 0, cursor: 'pointer', opacity: peutAvancer ? 1 : 0.4 }}>Continuer →</button>
          ) : (
            <button data-projet-creer disabled={envoi || !commune || progNum <= 0} onClick={() => void creer()}
              style={{ padding: '9px 18px', background: A.c, color: A.on, borderRadius: 8, fontSize: 14, fontWeight: 500, border: 0, cursor: 'pointer', opacity: (envoi || !commune || progNum <= 0) ? 0.4 : 1 }}>
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
