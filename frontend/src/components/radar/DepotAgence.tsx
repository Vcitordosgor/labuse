// RADAR-VEILLE-1 (R3) + SECTEUR-2b (U2) + RETOURS-4 S4 — DÉPÔT AGENCE « Publier une annonce ».
// REFONTE du parcours (Vic 31/08 soir) : la lecture serveur d'URL est bloquée par les portails (403),
// et un client ne fera jamais « vider le cache → Cmd+S → coller le HTML ». Le chemin PRINCIPAL devient
// donc un FORMULAIRE COURT — c'est SON annonce, l'agence connaît les faits. L'URL n'est qu'un RACCOURCI
// (préremplit si la lecture passe, bascule SILENCIEUSE sur le formulaire vide sinon — plus aucune erreur
// rouge). Le HTML collé (Cmd+S) est le chemin d'EXPERT (Vic), replié sous « Autre méthode ▾ ».
// Doctrine inchangée : on ne stocke AUCUN contenu d'annonce, seulement les FAITS et le LIEN.
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { radarDepotAgenceAnalyser, radarDepotAgencePublier, type DepotRec } from '../../lib/api'
import { ParcelInput } from '../ParcelInput'

const TYPES = [['', 'Type…'], ['maison', 'Maison'], ['appartement', 'Appartement'], ['terrain', 'Terrain']] as const
const REPLI_URL = 'Ce portail ne laisse pas lire ses pages automatiquement — complétez les champs ci-dessous.'

