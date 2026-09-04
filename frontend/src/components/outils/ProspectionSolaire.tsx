/**
 * Outil « Prospection solaire » — données solaire/piscines de `parcel_solar` / `parcel_equipements`,
 * GELÉES au 11/07/2026 (PVGIS v5.3 SARAH3, RGE ALTI, Ortho Express RVB 20 cm 2025, détection FLAIR).
 * RETOURS-11F4 C6 : « BD ORTHO 20 cm 2025 » corrigé — le seul millésime 2025 servi au 974 par l'IGN est
 * l'Ortho Express RVB (GetTile vérifié) ; « BD ORTHO 2025 » n'existe pas au 974. RGPD :
 * aucune donnée nominative — des parcelles et des caractéristiques, jamais des personnes.
 *
 * Mandat SOLAIRE (refonte 13 outils) — DEUX MÉTIERS, DEUX ENTRÉES (fini l'écran unique illisible) :
 *   • 💧 Piscines (pisciniste) : la STAT d'abord (compteur île + par commune), carte, listing.
 *   • ☀️ Ensoleillement (installateur PV) : critères + barre unique (SOCLE) → FICHE SOLEIL (potentiel
 *     avec unité, toiture, orientation, PROFIL MENSUEL 12 barres, limites affichées).
 * Écartées MASQUÉES par défaut dans les listes (option « les inclure »). Garde-fou : aucun recalcul —
 * présentation + requêtes d'agrégats (nouveaux endpoints /prospection-piscines et .../parcelle/{idu}
 * = lecture seule de données gelées).
 */
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { getPiscinesAgregat, getPiscinesPoints, getProspectionSolaire, getSolaireFiche,
  postPasUnePiscine, type SolaireFiche, type SolaireFiltres } from '../../lib/api'
import { fmtInt } from '../../lib/format'
import { TOKENS } from '../../lib/tokens'
import { useApp } from '../../store/useApp'
import { ParcelInput } from '../ParcelInput'
import { Loading } from '../Loading'
import { ErrorState } from '../States'
import { ListPaginationFooter, usePagination } from '../ListPagination'

const SOURCES_PIED = 'Détection FLAIR sur ortho · PVGIS v5.3 SARAH3 · RGE ALTI · données gelées 11/07/2026'
const MOIS = ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D']
const num = (v: number | null | undefined, unit = '') => (v == null ? '—' : `${fmtInt(v)}${unit}`)

export function ProspectionSolaire() {
  const [mode, setMode] = useState<'piscines' | 'ensoleillement' | null>(null)
  // RADAR-CATÉGORIE (T3) — la tuile « Solaire » de la fiche d'un bien pré-remplit l'IDU de la
  // parcelle rattachée : on ouvre DIRECTEMENT le mode ensoleillement sur cette parcelle (fiche soleil).
  const solairePrefill = useApp((s) => s.solairePrefill)
  const setSolairePrefill = useApp((s) => s.setSolairePrefill)
  const [prefillIdu, setPrefillIdu] = useState<string | null>(null)
  useEffect(() => {
    if (solairePrefill) { setPrefillIdu(solairePrefill); setMode('ensoleillement'); setSolairePrefill(null) }
  }, [solairePrefill, setSolairePrefill])
  if (mode === 'piscines') return <ModePiscines onBack={() => setMode(null)} />
  if (mode === 'ensoleillement') return <ModeEnsoleillement onBack={() => setMode(null)} prefillIdu={prefillIdu} />
  return <EntreeSolaire onChoose={setMode} />
}

