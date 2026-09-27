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
import { Squelette } from '../Loading'
import { ErrorState } from '../States'
import { Case } from '../ui/Case'
import { Chevron } from '../ui/Chevron'

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
      {/* RECETTE-1 R38 — la case « Piscine » (label court) réserve DEUX lignes comme ses voisines
          « Panneaux PV au sol » / « Stationnement ext. » : les champs de la grille 2 colonnes s'alignent. */}
      <span className="label-caps flex min-h-[2.1em] items-start text-[9.5px] leading-tight text-txt-dim">{label}</span>
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
  const cfg = useQuery({ queryKey: ['taxe-config'], queryFn: getTaxeConfig })
  const selectedIdu = useApp((s) => s.selectedIdu)   // parcelle sélectionnée → ouverture « depuis la parcelle »
  const focusParcelle = useApp((s) => s.focusParcelle)   // RETOURS-15 C5 — résolution → zoom + contour + fiche

  // ── saisie ──
  const [surface, setSurface] = useState<number | null>(null)
  const [residencePrincipale, setResidencePrincipale] = useState(false)
  const [logementAide, setLogementAide] = useState(false)
  // TAXE-FIX-1 point 1 — nature du projet EXONÉRÉE de plein droit (CGI 1635 quater D). Une seule
  // nature à la fois (une surface est agricole OU PLAI OU reconstruction) : cases à cocher qui se
  // désélectionnent l'une l'autre. Quand une nature est choisie, la surface saisie devient exonérée.
  const [motifExo, setMotifExo] = useState<'agricole' | 'plai' | 'reconstruction' | null>(null)
  const [piscine, setPiscine] = useState<number | null>(null)
  const [pvSol, setPvSol] = useState<number | null>(null)
  const [stationnement, setStationnement] = useState<number | null>(null)
  const [eoliennes, setEoliennes] = useState<number | null>(null)
  const [tauxCommunal, setTauxCommunal] = useState<number | null>(null)   // OBLIGATOIRE — jamais de défaut
  const [tauxDepartemental, setTauxDepartemental] = useState<number | null>(null)
  const [aideOuverte, setAideOuverte] = useState(false)   // DA-031 — accordéon « Où trouver le taux communal ? »

  // RETOURS-14 S4 — l'outil s'ouvre sur la BARRE UNIQUE (adresse / IDU / référence courte,
  // moteur ParcelInput) + « ou cliquez une parcelle sur la carte » ; un clic carte pendant que
  // l'outil est ouvert ADOPTE la parcelle (selectedIdu suivi en continu — avant, rien ne le
  // disait). Changer de parcelle remet la saisie à zéro (le calcul suit la parcelle).
  const [prefillIdu, setPrefillIdu] = useState<string | null>(selectedIdu)
  useEffect(() => {
    if (selectedIdu && selectedIdu !== prefillIdu) {
      setPrefillIdu(selectedIdu); setSurface(null); setMotifExo(null)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedIdu])
  const prefill = useQuery({
    queryKey: ['taxe-prefill', prefillIdu], queryFn: () => getTaxePrefill(prefillIdu!),
    enabled: !!prefillIdu, retry: false,
  })
  // OUTILS-FIX-2 B1 — la surface taxable n'est JAMAIS pré-remplie d'office (décision recette) : elle
  // reste VIDE. La SDP restante au gabarit reste affichée à côté du champ comme repère, avec un geste
  // « reprendre » pour la copier si l'utilisateur le veut (voir ci-dessous). Jamais copiée d'office.

  // Le taux départemental se pré-remplit avec le PLAFOND LÉGAL servi (part_departementale_defaut) dès
  // que la config arrive — étiqueté « à confirmer », car part_departementale_confirmee_974 est false.
  const depDefaut = cfg.data?.taux.part_departementale_defaut ?? null
  const tauxDepEffectif = tauxDepartemental ?? depDefaut

  // OUTILS-FIX-5 L2 — le taux communal PUBLIC de la parcelle, servi par le prefill (même id que la
  // fiche §7). Quand il existe (24/24 communes), l'outil l'AFFICHE et ne le fait plus saisir : on
  // envoie `insee` au calcul, le back applique le taux public (total chiffré) — plus aucune saisie.
  const insee = prefill.data?.insee ?? null
  const tauxCommunalPublic = prefill.data?.taux_communal_source === 'public'
    ? (prefill.data.taux_communal_pct ?? null) : null
  // TAXE-FIX-1 point 1 — zone A (agricole) mais PAS AU (à urbaniser) : on propose la case
  // « Locaux agricoles » (sans la cocher), car ces locaux y sont exonérés de plein droit.
  const zoneA = /^A(?!U)/i.test(prefill.data?.zone_plu ?? '')

  // Paramètres du calcul — envoyés seulement quand une surface taxable est saisie.
  const params: TaxeParams | null = useMemo(() => {
    if (surface == null || surface <= 0) return null
    // TAXE-FIX-1 point 1 — nature exonérée : la surface saisie part en `surface_exoneree_m2` (0 €)
    // et la part surface taxée tombe à 0. Sinon, comportement inchangé (surface taxée au barème).
    return {
      surface_taxable_m2: motifExo ? 0 : surface,
      surface_exoneree_m2: motifExo ? surface : undefined,
      motif_exoneration: motifExo ?? undefined,
      residence_principale: (!motifExo && residencePrincipale) || undefined,
      logement_aide: (!motifExo && logementAide) || undefined,
      piscine_m2: piscine ?? undefined,
      pv_sol_m2: pvSol ?? undefined,
      stationnement_ext_places: stationnement ?? undefined,
      eoliennes_mats: eoliennes ?? undefined,
      // taux communal : `insee` sert le taux PUBLIC au back ; `taux_communal_pct` reste une
      // correction FACULTATIVE (null par défaut → le back prend le public, source 'public').
      taux_communal_pct: tauxCommunal,
      taux_departemental_pct: tauxDepEffectif,
      insee: insee ?? undefined,
      // TAXE-FIX-1 point 3 — l'IDU permet au back de servir le taux du SECTEUR à taux majoré s'il y en a un.
      idu: prefillIdu ?? undefined,
    }
  }, [surface, motifExo, residencePrincipale, logementAide, piscine, pvSol, stationnement, eoliennes, tauxCommunal, tauxDepEffectif, insee, prefillIdu])

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

  return (
    <div data-taxe-panel className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
      {/* RETOURS-14 S4 — le PREMIER écran ne porte que la parcelle et le calcul : l'intro
          (service-public, CGI…) vit derrière le « i ». */}
      <div className="flex items-center gap-1.5">
        <p className="min-w-0 flex-1 text-[11px] text-txt-mut">Désignez la parcelle du projet :</p>
        <Tip garder side="bottom" tip={`Estimez la taxe d'aménagement de votre projet avant le dépôt du permis. Valeurs 2026 (arrêté officiel, base CGI art. 1635 quater A et suivants) ; à La Réunion, c'est la valeur forfaitaire hors Île-de-France qui s'applique. Le montant définitif est fixé par l'administration après le permis. Source : ${c.meta.source}.`}>
          <span role="button" tabIndex={0} aria-label="Méthode et sources"
            className="flex h-[15px] w-[15px] shrink-0 items-center justify-center rounded-full border border-line-2 text-[9px] font-bold leading-none text-txt-dim hover:border-mint hover:text-mint">i</span>
        </Tip>
      </div>
      {/* barre UNIQUE (adresse / IDU / référence courte — moteur ParcelInput, comme Étudier un bien) */}
      {/* RETOURS-15 C5 — résolution d'adresse → focusParcelle(idu, {fiche}) : zoom + contour + fiche. */}
      <ParcelInput dataAttr="taxe-parcelle" onPick={(i: string) => { setPrefillIdu(i); focusParcelle(i, { fiche: true }) }}
        placeholder="Adresse, IDU ou référence (BW0917)" />
      {!prefillIdu && (
        <p data-taxe-attente className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11px] leading-snug text-txt-dim">
          Le formulaire s'ouvrira quand une parcelle sera choisie — vous saisissez la surface taxable
          de votre projet (surface close et couverte, garages et annexes inclus).
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
              {/* OUTILS-FIX-2 B1 — la SDP au gabarit n'est plus ici : elle sert de repère « reprendre »
                  à côté du champ Surface taxable (source unique). B2 — plus de « retirer » : l'omnibox
                  en tête reste permanente, choisir une autre parcelle remplace. */}
            </div>
          )}
        </div>
      )}

      {/* SAISIE — repliée tant qu'aucune parcelle n'est choisie (S4). */}
      {prefillIdu && (
      <div className="flex flex-col gap-2 rounded-lg border border-line-2 bg-surface-2 p-3">
        {/* TAXE-FIX-1 point 4 — la SURFACE TAXABLE n'est PAS la SDP : c'est la somme des surfaces
            closes et couvertes sous plus de 1,80 m, calculée au nu intérieur des façades, GARAGES
            ET ANNEXES INCLUS (CGI art. 1635 quater H ; la SDP d'urbanisme, elle, les déduit). */}
        {/* RETOURS-15 C5 (P20) — l'outil ne parle QUE de surface taxable : le bloc « SDP restante au
            gabarit… Partir de la SDP du projet » est retiré (la SDP d'urbanisme n'est pas la surface
            taxable, art. 1635 quater H). Le champ reste vide, saisi par l'utilisateur. */}
        <NumField dataAttr="surface" label="Surface taxable" unit="m²" value={surface}
          onChange={(v) => setSurface(v)}
          hint={`Surface close et couverte > 1,80 m, garages et annexes INCLUS (CGI 1635 quater H) — ≠ SDP. Valeur forfaitaire ${fmtEur(c.valeur_forfaitaire_m2.hors_idf)}/m² (hors Île-de-France, DOM inclus).${
            c.exoneration_surface_min_m2 ? ` Surface < ${fmtInt(c.exoneration_surface_min_m2)} m² : exonérée.` : ''}`} />

        <div className="flex flex-col gap-1.5">
          <CheckField dataAttr="residence" label="Résidence principale"
            checked={residencePrincipale} onChange={setResidencePrincipale}
            hint={`Abattement ${fmtInt(c.abattement.taux_pct)} % sur les ${fmtInt(c.abattement.plafond_m2_residence_principale)} premiers m².`} />
          <CheckField dataAttr="aide" label="Logement aidé"
            checked={logementAide} onChange={setLogementAide}
            hint={`Abattement ${fmtInt(c.abattement.taux_pct)} % (logement locatif social / aidé) — PLUS/PLS. Un PLAI est EXONÉRÉ (ci-dessous), pas seulement abattu.`} />
        </div>

        {/* TAXE-FIX-1 point 1 — NATURE DU PROJET : exonérations de plein droit (CGI 1635 quater D).
            Cocher une nature EXONÈRE la surface saisie (0 €), à la différence de l'abattement (−50 %).
            Une seule nature à la fois (cases mutuellement exclusives). En zone A, la case « Locaux
            agricoles » est proposée (non cochée). */}
        <div data-taxe-nature className="flex flex-col gap-1.5 rounded-lg border border-line-2 bg-surface-3/40 p-2">
          <p className="label-caps text-[9.5px] text-txt-dim">Nature du projet — exonération de plein droit (optionnel)</p>
          <CheckField dataAttr="exo-agricole" label="Locaux agricoles"
            checked={motifExo === 'agricole'} onChange={(v) => setMotifExo(v ? 'agricole' : null)}
            hint={`Serres, bâtiments d'exploitation, stockage de récoltes, abris d'animaux — exonérés (CGI 1635 quater D, 3°).${zoneA ? ' Parcelle en zone A : les locaux agricoles y sont exonérés de plein droit.' : ''}`} />
          <CheckField dataAttr="exo-plai" label="Logements PLAI / très sociaux"
            checked={motifExo === 'plai'} onChange={(v) => setMotifExo(v ? 'plai' : null)}
            hint="Prêt locatif aidé d'intégration — exonérés de plein droit (CGI 1635 quater D, 2°). Pour du PLUS/PLS, cocher plutôt « Logement aidé »." />
          <CheckField dataAttr="exo-reconstruction" label="Reconstruction à l'identique"
            checked={motifExo === 'reconstruction'} onChange={(v) => setMotifExo(v ? 'reconstruction' : null)}
            hint="Reconstruction à l'identique d'un bâtiment détruit ou démoli depuis moins de 10 ans, après sinistre (CGI 1635 quater D, 9°)." />
          {motifExo && (
            <p data-taxe-nature-note className="text-[10px] leading-snug text-st-creuser">
              Surface exonérée : la part surface tombe à 0 € (abattements sans effet). Les exonérations
              <b> facultatives</b> votées par délibération communale (CGI 1635 quater E) ne sont pas appliquées ici — à vérifier auprès de la commune.
            </p>
          )}
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

        {/* TAUX — OUTILS-FIX-5 L2 : le taux communal PUBLIC (servi par le prefill, même id que la
            fiche §7) est AFFICHÉ, plus saisi. La saisie manuelle ne réapparaît qu'en repli si la
            commune n'a aucun taux public en base (défensif — les 24 sont peuplées). */}
        <div className="grid grid-cols-2 gap-2">
          {tauxCommunalPublic != null ? (
            <div data-taxe-taux-communal-public className="flex flex-col gap-1">
              <span className="label-caps flex min-h-[2.1em] items-start text-[9.5px] leading-tight text-txt-dim">Taux communal</span>
              <span className="flex items-center gap-1.5 rounded-lg border border-line-2 bg-surface-3 px-2 py-1.5">
                <span className="min-w-0 flex-1 font-mono text-xs tabular-nums text-mint">{tauxCommunalPublic} %</span>
                {/* TAXE-FIX-1 point 3 — secteur à taux majoré : on le DIT, le taux n'est pas le taux général. */}
                <span className={`shrink-0 text-[9px] uppercase tracking-[.06em] ${prefill.data?.secteur_majore ? 'font-semibold text-st-creuser' : 'text-txt-dim'}`}>
                  {prefill.data?.secteur_majore ? 'secteur majoré' : 'public'}
                </span>
              </span>
              <span className="text-[10px] leading-snug text-txt-dim">
                {prefill.data?.secteur_majore
                  ? 'Secteur à taux majoré voté par la commune pour cette parcelle'
                  : 'Voté par la commune'} — {prefill.data?.taux_communal_millesime ?? 'délibération communale'}.
                {prefill.data?.taux_communal_perime && (
                  <span data-taxe-taux-perime className="ml-1 font-medium text-st-creuser">⚠ non rafraîchi depuis plus d'un an.</span>
                )}
              </span>
            </div>
          ) : (
            <NumField dataAttr="taux-communal" label="Taux communal *" unit="%" value={tauxCommunal} onChange={setTauxCommunal}
              placeholder={`≤ ${fmtInt(c.taux.part_communale_plafond_pct)}`}
              hint={`Obligatoire — voté par la commune (plafond ${fmtInt(c.taux.part_communale_plafond_pct)} %). L’outil ne l’invente pas.`} />
          )}
          {/* TAXE-FIX-1 point 4 — le taux départemental 974 (2,5 %) est CONFIRMÉ par DELTA (comme la
              fiche) : on ne dit plus « à confirmer » en dur. On ne le dit que si la config ne l'a pas confirmé. */}
          <NumField dataAttr="taux-departemental" label="Taux départemental" unit="%" value={tauxDepEffectif} onChange={setTauxDepartemental}
            placeholder={depDefaut != null ? String(depDefaut) : undefined}
            hint={`${depDefaut != null ? depDefaut : '—'} %${c.taux.part_departementale_confirmee_974
              ? ' — confirmé (délibération départementale, source DGFiP/DELTA).'
              : ` (plafond légal) — à confirmer auprès du département.`}`} />
        </div>
        {/* RV2-V2 — aide pour trouver le taux communal : n'apparaît qu'en REPLI (taux public absent),
            sinon l'outil sert déjà le taux et la question ne se pose plus. */}
        {tauxCommunalPublic == null && (
        <details data-taux-aide open={aideOuverte}
          onToggle={(e) => setAideOuverte((e.target as HTMLDetailsElement).open)}
          className="group rounded-md border border-line-2 bg-surface-3/50 text-[10.5px] leading-snug text-txt-mut">
          <summary className="hover-fill flex cursor-pointer list-none items-center gap-1.5 rounded-md px-2.5 py-2 text-txt">
            <Chevron open={aideOuverte} />
            <b>Où trouver le taux communal ?</b>
          </summary>
          <div className="px-2.5 pb-2">
            Dans la <b>délibération du conseil municipal fixant le taux de la part communale de la taxe
            d’aménagement</b> (adoptée avant le 1<sup>er</sup> juillet pour l’année suivante). À demander au{' '}
            <b>service urbanisme de la mairie</b>, ou sur le site de la commune (recueil des actes
            administratifs). À défaut de délibération, le taux légal minimal est de 1 %.
          </div>
        </details>
        )}
      </div>
      )}

      {/* RÉSULTAT DÉTAILLÉ */}
      {prefillIdu && !params && (
        <p className="text-[11px] text-txt-dim">Saisissez une surface taxable pour estimer la taxe.</p>
      )}
      {calc.isLoading && <Squelette lignes={3} />}
      {calc.isError && <ErrorState message="Erreur de calcul — vérifiez les valeurs saisies." retry={() => calc.refetch()} />}

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
                {/* RETOURS-15 U6 — la ligne DIT quoi faire, pas un état passif. */}
                {r.part_communale_eur != null ? fmtEur(r.part_communale_eur) : <span className="text-txt-dim">taux non renseigné, saisissez-le ci-dessus</span>}
              </span>
            </div>
            {/* TAXE-AMÉNAGEMENT-1 lot C — taux communal public : millésime affiché (délibération en
                vigueur, source datée) + alerte si non rafraîchi depuis plus d'un an. */}
            {r.taux_communal_source === 'public' && r.taux_communal_millesime && (
              <p data-taxe-millesime className="text-[9.5px] leading-snug text-txt-dim">
                {r.taux_communal_millesime}
                {r.taux_communal_perime && (
                  <span data-taxe-perime className="ml-1 font-medium text-st-creuser">
                    ⚠ taux non rafraîchi depuis plus d'un an — à réingérer
                  </span>
                )}
              </p>
            )}
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
            {/* TAXE-FIX-1 point 2 — redevance d'archéologie préventive : taxe DISTINCTE de la TA,
                0,40 % de la même assiette, souvent due au dépôt du permis. Ligne à part, sous le total. */}
            {r.rap_eur != null && r.assiette_eur > 0 && (
              <div data-taxe-rap className="mt-1 flex items-start justify-between gap-2 border-t border-line pt-1.5">
                <span className="min-w-0 text-txt-mut">
                  Redevance d’archéologie préventive <span className="text-txt-dim">({r.rap_pct} %)</span>
                  <span className="mt-0.5 block text-[9.5px] leading-snug text-txt-dim">Taxe distincte, souvent due avec le permis — {r.rap_source}.</span>
                </span>
                <span className="shrink-0 font-mono tabular-nums text-txt">{fmtEur(r.rap_eur)}</span>
              </div>
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