export function DepotAgence({ drapeauFerme = false, onClose }: { drapeauFerme?: boolean; onClose?: () => void }) {
  // le formulaire EST le dépôt : `rec` porte les faits (type/prix/surfaces/pièces/url), `adresse`+`idu`
  // le rattachement, `agence` le déposant. Tout part vide ; l'URL/HTML ne font que PRÉ-REMPLIR.
  const [rec, setRec] = useState<DepotRec>({})
  const [adresse, setAdresse] = useState('')
  const [idu, setIdu] = useState('')
  const [agence, setAgence] = useState('')
  const [urlShort, setUrlShort] = useState('')       // raccourci « coller l'URL »
  const [urlMsg, setUrlMsg] = useState<string | null>(null)   // ligne GRISE (jamais rouge) du fallback
  const [htmlOpen, setHtmlOpen] = useState(false)    // chemin expert « Autre méthode ▾ »
  const [html, setHtml] = useState('')
  const [pubMsg, setPubMsg] = useState<string | null>(null)
  const [publie, setPublie] = useState<{ bien_id: number; idu?: string } | null>(null)

  const setF = (k: keyof DepotRec, v: unknown) => setRec((p) => ({ ...p, [k]: v }))
  const prefill = (r: DepotRec) => setRec((p) => ({
    ...p,
    type: r.type ?? p.type, prix: r.prix ?? p.prix, surface_hab: r.surface_hab ?? p.surface_hab,
    surface_terrain: r.surface_terrain ?? p.surface_terrain, pieces: r.pieces ?? p.pieces,
    url: r.url ?? p.url, description: r.description ?? p.description, photos: r.photos ?? p.photos,
    commune: r.commune ?? p.commune,
  }))

  // RACCOURCI URL — lecture serveur one-shot (livrée en R3). Succès → préremplit ; échec (403/Datadome/
  // timeout) → bascule SILENCIEUSE : ligne grise + formulaire vide, jamais d'erreur rouge.
  const lireUrl = useMutation({
    mutationFn: () => radarDepotAgenceAnalyser(urlShort),
    onSuccess: (res) => {
      if (res.ok && res.records?.length) { prefill(res.records[0]); if (!res.records[0].url) setF('url', urlShort.trim()); setUrlMsg(null) }
      else setUrlMsg(REPLI_URL)
    },
    onError: () => setUrlMsg(REPLI_URL),   // le réseau/serveur a échoué → on complète à la main, sans drame
  })
  // EXPERT — coller le HTML (Cmd+S). Même préremplissage ; en cas d'échec, ligne grise (pas rouge).
  const lireHtml = useMutation({
    mutationFn: () => radarDepotAgenceAnalyser(html),
    onSuccess: (res) => { if (res.ok && res.records?.length) { prefill(res.records[0]); setHtmlOpen(false); setUrlMsg(null) } else setUrlMsg(res.motif ?? REPLI_URL) },
    onError: () => setUrlMsg(REPLI_URL),
  })
  const publier = useMutation({
    mutationFn: () => radarDepotAgencePublier({ rec, idu, adresse_exacte: adresse, agence_nom: agence }),
    onSuccess: (r) => { if (r.ok) { setPublie({ bien_id: r.bien_id as number, idu: r.idu }); setPubMsg(null) } else setPubMsg(r.motif ?? 'Publication refusée.') },
  })

  const inp = 'h-8 w-full rounded-md border border-line-2 bg-surface-1 px-2 text-[12px] text-txt focus:border-mint focus:outline-none'
  const pretAPublier = Boolean(adresse && idu && agence && rec.type && rec.prix)
  const reset = () => { setRec({}); setAdresse(''); setIdu(''); setAgence(''); setUrlShort(''); setUrlMsg(null); setHtml(''); setHtmlOpen(false); setPublie(null); setPubMsg(null) }

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
            <div className="mb-1 flex items-center gap-2">
              <span className="rounded-md bg-mint/15 px-2 py-0.5 font-mono text-[10px] text-mint">✓ Rattachée — déposée par l'agence</span>
            </div>
            <p className="text-[11.5px] text-txt">Annonce publiée au Radar — bien #{publie.bien_id}{publie.idu ? <> · parcelle <span className="font-mono">{publie.idu}</span></> : ''}. Les abonnés voient la fiche complète et le bouton « Intéressé ».</p>
          </div>
          <button data-depot-nouveau onClick={reset} className="self-start rounded-md border border-line-2 px-3 py-1.5 text-[12px] text-txt-mut hover:text-txt">Nouveau dépôt</button>
        </div>
      ) : (
        <div data-depot-etape="1" className="flex flex-col gap-2.5">
          <p className="text-[11px] leading-snug text-txt-mut">C'est <b className="text-txt">votre</b> annonce : renseignez les faits (une minute). Rien de son contenu n'est stocké — seulement les faits et le lien.</p>

          {/* RACCOURCI URL — optionnel : tente la lecture auto ; sinon bascule silencieuse sur le formulaire. */}
          <div className="rounded-lg border border-line-2 bg-surface-2/60 p-2">
            <div className="flex items-center gap-1.5">
              <input data-depot-url value={urlShort} onChange={(e) => setUrlShort(e.target.value)}
                placeholder="Raccourci : collez l'URL de l'annonce (facultatif)" className={inp} />
              <button data-depot-url-lire disabled={!urlShort.trim() || lireUrl.isPending} onClick={() => lireUrl.mutate()}
                className="shrink-0 rounded-md border border-mint/40 bg-mint/10 px-2.5 py-1.5 text-[11.5px] font-medium text-mint hover:bg-mint/20 disabled:opacity-40">
                {lireUrl.isPending ? 'Lecture…' : 'Pré-remplir'}</button>
            </div>
            {urlMsg && <p data-depot-url-msg className="mt-1.5 text-[10.5px] leading-snug text-txt-dim">{urlMsg}</p>}
          </div>

          {/* LE FORMULAIRE COURT — le chemin principal. Sept faits, remplis en une minute. */}
          <div className="grid grid-cols-2 gap-1.5">
            <label className="col-span-2 text-[10px] text-txt-dim">Adresse exacte <span className="text-viz-cyan">visible des seuls abonnés, jamais publique</span>
              <input data-depot-adresse className={inp} value={adresse} onChange={(e) => setAdresse(e.target.value)} placeholder="27 chemin Vidot, La Bretagne, 97490 Saint-Denis" /></label>
            <label className="text-[10px] text-txt-dim">Type
              <select data-depot-type className={inp} value={rec.type ?? ''} onChange={(e) => setF('type', e.target.value)}>
                {TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select></label>
            <label className="text-[10px] text-txt-dim">Prix (€)<input data-depot-prix className={inp} type="number" min={0} value={rec.prix ?? ''} onChange={(e) => setF('prix', e.target.value === '' ? undefined : Number(e.target.value))} /></label>
            <label className="text-[10px] text-txt-dim">Surface bâtie (m²)<input data-depot-shab className={inp} type="number" min={0} value={rec.surface_hab ?? ''} onChange={(e) => setF('surface_hab', e.target.value === '' ? undefined : Number(e.target.value))} /></label>
            <label className="text-[10px] text-txt-dim">Surface terrain (m²)<input data-depot-sterr className={inp} type="number" min={0} value={rec.surface_terrain ?? ''} onChange={(e) => setF('surface_terrain', e.target.value === '' ? undefined : Number(e.target.value))} /></label>
            <label className="text-[10px] text-txt-dim">Nb de pièces <span className="text-txt-off">(facultatif)</span><input data-depot-pieces className={inp} type="number" min={0} value={rec.pieces ?? ''} onChange={(e) => setF('pieces', e.target.value === '' ? undefined : Number(e.target.value))} /></label>
            <label className="text-[10px] text-txt-dim">URL de l'annonce<input data-depot-url-annonce className={inp} value={rec.url ?? ''} onChange={(e) => setF('url', e.target.value)} placeholder="https://…" /></label>
          </div>

          {/* RATTACHEMENT PARCELLE immédiat depuis l'adresse (certain, source déclarée). */}
          <div>
            <p className="mb-1 text-[10px] text-txt-dim">Parcelle (résolue de l'adresse) — rattachement CERTAIN</p>
            <ParcelInput dataAttr="depot-parcelle" placeholder="Adresse ou IDU de la parcelle" onPick={(i) => setIdu(i)} onAddress={() => setPubMsg("Précisez un IDU : l'adresse n'a pas de parcelle rattachée.")} />
            {idu && <p className="mt-1 font-mono text-[11px] text-mint">✓ {idu} — Rattachée, certaine</p>}
          </div>

          <label className="text-[10px] text-txt-dim">Agence déposante<input data-depot-agence-nom className={inp} value={agence} onChange={(e) => setAgence(e.target.value)} placeholder="Agence Immo Transac" /></label>

          {pubMsg && <p className="text-[11px] text-st-ecartee">{pubMsg}</p>}
          <button data-depot-publier disabled={!pretAPublier || publier.isPending} onClick={() => publier.mutate()}
            className="self-start rounded-md bg-mint px-3 py-1.5 text-[12px] font-medium text-mint-ink disabled:opacity-40">{publier.isPending ? 'Publication…' : 'Publier l\'annonce →'}</button>

          {/* CHEMIN EXPERT — coller le HTML (Cmd+S), replié. C'est le chemin de Vic pour sa collecte. */}
          <div className="border-t border-line-2 pt-2">
            <button data-depot-html-toggle onClick={() => setHtmlOpen((o) => !o)} className="text-[10.5px] text-txt-dim hover:text-txt">
              Autre méthode {htmlOpen ? '▴' : '▾'}
            </button>
            {htmlOpen && (
              <div className="mt-2 flex flex-col gap-1.5">
                <p className="text-[10px] leading-snug text-txt-off">Enregistrez la page en « page web complète » (Cmd+S) et collez le HTML — le parseur pré-remplit le formulaire.</p>
                <textarea data-depot-html value={html} onChange={(e) => setHtml(e.target.value)} rows={3}
                  placeholder="Collez ici le HTML de la page…" className="w-full rounded-md border border-line-2 bg-surface-1 p-2 font-mono text-[11px] text-txt" />
                <button data-depot-html-lire disabled={!html || lireHtml.isPending} onClick={() => lireHtml.mutate()}
                  className="self-start rounded-md border border-line-2 px-2.5 py-1 text-[11.5px] text-txt-mut hover:text-txt disabled:opacity-40">
                  {lireHtml.isPending ? 'Analyse…' : 'Pré-remplir depuis le HTML'}</button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
