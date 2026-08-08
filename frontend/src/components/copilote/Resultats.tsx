// M26-B — les parcelles restituées (fin de run UNIQUEMENT — règle 5 : rien pendant).
// Champs du payload `restituees` seuls (arbitrage GO : la carte lead réduite à ce qui
// existe — l'enrichissement article/façade/comparables viendra du mandat M26-A-bis).
// Chaque chiffre porte l'étiquette de l'étape moteur qui l'a produit (règle 1).
// Règle 4 : la ligne « N autres retenues » est TOUJOURS visible quand retenues >
// restituées. Règle 7 : l'indicateur de charge supportable est une INFORMATION sur
// chaque parcelle concernée, jamais un filtre.
import { fmtEurCompact, fmtM2 } from '../../lib/format'
import { fmtInt } from '../../lib/format'
import { ALL_TIER_META } from '../../lib/status'
import { CLIENT } from '../../lib/strings'
import type { RecapAssemblage, Restituee } from '../../lib/copilote'
import { Etiquette } from './ui'

const S = CLIENT.copilote.resultats

// M-Q P7 : ALL_TIER_META (v2 + déclassements) — sinon un tier de déclassement retombait sur le
// repli `?? t` et affichait l'identifiant technique brut au client. Repli neutre, jamais le nom technique.
const tierLabel = (t: string) => ALL_TIER_META[t]?.label ?? '—'

/** Étiquettes par moteur producteur (extraites du fil par l'appelant — payload, pas front). */
export interface EtiquettesMoteurs {
  criblage: string | null
  faisabilite: string | null
  marche_dvf: string | null
  risques: string | null
}

function Stat({ v, l, etiquette }: { v: string; l: string; etiquette: string | null }) {
  return (
    <div>
      <div className="font-display text-[15px] font-bold tabular-nums text-cp-txt">{v}</div>
      <div className="mt-0.5 flex items-center gap-1.5 text-[9.5px] uppercase tracking-[.1em] text-cp-faint">
        {l}{etiquette && <Etiquette v={etiquette} />}
      </div>
    </div>
  )
}

/** Charge ≤ 0 = opération non viable même à foncier gratuit : cas d'affichage à part
 *  entière (décision produit, revue B). Jamais masqué, jamais un montant nu — la valeur
 *  brute reste visible, le sens est donné. La parcelle reste restituée (règle 7). */
const estNonViable = (p: Restituee) => p.charge_fonciere_eur != null && p.charge_fonciere_eur <= 0

function FlagCharge({ p }: { p: Restituee }) {
  const nonViable = estNonViable(p)
  return (
    <div data-charge-flag={nonViable ? 'non-viable' : 'au-dessus'}
      className="mt-2.5 flex items-start gap-2 rounded-xl border border-cp-amber/30 bg-cp-amber/10 px-3 py-2 text-[10.5px] leading-relaxed text-cp-amber">
      <span aria-hidden className="mt-px shrink-0">▲</span>
      <span>{nonViable
        ? S.chargeNonViable(fmtEurCompact(p.charge_fonciere_eur))
        : S.chargeFlag(fmtEurCompact(p.charge_fonciere_eur))}</span>
    </div>
  )
}

