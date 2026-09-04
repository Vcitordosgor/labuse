// RETOURS-4 S7 — FUSION « Veille promoteurs » → « Scan patrimoine ». Décision Vic : le nom « Scan
// patrimoine » est CONSERVÉ (on veut parfois juste regarder ce qu'une entreprise possède ; « promoteurs »
// referme le sujet à tort). La veille des opérations devient le SECOND ONGLET du même outil, pas un outil
// séparé. Le propriétaire sélectionné est PARTAGÉ entre les deux onglets — on bascule sans re-saisir.
//
// RETOURS-6 U1 (Vic 01/09) — PARCOURS EN DEUX TEMPS, UN SEUL CHAMP. À vide : la recherche SEULE — aucun
// onglet (il n'y a pas encore de propriétaire à onglet-er), une ligne d'aide et QUATRE exemples cliquables
// (nom / SIREN / IDU / adresse) qui lancent la recherche (ils remplacent le message d'attente). Propriétaire
// trouvé : le champ DISPARAÎT, remplacé par un encart en tête (raison sociale · SIREN + « changer » qui
// ramène à l'état 1), et LES ONGLETS APPARAISSENT — soulignés, pas des boutons pleins : ce sont des onglets,
// pas des actions. La bascule d'onglet ne relance AUCUNE recherche (le propriétaire est partagé).
import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { banAutocomplete, getFiche, modPatrimoine, modPatrimoineSearch, parcelAt } from '../../lib/api'
import { estIdu, iduComplet } from '../../lib/format'
import { useApp } from '../../store/useApp'
import { M02 } from './ModulePanel'
import { VeillePromoteurs } from './VeillePromoteurs'

type Tab = 'possede' | 'construit'

// U1.4 — EXEMPLES : montrent ce que le champ accepte, un par nature. Nom réel (CBO TERRITORIA), un SIREN,
// un IDU et une adresse du 974 ; le clic lance la recherche (résolution commune avec la barre).
const EXEMPLES: { k: string; v: string }[] = [
  { k: 'nom', v: 'CBO TERRITORIA' },
  { k: 'SIREN', v: '310 863 592' },
  { k: 'IDU', v: '97415000CM1799' },
  { k: 'adresse', v: '27 chemin Vidot, Saint-Denis' },
]

const PAS_DE_PM = "Cette parcelle n'a pas de propriétaire personne morale connu (particulier, ou non renseigné)."

