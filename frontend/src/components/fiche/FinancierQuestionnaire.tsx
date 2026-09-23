// EXPORTS-2 lot 4 — le questionnaire du Financier : 4 écrans, saisies persistées par compte+IDU.
// Trois règles (décisions Vic) :
//  1. chaque champ pré-rempli affiche SA SOURCE en une ligne sous le champ ;
//  2. un champ vidé par le client reste vide → « non chiffré » (jamais un retour au défaut) ;
//  3. le régime de TVA est OBLIGATOIRE (le champ qui décide si le bilan est vrai).
import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getFinancierQuestionnaire, putFinancierQuestionnaire, validerFinancierQuestionnaire,
         type QChamp, type QHorsMarche } from '../../lib/api'
import { Bouton } from '../ui/Bouton'

const MINT = '#4ADE80'
const CARD = '#0C1410'

const champInput = (unite: string): 'number' | 'text' => (
  ['€', '€/m²', 'm²', '%', 'logements', 'mois', 'nombre'].includes(unite) ? 'number' : 'text')

// RECETTE-12 A1 — LE GARDE DU HORS-MARCHÉ, CÔTÉ CLIENT (proactif, sans dépendre du réseau).
// RECETTE-11 posait le garde SEULEMENT côté serveur (POST …/valider) ET l'avalait sur panne
// (`gardeBloque` : catch → false = laisse passer) → une 401/coupure ouvrait la porte à l'écran final
// et au bouton « Ouvrir le Dossier financier ». Ici on REPRODUIT les mêmes bornes que le moteur
// (financier_bilan._hors_marche) pour DÉSACTIVER « Continuer »/« Enregistrer », surligner le champ et
// écrire le message SOUS le champ — immédiatement, quoi qu'il arrive au réseau. Le serveur reste la
// défense du PDF (422). Une valeur incohérente EST INCOHÉRENTE — jamais « elle manque ».
const MAX_PRIX_SORTIE_M2 = 20000, MAX_COUT_M2 = 8000, MAX_BAILLEUR_M2 = 12000
const fmtEurM2 = (n: number) => `${Math.round(n).toLocaleString('fr-FR')} €/m²`
interface HMClient { champ_id: string; ecran: number; affiner: boolean; message: string }
function horsMarcheClient(
  prix_sortie: number | null, cout: number | null, bailleur: number | null,
  ecranDe: (id: string) => number, affinerDe: (id: string) => boolean,
): HMClient | null {
  const mk = (id: string, message: string): HMClient => (
    { champ_id: id, ecran: ecranDe(id), affiner: affinerDe(id), message })
  // 1) bornes absolues (probable PRIX TOTAL saisi dans un champ €/m²), MÊME ORDRE que le serveur
  if (prix_sortie != null && prix_sortie > MAX_PRIX_SORTIE_M2)
    return mk('prix_sortie_saisi_eur_m2', `Cette valeur (${fmtEurM2(prix_sortie)}) est incohérente : elle dépasse tout prix de marché — un prix TOTAL a probablement été saisi à la place d'un prix au m².`)
  if (cout != null && cout > MAX_COUT_M2)
    return mk('cout_construction_saisi_eur_m2', `Cette valeur (${fmtEurM2(cout)}) est incohérente : elle dépasse tout coût de construction au m².`)
  if (bailleur != null && bailleur > MAX_BAILLEUR_M2)
    return mk('prix_vente_bailleur_saisi_eur_m2', `Cette valeur (${fmtEurM2(bailleur)}) est incohérente : un prix TOTAL a probablement été saisi à la place d'un prix au m².`)
  // 2) garde relationnelle : bailleur (vente en bloc) toujours < prix de vente libre
  if (prix_sortie != null && bailleur != null && bailleur > prix_sortie)
    return mk('prix_vente_bailleur_saisi_eur_m2', `Prix au bailleur (${fmtEurM2(bailleur)}) incohérent : il dépasse le prix de vente libre (${fmtEurM2(prix_sortie)}). Une vente EN BLOC à un bailleur social est toujours inférieure au prix du marché libre.`)
  return null
}

