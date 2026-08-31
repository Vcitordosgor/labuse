// RADAR-VEILLE-1 (R3) + SECTEUR-2b (U2) — DÉPÔT AGENCE « Publier une annonce », 4 étapes. Le parcours
// vit désormais dans l'ÉCRAN RADAR DE L'APP (plus dans la Tour de contrôle). La VISIBILITÉ est décidée
// par le parent (RadarView) : admin toujours (drapeau fermé compris), clients seulement drapeau ouvert.
// Ce composant ne fait QUE dérouler les 4 étapes ; `drapeauFerme` porte la mention « invisible des clients ».
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { radarDepotAgenceAnalyser, radarDepotAgencePublier, type DepotRec } from '../../lib/api'
import { ParcelInput } from '../ParcelInput'

export function DepotAgence({ drapeauFerme = false, onClose }: { drapeauFerme?: boolean; onClose?: () => void }) {
  const [step, setStep] = useState(1)
  const [html, setHtml] = useState('')
  const [rec, setRec] = useState<DepotRec | null>(null)
  const [adresse, setAdresse] = useState('')
  const [idu, setIdu] = useState('')
  const [agence, setAgence] = useState('')
  const [msg, setMsg] = useState<string | null>(null)
  const [publie, setPublie] = useState<{ bien_id: number; idu?: string } | null>(null)
  const analyser = useMutation({
    mutationFn: () => radarDepotAgenceAnalyser(html),
    onSuccess: (r) => { if (r.ok && r.records?.length) { setRec(r.records[0]); setStep(2); setMsg(null) } else setMsg(r.motif ?? 'Aucune annonce reconnue dans la page.') },
  })
  const publier = useMutation({
    mutationFn: () => radarDepotAgencePublier({ rec: rec as DepotRec, idu, adresse_exacte: adresse, agence_nom: agence }),
    onSuccess: (r) => { if (r.ok) { setPublie({ bien_id: r.bien_id as number, idu: r.idu }); setStep(4); setMsg(null) } else setMsg(r.motif ?? 'Publication refusée.') },
  })
  // RETOURS-3 R3 — le champ accepte l'URL de l'annonce OU le HTML collé. On détecte l'URL pour adapter
  // le libellé (le backend bascule sur une lecture serveur one-shot ; en cas de blocage, message honnête).
  const estUrl = /^\s*https?:\/\//i.test(html)
  const setF = (k: keyof DepotRec, v: unknown) => setRec((p) => (p ? { ...p, [k]: v } : p))
  const inp = 'h-8 w-full rounded-md border border-line-2 bg-surface-1 px-2 text-[12px] text-txt'
  const reset = () => { setStep(1); setHtml(''); setRec(null); setAdresse(''); setIdu(''); setAgence(''); setPublie(null); setMsg(null) }

  return (
    <div data-depot-agence className="rounded-xl border border-viz-cyan/30 bg-viz-cyan/[0.04] p-3">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span className="rounded bg-viz-cyan/15 px-1.5 py-0.5 font-mono text-[9px] tracking-wide text-viz-cyan">DÉPÔT AGENCE · BÊTA</span>
        <span className="font-mono text-[10px] text-txt-mut">ÉTAPE {step}/4</span>
        {drapeauFerme && <span data-depot-drapeau-ferme className="rounded border border-st-creuser/40 bg-st-creuser/10 px-1.5 py-0.5 font-mono text-[9px] text-st-creuser">drapeau fermé — invisible des clients</span>}
        {onClose && <button data-depot-fermer onClick={onClose} className="ml-auto text-txt-dim hover:text-txt-hi" aria-label="Fermer">✕</button>}
      </div>
      {msg && <p className="mb-2 text-[11px] text-st-ecartee">{msg}</p>}

      {step === 1 && (
        <div data-depot-etape="1" className="flex flex-col gap-2">
          <p className="text-[11px] leading-snug text-txt-mut">L'agence colle l'URL de SON annonce (https://…). Si le portail en bloque la lecture, enregistrez la page en « page web complète » (Cmd+S) et collez le HTML. Le parseur reconstruit tout — rien à ressaisir.</p>
          <textarea data-depot-html value={html} onChange={(e) => setHtml(e.target.value)} rows={4}
            placeholder="Collez l'URL de l'annonce (https://…) ou le HTML de la page…" className="w-full rounded-md border border-line-2 bg-surface-1 p-2 font-mono text-[11px] text-txt" />
          <button data-depot-analyser disabled={!html || analyser.isPending} onClick={() => analyser.mutate()}
            className="self-start rounded-md bg-mint px-3 py-1.5 text-[12px] font-medium text-mint-ink disabled:opacity-40">
            {analyser.isPending ? (estUrl ? 'Lecture de l’annonce…' : 'Analyse…') : (estUrl ? 'Récupérer l’annonce →' : 'Analyser la page →')}
          </button>
        </div>
      )}

      {step === 2 && rec && (
        <div data-depot-etape="2" className="flex flex-col gap-1.5">
          <p className="text-[11px] leading-snug text-txt-mut">Annonce reconstruite{rec.url ? <> depuis <span className="font-mono text-[10px]">{rec.url}</span></> : ''} — vérifiez, corrigez si besoin.</p>
          <div className="grid grid-cols-2 gap-1.5">
            <label className="text-[10px] text-txt-dim">Type<input className={inp} value={rec.type ?? ''} onChange={(e) => setF('type', e.target.value)} /></label>
            <label className="text-[10px] text-txt-dim">Prix (€)<input className={inp} type="number" value={rec.prix ?? ''} onChange={(e) => setF('prix', Number(e.target.value))} /></label>
            <label className="text-[10px] text-txt-dim">Surface hab (m²)<input className={inp} type="number" value={rec.surface_hab ?? ''} onChange={(e) => setF('surface_hab', Number(e.target.value))} /></label>
            <label className="text-[10px] text-txt-dim">Surface terrain (m²)<input className={inp} type="number" value={rec.surface_terrain ?? ''} onChange={(e) => setF('surface_terrain', Number(e.target.value))} /></label>
          </div>
          <label className="text-[10px] text-txt-dim">Description (confiée — s'affichera)<textarea className="w-full rounded-md border border-line-2 bg-surface-1 p-1.5 text-[11px] text-txt" rows={2} value={rec.description ?? ''} onChange={(e) => setF('description', e.target.value)} /></label>
          <p className="text-[10px] text-txt-dim">{(rec.photos?.length ?? 0)} photo(s) reprise(s) de l'annonce.</p>
          <button data-depot-continuer-adresse disabled={!rec.type || !rec.prix} onClick={() => setStep(3)}
            className="self-start rounded-md bg-mint px-3 py-1.5 text-[12px] font-medium text-mint-ink disabled:opacity-40">Continuer → l'adresse</button>
        </div>
      )}

      {step === 3 && rec && (
        <div data-depot-etape="3" className="flex flex-col gap-2">
          <label className="text-[10px] text-txt-dim">Adresse exacte <span className="text-viz-cyan">visible des seuls abonnés, jamais publique</span>
            <input data-depot-adresse className={inp} value={adresse} onChange={(e) => setAdresse(e.target.value)} placeholder="27 chemin Vidot, La Bretagne, 97490 Saint-Denis" /></label>
          <div>
            <p className="mb-1 text-[10px] text-txt-dim">Parcelle (résolue de l'adresse) — rattachement CERTAIN, source déclarée</p>
            <ParcelInput dataAttr="depot-parcelle" placeholder="Adresse ou IDU de la parcelle" onPick={(i) => setIdu(i)} onAddress={() => setMsg("Précisez un IDU : l'adresse n'a pas de parcelle rattachée.")} />
            {idu && <p className="mt-1 font-mono text-[11px] text-mint">✓ {idu} — Rattachée, certaine</p>}
          </div>
          <label className="text-[10px] text-txt-dim">Agence déposante<input data-depot-agence-nom className={inp} value={agence} onChange={(e) => setAgence(e.target.value)} placeholder="Agence Immo Transac" /></label>
          <div className="rounded-lg border border-line-2 bg-surface-2 p-2.5">
            <div className="mb-1 font-mono text-[9px] tracking-[0.18em] text-txt-mut">CE QUE LABUSE AJOUTE — AUTOMATIQUEMENT</div>
            <ul className="list-disc pl-4 text-[10.5px] leading-snug text-txt-mut">
              <li>Zone PLU calibrée, servitudes et prescriptions</li>
              <li>Risques : inondation, mouvement de terrain, CatNat</li>
              <li>Marché du secteur : DVF, prix demandés, écart demandé/acté</li>
              <li>Potentiel : emprise constructible, contexte foncier</li>
            </ul>
            <p className="mt-1 text-[10px] text-txt-dim">Votre annonce ici est plus riche que partout ailleurs — l'argument du dépôt.</p>
          </div>
          <button data-depot-publier disabled={!adresse || !idu || !agence || publier.isPending} onClick={() => publier.mutate()}
            className="self-start rounded-md bg-mint px-3 py-1.5 text-[12px] font-medium text-mint-ink disabled:opacity-40">{publier.isPending ? 'Publication…' : 'Publier l\'annonce →'}</button>
        </div>
      )}

      {step === 4 && publie && (
        <div data-depot-etape="4" className="flex flex-col gap-2">
          <div className="rounded-lg border border-mint/30 bg-mint/[0.06] p-3">
            <div className="mb-1 flex items-center gap-2">
              <span className="rounded-md bg-mint/15 px-2 py-0.5 font-mono text-[10px] text-mint">✓ Rattachée — déposée par l'agence</span>
            </div>
            <p className="text-[11.5px] text-txt">Annonce publiée au Radar — bien #{publie.bien_id}{publie.idu ? <> · parcelle <span className="font-mono">{publie.idu}</span></> : ''}. Les abonnés voient la fiche complète (photos, texte, adresse) et le bouton « Intéressé ».</p>
          </div>
          <button data-depot-nouveau onClick={reset} className="self-start rounded-md border border-line-2 px-3 py-1.5 text-[12px] text-txt-mut hover:text-txt">Nouveau dépôt</button>
        </div>
      )}
    </div>
  )
}
