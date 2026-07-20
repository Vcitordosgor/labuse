// M11 · SURFACE A — barre de recherche IA par fiche (maquette CADRE-M11 §1.4).
// Question libre sur LA parcelle → réponse SOURCÉE via le socle IA. L'IA cite ses sources
// et dit « non disponible » quand la donnée n'existe pas — jamais d'invention.
import { Fragment, useEffect, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { askParcel, type AskResponse, type Provenance } from '../../lib/api'

// Rend le Markdown minimal du modèle et GARANTIT qu'aucun marqueur brut ne reste visible côté client
// (filet de sécurité : répare aussi les réponses DÉJÀ EN CACHE — cf. incident zonage 15/07 où un
// serveur pré-fix avait caché du « ## » et des « > »). Inline : **gras**, *italique*, `code`, [texte](url).
// Bloc (par ligne) : titres ##/###, citations >, listes - / * → stylés, marqueur retiré.

// Inline : découpe sur les motifs (ordre lien → gras → code → italique) — aucun astérisque/backtick résiduel.
function renderInline(text: string, kp: string) {
  return text.split(/(\[[^\]]+\]\([^)]+\)|\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/g).map((seg, i) => {
    const key = `${kp}-${i}`
    let m: RegExpMatchArray | null
    if ((m = seg.match(/^\[([^\]]+)\]\(([^)]+)\)$/)))
      return <a key={key} href={m[2]} target="_blank" rel="noreferrer" className="text-mint underline">{m[1]}</a>
    if (seg.length > 4 && seg.startsWith('**') && seg.endsWith('**'))
      return <strong key={key} className="font-semibold text-txt-hi">{seg.slice(2, -2)}</strong>
    if (seg.length > 2 && seg.startsWith('`') && seg.endsWith('`'))
      return <code key={key} className="rounded bg-surface-3 px-1 font-mono text-[11px]">{seg.slice(1, -1)}</code>
    if (seg.length > 2 && seg.startsWith('*') && seg.endsWith('*'))
      return <em key={key}>{seg.slice(1, -1)}</em>
    return <Fragment key={key}>{seg}</Fragment>
  })
}

