/**
 * ANNONCE-1 — outil « Analyser une annonce ».
 *
 * Un écran d'ENTRÉE, deux entrées : une ADRESSE (omnibox / clic carte) OU un LIEN d'annonce Leboncoin.
 *  · Entrée adresse → rapport PARCELLE : 6 tuiles (surface, zone PLU, SDP restante, classement LABUSE,
 *    risques, exposition) + « Estimation du prix » (comparateur DVF de la fiche, débloqué par l'idu :
 *    repère €/m², fourchette, fiabilité, N ventes · rayon · période) + « Le foncier ». Tout est LU sur
 *    la fiche parcelle SERVIE (`getFiche`) et l'exposition — rien n'est recalculé ici.
 *  · Entrée lien → rapport COMMUNE : « Ce que dit l'annonce » (champs PRÉSENTS seulement, jamais devinés),
 *    « Prix face au marché » (écart au repère commune du bon type, fiabilité LIMITÉE — aucune adresse
 *    précise, aucun rattachement parcelle), « La commune » (données communales existantes).
 *
 * DA : panneau gauche (320 px) + carte. En-tête maison (le MÊME bandeau que ModulePanel) rendu ICI
 * pour porter les 3 écrans — un SEUL Retour par écran (« ← Outils » à l'entrée, « ← Retour » dans un
 * rapport). Composants charte uniquement (Bouton/Retour/Badge/Chip/ParcelInput), aucune couleur neuve.
 * Changer d'outil vide tout (T1, `setModule`) ; l'état local (étape, saisies) repart à zéro au remontage.
 */
import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'

import { ParcelInput } from '../ParcelInput'
import { analyserAnnonce, docAnalyseAnnonceLienUrl, docAnalyseAnnonceUrl, getAnnonceEstimation, getFiche, getParcelExposition, type AnnonceAnalyse } from '../../lib/api'
import { fmtInt, fmtM2, iduCourt } from '../../lib/format'
import { useApp } from '../../store/useApp'
import { useOuvrirDocument } from '../../lib/ouvrirDocument'
import { Chargement } from '../Loading'
import { ErrorState } from '../States'
import { Bouton } from '../ui/Bouton'
import { Retour } from '../ui/Retour'
import { Badge } from '../ui/Badge'

// ANNONCE-3 — « Exporter en PDF » : le MÊME document que Docs (mêmes routes /analyse-annonce…), donc
// le PDF sorti de l'outil et celui de Docs sont identiques, mêmes chiffres que cet écran. Ouverture
// propre (fetch + blob + attente + message FR) via le hook partagé useOuvrirDocument.
function ExportPdf({ url }: { url: string }) {
  const { ouvrir, enCours, erreur } = useOuvrirDocument()
  return (
    <div className="shrink-0">
      <Bouton niveau="secondaire" ton="vert" className="w-full" disabled={!!enCours}
        onClick={() => void ouvrir(url, 'analyse-annonce')}>
        {enCours ? <Chargement variant="inline" accent="courant" label="Export…" /> : 'Exporter en PDF'}
      </Bouton>
      {erreur && <p className="mt-1 text-[12px] leading-snug text-coral">{erreur}</p>}
    </div>
  )
}

type Etape = 'entree' | 'parcelle' | 'annonce'

function fmtPeriode(p: number[] | string | null | undefined): string | null {
  if (!p) return null
  if (Array.isArray(p)) { const [a, b] = p; return a === b ? String(a) : `${a}–${b}` }
  return String(p)
}
// ANNONCE-3-FIX — fiabilité en TROIS niveaux capitalisés (l'étiquette « Fiabilité » est posée à côté
// du badge, donc le badge ne porte QUE le niveau) : « Élevée » (repère fiable), « Moyenne » (indicatif),
// « Limitée » (repli commune / entrée lien).
// CHASSE-4-FIX (C4-001) — le MOT vient du backend (`fiabilite_mot`, même source que le PDF) ; le front
// l'AFFICHE tel quel, sans retraduction qui pourrait diverger (l'ancienne version ratait « limitee » et
// remontait à « Moyenne »). Seule la COULEUR est dérivée du mot (visuel, pas le libellé).
function fiab(mot?: string | null): { mot: string; ton: 'vert' | 'ambre' } {
  return { mot: mot || 'Moyenne', ton: mot === 'Élevée' ? 'vert' : 'ambre' }
}
const cap = (s: string | null | undefined) => (s ? s[0].toUpperCase() + s.slice(1) : null)
// « de maisons » / « de terrain nu » mais « d’appartements » (élision devant voyelle) — CHASSE-4-FIX (C4-003).
const dePl = (pl: string) => (/^[aeiouyàâäéèêëîïôöùûü]/i.test(pl) ? `d’${pl}` : `de ${pl}`)

