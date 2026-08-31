// RETOURS-4 S7 — FUSION « Veille promoteurs » → « Scan patrimoine ». Décision Vic : le nom « Scan
// patrimoine » est CONSERVÉ (on veut parfois juste regarder ce qu'une entreprise possède ; « promoteurs »
// referme le sujet à tort). La veille des opérations devient le SECOND ONGLET du même outil, pas un outil
// séparé. Une BARRE DE RECHERCHE UNIQUE (nom / SIREN·SIRET / IDU / adresse, nature détectée) ; le
// propriétaire sélectionné est PARTAGÉ entre les deux onglets — on bascule sans re-saisir. Les ponts
// croisés livrés en RETOURS-3 deviennent des bascules d'onglet.
import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getFiche, modPatrimoineSearch } from '../../lib/api'
import { estIdu } from '../../lib/format'
import { useApp } from '../../store/useApp'
import { M02 } from './ModulePanel'
import { VeillePromoteurs } from './VeillePromoteurs'

type Tab = 'possede' | 'construit'

export function ScanPatrimoine({ defaultTab = 'possede' }: { defaultTab?: Tab } = {}) {
  const [owner, setOwner] = useState<string | null>(null)   // le SIREN partagé entre les deux onglets
  const [tab, setTab] = useState<Tab>(defaultTab)
  const [q, setQ] = useState('')
  const [msg, setMsg] = useState<string | null>(null)

  // ponts EXTERNES (popup carte « voir son patrimoine », porte Scan de la fiche, deep-link) → sélection
  // partagée + bon onglet. Consommés ICI (M02/VeillePromoteurs embarqués ne lisent plus le store → 0 course).
  const m02Prefill = useApp((s) => s.m02Prefill); const setM02Prefill = useApp((s) => s.setM02Prefill)
  const veilleFocusSiren = useApp((s) => s.veilleFocusSiren); const setVeilleFocusSiren = useApp((s) => s.setVeilleFocusSiren)
  useEffect(() => { if (m02Prefill) { setOwner(m02Prefill); setTab('possede'); setM02Prefill(null) } }, [m02Prefill, setM02Prefill])
  useEffect(() => { if (veilleFocusSiren) { setOwner(veilleFocusSiren); setTab('construit'); setVeilleFocusSiren(null) } }, [veilleFocusSiren, setVeilleFocusSiren])

  const digits = q.replace(/\s/g, '')
  const looksSiren = /^\d{9}$/.test(digits) || /^\d{14}$/.test(digits)   // SIREN 9 / SIRET 14
  const looksIdu = estIdu(q.trim())
  // suggestions par NOM (uniquement si ce n'est ni un SIREN/SIRET ni un IDU)
  const sug = useQuery({ queryKey: ['scan-search', q], queryFn: () => modPatrimoineSearch(q.trim()), enabled: q.trim().length >= 2 && !looksSiren && !looksIdu })
  // résolution d'un IDU → propriétaire moral (owner_siren), à la demande
  const iduQ = useQuery({ queryKey: ['scan-idu', q], queryFn: () => getFiche(q.trim().toUpperCase().replace(/\s/g, '')), enabled: false })

  const choisir = (siren: string, nom?: string) => { setOwner(siren); setMsg(null); if (nom != null) setQ(nom) }
  const resoudre = async () => {
    setMsg(null)
    if (looksSiren) { choisir(digits.slice(0, 9)); return }   // SIRET → SIREN = 9 premiers chiffres
    if (looksIdu) {
      const f = await iduQ.refetch()
      const s = (f.data as { owner_siren?: string | null } | undefined)?.owner_siren
      if (s) choisir(String(s)); else setMsg("Cette parcelle n'a pas de propriétaire personne morale connu (particulier, ou non renseigné).")
      return
    }
    const first = sug.data?.[0]
    if (first) choisir(first.siren, first.nom); else setMsg('Aucun propriétaire trouvé — précisez le nom, un SIREN/SIRET ou un IDU.')
  }

  const inp = 'h-8 w-full rounded-md border border-line-2 bg-surface-1 px-2 text-[12px] text-txt focus:border-mint focus:outline-none'

  return (
    <div data-scan-patrimoine className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-1 text-[12.5px]">
      <div>
        <h2 className="font-display text-base font-bold text-txt-hi">Scan patrimoine</h2>
        <p className="mt-0.5 text-[11.5px] text-txt-mut">Ce qu'un propriétaire possède, et ce qu'il construit.</p>
      </div>

      {/* S7.1 — barre de recherche UNIQUE : nom, SIREN/SIRET, IDU ou adresse (nature détectée). */}
      <div className="flex items-center gap-1.5">
        <input data-scan-search value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') resoudre() }}
          placeholder="Nom d'entreprise, SIREN/SIRET, IDU ou adresse" className={inp} />
        <button data-scan-chercher onClick={resoudre} disabled={q.trim().length < 2 || iduQ.isFetching}
          className="shrink-0 rounded-md bg-mint px-3 py-1.5 text-[12px] font-medium text-mint-ink disabled:opacity-40">{iduQ.isFetching ? '…' : 'Chercher'}</button>
      </div>
      {msg && <p data-scan-msg className="text-[11px] leading-snug text-st-creuser">{msg}</p>}
      {/* suggestions par nom (tant qu'aucun propriétaire n'est fixé sur cette saisie) */}
      {q.trim().length >= 2 && !looksSiren && !looksIdu && (sug.data?.length ?? 0) > 0 && (
        <div className="flex flex-col gap-1">
          {(sug.data ?? []).slice(0, 8).map((s) => (
            <button key={s.siren} data-scan-sug onClick={() => choisir(s.siren, s.nom)}
              className="flex items-center justify-between rounded-lg border border-line-2 bg-surface-3 px-3 py-1.5 text-left text-xs text-txt transition-colors duration-quick hover:border-mint/50">
              <span className="truncate">{s.nom}</span><span className="font-mono text-[11px] text-txt-dim">{s.n} parc.</span>
            </button>
          ))}
        </div>
      )}

      {/* S7.2 — DEUX onglets ; le propriétaire est partagé. */}
      <div className="seg self-start" role="tablist">
        <button data-scan-tab="possede" role="tab" aria-selected={tab === 'possede'} className={tab === 'possede' ? 'on' : ''} onClick={() => setTab('possede')}>Ce qu'ils possèdent</button>
        <button data-scan-tab="construit" role="tab" aria-selected={tab === 'construit'} className={tab === 'construit' ? 'on' : ''} onClick={() => setTab('construit')}>Ce qu'ils construisent</button>
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-1.5">
        {tab === 'possede'
          ? <M02 embedded sirenProp={owner} onVoirOperations={(s) => { setOwner(s); setTab('construit') }} />
          : <VeillePromoteurs embedded focusSiren={owner} onVoirPatrimoine={(s) => { setOwner(s); setTab('possede') }} />}
      </div>
    </div>
  )
}
