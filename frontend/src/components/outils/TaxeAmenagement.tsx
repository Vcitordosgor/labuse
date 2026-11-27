import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  getTaxeAmenagement, getTaxeConfig, getTaxePrefill,
  type VotesTaxe, type LotTaxe, type TaxeParams, type TaxeResult,
} from '../../lib/api'
import { fmtEur, fmtInt } from '../../lib/format'
import { useApp } from '../../store/useApp'
import { EntreeParcelle, type SourceParcelle } from './EntreeParcelle'   // RECETTE-1 F2
import { Tip } from '../Tip'
import { Chargement, Squelette } from '../Loading'
import { ErrorState } from '../States'
import { Case } from '../ui/Case'
import { Chevron } from '../ui/Chevron'

// Keep the user's text while editing. Invalid entries suspend the whole estimate.
function readNumber(raw: string, max: number, integer = false, min = 0) {
  const value = Number(raw.trim().replace(',', '.'))
  const pattern = integer ? /^\d+$/ : /^\d+(?:[.,]\d+)?$/
  if (!raw.trim()) return 0
  return pattern.test(raw.trim()) && value >= min && value <= max ? value : NaN
}

function NumField({ label, value, onChange, unit, hint, dataAttr, max, integer = false, min = 0 }: {
  label: string; value: string; onChange: (v: string) => void
  unit?: string; hint?: string; dataAttr: string; max: number; min?: number; integer?: boolean
}) {
  const invalid = !Number.isFinite(readNumber(value, max, integer, min))
  return (
    <label className="flex min-w-0 flex-col gap-1">
      <span className="text-[11px] font-medium text-txt-mut">{label}</span>
      <span className="flex items-center gap-2 rounded-lg border border-line-2 bg-surface-3 px-2.5 py-2 focus-within:border-mint">
        <input data-taxe-field={dataAttr} type="text" inputMode={integer ? 'numeric' : 'decimal'}
          aria-label={label} aria-invalid={invalid} value={value} placeholder="0"
          onChange={(e) => onChange(e.target.value)}
          className="min-w-0 flex-1 bg-transparent font-mono text-sm text-txt tabular-nums focus:outline-none" />
        <span className="text-[10px] text-txt-dim">{unit}</span>
      </span>
      {invalid && <span role="alert" className="text-[11px] text-st-creuser">Saisissez {integer ? 'un entier' : 'un nombre'} entre {fmtInt(min)} et {fmtInt(max)}.</span>}
      {hint && <span className="text-[10px] leading-snug text-txt-dim">{hint}</span>}
    </label>
  )
}

// RETOURS-27 (pt 4) — pourcentages à la VIRGULE décimale (2,5 % · 0,4 %), jamais le point anglais.
const pc = (v: number | null | undefined) => (v == null ? '—' : `${String(v).replace('.', ',')} %`)
// OUTILS-P1-1 (pt 8) — date ISO (AAAA-MM-JJ) → JJ/MM/AAAA pour la date d'effet / la dernière vérification.
const fmtJMA = (s: string | null | undefined) => (s && /^\d{4}-\d{2}-\d{2}/.test(s) ? s.slice(0, 10).split('-').reverse().join('/') : (s ?? null))

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

export function TaxeAmenagement() {
  const idu = useApp((s) => s.selectedIdu)
  const focus = useApp((s) => s.focusParcelle)
  const select = useApp((s) => s.select)
  const [picked, setPicked] = useState<{ idu: string; source: SourceParcelle } | null>(null)
  return <div data-taxe-panel className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
    <EntreeParcelle picked={idu} source={idu && picked?.idu === idu ? picked.source : idu ? 'carte' : null}
      onChanger={() => { setPicked(null); select(null) }}
      onPick={(i, source) => { setPicked({ idu: i, source }); focus(i, { fiche: true }) }} />
    {idu && <ProjetTaxe key={idu} prefillIdu={idu} />}
  </div>
}

function libelleVotes(votes?: VotesTaxe) {
  const regimes: Record<string, string> = { social: 'logement social éligible', ptz: 'PTZ sur la fraction hors abattement', monument: 'monument historique' }
  return Object.entries(votes ?? {}).filter(([, valeur]) => typeof valeur === 'number' && valeur > 0)
    .map(([nom, valeur]) => `${regimes[nom] ?? nom} ${pc(Number(valeur))}`).join(' · ')
}

