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
  // RECETTE-6 (E5) — écran 0 : on ne montre les 4 écrans QUE lorsqu'un usage servi est choisi.
  const [usage, setUsage] = useState<string | null>(null)
  const [reponses, setReponses] = useState<Record<string, unknown>>({})
  const [envoi, setEnvoi] = useState(false)
  const [erreur, setErreur] = useState<string | null>(null)
  const [fini, setFini] = useState(false)
  const [docErr, setDocErr] = useState<{ libelle: string; raison?: string }[] | null>(null)
  // RECETTE-7 (C1) — un ÉCHEC TECHNIQUE et une DONNÉE MANQUANTE sont deux choses différentes :
  // le bandeau « il manque : » ne s'affiche que s'il peut NOMMER les champs (docErr) ; une erreur
  // de génération (500, réseau) est dite comme telle, séparément (docTech).
  const [docTech, setDocTech] = useState<string | null>(null)
  // RECETTE-8 W19bis — la saisie appartient à LA PARCELLE : on re-sème une seule fois PAR IDU.
  // Avant, `seeded` restait vrai après la 1re parcelle → en rouvrant le questionnaire sur une AUTRE
  // parcelle (sans démontage du composant), les réponses de la précédente restaient à l'écran. On
  // repère l'IDU semé ; à tout changement d'IDU on recharge les réponses de la nouvelle parcelle
  // (vierge si jamais saisie ; seuls les pré-remplissages SOURCÉS réapparaissent, via `c.prefill`)
  // et on remet l'assistant à zéro. Sur la MÊME parcelle, la saisie enregistrée est bien retrouvée.
  const seededIdu = useRef<string | null>(null)

  useEffect(() => {
    if (data && seededIdu.current !== idu) {
      const rep = data.reponses || {}
      setReponses(rep)
      seededIdu.current = idu
      // RECETTE-8 W13bis — restaure le parcours choisi (_usage) s'il a déjà été saisi sur CETTE
      // parcelle ; sinon écran 0 « Que voulez-vous chiffrer ? ».
      const u = rep['_usage']
      setUsage(u === 'construction' || u === 'revente' ? u : null)
      setEtape(0); setFini(false)
      setDocErr(null); setDocTech(null)
    }
  }, [data, idu])

  // RECETTE-8 W13bis — les écrans du PARCOURS choisi (construction = bilan à rebours ; revente =
  // calcul de marge). Repli sur les écrans construction tant qu'aucun usage n'est choisi.
  const ecrans = (usage && data?.ecrans_par_usage?.[usage]) || data?.ecrans || []
  const N = ecrans.length || 1

  const set = (id: string, v: unknown) => setReponses((r) => ({ ...r, [id]: v }))

  // RECETTE-5 (V19) — un champ INDISPENSABLE est « rempli » s'il porte une saisie non vide (ou, à défaut
  // de saisie, un pré-remplissage — mais les deux champs obligatoires n'en ont pas : ils DOIVENT être
  // saisis). Les champs obligatoires bloquent : « Continuer » sur leur écran, et « Enregistrer » au bout.
  const rempli = (c: QChamp): boolean => {
    const v = reponses[c.id]
    if (v != null && v !== '') return true
    return !(c.id in reponses) && c.prefill != null
  }
  const manquantsEcran = (i: number) => (ecrans[i]?.champs || []).filter((c) => c.obligatoire && !rempli(c))
  const tousManquants = () => {
    const out: { c: QChamp; i: number }[] = []
    ecrans.forEach((e, i) => e.champs.forEach((c) => { if (c.obligatoire && !rempli(c)) out.push({ c, i }) }))
    return out
  }

  const continuer = () => {
    const m = manquantsEcran(etape)
    if (m.length) { setErreur(`À renseigner avant de continuer : ${m.map((c) => c.libelle).join(', ')}.`); return }
    setErreur(null); setEtape(etape + 1)
  }

  const enregistrer = async () => {
    const m = tousManquants()
    if (m.length) {
      setErreur(`Indispensable(s) au calcul, encore vide(s) : ${m.map((x) => x.c.libelle).join(', ')}.`)
      setEtape(m[0].i); return
    }
    setEnvoi(true); setErreur(null)
    try { await putFinancierQuestionnaire(idu, reponses); setFini(true) }
    catch { setErreur('L\'enregistrement a échoué — réessayez.') }
    finally { setEnvoi(false) }
  }

  // RECETTE-5 (V18b) — ouvrir le document : si le back répond 422 (non établissable), on N'OUVRE PAS de
  // pages vides — on affiche ici la liste des éléments manquants (structure : ex. « programme constructible »).
  const ouvrirDoc = async () => {
    setDocErr(null); setDocTech(null)
    try {
      const r = await fetch(`/financier/${encodeURIComponent(idu)}.pdf`)
      // 422 = données INDISPENSABLES manquantes : on NOMME les champs (« il manque : … »).
      if (r.status === 422) {
        const d = await r.json().catch(() => null)
        setDocErr(d?.detail?.manques ?? [{ libelle: 'Éléments indispensables manquants' }])
        return
      }
      // tout autre échec = TECHNIQUE (500, réseau) : message d'erreur, jamais « il manque : ».
      if (!r.ok) { setDocTech('Le document n\'a pas pu être généré (erreur technique). Réessayez ; si cela persiste, signalez-le au support.'); return }
      const blob = await r.blob()
      window.open(URL.createObjectURL(blob), '_blank', 'noopener')
    } catch { setDocTech('Le document n\'a pas pu être généré — vérifiez votre connexion et réessayez.') }
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
              <button data-financier-doc onClick={() => void ouvrirDoc()}
                 style={{ ...btnMint, display: 'inline-block' }}>
                Ouvrir le Dossier financier
              </button>
              <button onClick={onClose} style={btnPlain}>Fermer</button>
            </div>
            {/* RECETTE-5 (V18b) — le document ne s'est pas généré : on dit lesquels des éléments manquent. */}
            {docErr && (
              <div data-financier-manques style={{ marginTop: 16, padding: 14, border: '.5px solid #E0B341', borderRadius: 8, background: 'rgba(224,179,65,.06)' }}>
                <p style={{ fontSize: 13, color: '#E0B341', margin: '0 0 8px', fontWeight: 500 }}>
                  Le Dossier financier ne peut pas être établi — il manque :
                </p>
                <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, color: '#C7D6CD' }}>
                  {docErr.map((m, i) => (
                    <li key={i} style={{ marginBottom: 4 }}><b>{m.libelle}</b>{m.raison ? ` — ${m.raison}` : ''}</li>
                  ))}
                </ul>
              </div>
            )}
            {/* RECETTE-7 (C1) — l'échec TECHNIQUE, dit comme tel (jamais sous « il manque : »). */}
            {docTech && (
              <div data-financier-tech style={{ marginTop: 16, padding: 14, border: '.5px solid #E0776B', borderRadius: 8, background: 'rgba(224,119,107,.06)' }}>
                <p style={{ fontSize: 13, color: '#E0776B', margin: 0 }}>{docTech}</p>
              </div>
            )}
          </div>
        )}

        {/* RECETTE-6 (E5) — ÉCRAN 0 « Que voulez-vous chiffrer ? ». Un seul moteur (le bilan à rebours,
            construction neuve) : les autres usages sont GRISÉS avec leur raison, jamais un formulaire faux. */}
        {!isLoading && !error && !fini && data && usage === null && (
          <>
            <h2 style={{ fontSize: 22, fontWeight: 500, margin: '8px 0 4px' }}>Que voulez-vous chiffrer ?</h2>
            <p style={{ fontSize: 13, color: '#8FA69A', margin: '0 0 20px' }}>
              Le chiffrage part de votre intention. Un seul parcours est servi aujourd'hui — les autres arrivent.
            </p>
            <div data-financier-usages style={{ display: 'grid', gap: 10 }}>
              {(data.usages || [{ key: 'construction', label: 'Construction neuve', servi: true }]).map((u) => (
                <button key={u.key} data-usage={u.key} data-usage-servi={u.servi ? '1' : '0'}
                  disabled={!u.servi}
                  onClick={() => { if (u.servi) { setUsage(u.key); set('_usage', u.key); setEtape(0) } }}
                  style={{
                    textAlign: 'left', padding: '14px 16px', borderRadius: 10, cursor: u.servi ? 'pointer' : 'not-allowed',
                    background: u.servi ? 'rgba(74,222,128,.06)' : 'transparent',
                    border: `.5px solid ${u.servi ? MINT : '#26332C'}`, color: u.servi ? '#ECF5EF' : '#5F7267',
                    opacity: u.servi ? 1 : 0.7,
                  }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 15, fontWeight: 500 }}>{u.label}</span>
                    <span style={{ fontSize: 11, color: u.servi ? MINT : '#5F7267' }}>{u.servi ? 'Disponible' : 'Bientôt'}</span>
                  </div>
                  <div style={{ fontSize: 12, color: u.servi ? '#8FA69A' : '#586A5F', marginTop: 4, lineHeight: 1.4 }}>
                    {u.servi ? (u.sous || '') : (u.raison || 'Pas encore servi.')}
                  </div>
                </button>
              ))}
            </div>
            <div style={{ paddingTop: 18, marginTop: 18, borderTop: '.5px solid #1E2A23' }}>
              <button onClick={onClose} style={btnPlain}>Annuler</button>
            </div>
          </>
        )}

        {!isLoading && !error && !fini && data && usage !== null && (
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
              <button onClick={() => (etape > 0 ? setEtape(etape - 1) : setUsage(null))} style={btnPlain}>
                ← Retour
              </button>
              {etape < N - 1
                ? <button onClick={continuer} style={btnMint}>Continuer →</button>
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
  // RECETTE-6 (E1) — le « i » du questionnaire n'affichait rien (tooltip natif `title`, invisible/flaky).
  // On rend une VRAIE bulle d'aide au survol (popover positionné), fiable sur les QUATRE écrans.
  const [aideOpen, setAideOpen] = useState(false)
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

  // RECETTE-7 (C2) — pas de DOUBLON d'aide : là où une explication est déjà imprimée SOUS le champ
  // (la source d'un pré-remplissage non touché, ou l'explication du régime de TVA), la bulle « i »
  // au survol répétait mot pour mot. On garde le texte sous le champ et on RETIRE la bulle ; la
  // bulle reste sur les champs SANS texte dessous (ex. un champ saisi, source masquée).
  const aideSousChamp = (!!prefill && !touche) || c.id === 'regime_tva_saisi'

  return (
    <div style={{ margin: '0 0 16px' }}>
      <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: '#C7D6CD', margin: '0 0 6px' }}>
        <span>{c.libelle}{c.unite && c.unite !== 'classe' && c.unite !== 'texte' ? ` (${c.unite})` : ''}</span>
        {/* RECETTE-6 (E1) — le « i » : ce qu'on attend comme valeur, en bulle d'aide FIABLE au survol.
            RECETTE-7 (C2) — masquée quand l'explication est déjà sous le champ (plus de doublon). */}
        {c.aide && !aideSousChamp && (
          <span style={{ position: 'relative', display: 'inline-flex' }}
            onMouseEnter={() => setAideOpen(true)} onMouseLeave={() => setAideOpen(false)}>
            <span data-champ-aide title={c.aide}
              style={{ display: 'inline-flex', width: 14, height: 14, borderRadius: 999, border: '1px solid #4A5A52',
                color: '#8FA69A', fontSize: 9, fontWeight: 700, alignItems: 'center', justifyContent: 'center', cursor: 'help', flex: 'none' }}>i</span>
            {aideOpen && (
              <span data-champ-aide-pop role="tooltip"
                style={{ position: 'absolute', bottom: '150%', left: 0, zIndex: 50, width: 250, whiteSpace: 'normal',
                  background: '#0A0F0C', border: '.5px solid #2A3A31', borderRadius: 6, padding: '8px 10px',
                  fontSize: 11, fontWeight: 400, lineHeight: 1.45, color: '#C7D6CD', boxShadow: '0 6px 20px rgba(0,0,0,.45)' }}>
                {c.aide}
              </span>
            )}
          </span>
        )}
        {c.obligatoire
          ? <span style={{ color: '#E0B341' }}>· indispensable</span>
          : <span style={{ color: '#5F7267' }}>· facultatif</span>}
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
