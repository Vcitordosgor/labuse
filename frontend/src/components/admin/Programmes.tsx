// PROMO-1 (P2/P3) — collecte assistée des programmes publiés par les promoteurs. L'admin colle l'URL du
// portfolio d'un promoteur → l'IA (modèle de ai_models.py, journalisé) propose {nom, commune, url, année} ;
// l'admin CORRIGE et VALIDE ligne à ligne AVANT insertion — rien n'entre sans validation. Aucun texte ni
// visuel du promoteur n'est stocké : seulement les faits + le lien.
//
// LOT S1 — le flux de collecte est EXTRAIT dans <CollecteProgrammes> (sous-composant réutilisable) afin
// d'être rejoué à l'intérieur de l'outil « Scan patrimoine » (onglet « Ce qu'ils construisent », geste
// admin discret), avec le SIREN du propriétaire courant PRÉ-REMPLI et verrouillé. La section admin
// historique <ProgrammesSection> (hors menu depuis LOT S1) réutilise le même sous-composant.
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { collecterProgrammes, delierProgramme, getProgrammes, supprimerProgramme, validerProgrammes,
  type ProgrammeCandidat } from '../../lib/api'

type Ligne = ProgrammeCandidat & { garder: boolean }

const inp = 'h-8 rounded-md border border-line-2 bg-surface-1 px-2 text-[12px] text-txt'