// ── ÉCRAN D'ENTRÉE — deux cartes ──
function EntreeSolaire({ onChoose }: { onChoose: (m: 'piscines' | 'ensoleillement') => void }) {
  const Carte = ({ k, ic, titre, desc }: { k: 'piscines' | 'ensoleillement'; ic: string; titre: string; desc: string }) => (
    <button data-solaire-mode={k} onClick={() => onChoose(k)}
      className="flex items-center gap-3 rounded-lg border border-line-2 bg-surface-2 px-3 py-3 text-left transition-colors duration-quick hover:border-mint/50 hover:bg-surface-3">
      <span className="text-xl">{ic}</span>
      <span className="min-w-0 flex-1">
        <b className="text-[13px] text-txt">{titre}</b>
        <span className="mt-0.5 block text-[10.5px] leading-snug text-txt-dim">{desc}</span>
      </span>
      <span className="text-txt-dim">→</span>
    </button>
  )
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2">
      <p className="text-[11px] text-txt-mut">Deux métiers, deux entrées.</p>
      <Carte k="piscines" ic="💧" titre="Piscines" desc="Pisciniste — parcelles avec piscine détectée : rénovation, couverture, entretien" />
      <Carte k="ensoleillement" ic="☀️" titre="Ensoleillement" desc="Installateur PV — potentiel, orientation, toiture" />
      <p className="mt-auto text-[9.5px] leading-snug text-txt-dim">{SOURCES_PIED}</p>
    </div>
  )
}

function BackBar({ onBack, titre }: { onBack: () => void; titre: string }) {
  return (
    <div className="flex items-center justify-between gap-2">
      {/* OUTILS-2 (O2-2) — fil d'Ariane vers l'OUTIL (« Prospection solaire »), pas un concept interne. */}
      <button data-solaire-retour onClick={onBack} className="text-[11px] text-mint hover:underline">‹ Prospection solaire</button>
      <span className="text-[12px] font-medium text-txt-hi">{titre}</span>
    </div>
  )
}

