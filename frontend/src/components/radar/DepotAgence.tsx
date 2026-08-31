// RADAR-VEILLE-1 (R3) + SECTEUR-2b (U2) + RETOURS-4 S4 + RETOURS-5 T5 — DÉPÔT AGENCE « Publier une annonce ».
// SIMPLIFIÉ AU MAXIMUM (Vic 01/09) : c'est SON annonce, l'agence connaît ses faits. Le parcours client
// est un FORMULAIRE COURT qui tient sur un écran. Le pré-remplissage par URL (raccourci) et par HTML
// (Cmd+S) est RETIRÉ du parcours client (il vaut pour la collecte de Vic, pas pour une agence) — le
// backend/parseur restent en place, appelés ailleurs. Doctrine inchangée : on ne stocke AUCUN contenu
// d'annonce, seulement les FAITS et le LIEN.
//  · un seul champ lien, « Lien de l'annonce », EN BAS (plus de doublon avec un champ URL en tête) ;
//  · champs réduits : adresse · type · prix · surface bâtie · surface terrain · lien (plus de « Nb de pièces ») ;
//  · la PARCELLE se déduit de l'adresse (AddressAutocomplete) — jamais saisie, montrée en RÉSULTAT ;
//  · l'AGENCE est déduite du compte connecté (jamais saisie).
import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { getMoi, parcelAt, radarDepotAgencePublier, type DepotRec } from '../../lib/api'
import { AddressAutocomplete, type AddressSelection } from '../AddressAutocomplete'

const TYPES = [['', 'Type…'], ['maison', 'Maison'], ['appartement', 'Appartement'], ['terrain', 'Terrain']] as const

