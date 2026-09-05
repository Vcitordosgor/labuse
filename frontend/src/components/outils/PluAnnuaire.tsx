import { useMutation, useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { pluAnnuaireSearch, pluAnnuaireCommunes, type PluExtrait } from '../../lib/api'
import { useApp } from '../../store/useApp'

// M51 / M82 puis M137-P (fusion outil PLU) — ANNUAIRE PLU en DEUX ÉTAPES : (1) les 24 communes, on
// clique celle dont on veut le PLU ; (2) deux voies — le PLU INTÉGRAL (pack officiel GPU .zip, à
// télécharger : aucun PDF n'est stocké en base) OU la RECHERCHE verbatim dans le règlement. Les 3
// communes sans règlement servi (RNU / révision) sont CLIQUABLES et DISENT leur statut — jamais un
// bouton qui ne mène nulle part. Source Géoportail de l'Urbanisme.
const RAISON: Record<string, string> = {
  rnu: 'RNU — pas de règlement communal',
  revision: 'révision en cours — vérifier en mairie',
  non_ingere: 'non ingéré',
}

export function PluAnnuaire() {
  const [q, setQ] = useState('')
  const [insee, setInsee] = useState('')                     // '' = les 24 communes ; sinon une commune
  const [zone, setZone] = useState('')                       // filtre zone (lien contextuel fiche → recherche)
  const [mode, setMode] = useState<'choix' | 'recherche'>('choix')   // étape 2 : voie choisie
  const pluPrefill = useApp((s) => s.pluPrefill)
  const setPluPrefill = useApp((s) => s.setPluPrefill)
  const communes = useQuery({ queryKey: ['plu-communes'], queryFn: pluAnnuaireCommunes })
  const m = useMutation({ mutationFn: () => pluAnnuaireSearch(q.trim(), insee || undefined, zone || undefined) })
  const d = m.data
  const run = () => { if (q.trim().length >= 2) m.mutate() }

  // Ouvert depuis une fiche / le Copilote (zone servie) : commune + zone pré-remplies → droit en RECHERCHE.
  useEffect(() => {
    if (pluPrefill) {
      setInsee(pluPrefill.insee)
      setZone(pluPrefill.zone ?? '')
      setMode('recherche')
      setPluPrefill(null)
    }
  }, [pluPrefill, setPluPrefill])

  const info = (code: string) => communes.data?.communes.find((c) => c.insee === code)
  const nomInsee = (code: string | null) => (code ? info(code)?.commune : null)
  const entrer = (code: string) => { setInsee(code); setQ(''); setZone(''); setMode('choix'); m.reset() }
  const communesVue = () => { setInsee(''); setZone(''); setQ(''); setMode('choix'); m.reset() }

  const cur = insee ? info(insee) : undefined
  const servable = cur?.statut === 'servable'

  return (
    <div data-plu-annuaire className="flex min-h-0 flex-1 flex-col gap-2 overflow-x-hidden overflow-y-auto">
      {/* ── ÉTAPE 1 — les 24 communes ─────────────────────────────────────────────── */}
      {!insee && (
        <>
          <p className="px-0.5 text-[11.5px] leading-snug text-txt-mut">
            Cliquez sur la commune dont vous voulez consulter le PLU.
          </p>
          {communes.data && (
            <div data-plu-biblio>
              {/* RETOURS-12 O4 — le bandeau lit désormais la SOURCE UNIQUE des procédures (veille_plu,
                  la même que « Vérif procédure » et la fiche) : `n_procedures` = procédures PLU EN COURS
                  (révision/élaboration prescrites, Sudocuh) — inclut Les Trois-Bassins, que l'ancien
                  compteur (disponibilité du règlement GPU) ratait. Le RNU (absence de PLU) et le règlement
                  non servi restent distincts. Plus jamais deux comptes qui se contredisent. */}
              {/* RETOURS-13 R22 — un PLU en révision RESTE EN VIGUEUR : le compteur dit les PLU
                  existants (24 − RNU), les procédures, et NOMME les trous de source (règlement en
                  vigueur mais non servi par le GPU) au lieu d'un « 21 disponibles » faux. */}
              <p className="mb-0.5 px-0.5 font-mono text-[9px] uppercase tracking-[.14em] text-txt-dim">
                {communes.data.n_plu_vigueur ?? communes.data.servables} PLU en vigueur ({communes.data.n_communes} communes{communes.data.n_rnu > 0 && <>, {communes.data.n_rnu} au RNU</>})
                {communes.data.n_procedures > 0 && <> · {communes.data.n_procedures} procédure{communes.data.n_procedures > 1 ? 's' : ''} en cours</>}
              </p>
              {(communes.data.non_servis?.length ?? 0) > 0 && (
                <p data-plu-trous className="mb-1.5 px-0.5 text-[9.5px] leading-snug text-cp-amber">
                  Règlement de {communes.data.non_servis.length} commune{communes.data.non_servis.length > 1 ? 's' : ''} non servi par le Géoportail ({communes.data.non_servis.join(', ')}) — PLU en vigueur, texte à consulter en mairie.
                </p>
              )}
              {/* R21 — UNE COLONNE : le nom de commune est TOUJOURS entier (la grille à 2 colonnes
                  écrasait « Saint-André » en « S… » dès qu'un badge s'ajoutait). */}
              <div className="grid grid-cols-1 gap-1.5">
                {communes.data.communes.map((c) => {
                  const ok = c.statut === 'servable'
                  return (
                    <button key={c.insee} data-plu-commune={c.insee} onClick={() => entrer(c.insee)}
                      className={`hover-fill flex cursor-pointer items-center justify-between gap-2 rounded-lg border px-2.5 py-2 text-left ${
                        ok ? 'border-line bg-surface-2' : 'border-line/60 bg-surface-1'}`}>
                      {/* RETOURS-13 R21 — le NOM DE COMMUNE d'abord, toujours visible ; le badge dit
                          « révision », UN MOT, à droite, sur une ligne (le détail vit dans le title).
                          R23 — nowrap partout : jamais un badge sur deux lignes. */}
                      <span className={`min-w-0 flex-1 text-[11.5px] font-medium ${ok ? 'text-txt' : 'text-txt-dim'}`}>{c.commune}</span>
                      {/* UN SEUL badge, UN MOT (« révision »), à droite, sur une ligne — le détail
                          (prescription, règlement non servi) vit dans le title + la note ambre. */}
                      <span className="flex shrink-0 items-center gap-1 whitespace-nowrap">
                        {c.procedure_active
                          ? <span data-plu-procedure={c.insee} className="whitespace-nowrap rounded bg-cp-amber/15 px-1 font-mono text-[8px] text-cp-amber" title={`${c.procedure_active} en cours${c.procedure_date ? ` (prescrite le ${new Date(c.procedure_date).toLocaleDateString('fr-FR')})` : ''} — le PLU actuel reste en vigueur${!ok ? ' ; règlement non servi par le GPU, à consulter en mairie' : ''}`}>{(c.procedure_active || '').split(' ')[0]}</span>
                          : !ok && <span className="whitespace-nowrap font-mono text-[8px] text-cp-amber" title={c.message ?? ''}>
                              {c.statut === 'rnu' ? 'RNU' : 'non servi'}</span>}
                      </span>
                    </button>
                  )
                })}
              </div>
            </div>
          )}
        </>
      )}

      {/* fil de retour — dans une commune */}
      {insee && (
        <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-txt-mut">
          <button data-plu-retour onClick={communesVue} className="text-mint hover:underline">‹ Les 24 communes</button>
          <span>·</span><b className="text-txt">{nomInsee(insee) ?? insee}</b>
          {servable
            ? <span className="font-mono text-[9px] text-mint/70">PLU du {cur?.millesime}</span>
            : <span className="font-mono text-[9px] text-cp-amber">{RAISON[cur?.statut ?? ''] ?? ''}</span>}
        </div>
      )}

      {/* ── ÉTAPE 2 — commune SANS règlement servi : on DIT pourquoi (aucun bouton mort) ── */}
      {insee && !servable && (
        <div data-plu-indispo className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11.5px] text-txt-mut">
          <span className="mr-1">🕓</span>{cur?.message ?? 'Règlement non disponible pour cette commune.'}
        </div>
      )}

      {/* ── ÉTAPE 2 — commune SERVABLE, voie à choisir : PLU intégral / Rechercher ── */}
      {insee && servable && mode === 'choix' && (
        <div data-plu-choix className="flex flex-col gap-2">
          <a data-plu-integral href={cur?.source_url ?? '#'} target="_blank" rel="noreferrer"
            className="hover-fill flex flex-col gap-0.5 rounded-lg border border-line-2 bg-mint/[0.05] px-3 py-2.5">
            <span className="text-[12.5px] font-medium text-mint">Télécharger le PLU intégral (.zip) ↓</span>
            <span className="text-[10px] leading-snug text-txt-dim">Pack officiel Géoportail de l’Urbanisme — règlement, zonage, annexes{cur?.document ? ` · contient ${cur.document}` : ''}</span>
          </a>
          <button data-plu-rechercher onClick={() => setMode('recherche')}
            className="hover-fill flex flex-col gap-0.5 rounded-lg border border-line-2 bg-surface-2 px-3 py-2.5 text-left">
            <span className="text-[12.5px] font-medium text-txt">Rechercher dans le PLU →</span>
            <span className="text-[10px] leading-snug text-txt-dim">Le verbatim opposable (article, page, lien), jamais un résumé</span>
          </button>
        </div>
      )}

      {/* ── ÉTAPE 2 — RECHERCHE : la barre + le verbatim sourcé ── */}
      {insee && servable && mode === 'recherche' && (
        <>
          <div className="flex flex-col gap-2 rounded-lg border border-line-2 bg-surface-2 p-3">
            <div className="flex items-center justify-between gap-2">
              <p className="text-[10.5px] leading-snug text-txt-mut">
                Cherchez dans le règlement de <b className="text-txt">{nomInsee(insee)}</b> — verbatim
                sourcé (article, page, lien), jamais un résumé.
              </p>
              <button onClick={() => { setMode('choix'); setQ(''); m.reset() }}
                className="shrink-0 text-[10px] text-mint hover:underline">‹ voies</button>
            </div>
            <div className="flex gap-2">
              {/* RETOURS-5 T6 — plus d'autoFocus (même correction que « Étudier un bien ») : bord neutre au repos. */}
              <input data-plu-q value={q} onChange={(e) => setQ(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') run() }}
                placeholder={`dans ${nomInsee(insee)} — ex. hauteur de clôture`}
                className="min-w-0 flex-1 rounded-md border border-line-2 bg-surface-3 px-2.5 py-1.5 text-[12px] text-txt focus:border-mint focus:outline-none" />
              <button onClick={run} disabled={q.trim().length < 2 || m.isPending}
                className="shrink-0 whitespace-nowrap rounded-md border border-mint/50 bg-mint/15 px-3.5 py-1.5 text-[12px] font-medium text-mint disabled:opacity-40">
                {m.isPending ? '…' : 'Chercher'}
              </button>
            </div>
            {zone && (
              <div className="flex items-center gap-1.5 text-[10.5px] text-txt-mut">
                <span>Filtré sur la <span className="font-mono text-mint">zone {zone}</span> (depuis la fiche)</span>
                <button onClick={() => setZone('')} className="rounded bg-surface-3 px-1 text-txt-dim hover:text-txt">✕ retirer</button>
              </div>
            )}
          </div>

          {m.isError && (
            <div className="rounded-lg border border-st-ecartee/40 bg-st-ecartee/10 px-3 py-2 text-[11px] text-st-ecartee">
              Erreur de recherche.
            </div>
          )}

          {d?.message && (
            <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11.5px] text-txt-mut">
              <span className="mr-1">🕓</span>{d.message}
            </div>
          )}

          {d && !d.message && (
            <div data-plu-results className="flex flex-col gap-2">
              <div className="text-[11px] text-txt-mut">
                {d.n} extrait{d.n > 1 ? 's' : ''} — {nomInsee(insee)}
              </div>
              {/* O7(c) — chaque extrait : titre d'article en tête, un aperçu court (≈ 4 lignes) du
                  verbatim opposable, dépliable « voir l'article entier », puis les sources (page PDF,
                  archive GPU). Le champ « titre d'article » n'existe pas dans le payload → on affiche
                  la référence d'article (r.article_ref) comme titre ; l'aperçu est un simple
                  troncage front (le backend ne renvoie pas d'offset de surlignage). */}
              {d.resultats.map((r: PluExtrait, i: number) => (
                <PluExtraitCard key={i} r={r} />
              ))}
              {d.avis && <div className="text-[10px] text-txt-dim">{d.avis}</div>}
            </div>
          )}
        </>
      )}
    </div>
  )
}

// O7(c) — carte d'un extrait de règlement. Verbatim opposable montré en aperçu court (≈ 4 lignes),
// dépliable en entier. Pas de surlignage : le backend ne renvoie ni offset d'occurrence ni titre
// d'article distinct — on affiche donc la référence d'article comme titre et on tronque au front.
const APERCU_MAX = 260   // caractères d'aperçu (≈ 4 lignes) avant « voir l'article entier »
function PluExtraitCard({ r }: { r: PluExtrait }) {
  const [ouvert, setOuvert] = useState(false)
  const texte = r.texte_verbatim ?? ''
  const long = texte.length > APERCU_MAX
  const apercu = long && !ouvert ? texte.slice(0, APERCU_MAX).trimEnd() + '…' : texte
  return (
    <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2">
      <div className="flex flex-wrap items-baseline gap-x-2 text-[11px]">
        <span className="font-medium text-mint">{r.article_ref ?? 'Extrait du règlement'}</span>
        {r.zone && <span className="text-txt-mut">zone {r.zone}</span>}
        <span className="text-txt-mut">{r.commune}</span>
        {r.doute && (
          <span className="rounded bg-st-ecartee/15 px-1 text-[9.5px] text-st-ecartee">
            doute — vérifier au PDF
          </span>
        )}
      </div>
      <pre className="mt-1 whitespace-pre-wrap break-words font-sans text-[11px] leading-snug text-txt">{apercu}</pre>
      {long && (
        <button onClick={() => setOuvert((o) => !o)}
          className="mt-0.5 text-[10.5px] text-mint hover:underline">
          {ouvert ? '‹ replier l’article' : 'voir l’article entier →'}
        </button>
      )}
      <div className="mt-1 flex flex-wrap items-center gap-x-2 text-[10px] text-txt-dim">
        <span>{r.document}{r.millesime ? ` · ${r.millesime}` : ''}</span>
        <a href={r.source_url} target="_blank" rel="noreferrer" className="text-mint hover:underline">
          page PDF {r.page_pdf} · archive GPU ↗
        </a>
        {r.pagination_note && <span className="text-st-creuser">⚠ {r.pagination_note}</span>}
      </div>
    </div>
  )
}