function Lead({ p, et }: { p: Restituee; et: EtiquettesMoteurs }) {
  return (
    <div data-restituee={p.idu} className="grid grid-cols-1 gap-4 border-b border-cp-line px-5 py-4 md:grid-cols-[1fr_230px]">
      <div>
        <div>
          <span className="rounded-md bg-cp-mint px-2 py-0.5 font-display text-[10px] font-bold tracking-wide text-[#08130E]">#01</span>
          <span className="ml-2.5 font-display text-lg font-bold text-cp-txt">{p.idu}</span>
        </div>
        <div className="mt-1 text-[11.5px] text-cp-faint">{p.commune}</div>
        {p.zone && (
          <div className="mt-3 flex flex-wrap gap-2">
            <span className="rounded-lg border border-cp-mint/25 bg-cp-mint/10 px-2.5 py-1 font-display text-[11px] font-semibold text-cp-mint">
              Zone {p.zone}
            </span>
          </div>
        )}
        <div className="mt-3.5 flex flex-wrap gap-6">
          {p.sdp_m2 != null && et.faisabilite && (
            <Stat v={fmtM2(p.sdp_m2)} l={S.sdp} etiquette={et.faisabilite} />)}
          <Stat v={fmtM2(p.surface_m2)} l={S.surface} etiquette={et.criblage} />
          {et.risques && (
            <Stat v={fmtInt(p.n_signaux_risques)} l={S.signauxRisques(p.n_signaux_risques)} etiquette={et.risques} />)}
        </div>
      </div>
      <div className="border-cp-line md:border-l md:pl-5">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-md border border-cp-tier/30 bg-cp-tier/10 px-2.5 py-1 font-display text-[9.5px] font-bold uppercase tracking-[.16em] text-cp-tier">
            {S.tier} · {tierLabel(p.tier)}
          </span>
          {/* pastille budget : la mention du payload, verbatim, toujours affichée */}
          {p.budget && (
            <span data-budget className="rounded-md border border-cp-line2 bg-cp-card2 px-2 py-1 font-display text-[9px] font-semibold uppercase tracking-[.1em] text-cp-muted">
              {p.budget}
            </span>
          )}
        </div>
        {/* prix probable et charge supportable CÔTE À CÔTE — l'arbitrage est là */}
        {et.marche_dvf && (p.prix_probable_eur != null || p.charge_fonciere_eur != null) && (
          <div className="mt-3 flex flex-wrap gap-5">
            {p.prix_probable_eur != null && (
              <div>
                <div className="font-display text-[26px] font-bold tabular-nums leading-none tracking-tight text-cp-txt">
                  {fmtEurCompact(p.prix_probable_eur)}
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[10px] text-cp-faint">
                  {S.prixProbable} <Etiquette v={et.marche_dvf} />
                </div>
              </div>
            )}
            {p.charge_fonciere_eur != null && (
              <div data-charge-supportable>
                <div className={`font-display text-[26px] font-bold tabular-nums leading-none tracking-tight ${
                  p.au_dessus_charge_supportable ? 'text-cp-amber' : 'text-cp-txt'}`}>
                  {fmtEurCompact(p.charge_fonciere_eur)}
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[10px] text-cp-faint">
                  {S.chargeSupportable} <Etiquette v={et.marche_dvf} />
                </div>
              </div>
            )}
          </div>
        )}
        {(p.au_dessus_charge_supportable || estNonViable(p)) && <FlagCharge p={p} />}
      </div>
    </div>
  )
}

