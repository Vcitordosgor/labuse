import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  getTaxeAmenagement, getTaxeConfig, getTaxePrefill,
  type TaxeParams, type TaxeResult,
} from '../../lib/api'
import { fmtEur, fmtInt, fmtM2 } from '../../lib/format'
import { useApp } from '../../store/useApp'
import { ParcelInput } from '../ParcelInput'
import { Tip } from '../Tip'
import { Loading } from '../Loading'

// K3 (rattrapage KelFoncier) — outil « Taxe d'aménagement » (calculette). 100 % piloté par le backend :
// le barème (valeur forfaitaire, abattement, forfaits) et les taux (plafonds/défauts) viennent de
// /outils/taxe-amenagement/config ; le calcul détaillé (assiette + parts) vient de l'endpoint. AUCUN
// montant ni taux n'est écrit en dur ici. Le TAUX COMMUNAL n'a JAMAIS de défaut : tant qu'il n'est pas
// saisi, l'outil affiche l'assiette et les parts « en attente » — il n'invente jamais de total.
// DA LABUSE : fond sombre, accent vert mint ; le mauve est réservé à l'IA (interdit ici).

/** Champ numérique compact réutilisable (label + input + unité optionnelle). */
function NumField({ label, value, onChange, unit, placeholder, hint, dataAttr }: {
  label: string; value: number | null; onChange: (v: number | null) => void
  unit?: string; placeholder?: string; hint?: string; dataAttr?: string
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="label-caps text-[9.5px] text-txt-dim">{label}</span>
      <span className="flex items-center gap-1.5 rounded-lg border border-line-2 bg-surface-3 px-2 py-1.5 focus-within:border-mint">
        <input
          data-taxe-field={dataAttr}
          type="number" inputMode="decimal" min={0}
          value={value ?? ''} placeholder={placeholder}
          onChange={(e) => { const v = e.target.value; onChange(v === '' ? null : Math.max(0, Number(v))) }}
          className="min-w-0 flex-1 bg-transparent font-mono text-xs text-txt tabular-nums focus:outline-none" />
        {unit && <span className="shrink-0 text-[10px] text-txt-dim">{unit}</span>}
      </span>
      {hint && <span className="text-[10px] leading-snug text-txt-dim">{hint}</span>}
    </label>
  )
}

/** Case à cocher au gabarit LABUSE. */
function CheckField({ label, checked, onChange, hint, dataAttr }: {
  label: string; checked: boolean; onChange: (v: boolean) => void; hint?: string; dataAttr?: string
}) {
  return (
    <label className="flex cursor-pointer items-start gap-2 rounded-lg border border-line-2 bg-surface-3 px-2.5 py-2">
      <input type="checkbox" checked={checked} data-taxe-check={dataAttr}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-0.5 h-3.5 w-3.5 shrink-0 accent-mint" />
      <span className="min-w-0">
        <span className="text-[11.5px] text-txt">{label}</span>
        {hint && <span className="mt-0.5 block text-[10px] leading-snug text-txt-dim">{hint}</span>}
      </span>
    </label>
  )
}