const INPUT_CLS =
  'w-full h-10 rounded-md border border-line-2 bg-surface-3 px-3 text-[13px] text-txt-hi ' +
  'placeholder:text-txt-mut focus:border-mint focus:outline-none'
const H_TILE = 'rounded-md border border-line-2 bg-surface-3 px-3 py-2'
const LBL = 'text-[10.5px] leading-tight text-txt-dim'
const VAL = 'mt-0.5 text-[13px] font-medium leading-tight text-txt-hi'
const SECTION = 'rounded-md border border-line-2 bg-surface-2 p-3'

// ───────────────────────────── En-tête maison (bandeau DA du panneau) ─────────────────────────────
function Entete({ retour, titre, sous }: { retour: { label: string; onClick: () => void }; titre: string; sous: React.ReactNode }) {
  const setModule = useApp((s) => s.setModule)
  return (
    <div className="flex shrink-0 flex-col border-b border-mint/20 bg-mint/[0.07] px-4 py-3">
      <div className="flex items-center justify-between gap-2">
        <Retour label={retour.label} onClick={retour.onClick} />
        <button onClick={() => setModule(null)} aria-label="Fermer le module"
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-txt-mut transition-colors duration-quick hover:bg-mint/10 hover:text-txt-hi">✕</button>
      </div>
      <div className="mt-1">
        <h2 className="text-sm font-medium leading-snug text-txt-hi">{titre}</h2>
        <p className="mt-0.5 text-[10.5px] leading-snug text-txt-dim">{sous}</p>
      </div>
    </div>
  )
}

function Corps({ children }: { children: React.ReactNode }) {
  return <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-4">{children}</div>
}