export function renderRich(text: string) {
  const clean = text.replace(/\s+([.,;:!?%€])/g, '$1').replace(/[ \t]{2,}/g, ' ')
  return clean.split('\n').map((raw, i) => {
    const line = raw.trim()
    if (!line) return <span key={i} className="block h-1.5" />       // ligne vide → petit espace, jamais de vide brut
    let m: RegExpMatchArray | null
    if ((m = line.match(/^#{1,6}\s+(.*)$/)))                          // titre ## → ligne en gras (marqueur retiré)
      return <strong key={i} className="mt-1 block font-semibold text-txt-hi">{renderInline(m[1], `h${i}`)}</strong>
    if ((m = line.match(/^>\s?(.*)$/)))                               // citation > → filet gauche discret
      return <span key={i} className="mt-0.5 block border-l-2 border-line-2 pl-2 text-txt-mut">{renderInline(m[1], `q${i}`)}</span>
    if ((m = line.match(/^[-*]\s+(.*)$/)))                            // liste - / * → puce
      return <span key={i} className="block pl-2">· {renderInline(m[1], `l${i}`)}</span>
    return <span key={i} className="block">{renderInline(line, `p${i}`)}</span>
  })
}

// clé de champ → libellé lisible pour l'étiquette de source
const SRC_LABEL: Record<string, string> = {
  zone_plu: 'zonage PLU', zone_plu_libelle: 'zonage PLU', reglement_regles: 'règlement PLU',
  viabilisation_assainissement: 'assainissement (M-VIA)', viabilisation_eau: 'eau (M-VIA)',
  viabilisation_elec: 'électricité (M-VIA)', viabilisation_indice: 'viabilisation (M-VIA)',
  viabilisation_cout_raccordement: 'coût raccordement (M-VIA)',
  risques: 'risques (PPR/Géorisques)', sdp_residuelle_m2: 'potentiel de transformation',
  potentiel_niveau: 'potentiel de transformation', faisabilite: 'moteur faisabilité',
  dvf_prix_m2_bati: 'prix DVF', dvf_derniere_mutation: 'DVF (dernière vente)',
  motif_exclusion: 'cascade (motif)', surface_m2: 'cadastre',
  amenites: 'équipements à proximité (OSM)',
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

export function AskBar({ idu }: { idu: string; zone?: string | null }) {
  const [q, setQ] = useState('')
  const [open, setOpen] = useState(false)   // Fix point 6 : REPLIÉE par défaut — la fiche d'abord
  const ask = useMutation({ mutationFn: (question: string) => askParcel(idu, question) })
  const d: AskResponse | undefined = ask.data
  const run = (question: string) => { const t = question.trim(); if (t) { setQ(t); ask.mutate(t) } }
  // à chaque changement de fiche : on replie et on repart propre (l'IA ne s'impose jamais).
  useEffect(() => { setOpen(false); setQ(''); ask.reset() }, [idu])   // eslint-disable-line react-hooks/exhaustive-deps

  // Exemples curés (point 15) — tous GROUNDÉS sur la liste blanche de /ask (aménités = ajout backend).
  const chips = [
    'Y a-t-il des équipements à proximité ?',
    'Combien je peux construire ?',
    'C’est raccordé à l’assainissement ?',
    'Des ventes récentes dans le secteur ?',
    'Y a-t-il un risque inondation ?',
    'Pourquoi ce statut ?',
  ]

  // ── REPLIÉE (défaut) : juste un bouton découvrable — la fiche reste PLEINEMENT visible (point 6) ──
  if (!open) {
    return (
      <div data-askbar className="shrink-0 border-b border-[#B497F0]/50 bg-[#171221] px-5 py-2">
        <button data-askbar-open onClick={() => setOpen(true)}
          className="group flex w-full items-center gap-2 rounded-lg border border-[#B497F0]/40 bg-[#1d1630] px-3 py-1.5 hover:border-[#B497F0] hover:bg-[#241833]">
          <span className="font-mono text-[10px] tracking-widest text-[#B497F0]">✦ DEMANDER À L'IA</span>
          <span className="rounded bg-[#B497F0]/15 px-1.5 py-0.5 text-[9px] font-semibold text-[#B497F0]">PREMIUM</span>
          <span className="ml-auto text-[11px] text-txt-dim group-hover:text-txt-mut">
            {d && !ask.isPending ? 'dernière réponse gardée — rouvrir →' : 'une question sur cette parcelle →'}
          </span>
        </button>
      </div>
    )
  }

  // ── DÉPLIÉE : la zone complète (champ + exemples + réponse), refermable à tout moment ──
  return (
    <div data-askbar className="shrink-0 border-b border-[#B497F0]/50 bg-[#171221] px-5 py-3">
      <div className="flex items-center gap-2">
        <span className="font-mono text-[10px] tracking-widest text-[#B497F0]">✦ DEMANDER À L'IA</span>
        <span className="rounded bg-[#B497F0]/15 px-1.5 py-0.5 text-[9px] font-semibold text-[#B497F0]">PREMIUM</span>
        <button data-askbar-close onClick={() => setOpen(false)}
          className="ml-auto rounded px-1.5 py-0.5 text-[11px] text-txt-dim hover:bg-[#241833] hover:text-txt"
          title="Replier — afficher toute la fiche">✕ fermer</button>
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
              <p className={`whitespace-pre-wrap text-[12px] leading-relaxed ${d.absent ? 'text-txt-dim italic' : 'text-txt'}`}>{renderRich(d.texte)}</p>
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

      {/* FIX post-validation E : quand une réponse occupe l'espace, un lien CLAIR replie toute la
          zone IA (réponse comprise) et rend la place à la fiche. La réponse reste gardée — rouvrir
          « ✦ Demander à l'IA » la ré-affiche (cache inchangé, aucun nouvel appel). */}
      {d && !ask.isPending && (
        <button data-askbar-voir-fiche onClick={() => setOpen(false)}
          className="mt-2 flex w-full items-center justify-center gap-1 rounded-lg border border-[#B497F0]/30 bg-[#1d1630]/60 py-1.5 text-[11px] font-medium text-[#B497F0] hover:border-[#B497F0]/60 hover:bg-[#1d1630]"
          title="Replier l'IA et afficher toute la fiche — la réponse reste gardée (rouvrir pour la revoir)">
          Voir l'entièreté de la fiche →
        </button>
      )}
    </div>
  )
}