// ── MODE PISCINES — la stat d'abord, puis carte + listing ──
// LOT8 (OUTILS-FINALE) : le mode Piscines IGNORE le classement (toutes les piscines listées, pas de
// pied « écartées ») ; PAS de sélecteur Périmètre (toute l'île d'office, la ventilation par commune
// reste dans le bloc stats, cliquable pour drill) ; tableau 2 colonnes (Parcelle · Commune ;
// surface retirée O12a), paginé par 200 (O12c).
function ModePiscines({ onBack }: { onBack: () => void }) {
  const select = useApp((s) => s.select)
  const setModuleMap = useApp((s) => s.setModuleMap)
  const qc = useQueryClient()
  const [commune, setCommune] = useState<string | null>(null)
  // RETOURS-11F M12 — bascule « inclure les incertaines » : par défaut seule la confiance HAUTE (≥ 0,80)
  // est comptée/cartographiée ; la bascule ajoute les bandes moyenne/basse (Vic a vu ~1 faux sur 4).
  const [inclureIncertaines, setInclureIncertaines] = useState(false)

  const agg = useQuery({ queryKey: ['piscines-agg', commune, inclureIncertaines], queryFn: () => getPiscinesAgregat(commune, 0, inclureIncertaines), staleTime: 60_000 })
  // O12a (RETOURS-11) — la surface piscine (mesure vue du ciel) était FAUSSE : plus de filtre ni de
  // colonne surface. Le pisciniste veut la parcelle et la commune, pas un m² inventé.
  // RETOURS-11F3 avenant (note liée) — le LISTING suit le MÊME filtre de confiance que le compteur.
  const filtres: SolaireFiltres = { commune, piscine: 'oui', inclureIncertaines }
  const list = useQuery({ queryKey: ['piscines-list', commune, inclureIncertaines], queryFn: () => getProspectionSolaire(filtres), staleTime: 60_000 })
  // « pas une piscine » — retire la parcelle du service et rafraîchit compteur/carte/listing.
  const [pasPiscine, setPasPiscine] = useState<Set<string>>(new Set())
  const signalerPasPiscine = async (idu: string) => {
    setPasPiscine((s) => new Set(s).add(idu))
    try { await postPasUnePiscine(idu) } finally {
      qc.invalidateQueries({ queryKey: ['piscines-agg'] })
    }
  }

  const items = list.data?.items ?? []   // aucune exclusion « écartée » : le pisciniste veut TOUTES les piscines
  // O12c (RETOURS-11) — le listing (jusqu'à 8 299) se pagine par 200 via le pied partagé.
  const page = usePagination(items.length)
  const [carteBusy, setCarteBusy] = useState(false)
  // R8(a) — la carte se BASCULE : une fois posée, le bouton dit « Masquer sur la carte » et un
  // second clic retire les marqueurs (l'utilisateur voit que l'action a eu lieu, et peut la défaire).
  const [carteAffichee, setCarteAffichee] = useState(false)
  // RETOURS-11F3 avenant R11 — une fois la carte affichée, le gros encadré « Piscines détectées »
  // (nombre + méthode + 8 communes) SE REPLIE en une ligne de résumé pour laisser voir le listing.
  // Réversible (déplier). Reposé à faux quand on masque la carte ou change de commune.
  const [comptageReplie, setComptageReplie] = useState(false)
  useEffect(() => () => setModuleMap({ idus: [], extra: null }), [setModuleMap])
  // Changer de commune (ou revenir à l'île) invalide les points posés : on repart « Voir sur la carte ».
  useEffect(() => { setCarteAffichee(false); setComptageReplie(false); setModuleMap({ idus: [], extra: null }) }, [commune, setModuleMap])
  // LOT8b — « Voir sur la carte » = TOUTES les piscines en marqueurs (pas le listing capé à 500) :
  // on charge les points GeoJSON et on les pose dans module-extra (couche module-pts, kind='piscine').
  const voirCarte = async () => {
    if (carteAffichee) { setModuleMap({ idus: [], extra: null }); setCarteAffichee(false); setComptageReplie(false); return }
    setCarteBusy(true)
    try {
      setModuleMap({ idus: [], extra: await getPiscinesPoints(commune, 0, inclureIncertaines) })
      setCarteAffichee(true); setComptageReplie(true)   // R11 — replie le comptage pour dévoiler le listing
    }
    finally { setCarteBusy(false) }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
      <BackBar onBack={onBack} titre="💧 Piscines" />
      {commune && (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
          <button data-piscines-reset onClick={() => setCommune(null)} className="text-[10.5px] text-mint hover:underline">‹ toute l’île</button>
        </div>
      )}

      {/* LA STAT D'ABORD */}
      {agg.isLoading && <Loading label="Comptage des piscines…" />}
      {agg.isError && <ErrorState message="Détection piscines momentanément indisponible." />}
      {/* R11 — quand la carte est affichée, le comptage se replie en UNE ligne (déplier) pour dévoiler le listing. */}
      {agg.data && comptageReplie && (
        <button data-piscines-comptage-replie onClick={() => setComptageReplie(false)}
          className="flex w-full items-center gap-2 rounded-lg border px-3 py-1.5 text-left text-[11px] transition-colors duration-quick hover:brightness-110"
          style={{ borderColor: `${TOKENS.mint}4d`, background: `${TOKENS.mint}0f` }}>
          <b className="tnum" style={{ color: TOKENS.mint }}>{fmtInt(agg.data.total)}</b>
          <span className="text-txt-mut">piscines · confiance {inclureIncertaines ? 'haute + incertaines' : 'haute'}</span>
          <span className="ml-auto text-mint">déplier ▾</span>
        </button>
      )}
      {agg.data && !comptageReplie && (
        <div className="rounded-lg border px-3 py-2.5" style={{ borderColor: `${TOKENS.mint}4d`, background: `${TOKENS.mint}0f` }}>
          {carteAffichee && (
            <div className="mb-1 text-right">
              <button data-piscines-comptage-replier onClick={() => setComptageReplie(true)} className="text-[10px] text-txt-dim hover:text-mint">replier ▴</button>
            </div>
          )}
          <div className="text-[10px] text-txt-dim">Piscines détectées — {commune ?? 'toute l’île'}</div>
          <div className="mt-0.5"><b data-piscines-total className="tnum text-2xl font-semibold" style={{ color: TOKENS.mint }}>{fmtInt(agg.data.total)}</b>
            <span className="ml-2 text-[9.5px] text-txt-dim">détection ortho/IA · à confirmer sur site</span></div>
          {/* RETOURS-11F M12 — bascule CONFIANCE : par défaut « haute » ; le nombre d'incertaines est DIT. */}
          {agg.data.confiance && (
            <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-[10px]">
              <span className="text-txt-dim">Confiance <b className="text-txt-mut">haute (≥ {agg.data.confiance.seuil_haute.toLocaleString('fr-FR')})</b> par défaut.</span>
              <button data-piscines-toggle-incertaines onClick={() => setInclureIncertaines((v) => !v)}
                className="rounded border px-1.5 py-0.5 font-medium transition-colors duration-quick hover:brightness-110"
                style={inclureIncertaines
                  ? { borderColor: `${TOKENS.mint}66`, color: TOKENS.mint, background: `${TOKENS.mint}12` }
                  : { borderColor: 'var(--line-2)', color: 'var(--txt-mut)' }}>
                {inclureIncertaines ? '✓ incertaines incluses' : `inclure les incertaines (+${fmtInt(agg.data.confiance.incertaines)})`}
              </button>
              {(agg.data.corrigees ?? 0) > 0 && (
                <span className="text-txt-dim">· {fmtInt(agg.data.corrigees ?? 0)} retirée(s) « pas une piscine »</span>
              )}
            </div>
          )}
          {/* LOT8a — le SEUIL de rétention est écrit à l'écran (des détections plus incertaines sont exclues) */}
          <div data-piscines-source className="mt-1 text-[9px] leading-snug text-txt-dim">{agg.data.source}</div>
          {!commune && agg.data.communes.length > 0 && (
            <div className="mt-2 flex flex-col gap-0.5">
              {agg.data.communes.slice(0, 8).map((c) => (
                <div key={c.commune} className="flex items-baseline justify-between gap-2 text-[11px]">
                  <button onClick={() => setCommune(c.commune)} className="text-txt-mut hover:text-mint">{c.commune}</button>
                  <span className="tnum text-txt">{fmtInt(c.n)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <button data-solaire-carte data-carte-affichee={carteAffichee ? '1' : '0'} onClick={voirCarte} disabled={carteBusy}
        className="rounded-lg border py-1.5 text-center text-[11px] font-medium transition-colors duration-quick hover:brightness-110 disabled:opacity-50"
        style={carteAffichee
          ? { borderColor: `${TOKENS.mint}66`, color: 'var(--txt-mut)', background: 'transparent' }
          : { borderColor: `${TOKENS.mint}66`, color: TOKENS.mint, background: `${TOKENS.mint}12` }}>
        {carteBusy ? '💧 Chargement…'
          : carteAffichee ? 'Masquer sur la carte'
            : `💧 Voir sur la carte${agg.data ? ` (${fmtInt(agg.data.total)})` : ''}`}
      </button>

      {/* LISTING piscines — 2 colonnes (Parcelle · Commune), surface retirée (O12a). */}
      {list.isLoading && <Loading label="Parcelles…" />}
      {list.data && (
        <>
          <div className="min-h-0 flex-1 overflow-y-auto">
            <table className="w-full text-[11px]">
              <thead className="sticky top-0 bg-surface-2 text-left text-[10px] uppercase tracking-wide text-txt-dim">
                <tr><th className="px-2 py-1.5">Parcelle</th><th className="px-2 py-1.5">Commune</th><th className="px-2 py-1.5" /></tr>
              </thead>
              <tbody>
                {items.slice(0, page.shown).map((it) => {
                  const retiree = pasPiscine.has(it.idu)
                  return (
                  <tr key={it.idu} data-piscines-row className={`border-t border-line ${retiree ? 'opacity-40' : 'hover-fill cursor-pointer'}`} onClick={() => !retiree && select(it.idu)}>
                    <td className="px-2 py-1.5 font-mono text-txt">{it.idu}</td>
                    <td className="px-2 py-1.5 text-txt-mut">{it.commune}</td>
                    {/* RETOURS-11F M12 — « pas une piscine » : signal humain, retire du service (compteur/carte). */}
                    <td className="px-2 py-1.5 text-right">
                      {retiree ? <span className="text-[9.5px] text-txt-dim">retirée</span> : (
                        <button data-piscines-pas onClick={(e) => { e.stopPropagation(); void signalerPasPiscine(it.idu) }}
                          title="Signaler que cette parcelle n'a pas de piscine — la retire du compteur et de la carte"
                          className="text-[9.5px] text-txt-dim hover:text-mint">pas une piscine</button>
                      )}
                    </td>
                  </tr>
                )})}
              </tbody>
            </table>
          </div>
          {/* R8(b) — COMPTEUR HONNÊTE. Le listing est plafonné par le serveur (`cap`, ex. 500) alors que
              la détection compte ~8 299 piscines (`total`). On paginait 200 par 200 SUR les lignes chargées,
              d'où le trompeur « 200 / 500 ». Ici : « N affichées · P listées sur T détectées » — la borne de
              pagination reste le nombre de lignes réellement chargées (items.length), on annonce la vérité. */}
          <ListPaginationFooter shown={Math.min(page.shown, items.length)} total={items.length} onMore={page.more}>
            {list.data && list.data.total > items.length && (
              <span data-piscines-cap className="text-[10.5px] text-txt-dim">
                {fmtInt(items.length)} listées{list.data.tronquee ? ` (limite ${fmtInt(list.data.cap)})` : ''} sur <b className="text-txt-mut">{fmtInt(list.data.total)}</b> détectées — la carte les montre toutes.
              </span>
            )}
          </ListPaginationFooter>
        </>
      )}
      <p className="text-[9.5px] leading-snug text-txt-dim">{SOURCES_PIED}</p>
    </div>
  )
}

// ── MODE ENSOLEILLEMENT — barre unique → fiche soleil « Ma parcelle » ──
// O13a (RETOURS-11) — l'onglet « Top parcelles » (classement) est retiré : l'installateur PV part
// d'UNE parcelle désignée, pas d'une liste globale. Reste la barre unique (SOCLE) → fiche soleil.
function ModeEnsoleillement({ onBack, prefillIdu }: { onBack: () => void; prefillIdu?: string | null }) {
  const select = useApp((s) => s.select)
  const [ficheIdu, setFicheIdu] = useState<string | null>(prefillIdu ?? null)

  const fiche = useQuery({ queryKey: ['solaire-fiche', ficheIdu], queryFn: () => getSolaireFiche(ficheIdu!), enabled: !!ficheIdu, retry: false })

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
      <BackBar onBack={onBack} titre="☀️ Ensoleillement" />
      {/* BARRE UNIQUE (SOCLE) → FICHE SOLEIL */}
      <ParcelInput dataAttr="solaire-idu" placeholder="Adresse ou IDU — la fiche soleil de la parcelle" onPick={setFicheIdu} />
      {ficheIdu && fiche.isLoading && <p className="text-[11px] text-txt-mut">Fiche soleil…</p>}
      {ficheIdu && fiche.isError && <p className="text-[11px] text-st-ecartee">Parcelle introuvable — vérifiez l’IDU.</p>}
      {ficheIdu && fiche.data && <FicheSoleil f={fiche.data} onOpen={() => select(ficheIdu)} />}
      {!ficheIdu && <p className="text-[11px] text-txt-mut">Saisissez une parcelle pour sa fiche soleil (potentiel, toiture, profil mensuel).</p>}
      <p className="mt-auto text-[9.5px] leading-snug text-txt-dim">{SOURCES_PIED}</p>
    </div>
  )
}

function KPI({ k, v, u }: { k: string; v: string; u?: string }) {
  return (
    <div className="rounded bg-surface-2 px-2 py-1">
      <div className="text-[9px] text-txt-dim">{k}</div>
      <div className="text-[13px] font-semibold text-txt">{v}{u && <span className="ml-1 text-[9px] font-normal text-txt-dim">{u}</span>}</div>
    </div>
  )
}

// FICHE SOLEIL — potentiel (unité), toiture, orientation, PROFIL MENSUEL (12 barres), limites.
function FicheSoleil({ f, onOpen }: { f: SolaireFiche; onOpen: () => void }) {
  if (!f.ok) return <p className="rounded-lg bg-surface-2 px-3 py-2 text-[11px] leading-snug text-txt-dim">{f.message ?? 'Aucune donnée solaire pour cette parcelle.'}</p>
  const pm = f.prod_mensuel ?? []
  const max = Math.max(...pm, 1)
  // O13b (RETOURS-11) — dimensionnement dérivé des champs déjà servis (jamais inventé) :
  //   kWc installable = emprise toit × part réellement exploitable (0,2 kWc/m², règle métier) ;
  //   production annuelle = kWc × productible PVGIS (kWh/kWc/an). Absents → « — » (pas de zéro fabriqué).
  const kwc = f.toit_m2 == null ? null : Math.round(f.toit_m2 * 0.2 * 10) / 10
  const prodAn = kwc == null || f.productible == null ? null : Math.round(kwc * f.productible)
  return (
    <div data-solaire-fiche className="rounded-lg border px-3 py-2.5" style={{ borderColor: `${TOKENS.mint}55` }}>
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-[11px] text-txt">{f.idu}</span>
        <span className="text-[10px] text-txt-dim">{f.commune}{f.classement ? ` · ${f.classement}` : ''}</span>
      </div>
      <div className="mt-2 grid grid-cols-2 gap-1.5">
        <KPI k="Potentiel" v={num(f.productible)} u="kWh/kWc/an" />
        <KPI k="Toiture (emprise)" v={num(f.toit_m2, ' m²')} />
        {/* O13b — puissance installable + production annuelle estimées, dérivées des mesures servies. */}
        <KPI k="Puissance installable" v={kwc == null ? '—' : String(kwc).replace('.', ',')} u="kWc" />
        <KPI k="Production annuelle" v={num(prodAn)} u="kWh/an" />
        {/* orientation = azimut DU BÂTI (Estimé), pas une orientation « optimale » (non calculée) ;
            l'inclinaison optimale n'est pas servie par la V1 → non affichée (jamais inventée). */}
        <KPI k="Orientation du bâti" v={f.azimut == null ? '—' : `${f.azimut}°`} />
        <KPI k="Pente terrain" v={f.pente == null ? '—' : `${f.pente}°`} />
      </div>
      {/* O13b — croisement piscine sur la parcelle (champ déjà servi par la fiche) : signal métier
          (climatisation / bassin à chauffer). Surface piscine NON affichée (mesure aérienne fausse, O12a). */}
      {f.piscine && (
        <div data-solaire-piscine className="mt-1.5 rounded px-2 py-1 text-[10px]" style={{ background: `${TOKENS.mint}12`, color: TOKENS.mint }}>
          💧 Piscine détectée sur la parcelle
        </div>
      )}
      {pm.length === 12 && (
        <>
          <p className="mt-2 text-[9px] text-txt-dim">Profil mensuel (kWh/kWc · maille PVGIS){f.mois_optimal ? ` · pic en ${MOIS[f.mois_optimal - 1]}` : ''}</p>
          <div className="mt-0.5 flex h-14 items-end gap-0.5">
            {pm.map((v, i) => (
              <div key={i} data-solaire-bar className="flex-1 rounded-t" title={`${MOIS[i]} : ${fmtInt(v)} kWh/kWc`}
                style={{ height: `${Math.max(4, Math.round((v / max) * 100))}%`, background: i + 1 === f.mois_optimal ? TOKENS.mint : `${TOKENS.mint}55` }} />
            ))}
          </div>
          <div className="flex gap-0.5 text-[8px] text-txt-dim">{MOIS.map((m, i) => <span key={i} className="flex-1 text-center">{m}</span>)}</div>
        </>
      )}
      {/* LOT9a — HONNÊTETÉ de la maille : le productible (annuel ET mensuel) est servi à la MAILLE
          PVGIS (~400 m), pas mesuré au toit → des parcelles voisines partagent la même valeur. On le
          DIT, pas de fausse précision parcellaire. */}
      <p className="mt-1.5 text-[9px] leading-snug text-txt-dim">
        Productible estimé à la <b className="text-txt-mut">maille PVGIS (~400 m)</b> — commun aux parcelles voisines, pas une mesure au toit. · Ombrage de proximité (bâti, arbres) non modélisé · panneaux existants non détectés — vérif photo aérienne avant démarchage.{f.millesime ? ` · ${f.millesime}` : ''}
      </p>
      {/* O13b — explication en clair de la maille et de l'orientation de référence (jargon → phrase). */}
      <p className="mt-1 text-[9px] leading-snug text-txt-dim">
        En clair : le potentiel est calculé sur un carré d’environ 400 m de côté (une même valeur pour toutes les parcelles du carré), pour des panneaux exposés plein nord et inclinés à 65° — l’orientation qui capte le mieux le soleil à La Réunion.
      </p>
      <button data-solaire-fiche-ouvrir onClick={onOpen} className="mt-1 text-[11px] font-medium text-mint hover:underline">Ouvrir la fiche complète →</button>
    </div>
  )
}
