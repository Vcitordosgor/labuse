// M113 · Phase 3 — LE PARCOURS PROJET GUIDÉ. La création de projet quitte le langage naturel : un
// parcours en étapes, champ par champ (nom → commune → programme → critères → récap → créer). La
// commune vient du RÉFÉRENTIEL (/communes), jamais du texte libre. Le Copilote ne crée plus jamais
// directement : il ouvre CE formulaire, prérempli de ce qu'il a compris ; l'utilisateur vérifie,
// complète, valide. Le formulaire protège par construction (valeurs contrôlées, création explicite).
// Même composant côté section Projets (accès direct, sans Copilote) : `onVoir` navigue vers le projet.
import { useEffect, useMemo, useState } from 'react'
import { createProjet, getCommunes, type CommuneInfo, type FicheProjet } from '../../lib/api'

type Mode = 'logements' | 'surface'

export function ParcoursProjet({ prefill, onVoir, onFermer }: {
  prefill?: Record<string, unknown> | null
  onVoir: (projet: { id: number; nom: string }) => void   // « Voir le projet → » (mécanique M107-B)
  onFermer: () => void
}) {
  const [communes, setCommunes] = useState<CommuneInfo[]>([])
  useEffect(() => { getCommunes().then(setCommunes).catch(() => {}) }, [])

  // préremplissage COMPRIS (texte libre → chip « Créer un projet ») : commune, logements, budget.
  const pf = prefill || {}
  const [nom, setNom] = useState('')
  const [commune, setCommune] = useState<string>(typeof pf.commune === 'string' ? pf.commune : '')
  const [mode, setMode] = useState<Mode>('logements')
  const [logements, setLogements] = useState<string>(
    typeof pf.programme_logements === 'number' ? String(pf.programme_logements) : '')
  const [surface, setSurface] = useState<string>('')
  const [budget, setBudget] = useState<string>(typeof pf.budget_eur === 'number' ? String(pf.budget_eur) : '')
  const [criteres, setCriteres] = useState<string>('')

  const [etape, setEtape] = useState(0)   // 0 nom · 1 commune · 2 programme · 3 critères · 4 récap
  const [envoi, setEnvoi] = useState(false)
  const [erreur, setErreur] = useState<string | null>(null)
  const [cree, setCree] = useState<{ id: number; nom: string; existing?: boolean } | null>(null)

  const progNum = mode === 'logements' ? parseInt(logements || '0', 10) : parseInt(surface || '0', 10)
  const nomEffectif = nom.trim() || (commune ? `Projet ${commune}` : 'Nouveau projet')
  const etapes = ['Nom', 'Commune', 'Programme', 'Critères', 'Récapitulatif']
  const peutAvancer = (
    etape === 0 ? true :                                  // le nom est facultatif (dérivé sinon)
    etape === 1 ? !!commune :                             // la commune est OBLIGATOIRE (référentiel)
    etape === 2 ? progNum > 0 :                           // un programme chiffré est obligatoire
    true)                                                 // critères facultatifs · récap

  const fiche: FicheProjet = useMemo(() => ({
    type_programme: 'logements',
    ampleur: mode === 'logements' ? { logements: progNum || undefined } : { sdp_m2: progNum || undefined },
    perimetre: { mode: 'communes', communes: commune ? [commune] : [] },
    ...(budget.trim() ? { budget_foncier_eur: parseInt(budget, 10) } : {}),
    ...(criteres.trim() ? { criteres_libres: criteres.trim() } : {}),
  }), [mode, progNum, commune, budget, criteres])

  const creer = async () => {
    setEnvoi(true); setErreur(null)
    try {
      const r = await createProjet({ fiche, nom: nom.trim() || undefined })
      setCree({ id: r.projet.id, nom: r.projet.nom, existing: r.existing })
    } catch {
      setErreur("La création a échoué — vérifiez la commune et le programme, puis réessayez.")
    } finally { setEnvoi(false) }
  }

  const champCls = 'w-full rounded-lg border border-cp-line2 bg-cp-card2 px-3.5 py-2.5 text-[13px] text-cp-txt outline-none placeholder:text-cp-faint focus:border-mint'
  const primaire = 'rounded-lg bg-mint px-5 py-2.5 font-display text-[12.5px] font-bold text-mint-on transition-[filter] duration-quick hover:brightness-110 disabled:opacity-40'
  const secondaire = 'rounded-lg border border-cp-line px-4 py-2.5 font-display text-[12px] font-semibold text-cp-muted transition-colors duration-quick hover:border-cp-line2 hover:text-cp-txt'

  // ── projet créé : la sortie porte « Voir le projet → » (ouvre CE projet) ──
  if (cree) {
    return (
      <div data-parcours-projet-cree className="rounded-2xl border border-mint/30 bg-cp-card px-5 py-5">
        <p className="text-[14px] text-cp-txt">
          Projet créé : <b>{cree.nom}</b>{cree.existing ? ' (il existait déjà)' : ''}.
        </p>
        <div className="mt-3.5 flex gap-2">
          <button data-projet-voir onClick={() => onVoir({ id: cree.id, nom: cree.nom })} className={primaire}>Voir le projet →</button>
          <button onClick={onFermer} className={secondaire}>Fermer</button>
        </div>
      </div>
    )
  }

  return (
    <div data-parcours-projet className="rounded-2xl border border-mint/25 bg-cp-card px-5 py-5">
      {/* fil d'étapes */}
      <div className="mb-4 flex items-center gap-2">
        {etapes.map((e, i) => (
          <div key={e} className="flex items-center gap-2">
            <span className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold ${
              i < etape ? 'bg-mint text-mint-on' : i === etape ? 'border border-mint text-mint' : 'border border-cp-line text-cp-faint'}`}>
              {i + 1}
            </span>
            <span className={`font-display text-[11px] ${i === etape ? 'text-cp-txt' : 'text-cp-faint'}`}>{e}</span>
            {i < etapes.length - 1 && <span className="text-cp-faint">·</span>}
          </div>
        ))}
      </div>

      {etape === 0 && (
        <label className="block">
          <span className="mb-1.5 block font-display text-[12px] font-semibold text-cp-txt">Nom du projet <span className="text-cp-faint">(facultatif)</span></span>
          <input data-projet-nom autoFocus value={nom} onChange={(e) => setNom(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') setEtape(1) }}
            placeholder={`Ex. ${nomEffectif}`} className={champCls} />
        </label>
      )}

      {etape === 1 && (
        <label className="block">
          <span className="mb-1.5 block font-display text-[12px] font-semibold text-cp-txt">Commune</span>
          <select data-projet-commune autoFocus value={commune} onChange={(e) => setCommune(e.target.value)} className={champCls}>
            <option value="">— choisir une commune —</option>
            {communes.map((c) => <option key={c.insee} value={c.commune}>{c.commune}</option>)}
          </select>
          <span className="mt-1.5 block text-[11px] text-cp-faint">Depuis le référentiel des communes — jamais une saisie libre.</span>
        </label>
      )}

      {etape === 2 && (
        <div>
          <span className="mb-1.5 block font-display text-[12px] font-semibold text-cp-txt">Programme</span>
          <div className="mb-2.5 flex gap-2">
            <button data-projet-mode-logements onClick={() => setMode('logements')}
              className={mode === 'logements' ? 'rounded-lg border border-mint bg-mint/15 px-3.5 py-1.5 text-[12px] font-semibold text-mint' : secondaire}>
              Logements
            </button>
            <button data-projet-mode-surface onClick={() => setMode('surface')}
              className={mode === 'surface' ? 'rounded-lg border border-mint bg-mint/15 px-3.5 py-1.5 text-[12px] font-semibold text-mint' : secondaire}>
              Surface de plancher
            </button>
          </div>
          {mode === 'logements' ? (
            <input data-projet-logements autoFocus type="number" min="1" value={logements}
              onChange={(e) => setLogements(e.target.value)} placeholder="Nombre de logements (ex. 15)" className={champCls} />
          ) : (
            <input data-projet-surface autoFocus type="number" min="1" value={surface}
              onChange={(e) => setSurface(e.target.value)} placeholder="Surface de plancher en m² (ex. 2000)" className={champCls} />
          )}
        </div>
      )}

      {etape === 3 && (
        <div className="flex flex-col gap-3">
          <label className="block">
            <span className="mb-1.5 block font-display text-[12px] font-semibold text-cp-txt">Budget foncier <span className="text-cp-faint">(facultatif, €)</span></span>
            <input data-projet-budget type="number" min="0" value={budget} onChange={(e) => setBudget(e.target.value)}
              placeholder="Ex. 800000" className={champCls} />
          </label>
          <label className="block">
            <span className="mb-1.5 block font-display text-[12px] font-semibold text-cp-txt">Critères libres <span className="text-cp-faint">(facultatif)</span></span>
            <input data-projet-criteres value={criteres} onChange={(e) => setCriteres(e.target.value)}
              placeholder="Ex. proximité transport, hors PPR rouge…" className={champCls} />
          </label>
        </div>
      )}

      {etape === 4 && (
        <div data-projet-recap className="rounded-lg border border-cp-line bg-cp-card2 px-4 py-3 text-[13px] text-cp-txt">
          <p className="mb-1.5 font-display text-[11px] uppercase tracking-[.14em] text-mint">Récapitulatif</p>
          <ul className="flex flex-col gap-1 text-[12.5px]">
            <li><span className="text-cp-muted">Nom :</span> {nomEffectif}</li>
            <li><span className="text-cp-muted">Commune :</span> {commune || <em className="text-cp-amber">à choisir</em>}</li>
            <li><span className="text-cp-muted">Programme :</span> {progNum > 0
              ? (mode === 'logements' ? `${progNum} logements` : `${progNum} m² de plancher`)
              : <em className="text-cp-amber">à renseigner</em>}</li>
            {budget.trim() && <li><span className="text-cp-muted">Budget foncier :</span> {parseInt(budget, 10).toLocaleString('fr-FR')} €</li>}
            {criteres.trim() && <li><span className="text-cp-muted">Critères :</span> {criteres.trim()}</li>}
          </ul>
        </div>
      )}

      {erreur && <p className="mt-3 text-[12px] text-cp-amber">{erreur}</p>}

      <div className="mt-4 flex items-center justify-between gap-2">
        <button onClick={etape === 0 ? onFermer : () => setEtape(etape - 1)} className={secondaire}>
          {etape === 0 ? 'Annuler' : '← Retour'}
        </button>
        {etape < 4 ? (
          <button data-projet-suivant disabled={!peutAvancer} onClick={() => setEtape(etape + 1)} className={primaire}>
            Continuer →
          </button>
        ) : (
          <button data-projet-creer disabled={envoi || !commune || progNum <= 0} onClick={() => void creer()} className={primaire}>
            {envoi ? 'Création…' : 'Créer le projet'}
          </button>
        )}
      </div>
    </div>
  )
}
