// M11 · SURFACE A — barre de recherche IA par fiche (maquette CADRE-M11 §1.4).
// Question libre sur LA parcelle → réponse SOURCÉE via le socle IA. L'IA cite ses sources
// et dit « non disponible » quand la donnée n'existe pas — jamais d'invention.
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { askParcel, type AskResponse, type Provenance } from '../../lib/api'

// clé de champ → libellé lisible pour l'étiquette de source
const SRC_LABEL: Record<string, string> = {
  zone_plu: 'zonage PLU', zone_plu_libelle: 'zonage PLU', reglement_regles: 'règlement PLU',
  viabilisation_assainissement: 'assainissement (M-VIA)', viabilisation_eau: 'eau (M-VIA)',
  viabilisation_elec: 'électricité (M-VIA)', viabilisation_indice: 'viabilisation (M-VIA)',
  viabilisation_cout_raccordement: 'coût raccordement (M-VIA)',
  risques: 'risques (PPR/Géorisques)', sdp_residuelle_m2: 'potentiel de transformation',
  potentiel_niveau: 'potentiel de transformation', faisabilite: 'moteur faisabilité',
  dvf_prix_m2_bati: 'prix DVF', motif_exclusion: 'cascade (motif)', surface_m2: 'cadastre',
}

function ProvChip({ src, prov, href }: { src: string; prov?: Provenance; href?: string }) {
  const label = SRC_LABEL[src] ?? src
  const style =
    prov === 'ESTIME' ? 'border-st-creuser/40 bg-[#211a10] text-st-creuser'
      : prov === 'ABSENT' ? 'border-line-2 bg-surface-2 text-txt-dim'
        : 'border-mint/40 bg-[#0f1a15] text-mint' // SOURCE (défaut)
  const tag = prov === 'ESTIME' ? 'Estimé' : prov === 'ABSENT' ? 'Absent' : 'Sourcé'
  const body = <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] ${style}`}>
    <b className="font-semibold">{tag}</b> · {label}{href ? ' ↗' : ''}
  </span>
  return href ? <a href={href} target="_blank" rel="noreferrer" title="Voir la source">{body}</a> : body
}

export function AskBar({ idu, zone }: { idu: string; zone?: string | null }) {
  const [q, setQ] = useState('')
  const ask = useMutation({ mutationFn: (question: string) => askParcel(idu, question) })
  const d: AskResponse | undefined = ask.data
  const run = (question: string) => { const t = question.trim(); if (t) { setQ(t); ask.mutate(t) } }

  const chips = [
    zone ? `Ça veut dire quoi la zone ${zone} ?` : 'Ça veut dire quoi cette zone ?',
    'Combien je peux construire ?',
    'C’est raccordé à l’assainissement ?',
    'Y a-t-il un risque inondation ?',
    'Pourquoi ce statut ?',
  ]

  return (
    <div data-askbar className="shrink-0 border-b border-[#B497F0]/50 bg-[#171221] px-5 py-3">
      <div className="flex items-center gap-2">
        <span className="font-mono text-[10px] tracking-widest text-[#B497F0]">✦ DEMANDER À L'IA</span>
        <span className="rounded bg-[#B497F0]/15 px-1.5 py-0.5 text-[9px] font-semibold text-[#B497F0]">PREMIUM</span>
      </div>
      <div className="mt-2 flex items-center gap-2">
        <input
          value={q} onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') run(q) }}
          placeholder="Expliquez un point, un acronyme, ou trouvez une donnée…"
          className="min-w-0 flex-1 rounded-lg border border-[#B497F0]/40 bg-surface-1 px-3 py-1.5 text-[12px] text-txt placeholder:text-txt-dim focus:border-[#B497F0] focus:outline-none" />
        <button onClick={() => run(q)} disabled={ask.isPending || !q.trim()}
          className="shrink-0 rounded-lg bg-[#B497F0] px-3 py-1.5 text-[12px] font-medium text-[#171221] disabled:opacity-40">
          {ask.isPending ? '…' : 'Demander'}
        </button>
      </div>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {chips.map((c) => (
          <button key={c} onClick={() => run(c)} disabled={ask.isPending}
            className="rounded-full border border-line-2 px-2.5 py-1 text-[10.5px] text-txt-mut hover:border-[#B497F0]/60 hover:text-txt">
            {c}
          </button>
        ))}
      </div>

      {/* état de chargement HONNÊTE (pas de silent-fail) */}
      {ask.isPending && <p className="mt-3 flex items-center gap-2 text-[11px] text-[#B497F0]">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[#B497F0]" /> L'IA lit la fiche…</p>}
      {ask.isError && <p className="mt-3 text-[11px] text-st-ecartee">Erreur — réessayez.</p>}

      {d && !ask.isPending && (
        <div className="mt-3 rounded-lg border border-line-2 bg-surface-1 p-3">
          {d.quota_atteint ? (
            <p className="text-[12px] text-st-creuser">{d.texte}</p>
          ) : d.degraded ? (
            <p className="text-[12px] text-st-ecartee">{d.texte}</p>
          ) : (
            <>
              <p className={`whitespace-pre-wrap text-[12px] leading-relaxed ${d.absent ? 'text-txt-dim italic' : 'text-txt'}`}>{d.texte}</p>
              {(d.sources?.length ?? 0) > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5 border-t border-line pt-2">
                  {d.sources!.map((s) => (
                    <ProvChip key={s} src={s} prov={d.provenance?.[s]} href={d.deeplinks?.[s]} />
                  ))}
                </div>
              )}
              {d.absent && (d.sources?.length ?? 0) === 0 && (
                <div className="mt-2 border-t border-line pt-2">
                  <ProvChip src="—" prov="ABSENT" />
                </div>
              )}
              {d.cached && <p className="mt-1.5 text-[9px] text-txt-dim">réponse en cache (aucun nouvel appel)</p>}
            </>
          )}
        </div>
      )}
    </div>
  )
}