function ProjetTaxe({ prefillIdu }: { prefillIdu: string }) {
  const cfg = useQuery({ queryKey: ['taxe-config', prefillIdu], queryFn: () => getTaxeConfig(prefillIdu), refetchInterval: 60_000 })
  const [surface, setSurface] = useState('')
  const [existant, setExistant] = useState('')
  const [collectif, setCollectif] = useState(false)
  const [locaux, setLocaux] = useState<{ categorie: string; surface: string; principale: string }[]>([])
  const [terrain, setTerrain] = useState(false)
  const formules = cfg.data?.formules_locales ?? {}
  const categories = Object.entries(formules).filter(([, f]) => !f.projet_entier)
  const modifierLocal = (i: number, patch: Partial<typeof locaux[number]>) =>
    setLocaux(current => current.map((local, n) => i === n ? { ...local, ...patch } : local))
  const surfaces = locaux.map(local => ({ categorie: local.categorie, surface: readNumber(local.surface, 1_000_000),
    surface_principale: formules[local.categorie]?.seuil_principal_exclusif ? readNumber(local.principale, 1_000_000) : undefined }))
  const surfacesValides = surfaces.every(l => l.surface > 0 && (l.surface_principale === undefined || l.surface_principale > 0))
  const [ptz, setPtz] = useState(false)
  const [monument, setMonument] = useState(false)
  const nouveauLot = () => ({ nombre: '1', surface: '', existant: '', regime: 'rp' as LotTaxe['regime'], monument: false })
  const [groupes, setGroupes] = useState(() => [nouveauLot()])
  const modifierLot = (index: number, patch: Partial<typeof groupes[number]>) =>
    setGroupes(current => current.map((lot, i) => i === index ? { ...lot, ...patch } : lot))
  const lots = groupes.map(lot => ({ ...lot, nombre: readNumber(lot.nombre, 100_000, true, 1),
    surface: readNumber(lot.surface, 1_000_000), existant: readNumber(lot.existant, 1_000_000) }))
  const totalSurface = lots.reduce((s, lot) => s + lot.nombre * lot.surface, 0)
  const lotsValides = lots.every(lot => lot.nombre >= 1 && lot.surface > 0 && Number.isFinite(lot.existant)) && totalSurface <= 1_000_000
  const [usage, setUsage] = useState<'logement' | 'autre'>('logement')
  const [residencePrincipale, setResidencePrincipale] = useState(false)
  const [logementAide, setLogementAide] = useState(false)
  const [optionsOuvertes, setOptionsOuvertes] = useState(false)
  const [piscine, setPiscine] = useState('')
  const [pvSol, setPvSol] = useState('')
  const [stationnement, setStationnement] = useState('')
  const [eoliennes, setEoliennes] = useState('')
  const [tarifPlace, setTarifPlace] = useState('')
  const [tauxManuel, setTauxManuel] = useState('')
  const [motifExo, setMotifExo] = useState<TaxeParams['motif_exoneration']>(null)
  const prefill = useQuery({
    queryKey: ['taxe-prefill', prefillIdu], queryFn: () => getTaxePrefill(prefillIdu!),
    enabled: !!prefillIdu, retry: false,
  })

  const zoneA = prefill.data?.zone_famille === 'A'
  const logement = usage === 'logement'
  const manual = prefill.isSuccess && prefill.data.taux_communal_pct == null
  const created = collectif ? totalSurface : readNumber(surface, 1_000_000)
  const quantities = {
    piscine_m2: readNumber(piscine, 100_000),
    pv_sol_m2: readNumber(pvSol, 1_000_000),
    stationnement_ext_places: readNumber(stationnement, 100_000, true),
    eoliennes_mats: readNumber(eoliennes, 10_000, true),
  }
  const inputs = [created, ...surfaces.map(l => l.surface), ...Object.values(quantities)]
  const existing = collectif ? 0 : readNumber(existant, 1_000_000)
  const rate = manual && tauxManuel.trim() ? readNumber(tauxManuel, 20) : undefined
  const forfaits = cfg.data?.forfaits
  const parkingRate = quantities.stationnement_ext_places > 0 && tarifPlace.trim() && forfaits
    ? readNumber(tarifPlace, forfaits.stationnement_ext_place_max_delib, true, forfaits.stationnement_ext_place)
    : undefined
  const valid = surfacesValides && created + surfaces.reduce((n, l) => n + l.surface, 0) <= 1_000_000 && (!collectif || lotsValides) && [...inputs, existing, rate ?? 0, parkingRate ?? 0].every(Number.isFinite)
  const params: TaxeParams | null = valid && inputs.some(v => v > 0) && prefill.isSuccess ? {
    idu: prefillIdu, surface_taxable_m2: collectif || motifExo ? 0 : created, lots: collectif ? lots : undefined,
    ptz: !collectif && !motifExo && logement && residencePrincipale && !logementAide && ptz,
    surfaces, terrain_rehabilite: terrain,
    monument: !collectif && !motifExo && monument,
    surface_existante_m2: existing,
    surface_exoneree_m2: !collectif && motifExo ? created : undefined, motif_exoneration: collectif ? null : motifExo,
    residence_principale: !collectif && logement && residencePrincipale && !motifExo,
    logement_aide: !collectif && logement && logementAide && !motifExo,
    forfait_stationnement_eur: parkingRate, taux_communal_pct: rate, ...quantities,
  } : null
  const calc = useQuery({
    queryKey: ['taxe-calc', params, cfg.data?.formules_locales, cfg.data?.exonerations_locales?.version, cfg.data?.exonerations_locales?.releve_le],
    queryFn: () => getTaxeAmenagement(params!),
    enabled: !!params,
  })
  const r: TaxeResult | undefined = calc.data

  if (cfg.isLoading) return <Squelette lignes={4} />
  if (cfg.isError || !cfg.data) return (
    <ErrorState message="Barème indisponible — réessayez plus tard." retry={() => cfg.refetch()} />
  )
  const c = cfg.data
  const releve = c.exonerations_locales
  const votes = releve?.communes[prefillIdu.slice(0, 5)]
  const votesDep = releve?.departement
  const communal = libelleVotes(votes)
  const departemental = libelleVotes(votesDep)
  const lignes = r?.lignes ?? []

  return (
    <>
      {prefill.isError && <ErrorState message="Contexte de la parcelle indisponible." retry={() => prefill.refetch()} />}
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
          {/* OUTILS-P1-1 LOT3c (pt 10) — la DÉFINITION de la surface taxable (close+couverte > 1,80 m, garages
              inclus) vit désormais en clair sous le champ (label + exemple) : on ne la répète plus dans le
              « i », qui garde la MÉTHODE et les SOURCES (valeur forfaitaire, base légale, administration). */}
          <Tip garder side="bottom" tip={`Estimez la taxe d'aménagement avant le dépôt du permis. Valeurs ${c.meta.annee} (CGI art. 1635 quater A et s.) ; à La Réunion, c'est la valeur forfaitaire hors Île-de-France qui s'applique (${fmtEur(c.valeur_forfaitaire_m2.hors_idf)}/m²). Le montant définitif est fixé par l'administration. Source : ${c.meta.source}.`}>
            <span role="button" tabIndex={0} aria-label="Méthode et sources"
              className="flex h-[15px] w-[15px] shrink-0 items-center justify-center rounded-full border border-line-2 text-[9px] font-bold leading-none text-txt-dim hover:border-mint hover:text-mint">i</span>
          </Tip>
        </div>

        {manual && <NumField dataAttr="taux" label="Taux communal de la délibération" unit="%" max={20}
          value={tauxManuel} onChange={setTauxManuel} hint="Taux public indisponible. Utilisez le taux applicable au secteur de cette parcelle." />}
        {releve && <div data-taxe-votes className="text-[11px] text-txt-mut">
          {communal ? <><b>Exonérations communales publiées</b> · {communal}.</>
            : 'Aucune exonération facultative communale renseignée par DELTA pour cette parcelle.'}
          {' '}{departemental ? `Exonérations départementales · ${departemental}.` : 'Aucune exonération facultative départementale publiée.'} <a className="text-mint" href={releve.source} target="_blank" rel="noreferrer">DGFiP · relevé du {fmtJMA(releve.releve_le)}</a>
        </div>}
        {categories.length > 0 && <details className="rounded border border-line p-2 text-xs text-txt-mut">
          <summary className="cursor-pointer font-medium">Autres catégories fiscales</summary>
          <p className="my-2">Ajoutez une ligne par local. Ces surfaces s’ajoutent au projet. Saisissez-les une seule fois.</p>
          {locaux.map((local, i) => <fieldset key={i} className="mb-2 grid min-w-0 gap-2 rounded border border-line p-2">
            <legend>Local {i + 1}</legend>
            <label>Catégorie du local
              <select className="block w-full rounded bg-surface-3 p-2" value={local.categorie}
                onChange={e => modifierLocal(i, {categorie: e.target.value, principale: ''})}>
                {categories.map(([id, f]) => <option key={id} value={id}>{f.label}</option>)}
              </select>
            </label>
            <p>{formules[local.categorie]?.condition}</p>
            <NumField label="Surface taxable de ce local" unit="m²" dataAttr="categorie-surface" max={1_000_000}
              value={local.surface} onChange={surface => modifierLocal(i, {surface})} />
            {formules[local.categorie]?.seuil_principal_exclusif && <NumField label="Surface principale totale du magasin" unit="m²" dataAttr="categorie-principale" max={1_000_000}
              value={local.principale} onChange={principale => modifierLocal(i, {principale})} />}
            <button onClick={() => setLocaux(locaux.filter((_, n) => n !== i))}>Retirer le local {i + 1}</button>
          </fieldset>)}
          {locaux.length < 200 && <button className="mb-2 rounded border border-mint/40 px-2 py-1 text-mint" onClick={() =>
            setLocaux([...locaux, {categorie: categories[0][0], surface: '', principale: ''}])}>Ajouter un local</button>}
          {formules.terrain && <CheckField label={formules.terrain.label} hint={formules.terrain.condition} checked={terrain} onChange={setTerrain} />}
          <a href="https://bofip.impots.gouv.fr/bofip/13979-PGP.html/identifiant=BOI-IF-TU-10-20-40-20260826" target="_blank" rel="noreferrer" className="text-mint">Conditions officielles du BOFiP</a>
        </details>}
        <CheckField label="Programme de plusieurs logements" checked={collectif} onChange={setCollectif}
          hint="Regroupez les logements de surface et de régime fiscal identiques." />
        {collectif ? <>
          <p className="text-[11px] text-txt-mut">Indiquez les surfaces par logement, annexes et quote-part des surfaces communes comprises. Ajoutez les aménagements extérieurs une seule fois dans les options.</p>
          {groupes.map((lot, i) => <fieldset key={i} className="grid grid-cols-2 gap-2 rounded-lg border border-line p-2">
            <legend className="px-1 text-xs">Groupe {i + 1}</legend>
            <NumField label="Nombre de logements" dataAttr="lot-nombre" value={lot.nombre} onChange={nombre => modifierLot(i, {nombre})} min={1} max={100_000} integer />
            <NumField label="Surface créée par logement" unit="m²" dataAttr="lot-surface" value={lot.surface} onChange={surface => modifierLot(i, {surface})} max={1_000_000} />
            <NumField label="Existant conservé par logement" unit="m²" dataAttr="lot-existant" value={lot.existant} onChange={existant => modifierLot(i, {existant})} max={1_000_000} />
            <label className="flex min-w-0 flex-col text-[11px]">Régime fiscal
              <select className="min-w-0 rounded bg-surface-3 p-2" value={lot.regime} onChange={e => modifierLot(i, {regime: e.target.value as LotTaxe['regime']})}>
                <option value="rp">Résidence principale</option><option value="ptz">Résidence principale avec PTZ</option>
                <option value="social">Logement social aidé éligible</option><option value="plai">PLAI / LLTS exonéré</option>
                <option value="plein">Taux plein</option>
              </select>
            </label>
            {Boolean(votes?.monument || votesDep?.monument) && <CheckField label="Surface classée ou inscrite" checked={lot.monument} onChange={monument => modifierLot(i, {monument})} />}
            {groupes.length > 1 && <button type="button" onClick={() => setGroupes(groupes.filter((_, n) => n !== i))} className="text-xs text-txt-mut">Retirer le groupe {i + 1}</button>}
          </fieldset>)}
          {groupes.length < 200 && <button className="rounded border border-mint/40 p-2 text-xs text-mint" onClick={() => setGroupes([...groupes, nouveauLot()])}>Ajouter un groupe</button>}
          <p className="text-xs text-txt-mut">{lotsValides ? `Programme · ${lots.reduce((s, lot) => s + lot.nombre, 0)} logements · ${totalSurface.toLocaleString('fr-FR')} m² créés` : 'Renseignez un effectif et une surface positive par groupe (maximum 1 000 000 m² au total).'}</p>
        </> : <>
        {/* OUTILS-P1-1 (pt 8) — le champ NOMME explicitement « Surface taxable (différente de la surface
            de plancher) » et donne un exemple incluant un garage (la surface taxable inclut garages et
            annexes clos et couverts, contrairement à la surface de plancher). */}
        <NumField dataAttr="surface" label="Surface taxable créée (différente de la surface de plancher)" unit="m²" max={1_000_000} value={surface} onChange={setSurface} />
        <p data-taxe-surface-exemple className="text-[10px] leading-snug text-txt-dim">
          Pour une opération soumise à autorisation. Surface close et couverte, sous une hauteur de plafond de plus de 1,80 m — garages et annexes inclus. Ex. : une maison de 100 m² + un garage de 20 m² = 120 m² de surface taxable.
        </p>

        <details className="text-[11px] text-txt-mut">
          <summary className="cursor-pointer">Extension d’un bâtiment existant</summary>
          <NumField dataAttr="existant" label="Surface taxable existante conservée" unit="m²" max={1_000_000}
            value={existant} onChange={setExistant} hint="Pour une résidence principale, l’existant consomme une partie des 100 premiers m²." />
        </details>


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
              hint={`Minore la taxe : abattement de ${fmtInt(c.abattement.taux_pct)} % sur les ${fmtInt(c.abattement.plafond_m2_residence_principale)} premiers m². Pour plusieurs logements, activez le mode programme (CGI 1635 quater I).`} />
            {/* RETOURS-27 (pt 4) — libellé EXACT de l'abattement appliqué. */}
            <CheckField dataAttr="aide" label="Logement social aidé"
              checked={logementAide} onChange={setLogementAide}
              hint={`Abattement ${fmtInt(c.abattement.taux_pct)} % (logement locatif social / aidé, PLUS-PLS).`} />
          </div>
        )}
        {Boolean(votes?.ptz || votesDep?.ptz) && logement && residencePrincipale && !logementAide && !motifExo && <CheckField label="Résidence financée par un PTZ éligible" checked={ptz} onChange={setPtz} />}
        {Boolean(votes?.monument || votesDep?.monument) && !motifExo && <CheckField label="Surface créée entièrement classée ou inscrite" checked={monument} onChange={setMonument}
          hint="En cas de classement partiel, distinguez les surfaces protégées dans la simulation." />}
        </>}
      </div>
      )}

      {/* OPTIONS (repliées par défaut) — aménagements au forfait + exonérations. Entre « Votre projet » et
          le résultat. Mêmes valeurs/calcul qu'avant la refonte ; le résultat se recalcule à chaque changement
          (params dans la deps du useMemo) et la ligne correspondante apparaît dans le détail du résultat. */}
      {prefillIdu && (
      <details data-taxe-options open={optionsOuvertes}
        onToggle={(e) => setOptionsOuvertes((e.target as HTMLDetailsElement).open)}
        className="group rounded-lg border border-line-2 bg-surface-2">
        <summary className="flex cursor-pointer list-none items-center gap-1.5 px-3 py-2 text-[11px] font-medium text-txt-dim marker:hidden hover:text-mint">
          <Chevron open={optionsOuvertes} />Options
          <span className="ml-1 text-[9.5px] font-normal text-txt-dim">aménagements au forfait · exonérations</span>
        </summary>
        <div className="flex flex-col gap-3 px-3 pb-3">
          {/* Aménagements au forfait — barème servi par la config. */}
          <div>
            <p className="label-caps mb-1.5 text-[9.5px] text-txt-dim">Aménagements au forfait</p>
            <div className="grid grid-cols-2 gap-2">
              <NumField integer max={100_000} dataAttr="stationnement" label="Stationnement ext." unit="places" value={stationnement} onChange={setStationnement}
                hint={`${fmtEur(c.forfaits.stationnement_ext_place)}/place (jusqu’à ${fmtEur(c.forfaits.stationnement_ext_place_max_delib)} sur délibération)`} />
              {quantities.stationnement_ext_places > 0 && <NumField dataAttr="tarif-place" label="Forfait voté par place" unit="€"
                integer min={c.forfaits.stationnement_ext_place} max={c.forfaits.stationnement_ext_place_max_delib}
                value={tarifPlace} onChange={setTarifPlace} hint={`Facultatif. Par défaut, ${fmtEur(c.forfaits.stationnement_ext_place)} par place.`} />}
              <NumField max={100_000} dataAttr="piscine" label="Piscine" unit="m²" value={piscine} onChange={setPiscine}
                hint={`${fmtEur(c.forfaits.piscine_m2)}/m²`} />
              <NumField max={1_000_000} dataAttr="pv" label="Panneaux PV au sol" unit="m²" value={pvSol} onChange={setPvSol}
                hint={`${fmtEur(c.forfaits.panneau_pv_sol_m2)}/m²`} />
              <NumField integer max={10_000} dataAttr="eoliennes" label="Éoliennes de plus de 12 m" unit="mâts" value={eoliennes} onChange={setEoliennes}
                hint={`${fmtEur(c.forfaits.eolienne_mat)}/mât`} />
            </div>
          </div>
          {/* Exonérations de plein droit (CGI 1635 quater D) — mutuellement exclusives. */}
          {!collectif && <div className="flex flex-col gap-1.5">
            <p className="label-caps text-[9.5px] text-txt-dim">Exonération de plein droit</p>
            <CheckField dataAttr="exo-agricole" label="Locaux agricoles"
              checked={motifExo === 'agricole'} onChange={(v) => setMotifExo(v ? 'agricole' : null)}
              hint={`Serres, bâtiments d'exploitation, stockage de récoltes, abris d'animaux — exonérés (CGI 1635 quater D, 3°).${zoneA ? ' Zone A : vérifiez l’usage agricole des locaux.' : ''}`} />
            <CheckField dataAttr="exo-plai" label="Logements PLAI / très sociaux"
              checked={motifExo === 'plai'} onChange={(v) => setMotifExo(v ? 'plai' : null)}
              hint="Prêt locatif aidé d'intégration — exonérés de plein droit (CGI 1635 quater D, 2°). Pour du PLUS/PLS, cocher plutôt « Logement social » ci-dessus." />
            <CheckField dataAttr="exo-reconstruction" label="Reconstruction à l'identique"
              checked={motifExo === 'reconstruction'} onChange={(v) => setMotifExo(v ? 'reconstruction' : null)}
              hint="Reconstruction à l'identique d'un bâtiment détruit/démoli depuis moins de 10 ans, après sinistre (CGI 1635 quater D, 9°)." />
            {motifExo && (
              <p data-taxe-nature-note className="text-[10px] leading-snug text-st-creuser">
                Surface exonérée : la part surface tombe à 0 € (abattements sans effet). Les aménagements au forfait sont calculés séparément.
              </p>
            )}
          </div>}
        </div>
      </details>
      )}

      {/* RÉSULTAT — total (gros, vert) · assiette détaillée · parts · archéologie · note. */}
      {prefill.isSuccess && valid && !params && (
        <p className="text-[11px] text-txt-dim">Saisissez la surface créée ou ajoutez un aménagement dans les options.</p>
      )}
      {calc.isLoading && <Squelette lignes={3} />}
      {calc.isError && <ErrorState message="Erreur de calcul — vérifiez les valeurs saisies." retry={() => calc.refetch()} />}

      {params && r && !calc.isLoading && (() => {
        const rap = r.rap_eur != null && r.assiette_eur > 0 ? r.rap_eur : null
        // RETOURS-27 (pt 4) — « Total à prévoir » = Taxe d'aménagement (parts) + Redevance d'archéologie.
        const totalAPrevoir = r.total_eur != null ? r.total_eur + (rap ?? 0) : null
        return (
        <div data-taxe-resultat className="flex flex-col gap-1.5 rounded-lg border border-mint/40 bg-surface-1 p-3">
          {/* TOTAL À PRÉVOIR en tête (gros, vert) — ou message honnête si le taux communal manque. */}
          {totalAPrevoir != null ? (
            <div className="flex items-baseline justify-between gap-2 border-b border-line pb-2">
              <span className="text-[12px] text-txt-mut">Taxe d’aménagement estimée</span>
              <span data-taxe-total data-taxe-ta className="font-mono text-[22px] font-bold tabular-nums text-mint">{fmtEur(r.total_eur)}</span>
            </div>
          ) : r.taux_communal_manquant && r.message_taux_communal ? (
            <div data-taxe-manque className="rounded-md border border-st-creuser/40 bg-st-creuser/10 px-2.5 py-1.5 text-[10.5px] leading-snug text-st-creuser">
              {r.message_taux_communal}
            </div>
          ) : null}

          {/* Assiette — une ligne par poste (surface + forfaits actifs) ; chaque option ajoutée y apparaît. */}
          {lignes.length <= 1 ? (
            <div className="flex items-baseline justify-between gap-2 pt-1 text-[11px]">
              <span className="min-w-0 text-txt-mut">Assiette{lignes[0]?.detail ? <span className="text-txt-dim"> ({lignes[0].detail})</span> : ''}</span>
              <span className="shrink-0 font-mono tabular-nums text-txt">{fmtEur(r.assiette_eur)}</span>
            </div>
          ) : (
            <>
              {lignes.map((l, i) => (
                <div key={i} data-taxe-ligne className="flex items-baseline justify-between gap-2 pt-0.5 text-[11px]">
                  <span className="min-w-0 text-txt-mut">{l.poste}{l.detail ? <span className="text-txt-dim"> ({l.detail})</span> : ''}</span>
                  <span className="shrink-0 font-mono tabular-nums text-txt-dim">{fmtEur(l.assiette_eur)}</span>
                </div>
              ))}
              <div className="flex items-baseline justify-between gap-2 border-t border-line pt-1 text-[11px]">
                <span className="font-medium text-txt-hi">Assiette imposable</span>
                <span className="shrink-0 font-mono font-semibold tabular-nums text-txt-hi">{fmtEur(r.assiette_eur)}</span>
              </div>
            </>
          )}

          {/* Parts (composent la Taxe d'aménagement). OUTILS-P1-1 (pt 8) — CHAQUE taux montre sa SOURCE,
              sa DATE D'EFFET et sa DERNIÈRE VÉRIFICATION, en clair sous la ligne du taux. */}
          {r.exonerations_locales && r.exonerations_locales.base_exoneree_communale > 0 && <p data-taxe-exoneration className="text-xs text-mint">
            Exonération locale · {fmtEur(r.exonerations_locales.base_exoneree_communale)} d’assiette déduits de la part communale.
          </p>}
          {r.exonerations_locales && r.exonerations_locales.base_exoneree_departementale > 0 && <p className="text-xs text-mint">
            Exonération départementale · {fmtEur(r.exonerations_locales.base_exoneree_departementale)} d’assiette déduits de la part départementale.
          </p>}
          {r.part_communale_eur != null && (
            <div>
              <div className="flex items-baseline justify-between gap-2 text-[11px]">
                <span className="text-txt-mut">Part communale <span className="text-txt-dim">· {pc(r.taux_communal_pct)}{r.taux_communal_secteur_majore ? ' (majoré)' : ''}</span></span>
                <span className="shrink-0 font-mono tabular-nums text-txt">{fmtEur(r.part_communale_eur)}</span>
              </div>
              <p data-taxe-prov-communal className="pl-0.5 text-[9px] leading-snug text-txt-dim">
                Source : {r.taux_communal_source === 'public' ? <a className="text-mint hover:underline" href="https://data.economie.gouv.fr/explore/dataset/delta_deliberation_tam_17_01_23/" target="_blank" rel="noreferrer">délibération communale (DGFiP)</a> : 'taux saisi'}
                {r.taux_communal_delib_date ? ` · effet le ${fmtJMA(r.taux_communal_delib_date)}` : ''}
                {r.taux_communal_maj_at ? ` · relevé le ${fmtJMA(r.taux_communal_maj_at)}` : ''}
                {r.taux_communal_perime ? ' · ⚠ non rafraîchi depuis plus d’un an' : ''}
              </p>
            </div>
          )}
          {r.part_departementale_eur != null && (
            <div>
              <div className="flex items-baseline justify-between gap-2 text-[11px]">
                <span className="text-txt-mut">Part départementale <span className="text-txt-dim">· {pc(r.taux_departemental_pct)}{!r.part_departementale_confirmee ? ', à confirmer' : ''}</span></span>
                <span className="shrink-0 font-mono tabular-nums text-txt">{fmtEur(r.part_departementale_eur)}</span>
              </div>
              <p data-taxe-prov-departemental className="pl-0.5 text-[9px] leading-snug text-txt-dim">
                Source : {r.part_departementale_confirmee
                  ? 'Conseil départemental 974 (délibération — plafond légal 2,5 %)'
                  : 'plafond légal CGI art. 1635 quater — taux simulé au plafond, à confirmer'}
                {` · barème ${r.annee}`}
                {c.meta.releve_le ? ` · vérifié le ${fmtJMA(c.meta.releve_le)}` : ''}
              </p>
            </div>
          )}

          {/* RETOURS-27 (pt 4) — le total ventile les DEUX taxes distinctes puis le total à prévoir. */}
          {totalAPrevoir != null && (
            <div className="mt-0.5 flex flex-col gap-1 border-t border-line pt-1.5 text-[11px]">
              {rap != null && (
                <div data-taxe-rap className="flex items-baseline justify-between gap-2">
                  <span className="text-txt">Archéologie préventive si les travaux affectent le sous-sol <span className="text-txt-dim">· {pc(r.rap_pct)}</span></span>
                  <span className="shrink-0 font-mono tabular-nums text-txt">{fmtEur(rap)}</span>
                </div>
              )}
              <div className="flex items-baseline justify-between gap-2 border-t border-line pt-1">
                <span className="font-semibold text-mint">Budget estimé si la taxe d’archéologie s’applique
                  {/* OUTILS-P1-1 (pt 8) — quand le taux départemental est SIMULÉ au plafond (non confirmé),
                      « à confirmer » figure à côté du Total à prévoir, pas seulement sur la ligne du taux. */}
                  {!r.part_departementale_confirmee && (
                    <span data-taxe-total-a-confirmer className="ml-1.5 text-[10px] font-normal text-st-creuser">· à confirmer (taux départemental simulé au plafond)</span>
                  )}
                </span>
                <span className="shrink-0 font-mono font-bold tabular-nums text-mint">{fmtEur(totalAPrevoir)}</span>
              </div>
            </div>
          )}

          {/* RETOURS-27 (pt 4) — note = valeur forfaitaire + taux (virgules décimales) ; « Non pris en
              compte » passe dans le « i » (plus de paragraphe discret). Plus de « exigible au permis ». */}
          <p className="mt-0.5 flex flex-wrap items-center gap-1 border-t border-line pt-1.5 text-[9.5px] leading-snug text-txt-dim">
            <span>Valeur forfaitaire {r.annee} : {fmtEur(r.valeur_forfaitaire_m2)}/m² · taux communal {pc(r.taux_communal_pct)} · taux départemental {pc(r.taux_departemental_pct)}</span>
            {r.non_couvert && r.non_couvert.length > 0 && (
              <Tip garder side="top" tip={`Non pris en compte : ${r.non_couvert.join(' · ')}.`}>
                <span role="button" tabIndex={0} aria-label="Ce qui n'est pas pris en compte"
                  className="flex h-[13px] w-[13px] shrink-0 items-center justify-center rounded-full border border-line-2 text-[8px] font-bold leading-none text-txt-dim hover:border-mint hover:text-mint">i</span>
              </Tip>
            )}
            <a href={r.url} target="_blank" rel="noreferrer" className="text-mint hover:underline">Barème officiel {r.annee}</a>
            {r.taux_communal_perime && <span data-taxe-perime className="font-medium text-st-creuser">⚠ taux non rafraîchi depuis plus d'un an.</span>}
          </p>
        </div>
        )
      })()}
    </>
  )
}