function Ligne({ p, i, et }: { p: Restituee; i: number; et: EtiquettesMoteurs }) {
  return (
    <div data-restituee={p.idu}
      className="grid grid-cols-[52px_minmax(0,1fr)_auto] items-center gap-3 border-b border-cp-line px-5 py-3 last:border-none md:grid-cols-[52px_150px_minmax(0,1fr)_auto]">
      <div className="rounded-md border border-cp-line2 bg-cp-card2 py-0.5 text-center font-display text-[10px] font-bold text-cp-muted">
        #{String(i + 1).padStart(2, '0')}
      </div>
      <div className="min-w-0">
        <div className="truncate font-display text-[12.5px] font-semibold text-cp-txt">{p.idu}</div>
        <div className="truncate text-[11px] text-cp-faint">{p.commune}</div>
      </div>
      <div className="hidden flex-wrap items-center gap-2 md:flex">
        {p.zone && <span className="rounded-lg border border-cp-line2 bg-cp-card2 px-2 py-0.5 font-display text-[10.5px] font-semibold text-cp-muted">{p.zone}</span>}
        {p.sdp_m2 != null && et.faisabilite && (
          <span className="flex items-center gap-1.5 rounded-lg border border-cp-line2 bg-cp-card2 px-2 py-0.5 font-display text-[10.5px] font-semibold text-cp-muted">
            SDP {fmtM2(p.sdp_m2)} <Etiquette v={et.faisabilite} />
          </span>
        )}
        {estNonViable(p) ? (
          <span data-charge-flag="non-viable"
            className="rounded-lg border border-cp-amber/30 bg-cp-amber/10 px-2 py-0.5 text-[10px] text-cp-amber">
            ▲ {S.chargeNonViableCourt(fmtEurCompact(p.charge_fonciere_eur))}
          </span>
        ) : p.au_dessus_charge_supportable ? (
          <span data-charge-flag="au-dessus"
            className="rounded-lg border border-cp-amber/30 bg-cp-amber/10 px-2 py-0.5 text-[10px] text-cp-amber">
            ▲ {S.chargeSupportableCourt(fmtEurCompact(p.charge_fonciere_eur))}
          </span>
        ) : null}
        {p.budget && p.budget !== 'dans le budget' && (
          <span className="text-[10px] text-cp-muted">{p.budget}</span>
        )}
      </div>
      <div className="text-right">
        {p.prix_probable_eur != null && et.marche_dvf ? (
          <div className="flex items-center justify-end gap-1.5">
            <span className="font-display text-[13.5px] font-bold tabular-nums text-cp-txt">
              {fmtEurCompact(p.prix_probable_eur)}
            </span>
            <Etiquette v={et.marche_dvf} />
          </div>
        ) : null}
        <div className="font-display text-[9px] font-bold uppercase tracking-[.1em] text-cp-tier">
          {tierLabel(p.tier)}
        </div>
      </div>
    </div>
  )
}

export function Resultats({ recap, titre, etiquettes }: {
  recap: RecapAssemblage
  titre: string
  etiquettes: EtiquettesMoteurs
}) {
  const liste = recap.restituees ?? []
  const idus = recap.restituees_idu ?? []
  const nAutres = recap.n_retenues - recap.n_restituees
  return (
    <div data-resultats className="overflow-hidden rounded-2xl border border-cp-line bg-cp-card">
      <div className="flex flex-wrap items-center gap-3 border-b border-cp-line px-5 py-3.5">
        <h3 className="font-display text-[13.5px] font-semibold text-cp-txt">{titre}</h3>
      </div>
      {liste.length > 0 && <Lead p={liste[0]} et={etiquettes} />}
      {liste.slice(1).map((p, i) => <Ligne key={p.idu} p={p} i={i + 1} et={etiquettes} />)}
      {/* mission shortlist (assemblage_court) : le payload ne porte que les IDU */}
      {liste.length === 0 && idus.map((idu, i) => (
        <div key={idu} data-restituee={idu}
          className="flex items-center gap-3 border-b border-cp-line px-5 py-3 last:border-none">
          <div className="w-[52px] rounded-md border border-cp-line2 bg-cp-card2 py-0.5 text-center font-display text-[10px] font-bold text-cp-muted">
            #{String(i + 1).padStart(2, '0')}
          </div>
          <div className="font-display text-[12.5px] font-semibold text-cp-txt">{idu}</div>
        </div>
      ))}
      {/* règle 4 : jamais laisser croire que top-20 = tout (pas de bouton « liste
          complète » — le back ne restitue que le top-N, arbitrage GO) */}
      {nAutres > 0 && (
        <div data-autres-retenues
          className="flex items-center border-t border-cp-line bg-white/[0.015] px-5 py-3.5 text-[11.5px] text-cp-muted">
          <span>
            <b className="font-semibold text-cp-txt">{fmtInt(nAutres)} {S.autresRetenuesFort}</b>
            {S.autresRetenuesSuite(recap.n_restituees)}
          </span>
        </div>
      )}
    </div>
  )
}