export function ScanPatrimoine({ defaultTab = 'possede' }: { defaultTab?: Tab } = {}) {
  const [owner, setOwner] = useState<string | null>(null)   // le SIREN partagé entre les deux onglets
  const [ownerLabel, setOwnerLabel] = useState<string | null>(null)  // raison sociale connue à la sélection (sinon résolue)
  const [tab, setTab] = useState<Tab>(defaultTab)
  // LOT S1 — compteur réel de l'onglet « Ce qu'ils construisent », remonté par VeillePromoteurs
  // (opérations + programmes collectés). null tant qu'inconnu → l'onglet reste sans nombre (rien d'inventé).
  const [nConstruit, setNConstruit] = useState<number | null>(null)
  const [q, setQ] = useState('')
  const [msg, setMsg] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const qc = useQueryClient()

  // ponts EXTERNES (popup carte « voir son patrimoine », porte Scan de la fiche, deep-link) → sélection
  // partagée + bon onglet. Consommés ICI (M02/VeillePromoteurs embarqués ne lisent plus le store → 0 course).
  const m02Prefill = useApp((s) => s.m02Prefill); const setM02Prefill = useApp((s) => s.setM02Prefill)
  const veilleFocusSiren = useApp((s) => s.veilleFocusSiren); const setVeilleFocusSiren = useApp((s) => s.setVeilleFocusSiren)
  useEffect(() => { if (m02Prefill) { setOwner(m02Prefill); setOwnerLabel(null); setTab('possede'); setM02Prefill(null) } }, [m02Prefill, setM02Prefill])
  useEffect(() => { if (veilleFocusSiren) { setOwner(veilleFocusSiren); setOwnerLabel(null); setTab('construit'); setVeilleFocusSiren(null) } }, [veilleFocusSiren, setVeilleFocusSiren])

  // U1.5 — encart propriétaire (état 2) : raison sociale + SIREN. Partage la CLÉ react-query de M02
  // (['m02', siren]) → aucune requête en double. Le payload patrimoine n'expose PAS de « qualité »
  // (forme juridique / rôle) : on n'en invente pas — l'encart montre le nom et le SIREN, rien de plus.
  // LOT S1 — au changement de propriétaire, on oublie le compteur « construit » (VeillePromoteurs le
//  re-remontera pour le nouveau SIREN) ; évite d'afficher un nombre hérité du promoteur précédent.
  useEffect(() => { setNConstruit(null) }, [owner])
  const ownerQ = useQuery({ queryKey: ['m02', owner], queryFn: () => modPatrimoine(owner!), enabled: !!owner })
  const ownerNom = (ownerQ.data as { nom?: string } | undefined)?.nom ?? ownerLabel

  const digits = q.replace(/\s/g, '')
  const looksSiren = /^\d{9}$/.test(digits) || /^\d{14}$/.test(digits)   // SIREN 9 / SIRET 14
  const looksIdu = estIdu(q.trim())
  // suggestions live par NOM (état 1 seulement, et tant que ce n'est ni un SIREN/SIRET ni un IDU)
  const sug = useQuery({ queryKey: ['scan-search', q.trim()], queryFn: () => modPatrimoineSearch(q.trim()), enabled: q.trim().length >= 2 && !looksSiren && !looksIdu && !owner })

  const choisir = (siren: string, nom?: string) => { setOwner(siren); setOwnerLabel(nom ?? null); setMsg(null) }
  const changer = () => { setOwner(null); setOwnerLabel(null); setQ(''); setMsg(null) }
  // résout l'IDU → propriétaire moral de la fiche (owner_siren) ; null si particulier / non renseigné.
  const ownerDeIdu = async (idu: string): Promise<string | null> => {
    const clean = iduComplet(idu.toUpperCase().replace(/\s/g, ''))
    const f = await qc.fetchQuery({ queryKey: ['scan-idu', clean], queryFn: () => getFiche(clean) }).catch(() => null)
    const s = (f as { owner_siren?: string | null } | null)?.owner_siren
    return s ? String(s) : null
  }

  // RETOURS-6 U1 — résolution ROBUSTE et self-contained (fetchQuery), utilisée par la barre ET les exemples.
  //   SIREN/SIRET → 9 chiffres · IDU → propriétaire de la fiche · sinon NOM (fichiers fonciers, cas
  //   principal) puis REPLI ADRESSE (BAN → parcelle → propriétaire) quand le nom ne matche aucune dénomination.
  const resoudre = async (raw?: string) => {
    const val = (raw ?? q).trim()
    if (raw != null) setQ(raw)
    setMsg(null)
    if (val.length < 2) return
    setBusy(true)
    try {
      const dg = val.replace(/\s/g, '')
      if (/^\d{9}$/.test(dg) || /^\d{14}$/.test(dg)) { choisir(dg.slice(0, 9)); return }   // SIRET → SIREN = 9 premiers
      if (estIdu(val)) {
        const s = await ownerDeIdu(dg)
        if (s) choisir(s); else setMsg(PAS_DE_PM)
        return
      }
      // NOM d'entreprise — le cas d'usage principal (recherche sur les dénominations des fichiers fonciers).
      const results = await qc.fetchQuery({ queryKey: ['scan-search', val], queryFn: () => modPatrimoineSearch(val) })
      const first = (results as { siren: string; nom: string }[] | undefined)?.[0]
      if (first) { choisir(first.siren, first.nom); return }
      // REPLI ADRESSE : une adresse ne matche aucune dénomination → on la géocode (BAN, publique) et on
      // remonte à la parcelle puis au propriétaire.
      const feats = await banAutocomplete(val)
      const f0 = feats[0]
      let iduRes = f0?.idu ?? null
      if (f0 && !iduRes) { const at = await parcelAt(f0.lon, f0.lat).catch(() => null); iduRes = at?.idu ?? null }
      if (iduRes) {
        const s = await ownerDeIdu(iduRes)
        if (s) choisir(s); else setMsg(PAS_DE_PM)
        return
      }
      setMsg('Aucun propriétaire trouvé — précisez le nom, un SIREN/SIRET, un IDU ou une adresse.')
    } finally { setBusy(false) }
  }

  const inp = 'h-8 w-full rounded-md border border-line-2 bg-surface-1 px-2 text-[12px] text-txt focus:border-mint focus:outline-none'

  return (
    <div data-scan-patrimoine className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-1 text-[12.5px]">
      <div>
        <h2 className="font-display text-base font-bold text-txt-hi">Scan patrimoine</h2>
        <p className="mt-0.5 text-[11.5px] text-txt-mut">Ce qu'un propriétaire possède, et ce qu'il construit.</p>
      </div>

      {!owner ? (
        /* ───────── ÉTAT 1 — aucun propriétaire : la recherche SEULE, pas d'onglets. ───────── */
        <>
          {/* U1.1 — UN seul champ, celui de l'outil ; aucun renvoi vers une autre barre. */}
          <div className="flex items-center gap-1.5">
            <input data-scan-search value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') resoudre() }}
              placeholder="Nom, SIREN, IDU ou adresse" className={inp} />
            <button data-scan-chercher onClick={() => resoudre()} disabled={q.trim().length < 2 || busy}
              className="shrink-0 rounded-md bg-mint px-3 py-1.5 text-[12px] font-medium text-mint-ink disabled:opacity-40">{busy ? '…' : 'Chercher'}</button>
          </div>
          {/* U1.3 — ligne d'aide sous le champ. */}
          <p className="text-[11px] leading-snug text-txt-off">Une société, une parcelle, une adresse — LABUSE remonte au propriétaire.</p>
          {msg && <p data-scan-msg className="text-[11px] leading-snug text-st-creuser">{msg}</p>}
          {/* suggestions live par nom (tant qu'on frappe) */}
          {q.trim().length >= 2 && !looksSiren && !looksIdu && (sug.data?.length ?? 0) > 0 && (
            <div className="flex flex-col gap-1">
              {(sug.data ?? []).slice(0, 8).map((s) => (
                <button key={s.siren} data-scan-sug onClick={() => choisir(s.siren, s.nom)}
                  className="hover-fill flex items-center justify-between rounded-lg border border-line-2 bg-surface-3 px-3 py-1.5 text-left text-xs text-txt transition-colors duration-quick">
                  <span className="truncate">{s.nom}</span><span className="font-mono text-[11px] text-txt-dim">{s.n} parc.</span>
                </button>
              ))}
            </div>
          )}
          {/* U1.4 — bloc EXEMPLES : à vide seulement (remplace le message d'attente ; montre ce que le champ accepte). */}
          {q.trim().length < 2 && (
            <div className="flex flex-col gap-1.5">
              <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-txt-dim">Exemples</div>
              {EXEMPLES.map((e) => (
                <button key={e.k} data-scan-exemple={e.k} onClick={() => resoudre(e.v)} disabled={busy}
                  className="hover-fill flex items-center gap-2.5 rounded-lg border border-line-2 bg-surface-3 px-3 py-2 text-left disabled:opacity-40">
                  <span className="shrink-0 rounded bg-mint/10 px-1.5 py-0.5 font-mono text-[10px] text-mint">{e.k}</span>
                  <span className="truncate text-[12.5px] text-txt">{e.v}</span>
                </button>
              ))}
            </div>
          )}
        </>
      ) : (
        /* ───────── ÉTAT 2 — propriétaire trouvé : encart en tête + onglets soulignés. ───────── */
        <>
          {/* U1.5 — encart propriétaire : raison sociale + SIREN + « changer » (retour état 1). */}
          <div data-scan-owner className="flex items-center justify-between gap-2.5 rounded-lg border border-line-2 bg-surface-3 px-3 py-2">
            <div className="min-w-0">
              <div className="truncate text-[13.5px] font-semibold text-txt-hi">{ownerNom ?? '…'}</div>
              <div className="mt-0.5 font-mono text-[10.5px] text-txt-dim">SIREN {owner}</div>
            </div>
            <button data-scan-changer onClick={changer} className="shrink-0 text-[11.5px] text-mint underline underline-offset-2 hover:text-mint/80">changer</button>
          </div>

          {/* U1.6 — onglets SOULIGNÉS (pas des boutons pleins) ; le propriétaire est partagé (aucune relance). */}
          <div className="flex gap-6 border-b border-line-2" role="tablist">
            {([['possede', 'Ce qu\'ils possèdent'], ['construit', 'Ce qu\'ils construisent']] as const).map(([k, label]) => (
              <button key={k} data-scan-tab={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
                className={`-mb-px border-b-2 pb-2 pt-1 text-[13px] transition-colors ${tab === k ? 'border-mint font-medium text-mint' : 'border-transparent text-txt-mut hover:text-txt'}`}>
                {/* LOT S1 — compteur réel sur l'onglet « construit » quand VeillePromoteurs l'a remonté. */}
                {label}{k === 'construit' && nConstruit != null && <span className="ml-1 text-txt-dim">({nConstruit})</span>}
              </button>
            ))}
          </div>

          <div className="flex min-h-0 flex-1 flex-col gap-1.5">
            {tab === 'possede'
              ? <M02 embedded sirenProp={owner} onVoirOperations={(s) => { setOwner(s); setOwnerLabel(null); setTab('construit') }} />
              : <VeillePromoteurs embedded focusSiren={owner} onCount={setNConstruit} onVoirPatrimoine={(s) => { setOwner(s); setOwnerLabel(null); setTab('possede') }} />}
          </div>
        </>
      )}
    </div>
  )
}
