// RADAR-CATÉGORIE (T1/T2/T3) — LA CATÉGORIE RADAR, plein écran : rail · panneau listing (434px) ·
// carte. Fidèle à la maquette docs/PIGE/maquette-radar-v2.html (écrans 1, 2, 3).
// LIGNE ROUGE (doctrine §2) : des FAITS et un LIEN, jamais le titre/texte/photo de l'annonce. Le
// mauve est réservé à l'IA — il n'apparaît nulle part ici. Couleurs = source unique (mint/amber tokens).
// Le back (pige/client.py) est réutilisé tel quel — aucune requête portail côté code (collecte 100 % humaine).
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { lazy, Suspense, useEffect, useMemo, useState } from 'react'
import { getRadarBienDetail, getRadarBiens, radarClic, radarInstruire, radarRattacherHumain, radarSignaler,
  type RadarBienClient, type RadarCritere, type RadarFiltres, type RadarPiste } from '../../lib/api'
import { CP_COMMUNES } from '../panel/FiltreLabuse'   // R2 — source unique des 24 communes
import { useApp } from '../../store/useApp'

// T6 — la carte est montée par RadarView (pour piloter le responsive) ; lazy comme dans App.
const MapView = lazy(() => import('../map/MapView').then((m) => ({ default: m.MapView })))

// T6 — mobile ≤ 767px : une seule vue à la fois (listing / carte / fiche, plein écran).
function useIsMobile(): boolean {
  const [m, setM] = useState(() => typeof window !== 'undefined' && window.matchMedia('(max-width: 767px)').matches)
  useEffect(() => {
    const mq = window.matchMedia('(max-width: 767px)')
    const on = () => setM(mq.matches)
    mq.addEventListener('change', on)
    return () => mq.removeEventListener('change', on)
  }, [])
  return m
}

const COMMUNES_24 = CP_COMMUNES.map(([, nom]) => nom).sort((a, b) => a.localeCompare(b, 'fr'))
const TYPES = [['', 'Tous types'], ['maison', 'Maison'], ['appartement', 'Appartement'], ['terrain', 'Terrain'], ['immeuble', 'Immeuble']] as const
const TRIS = [['recentes', 'Plus récentes'], ['prix_asc', 'Prix croissant'], ['prix_desc', 'Prix décroissant'], ['anciennete', 'Ancienneté'], ['baisses', 'Baisses']] as const
const STATUT_LABEL: Record<string, string> = {
  active: 'EN VENTE', en_vente_longue: 'EN VENTE LONGUE', a_reverifier: 'À REVÉRIFIER',
  retiree: 'RETIRÉE', vendue: 'VENDUE', retiree_sans_vente: 'RETIRÉE',
}
const ET_LABEL: Record<string, string> = { source: 'SOURCÉ', estime: 'ESTIMÉ', absent: 'ABSENT' }
const fmtEur = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('fr-FR') + ' €')
const fmtDate = (iso: string | null) => (iso ? new Intl.DateTimeFormat('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric', timeZone: 'Indian/Reunion' }).format(new Date(iso)) : '—')

// ancienneté en jours (publication si connue, sinon saisie) — le pied de carte de la maquette
function joursDepuis(iso: string | null): number | null {
  if (!iso) return null
  const d = new Date(iso).getTime()
  if (Number.isNaN(d)) return null
  return Math.max(0, Math.floor((Date.now() - d) / 86_400_000))
}

// specs d'un bien selon son type — le corps de la carte de la maquette (« 620 m² de terrain », etc.)
function specsBien(b: RadarBienClient): string {
  const p: string[] = []
  if (b.faits.pieces) p.push(`${b.faits.pieces} pièces`)
  if (b.faits.surface_hab) p.push(`${b.faits.surface_hab} m² hab`)
  if (b.faits.surface_terrain) p.push(`${b.faits.surface_terrain} m² de terrain`)
  if (!b.faits.surface_hab && !b.faits.surface_terrain && b.faits.dpe_classe) p.push(`DPE ${b.faits.dpe_classe}`)
  else if (p.length && b.faits.dpe_classe && !b.faits.surface_terrain) p.push(`DPE ${b.faits.dpe_classe}`)
  return p.join(' · ') || '—'
}