export function TaxeAmenagement() {
  const cfg = useQuery({ queryKey: ['taxe-config'], queryFn: getTaxeConfig })
  const selectedIdu = useApp((s) => s.selectedIdu)   // parcelle sélectionnée → ouverture « depuis la parcelle »

  // ── saisie ──
  const [surface, setSurface] = useState<number | null>(null)
  const [residencePrincipale, setResidencePrincipale] = useState(false)
  const [logementAide, setLogementAide] = useState(false)
  const [piscine, setPiscine] = useState<number | null>(null)
  const [pvSol, setPvSol] = useState<number | null>(null)
  const [stationnement, setStationnement] = useState<number | null>(null)
  const [eoliennes, setEoliennes] = useState<number | null>(null)
  const [tauxCommunal, setTauxCommunal] = useState<number | null>(null)   // OBLIGATOIRE — jamais de défaut
  const [tauxDepartemental, setTauxDepartemental] = useState<number | null>(null)

  // RETOURS-14 S4 — l'outil s'ouvre sur la BARRE UNIQUE (adresse / IDU / référence courte,
  // moteur ParcelInput) + « ou cliquez une parcelle sur la carte » ; un clic carte pendant que
  // l'outil est ouvert ADOPTE la parcelle (selectedIdu suivi en continu — avant, rien ne le
  // disait). Changer de parcelle remet la saisie à zéro (le calcul suit la parcelle).
  const [prefillIdu, setPrefillIdu] = useState<string | null>(selectedIdu)
  useEffect(() => {
    if (selectedIdu && selectedIdu !== prefillIdu) {
      setPrefillIdu(selectedIdu); setSurface(null); setSdpPrefill(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedIdu])
  const prefill = useQuery({
    queryKey: ['taxe-prefill', prefillIdu], queryFn: () => getTaxePrefill(prefillIdu!),
    enabled: !!prefillIdu, retry: false,
  })
  // RETOURS-13 R26 — LABUSE pré-remplit la surface taxable avec ce qu'il SAIT : la SDP
  // CONSTRUCTIBLE AU GABARIT (résiduel du run servi). Étiquetée, MODIFIABLE — la surface du
  // projet reste celle du client s'il la connaît ; toute retouche efface l'étiquette.
  const [sdpPrefill, setSdpPrefill] = useState(false)
  useEffect(() => {
    const sdp = prefill.data?.sdp_gabarit_m2
    if (sdp != null && surface == null) { setSurface(sdp); setSdpPrefill(true) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prefill.data])

  // Le taux départemental se pré-remplit avec le PLAFOND LÉGAL servi (part_departementale_defaut) dès
  // que la config arrive — étiqueté « à confirmer », car part_departementale_confirmee_974 est false.
  const depDefaut = cfg.data?.taux.part_departementale_defaut ?? null
  const tauxDepEffectif = tauxDepartemental ?? depDefaut

  // Paramètres du calcul — envoyés seulement quand une surface taxable est saisie.
  const params: TaxeParams | null = useMemo(() => {
    if (surface == null || surface <= 0) return null
    return {
      surface_taxable_m2: surface,
      residence_principale: residencePrincipale || undefined,
      logement_aide: logementAide || undefined,
      piscine_m2: piscine ?? undefined,
      pv_sol_m2: pvSol ?? undefined,
      stationnement_ext_places: stationnement ?? undefined,
      eoliennes_mats: eoliennes ?? undefined,
      taux_communal_pct: tauxCommunal,               // null → total non calculé (jamais inventé)
      taux_departemental_pct: tauxDepEffectif,
    }
  }, [surface, residencePrincipale, logementAide, piscine, pvSol, stationnement, eoliennes, tauxCommunal, tauxDepEffectif])

  const calc = useQuery({
    queryKey: ['taxe-calc', params],
    queryFn: () => getTaxeAmenagement(params!),
    enabled: !!params,
  })
  const r: TaxeResult | undefined = calc.data

  if (cfg.isLoading) return <Loading accent="mint" label="Barème…" />
  if (cfg.isError || !cfg.data) return (
    <p className="text-[11px] text-st-ecartee">Barème indisponible — réessayez plus tard.</p>
  )
  const c = cfg.data

  return (
    <div data-taxe-panel className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
      {/* RETOURS-14 S4 — le PREMIER écran ne porte que la parcelle et le calcul : l'intro
          (service-public, CGI…) vit derrière le « i ». */}
      <div className="flex items-center gap-1.5">
        <p className="min-w-0 flex-1 text-[11px] text-txt-mut">Désignez la parcelle du projet :</p>
        <Tip side="bottom" tip={`Estimez la taxe d'aménagement de votre projet avant le dépôt du permis. Valeurs 2026 (arrêté officiel, base CGI art. 1635 quater A et suivants) ; à La Réunion, c'est la valeur forfaitaire hors Île-de-France qui s'applique. Le montant définitif est fixé par l'administration après le permis. Source : ${c.meta.source}.`}>
          <span role="button" tabIndex={0} aria-label="Méthode et sources"
            className="flex h-[15px] w-[15px] shrink-0 items-center justify-center rounded-full border border-line-2 text-[9px] font-bold leading-none text-txt-dim hover:border-mint hover:text-mint">i</span>
        </Tip>
      </div>
      {/* barre UNIQUE (adresse / IDU / référence courte — moteur ParcelInput, comme Étudier un bien) */}
      <ParcelInput dataAttr="taxe-parcelle" withCarte={false} onPick={(i: string) => setPrefillIdu(i)}
        placeholder="Adresse, IDU ou référence (ex. BZ1065)" />
      <p className="text-[10px] text-txt-dim">… ou cliquez une parcelle sur la carte : l'outil la reprend automatiquement.</p>
      {!prefillIdu && (
        <p data-taxe-attente className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11px] leading-snug text-txt-dim">
          Le formulaire s'ouvrira quand une parcelle sera choisie — LABUSE préremplit alors la
          surface taxable avec la SDP constructible au gabarit (modifiable).
        </p>
      )}
      {prefillIdu && (
        <div data-taxe-contexte className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[10.5px] text-txt-mut">
          {prefill.isLoading && <span className="text-txt-dim">Chargement du contexte parcelle…</span>}
          {prefill.isError && <span className="text-st-ecartee">Contexte parcelle indisponible.</span>}
          {prefill.data && (
            <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5">
              <span className="font-mono text-[10px] text-txt-dim">{prefill.data.idu}</span>
              <span className="text-txt">{prefill.data.commune}</span>
              {prefill.data.zone_plu && <span>zone <b className="text-txt">{prefill.data.zone_plu}</b></span>}
              {prefill.data.surface_terrain_m2 != null && (
                <span className="text-txt-dim">terrain : {fmtM2(prefill.data.surface_terrain_m2)} <span className="text-[9px]">(référence)</span></span>
              )}
              {prefill.data.sdp_gabarit_m2 != null && (
                <span className="text-txt-dim">SDP au gabarit : <b className="text-mint">{fmtM2(prefill.data.sdp_gabarit_m2)}</b></span>
              )}
              <button onClick={() => setPrefillIdu(null)} className="ml-auto text-[10px] text-mint hover:underline">retirer</button>
            </div>
          )}
        </div>
      )}

      {/* SAISIE — repliée tant qu'aucune parcelle n'est choisie (S4). */}
      {prefillIdu && (
      <div className="flex flex-col gap-2 rounded-lg border border-line-2 bg-surface-2 p-3">
        <NumField dataAttr="surface" label="Surface taxable" unit="m²" value={surface}
          onChange={(v) => { setSurface(v); setSdpPrefill(false) }}
          hint={`${sdpPrefill
            ? 'Pré-rempli par LABUSE — SDP au gabarit, modifiable (la surface taxable est celle de VOTRE projet). '
            : (prefill.data && prefill.data.sdp_gabarit_m2 == null
              ? `Gabarit non calculable${prefill.data.zone_plu ? ` en zone ${prefill.data.zone_plu}` : ''} — saisissez la surface de votre projet. `
              : '')}Valeur forfaitaire ${fmtEur(c.valeur_forfaitaire_m2.hors_idf)}/m² (hors Île-de-France, DOM inclus).${
            c.exoneration_surface_min_m2 ? ` Surface < ${fmtInt(c.exoneration_surface_min_m2)} m² : exonérée.` : ''}`} />

        <div className="flex flex-col gap-1.5">
          <CheckField dataAttr="residence" label="Résidence principale"
            checked={residencePrincipale} onChange={setResidencePrincipale}
            hint={`Abattement ${fmtInt(c.abattement.taux_pct)} % sur les ${fmtInt(c.abattement.plafond_m2_residence_principale)} premiers m².`} />
          <CheckField dataAttr="aide" label="Logement aidé"
            checked={logementAide} onChange={setLogementAide}
            hint={`Abattement ${fmtInt(c.abattement.taux_pct)} % (logement locatif social / aidé).`} />
        </div>

        {/* FORFAITS OPTIONNELS — installations et aménagements taxés au forfait (barème servi). */}
        <div className="rounded-lg border border-line-2 bg-surface-3/60 p-2">
          <p className="label-caps mb-1.5 text-[9.5px] text-txt-dim">Aménagements au forfait (optionnel)</p>
          <div className="grid grid-cols-2 gap-2">
            <NumField dataAttr="piscine" label="Piscine" unit="m²" value={piscine} onChange={setPiscine}
              hint={`${fmtEur(c.forfaits.piscine_m2)}/m²`} />
            <NumField dataAttr="pv" label="Panneaux PV au sol" unit="m²" value={pvSol} onChange={setPvSol}
              hint={`${fmtEur(c.forfaits.panneau_pv_sol_m2)}/m²`} />
            <NumField dataAttr="stationnement" label="Stationnement ext." unit="places" value={stationnement} onChange={setStationnement}
              hint={`${fmtEur(c.forfaits.stationnement_ext_place)}/place (jusqu’à ${fmtEur(c.forfaits.stationnement_ext_place_max_delib)} sur délibération)`} />
            <NumField dataAttr="eoliennes" label="Éoliennes" unit="mâts" value={eoliennes} onChange={setEoliennes}
              hint={`${fmtEur(c.forfaits.eolienne_mat)}/mât`} />
          </div>
        </div>

        {/* TAUX — communal OBLIGATOIRE (jamais de défaut) · départemental pré-rempli au plafond légal. */}
        <div className="grid grid-cols-2 gap-2">
          <NumField dataAttr="taux-communal" label="Taux communal *" unit="%" value={tauxCommunal} onChange={setTauxCommunal}
            placeholder={`≤ ${fmtInt(c.taux.part_communale_plafond_pct)}`}
            hint={`Obligatoire — voté par la commune (plafond ${fmtInt(c.taux.part_communale_plafond_pct)} %). L’outil ne l’invente pas.`} />
          <NumField dataAttr="taux-departemental" label="Taux départemental" unit="%" value={tauxDepEffectif} onChange={setTauxDepartemental}
            placeholder={depDefaut != null ? String(depDefaut) : undefined}
            hint={`Plafond légal ${depDefaut != null ? depDefaut : '—'} % — à confirmer auprès du département.`} />
        </div>
        {/* RV2-V2 — aide CONCRÈTE pour trouver le taux communal (pas d'open data exploitable).
            RETOURS-11 O4b : repliée par défaut (accordéon <details>). */}
        <details data-taux-aide className="group rounded-md border border-line-2 bg-surface-3/50 text-[10.5px] leading-snug text-txt-mut">
          <summary className="hover-fill flex cursor-pointer list-none items-center gap-1.5 rounded-md px-2.5 py-2 text-txt">
            <span aria-hidden className="text-txt-dim transition-transform duration-quick group-open:rotate-90">›</span>
            <b>Où trouver le taux communal ?</b>
          </summary>
          <div className="px-2.5 pb-2">
            Dans la <b>délibération du conseil municipal fixant le taux de la part communale de la taxe
            d’aménagement</b> (adoptée avant le 1<sup>er</sup> juillet pour l’année suivante). À demander au{' '}
            <b>service urbanisme de la mairie</b>, ou sur le site de la commune (recueil des actes
            administratifs). À défaut de délibération, le taux légal minimal est de 1 %.
          </div>
        </details>
      </div>
      )}

      {/* RÉSULTAT DÉTAILLÉ */}
      {prefillIdu && !params && (
        <p className="text-[11px] text-txt-dim">Saisissez une surface taxable pour estimer la taxe.</p>
      )}
      {calc.isLoading && <p className="text-[11px] text-txt-mut">Calcul…</p>}
      {calc.isError && <p className="text-[11px] text-st-ecartee">Erreur de calcul — vérifiez les valeurs saisies.</p>}

      {r && !calc.isLoading && (
        <div data-taxe-resultat className="flex flex-col gap-2 rounded-lg border border-line-2 bg-surface-1 p-3">
          {/* Détail ligne par ligne — un promoteur doit pouvoir vérifier chaque poste. */}
          <div className="flex flex-col">
            <div className="grid grid-cols-[1fr_auto] gap-x-3 border-b border-line pb-1 text-[9.5px] uppercase tracking-[.08em] text-txt-dim">
              <span>Poste</span><span className="text-right">Assiette</span>
            </div>
            {r.lignes.map((l, i) => (
              <div key={i} data-taxe-ligne className="grid grid-cols-[1fr_auto] gap-x-3 border-b border-line py-1.5 text-[11px]">
                <span className="min-w-0">
                  <span className="text-txt">{l.poste}</span>
                  {/* OUTILS-1 A1/B8 — le produit exact sous chaque poste, en petit mono : l'écran
                      s'auto-vérifie (assiette = somme des postes affichés), par le client comme par un notaire. */}
                  {l.detail && <span className="mt-0.5 block font-mono text-[10px] leading-snug text-txt-dim">{l.detail}</span>}
                </span>
                <span className="text-right font-mono tabular-nums text-txt-mut">{fmtEur(l.assiette_eur)}</span>
              </div>
            ))}
            {/* Assiette totale */}
            <div className="grid grid-cols-[1fr_auto] gap-x-3 py-1.5 text-[12px]">
              <span className="font-medium text-txt-hi">Assiette imposable</span>
              <span className="text-right font-mono font-semibold tabular-nums text-txt-hi">{fmtEur(r.assiette_eur)}</span>
            </div>
          </div>

          {/* Parts + total */}
          <div className="flex flex-col gap-1 rounded-lg border border-line-2 bg-surface-2 p-2.5 text-[11px]">
            <div className="flex items-center justify-between gap-2">
              <span className="text-txt-mut">Part communale <span className="text-txt-dim">({r.taux_communal_pct != null ? `${r.taux_communal_pct} %` : '—'})</span></span>
              <span className="font-mono tabular-nums text-txt">
                {r.part_communale_eur != null ? fmtEur(r.part_communale_eur) : <span className="text-txt-dim">en attente du taux communal</span>}
              </span>
            </div>
            <div className="flex items-center justify-between gap-2">
              <span className="text-txt-mut">
                Part départementale <span className="text-txt-dim">({r.taux_departemental_pct} %{!r.part_departementale_confirmee ? ', à confirmer' : ''})</span>
              </span>
              <span className="font-mono tabular-nums text-txt">
                {r.part_departementale_eur != null ? fmtEur(r.part_departementale_eur) : '—'}
              </span>
            </div>

            {r.total_eur != null ? (
              <div className="mt-1 flex items-center justify-between gap-2 border-t border-line pt-1.5">
                <span className="text-[12.5px] font-semibold text-mint">Total estimé</span>
                <span className="font-mono text-[13px] font-bold tabular-nums text-mint">{fmtEur(r.total_eur)}</span>
              </div>
            ) : (
              // Taux communal absent → PAS de total inventé. Message en évidence, ton neutre/ambre.
              r.taux_communal_manquant && r.message_taux_communal && (
                <div data-taxe-manque className="mt-1 rounded-md border border-st-creuser/40 bg-st-creuser/10 px-2.5 py-1.5 text-[10.5px] leading-snug text-st-creuser">
                  {r.message_taux_communal}
                </div>
              )
            )}
          </div>

          {/* RETOURS-11 O4c : le rappel « estimation indicative » (r.note) est déjà dit dans l'intro
              en tête de page → on ne garde ici que la provenance datée (année + source), non redondante. */}
          <p className="text-[10px] leading-snug text-txt-dim">
            Valeurs {r.annee} —{' '}
            <a href={r.url} target="_blank" rel="noreferrer" className="text-mint hover:underline">{r.source}</a>
          </p>
        </div>
      )}
    </div>
  )
}
