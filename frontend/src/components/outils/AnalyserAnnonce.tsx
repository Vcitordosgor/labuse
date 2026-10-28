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
import { analyserAnnonce, docAnalyseAnnonceLienUrl, docAnalyseAnnonceUrl, getAnnonceClassement, getAnnonceEstimation, getContexteCommune, getFiche, getParcelExposition, type AnnonceAnalyse } from '../../lib/api'
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
function fiab(f?: string | null, communeFallback?: boolean): { mot: string; ton: 'vert' | 'ambre' } {
  if (communeFallback) return { mot: 'Limitée', ton: 'ambre' }
  if (f === 'fiable') return { mot: 'Élevée', ton: 'vert' }
  return { mot: 'Moyenne', ton: 'ambre' }
}

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
  // Classement LABUSE = la BANDE du run SERVI + le vocabulaire client gravé (back, score_labuse.yaml) —
  // JAMAIS `score_v2.verbal.mot` (c'est le phrasé de percentile du Signal, d'où l'ancien « proche de la moyenne »).
  const cls = useQuery({ queryKey: ['annonce-classement', idu], queryFn: () => getAnnonceClassement(idu) })
  // ANNONCE-3-FIX — l'estimation selon la nature (nue → terrain nu ; bâtie → bâti), servie par le MÊME
  // point que le PDF (/radar/annonce/estimation) → mêmes chiffres à l'écran et dans le document.
  const estim = useQuery({ queryKey: ['annonce-estim', idu], queryFn: () => getAnnonceEstimation(idu) })

  if (fiche.isLoading) return <Corps><Chargement /></Corps>
  if (fiche.isError || !fiche.data) return <Corps><ErrorState message="Impossible de charger la fiche parcelle." retry={() => fiche.refetch()} /></Corps>
  const f = fiche.data
  const zone = f.reglement_plu?.zones?.[0]?.zone ?? null
  const pot = f.potentiel_transformation
  const sdp = pot?.sdp_residuelle_m2
  const classement = cls.data?.bande
    ? (cls.data.libelle && cls.data.libelle !== cls.data.bande ? `${cls.data.bande} · ${cls.data.libelle}` : cls.data.bande)
    : (cls.isLoading ? '…' : '—')
  const nAleas = f.aleas?.n ?? 0
  const orientation = expo.data?.orientation ?? null

  const tuiles: { k: string; v: string }[] = [
    { k: 'Surface', v: fmtM2(f.surface_m2) },
    { k: 'Zone PLU', v: zone ?? '—' },
    { k: 'SDP restante', v: sdp == null ? '—' : fmtM2(Math.round(sdp)) },
    { k: 'Classement LABUSE', v: classement ?? '—' },
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
  const fi = fiab(e?.fiabilite, e?.commune_fallback)

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
                <>Parcelle nue — comparée aux ventes de <strong className="text-txt-hi">terrain nu</strong> (repère €/m² de terrain).</>
              ) : (
                <>Parcelle bâtie — comparée au <strong className="text-txt-hi">bâti ancien</strong> (prix observés au m²{e?.type_prix ? `, ${e.type_prix}` : ''}) autour de la parcelle.{e?.commune_fallback ? ' Repère élargi à la commune (secteur trop peu fourni).' : ''} La valeur d’un bien dépend de sa surface et de son état, non connus du modèle.</>
              )}
            </p>
          </>
        )}
      </section>

      <section className={SECTION}>
        <h3 className="text-sm font-medium text-txt-hi">Le foncier</h3>
        <p className="mt-1 text-[12px] leading-snug text-txt-dim">
          {zone ? <>Zone <strong className="text-txt-hi">{zone}</strong>. </> : null}
          {pot?.hauteur_regle_m != null ? `Hauteur réglementaire ${fmtInt(Math.round(pot.hauteur_regle_m))} m. ` : ''}
          {sdp != null
            ? <>SDP restante estimée : <strong className="text-txt-hi">{fmtM2(Math.round(sdp))}</strong>{pot?.estimation_simplifiee ? ' (estimation simplifiée)' : ''}.</>
            : (pot?.libelle ?? 'Potentiel non calculé pour cette parcelle.')}
        </p>
        <Bouton niveau="lien" ton="vert" className="mt-2"
          onClick={() => focusParcelle(idu, { fiche: true })}>Ouvrir la fiche parcelle →</Bouton>
      </section>

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
  const m = res.marche
  const commune = a.commune ?? ''
  const ctx = useQuery({ queryKey: ['annonce-commune', commune], queryFn: () => getContexteCommune(commune), enabled: !!commune })

  // ANNONCE-1-FIX (pt 3) — « non précisé dans l'annonce » est RÉSERVÉ aux champs ATTENDUS pour ce type
  // et absents. Un champ non applicable au type (ex. Pièces sur un terrain) n'apparaît PAS du tout.
  const NP = 'non précisé dans l’annonce'
  const cap = (s: string | null | undefined) => (s ? s[0].toUpperCase() + s.slice(1) : null)
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

  // « La commune » : repère de prix par type (du moteur de prix, via `marche`) + PLU + aléas (contexte).
  const c = ctx.data
  const aleas: string[] = []
  if (c?.risques) {
    if ((c.risques.ppr_pct ?? 0) > 0 || (c.risques.azi_tri?.azi?.length ?? 0) > 0 || (c.risques.azi_tri?.tri?.length ?? 0) > 0) aleas.push('inondation')
    if ((c.risques.mouvement_terrain_pct ?? 0) > 0) aleas.push('mouvement de terrain')
    if (c.risques.parc_national) aleas.push('parc national')
  }
  const pluTxt = c?.plu_statut?.statut ?? c?.plu_statut?.libelle ?? '—'

  return (
    <Corps>
      <section className={SECTION}>
        <h3 className="text-sm font-medium text-txt-hi">Ce que dit l’annonce</h3>
        <div className="mt-2">{pairs(rows)}</div>
        <p className="mt-2 text-[11px] leading-snug text-txt-mut">Seules les informations présentes dans l’annonce sont affichées.</p>
      </section>

      <section className={SECTION}>
        <h3 className="text-sm font-medium text-txt-hi">Prix face au marché</h3>
        {m && m.calculable && m.ecart_libelle ? (
          <>
            <p className="mt-1 text-xl font-semibold leading-none text-txt-hi">{m.ecart_libelle}</p>
            <p className="mt-0.5 text-[12px] text-txt-dim">
              face au repère commune {m.repere_perimetre ?? m.perimetre ?? 'du bon type'}
              {m.referentiel_eur_m2 != null ? ` : ${fmtInt(m.referentiel_eur_m2)} €/m²` : ''}
            </p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <span className="text-[11px] text-txt-dim">Fiabilité</span>
              <Badge ton="ambre" point>Limitée</Badge>
              <span className="text-[11px] text-txt-dim">repère à l’échelle de la commune</span>
            </div>
          </>
        ) : (
          <p className="mt-1 text-[12px] text-txt-dim">
            {m?.motif ?? 'Comparaison au marché indisponible (prix ou surface absents de l’annonce, ou échantillon DVF insuffisant).'}
          </p>
        )}
        <p className="mt-2 text-[11px] leading-snug text-txt-mut">
          L’annonce ne donne pas d’adresse précise : le repère est large. Localisez la parcelle pour une
          estimation au micro-marché et l’analyse foncière.
        </p>
      </section>

      <section className={SECTION}>
        <h3 className="text-sm font-medium text-txt-hi">La commune{commune ? ` · ${commune}` : ''}</h3>
        <div className="mt-2">
          {pairs([
            { k: `Ventes ${m?.repere_perimetre ?? 'comparables'}`, v: m?.n_referentiel != null ? `${fmtInt(m.n_referentiel)}${m.periode ? ` · ${m.periode}` : ''}` : '—' },
            { k: 'Prix médian (DVF)', v: m?.referentiel_eur_m2 != null ? `${fmtInt(m.referentiel_eur_m2)} €/m²` : '—' },
            { k: 'PLU', v: pluTxt },
            { k: 'Aléas principaux', v: aleas.length ? aleas.join(', ') : (ctx.isLoading ? '…' : '—') },
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
      <Entete retour={{ label: 'Outils', onClick: toggleOutils }}
        titre="Analyser une annonce"
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
