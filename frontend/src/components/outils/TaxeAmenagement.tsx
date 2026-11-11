import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  getTaxeAmenagement, getTaxeConfig, getTaxePrefill,
  type TaxeParams, type TaxeResult,
} from '../../lib/api'
import { fmtEur, fmtInt, fmtM2 } from '../../lib/format'
import { useApp } from '../../store/useApp'
import { EntreeParcelle, type SourceParcelle } from './EntreeParcelle'   // RECETTE-1 F2
import { Tip } from '../Tip'
import { Chargement, Squelette } from '../Loading'
import { ErrorState } from '../States'
import { Case } from '../ui/Case'
import { Bouton } from '../ui/Bouton'

// K3 (rattrapage KelFoncier) — outil « Taxe d'aménagement » (calculette). 100 % piloté par le backend :
// le barème (valeur forfaitaire, abattement) et les taux viennent de /outils/taxe-amenagement/config et
// du prefill (taux communal PUBLIC de la parcelle). AUCUN montant ni taux n'est écrit en dur ici. Tant
// que le taux communal public manque, l'outil n'invente jamais de total.
// OUTILS-REFONTE-1 (9c) — maquette 9c-taxe : « Votre projet » (surface taxable · Logement/Autre ·
// abattements à cocher) → encadré résultat (total, assiette, parts, archéologie, note) → export.
// Simplifié par rapport à l'ancien formulaire (forfaits piscine/PV/…, nature exonérée, saisie manuelle
// des taux, nombre de logements RETIRÉS) ; le calcul back reste le MÊME lecteur.
// DA LABUSE : fond sombre, accent vert mint ; le mauve est réservé à l'IA (interdit ici).

/** Case à cocher au gabarit LABUSE. */
function CheckField({ label, checked, onChange, hint, dataAttr }: {
  label: string; checked: boolean; onChange: (v: boolean) => void; hint?: string; dataAttr?: string
}) {
  return (
    <Case checked={checked} data-taxe-check={dataAttr}
      onChange={(e) => onChange(e.target.checked)}
      className="items-start rounded-lg border border-line-2 bg-surface-3 px-2.5 py-2"
      label={
        <span className="min-w-0">
          <span className="text-[11.5px] text-txt">{label}</span>
          {hint && <span className="mt-0.5 block text-[10px] leading-snug text-txt-dim">{hint}</span>}
        </span>
      } />
  )
}

/** OUTILS-REFONTE-1 (9c) — export : fenêtre imprimable du résultat (le navigateur enregistre en PDF).
 *  Toutes les valeurs viennent du résultat calculé (`r`) — rien n'est recomposé ni inventé. */
