/**
 * ESTIMER-ECRAN-1 — l'outil « Estimer un bien » sur la maquette validée (nov-2026/12-estimer-un-ecran).
 *
 * UN SEUL ÉCRAN, bâti autour de la BOÎTE PARCELLE (option A : adresse en gras + « IDU · zone · surface »
 * + ✕ pour changer). Une fois la parcelle choisie (adresse, clic carte, ou pont « Estimer » de la fiche),
 * tout se construit DESSOUS, sur le point unique ESTIMER-3 (`POST /radar/annonce/estimation3/{idu}`) :
 *   · « Ce que LABUSE a mesuré » — en puces, UNIQUEMENT ce qui est connu (type, terrain, bâti au sol,
 *     niveaux, piscine, pente) ;
 *   · UNE SEULE question — la surface habitable, pré-remplie par l'estimation de LABUSE (badge « estimée »,
 *     hypothèse écrite dessous), saisie au clavier (badge « saisie » dès qu'on la change). Pour un
 *     APPARTEMENT s'ajoute le nombre de pièces ; pour un TERRAIN nu, aucune question ;
 *   · la VALEUR estimée — le montant, le badge de fiabilité, et une jauge à DEUX bandes servies telles
 *     quelles par l'API (« 1 fois sur 2 » = écart médian ; « 3 fois sur 4 » = Q3), chacune avec ses deux
 *     bornes en euros ; dessous la méthode servie (« Prix du secteur » / « Biens semblables ») ;
 *   · les VENTES RETENUES — chaque ligne se décoche (l'API recalcule) ;
 *   · « En vente en ce moment · Radar » — les biens similaires s'il y en a ;
 *   · le repère de marché (pas une expertise) et l'export PDF.
 *
 * L'entrée par LIEN d'annonce (Leboncoin) reste atteignable DEPUIS le Radar (« Estimer ce bien → ») et
 * rend son rapport commune inchangé ; la maquette validée, elle, est l'écran PARCELLE ci-dessus.
 *
 * DA : panneau gauche + carte, en-tête maison (le MÊME bandeau que ModulePanel) porté ici. La boîte
 * parcelle est le composant COMMUN des outils `EntreeParcelle` (option A, affichage instantané via
 * `getParcelApercu` : adresse + zone + surface d'un coup). Changer d'outil vide tout (T1).
 */