// ════════════ carte d'un bien dans le listing (structure verrouillée de la maquette) ════════════
function CarteBien({ b, sel, onClick }: { b: RadarBienClient; sel: boolean; onClick: () => void }) {
  const ratt = b.rattachement.idu != null
  const j = joursDepuis(b.date_publication || b.date_saisie)
  const meta = [b.faits.particulier_pro === 'pro' ? 'Pro' : b.faits.particulier_pro === 'particulier' ? 'Particulier' : b.portail,
    j != null ? `${j} j` : null].filter(Boolean).join(' · ')
  return (
    <button data-radar-bien={b.bien_id} onClick={onClick}
      className={`relative grid grid-cols-[minmax(0,1fr)_auto] gap-x-3 rounded-xl border px-4 py-3 text-left transition-colors duration-quick ${
        sel ? 'border-mint/40 bg-mint/[0.06]' : 'border-line-2 bg-surface-2 hover:border-line-3'}`}>
      {sel && <span aria-hidden className="absolute -left-px bottom-2.5 top-2.5 w-[3px] rounded bg-mint" />}
      <div className="self-center truncate font-mono text-[11px] tracking-[0.05em]">
        <span className="font-bold text-mint">{(b.type_bien ?? '—').toUpperCase()}</span>
        <span className="text-txt-mut"> · {b.commune}</span>
      </div>
      <div className="self-center whitespace-nowrap text-right text-[16.5px] font-bold tabular-nums text-txt-hi">{fmtEur(b.faits.prix)}</div>
      <div className="col-span-2 mt-1.5 text-[12.5px] leading-snug text-txt-mut">{specsBien(b)}</div>
      <div className="col-span-2 mt-2.5 flex items-center gap-2 overflow-hidden">
        {ratt ? (
          <span className="flex shrink-0 items-center gap-1.5 rounded-full bg-mint/12 px-2.5 py-1 text-[11px] text-mint">
            <span className="h-1.5 w-1.5 rounded-full bg-mint" />Sur la carte
          </span>
        ) : (
          <span className="shrink-0 rounded-full border border-dashed border-line-3 px-2.5 py-1 text-[11px] text-txt-mut">Non localisé — voir l'annonce ↗</span>
        )}
        {b.baisse && <span className="shrink-0 rounded-md bg-mint/12 px-2 py-0.5 font-mono text-[10.5px] text-mint">baisse</span>}
        {b.statut === 'en_vente_longue' && <span className="shrink-0 rounded-md bg-amber/12 px-2 py-0.5 font-mono text-[10.5px] text-amber">Vente longue</span>}
        {/* RADAR-RECETTE-1 D1c — un bien incohérent est MARQUÉ dans le flux (hors stats/veilles, non rattaché). */}
        {b.a_qualifier && <span className="shrink-0 rounded-md bg-st-ecartee/15 px-2 py-0.5 font-mono text-[10.5px] text-st-ecartee">à qualifier</span>}
        <span className="ml-auto min-w-0 truncate text-right text-[11px] text-txt-dim">{meta}</span>
      </div>
    </button>
  )
}

// ════════════ tuile « Étudier ce bien » (T3, écran 2) ════════════
function Tuile({ label, onClick, children }: { label: string; onClick: () => void; children: React.ReactNode }) {
  return (
    <button data-radar-tuile={label} onClick={onClick}
      className="flex items-center gap-2 overflow-hidden rounded-lg border border-line-2 bg-surface-2 px-2.5 py-2 text-left text-[11.5px] text-txt transition-colors duration-quick hover:border-mint/40">
      <span className="shrink-0 text-mint">{children}</span>
      <span className="truncate">{label}</span>
    </button>
  )
}