// LOT S1 — sous-composant de collecte réutilisable. `sirenFixe` : quand fourni (contexte Scan patrimoine),
// le SIREN est PRÉ-REMPLI et non éditable (c'est le propriétaire courant) et les champs identité sont
// masqués. `onValide` : notifie l'appelant (rafraîchir la liste embarquée). En mode admin plein (sans
// `sirenFixe`), les champs SIREN/nom restent saisissables comme avant.
export function CollecteProgrammes({ sirenFixe, nomFixe, onValide }: {
  sirenFixe?: string; nomFixe?: string; onValide?: () => void
} = {}) {
  const qc = useQueryClient()
  const [siren, setSiren] = useState(sirenFixe ?? '')
  const [nom, setNom] = useState(nomFixe ?? '')
  const [url, setUrl] = useState('')
  const [lignes, setLignes] = useState<Ligne[] | null>(null)
  const [motif, setMotif] = useState<string | null>(null)
  const [bilan, setBilan] = useState<string | null>(null)
  const verrou = !!sirenFixe   // SIREN imposé par le contexte (propriétaire courant)
  const effSiren = sirenFixe ?? siren

  const collecte = useMutation({
    mutationFn: () => collecterProgrammes({ url, promoteur_siren: effSiren || undefined, promoteur_nom: nom || undefined }),
    onSuccess: (r) => {
      setMotif(r.ok ? null : (r.motif ?? 'échec'))
      setLignes(r.ok ? (r.programmes ?? []).map((p) => ({ ...p, garder: true })) : null)
      if (r.promoteur_nom && !nom) setNom(r.promoteur_nom)
    },
  })
  const validation = useMutation({
    mutationFn: () => validerProgrammes({
      promoteur_siren: effSiren || undefined, promoteur_nom: nom || undefined, url_portfolio: url,
      programmes: (lignes ?? []).filter((l) => l.garder && l.nom.trim()).map(({ nom, commune, url, annee }) => ({ nom, commune, url, annee })),
    }),
    onSuccess: (r) => {
      setBilan(r.note); setLignes(null)
      qc.invalidateQueries({ queryKey: ['programmes-admin'] })
      if (effSiren) qc.invalidateQueries({ queryKey: ['programmes-admin', effSiren] })
      onValide?.()
    },
  })

  const maj = (i: number, patch: Partial<Ligne>) => setLignes((ls) => ls ? ls.map((l, j) => (j === i ? { ...l, ...patch } : l)) : ls)

  return (
    <div className="flex flex-col gap-3 text-[12.5px]">
      {/* collecte */}
      <section className="rounded-lg border border-line-2 bg-surface-2 p-3">
        <p className="text-[11px] text-txt-mut">Coller l'URL de la page « nos programmes » du site du promoteur. L'IA propose la liste ; vous corrigez et validez ligne à ligne. Aucun texte ni photo n'est conservé — seulement le nom, la commune et le lien.</p>
        <div className="mt-2 flex flex-wrap gap-2">
          {verrou ? (
            <span data-prog-siren-fixe className="inline-flex h-8 items-center rounded-md border border-line-2 bg-surface-1 px-2 font-mono text-[11px] text-txt-dim" title="SIREN du propriétaire courant">SIREN {sirenFixe}</span>
          ) : (
            <>
              <input data-prog-siren value={siren} onChange={(e) => setSiren(e.target.value)} placeholder="SIREN (si connu)" className={`w-40 ${inp}`} />
              <input data-prog-nom value={nom} onChange={(e) => setNom(e.target.value)} placeholder="Nom du promoteur" className={`w-52 ${inp}`} />
            </>
          )}
          <input data-prog-url value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://…/nos-programmes" className={`min-w-[240px] flex-1 ${inp}`} />
          <button data-prog-collecter onClick={() => { setBilan(null); setMotif(null); collecte.mutate() }} disabled={!url || collecte.isPending}
            className="h-8 rounded-md border border-mint/40 bg-mint/10 px-3 text-[12px] font-medium text-mint disabled:opacity-40">
            {collecte.isPending ? 'Lecture…' : 'Collecter'}
          </button>
        </div>
        {motif && <p className="mt-2 text-[11.5px] text-st-ecartee">Échec : {motif} — rien n'a été extrait (aucun programme inventé).</p>}
        {bilan && <p data-prog-bilan className="mt-2 text-[11.5px] text-mint">{bilan}</p>}
      </section>

      {/* validation ligne à ligne */}
      {lignes && (
        <section className="rounded-lg border border-line-2 bg-surface-2 p-3">
          <div className="mb-2 flex items-center gap-2">
            <h3 className="font-display text-sm font-bold text-txt-hi">Propositions du modèle — corrigez, puis validez</h3>
            <span className="text-[11px] text-txt-dim">{lignes.length} ligne{lignes.length > 1 ? 's' : ''}</span>
          </div>
          {lignes.length === 0 && <p className="text-[11.5px] text-txt-dim">Aucun programme repéré sur la page.</p>}
          <div className="flex flex-col gap-1.5">
            {lignes.map((l, i) => (
              <div key={i} data-prog-ligne className="grid grid-cols-[auto_1.6fr_1fr_2fr_auto] items-center gap-2">
                <input type="checkbox" checked={l.garder} onChange={(e) => maj(i, { garder: e.target.checked })} title="garder cette ligne" />
                <input value={l.nom} onChange={(e) => maj(i, { nom: e.target.value })} placeholder="nom du programme" className={inp} />
                <input value={l.commune ?? ''} onChange={(e) => maj(i, { commune: e.target.value || null })} placeholder="commune" className={inp} />
                <input value={l.url ?? ''} onChange={(e) => maj(i, { url: e.target.value || null })} placeholder="URL (lien)" className={`font-mono text-[10.5px] ${inp}`} />
                <input type="number" value={l.annee ?? ''} onChange={(e) => maj(i, { annee: e.target.value ? Number(e.target.value) : null })} placeholder="année" className={`w-16 ${inp}`} />
              </div>
            ))}
          </div>
          <button data-prog-valider onClick={() => validation.mutate()} disabled={validation.isPending || !lignes.some((l) => l.garder && l.nom.trim())}
            className="mt-3 h-8 rounded-md border border-mint/40 bg-mint/15 px-3 text-[12px] font-semibold text-mint disabled:opacity-40">
            {validation.isPending ? 'Enregistrement…' : `Valider ${lignes.filter((l) => l.garder && l.nom.trim()).length} programme(s)`}
          </button>
        </section>
      )}
    </div>
  )
}

export function ProgrammesSection() {
  const progs = useQuery({ queryKey: ['programmes-admin'], queryFn: () => getProgrammes() })

  return (
    <div data-admin-programmes className="flex flex-col gap-4 text-[12.5px]">
      {/* collecte (SIREN/nom saisissables — contexte admin plein) */}
      <section>
        <h3 className="mb-2 font-display text-sm font-bold text-txt-hi">Collecter un portfolio de promoteur</h3>
        <CollecteProgrammes onValide={() => progs.refetch()} />
      </section>

      {/* référentiel existant */}
      <section>
        <h3 className="mb-2 font-display text-sm font-bold text-txt-hi">Référentiel des programmes <span className="text-[11px] font-normal text-txt-dim">{progs.data ? `· ${progs.data.n}` : ''}</span></h3>
        <div className="overflow-hidden rounded-lg border border-line-2">
          <div className="grid grid-cols-[1.4fr_1.6fr_1fr_auto_auto] bg-surface-2 px-3 py-2 text-[11px] font-semibold text-txt-mut">
            <span>Promoteur</span><span>Programme</span><span>Commune</span><span>Rattachement</span><span></span>
          </div>
          {(progs.data?.programmes ?? []).map((p) => (
            <div key={p.id} data-prog-row className="grid grid-cols-[1.4fr_1.6fr_1fr_auto_auto] items-center border-t border-line-2 px-3 py-1.5 text-[11.5px]">
              <span className="truncate text-txt-mut" title={p.promoteur_nom}>{p.promoteur_nom}</span>
              <span className="truncate text-txt-hi" title={p.nom}>{p.url ? <a href={p.url} target="_blank" rel="noreferrer" className="text-mint hover:underline">{p.nom}</a> : p.nom}</span>
              <span className="text-txt-dim">{p.commune ?? '—'}{p.annee ? ` · ${p.annee}` : ''}</span>
              <span className="text-[10.5px]">{p.rattachement_mode
                ? <span className="text-mint">{p.rattachement_mode}{p.rattachement_confiance != null ? ` (${p.rattachement_confiance})` : ''} → {p.op_commune} {p.op_annee ?? ''}</span>
                : <span className="text-txt-dim">publié sur leur site</span>}</span>
              <span className="flex gap-2 text-[10.5px]">
                {p.rattachement_mode && <button onClick={() => delierProgramme(p.id).then(() => progs.refetch())} className="text-amber hover:underline">délier</button>}
                <button onClick={() => supprimerProgramme(p.id).then(() => progs.refetch())} className="text-st-ecartee hover:underline">suppr.</button>
              </span>
            </div>
          ))}
          {progs.data && progs.data.n === 0 && <p className="px-3 py-3 text-[11.5px] text-txt-dim">Aucun programme encore collecté.</p>}
        </div>
      </section>
    </div>
  )
}