import { useEffect, useRef, useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'

import { EntreeParcelle, type SourceParcelle } from './EntreeParcelle'
import {
  analyserAnnonce, docAnalyseAnnonceLienUrl, docAnalyseAnnonceUrl, getEstimation3,
  type AnnonceAnalyse, type Estimer3Mesures, type Estimer3Rapport, type Estimer3Vente,
} from '../../lib/api'
import { fmtInt, fmtM2, aCommune } from '../../lib/format'
import { useApp } from '../../store/useApp'
import { useOuvrirDocument } from '../../lib/ouvrirDocument'
import { Chargement } from '../Loading'
import { ErrorState } from '../States'
import { Bouton } from '../ui/Bouton'
import { Retour } from '../ui/Retour'
import { Badge } from '../ui/Badge'

// « Exporter en PDF » : le MÊME document que Docs (route /analyse-annonce…), mêmes chiffres que l'écran.
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

// Fiabilité : le MOT vient du backend (`fiabilite_mot`), le front l'affiche tel quel ; seule la couleur
// est dérivée (Élevée → vert, sinon ambre) — même règle qu'ESTIMER-2.
function fiab(mot?: string | null): { mot: string; ton: 'vert' | 'ambre' } {
  return { mot: mot || 'Moyenne', ton: mot === 'Élevée' ? 'vert' : 'ambre' }
}
const cap = (s: string | null | undefined) => (s ? s[0].toUpperCase() + s.slice(1) : null)
const dePl = (pl: string) => (/^[aeiouyàâäéèêëîïôöùûü]/i.test(pl) ? `d’${pl}` : `de ${pl}`)

const LBL = 'text-[10.5px] leading-tight text-txt-dim'
const VAL = 'mt-0.5 text-[13px] font-medium leading-tight text-txt-hi'
const SECTION = 'rounded-md border border-line-2 bg-surface-2 p-3'
const SECTION_TITRE = 'text-[10px] font-semibold uppercase tracking-wide text-txt-dim'

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

// ═══════════════════════════ ÉCRAN ESTIMER — PARCELLE (maquette validée) ═══════════════════════════

// ── Dernière vente DE CE BIEN, montrée juste sous la boîte parcelle (JAMAIS dans le calcul) ──
function DerniereVente({ dv }: { dv: Estimer3Rapport['derniere_vente'] }) {
  if (!dv || !dv.date) return null
  // OUTILS-P0-2 (recette) — une mutation à prix SYMBOLIQUE (< 100 €, donation/cession familiale) n'est
  // PAS une vente de marché : « Dernière mutation : 12/2024 · cession à 1 €, hors marché » (pas « vente »,
  // pas de surface qui laisserait croire à un prix au m²). Sinon : « Dernière vente : … · surface · prix ».
  const symbolique = dv.prix_eur != null && dv.prix_eur < 100
  if (symbolique) {
    return (
      <p data-estimer-derniere-vente className="truncate text-[11px] leading-snug text-txt-dim">
        <span className="text-txt-mut">Dernière mutation :</span> {dv.date} · cession à {fmtInt(dv.prix_eur!)} €, hors marché
      </p>
    )
  }
  // Une seule ligne : « Dernière vente : 12/2025 · 116 m² · 455 000 € » (prix en gras, blanc).
  return (
    <p data-estimer-derniere-vente className="truncate text-[11px] leading-snug text-txt-dim">
      <span className="text-txt-mut">Dernière vente :</span> {dv.date}
      {dv.surface_m2 != null ? ` · ${fmtM2(dv.surface_m2)}` : ''}
      {dv.prix_eur != null && <> · <span className="font-semibold text-txt-hi">{fmtInt(dv.prix_eur)} €</span></>}
    </p>
  )
}

// ── « Ce que LABUSE a mesuré » : en puces, UNIQUEMENT ce qui est connu ──
function Mesures({ m, typeBien }: { m: Estimer3Mesures; typeBien: string }) {
  const typeLabel = typeBien === 'maison' ? 'Maison' : typeBien === 'appartement' ? 'Appartement' : 'Terrain nu'
  const puces: string[] = [typeLabel]
  if (m.terrain_m2) puces.push(`Terrain ${fmtM2(m.terrain_m2)}`)
  if (m.emprise_bati_m2) puces.push(`Bâti ${fmtM2(m.emprise_bati_m2)} au sol`)
  if (m.niveaux) puces.push(`${m.niveaux} niveau${m.niveaux > 1 ? 'x' : ''}`)
  if (m.piscine?.presente) puces.push('Piscine')
  if (m.pente) puces.push(`Pente ${m.pente.pct} %`)
  return (
    <section>
      <p className={SECTION_TITRE}>Ce que LABUSE a mesuré</p>
      <div className="mt-1.5 flex flex-wrap gap-1.5">
        {puces.map((p) => (
          <span key={p} className="rounded-md border border-line-2 bg-surface-3 px-2 py-1 text-[11px] leading-none text-txt">{p}</span>
        ))}
      </div>
    </section>
  )
}

// ── La jauge à deux bandes (servies telles quelles par l'API) : claire = « 3 fois sur 4 » (Q3),
//    foncée = « 1 fois sur 2 » (médian), repère central sur la valeur estimée. ──
function Jauge({ valeur, basse, haute, basseQ3, hauteQ3 }: {
  valeur: number; basse: number; haute: number; basseQ3: number; hauteQ3: number
}) {
  const lo = Math.min(basseQ3, basse)
  const hi = Math.max(hauteQ3, haute)
  const span = hi - lo || 1
  const pct = (x: number) => Math.max(0, Math.min(100, ((x - lo) / span) * 100))
  const g = pct(basse), d = pct(haute), c = pct(valeur)
  return (
    <div className="relative mt-2 h-2.5 w-full rounded-full bg-mint/15" aria-hidden>
      <div className="absolute inset-y-0 rounded-full bg-mint/45" style={{ left: `${g}%`, width: `${Math.max(2, d - g)}%` }} />
      <div className="absolute top-1/2 h-3.5 w-0.5 -translate-y-1/2 rounded-full bg-mint" style={{ left: `calc(${c}% - 1px)` }} />
    </div>
  )
}

// ── La valeur estimée : montant + fiabilité + jauge deux bandes + méthode servie ──
function ValeurEstimee({ e, typeBien, commune }: { e: Estimer3Rapport['estimation']; typeBien: string; commune: string | null }) {
  const fi = fiab(e.fiabilite_mot)
  const typePl = typeBien === 'maison' ? 'maisons' : typeBien === 'appartement' ? 'appartements' : 'terrains'
  const methode = e.methode_prix === 'semblable' ? 'Biens semblables' : 'Prix du secteur'
  const ligneMethode = (
    <p className="mt-2 text-[11px] leading-snug text-txt-mut">
      <strong className="font-medium text-txt-dim">{methode}</strong> · mesuré sur les ventes réelles {dePl(typePl)}{commune ? ` ${aCommune(commune)}` : ''}.
    </p>
  )
  // DÉFAUT B (Vic, correction) — sur un bien bâti, AUCUNE valeur de terrain n'est affichée (ni bandeau,
  // ni bloc) : mesuré au banc, la retenir dégrade la précision. La fiabilité reste celle du banc.

  // DÉFAUT A (Vic) — surface habitable inconnue + bande « 3 fois sur 4 » trop large : PAS de valeur totale.
  // On sert le prix au m² du secteur avec sa fourchette, et on invite à saisir la surface (la valeur et ses
  // deux bandes reviennent dès qu'elle est saisie — l'API lève le masque).
  if (e.total_masque && e.eur_m2 != null) {
    return (
      <section className={SECTION} role="status" aria-live="polite">
        <p className={SECTION_TITRE}>Prix au m²</p>
        <div className="mt-1 flex flex-wrap items-center gap-2">
          <span className="text-[26px] font-semibold leading-none text-txt-hi">{fmtInt(e.eur_m2)} €/m²</span>
          <Badge ton={fi.ton} point>Fiabilité {fi.mot.toLowerCase()}</Badge>
        </div>
        {e.eur_m2_bas != null && e.eur_m2_haut != null && (
          <p className="mt-1 text-[12px] text-txt-dim">de {fmtInt(e.eur_m2_bas)} à {fmtInt(e.eur_m2_haut)} €/m²</p>
        )}
        <p data-estimer-invite-surface className="mt-2 rounded-md border border-mint/30 bg-mint/[0.06] px-2.5 py-2 text-[11px] leading-snug text-txt-dim">
          Saisissez la surface habitable ci-dessus pour obtenir une valeur totale et ses deux fourchettes. Sans elle, la fourchette serait trop large pour un montant fiable.
        </p>
        {ligneMethode}
      </section>
    )
  }
  // OUTILS-P0-2 (P2) — terrain nu SANS total à bâtir (hors gamme des ventes de référence, ou non
  // constructible) : pas de montant, mais le repère au m² et la raison restent affichés (les ventes
  // de référence sont servies plus bas). On N'INVENTE PAS un total que les ventes ne peuvent pas porter.
  if (e.terrain_sans_total_raison && e.eur_m2 != null) {
    return (
      <section className={SECTION} role="status" aria-live="polite">
        <p className={SECTION_TITRE}>Prix au m²</p>
        <div className="mt-1 flex flex-wrap items-center gap-2">
          <span className="text-[26px] font-semibold leading-none text-txt-hi">{fmtInt(e.eur_m2)} €/m²</span>
          <Badge ton={fi.ton} point>Fiabilité {fi.mot.toLowerCase()}</Badge>
        </div>
        {e.eur_m2_bas != null && e.eur_m2_haut != null && (
          <p className="mt-1 text-[12px] text-txt-dim">de {fmtInt(e.eur_m2_bas)} à {fmtInt(e.eur_m2_haut)} €/m²</p>
        )}
        <p data-estimer-terrain-sans-total className="mt-2 rounded-md border border-cp-amber/30 bg-cp-amber/[0.07] px-2.5 py-2 text-[11px] leading-snug text-txt-dim">
          {e.terrain_sans_total_raison}
        </p>
      </section>
    )
  }
  // OUTILS-P0-2 (recette, point 4) — TERRAIN NON CONSTRUCTIBLE : aucune estimation, aucun prix au m².
  // « Pas d'estimation : zone non constructible (A) ». La dernière vente de la parcelle est montrée à part.
  if (e.terrain_non_constructible) {
    return (
      <section className={SECTION} role="status" aria-live="polite">
        <p className={SECTION_TITRE}>Estimation</p>
        <p data-estimer-non-constructible className="mt-1 rounded-md border border-cp-amber/30 bg-cp-amber/[0.07] px-2.5 py-2 text-[12px] leading-snug text-txt-dim">
          {e.terrain_sans_total_raison ?? 'Pas d’estimation : parcelle non constructible.'}
        </p>
      </section>
    )
  }
  if (e.valeur_eur == null) {
    return (
      <section className={SECTION} role="status" aria-live="polite">
        <p className={SECTION_TITRE}>Valeur estimée</p>
        <p className="mt-1 text-[12px] leading-snug text-txt-dim">
          Indisponible — pas assez de ventes comparables dans le secteur pour un repère de prix.
        </p>
      </section>
    )
  }
  const bq = e.valeur_basse_q3, hq = e.valeur_haute_q3, bm = e.valeur_basse, hm = e.valeur_haute
  // OUTILS-P0-2 (recette, point 3) — les bandes servies telles quelles par le banc (deux distinctes, ou
  // une seule « Fourchette estimée »). Repli si l'API ne les fournit pas (anciens clients).
  const bandes = (e.fourchettes && e.fourchettes.length)
    ? e.fourchettes
    : (bm != null && hm != null
        ? (bq != null && hq != null && (bq !== bm || hq !== hm)
            ? [{ nom: '1 fois sur 2', basse: bm, haute: hm }, { nom: '3 fois sur 4', basse: bq, haute: hq }]
            : [{ nom: 'Fourchette estimée', basse: bm, haute: hm }])
        : [])
  return (
    <section className={SECTION} role="status" aria-live="polite">
      <p className={SECTION_TITRE}>Valeur estimée</p>
      <div className="mt-1 flex flex-wrap items-center gap-2">
        <span className="text-[26px] font-semibold leading-none text-txt-hi">{fmtInt(e.valeur_eur)} €</span>
        <Badge ton={fi.ton} point>Fiabilité {fi.mot.toLowerCase()}</Badge>
      </div>
      {bandes.length > 0 && (
        <>
          {bm != null && hm != null && (
            <Jauge valeur={e.valeur_eur} basse={bm} haute={hm} basseQ3={bq ?? bm} hauteQ3={hq ?? hm} />
          )}
          <div className="mt-2 space-y-1">
            {bandes.map((b, i) => (
              <div key={b.nom} className="flex items-center justify-between gap-2 text-[12px]">
                <span className="text-txt-dim">{b.nom}</span>
                <span className={`tabular-nums ${i === 0 ? 'font-medium text-txt-hi' : 'text-txt-dim'}`}>{fmtInt(b.basse)} – {fmtInt(b.haute)} €</span>
              </div>
            ))}
          </div>
          {/* OUTILS-P0-2 (P4) — d'où viennent les fourchettes (ventes passées de biens comparables). */}
          <p className="mt-1.5 text-[11px] leading-snug text-txt-mut">
            Fourchettes mesurées sur des ventes passées de biens comparables.
          </p>
        </>
      )}
      {ligneMethode}
    </section>
  )
}

// ── Les ventes retenues : chaque ligne se décoche (l'API recalcule) ──
function VentesRetenues({ ventes, ecartees, onToggle, typeBien }: {
  ventes: Estimer3Vente[]; ecartees: Set<string>; onToggle: (id: string) => void; typeBien: string
}) {
  if (!ventes.length) return null
  // Une mutation peut arriver deux fois (plusieurs lots d'un même acte) : on ne garde qu'une ligne par
  // identifiant pour l'affichage (clé stable, pas de doublon à l'écran).
  const vues = new Set<string>()
  const uniques = ventes.filter((v) => (vues.has(v.id) ? false : (vues.add(v.id), true)))
  return (
    <section>
      <div className="flex items-baseline justify-between gap-2">
        <p className={SECTION_TITRE}>Les ventes retenues</p>
        <span className="text-[10px] text-txt-mut">décochez pour écarter</span>
      </div>
      {/* OUTILS-P0-2 (recette) — rien de tronqué, et chaque chiffre dit ce qu'il mesure selon le type :
          · TERRAIN → la surface est celle du TERRAIN (« 472 m² de terrain »), jamais « hab. » ;
          · APPARTEMENT → surface habitable seule, AUCUNE mention de terrain ;
          · MAISON → habitable + terrain (si renseigné, sinon rien — plus de « terrain non renseigné ») ;
          · distance = la VRAIE (ST_Distance), « — » si inconnue, jamais « 0 m » par défaut. */}
      <ul className="mt-1.5 flex flex-col gap-1">
        {uniques.map((v) => {
          const off = ecartees.has(v.id)
          const terrain = typeBien === 'terrain'
          const appart = typeBien === 'appartement'
          const surfTxt = v.surface_m2 != null
            ? (terrain ? `${fmtM2(v.surface_m2)} de terrain` : `${fmtM2(v.surface_m2)} habitable`)
            : null
          const terrTxt = (!terrain && !appart && v.terrain_m2) ? `${fmtM2(v.terrain_m2)} de terrain` : null
          const distTxt = v.distance_m != null && v.distance_m > 0 ? `${fmtInt(v.distance_m)} m` : '—'
          return (
            <li key={v.id}>
              <label className={`flex cursor-pointer items-start gap-2 rounded-md border px-2 py-1.5 text-[11px] ${off ? 'border-line-2 bg-surface-2 opacity-50' : 'border-line-2 bg-surface-3'}`}>
                <input type="checkbox" checked={!off} onChange={() => onToggle(v.id)}
                  className="mt-0.5 h-3.5 w-3.5 shrink-0 accent-mint" aria-label={`Vente ${v.date ?? ''} — ${off ? 'écartée' : 'retenue'}`} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="tabular-nums text-txt-dim">{v.date ?? ''}</span>
                    <span className="tabular-nums font-medium text-txt-hi">{v.prix_eur != null ? `${fmtInt(v.prix_eur)} €` : ''}</span>
                  </div>
                  <div className="mt-0.5 flex flex-wrap gap-x-2 gap-y-0.5 tabular-nums text-txt-dim">
                    {surfTxt && <span>{surfTxt}</span>}
                    {terrTxt && <span>{terrTxt}</span>}
                    <span>· {distTxt}</span>
                  </div>
                </div>
              </label>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

// ── « En vente en ce moment · Radar » : les 5 annonces similaires LES PLUS PROCHES (commune + distance) ;
//    le bloc n'apparaît pas s'il n'y en a aucune à proximité. ──
const fmtDist = (m?: number | null): string | null =>
  m == null ? null : (m >= 1000 ? `${(m / 1000).toFixed(1).replace('.', ',')} km` : `${fmtInt(m)} m`)
function RadarEnVente({ radar }: { radar: Estimer3Rapport['radar'] }) {
  if (!radar?.biens?.length) return null
  return (
    <section>
      <p className={SECTION_TITRE}>En vente en ce moment · Radar</p>
      <ul className="mt-1.5 flex flex-col gap-1">
        {radar.biens.map((b, i) => (
          <li key={i} className="flex items-start justify-between gap-2 rounded-md border border-line-2 bg-surface-3 px-2 py-1.5 text-[11px]">
            <div className="min-w-0 flex-1">
              <div className="text-txt">
                {[b.type, b.pieces != null ? `${b.pieces} p.` : null, b.surface_m2 != null ? fmtM2(b.surface_m2) : null].filter(Boolean).join(' · ')}
              </div>
              <div className="mt-0.5 flex flex-wrap gap-x-1.5 text-[10.5px] text-txt-dim">
                {b.commune && <span>{b.commune}</span>}
                {fmtDist(b.distance_m) && <span>· {fmtDist(b.distance_m)}</span>}
              </div>
            </div>
            <span className="shrink-0 tabular-nums text-txt-dim">{b.prix_affiche_eur != null ? `${fmtInt(b.prix_affiche_eur)} € affiché` : ''}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}

// ── La question UNIQUE : surface habitable (+ pièces pour l'appartement). Terrain nu : aucune. ──
function Question({ rapport, surfaceStr, onSurfaceChange, onSurfaceCommit, surfaceTouchee, pieces, onPieces }: {
  rapport: Estimer3Rapport
  surfaceStr: string; onSurfaceChange: (v: string) => void; onSurfaceCommit: () => void; surfaceTouchee: boolean
  pieces: number | null; onPieces: (n: number) => void
}) {
  const qSurface = rapport.questions.find((q) => q.cle === 'surface_hab')
  const qPieces = rapport.questions.find((q) => q.cle === 'pieces')
  if (!qSurface) return null
  const detail = rapport.estimation.surface_hab_detail
  const masque = !!rapport.estimation.total_masque
  // OUTILS-P0-2 (recette) — immeuble à plusieurs logements : champ vide, indication de la dernière vente
  // DE L'IMMEUBLE (un autre lot), et le badge « connue » est RÉSERVÉ au mono-logement.
  const multi = !!rapport.estimation.multi_logement
  const immeuble = rapport.estimation.immeuble_derniere_vente
  const estLabuse = rapport.mesures.surface_hab_estimee_m2
  // badge : « saisie » si l'utilisateur a entré la valeur ; sinon « connue » (vente DVF, mono-logement) /
  // « estimée » (calcul depuis le bâti). Total masqué ou immeuble multi-logements → champ VIDE, pas de badge.
  const badge: 'connue' | 'estimée' | 'saisie' | null =
    surfaceTouchee ? 'saisie' : ((masque || multi) ? null : (detail?.badge ?? 'estimée'))
  const texte = multi
    ? `${immeuble ? immeuble[0].toUpperCase() + immeuble.slice(1) + '. ' : ''}Un immeuble à plusieurs logements : saisissez la surface du bien à estimer.`
    : masque
    ? `LABUSE estime ${estLabuse != null ? `≈ ${estLabuse} m²` : 'la surface'}${detail?.texte ? ` — ${detail.texte}` : ''} Saisissez la surface réelle pour obtenir une valeur totale.`
    : (surfaceTouchee ? 'Votre surface. L’estimation s’appuie sur cette valeur.'
        : (detail?.texte ?? 'Surface habitable estimée depuis le bâti (LiDAR).'))
  return (
    <section className={SECTION}>
      <p className={SECTION_TITRE}>Surface habitable</p>
      <div className="mt-1.5 flex items-center gap-2">
        <input
          data-estimer-surface type="text" inputMode="numeric"
          className="h-10 w-24 rounded-md border border-line-2 bg-surface-3 px-2 text-[22px] font-semibold tabular-nums text-txt-hi placeholder:text-[13px] placeholder:font-normal placeholder:text-txt-mut focus:outline-none focus:border-mint/60"
          value={surfaceStr}
          placeholder={(masque || multi) ? 'à saisir' : ''}
          onChange={(e) => onSurfaceChange(e.target.value.replace(/[^\d]/g, ''))}
          onBlur={onSurfaceCommit}
          onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); (e.target as HTMLInputElement).blur() } }}
          aria-label="Surface habitable en m²" />
        <span className="text-[13px] text-txt-dim">m²</span>
        {badge && (
          <Badge ton={badge === 'estimée' ? 'neutre' : 'vert'} data-estimer-surface-badge>{badge}</Badge>
        )}
      </div>
      <p className="mt-1.5 text-[11px] leading-snug text-txt-mut">{texte}</p>
      {qPieces && (
        <div className="mt-3">
          <p className="text-[11px] text-txt-dim">Nombre de pièces</p>
          <div className="mt-1 flex flex-wrap gap-1">
            {(qPieces.options ?? [2, 3, 4, 5, '6+']).map((opt) => {
              const n = typeof opt === 'number' ? opt : 6
              const actif = pieces === n
              return (
                <button key={String(opt)} data-estimer-pieces onClick={() => onPieces(n)}
                  className={`rounded-md border px-2.5 py-1 text-[12px] tabular-nums transition-colors ${actif ? 'border-mint/50 bg-mint/15 text-txt-hi' : 'border-line-2 bg-surface-3 text-txt-dim hover:text-txt-hi'}`}>
                  {opt}
                </button>
              )
            })}
          </div>
        </div>
      )}
    </section>
  )
}

// ── L'écran complet dès qu'une parcelle est choisie (lit le point unique estimation3). La boîte
//    parcelle (EntreeParcelle) est rendue AU-DESSUS par le parent — ici, uniquement l'estimation. ──
function Estimer3({ idu }: { idu: string }) {
  // Saisie locale : la surface est COMMISE au blur/Entrée (pas à chaque frappe) ; pièces & décochages
  // s'appliquent tout de suite. La requête se re-joue sur (surface commise, pièces, ventes écartées).
  const [surfaceStr, setSurfaceStr] = useState('')
  const [surfaceCommit, setSurfaceCommit] = useState<number | null>(null)
  const [surfaceTouchee, setSurfaceTouchee] = useState(false)
  const [pieces, setPieces] = useState<number | null>(null)
  const [ecartees, setEcartees] = useState<Set<string>>(new Set())
  // la parcelle change → on repart de zéro (nouvelle estimation).
  useEffect(() => {
    setSurfaceStr(''); setSurfaceCommit(null); setSurfaceTouchee(false); setPieces(null); setEcartees(new Set())
  }, [idu])

  const ecartList = Array.from(ecartees).sort()
  const q = useQuery({
    queryKey: ['estimer3', idu, surfaceCommit, pieces, ecartList.join(',')],
    queryFn: () => getEstimation3(idu, { surface_hab: surfaceCommit, pieces, ecartees: ecartList }),
    placeholderData: (prev) => prev,
  })
  const r = q.data

  // OUTILS-P0-2 (recette) — immeuble à plusieurs logements : AUCUN préremplissage (la dernière vente est
  // un autre lot), le champ reste vide avec l'indication « dernière vente dans l'immeuble : N m² (AAAA) ».
  const multiLog = !!r?.estimation?.multi_logement
  const preSurface = multiLog ? null : (r?.questions.find((x) => x.cle === 'surface_hab')?.prerempli ?? r?.mesures.surface_hab_estimee_m2 ?? null)
  // Préremplissage UNE fois depuis la surface servie (DVF ou estimée) — SAUF quand le total est masqué
  // ou l'immeuble multi-logements : là le champ reste VIDE, on ne remplit pas.
  useEffect(() => {
    if (surfaceTouchee || surfaceStr) return
    if (r?.estimation?.total_masque || multiLog) return
    if (preSurface != null) setSurfaceStr(String(preSurface))
  }, [r, surfaceTouchee, surfaceStr, multiLog, preSurface])

  const commitSurface = () => {
    const n = surfaceStr.trim() ? Math.round(Number(surfaceStr)) : null
    const val = n != null && Number.isFinite(n) && n > 0 ? n : null
    setSurfaceCommit(val)
    setSurfaceTouchee(val != null && val !== preSurface)
  }
  const toggle = (id: string) => setEcartees((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n })

  if (q.isLoading) return <Chargement />
  if (q.isError || !r || r.erreur) {
    return <ErrorState message={r?.note ?? 'Impossible de charger l’estimation de cette parcelle.'} retry={() => q.refetch()} />
  }

  const terrain = r.type_bien === 'terrain'
  // Le PDF (route /analyse-annonce) partage le MÊME point : mêmes chiffres écran == document. OUTILS-P0-2
  // (P1) — on transmet le scénario EXACT affiché : surface + pièces saisies, ventes décochées (ecartees).
  const pdfUrl = docAnalyseAnnonceUrl(idu, surfaceCommit, { pieces, ecartees: ecartList })

  return (
    <>
      <DerniereVente dv={r.derniere_vente} />
      <Mesures m={r.mesures} typeBien={r.type_bien} />
      {!terrain && (
        <Question rapport={r} surfaceStr={surfaceStr}
          onSurfaceChange={(v) => { setSurfaceStr(v) }}
          onSurfaceCommit={commitSurface} surfaceTouchee={surfaceTouchee}
          pieces={pieces} onPieces={(n) => setPieces(n)} />
      )}
      <ValeurEstimee e={r.estimation} typeBien={r.type_bien} commune={r.commune} />
      <VentesRetenues ventes={r.ventes_retenues} ecartees={ecartees} onToggle={toggle} typeBien={r.type_bien} />
      <RadarEnVente radar={r.radar} />
      <p className="text-[11px] leading-snug text-txt-mut">
        LABUSE ne connaît ni l’état du bien ni sa vue : ce prix est un repère de marché, pas une expertise.
      </p>
      <ExportPdf url={pdfUrl} />
    </>
  )
}

// ════════════════════════════════════════ RAPPORT ANNONCE (lien) ════════════════════════════════════════
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

// ══════════════════════════════════════════ ÉCRAN ESTIMER ══════════════════════════════════════════
export function AnalyserAnnonce() {
  const toggleOutils = useApp((s) => s.toggleOutils)
  const focusParcelle = useApp((s) => s.focusParcelle)
  const setModuleMap = useApp((s) => s.setModuleMap)
  const setFlyTo = useApp((s) => s.setFlyTo)
  const selectedIdu = useApp((s) => s.selectedIdu)

  const [etape, setEtape] = useState<Etape>('entree')
  const [parcelle, setParcelle] = useState<string | null>(null)
  const [source, setSource] = useState<SourceParcelle>(null)
  const [res, setRes] = useState<AnnonceAnalyse | null>(null)
  const [erreur, setErreur] = useState<string | null>(null)

  // `source` (adresse | carte) grise l'autre entrée dans EntreeParcelle ; l'écran reste identique
  // quelle que soit la provenance (la boîte option A s'affiche dans les deux cas).
  const choisir = (idu: string, src: 'adresse' | 'carte') => { setParcelle(idu); setSource(src); setEtape('parcelle') }

  // Clic carte : la parcelle sélectionnée est ADOPTÉE (source carte) tant qu'on est sur l'écran d'entrée
  // ou déjà en mode parcelle — même idiome que les autres outils (selectedIdu suivi en continu).
  const lastSelected = useRef<string | null>(null)
  useEffect(() => {
    if (selectedIdu && selectedIdu !== lastSelected.current && etape !== 'annonce' && !parcelle) {
      choisir(selectedIdu, 'carte')
    }
    lastSelected.current = selectedIdu
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedIdu])

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

  // Pont Radar « Ce bien » → rapport COMMUNE (lien) ; pont fiche « Estimer » → écran PARCELLE.
  const annonceLienPrefill = useApp((s) => s.annonceLienPrefill)
  const setAnnonceLienPrefill = useApp((s) => s.setAnnonceLienPrefill)
  const annonceParcellePrefill = useApp((s) => s.annonceParcellePrefill)
  const setAnnonceParcellePrefill = useApp((s) => s.setAnnonceParcellePrefill)
  useEffect(() => {
    if (annonceParcellePrefill) {
      choisir(annonceParcellePrefill, 'adresse')
      setAnnonceParcellePrefill(null)
      return
    }
    if (!annonceLienPrefill) return
    analyse.mutate(annonceLienPrefill)
    setAnnonceLienPrefill(null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Carte : parcelle zoomée+surlignée (parcelle) · commune centrée (lien) · rien (entrée).
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

  const changerParcelle = () => { setParcelle(null); setSource(null); setEtape('entree') }

  // ── Rapport annonce (lien, depuis le Radar) — inchangé ──
  if (etape === 'annonce' && res?.annonce) {
    const a = res.annonce
    const titre = `${a.type ? a.type[0].toUpperCase() + a.type.slice(1) : 'Annonce'}${a.pieces != null ? ` ${a.pieces} pièces` : ''}${a.commune ? ` · ${a.commune}` : ''}`
    const d = a.releve_le ? a.releve_le.split('-').reverse().join('/') : null
    return (
      <>
        <Entete retour={{ label: 'Retour', onClick: () => { setRes(null); setEtape('entree') } }}
          titre={titre} sous={`Annonce Leboncoin${d ? ` · relevée le ${d}` : ''}`} />
        <RapportAnnonce res={res} />
      </>
    )
  }

  // ── Écran ESTIMER (maquette validée) : un seul écran, la boîte parcelle puis tout dessous ──
  return (
    <>
      <Entete retour={{ label: 'Retour', onClick: toggleOutils }}
        titre="Estimer un bien"
        sous="Une adresse ou une parcelle : LABUSE part des ventes réelles de biens semblables." />
      <Corps>
        {/* Boîte parcelle COMMUNE (EntreeParcelle, option A) : champ de recherche tant qu'aucune parcelle,
            puis boîte remplie (adresse + IDU · zone · surface + ✕) à l'affichage instantané. Pas de libellé
            au-dessus : le sous-titre de l'en-tête le dit déjà. */}
        <EntreeParcelle source={source} picked={parcelle} onPick={choisir} onChanger={changerParcelle} />
        {parcelle ? (
          <Estimer3 idu={parcelle} />
        ) : (
          erreur && <p role="alert" className="rounded-md border border-coral/40 bg-surface-3 px-3 py-2 text-[12px] leading-snug text-coral">{erreur}</p>
        )}
      </Corps>
    </>
  )
}

export default AnalyserAnnonce