// ════════════ la fiche d'un bien — overlay flottant sur la carte (maquette écran 2) ════════════
// T6 — desktop : overlay 398px à droite. mobile : plein écran (inset-0).
function RadarFiche({ bienId, onClose, mobile }: { bienId: number; onClose: () => void; mobile?: boolean }) {
  const qc = useQueryClient()
  const { data: b, isError } = useQuery({ queryKey: ['radar-bien', bienId], queryFn: () => getRadarBienDetail(bienId) })
  const [signale, setSignale] = useState(false)
  // RADAR-HTML (Lot 3) + V2 (Lot 2) — « Instruire » : candidates enrichies (ortho + critères) ; le
  // client tranche via l'ortho (rattachement humain, fait foi).
  const [instr, setInstr] = useState<{ busy: boolean; cands?: RadarPiste[]; motif?: string | null }>({ busy: false })
  const [choix, setChoix] = useState<{ busy: boolean; idu?: string }>({ busy: false })
  const st = useApp.getState
  const cadre = mobile
    ? 'absolute inset-0 z-40 flex flex-col overflow-hidden border-line-2 bg-surface-1'
    : 'absolute bottom-3.5 right-3.5 top-3.5 z-30 flex w-[398px] flex-col overflow-hidden rounded-2xl border border-line-2 bg-surface-1/97 shadow-elev-3'
  if (isError) return (
    <div className={`${cadre} p-4 text-[12px] text-txt-mut`}>
      Fiche indisponible — le serveur n’a pas répondu. <button onClick={onClose} className="text-mint hover:underline">fermer</button>
    </div>
  )
  if (!b || !b.bien_id) return (
    <div className={`${cadre} p-4 text-[12px] text-txt-dim`}>Chargement…</div>
  )
  const ratt = b.rattachement.niveau !== 'absent' && b.rattachement.idu != null
  const idu = b.rattachement.idu

  // les FAITS, étiquetés (Sourcé/Estimé/Absent) — l'étiquette suit le champ (b.etiquettes)
  const faits: [string, string, string | null][] = [
    ['Surface terrain', b.faits.surface_terrain ? `${b.faits.surface_terrain} m²` : '—', b.etiquettes.surface_terrain ?? null],
    ['Surface habitable', b.faits.surface_hab ? `${b.faits.surface_hab} m²` : '—', b.etiquettes.surface_hab ?? null],
    ['Pièces', b.faits.pieces?.toString() ?? '—', b.etiquettes.pieces ?? null],
    ['DPE', b.faits.dpe_classe ?? '—', b.etiquettes.dpe_classe ?? null],
    ['Vendeur', b.faits.particulier_pro ? (b.faits.particulier_pro === 'pro' ? 'Professionnel' : 'Particulier') : '—', b.etiquettes.particulier_pro ?? null],
    ['Parution', fmtDate(b.date_publication), b.date_publication ? 'source' : 'absent'],
  ]

  // mention de baisse + prix de parution (1er ancien connu) — sans invention
  const prixParution = b.historique_prix.length ? b.historique_prix[0].ancien : null
  const derniereBaisse = [...b.historique_prix].reverse().find((h) => (h.nouveau ?? 0) < (h.ancien ?? 0))
  // sparkline des prix (si ≥ 2 points) — polyline simple, jamais une fausse précision
  const spark = (() => {
    const pts = b.historique_prix.flatMap((h) => [h.ancien, h.nouveau]).filter((v): v is number => v != null)
    if (pts.length < 2) return null
    const min = Math.min(...pts), max = Math.max(...pts), span = max - min || 1
    const coords = pts.map((v, i) => `${4 + (i / (pts.length - 1)) * 104},${31 - ((v - min) / span) * 26}`).join(' ')
    return coords
  })()

  const ouvrirPortail = () => { radarClic(b.bien_id, b.annonce_id).catch(() => {}); window.open(b.url_sortante, '_blank', 'noopener,noreferrer') }
  // les 6 tuiles → l'outil réel, pré-rempli avec la parcelle rattachée (mappings vérifiés, cf. rapport)
  const outil = (fn: () => void) => { if (idu) fn() }
  const tuiles = idu ? [
    { label: 'Étudier le bien', ico: <IcoEtude />, go: () => { const s = st(); s.setCalcPrefill(idu); s.setModule('scoreur-adresse') } },
    { label: 'Remonter le temps', ico: <IcoTemps />, go: () => { const s = st(); if (b.coords) s.setFlyTo({ center: b.coords as [number, number], zoom: 16 }); s.setParcelPrefill(idu); s.setModule('temps') } },
    { label: 'Calculette foncière', ico: <IcoCalc />, go: () => { const s = st(); s.setCalcPrefill(idu); s.setModule('calculette-fonciere') } },
    { label: 'Taxe d\'aménagement', ico: <IcoTaxe />, go: () => { const s = st(); s.select(idu); s.setModule('taxe-amenagement') } },
    { label: 'Pièges & risques', ico: <IcoRisque />, go: () => { const s = st(); s.select(idu); s.setModule('risques') } },
    { label: 'Solaire', ico: <IcoSoleil />, go: () => { const s = st(); s.setSolairePrefill(idu); s.setModule('prospection-solaire') } },
  ] : []

  return (
    <div data-radar-fiche className={cadre}>
      <div className="shrink-0 border-b border-line-2 px-4 py-3">
        <div className="flex items-center justify-between font-mono text-[10.5px] tracking-[0.2em] text-txt-mut">
          <span>RADAR › BIEN</span>
          <button onClick={onClose} aria-label="Fermer" className="tracking-normal text-txt-dim hover:text-txt">✕</button>
        </div>
        <h4 className="mt-1.5 flex items-center gap-2 text-[17px] font-semibold text-txt-hi">
          <span className="truncate">{(b.type_bien ?? 'Bien')[0].toUpperCase()}{(b.type_bien ?? '').slice(1)} · {b.commune}</span>
          <span className="shrink-0 rounded-md bg-mint/12 px-2 py-0.5 font-mono text-[10px] tracking-wide text-mint">{STATUT_LABEL[b.statut] ?? b.statut}</span>
        </h4>
      </div>
      <div className="flex min-h-0 flex-1 flex-col gap-3.5 overflow-y-auto px-4 py-3.5">
        {/* 2. prix + baisse + sparkline */}
        <div className="grid grid-cols-[1fr_auto] items-end gap-x-3">
          <div className="text-[25px] font-bold tabular-nums text-txt-hi">{fmtEur(b.faits.prix)}
            {b.baisse && derniereBaisse && (
              <span className="mt-1 block text-[11.5px] font-normal leading-snug text-txt-mut">
                Baisse du {fmtDate(derniereBaisse.date)}{prixParution ? ` — affiché ${fmtEur(prixParution)} à la parution` : ''}
              </span>
            )}
          </div>
          {spark && (
            <svg viewBox="0 0 112 36" className="h-9 w-28"><polyline points={spark} fill="none" stroke="#4ADE80" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
          )}
        </div>
        {/* 3. Voir l'annonce — juste sous le prix, visible sans scroller */}
        <a onClick={(e) => { e.preventDefault(); ouvrirPortail() }} href={b.url_sortante} target="_blank" rel="noopener noreferrer"
          data-radar-portail className="flex items-center justify-center gap-2 rounded-xl bg-mint py-3 text-[13.5px] font-semibold text-mint-on hover:brightness-110">
          Voir l’annonce sur {b.portail} ↗
        </a>
        {/* RADAR-RECETTE-1 D1c — bien À QUALIFIER : champs contradictoires. Visible mais marqué, motifs
            consultables ; hors statistiques, hors veilles, jamais rattaché (surface suspecte). */}
        {b.a_qualifier && (
          <div data-radar-aqualifier className="rounded-xl border border-st-ecartee/40 bg-st-ecartee/[0.06] px-3 py-2.5">
            <div className="mb-1 font-mono text-[10px] tracking-[0.2em] text-st-ecartee">À QUALIFIER — INCOHÉRENCE</div>
            <p className="mb-1.5 text-[11px] leading-snug text-txt-mut">
              Les champs de cette annonce se contredisent. Elle est écartée des statistiques, des veilles
              et du rattachement tant qu’elle n’est pas vérifiée.
            </p>
            <ul className="list-disc pl-4 text-[11px] leading-snug text-txt">
              {b.a_qualifier_motifs.map((m, i) => <li key={i}>{m}</li>)}
            </ul>
          </div>
        )}
        {/* 4. LES FAITS */}
        <div>
          <div className="mb-1.5 font-mono text-[10px] tracking-[0.2em] text-txt-mut">LES FAITS</div>
          <div className="overflow-hidden rounded-xl border border-line-2">
            {faits.map(([k, v, et], i) => (
              <div key={k} className={`grid grid-cols-[1fr_auto_auto] items-center gap-x-2.5 px-3 py-2 text-[12.5px] ${i ? 'border-t border-line-2' : ''}`}>
                <span className="text-txt-mut">{k}</span>
                <span className="whitespace-nowrap tabular-nums text-txt">{v}</span>
                <span className={`rounded font-mono text-[9px] tracking-[0.06em] px-1.5 py-0.5 ${et === 'source' ? 'bg-mint/12 text-mint' : et === 'estime' ? 'bg-amber/12 text-amber' : 'bg-surface-3 text-txt-dim'}`}>{ET_LABEL[et ?? 'absent'] ?? 'ABSENT'}</span>
              </div>
            ))}
          </div>
        </div>
        {/* 5 + 6 : réservés aux biens RATTACHÉS (pas de parcelle → pas d'outils) */}
        {ratt && idu && (
          <>
            <div>
              <div className="mb-1.5 flex items-center gap-2 font-mono text-[10px] tracking-[0.2em] text-txt-mut">
                PARCELLE RATTACHÉE
                {b.rattachement_humain && <span className="rounded bg-mint/15 px-1.5 py-0.5 tracking-normal text-mint">tranché à la main</span>}
              </div>
              <div className="grid grid-cols-[1fr_auto] items-center gap-x-2.5 rounded-xl border border-mint/30 bg-mint/[0.05] px-3 py-2.5">
                <span className="font-mono text-[12.5px] text-mint">{idu}</span>
                <button data-radar-parcelle onClick={() => { const s = st(); if (b.coords) s.setFlyTo({ center: b.coords as [number, number], zoom: 17 }); s.setView('cartes'); s.select(idu) }}
                  className="whitespace-nowrap rounded-lg border border-line-2 px-2.5 py-1.5 text-[11.5px] text-txt-mut hover:text-txt">Ouvrir la fiche parcelle →</button>
              </div>
              {/* RATTACHEMENT-V2 — POURQUOI cette parcelle tient : les critères indépendants qui ont convergé. */}
              {b.rattachement_criteres && b.rattachement_criteres.length > 0 && (
                <ul className="mt-1.5 flex flex-col gap-0.5 text-[10.5px] leading-snug text-txt-dim">
                  {b.rattachement_criteres.map((c: RadarCritere, i: number) => (
                    <li key={i}>✓ <span className="text-txt-mut">{c.critere}</span> — {c.valeur}</li>
                  ))}
                </ul>
              )}
            </div>
            <div>
              <div className="mb-1.5 font-mono text-[10px] tracking-[0.2em] text-txt-mut">ÉTUDIER CE BIEN</div>
              <div className="grid grid-cols-2 gap-1.5">
                {tuiles.map((t) => <Tuile key={t.label} label={t.label} onClick={() => outil(t.go)}>{t.ico}</Tuile>)}
              </div>
            </div>
          </>
        )}
        {/* PISTE (Lot 3) — plusieurs candidates possibles : à instruire À LA DEMANDE. Aucun automatisme
            n'en part (ni courrier, ni « vendue »). Geste client explicite. */}
        {!ratt && b.rattachement_etat === 'piste' && (
          <div className="rounded-xl border border-amber/30 bg-amber/[0.05] px-3 py-2.5">
            <div className="mb-1 font-mono text-[10px] tracking-[0.2em] text-amber">PISTE — À INSTRUIRE{b.pistes?.length ? ` · ${b.pistes.length} candidate${b.pistes.length > 1 ? 's' : ''}` : ''}</div>
            <p className="mb-2 text-[11px] leading-snug text-txt-mut">
              Plusieurs parcelles peuvent correspondre. Aucune n’est retenue par défaut : rien ne part
              d’une piste tant qu’elle n’est pas confirmée.
            </p>
            <button data-radar-instruire disabled={instr.busy}
              onClick={() => { setInstr({ busy: true }); radarInstruire(b.bien_id)
                .then((r) => setInstr({ busy: false, cands: r.candidates, motif: r.motif }))
                .catch(() => setInstr({ busy: false, motif: 'échec — réessayer' })) }}
              className="rounded-lg border border-amber/50 bg-amber/10 px-2.5 py-1.5 text-[11.5px] font-medium text-amber hover:bg-amber/20 disabled:opacity-60">
              {instr.busy ? 'Instruction…' : 'Instruire cette annonce'}
            </button>
            {instr.cands && (
              <div className="mt-2.5 flex flex-col gap-2">
                {instr.cands.length === 0 && <span className="text-[11px] text-txt-dim">{instr.motif || 'aucune candidate exploitable'}</span>}
                {/* RATTACHEMENT-V2 (Lot 2) — chaque candidate : sa VUE ORTHO + ses critères (✓ convergent /
                    ✗ divergent). Le client compare les toits avec les photos de l'annonce et tranche. */}
                {instr.cands.map((c) => (
                  <div key={c.idu} data-radar-candidate className="overflow-hidden rounded-xl border border-line-2 bg-surface-2">
                    <div className="grid grid-cols-[96px_1fr]">
                      {c.ortho_url
                        ? <img src={c.ortho_url} alt={`ortho ${c.idu}`} className="h-24 w-24 object-cover" loading="lazy" />
                        : <div className="flex h-24 w-24 items-center justify-center bg-surface-3 text-[9px] text-txt-dim">ortho indispo.</div>}
                      <div className="min-w-0 px-2.5 py-2">
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-[11px] text-txt">{c.idu}</span>
                          <span className="text-[10px] text-txt-dim">{c.distance_m != null ? `${Math.round(c.distance_m)} m` : ''}</span>
                        </div>
                        <ul className="mt-1 flex flex-col gap-0.5 text-[10px] leading-snug">
                          {(c.criteres_detail ?? []).map((x: RadarCritere, i: number) => (
                            <li key={i} className={x.converge ? 'text-mint' : 'text-txt-dim'}>
                              {x.converge ? '✓' : '✗'} <span className="text-txt-mut">{x.critere}</span> {x.valeur}
                            </li>
                          ))}
                        </ul>
                        <button data-radar-choisir disabled={choix.busy}
                          onClick={() => { setChoix({ busy: true, idu: c.idu }); radarRattacherHumain(b.bien_id, c.idu)
                            .then(() => { setChoix({ busy: false }); qc.invalidateQueries({ queryKey: ['radar-bien', bienId] }); qc.invalidateQueries({ queryKey: ['radar-biens'] }) })
                            .catch(() => setChoix({ busy: false })) }}
                          className="mt-1.5 rounded-md border border-mint/50 bg-mint/10 px-2 py-1 text-[10.5px] font-medium text-mint hover:bg-mint/20 disabled:opacity-60">
                          {choix.busy && choix.idu === c.idu ? 'Enregistrement…' : "C'est cette parcelle"}
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
        {!ratt && b.rattachement_etat !== 'piste' && (
          <p className="text-[11px] leading-snug text-txt-dim">Bien non rattaché à une parcelle — la position servie est le quartier ; seul le lien vers la source est disponible.</p>
        )}
        {/* 7. Signaler + note de doctrine */}
        <div className="flex flex-col gap-2 pt-0.5">
          <button disabled={signale} onClick={() => radarSignaler(bienId, 'annonce retirée / erreur').then(() => setSignale(true))}
            className="text-center text-[11.5px] text-txt-mut underline decoration-dotted hover:text-txt disabled:opacity-60">
            {signale ? 'Signalé — merci, Victor va vérifier' : 'Signaler — annonce retirée ou erreur'}
          </button>
          <p className="text-center text-[10px] leading-relaxed text-txt-dim">Faits extraits de l’annonce publique. Aucune photo ni texte d’annonce n’est conservé ou affiché.</p>
        </div>
      </div>
    </div>
  )
}

// petites icônes des tuiles (trait mint, viewBox 24)
const IcoEtude = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M2 3h20v14H2z" /><path d="M8 21h8M12 17v4" /></svg>
const IcoTemps = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 3" /></svg>
const IcoCalc = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="4" y="2" width="16" height="20" rx="2" /><path d="M8 6h8M8 10h2M14 10h2M8 14h2M14 14h2" /></svg>
const IcoTaxe = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2 2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" /></svg>
const IcoRisque = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" /><path d="M12 9v4M12 17h.01" /></svg>
const IcoSoleil = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></svg>

// ════════════ LA CATÉGORIE — panneau (434px) + fiche overlay ════════════
export function RadarView() {
  const [f, setF] = useState<RadarFiltres>({})
  const [tri, setTri] = useState('recentes')
  const [bienOuvert, setBienOuvert] = useState<number | null>(null)
  const isMobile = useIsMobile()
  const [mobileVue, setMobileVue] = useState<'liste' | 'carte'>('liste')
  const setModuleMap = useApp((s) => s.setModuleMap)
  const setFlyTo = useApp((s) => s.setFlyTo)
  const radarToOpen = useApp((s) => s.radarToOpen)
  const setRadarToOpen = useApp((s) => s.setRadarToOpen)

  const { data, isLoading } = useQuery({ queryKey: ['radar-biens', f, tri], queryFn: () => getRadarBiens(f, tri) })
  const biens = useMemo(() => data?.biens ?? [], [data])

  // carte = rattachés SEULEMENT → pins (kind='radar', couleur par statut) poussés sur la carte existante
  useEffect(() => {
    const feats = biens.filter((b) => b.coords).map((b) => ({
      type: 'Feature', geometry: { type: 'Point', coordinates: b.coords },
      properties: { kind: 'radar', bien_id: b.bien_id, idu: b.rattachement.idu, statut: b.statut },
    }))
    setModuleMap({ idus: biens.filter((b) => b.rattachement.idu).map((b) => b.rattachement.idu as string),
      extra: { type: 'FeatureCollection', features: feats } })
    return () => setModuleMap({ idus: [], extra: null })
  }, [biens, setModuleMap])

  // clic sur un pin de la carte → ouvre la fiche du bien (idiome consommé-puis-reset)
  useEffect(() => {
    if (radarToOpen != null) { setBienOuvert(radarToOpen); setRadarToOpen(null) }
  }, [radarToOpen, setRadarToOpen])

  // Clic d'une carte du listing → sa FICHE (T3). Rattaché : la carte vole à la parcelle + fiche
  // complète. Non localisé : fiche qui s'arrête aux faits, avec le bouton portail (le seul chemin
  // sortant, logué) — T2 « non localisé → portail » est honoré par ce bouton, pas de carte.
  const ouvrir = (b: RadarBienClient) => {
    if (b.rattachement.idu && b.coords) setFlyTo({ center: b.coords as [number, number], zoom: 17 })
    ouvrirBien(b.bien_id)
  }
  const setNum = (k: keyof RadarFiltres, v: string) => setF((p) => ({ ...p, [k]: v === '' ? undefined : Number(v) }))

  const nTotal = data?.n_total ?? 0
  const nRatt = data?.n_rattaches ?? 0
  const aucunFiltre = !f.commune && !f.type_bien && f.prix_min == null && f.prix_max == null && f.surface_terrain_min == null && !f.rattache && !f.particulier_pro

  const selInput = 'h-[35px] rounded-lg border border-line-2 bg-surface-1 px-2.5 text-[12.5px] text-txt focus:border-mint focus:outline-none'

  // T6 — ouvrir un bien sur mobile : la fiche prend le plein écran (on repart en vue liste dessous).
  const ouvrirBien = (id: number | null) => { setBienOuvert(id); if (isMobile) setMobileVue('liste') }
  const carteVisible = !isMobile || mobileVue === 'carte'

  return (
    <>
      <aside data-radar-panel className={`flex-col border-r border-line bg-surface-1 md:flex md:w-[434px] md:shrink-0 ${isMobile && mobileVue === 'carte' ? 'hidden' : 'flex w-full'}`}>
        {/* en-tête (wording maquette) */}
        <div className="shrink-0 border-b border-line-2 px-5 pb-4 pt-5">
          <div className="font-mono text-[10.5px] tracking-[0.2em] text-txt-mut">RADAR</div>
          <h3 className="mt-1.5 text-[20px] font-semibold text-txt-hi">Les biens en vente</h3>
          <p className="mt-1.5 text-[12.5px] leading-snug text-txt-mut">Repérés sur les portails, rattachés à leur parcelle. Des faits et un lien — jamais le contenu de l’annonce.</p>
        </div>

        {/* filtres (maquette) : commune · type · prix min/max · surface min · 2 segments */}
        <div className="grid shrink-0 gap-2 border-b border-line-2 px-5 py-3.5">
          <div className="grid grid-cols-[1.25fr_1fr] gap-2">
            <select data-radar-commune value={f.commune ?? ''} onChange={(e) => setF((p) => ({ ...p, commune: e.target.value || undefined }))} className={selInput}>
              <option value="">Toute l’île</option>
              {COMMUNES_24.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
            <select value={f.type_bien ?? ''} onChange={(e) => setF((p) => ({ ...p, type_bien: e.target.value || undefined }))} className={selInput}>
              {TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-3 gap-2">
            <input type="number" min={0} placeholder="Prix min" value={f.prix_min ?? ''} onChange={(e) => setNum('prix_min', e.target.value)} className={`min-w-0 ${selInput}`} />
            <input type="number" min={0} placeholder="Prix max" value={f.prix_max ?? ''} onChange={(e) => setNum('prix_max', e.target.value)} className={`min-w-0 ${selInput}`} />
            <input type="number" min={0} placeholder="Surface min" value={f.surface_terrain_min ?? ''} onChange={(e) => setNum('surface_terrain_min', e.target.value)} className={`min-w-0 ${selInput}`} />
          </div>
          <div className="grid grid-cols-[1fr_1.2fr] gap-2">
            <Segment value={f.rattache ?? ''} onChange={(v) => setF((p) => ({ ...p, rattache: (v || undefined) as RadarFiltres['rattache'] }))}
              options={[['', 'Tous'], ['oui', 'Rattachés']]} data="radar-seg-ratt" />
            <Segment value={f.particulier_pro ?? ''} onChange={(v) => setF((p) => ({ ...p, particulier_pro: (v || undefined) as RadarFiltres['particulier_pro'] }))}
              options={[['', 'Tous'], ['particulier', 'Particulier'], ['pro', 'Pro']]} data="radar-seg-pp" />
          </div>
        </div>

        {/* compteur + tri */}
        <div className="flex shrink-0 items-center justify-between border-b border-line-2 px-5 py-3">
          <div className="text-[12.5px] text-txt-mut"><b className="text-[14px] font-semibold text-txt-hi">{nTotal}</b> bien{nTotal > 1 ? 's' : ''} · <span className="text-mint">{nRatt} sur la carte</span></div>
          {/* RV2-V4 — le sélecteur de tri avait un fond BLANC (hors DA, pas de bg-surface) : aligné sur
              les autres contrôles de l'écran (fond sombre, bordure, texte). */}
          <select value={tri} onChange={(e) => setTri(e.target.value)}
            className="rounded-lg border border-line-2 bg-surface-1 px-2.5 py-1.5 text-[12px] text-txt focus:border-mint focus:outline-none">
            {TRIS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>

        {/* listing OU état vide */}
        <div className="flex min-h-0 flex-1 flex-col gap-2.5 overflow-y-auto px-3.5 py-3">
          {isLoading && <div className="py-6 text-center text-[12px] text-txt-dim">Chargement…</div>}
          {!isLoading && biens.length === 0 && aucunFiltre && (
            <div className="flex flex-1 flex-col items-center justify-center gap-3 px-6 py-8 text-center">
              <span className="grid h-[74px] w-[74px] place-items-center rounded-full border border-mint/30 bg-mint/[0.08] text-mint">
                <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="4.5" /><circle cx="12" cy="12" r="1" fill="currentColor" /><path d="M12 3v3M21 12h-3" /></svg>
              </span>
              <h5 className="text-[15.5px] font-semibold text-txt-hi">Le Radar démarre</h5>
              <p className="max-w-[34ch] text-[12.5px] leading-relaxed text-txt-mut">Les biens en vente arrivent au fil de la collecte, chaque jour. Le premier digest part dès qu’il y a du neuf à montrer.</p>
            </div>
          )}
          {!isLoading && biens.length === 0 && !aucunFiltre && (
            <div className="rounded-xl border border-dashed border-line-2 py-8 text-center text-[12px] text-txt-mut">Aucun bien ne correspond à ces filtres.<br />Élargissez la recherche.</div>
          )}
          {biens.map((b) => <CarteBien key={b.bien_id} b={b} sel={bienOuvert === b.bien_id} onClick={() => ouvrir(b)} />)}
        </div>
      </aside>

      {/* CARTE — desktop toujours ; mobile seulement en vue carte (montée/démontée pour éviter un
          canvas maplibre 0×0). Les pins radar sont repoussés par l'effet au remontage. */}
      {carteVisible && (
        <div className="relative flex min-w-0 flex-1">
          <Suspense fallback={<div className="flex-1 bg-bg" />}><MapView /></Suspense>
        </div>
      )}

      {/* T6 — bascule mobile listing ↔ carte (patron tiroir P3). Masquée quand une fiche est ouverte. */}
      {isMobile && bienOuvert == null && (
        <button data-radar-mobile-bascule onClick={() => setMobileVue((v) => (v === 'liste' ? 'carte' : 'liste'))}
          className="fixed bottom-5 left-1/2 z-40 -translate-x-1/2 rounded-full bg-mint px-5 py-2.5 text-[12.5px] font-semibold text-mint-on shadow-elev-3">
          {mobileVue === 'liste' ? 'Voir la carte' : 'Voir la liste'}
        </button>
      )}

      {bienOuvert != null && <RadarFiche bienId={bienOuvert} onClose={() => ouvrirBien(null)} mobile={isMobile} />}
    </>
  )
}

// segment (Tous / Rattachés · Tous / Particulier / Pro) — bascule mint, gabarit maquette
function Segment({ value, onChange, options, data }: { value: string; onChange: (v: string) => void; options: readonly (readonly [string, string])[]; data: string }) {
  return (
    <div data-seg={data} className="grid h-[35px] overflow-hidden rounded-lg border border-line-2" style={{ gridAutoFlow: 'column', gridAutoColumns: '1fr' }}>
      {options.map(([v, l], i) => (
        <button key={v || 'tous'} onClick={() => onChange(v)}
          className={`flex items-center justify-center whitespace-nowrap px-1.5 text-[12px] ${i ? 'border-l border-line-2' : ''} ${value === v ? 'bg-mint/12 font-medium text-mint' : 'text-txt-mut hover:text-txt'}`}>{l}</button>
      ))}
    </div>
  )
}
