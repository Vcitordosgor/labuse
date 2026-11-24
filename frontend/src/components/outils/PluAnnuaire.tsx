import { useMutation, useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { pluAnnuaireSearch, pluAnnuaireCommunes, pluAnnuairePack, type PluExtrait } from '../../lib/api'
import { fmtDateNum } from '../../lib/format'
import { useApp } from '../../store/useApp'
import { Squelette } from '../Loading'
import { ErrorState } from '../States'
import { Bouton } from '../ui/Bouton'

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

// RECETTE-OUTILS-2 (R4) — `onHub` RETIRÉ (plus de hub PLU : l'Annuaire est la seule voie).
// Historique — RECETTE-OUTILS-1 (T3 / point 1) : `onHub` ramenait à la page des 2 voies. Le retour
// interne devient UN SEUL « Retour » hiérarchique : dans une commune → les 24 communes ; sur la liste
// → le choix du chemin (onHub). Les anciens « ← Choix PLU » (wrapper Plu) + « ← Les 24 communes » fusionnent.
export function PluAnnuaire() {
  const LIMIT = 25
  const [q, setQ] = useState('')
  const [insee, setInsee] = useState('')                     // '' = les 24 communes ; sinon une commune
  const [zone, setZone] = useState('')                       // filtre zone (lien contextuel fiche → recherche)
  const [page, setPage] = useState(0)                        // OUTIL-PLU-FIX-1 (LOT 5) — page servie (offset)
  const [mode, setMode] = useState<'choix' | 'recherche'>('choix')   // étape 2 : voie choisie
  const pluPrefill = useApp((s) => s.pluPrefill)
  const setPluPrefill = useApp((s) => s.setPluPrefill)
  const communes = useQuery({ queryKey: ['plu-communes'], queryFn: pluAnnuaireCommunes })
  // OUTIL-PLU-FIX-1 (LOT 5) — la recherche pagine RÉELLEMENT par offset : mutate(offset).
  const m = useMutation({ mutationFn: (off: number = 0) => pluAnnuaireSearch(q.trim(), insee || undefined, zone || undefined, off) })
  const d = m.data
  const run = () => { if (q.trim().length >= 2) { setPage(0); m.mutate(0) } }
  const goPage = (p: number) => { setPage(p); m.mutate(p * LIMIT) }

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

  // RETOURS-23 (pt 1) — le « ← Retour » interne est retiré : dans une commune, le bouton UNIQUE du
  // haut ramène aux 24 communes (sinon au menu Outils). On enregistre ce recul tant qu'on est entré
  // dans une commune ; au niveau racine (les 24), le retour de l'en-tête ferme l'outil.
  const setOutilSousRetour = useApp((s) => s.setOutilSousRetour)
  useEffect(() => {
    setOutilSousRetour(insee ? communesVue : null)
    return () => setOutilSousRetour(null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [insee, setOutilSousRetour])

  const cur = insee ? info(insee) : undefined
  const servable = cur?.statut === 'servable'

  return (
    <div data-plu-annuaire className="flex min-h-0 flex-1 flex-col gap-2 overflow-x-hidden overflow-y-auto">
      {/* RETOURS-23 (pt 1) — le « ← Retour » interne est retiré : le bouton unique de l'en-tête
          recule d'un niveau (commune → les 24 communes, via outilSousRetour ci-dessus). */}
      {/* ── ÉTAPE 1 — les 24 communes ─────────────────────────────────────────────── */}
      {!insee && (
        <>
          {/* CHASSE-APP-FIX-1 (pt 3) — squelette IMMÉDIAT pendant le chargement des 24 communes :
              avant, la liste était rendue sous `{communes.data && …}` seulement → zone BLANCHE tant que
              la réponse n'arrivait pas (constat chasse : PLU 37 s au 1er chargement, rien à l'écran). */}
          {communes.isLoading && <Squelette lignes={8} className="mt-1" label="Chargement des communes" />}
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
                {/* RECETTE-1 R26 — « · N procédures en cours » RETIRÉ de ce bandeau (demande Vic). */}
              </p>
              {/* RETOURS-23 (pt 5) — bandeau « N PLU en révision … N règlements non servis … texte à
                  consulter en mairie » RETIRÉ (demande Vic) : l'état par commune reste porté par le
                  badge « révision » / « RNU » / « non servi » de chaque carte ci-dessous. */}
              {/* R21 — UNE COLONNE : le nom de commune est TOUJOURS entier (la grille à 2 colonnes
                  écrasait « Saint-André » en « S… » dès qu'un badge s'ajoutait). */}
              <div className="grid grid-cols-1 gap-1.5">
                {communes.data.communes.map((c) => {
                  const ok = c.statut === 'servable'
                  // RETOURS-14 S3 — MÊME fond, MÊME texte pour les 24 (un PLU en révision est en
                  // vigueur ; le RNU est cliquable — il mène au règlement national) : le BADGE
                  // porte l'information, la carte ne s'éteint pas.
                  return (
                    <button key={c.insee} data-plu-commune={c.insee} onClick={() => entrer(c.insee)}
                      className="hover-fill flex cursor-pointer items-center justify-between gap-2 rounded-lg border border-line bg-surface-2 px-2.5 py-2 text-left">
                      {/* RETOURS-13 R21 — le NOM DE COMMUNE d'abord, toujours visible ; le badge dit
                          « révision », UN MOT, à droite, sur une ligne (le détail vit dans le title).
                          R23 — nowrap partout : jamais un badge sur deux lignes. */}
                      <span className="min-w-0 flex-1 text-[11.5px] font-medium text-txt">{c.commune}</span>
                      {/* UN SEUL badge, UN MOT (« révision »), à droite, sur une ligne — le détail
                          (prescription, règlement non servi) vit dans le title + la note ambre. */}
                      <span className="flex shrink-0 items-center gap-1 whitespace-nowrap">
                        {c.procedure_active
                          ? <span data-plu-procedure={c.insee} className="whitespace-nowrap rounded bg-cp-amber/15 px-1 font-mono text-[8px] text-cp-amber">{(c.procedure_active || '').split(' ')[0]}</span>
                          : !ok && <span className="whitespace-nowrap font-mono text-[8px] text-cp-amber">
                              {c.statut === 'rnu' ? 'RNU' : 'non servi'}</span>}
                      </span>
                    </button>
                  )
                })}
              </div>
              {/* OUTIL-PLU-FIX-1 (LOT 1) — l'absence de badge ne vaut PAS « aucune procédure » : le radar
                  (Sudocuh/registre) n'est pas exhaustif. On le DIT sous la liste. */}
              <p className="mt-1.5 px-0.5 text-[9px] leading-snug text-txt-dim">
                Un badge « révision » signale une procédure connue du radar ; son absence ne garantit pas
                qu’aucune procédure n’est en cours — vérifiez au GPU / en mairie.
              </p>
            </div>
          )}
        </>
      )}

      {/* fil « dans une commune » — le Retour unique est en tête du panneau (point 1) ; ici ne reste
          que le nom de la commune + le millésime/état. */}
      {insee && (
        <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-txt-mut">
          <b className="text-txt">{nomInsee(insee) ?? insee}</b>
          {servable
            ? <span className="font-mono text-[9px] text-mint/70">PLU du {cur?.millesime}</span>
            : <span className="font-mono text-[9px] text-cp-amber">{RAISON[cur?.statut ?? ''] ?? ''}</span>}
        </div>
      )}

      {/* ── ÉTAPE 2 — commune SANS règlement servi : on DIT pourquoi (aucun bouton mort) ── */}
      {insee && !servable && (
        <div data-plu-indispo className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11.5px] text-txt-mut">
          <span className="mr-1">🕓</span>{cur?.message ?? 'Règlement non disponible pour cette commune.'}
          {/* OUTIL-PLU-FIX-1 (LOT 1) — commune en révision dont le PLU opposable existe (Saint-André 2019,
              Saint-Leu 2007) : on DIT qu'il fait foi et on pointe la mairie, jamais « aucun document ». */}
          {cur?.note_doc && <p className="mt-1 text-[10.5px] text-txt-dim">{cur.note_doc}</p>}
          {/* RETOURS-14 S3 — le RNU est une VRAIE règle : la carte mène à son texte. */}
          {cur?.statut === 'rnu' && (
            <p className="mt-1.5">
              <a data-plu-rnu-lien href="https://www.legifrance.gouv.fr/codes/section_lc/LEGITEXT000006074075/LEGISCTA000031720025/"
                target="_blank" rel="noreferrer" className="text-mint hover:underline">
                Lire le règlement national d'urbanisme (art. R111-1 s., Légifrance) ↗
              </a>
            </p>
          )}
          {/* RETOURS-15 U8 — une commune en RÉVISION propose quand même son PLU EN VIGUEUR
              (résolu en direct sur le GPU). GPU vide (cas mesuré : Saint-André, Saint-Leu) →
              on le DIT et on donne la mairie ; GPU injoignable → dit comme tel. */}
          {cur?.statut === 'revision' && <PackVigueur insee={insee} />}
        </div>
      )}

      {/* ── ÉTAPE 2 — commune SERVABLE, voie à choisir : PLU intégral / Rechercher ── */}
      {insee && servable && mode === 'choix' && (
        <div data-plu-choix className="flex flex-col gap-2">
          {/* OUTIL-PLU-FIX-2 (C6) — le lien « intégral » est résolu EN DIRECT sur le GPU (comme pour une
              commune en révision), pas gelé à l'ingestion : si le dépôt actif change, le lien suit. */}
          <PackIntegral insee={insee} fallback={cur?.source_url ?? undefined} document={cur?.document ?? undefined} />
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
          {/* FUSION MINI-CORRECTIONS-2 × OUTIL-PLU-FIX-1 — l'encadré VERBEUX de pt 14 (nom de fichier +
              « édition <millésime> » + « Indexé : N extraits ») est bien RETIRÉ (grief Vic : du bruit).
              Mais le contre-audit EXIGE à l'écran : l'IDENTIFIANT du dépôt actif (idurba), les dates
              DISTINCTES (approbation / édition / publication, format FR — fini le « édition 17/12/2025 »
              faux), les actes postérieurs, les procédures, et la PART INDEXÉE. On réintroduit donc un
              bloc ÉPURÉ, porteur de cette seule information utile — pas l'ancien encadré. */}
          <div data-plu-doc-etat className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[10px] leading-snug text-txt-dim">
            {cur?.idurba && <span className="font-mono text-[9.5px]">dépôt {cur.idurba}</span>}
            {/* LOT 1 — dates distinctes, nommées, en français. */}
            <div className="mt-0.5 flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
              {cur?.date_approbation && <span>version approuvée le <b className="text-txt-mut">{fmtDateNum(cur.date_approbation) ?? cur.date_approbation}</b></span>}
              {cur?.edition && <span>· édition PDF {cur.edition}</span>}
              {cur?.publication_gpu && <span>· publiée au GPU le {fmtDateNum(cur.publication_gpu) ?? cur.publication_gpu}</span>}
            </div>
            {cur?.modifications && cur.modifications.length > 0 && (
              <div className="mt-0.5 text-cp-amber">
                {cur.modifications.map((mo, i) => (
                  <div key={i}>⚠ {mo.type}{mo.date ? ` du ${fmtDateNum(mo.date) ?? mo.date}` : ''}{mo.note ? ` — ${mo.note}` : ''}</div>
                ))}
              </div>
            )}
            {cur?.procedures_inventaire && cur.procedures_inventaire.length > 0 && (
              <div className="mt-0.5">Procédure(s) en cours : {cur.procedures_inventaire.map((p) => p.type).join(', ')} (source : contre-audit).</div>
            )}
            {/* LOT 3 — part INDEXÉE + pages en image : l'écran ne laisse plus croire qu'une commune
                sous-couverte « n'a pas la règle ». */}
            {cur?.pct_indexe != null && (
              <div className="mt-0.5">
                Indexé pour la recherche : ≈ {cur.pct_indexe} % des pages de texte
                {/* OUTIL-PLU-FIX-4 (critère 3) — part indexée À L'ARTICLE vs AU CHAPITRE, dite séparément. */}
                {cur.pct_article != null ? <> (dont ≈ {cur.pct_article} % à l’article{cur.pct_chapitre ? `, ${cur.pct_chapitre} % au chapitre` : ''})</> : null}
                {cur.pages_image ? <> · <b className="text-cp-amber">{cur.pages_image} page{cur.pages_image > 1 ? 's' : ''} en image</b> (non indexée{cur.pages_image > 1 ? 's' : ''})</> : null}
                {cur?.pagination_ambigue ? ' · pagination à vérifier' : ''}
                {cur.pct_indexe < 100 ? ' — le reste est dans le PDF intégral.' : '.'}
              </div>
            )}
            {/* OUTIL-PLU-FIX-4 (critère 3) — règlement peu structuré (scanné / en-têtes non détectés) :
                certains résultats sont servis AU CHAPITRE, pas à l'article. On le DIT à l'écran. */}
            {cur?.peu_structure && (
              <div className="mt-0.5 text-cp-amber">⚠ Règlement peu structuré : certains résultats sont donnés par chapitre (et non par article).</div>
            )}
            {/* OUTIL-PLU-FIX-2 (C7) — note d'édition (ex. La Possession : texte indexé déc. 2025, lien PDF
                juin 2026) servie aussi sur une commune SERVABLE, pas seulement en révision. */}
            {cur?.note_doc && <div className="mt-0.5 text-cp-amber">{cur.note_doc}</div>}
          </div>
          <div className="flex flex-col gap-2 rounded-lg border border-line-2 bg-surface-2 p-3">
            {/* RETOURS-15 C1 (P1) — le bouton « ← Voies » est retiré de l'annuaire (demande Vic). */}
            <p className="text-[10.5px] leading-snug text-txt-mut">
              Cherchez dans le règlement de <b className="text-txt">{nomInsee(insee)}</b> — verbatim
              sourcé (article, page, lien), jamais un résumé.
            </p>
            {/* OUTIL-PLU-FIX-1 (LOT 6) — mention VISIBLE du périmètre : la recherche porte sur le TEXTE
                du règlement de la commune ; elle ne vérifie PAS, pour une parcelle donnée, les
                prescriptions graphiques, les servitudes (SUP) ni le PPR. L'absence de résultat sur un
                risque ne vaut pas absence du risque. */}
            <p data-plu-limites className="rounded-md border border-line/60 bg-surface-3/60 px-2 py-1 text-[9.5px] leading-snug text-txt-dim">
              ⚠ Recherche <b>communale</b> (texte du règlement). Elle ne vérifie pas, à la parcelle, les
              prescriptions graphiques, les servitudes d’utilité publique ni le PPR — à contrôler sur la
              fiche parcelle et au document graphique.
            </p>
            <div className="flex gap-2">
              {/* RETOURS-5 T6 — plus d'autoFocus (même correction que « Étudier un bien ») : bord neutre au repos. */}
              {/* RECETTE-1 (H1, Vic) — placeholder RACCOURCI : « dans <commune> » était redondant (la
                  phrase au-dessus le dit déjà) et se faisait COUPER dans le champ étroit sur les noms de
                  commune longs. Reste l'exemple seul, qui tient toujours. */}
              <input data-plu-q value={q} onChange={(e) => setQ(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') run() }}
                placeholder="ex. hauteur clôture / Ua"
                className="min-w-0 flex-1 rounded-md border border-line-2 bg-surface-3 px-2.5 py-1.5 text-[12px] text-txt focus:outline-none" />
              <Bouton niveau="secondaire" ton="vert" onClick={run} disabled={q.trim().length < 2 || m.isPending}
                className="shrink-0 whitespace-nowrap">
                {m.isPending ? '…' : 'Chercher'}
              </Bouton>
            </div>
            {zone && (
              <div className="flex items-center gap-1.5 text-[10.5px] text-txt-mut">
                <span>Filtré sur la <span className="font-mono text-mint">zone {zone}</span> (depuis la fiche)</span>
                <button onClick={() => setZone('')} className="rounded bg-surface-3 px-1 text-txt-dim hover:text-txt">✕ retirer</button>
              </div>
            )}
          </div>

          {m.isError && (
            <ErrorState message="Erreur de recherche." retry={() => run()} />
          )}

          {/* OUTIL-PLU-FIX-2 (M2) — le 🕓 bandeau de STATUT ne vaut que pour RNU / révision (retour
              anticipé sans n_total) ; un 0-résultat de recherche (n_total === 0) passe par le bloc
              « aucun extrait » ci-dessous, qui garde le lien « Ouvrir le règlement ». */}
          {d?.message && d.n_total == null && (
            <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11.5px] text-txt-mut">
              <span className="mr-1">🕓</span>{d.message}
            </div>
          )}

          {/* OUTIL-PLU-FIX-1 (LOT 5) — le bloc d'exceptions est rendu HORS du bloc « résultats » : il
              s'affiche MÊME sans extrait trouvé (un filtre de zone erroné ne masque plus l'exception),
              et il DIT sa provenance (calibrage LABUSE, pas le texte indexé). */}
          {d && d.n_total != null && d.exceptions_zone && d.exceptions_zone.length > 0 && (
            <div data-plu-exceptions className="rounded-lg border border-amber/40 bg-amber/10 px-3 py-2">
              <div className="mb-1 text-[11px] font-medium text-amber">
                Exception{d.exceptions_zone.length > 1 ? 's' : ''} au règlement — zone {zone}
              </div>
              <div className="flex flex-col gap-1.5">
                {d.exceptions_zone.map((e, i) => (
                  <div key={i} className="text-[11px] leading-snug text-txt">
                    <em>« {e.texte} »</em>
                    {(e.article || e.page_pdf != null) && (
                      <span className="text-txt-mut"> — {[e.article, e.page_pdf != null ? `p. ${e.page_pdf}` : null].filter(Boolean).join(' · ')}</span>
                    )}
                  </div>
                ))}
              </div>
              {d.exceptions_source && <div className="mt-1 text-[9.5px] text-txt-dim">{d.exceptions_source}</div>}
            </div>
          )}

          {/* OUTILS-P1-1 (pt 9) — recherche VIDE sur un document (partiellement) indexé : on le DIT
              honnêtement (« Aucun extrait trouvé dans les documents indexés ») et on offre d'ouvrir le
              règlement intégral — le reste du règlement, non indexé, peut contenir d'autres passages. */}
          {d && d.n_total != null && d.resultats.length === 0 && (
            <div data-plu-aucun className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2.5 text-[11px] leading-snug text-txt-mut">
              <p>Aucun extrait trouvé dans les documents indexés{zone ? <> pour la zone <span className="font-mono text-mint">{zone}</span></> : null}.</p>
              <p className="mt-1 text-[10px] text-txt-dim">La recherche porte sur les articles indexés par LABUSE ; le règlement complet peut contenir d’autres passages.</p>
              {cur?.source_url && (
                <a data-plu-ouvrir-reglement href={cur.source_url} target="_blank" rel="noreferrer"
                  className="mt-1.5 inline-block text-[11px] font-medium text-mint hover:underline">Ouvrir le règlement ↗</a>
              )}
            </div>
          )}

          {d && d.n_total != null && d.resultats.length > 0 && (
            <div data-plu-results className="flex flex-col gap-2">
              <div className="text-[11px] text-txt-mut">
                {/* OUT-PLU-008 + LOT 5 — « X–Y sur M » : le décalage de page est DIT (jamais le compte
                    plafonné pris pour le total). */}
                {d.n_total != null && d.n_total > d.n
                  ? <>Extraits {page * LIMIT + 1}–{page * LIMIT + d.n} sur {d.n_total} — {nomInsee(insee)}</>
                  : <>{d.n} extrait{d.n > 1 ? 's' : ''} — {nomInsee(insee)}</>}
              </div>
              {/* O7(c) — chaque extrait : titre, aperçu, « Lire tout », sources (page PDF, lien PDF/zip). */}
              {d.resultats.map((r: PluExtrait, i: number) => (
                <PluExtraitCard key={i} r={r} premier={i === 0 && page === 0} />
              ))}
              {/* OUTIL-PLU-FIX-1 (LOT 5) — pagination : TOUS les résultats sont atteignables (offset réel). */}
              {d.n_total != null && d.n_total > LIMIT && (
                <div data-plu-pagination className="flex items-center justify-between gap-2 text-[11px]">
                  <button disabled={page === 0 || m.isPending} onClick={() => goPage(page - 1)}
                    className="rounded border border-line-2 px-2 py-1 text-txt-mut disabled:opacity-40 hover:text-txt">← Précédent</button>
                  <span className="text-txt-dim">page {page + 1} / {Math.ceil(d.n_total / LIMIT)}</span>
                  <button disabled={(page + 1) * LIMIT >= d.n_total || m.isPending} onClick={() => goPage(page + 1)}
                    className="rounded border border-line-2 px-2 py-1 text-txt-mut disabled:opacity-40 hover:text-txt">Suivant →</button>
                </div>
              )}
              {d.avis && <div className="text-[10px] text-txt-dim">{d.avis}</div>}
            </div>
          )}

          {/* OUTIL-PLU-FIX-3 (point 8) — les DISPOSITIONS COMMUNES (articles sans zone propre, communs à
              toutes les zones) sont présentées À PART, jamais mélangées aux articles de la zone filtrée. */}
          {d && d.n_total != null && d.dispositions_communes && d.dispositions_communes.length > 0 && (
            <div data-plu-communes className="flex flex-col gap-2">
              <div className="mt-1 text-[11px] font-medium text-txt-mut">
                Dispositions communes (applicables à toutes les zones) — {d.dispositions_communes.length}
              </div>
              {d.dispositions_communes.map((r: PluExtrait, i: number) => (
                <PluExtraitCard key={`c${i}`} r={r} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}

// RETOURS-23 (pt 6) — carte d'un extrait de règlement, maquette 8-plu-articles : numéro d'article en
// VERT mono, zone + commune en PUCES, TITRE en clair (lu côté back, remis en casse de phrase — jamais
// les majuscules recopiées du PDF), aperçu de TROIS lignes, « Lire tout ▾ » qui déplie DANS la carte,
// pied d'une ligne « Règlement du jj/mm/aaaa · p. N » + « PDF ↗ ». Le premier extrait porte un liseré
// vert (mis en avant). Plus de surlignage : le backend ne renvoie pas d'offset d'occurrence.
function numeroArticle(ref: string | null): string {
  if (!ref) return 'Article'
  const court = ref.replace(/^\s*(?:ARTICLE|Article|article)\s+/i, '').replace(/\s*[-–—]\s*$/, '').trim()
  return court || ref
}
function PluExtraitCard({ r, premier = false }: { r: PluExtrait; premier?: boolean }) {
  const [ouvert, setOuvert] = useState(false)
  const complet = r.texte_verbatim ?? ''
  const corps = r.corps && r.corps.trim() ? r.corps : complet
  const long = complet.trim().length > 180 || complet.length > corps.length + 8
  return (
    <div data-plu-carte className={`rounded-lg border bg-surface-2 px-3 py-2.5 ${premier ? 'border-mint/60' : 'border-line-2'}`}>
      {/* en-tête : numéro vert mono à gauche, puces zone/commune à droite */}
      <div className="flex items-start justify-between gap-2">
        <span className="shrink-0 font-mono text-[12px] font-medium text-mint">{numeroArticle(r.article_ref)}</span>
        <div className="flex flex-wrap items-center justify-end gap-1">
          {r.zone && <span className="rounded border border-line-2 bg-surface-3 px-1.5 py-0.5 text-[9.5px] text-txt-mut">zone {r.zone}</span>}
          <span className="rounded border border-line-2 bg-surface-3 px-1.5 py-0.5 text-[9.5px] text-txt-mut">{r.commune}</span>
        </div>
      </div>
      {/* titre « en clair », deux lignes au plus */}
      {r.titre && <p className="mt-1 line-clamp-2 text-[12px] font-medium leading-snug text-txt-hi">{r.titre}</p>}
      {/* aperçu 3 lignes (corps, sans le titre) ; déplié → verbatim complet */}
      <p className={`mt-1 whitespace-pre-wrap break-words text-[11px] leading-snug text-txt ${ouvert ? '' : 'line-clamp-3'}`}>
        {ouvert ? complet : corps}
      </p>
      {r.doute && (
        <span className="mt-1 inline-block rounded bg-st-ecartee/15 px-1 text-[9.5px] text-st-ecartee">doute — vérifier au PDF</span>
      )}
      {/* pied une ligne : règlement daté + PAGE DU MOT (+ étendue de l'article) · Lire tout ▾ · PDF ↗ */}
      <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 border-t border-line/60 pt-1.5 text-[10px] text-txt-dim">
        {/* OUTIL-PLU-FIX-3 — p. = page où le mot apparaît ; « article p. X-Y » quand l'article court
            sur plusieurs pages. « Lire tout » montre l'article ENTIER (exceptions comprises). */}
        {/* OUTIL-PLU-FIX-4 (point 1) — p. = TOUTES les pages où le mot apparaît (pluriels compris) ;
            « article p. X-Y » = étendue de l'article. Le lien ouvre la 1re page du mot. */}
        <span className="text-txt-mut">Règlement{r.millesime ? ` du ${fmtDateNum(r.millesime)}` : ''} · p. {r.pages_match && r.pages_match.length > 1 ? r.pages_match.join(', ') : r.page_pdf}{r.page_debut != null && r.page_fin != null && r.page_fin !== r.page_debut ? ` (article p. ${r.page_debut}-${r.page_fin})` : ''}</span>
        {long && (
          <button data-plu-lire onClick={() => setOuvert((o) => !o)} className="text-mint hover:underline">
            {ouvert ? 'Réduire ▲' : 'Lire l’article entier ▾'}
          </button>
        )}
        {/* OUTIL-PLU-FIX-1 (LOT 2) — un lien « PDF » ouvre un PDF (règlement écrit direct, + ancre
            #page) ; à défaut on dit clairement que c'est le pack .zip. Plus de « PDF ↗ » qui ouvrait un zip. */}
        {r.pdf_url
          ? <a href={`${r.pdf_url}#page=${r.page_pdf}`} target="_blank" rel="noreferrer" className="text-mint hover:underline">règlement PDF ↗ (p. {r.page_pdf})</a>
          : <a href={r.source_url} target="_blank" rel="noreferrer" className="text-txt-mut hover:underline">pack PLU (.zip) ↗</a>}
        {r.pagination_note && <span className="text-st-creuser">⚠ {r.pagination_note}</span>}
      </div>
    </div>
  )
}

// OUTIL-PLU-FIX-2 (C6) — bouton « PLU intégral (.zip) » d'une commune SERVABLE, résolu EN DIRECT sur le
// GPU (comme PackVigueur) : plus de lien gelé à l'ingestion. On garde le lien stocké en REPLI (GPU
// injoignable) et on ALERTE si le dépôt actif du GPU a dérivé depuis l'ingestion (idurba différent).
function PackIntegral({ insee, fallback, document }: { insee: string; fallback?: string; document?: string }) {
  const pack = useQuery({ queryKey: ['plu-pack', insee], queryFn: () => pluAnnuairePack(insee), staleTime: 300_000 })
  const p = pack.data
  const live = p?.disponible && p.url ? p.url : undefined
  const href = live ?? fallback ?? '#'
  return (
    <a data-plu-integral href={href} target="_blank" rel="noreferrer"
      className="hover-fill flex flex-col gap-0.5 rounded-lg border border-line-2 bg-mint/[0.05] px-3 py-2.5">
      <span className="text-[12.5px] font-medium text-mint">Télécharger le PLU intégral (.zip) ↓</span>
      <span className="text-[10px] leading-snug text-txt-dim">
        Pack officiel Géoportail de l’Urbanisme — règlement, zonage, annexes{document ? ` · contient ${document}` : ''}
        {live ? ' · lien vérifié en direct' : (pack.isLoading ? ' · vérification du pack actif…' : '')}
      </span>
    </a>
  )
}

// RETOURS-15 U8 — le PLU EN VIGUEUR d'une commune en révision, résolu EN DIRECT sur le GPU.
// Trois issues DISTINCTES, jamais confondues : trouvé (lien .zip + millésime + mention « reste
// applicable ») · GPU vide (dit, mairie servie — source K2) · GPU injoignable (dit comme tel).
function PackVigueur({ insee }: { insee: string }) {
  const pack = useQuery({ queryKey: ['plu-pack', insee], queryFn: () => pluAnnuairePack(insee), staleTime: 300_000 })
  if (pack.isLoading) return <Squelette lignes={2} className="mt-1.5" />
  const p = pack.data
  if (!p) return <ErrorState message="Vérification GPU impossible — réessayez." retry={() => pack.refetch()} />
  if (p.disponible && p.url) {
    return (
      <div className="mt-2">
        <a data-plu-pack-vigueur href={p.url} target="_blank" rel="noreferrer"
          className="hover-fill flex flex-col gap-0.5 rounded-lg border border-line-2 bg-mint/[0.05] px-3 py-2.5">
          <span className="text-[12px] font-medium text-mint">Télécharger le PLU en vigueur (.zip) ↓</span>
          <span className="text-[10px] leading-snug text-txt-dim">
            Pack officiel Géoportail de l'Urbanisme{p.millesime ? ` — version du ${p.millesime}` : ''}{p.idurba ? ` (${p.idurba})` : ''}
          </span>
        </a>
        <p className="mt-1 text-[10px] leading-snug text-txt-dim">
          Révision en cours — ce document reste applicable jusqu'à l'approbation du nouveau.
        </p>
      </div>
    )
  }
  return (
    <div data-plu-pack-absent className="mt-2 text-[10.5px] leading-snug">
      <p className={p.erreur === 'gpu_injoignable' ? 'text-st-creuser' : 'text-txt-mut'}>{p.message}</p>
      {p.mairie && !p.erreur && (
        <p className="mt-1 text-txt-dim">
          {p.mairie.nom}{p.mairie.telephone ? ` · ${p.mairie.telephone}` : ''}{p.mairie.email ? ` · ${p.mairie.email}` : ''}
          {p.mairie.site_officiel && (
            <> · <a href={p.mairie.site_officiel} target="_blank" rel="noreferrer" className="text-mint hover:underline">site officiel ↗</a></>
          )}
        </p>
      )}
    </div>
  )
}