// ═══════════════════════════════════════ RAPPORT PARCELLE ═══════════════════════════════════════
function RapportParcelle({ idu }: { idu: string }) {
  const focusParcelle = useApp((s) => s.focusParcelle)
  const fiche = useQuery({ queryKey: ['annonce-fiche', idu], queryFn: () => getFiche(idu) })
  const expo = useQuery({ queryKey: ['annonce-expo', idu], queryFn: () => getParcelExposition(idu) })
  // RECETTE-4 — la tuile « Classement LABUSE » est remplacée par « Dernière vente » (date + prix DVF de la
  // parcelle, lus de la fiche `dvf_parcelle.derniere_mutation`). La requête `getAnnonceClassement` n'est
  // donc plus appelée côté écran.
  // ANNONCE-3-FIX — l'estimation selon la nature (nue → terrain nu ; bâtie → bâti), servie par le MÊME
  // point que le PDF (/radar/annonce/estimation) → mêmes chiffres à l'écran et dans le document.
  const estim = useQuery({ queryKey: ['annonce-estim', idu], queryFn: () => getAnnonceEstimation(idu) })

  if (fiche.isLoading) return <Corps><Chargement /></Corps>
  if (fiche.isError || !fiche.data) return <Corps><ErrorState message="Impossible de charger la fiche parcelle." retry={() => fiche.refetch()} /></Corps>
  const f = fiche.data
  const zone = f.reglement_plu?.zones?.[0]?.zone ?? null
  const pot = f.potentiel_transformation
  const sdp = pot?.sdp_residuelle_m2
  // RECETTE-4 — « Dernière vente » : date (MM/AAAA) + prix DVF de la parcelle (sa dernière mutation),
  // sinon « aucune depuis 2014 » (début de la couverture DVF). Lu de la fiche, aucun recalcul.
  const dm = (f.dvf_parcelle?.derniere_mutation ?? null) as { date_mutation?: string | null; valeur?: number | null } | null
  const derniereVente = dm?.date_mutation
    ? `${dm.date_mutation.slice(5, 7)}/${dm.date_mutation.slice(0, 4)}${dm.valeur != null ? ` · ${fmtInt(dm.valeur)} €` : ''}`
    : 'aucune depuis 2014'
  // CHASSE-4-FIX (C4-002) — la tuile « Risques » lit le MÊME compte dédupliqué que le PDF (servi par
  // l'estimation, `n_aleas` = liste `_risques_rows`). Repli sur le brut `aleas.n` seulement si l'estimation
  // n'est pas encore là.
  const nAleas = estim.data?.n_aleas ?? f.aleas?.n ?? 0
  const orientation = expo.data?.orientation ?? null

  const tuiles: { k: string; v: string }[] = [
    { k: 'Surface', v: fmtM2(f.surface_m2) },
    { k: 'Zone PLU', v: zone ?? '—' },
    { k: 'SDP restante', v: sdp == null ? '—' : fmtM2(Math.round(sdp)) },
    { k: 'Dernière vente', v: derniereVente },
    { k: 'Risques', v: nAleas === 0 ? 'aucun aléa' : `${nAleas} aléa${nAleas > 1 ? 's' : ''}` },
    { k: 'Exposition', v: orientation ?? '—' },
  ]

  // Estimation en €/m² (jamais un total inventé). Selon la nature de la parcelle : nue → repère terrain
  // nu ; bâtie → comparateur bâti. On lit le point unique partagé avec le PDF (pas de recalcul au front).
  const e = estim.data
  const terrain = e?.type_comparateur === 'terrain_nu'
  const median = e?.median ?? null
  const p25 = e?.q1 ?? null
  const p75 = e?.q3 ?? null
  const nVentes = e?.n ?? null
  const rayon = e?.radius_m ?? null
  const periode = fmtPeriode(e?.periode)
  const copro = e?.nature === 'copropriete'
  const fi = fiab(e?.fiabilite_mot)
  // CHASSE-4-FIX (C4-005) — périmètre des comparables avec le rayon RÉEL (distinct du « secteur cadastral »
  // du repère €/m²). Terrain nu → rayon des ventes de terrain ; bâti → rayon du comparateur bâti.
  const rayonComp = terrain ? e?.comparables_radius_m : rayon
  const rayonTxt = (rayonComp != null && rayonComp > 0)
    ? (rayonComp >= 1000 ? `à moins de ${rayonComp / 1000} km` : `à moins de ${fmtInt(rayonComp)} m`)
    : 'à proximité'

  return (
    <Corps>
      <div className="grid grid-cols-2 gap-2">
        {tuiles.map((t) => (
          <div key={t.k} className={H_TILE}>
            <p className={LBL}>{t.k}</p>
            <p className={VAL}>{t.v}</p>
          </div>
        ))}
      </div>
      {/* RECETTE-4 — le lien « Ouvrir la fiche parcelle → » remonte SOUS les tuiles (la section
          « Le foncier » qui le portait est supprimée). */}
      <Bouton niveau="lien" ton="vert" onClick={() => focusParcelle(idu, { fiche: true })}>Ouvrir la fiche parcelle →</Bouton>

      <section className={SECTION}>
        <h3 className="text-sm font-medium text-txt-hi">Estimation du prix</h3>
        {estim.isLoading ? (
          <p className="mt-1 text-[12px] text-txt-dim">…</p>
        ) : median == null ? (
          <p className="mt-1 text-[12px] text-txt-dim">
            {e?.note ?? (terrain
              ? 'Indisponible — pas assez de ventes de terrain nu comparables dans le secteur.'
              : 'Indisponible — pas assez de ventes comparables dans le secteur pour un repère de prix.')}
          </p>
        ) : (
          <>
            <p className="mt-1 text-xl font-semibold leading-none text-txt-hi">{fmtInt(Math.round(median))} €/m²</p>
            {p25 != null && p75 != null && (
              <p className="mt-0.5 text-[12px] text-txt-dim">de {fmtInt(Math.round(p25))} à {fmtInt(Math.round(p75))} €/m²</p>
            )}
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <span className="text-[11px] text-txt-dim">Fiabilité</span>
              <Badge ton={fi.ton} point>{fi.mot}</Badge>
              {/* ANNONCE-3-FIX-2 — le terrain nu affiche sa source comme le bâti : n réel · périmètre/rayon · période. */}
              {(nVentes != null || rayon != null || e?.perimetre || periode) && (
                <span className="text-[11px] text-txt-dim">
                  {nVentes != null ? `${fmtInt(nVentes)} ${terrain ? 'ventes de terrain' : 'ventes comparables'}` : (terrain ? 'ventes de terrain' : 'ventes comparables')}
                  {terrain ? (e?.perimetre ? ` · ${e.perimetre === 'secteur' ? 'secteur cadastral' : 'commune'}` : '') : (rayon != null ? ` · rayon ${fmtInt(Math.round(rayon))} m` : '')}
                  {periode ? ` · ${periode}` : ''}
                </span>
              )}
            </div>
            <p className="mt-2 text-[11px] leading-snug text-txt-mut">
              {terrain ? (
                <>Parcelle nue — comparée aux ventes de <strong className="text-txt-hi">terrain nu</strong> du secteur (repère €/m² de terrain).</>
              ) : copro ? (
                /* CHASSE-4-FIX (C4-003) — copropriété comparée aux appartements, pas de bien unique à valoriser. */
                <>Copropriété — comparée aux ventes d’<strong className="text-txt-hi">{e?.type_label_pluriel ?? 'appartements'}</strong> de la commune (repère €/m²). Le lot exact (étage, surface) n’est pas connu du modèle.</>
              ) : (
                <>{cap(e?.type_bien) ?? 'Bâti'} — comparé{e?.type_bien === 'maison' ? 'e' : ''} aux ventes de <strong className="text-txt-hi">{e?.type_label_pluriel ?? 'biens bâtis anciens'}</strong> autour de la parcelle. État et prestations du bien non connus du modèle.</>
              )}
              {e?.precision_pct != null && <> Précision mesurée sur les ventes 2025 : ±{fmtInt(e.precision_pct)} %.</>}
            </p>
            {/* ANNONCE-5-FIX — ORDRE DE GRANDEUR (jamais un calcul exact, bâti = emprise au sol). */}
            {e?.valeur_indicative && (
              <div className="mt-3 rounded-md border border-line-2 bg-surface-3 p-2.5">
                <p className="text-[10px] uppercase tracking-wide text-txt-dim">{terrain ? 'Ordre de grandeur du terrain' : 'Ordre de grandeur du bien'}</p>
                <p className="mt-1 flex justify-between gap-2 text-[12.5px] text-txt-hi">
                  <span className="text-txt-dim">{terrain ? `Terrain ${fmtM2(e.valeur_indicative.surface_m2)}` : `D’après l’emprise au sol BD TOPO (${fmtM2(e.valeur_indicative.surface_m2)})`} × {fmtInt(e.valeur_indicative.eur_m2)} €/m²</span>
                  <span className="shrink-0 font-semibold">{fmtInt(e.valeur_indicative.valeur_eur)} €</span>
                </p>
                {e.valeur_indicative.valeur_basse != null && e.valeur_indicative.valeur_haute != null && (
                  <p className="mt-1 flex justify-between gap-2 text-[12px] text-txt-dim">
                    <span>Fourchette</span><span className="shrink-0">{fmtInt(e.valeur_indicative.valeur_basse)} – {fmtInt(e.valeur_indicative.valeur_haute)} €</span>
                  </p>
                )}
                {!terrain && <p className="mt-1.5 text-[11px] leading-snug text-txt-mut">Ordre de grandeur, pas un calcul exact : la surface habitable réelle n’est pas connue (emprise au sol BD TOPO).</p>}
              </div>
            )}
            {/* Lecture foncière (parcelle bâtie) — comme la variante lien. */}
            {!terrain && e?.lecture_fonciere && (
              <div className="mt-2 rounded-md border border-line-2 bg-surface-3 p-2.5">
                <p className="text-[10px] uppercase tracking-wide text-txt-dim">Lecture foncière · valeur du terrain</p>
                <p className="mt-1 text-lg font-semibold leading-none text-mint">{fmtInt(e.lecture_fonciere.valeur_eur)} €</p>
                <p className="mt-0.5 text-[12px] text-txt-dim">{fmtM2(e.lecture_fonciere.surface_m2)} × {fmtInt(e.lecture_fonciere.eur_m2)} €/m² de terrain nu{e.lecture_fonciere.perimetre ? ` · ${e.lecture_fonciere.perimetre}` : ''}</p>
                {e.lecture_fonciere.pct_du_bati != null && <p className="mt-1 text-[11px] text-txt-mut">soit {fmtInt(e.lecture_fonciere.pct_du_bati)} % de l’ordre de grandeur bâti.</p>}
              </div>
            )}
          </>
        )}
      </section>

      {/* ANNONCE-5 — les 8 ventes comparables, accordéon FERMÉ par défaut (mêmes lignes que le PDF). */}
      {(e?.comparables?.length ?? 0) > 0 && (
        <details className={SECTION}>
          <summary className="cursor-pointer text-sm font-medium text-txt-hi">{terrain ? `Les ventes de terrain nu ${rayonTxt}` : 'Les ventes comparables'}{e?.n_total != null ? ` (${fmtInt(e.n_total)})` : ''}</summary>
          {/* RECETTE-4 — le tableau TIENT SANS DÉFILEMENT HORIZONTAL : police réduite (10 px), colonnes
              resserrées (padding serré), prix et €/m² sur UNE ligne (tabular-nums + nowrap). */}
          <div className="mt-2">
            <table className="w-full table-fixed text-[10px] tabular-nums">
              <thead>
                <tr className="text-left text-txt-dim">
                  <th className="pb-1 pr-1 font-medium">Date</th><th className="pb-1 pr-1 font-medium">Type</th>
                  <th className="pb-1 pr-1 text-right font-medium">Surf.</th><th className="pb-1 pr-1 text-right font-medium">Prix</th>
                  <th className="pb-1 pr-1 text-right font-medium">€/m²</th><th className="pb-1 text-right font-medium">Dist.</th>
                </tr>
              </thead>
              <tbody>
                {e!.comparables!.map((c, i) => (
                  <tr key={i} className="border-t border-line-2 text-txt-hi">
                    <td className="py-1 pr-1 whitespace-nowrap">{c.date ?? ''}</td><td className="py-1 pr-1 truncate">{c.type ?? ''}</td>
                    <td className="py-1 pr-1 text-right whitespace-nowrap">{c.surface_m2 != null ? fmtM2(c.surface_m2) : ''}</td>
                    <td className="py-1 pr-1 text-right whitespace-nowrap">{c.prix_eur != null ? `${fmtInt(c.prix_eur)} €` : ''}</td>
                    <td className="py-1 pr-1 text-right whitespace-nowrap">{c.prix_m2 != null ? fmtInt(c.prix_m2) : ''}</td>
                    <td className="py-1 text-right whitespace-nowrap">{c.distance_m != null ? `${fmtInt(c.distance_m)} m` : ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-1.5 text-[11px] leading-snug text-txt-mut">
            {(() => { const autres = Math.max(0, (e?.n_total ?? 0) - (e?.comparables?.length ?? 0)); const pl = terrain ? 'terrain nu' : (e?.type_label_pluriel ?? 'biens'); return autres > 0 ? `${fmtInt(autres)} autre${autres > 1 ? 's' : ''} vente${autres > 1 ? 's' : ''} ${dePl(pl)} ${rayonTxt}. ` : '' })()}
            Source : DVF, ventes {dePl(terrain ? 'terrain nu' : (e?.type_label_pluriel ?? 'biens'))}{(terrain ? fmtPeriode(e?.comparables_periode) : periode) ? `, ${terrain ? fmtPeriode(e?.comparables_periode) : periode}` : ''}.
          </p>
        </details>
      )}

      {/* RECETTE-4 — section « Le foncier » supprimée de l'écran (zone/hauteur/SDP restent dans la fiche
          parcelle, ouverte par le lien remonté sous les tuiles). */}

      <ExportPdf url={docAnalyseAnnonceUrl(idu)} />
    </Corps>
  )
}

// ════════════════════════════════════════ RAPPORT ANNONCE ════════════════════════════════════════
function pairs(entries: { k: string; v: string }[]) {
  return (
    <div className="grid grid-cols-2 gap-x-3 gap-y-2">
      {entries.map((e) => (
        <div key={e.k}>
          <p className={LBL}>{e.k}</p>
          <p className={VAL}>{e.v}</p>
        </div>
      ))}
    </div>
  )
}

function RapportAnnonce({ res }: { res: AnnonceAnalyse }) {
  const setContexteCommune = useApp((s) => s.setContexteCommune)
  const a = res.annonce!
  const commune = a.commune ?? ''
  const lb = res.lectures?.bati
  const lf = res.lectures?.fonciere
  const cm = res.commune

  // ANNONCE-1-FIX (pt 3) — « non précisé dans l'annonce » est RÉSERVÉ aux champs ATTENDUS pour ce type
  // et absents. Un champ non applicable au type (ex. Pièces sur un terrain) n'apparaît PAS du tout.
  const NP = 'non précisé dans l’annonce'
  const prixM2 = a.prix_m2 != null ? ` · ${fmtInt(a.prix_m2)} €/m²` : ''
  const rows: { k: string; v: string }[] = [
    { k: 'Prix demandé', v: a.prix != null ? `${fmtInt(a.prix)} €` : NP },
    { k: 'Type', v: cap(a.type) ?? NP },
  ]
  if (a.type === 'terrain') {
    rows.push({ k: 'Surface du terrain', v: a.surface_terrain != null ? `${fmtM2(a.surface_terrain)}${prixM2}` : NP })
  } else if (a.type === 'maison' || a.type === 'appartement') {
    rows.push({ k: 'Surface', v: a.surface_hab != null ? `${fmtM2(a.surface_hab)}${prixM2}` : NP })
    rows.push({ k: 'Pièces', v: a.pieces != null ? String(a.pieces) : NP })
    if (a.type === 'maison') rows.push({ k: 'Terrain', v: a.surface_terrain != null ? fmtM2(a.surface_terrain) : NP })
  } else {
    // type inconnu : on n'affirme aucun attendu → on ne montre que ce qui est réellement présent.
    if (a.surface_hab != null) rows.push({ k: 'Surface', v: `${fmtM2(a.surface_hab)}${prixM2}` })
    if (a.pieces != null) rows.push({ k: 'Pièces', v: String(a.pieces) })
    if (a.surface_terrain != null) rows.push({ k: 'Terrain', v: fmtM2(a.surface_terrain) })
  }

  const pctSigne = (n: number) => {
    const s = n.toFixed(1).replace('.', ',').replace(/,0$/, '')
    return n > 0 ? `+${s} %` : `${s} %`
  }
  const desc = (a as { description?: string | null }).description
  const descCourt = typeof desc === 'string' && desc.trim()
    ? (desc.trim().replace(/\s+/g, ' ').length > 150 ? desc.trim().replace(/\s+/g, ' ').slice(0, 148) + '…' : desc.trim().replace(/\s+/g, ' '))
    : null

  return (
    <Corps>
      <section className={SECTION}>
        <h3 className="text-sm font-medium text-txt-hi">Ce que dit l’annonce</h3>
        <div className="mt-2">{pairs(rows)}</div>
        {descCourt && (
          <p className="mt-2 border-l-2 border-line-2 pl-2 text-[11px] italic leading-snug text-txt-dim">« {descCourt} » <span className="not-italic text-txt-mut">— extrait, texte complet sur l’annonce</span></p>
        )}
        <p className="mt-2 text-[11px] leading-snug text-txt-mut">Seules les informations présentes dans l’annonce sont affichées.</p>
      </section>

      {/* ANNONCE-5 — les DEUX lectures CHIFFRÉES (la phrase « valeur surtout foncière » sans chiffre disparaît). */}
      <section className={SECTION}>
        <h3 className="text-sm font-medium text-txt-hi">Prix face au marché</h3>
        {(lb || lf) ? (
          <>
            <div className="mt-2 flex flex-col gap-2">
              {lb && (
                <div className="rounded-md border border-line-2 bg-surface-3 p-2.5">
                  <p className="text-[10px] uppercase tracking-wide text-txt-dim">Lecture bâti · au m² habitable</p>
                  <p className="mt-1 text-xl font-semibold leading-none text-txt-hi">{lb.ecart_pct > 0 ? '+' : ''}{lb.ecart_pct} %</p>
                  <p className="mt-0.5 text-[12px] text-txt-dim">face aux {lb.type_label_pluriel} de la commune{lb.referentiel_eur_m2 != null ? ` : ${fmtInt(lb.referentiel_eur_m2)} €/m²` : ''}</p>
                  {lb.n != null && <p className="mt-0.5 text-[11px] text-txt-mut">{fmtInt(lb.n)} ventes · {lb.type_label_pluriel}</p>}
                </div>
              )}
              {lf && (
                <div className="rounded-md border border-line-2 bg-surface-3 p-2.5">
                  <p className="text-[10px] uppercase tracking-wide text-txt-dim">Lecture foncière · valeur du terrain</p>
                  <p className="mt-1 text-xl font-semibold leading-none text-mint">{fmtInt(lf.valeur_eur)} €</p>
                  <p className="mt-0.5 text-[12px] text-txt-dim">{fmtM2(lf.terrain_m2)} × {fmtInt(lf.terrain_eur_m2)} €/m² de terrain nu</p>
                  <p className="mt-1 text-[11px] leading-snug text-txt-mut">{lf.conclusion}</p>
                </div>
              )}
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <span className="text-[11px] text-txt-dim">Fiabilité</span>
              <Badge ton="ambre" point>Limitée</Badge>
              <span className="text-[11px] text-txt-dim">repère communal, sans adresse précise · les deux lectures sont indicatives</span>
            </div>
          </>
        ) : (
          <p className="mt-1 text-[12px] text-txt-dim">
            Comparaison au marché indisponible : le prix, la surface ou le repère communal manquent pour cette annonce.
          </p>
        )}
      </section>

      <section className={SECTION}>
        <h3 className="text-sm font-medium text-txt-hi">La commune{commune ? ` · ${commune}` : ''}</h3>
        <div className="mt-2">
          {pairs([
            { k: 'Ventes de maisons, 12 mois', v: cm?.ventes_maison_12m != null ? fmtInt(cm.ventes_maison_12m) : '—' },
            { k: 'Prix médian maison', v: cm?.median_maison_eur_m2 != null ? `${fmtInt(cm.median_maison_eur_m2)} €/m²` : '—' },
            { k: 'Terrain nu, médiane', v: cm?.median_terrain_eur_m2 != null ? `${fmtInt(cm.median_terrain_eur_m2)} €/m²` : '—' },
            { k: 'Évolution maisons, 12 mois', v: cm?.evolution_maison_12m_pct != null ? pctSigne(cm.evolution_maison_12m_pct) : '—' },
            { k: 'PLU', v: cm?.plu_statut ?? '—' },
            { k: 'Aléas principaux', v: cm?.aleas?.length ? cm.aleas.join(', ') : '—' },
            { k: 'Permis déposés, 12 mois', v: cm?.permis_12m != null ? fmtInt(cm.permis_12m) : '—' },
          ])}
        </div>
        {commune && (
          <Bouton niveau="lien" ton="vert" className="mt-2" onClick={() => setContexteCommune(commune)}>Fiche commune →</Bouton>
        )}
      </section>

      <ExportPdf url={docAnalyseAnnonceLienUrl(a.url)} />
    </Corps>
  )
}

// ══════════════════════════════════════════ ÉCRAN D'ENTRÉE ══════════════════════════════════════════
export function AnalyserAnnonce() {
  const toggleOutils = useApp((s) => s.toggleOutils)
  const focusParcelle = useApp((s) => s.focusParcelle)
  const setModuleMap = useApp((s) => s.setModuleMap)
  const setFlyTo = useApp((s) => s.setFlyTo)

  const [etape, setEtape] = useState<Etape>('entree')
  const [parcelle, setParcelle] = useState<string | null>(null)
  const [lien, setLien] = useState('')
  const [erreur, setErreur] = useState<string | null>(null)
  const [res, setRes] = useState<AnnonceAnalyse | null>(null)

  // ANNONCE-1-FIX (pt 2) / ANNONCE-2 (pt 4) — UNE phrase d'erreur, aucun code HTTP ni jargon (le détail
  // technique part en log côté back). `url_bloquee` n'arrive QUE si le bien est absent du Radar ET que
  // Leboncoin bloque le fetch (le lookup Radar est tenté d'abord) → la phrase le dit.
  const messageErreur = (erreur?: string): string => {
    switch (erreur) {
      case 'url_bloquee':
        return 'Cette annonce n’a pas encore été relevée par LABUSE et Leboncoin bloque sa lecture automatique. Entrez l’adresse du bien pour l’analyser.'
      case 'url_illisible':
        return 'Cette page n’est pas une annonce exploitable. Entrez l’adresse du bien pour l’analyser.'
      case 'url_invalide':
        return 'Collez un lien d’annonce Leboncoin, ou entrez l’adresse du bien pour l’analyser.'
      default:
        return 'La lecture de l’annonce a échoué. Entrez l’adresse du bien pour l’analyser.'
    }
  }
  const analyse = useMutation({
    mutationFn: (url: string) => analyserAnnonce(url),
    onSuccess: (data) => {
      if (!data.ok || !data.annonce) { setErreur(messageErreur(data.erreur)); return }
      setErreur(null); setRes(data); setEtape('annonce')
    },
    onError: () => setErreur(messageErreur()),
  })

  // RECETTE-4 — pont Radar « Ce bien » → « Estimer ce bien → » : le lien de l'annonce préremplit l'entrée
  // LIEN et lance l'analyse au montage (consommé-puis-reset, comme les autres prefills).
  const annonceLienPrefill = useApp((s) => s.annonceLienPrefill)
  const setAnnonceLienPrefill = useApp((s) => s.setAnnonceLienPrefill)
  useEffect(() => {
    if (!annonceLienPrefill) return
    setLien(annonceLienPrefill)
    analyse.mutate(annonceLienPrefill)
    setAnnonceLienPrefill(null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Carte : parcelle zoomée+surlignée (adresse) · commune centrée sans parcelle (lien) · rien (entrée).
  const lastCommune = useRef<string | null>(null)
  useEffect(() => {
    if (etape === 'parcelle' && parcelle) {
      focusParcelle(parcelle)
    } else if (etape === 'annonce' && res?.annonce) {
      focusParcelle(null)
      setModuleMap({ idus: [], extra: null })
      const { lat, lng } = res.annonce
      if (lat != null && lng != null && res.annonce.commune !== lastCommune.current) {
        setFlyTo({ center: [lng, lat], zoom: 12 })
        lastCommune.current = res.annonce.commune
      }
    } else {
      focusParcelle(null)
      setModuleMap({ idus: [], extra: null })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [etape, parcelle, res])

  const revenir = () => { setEtape('entree'); setErreur(null) }

  if (etape === 'parcelle' && parcelle) {
    return (
      <>
        <Entete retour={{ label: 'Retour', onClick: revenir }}
          titre={iduCourt(parcelle)}
          sous={<>{parcelle} · <button className="underline underline-offset-2 hover:text-mint" onClick={revenir}>Changer de parcelle</button></>} />
        <RapportParcelle idu={parcelle} />
      </>
    )
  }

  if (etape === 'annonce' && res?.annonce) {
    const a = res.annonce
    const titre = `${a.type ? a.type[0].toUpperCase() + a.type.slice(1) : 'Annonce'}${a.pieces != null ? ` ${a.pieces} pièces` : ''}${a.commune ? ` · ${a.commune}` : ''}`
    const d = a.releve_le ? a.releve_le.split('-').reverse().join('/') : null
    return (
      <>
        <Entete retour={{ label: 'Retour', onClick: revenir }}
          titre={titre} sous={`Annonce Leboncoin${d ? ` · relevée le ${d}` : ''}`} />
        <RapportAnnonce res={res} />
      </>
    )
  }

  // ÉCRAN D'ENTRÉE
  return (
    <>
      {/* RECETTE-4 — titre renommé « Estimer un bien » (clé interne analyser-annonce inchangée). */}
      <Entete retour={{ label: 'Outils', onClick: toggleOutils }}
        titre="Estimer un bien"
        sous="Une adresse ou un lien d’annonce : LABUSE croise le bien avec le marché et le foncier." />
      <Corps>
        <div className="flex flex-col gap-1.5">
          <p className="text-[11px] font-medium text-txt-dim">Une adresse</p>
          <ParcelInput
            placeholder="Adresse, IDU ou référence (BW0917)"
            onPick={(idu) => { setParcelle(idu); setEtape('parcelle') }}
          />
        </div>

        <div className="flex items-center gap-2 text-[11px] text-txt-mut">
          <span className="h-px flex-1 bg-line-2" />OU<span className="h-px flex-1 bg-line-2" />
        </div>

        <div className="flex flex-col gap-1.5">
          <p className="text-[11px] font-medium text-txt-dim">Un lien d’annonce</p>
          <input
            className={INPUT_CLS}
            placeholder="https://www.leboncoin.fr/ventes_immobilieres/…"
            value={lien}
            onChange={(e) => { setLien(e.target.value); setErreur(null) }}
            onKeyDown={(e) => { if (e.key === 'Enter' && lien.trim() && !analyse.isPending) analyse.mutate(lien.trim()) }}
          />
          <Bouton niveau="primaire" ton="vert" className="self-start"
            disabled={!lien.trim() || analyse.isPending}
            onClick={() => analyse.mutate(lien.trim())}>
            {analyse.isPending ? 'Lecture…' : 'Analyser l’annonce'}
          </Bouton>
          {erreur && <p className="text-[12px] leading-snug text-coral">{erreur}</p>}
          <p className="text-[11px] leading-snug text-txt-mut">Leboncoin pour l’instant. SeLoger et Bien’ici à venir.</p>
        </div>
      </Corps>
    </>
  )
}

export default AnalyserAnnonce
