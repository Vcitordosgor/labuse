// EXPORTS-2 lot 4 — le questionnaire du Financier : 4 écrans, saisies persistées par compte+IDU.
// Trois règles (décisions Vic) :
//  1. chaque champ pré-rempli affiche SA SOURCE en une ligne sous le champ ;
//  2. un champ vidé par le client reste vide → « non chiffré » (jamais un retour au défaut) ;
//  3. le régime de TVA est OBLIGATOIRE (le champ qui décide si le bilan est vrai).
import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getFinancierQuestionnaire, putFinancierQuestionnaire, type QChamp } from '../../lib/api'

const MINT = '#4ADE80'
const CARD = '#0C1410'

const champInput = (unite: string): 'number' | 'text' => (
  ['€', '€/m²', 'm²', '%', 'logements', 'mois', 'nombre'].includes(unite) ? 'number' : 'text')

export function FinancierQuestionnaire({ idu, onClose }: { idu: string; onClose: () => void }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['financier-questionnaire', idu],
    queryFn: () => getFinancierQuestionnaire(idu),
  })
  const [etape, setEtape] = useState(0)
  const [reponses, setReponses] = useState<Record<string, unknown>>({})
  const [envoi, setEnvoi] = useState(false)
  const [erreur, setErreur] = useState<string | null>(null)
  const [fini, setFini] = useState(false)
  const seeded = useRef(false)

  useEffect(() => {
    if (data && !seeded.current) { setReponses(data.reponses || {}); seeded.current = true }
  }, [data])

  const ecrans = data?.ecrans || []
  const N = ecrans.length || 1
  const tvaOk = reponses['regime_tva_saisi'] != null && reponses['regime_tva_saisi'] !== ''

  const set = (id: string, v: unknown) => setReponses((r) => ({ ...r, [id]: v }))

  const enregistrer = async () => {
    if (!tvaOk) { setErreur('Le régime de TVA est obligatoire — il décide si le bilan est vrai.'); setEtape(N - 1); return }
    setEnvoi(true); setErreur(null)
    try { await putFinancierQuestionnaire(idu, reponses); setFini(true) }
    catch { setErreur('L\'enregistrement a échoué — réessayez.') }
    finally { setEnvoi(false) }
  }

  const backdrop: React.CSSProperties = {
    position: 'fixed', inset: 0, background: 'rgba(2,6,4,.72)', zIndex: 4000,
    display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24,
  }
  const card: React.CSSProperties = {
    background: CARD, border: `.5px solid ${MINT}`, borderRadius: 12, padding: 24,
    width: 'min(720px, 96vw)', maxHeight: '92vh', overflow: 'auto', color: '#ECF5EF',
  }

  return (
    <div style={backdrop} onClick={onClose}>
      <div style={card} onClick={(e) => e.stopPropagation()} data-financier-questionnaire>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6 }}>
          <div style={{ fontSize: 11, letterSpacing: '.12em', color: MINT }}>FINANCIER</div>
          <button onClick={onClose} style={{ background: 'none', border: 0, color: '#6F8578', cursor: 'pointer', fontSize: 20 }}>×</button>
        </div>

        {isLoading && <p style={{ color: '#8FA69A' }}>Chargement…</p>}
        {error && <p style={{ color: '#E0B341' }}>Impossible de charger le questionnaire.</p>}

        {fini && (
          <div>
            <h2 style={{ fontSize: 22, fontWeight: 500, margin: '8px 0 6px' }}>Questionnaire enregistré</h2>
            <p style={{ fontSize: 14, color: '#8FA69A', margin: '0 0 20px' }}>
              Le document Financier reprend ces hypothèses. Vous pouvez rouvrir ce questionnaire à tout moment pour les modifier.
            </p>
            {/* RECETTE-2 S2 — le parcours PRODUIT enfin le document : jusqu'ici il s'arrêtait sur
                « enregistré » sans jamais ouvrir le PDF (route /financier/{idu}.pdf pourtant servie).
                Action primaire = ouvrir le document ; « Fermer » devient secondaire. */}
            <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
              <a data-financier-doc href={`/financier/${encodeURIComponent(idu)}.pdf`} target="_blank" rel="noreferrer"
                 style={{ ...btnMint, textDecoration: 'none', display: 'inline-block' }}>
                Ouvrir le document Financier
              </a>
              <button onClick={onClose} style={btnPlain}>Fermer</button>
            </div>
          </div>
        )}

        {!isLoading && !error && !fini && data && (
          <>
            <div style={{ fontSize: 12, color: '#5F7267', marginBottom: 6 }}>{etape + 1} / {N} · {ecrans[etape]?.titre}</div>
            <div style={{ display: 'flex', gap: 5, marginBottom: 22 }}>
              {ecrans.map((_, i) => <i key={i} style={{ flex: 1, height: 2, background: i <= etape ? MINT : '#1E2A23' }} />)}
            </div>
            <h2 style={{ fontSize: 22, fontWeight: 500, margin: '0 0 4px' }}>{ecrans[etape]?.titre}</h2>
            <p style={{ fontSize: 13, color: '#8FA69A', margin: '0 0 20px' }}>
              Tout est pré-rempli avec une valeur sourcée ; vous corrigez ce que vous savez. Un champ vidé s'imprime « non chiffré ».
            </p>

            {(ecrans[etape]?.champs || []).map((c) => (
              <ChampRow key={c.id} c={c} valeur={reponses[c.id]} touche={c.id in reponses}
                        tvaExplication={data.tva_explication} onChange={(v) => set(c.id, v)} />
            ))}

            {erreur && <p style={{ fontSize: 12, color: '#E0B341', margin: '14px 0 0' }}>{erreur}</p>}

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: 18, marginTop: 18, borderTop: '.5px solid #1E2A23' }}>
              <button onClick={() => (etape > 0 ? setEtape(etape - 1) : onClose())} style={btnPlain}>
                {etape > 0 ? '← Retour' : 'Annuler'}
              </button>
              {etape < N - 1
                ? <button onClick={() => setEtape(etape + 1)} style={btnMint}>Continuer →</button>
                : <button disabled={envoi} onClick={() => void enregistrer()} style={{ ...btnMint, opacity: envoi ? 0.4 : 1 }}>
                    {envoi ? 'Enregistrement…' : 'Enregistrer'}
                  </button>}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