export function FinancierQuestionnaire({ idu, onClose }: { idu: string; onClose: () => void }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['financier-questionnaire', idu],
    queryFn: () => getFinancierQuestionnaire(idu),
  })
  const [etape, setEtape] = useState(0)
  // RECETTE-10 T2b — la section « Affiner » (champs d'usage repliés) est fermée par défaut, par étape.
  const [affinerOuvert, setAffinerOuvert] = useState<Record<number, boolean>>({})
  // RECETTE-6 (E5) — écran 0 : on ne montre les 4 écrans QUE lorsqu'un usage servi est choisi.
  const [usage, setUsage] = useState<string | null>(null)
  const [reponses, setReponses] = useState<Record<string, unknown>>({})
  const [envoi, setEnvoi] = useState(false)
  const [erreur, setErreur] = useState<string | null>(null)
  // RECETTE-11 B2 — le garde du questionnaire : une saisie hors marché bloque « Continuer »/« Enregistrer »,
  // ouvre l'accordéon et surligne le champ concerné. JAMAIS un PDF « bilan non établi ».
  const [garde, setGarde] = useState<QHorsMarche | null>(null)
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

  const set = (id: string, v: unknown) => {
    setReponses((r) => ({ ...r, [id]: v }))
    if (garde && id === garde.champ_id) setGarde(null)   // corrigé → le surlignage disparaît
  }
  // RECETTE-11 B3 — « revenir à la valeur sourcée » : on RETIRE la saisie (la clé) → le champ reprend
  // son pré-remplissage sourcé (touche=false) et réaffiche sa source.
  const resetChamp = (id: string) => {
    setReponses((r) => { const n = { ...r }; delete n[id]; return n })
    if (garde && id === garde.champ_id) setGarde(null)
  }

  // RECETTE-11 B2 — interroge le garde serveur (point de vérité unique). Si hors marché : saute à
  // l'écran, ouvre son accordéon si le champ y est replié, surligne. Rend true si BLOQUÉ.
  const gardeBloque = async (): Promise<boolean> => {
    try {
      const r = await validerFinancierQuestionnaire(idu, reponses)
      if (r.hors_marche) {
        setGarde(r.hors_marche)
        setErreur(null)
        setEtape(r.hors_marche.ecran)
        if (r.hors_marche.affiner) setAffinerOuvert((s) => ({ ...s, [r.hors_marche!.ecran]: true }))
        return true
      }
      setGarde(null)
      return false
    } catch { return false }   // le garde ne doit jamais bloquer sur une panne réseau (défense au PDF)
  }

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

  // RECETTE-12 A1 — état hors-marché CLIENT (proactif). Résout chaque champ (saisie sinon
  // pré-remplissage), trouve son écran et son tri, et applique les bornes du moteur. Recalculé à
  // chaque rendu (quelques champs — négligeable), donc réactif à la moindre correction.
  const valNum = (id: string): number | null => {
    const v = reponses[id]
    if (v != null && v !== '') { const n = Number(v); return Number.isFinite(n) ? n : null }
    for (const e of ecrans) for (const c of e.champs) if (c.id === id && c.prefill?.valeur != null) {
      const n = Number(c.prefill.valeur); return Number.isFinite(n) ? n : null
    }
    return null
  }
  const ecranDe = (id: string): number => {
    const i = ecrans.findIndex((e) => e.champs.some((c) => c.id === id)); return i < 0 ? 0 : i
  }
  const affinerDe = (id: string): boolean => {
    for (const e of ecrans) for (const c of e.champs) if (c.id === id) return c.tri === 'affiner' && !c.obligatoire
    return false
  }
  const hm = horsMarcheClient(valNum('prix_sortie_saisi_eur_m2'), valNum('cout_construction_saisi_eur_m2'),
                              valNum('prix_vente_bailleur_saisi_eur_m2'), ecranDe, affinerDe)
  // le champ incohérent est en « Affiner » (bailleur, part sociale…) → on OUVRE l'accordéon de son
  // écran pour que le surlignage et le message soient visibles sans chercher.
  useEffect(() => {
    if (hm?.affiner) setAffinerOuvert((s) => (s[hm.ecran] ? s : { ...s, [hm.ecran]: true }))
  }, [hm?.champ_id, hm?.ecran, hm?.affiner])

  const continuer = async () => {
    const m = manquantsEcran(etape)
    if (m.length) { setErreur(`À renseigner avant de continuer : ${m.map((c) => c.libelle).join(', ')}.`); return }
    if (await gardeBloque()) return          // RECETTE-11 B2 — hors marché : on ne continue pas
    setErreur(null); setEtape(etape + 1)
  }

  const enregistrer = async () => {
    const m = tousManquants()
    if (m.length) {
      setErreur(`Indispensable(s) au calcul, encore vide(s) : ${m.map((x) => x.c.libelle).join(', ')}.`)
      setEtape(m[0].i); return
    }
    if (await gardeBloque()) return          // RECETTE-11 B2 — hors marché : jamais un PDF « non établi »
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
    background: CARD, border: `.5px solid ${MINT}`, borderRadius: 6, padding: 24,
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
              <Bouton data-financier-doc niveau="primaire" ton="vert" onClick={() => void ouvrirDoc()}>
                Ouvrir le Dossier financier
              </Bouton>
              <Bouton niveau="lien" onClick={onClose}>Fermer</Bouton>
            </div>
            {/* RECETTE-5 (V18b) — le document ne s'est pas généré : on dit lesquels des éléments manquent. */}
            {docErr && (
              <div data-financier-manques style={{ marginTop: 16, padding: 14, border: '.5px solid #E0B341', borderRadius: 6, background: 'rgba(224,179,65,.06)' }}>
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
              <div data-financier-tech style={{ marginTop: 16, padding: 14, border: '.5px solid #E0776B', borderRadius: 6, background: 'rgba(224,119,107,.06)' }}>
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
                    textAlign: 'left', padding: '14px 16px', borderRadius: 6, cursor: u.servi ? 'pointer' : 'not-allowed',
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
              <Bouton niveau="lien" onClick={onClose}>Annuler</Bouton>
            </div>
          </>
        )}

        {!isLoading && !error && !fini && data && usage !== null && (
          <>
            <div style={{ fontSize: 12, color: '#5F7267', marginBottom: 6 }}>{etape + 1} / {N} · {ecrans[etape]?.titre}</div>
            {/* RECETTE-9 T1 (défaut n°3) — NAVIGATION avant/arrière : chaque étape est cliquable pour
                y revenir (ou y aller) directement ; la saisie est conservée (état `reponses`). Avant,
                seul un « ← Retour » pas-à-pas existait — on rend le fil des étapes navigable. */}
            <div data-financier-etapes style={{ display: 'flex', gap: 5, marginBottom: 22 }}>
              {ecrans.map((e, i) => (
                <button key={i} type="button" data-etape={i} aria-current={i === etape}
                  aria-label={`Étape ${i + 1} — ${e.titre}`} onClick={() => { setErreur(null); setEtape(i) }}
                  style={{ flex: 1, height: 6, padding: 0, border: 0, borderRadius: 4, cursor: 'pointer',
                    background: i === etape ? MINT : i < etape ? '#2F6B45' : '#1E2A23' }} />
              ))}
            </div>
            <h2 style={{ fontSize: 22, fontWeight: 500, margin: '0 0 4px' }}>{ecrans[etape]?.titre}</h2>
            <p style={{ fontSize: 13, color: '#8FA69A', margin: '0 0 14px' }}>
              Tout est pré-rempli avec une valeur sourcée ; vous corrigez ce que vous savez. Un champ vidé s'imprime « non chiffré ».
            </p>
            {/* RECETTE-9 T1 (défauts n°1 et n°2) — quand la parcelle n'a PAS de potentiel chiffrable,
                le programme constructible DOIT être décrit (logements + typologie).
                RECETTE-10 T2a — l'avertissement s'affiche UNE FOIS, à l'endroit du champ concerné
                (l'écran qui porte « logements visés »), et DISPARAÎT dès qu'il est renseigné. Avant, il
                se répétait sur les quatre écrans et restait même après réponse → du décor. */}
            {usage === 'construction' && data.programme && !data.programme.auto
              && ecrans[etape]?.champs.some((c) => c.id === 'logements_vises_saisi')
              && (reponses['logements_vises_saisi'] == null || reponses['logements_vises_saisi'] === '') && (
              <div data-financier-programme style={{ margin: '0 0 18px', padding: 12, borderRadius: 6,
                border: '.5px solid #E0B341', background: 'rgba(224,179,65,.06)' }}>
                <p style={{ fontSize: 12.5, color: '#E9C868', margin: 0, lineHeight: 1.5 }}>
                  {data.programme.message}
                </p>
              </div>
            )}

            {/* RECETTE-10 T2b — le tri des questions : « garder » toujours visibles, « affiner »
                repliées derrière une section (fermée par défaut), « supprimer » jamais montrées.
                Un champ obligatoire reste toujours visible quel que soit son tri. */}
            {(() => {
              const champs = (ecrans[etape]?.champs || []).filter((c) => c.tri !== 'supprimer')
              const estAffiner = (c: typeof champs[number]) => c.tri === 'affiner' && !c.obligatoire
              const garder = champs.filter((c) => !estAffiner(c))
              const affiner = champs.filter(estAffiner)
              const ouvert = !!affinerOuvert[etape]
              const row = (c: typeof champs[number]) => (
                <ChampRow key={c.id} c={c} valeur={reponses[c.id]} touche={c.id in reponses}
                          tvaExplication={data.tva_explication} onChange={(v) => set(c.id, v)}
                          onReset={() => resetChamp(c.id)}
                          surligne={hm?.champ_id === c.id || garde?.champ_id === c.id}
                          messageGarde={hm?.champ_id === c.id ? hm.message
                            : garde?.champ_id === c.id ? garde.message : null} />
              )
              // RECETTE-11 B3 — combien de valeurs « Affiner » sont modifiées (touchées) sur cet écran.
              const modifies = affiner.filter((c) => c.id in reponses).length
              return (
                <>
                  {garder.map(row)}
                  {affiner.length > 0 && (
                    <div data-financier-affiner style={{ margin: '4px 0 8px' }}>
                      <button type="button" data-financier-affiner-toggle aria-expanded={ouvert}
                        onClick={() => setAffinerOuvert((s) => ({ ...s, [etape]: !ouvert }))}
                        style={{ background: 'none', border: 0, color: MINT, cursor: 'pointer',
                          fontSize: 12.5, padding: '6px 0', display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span>{ouvert ? '▾' : '▸'}</span>
                        <span>Affiner les hypothèses ({affiner.length})</span>
                        {/* RECETTE-11 B3 — l'en-tête dit combien de valeurs sont MODIFIÉES. */}
                        {modifies > 0
                          ? <span style={{ color: '#E9C868' }} data-financier-affiner-modifies>· {modifies} modifiée{modifies > 1 ? 's' : ''}</span>
                          : <span style={{ color: '#5F7267' }}>— valeurs d'usage sourcées, à ajuster si besoin</span>}
                      </button>
                      {ouvert && <div style={{ marginTop: 8 }}>{affiner.map(row)}</div>}
                    </div>
                  )}
                </>
              )
            })()}

            {erreur && <p style={{ fontSize: 12, color: '#E0B341', margin: '14px 0 0' }}>{erreur}</p>}

            {/* RECETTE-12 A1 — hors marché sur un AUTRE écran : on le NOMME et on offre d'y aller,
                pour que « Enregistrer » désactivé soit compréhensible (jamais un blocage muet). */}
            {hm && hm.ecran !== etape && (
              <p data-financier-garde-ailleurs style={{ fontSize: 12, color: '#E0776B', margin: '14px 0 0' }}>
                Une valeur est incohérente sur l'écran «&nbsp;{ecrans[hm.ecran]?.titre}&nbsp;».{' '}
                <button type="button" onClick={() => setEtape(hm.ecran)}
                  style={{ background: 'none', border: 0, color: '#E0776B', textDecoration: 'underline', cursor: 'pointer', font: 'inherit', padding: 0 }}>
                  Corriger
                </button>{' '}pour pouvoir enregistrer.
              </p>
            )}

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: 18, marginTop: 18, borderTop: '.5px solid #1E2A23' }}>
              <button onClick={() => (etape > 0 ? setEtape(etape - 1) : setUsage(null))} style={btnPlain}>
                ← Retour
              </button>
              {/* RECETTE-12 A1 — « Continuer » désactivé quand l'écran courant porte une valeur hors
                  marché ; « Enregistrer » désactivé dès qu'UNE valeur (n'importe quel écran) est hors
                  marché — on ne peut ni atteindre l'écran final ni ouvrir le Financier. */}
              {etape < N - 1
                ? <Bouton niveau="primaire" ton="vert" disabled={!!hm && hm.ecran === etape}
                    onClick={() => void continuer()}>
                    Continuer →
                  </Bouton>
                : <Bouton niveau="primaire" ton="vert" disabled={envoi || !!hm} onClick={() => void enregistrer()}>
                    {envoi ? 'Enregistrement…' : 'Enregistrer'}
                  </Bouton>}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

const btnPlain: React.CSSProperties = {
  fontSize: 13, color: '#6F8578', background: 'none', border: 0, cursor: 'pointer',
}

function ChampRow({ c, valeur, touche, tvaExplication, onChange, onReset, surligne, messageGarde }: {
  c: QChamp; valeur: unknown; touche: boolean; tvaExplication: string; onChange: (v: unknown) => void
  onReset?: () => void                               // RECETTE-11 B3 — revenir à la valeur sourcée
  surligne?: boolean; messageGarde?: string | null   // RECETTE-11 B2 — champ hors marché à corriger
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
    width: '100%', height: 42, background: '#060A08',
    // RECETTE-11 B2 — champ hors marché : bord rouge, il faut le corriger pour continuer.
    border: surligne ? '1.5px solid #E0776B' : '.5px solid #2A3A31',
    borderRadius: 6, padding: '0 14px', fontSize: 15, color: '#ECF5EF', outline: 'none',
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
            <span data-champ-aide aria-label={c.aide}
              style={{ display: 'inline-flex', width: 14, height: 14, borderRadius: 9999, border: '1px solid #4A5A52',
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
      {/* RECETTE-11 B3 — champ MODIFIÉ qui a une valeur sourcée : proposer d'y revenir. */}
      {prefill && touche && onReset && (
        <button type="button" data-financier-reset onClick={onReset}
          style={{ background: 'none', border: 0, padding: '5px 0 0', margin: 0, cursor: 'pointer',
            fontSize: 11, color: '#4ADE80', textAlign: 'left' }}>
          ↺ Revenir à la valeur sourcée{prefill.valeur != null ? ` (${String(prefill.valeur)})` : ''}
        </button>
      )}
      {/* règle 2 — un champ vidé s'imprimera « non chiffré » */}
      {vide && (
        <p style={{ fontSize: 11, color: '#E0B341', margin: '5px 0 0' }}>Laissé vide → « non chiffré » dans le document.</p>
      )}
      {/* RECETTE-11 B2 — le message du garde, sous le champ hors marché (jamais un PDF « non établi ») */}
      {surligne && messageGarde && (
        <p data-financier-garde style={{ fontSize: 11.5, color: '#E0776B', margin: '5px 0 0', lineHeight: 1.45 }}>{messageGarde}</p>
      )}
      {/* règle 3 — l'explication du régime de TVA + renvoi expert-comptable */}
      {c.id === 'regime_tva_saisi' && (
        <p style={{ fontSize: 11, color: '#8FA69A', margin: '6px 0 0' }}>{tvaExplication}</p>
      )}
    </div>
  )
}