export function DepotAgence({ drapeauFerme = false, onClose }: { drapeauFerme?: boolean; onClose?: () => void }) {
  const [rec, setRec] = useState<DepotRec>({})
  const [adresse, setAdresse] = useState('')
  const [idu, setIdu] = useState('')           // déduit de l'adresse (rattachement certain), jamais saisi
  const [pubMsg, setPubMsg] = useState<string | null>(null)
  const [publie, setPublie] = useState<{ bien_id: number; idu?: string } | null>(null)
  // T5.3 — l'agence déposante est DÉDUITE du compte connecté (jamais un champ). On prend l'identifiant du
  // compte (email) faute de raison sociale exposée par /moi ; en session locale, repli neutre.
  const moi = useQuery({ queryKey: ['moi'], queryFn: getMoi, staleTime: 3_600_000 })
  const agence = moi.data?.email || 'Compte agence'

  const setF = (k: keyof DepotRec, v: unknown) => setRec((p) => ({ ...p, [k]: v }))
  // T5.2 — la parcelle se DÉDUIT de l'adresse : l'autocomplétion renvoie l'IDU (ou on le résout au point).
  const onAdresse = async (sel: AddressSelection) => {
    setAdresse(sel.label); setPubMsg(null)
    if (sel.idu) { setIdu(sel.idu); return }
    const at = await parcelAt(sel.lon, sel.lat).catch(() => null)
    setIdu(at?.idu ?? '')
  }
  const publier = useMutation({
    mutationFn: () => radarDepotAgencePublier({ rec, idu, adresse_exacte: adresse, agence_nom: agence }),
    onSuccess: (r) => { if (r.ok) { setPublie({ bien_id: r.bien_id as number, idu: r.idu }); setPubMsg(null) } else setPubMsg(r.motif ?? 'Publication refusée.') },
  })
  const pret = Boolean(adresse && idu && rec.type && rec.prix)
  const reset = () => { setRec({}); setAdresse(''); setIdu(''); setPubMsg(null); setPublie(null) }

  const inp = 'h-9 w-full rounded-md border border-line-2 bg-surface-1 px-2.5 text-[13px] text-txt focus:border-mint focus:outline-none'
  const lab = 'mb-1 block text-[11px] text-txt-dim'

  return (
    <div data-depot-agence className="rounded-xl border border-viz-cyan/30 bg-viz-cyan/[0.04] p-3">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span className="rounded bg-viz-cyan/15 px-1.5 py-0.5 font-mono text-[9px] tracking-wide text-viz-cyan">DÉPÔT AGENCE · BÊTA</span>
        {drapeauFerme && <span data-depot-drapeau-ferme className="rounded border border-st-creuser/40 bg-st-creuser/10 px-1.5 py-0.5 font-mono text-[9px] text-st-creuser">drapeau fermé — invisible des clients</span>}
        {onClose && <button data-depot-fermer onClick={onClose} className="ml-auto text-txt-dim hover:text-txt-hi" aria-label="Fermer">✕</button>}
      </div>

      {publie ? (
        <div data-depot-etape="publie" className="flex flex-col gap-2">
          <div className="rounded-lg border border-mint/30 bg-mint/[0.06] p-3">
            <div className="mb-1"><span className="rounded-md bg-mint/15 px-2 py-0.5 font-mono text-[10px] text-mint">✓ Rattachée — déposée par l'agence</span></div>
            <p className="text-[11.5px] text-txt">Annonce publiée au Radar — bien #{publie.bien_id}{publie.idu ? <> · parcelle <span className="font-mono">{publie.idu}</span></> : ''}. Les abonnés voient la fiche complète et le bouton « Intéressé ».</p>
          </div>
          <button data-depot-nouveau onClick={reset} className="self-start rounded-md border border-line-2 px-3 py-1.5 text-[12px] text-txt-mut hover:text-txt">Nouveau dépôt</button>
        </div>
      ) : (
        <div data-depot-etape="1" className="flex flex-col gap-2.5">
          <p className="text-[11px] leading-snug text-txt-mut">C'est <b className="text-txt">votre</b> annonce : renseignez les faits, une minute. Rien de son contenu n'est stocké.</p>

          {/* T5.4 — adresse exacte : l'autocomplétion résout la parcelle en coulisse (montrée après validation). */}
          <div>
            <label className={lab}>Adresse exacte</label>
            <AddressAutocomplete placeholder="27 chemin Vidot, La Bretagne, 97490 Saint-Denis"
              className={inp} onSelect={onAdresse} onClear={() => { setAdresse(''); setIdu('') }} />
            <p className="mt-1 text-[10.5px] text-txt-off">Visible des seuls abonnés · sert au rattachement de la parcelle{idu ? <> — <span className="font-mono text-mint">✓ {idu}</span></> : ''}</p>
          </div>

          <div className="grid grid-cols-2 gap-2.5">
            <div><label className={lab}>Type</label>
              <select data-depot-type className={inp} value={rec.type ?? ''} onChange={(e) => setF('type', e.target.value)}>
                {TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select></div>
            <div><label className={lab}>Prix (€)</label><input data-depot-prix className={inp} type="number" min={0} value={rec.prix ?? ''} onChange={(e) => setF('prix', e.target.value === '' ? undefined : Number(e.target.value))} placeholder="—" /></div>
            <div><label className={lab}>Surface bâtie (m²)</label><input data-depot-shab className={inp} type="number" min={0} value={rec.surface_hab ?? ''} onChange={(e) => setF('surface_hab', e.target.value === '' ? undefined : Number(e.target.value))} placeholder="—" /></div>
            <div><label className={lab}>Surface terrain (m²)</label><input data-depot-sterr className={inp} type="number" min={0} value={rec.surface_terrain ?? ''} onChange={(e) => setF('surface_terrain', e.target.value === '' ? undefined : Number(e.target.value))} placeholder="—" /></div>
          </div>

          {/* T5.1 — un SEUL champ lien, en bas (plus de doublon avec un raccourci URL en tête). */}
          <div>
            <label className={lab}>Lien de l'annonce</label>
            <input data-depot-url-annonce className={inp} value={rec.url ?? ''} onChange={(e) => setF('url', e.target.value)} placeholder="https://…" />
          </div>

          {pubMsg && <p className="text-[11px] text-st-ecartee">{pubMsg}</p>}
          <button data-depot-publier disabled={!pret || publier.isPending} onClick={() => publier.mutate()}
            className="w-full rounded-md bg-mint py-2 text-[13px] font-semibold text-mint-ink disabled:opacity-40">{publier.isPending ? 'Publication…' : 'Publier'}</button>
        </div>
      )}
    </div>
  )
}