const btnMint: React.CSSProperties = {
  padding: '9px 18px', background: MINT, color: '#05140B', borderRadius: 8, fontSize: 14,
  fontWeight: 500, border: 0, cursor: 'pointer',
}
const btnPlain: React.CSSProperties = {
  fontSize: 13, color: '#6F8578', background: 'none', border: 0, cursor: 'pointer',
}

function ChampRow({ c, valeur, touche, tvaExplication, onChange }: {
  c: QChamp; valeur: unknown; touche: boolean; tvaExplication: string; onChange: (v: unknown) => void
}) {
  const prefill = c.prefill
  // valeur affichée : la saisie si le champ a été touché, sinon le pré-remplissage.
  const brute = touche ? valeur : (prefill ? prefill.valeur : undefined)
  const shown = brute == null ? '' : String(brute)
  const vide = touche && (valeur == null || valeur === '')      // règle 2 : vidé → non chiffré
  const num = champInput(c.unite) === 'number'

  const champStyle: React.CSSProperties = {
    width: '100%', height: 42, background: '#060A08', border: '.5px solid #2A3A31',
    borderRadius: 8, padding: '0 14px', fontSize: 15, color: '#ECF5EF', outline: 'none',
    boxSizing: 'border-box',
  }
  const onInput = (raw: string) => {
    if (raw === '') { onChange(null); return }                  // vidé
    onChange(num ? Number(raw) : raw)
  }

  return (
    <div style={{ margin: '0 0 16px' }}>
      <label style={{ display: 'block', fontSize: 13, color: '#C7D6CD', margin: '0 0 6px' }}>
        {c.libelle}{c.unite && c.unite !== 'classe' && c.unite !== 'texte' ? ` (${c.unite})` : ''}
        {c.obligatoire && <span style={{ color: '#E0B341' }}> · obligatoire</span>}
      </label>
      {c.type === 'classe' && c.domaine
        ? <select value={shown} onChange={(e) => onInput(e.target.value)} style={champStyle}>
            <option value="">— à choisir —</option>
            {c.domaine.map((o) => <option key={o} value={o}>{o.replace(/_/g, ' ')}</option>)}
          </select>
        : <input type={num ? 'number' : 'text'} value={shown} onChange={(e) => onInput(e.target.value)} style={champStyle} />}

      {/* règle 1 — la source du pré-remplissage, sous le champ (si non touché) */}
      {prefill && !touche && (
        <p style={{ fontSize: 11, color: '#6F8578', margin: '5px 0 0' }}>Source : {prefill.source}</p>
      )}
      {/* règle 2 — un champ vidé s'imprimera « non chiffré » */}
      {vide && (
        <p style={{ fontSize: 11, color: '#E0B341', margin: '5px 0 0' }}>Laissé vide → « non chiffré » dans le document.</p>
      )}
      {/* règle 3 — l'explication du régime de TVA + renvoi expert-comptable */}
      {c.id === 'regime_tva_saisi' && (
        <p style={{ fontSize: 11, color: '#8FA69A', margin: '6px 0 0' }}>{tvaExplication}</p>
      )}
    </div>
  )
}