function exporterTaxe(r: TaxeResult, parcelle: { idu?: string; commune?: string } | null) {
  const w = window.open('', '_blank', 'width=720,height=900')
  if (!w) return
  const row = (k: string, v: string) => `<tr><td>${k}</td><td style="text-align:right;font-variant-numeric:tabular-nums">${v}</td></tr>`
  const lignes = (r.lignes ?? []).map((l) => row(`${l.poste}${l.detail ? ` <span style="color:#888;font-size:11px">(${l.detail})</span>` : ''}`, fmtEur(l.assiette_eur))).join('')
  w.document.write(`<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Taxe d'aménagement${parcelle?.idu ? ` — ${parcelle.idu}` : ''}</title>
    <style>body{font:13px/1.5 system-ui,sans-serif;color:#111;max-width:620px;margin:32px auto;padding:0 20px}
    h1{font-size:18px;margin:0 0 2px} .sub{color:#666;margin:0 0 18px}
    table{width:100%;border-collapse:collapse} td{padding:6px 0;border-bottom:1px solid #eee}
    .total td{font-size:17px;font-weight:700;color:#0a7a52;border-bottom:2px solid #0a7a52}
    .note{color:#777;font-size:11px;margin-top:14px}</style></head><body>
    <h1>Taxe d'aménagement — estimation</h1>
    <p class="sub">${parcelle?.idu ?? ''}${parcelle?.commune ? ` · ${parcelle.commune}` : ''}</p>
    <table>
      ${r.total_eur != null ? `<tr class="total"><td>Taxe d'aménagement estimée</td><td style="text-align:right">${fmtEur(r.total_eur)}</td></tr>` : ''}
      ${row('Assiette imposable', fmtEur(r.assiette_eur))}
      ${lignes}
      ${r.part_communale_eur != null ? row(`Part communale${r.taux_communal_pct != null ? ` · ${r.taux_communal_pct} %` : ''}`, fmtEur(r.part_communale_eur)) : ''}
      ${r.part_departementale_eur != null ? row(`Part départementale · ${r.taux_departemental_pct} %`, fmtEur(r.part_departementale_eur)) : ''}
      ${r.rap_eur != null ? row(`Redevance d'archéologie préventive${r.rap_pct != null ? ` · ${r.rap_pct} %` : ''}`, fmtEur(r.rap_eur)) : ''}
    </table>
    <p class="note">Valeur forfaitaire ${r.annee} · ${r.source}. Estimation indicative ; le montant définitif est fixé par l'administration après le permis.</p>
    </body></html>`)
  w.document.close()
  w.focus()
  setTimeout(() => w.print(), 300)
}

export function TaxeAmenagement() {
  const cfg = useQuery({ queryKey: ['taxe-config'], queryFn: getTaxeConfig })
  const selectedIdu = useApp((s) => s.selectedIdu)   // parcelle sélectionnée → ouverture « depuis la parcelle »
  const focusParcelle = useApp((s) => s.focusParcelle)   // RETOURS-15 C5 — résolution → zoom + contour + fiche
  const select = useApp((s) => s.select)             // RECETTE-1 F1/F3 — vider la parcelle partagée (fiche)

  // ── saisie (maquette 9c) ──
  const [surface, setSurface] = useState<number | null>(null)
  // OUTILS-REFONTE-1 (9c) — Logement / Autre : « Autre » (non résidentiel) = pas d'abattement RP/social.
  const [usage, setUsage] = useState<'logement' | 'autre'>('logement')
  const [residencePrincipale, setResidencePrincipale] = useState(false)
  const [logementAide, setLogementAide] = useState(false)
  const [tauxDepartemental, setTauxDepartemental] = useState<number | null>(null)

  const [prefillIdu, setPrefillIdu] = useState<string | null>(selectedIdu)
  // RECETTE-1 (F2) — quelle entrée a désigné la parcelle (grise l'autre dans EntreeParcelle).
  const [source, setSource] = useState<SourceParcelle>(selectedIdu ? 'carte' : null)
  // RECETTE-1 (F1) — la parcelle de l'outil EST celle de la fiche (selectedIdu) : un clic carte l'adopte ;
  // FERMER la fiche (selectedIdu → null) VIDE l'outil.
  useEffect(() => {
    if (selectedIdu !== prefillIdu) {
      setPrefillIdu(selectedIdu)
      setSurface(null)
      if (selectedIdu == null) setSource(null)
      else if (source == null) setSource('carte')
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedIdu])
  const resetAll = () => {
    select(null)
    setPrefillIdu(null); setSource(null)
    setSurface(null); setUsage('logement'); setResidencePrincipale(false); setLogementAide(false)
    setTauxDepartemental(null)
  }
  const prefill = useQuery({
    queryKey: ['taxe-prefill', prefillIdu], queryFn: () => getTaxePrefill(prefillIdu!),
    enabled: !!prefillIdu, retry: false,
  })

  // Taux départemental = PLAFOND LÉGAL servi (part_departementale_defaut) tant que non surchargé.
  const depDefaut = cfg.data?.taux.part_departementale_defaut ?? null
  const tauxDepEffectif = tauxDepartemental ?? depDefaut
  // Taux communal PUBLIC de la parcelle (prefill, même id que la fiche §7) → envoyé via `insee`.
  const insee = prefill.data?.insee ?? null
  const logement = usage === 'logement'

  const params: TaxeParams | null = useMemo(() => {
    if (surface == null || surface <= 0) return null
    return {
      surface_taxable_m2: surface,
      residence_principale: (logement && residencePrincipale) || undefined,
      logement_aide: (logement && logementAide) || undefined,
      taux_departemental_pct: tauxDepEffectif,
      insee: insee ?? undefined,
      idu: prefillIdu ?? undefined,   // TAXE-FIX-1 point 3 — secteur à taux majoré prioritaire
    }
  }, [surface, logement, residencePrincipale, logementAide, tauxDepEffectif, insee, prefillIdu])

  const calc = useQuery({
    queryKey: ['taxe-calc', params],
    queryFn: () => getTaxeAmenagement(params!),
    enabled: !!params,
  })
  const r: TaxeResult | undefined = calc.data

  if (cfg.isLoading) return <Squelette lignes={4} />
  if (cfg.isError || !cfg.data) return (
    <ErrorState message="Barème indisponible — réessayez plus tard." retry={() => cfg.refetch()} />
  )
  const c = cfg.data
  const parcelle = prefill.data ? { idu: prefill.data.idu, commune: prefill.data.commune } : null

  return (
    <div data-taxe-panel className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
      {/* RECETTE-1 (F2) — EntreeParcelle (boîte parcelle option A) : adresse/IDU OU clic carte. */}
      <EntreeParcelle source={source} picked={prefillIdu} onChanger={resetAll}
        onPick={(i, src) => { setSource(src); setPrefillIdu(i); focusParcelle(i, { fiche: true }) }} />

      {prefillIdu && prefill.isLoading && (
        <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[10.5px] text-txt-mut">
          <Chargement variant="inline" label="Chargement du contexte parcelle…" />
        </div>
      )}

      {/* VOTRE PROJET — surface taxable · Logement/Autre · abattements à cocher. */}
      {prefillIdu && (
      <div className="flex flex-col gap-2 rounded-lg border border-line-2 bg-surface-2 p-3">
        <div className="flex items-center gap-1.5">
          <p className="label-caps text-[9.5px] text-txt-dim">Votre projet</p>
          <Tip garder side="bottom" tip={`Estimez la taxe d'aménagement avant le dépôt du permis. Valeurs ${c.meta.annee} (CGI art. 1635 quater A et s.) ; à La Réunion, c'est la valeur forfaitaire hors Île-de-France qui s'applique (${fmtEur(c.valeur_forfaitaire_m2.hors_idf)}/m²). La surface taxable = surface close et couverte > 1,80 m, garages et annexes INCLUS (≠ SDP). Le montant définitif est fixé par l'administration. Source : ${c.meta.source}.`}>
            <span role="button" tabIndex={0} aria-label="Méthode et sources"
              className="flex h-[15px] w-[15px] shrink-0 items-center justify-center rounded-full border border-line-2 text-[9px] font-bold leading-none text-txt-dim hover:border-mint hover:text-mint">i</span>
          </Tip>
        </div>

        {/* Surface taxable — champ saisissable (texte, clavier numérique, sans flèches), « m² de surface taxable » à droite. */}
        <div className="flex items-center gap-2">
          <input
            data-taxe-field="surface" type="text" inputMode="numeric" aria-label="Surface taxable"
            className="h-10 w-28 rounded-lg border border-line-2 bg-surface-3 px-3 text-[16px] font-mono tabular-nums text-txt-hi focus:border-mint focus:outline-none"
            placeholder="0" value={surface ?? ''}
            onChange={(e) => { const v = e.target.value.replace(/[^\d]/g, ''); setSurface(v === '' ? null : Number(v)) }} />
          <span className="text-[11px] text-txt-mut">m² de surface taxable</span>
        </div>

        {/* Logement / Autre — segmented toggle. */}
        <div data-taxe-usage className="flex gap-1.5">
          {([['logement', 'Logement'], ['autre', 'Autre']] as const).map(([k, l]) => (
            <button key={k} data-taxe-usage-opt={k} onClick={() => setUsage(k)}
              aria-pressed={usage === k}
              className={`rounded-lg border px-3 py-1.5 text-[11.5px] transition-colors duration-quick ${
                usage === k ? 'border-mint bg-mint/15 font-medium text-mint' : 'border-line-2 text-txt-mut hover:text-txt'}`}>
              {l}
            </button>
          ))}
        </div>

        {/* Abattements à cocher — seulement pour un logement (pas de minoration RP/social sur « Autre »). */}
        {logement && (
          <div className="flex flex-col gap-1.5">
            <CheckField dataAttr="residence" label={`Résidence principale (abattement ${fmtInt(c.abattement.taux_pct)} % sur ${fmtInt(c.abattement.plafond_m2_residence_principale)} m²)`}
              checked={residencePrincipale} onChange={setResidencePrincipale}
              hint={`Minore la taxe : abattement de ${fmtInt(c.abattement.taux_pct)} % sur les ${fmtInt(c.abattement.plafond_m2_residence_principale)} premiers m² (CGI 1635 quater I).`} />
            <CheckField dataAttr="aide" label="Logement social ou financé par un PTZ"
              checked={logementAide} onChange={setLogementAide}
              hint={`Abattement ${fmtInt(c.abattement.taux_pct)} % (logement locatif social / aidé, PLUS-PLS).`} />
          </div>
        )}
      </div>
      )}

      {/* RÉSULTAT — total (gros, vert) · assiette · parts · archéologie · note. */}
      {prefillIdu && !params && (
        <p className="text-[11px] text-txt-dim">Saisissez une surface taxable pour estimer la taxe.</p>
      )}
      {calc.isLoading && <Squelette lignes={3} />}
      {calc.isError && <ErrorState message="Erreur de calcul — vérifiez les valeurs saisies." retry={() => calc.refetch()} />}

      {r && !calc.isLoading && (
        <div data-taxe-resultat className="flex flex-col gap-1.5 rounded-lg border border-mint/40 bg-surface-1 p-3">
          {/* Total EN TÊTE (gros, vert) — ou message honnête si le taux communal manque. */}
          {r.total_eur != null ? (
            <div className="flex items-baseline justify-between gap-2 border-b border-line pb-2">
              <span className="text-[12px] text-txt-mut">Taxe d'aménagement estimée</span>
              <span data-taxe-total className="font-mono text-[22px] font-bold tabular-nums text-mint">{fmtEur(r.total_eur)}</span>
            </div>
          ) : r.taux_communal_manquant && r.message_taux_communal ? (
            <div data-taxe-manque className="rounded-md border border-st-creuser/40 bg-st-creuser/10 px-2.5 py-1.5 text-[10.5px] leading-snug text-st-creuser">
              {r.message_taux_communal}
            </div>
          ) : null}

          {/* Assiette (surface × valeur forfaitaire). */}
          <div className="flex items-baseline justify-between gap-2 pt-1 text-[11px]">
            <span className="min-w-0 text-txt-mut">Assiette{r.lignes?.[0]?.detail ? <span className="text-txt-dim"> ({r.lignes[0].detail})</span> : ''}</span>
            <span className="shrink-0 font-mono tabular-nums text-txt">{fmtEur(r.assiette_eur)}</span>
          </div>
          {/* Parts. */}
          {r.part_communale_eur != null && (
            <div className="flex items-baseline justify-between gap-2 text-[11px]">
              <span className="text-txt-mut">Part communale <span className="text-txt-dim">· {r.taux_communal_pct != null ? `${r.taux_communal_pct} %` : '—'}{r.taux_communal_secteur_majore ? ' (majoré)' : ''}</span></span>
              <span className="shrink-0 font-mono tabular-nums text-txt">{fmtEur(r.part_communale_eur)}</span>
            </div>
          )}
          {r.part_departementale_eur != null && (
            <div className="flex items-baseline justify-between gap-2 text-[11px]">
              <span className="text-txt-mut">Part départementale <span className="text-txt-dim">· {r.taux_departemental_pct} %{!r.part_departementale_confirmee ? ', à confirmer' : ''}</span></span>
              <span className="shrink-0 font-mono tabular-nums text-txt">{fmtEur(r.part_departementale_eur)}</span>
            </div>
          )}
          {/* Redevance d'archéologie préventive — taxe DISTINCTE (0,40 % de la même assiette). */}
          {r.rap_eur != null && r.assiette_eur > 0 && (
            <div data-taxe-rap className="flex items-baseline justify-between gap-2 text-[11px]">
              <span className="text-txt-mut">Redevance archéologie <span className="text-txt-dim">· {r.rap_pct} %</span></span>
              <span className="shrink-0 font-mono tabular-nums text-txt">{fmtEur(r.rap_eur)}</span>
            </div>
          )}
          {/* Note de valeur forfaitaire + millésime du taux communal + exigibilité. */}
          <p className="mt-0.5 border-t border-line pt-1.5 text-[9.5px] leading-snug text-txt-dim">
            Valeur forfaitaire {r.annee}
            {r.taux_communal_source === 'public' && r.taux_communal_millesime ? ` · taux communaux ${r.taux_communal_millesime}` : ''}
            {' · exigible au permis · '}
            <a href={r.url} target="_blank" rel="noreferrer" className="text-mint hover:underline">{r.source}</a>
            {r.taux_communal_perime && <span data-taxe-perime className="ml-1 font-medium text-st-creuser">⚠ taux non rafraîchi depuis plus d'un an.</span>}
          </p>
          {/* Ce que le barème ne couvre pas (discret). */}
          {r.non_couvert && r.non_couvert.length > 0 && (
            <p data-taxe-non-couvert className="text-[9px] leading-snug text-txt-dim">Non pris en compte : {r.non_couvert.join(' · ')}.</p>
          )}

          {/* Export PDF (impression du résultat → le navigateur enregistre en PDF). */}
          {r.total_eur != null && (
            <Bouton niveau="secondaire" ton="vert" data-taxe-export className="mt-1 w-full justify-center"
              onClick={() => exporterTaxe(r, parcelle)}>
              Exporter en PDF
            </Bouton>
          )}
        </div>
      )}
      {/* repère : surface terrain (prefill) — discret, ne sert pas au calcul. */}
      {prefill.data?.surface_terrain_m2 != null && prefillIdu && (
        <p className="text-[9.5px] text-txt-dim">Terrain : {fmtM2(prefill.data.surface_terrain_m2)} (référence cadastrale).</p>
      )}
    </div>
  )
}
