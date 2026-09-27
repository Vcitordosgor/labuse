// RADAR-2 (Lot 4) — LA VEILLE, trois écrans plein écran (SANS carte), derrière la porte « Veille » du
// hub Radar : les deux portes (Le foncier / Les annonces) + le réglage du mail ; les parcelles suivies ;
// les alertes. Le réglage du mail partage LA MÊME source que Mon compte (VEILLE-FIX-2, /events/prefs).
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  ApiError, creerRadarVeille, getNotifPrefs, getRadarAlertes, getRadarApercu, getSuivis,
  patchDigestFrequence, pauseRadarVeille, supprimerRadarVeille, toggleWatch,
  type RadarAlerte,
} from '../../lib/api'
import { useApp } from '../../store/useApp'
import { iduCourt } from '../../lib/format'
import { CP_COMMUNES } from '../panel/FiltreLabuse'
import { trierCommunes } from '../../lib/communes'
import { ParcelInput } from '../ParcelInput'
import { Squelette } from '../Loading'
import { EmptyState } from '../States'
import { Badge } from '../ui/Badge'
import { Bouton } from '../ui/Bouton'
import { Retour } from '../ui/Retour'
import { EcranTete, PorteCard } from './RadarHub'

// icônes des portes Veille (bouclier / maison)
const IcoBouclier = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round">
    <path d="M12 3l7 3v5c0 4.4-3 7.6-7 9-4-1.4-7-4.6-7-9V6z" />
  </svg>
)
const IcoMaison = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round">
    <path d="M4 11l8-6 8 6" /><path d="M6 10v9h12v-9" />
  </svg>
)

// fréquence du mail — mêmes valeurs que Mon compte (VEILLE-FIX-2). Libellés de la maquette.
const FREQ_LABEL: Record<string, string> = { quotidien: 'Chaque matin', hebdo: 'Chaque lundi', cloche_seule: 'Seulement dans la cloche' }
const FREQ_ORDRE = ['quotidien', 'hebdo', 'cloche_seule']

// RADAR-2 (retouches 2) — création d'une alerte DANS la Veille (le formulaire vit ici, plus dans Radar).
const COMMUNES_24 = trierCommunes(CP_COMMUNES.map(([, nom]) => nom), (n) => n)
const TYPES_ALERTE = [['', 'Tous'], ['terrain', 'Terrain'], ['maison', 'Maison']] as const
const VENDEURS_ALERTE = [['', 'Tous'], ['particulier', 'Particulier']] as const

// ══════════════ VEILLE — les deux portes + le réglage du mail ══════════════
export function VeillePortes() {
  const setRadarEcran = useApp((s) => s.setRadarEcran)
  const qc = useQueryClient()
  const { data } = useQuery({ queryKey: ['radar-apercu'], queryFn: getRadarApercu })
  const prefs = useQuery({ queryKey: ['notif-prefs'], queryFn: getNotifPrefs })
  const freq = prefs.data?.frequence ?? 'quotidien'
  const frequences = prefs.data?.frequences?.length ? prefs.data.frequences : FREQ_ORDRE
  const setFreq = useMutation({
    mutationFn: (v: string) => patchDigestFrequence(v),
    onMutate: (v) => { qc.setQueryData(['notif-prefs'], (p: { frequence: string } | undefined) => (p ? { ...p, frequence: v } : p)) },
    onSettled: () => qc.invalidateQueries({ queryKey: ['notif-prefs'] }),
  })
  const suivis = data?.suivis_n ?? 0
  const alertes = data?.alertes_n ?? 0
  const nouveaux = data?.nouveaux_total ?? 0
  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
     <div className="mx-auto w-full max-w-[1060px] px-8 py-10">
      <EcranTete surtitre="VEILLE" titre="Choisissez ce que vous voulez surveiller"
        retour={<Retour label="Radar" data-veille-retour-radar onClick={() => setRadarEcran('portes')} />} />
      <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
        <PorteCard data="veille-porte-foncier" ic={<IcoBouclier />} titre="Le foncier"
          desc="Vos parcelles suivies : vente, permis, changement de propriétaire, mise en vente sur un portail."
          resume={<>{suivis} parcelle{suivis > 1 ? 's' : ''} suivie{suivis > 1 ? 's' : ''}</>}
          onClick={() => setRadarEcran('veille-foncier')} />
        <PorteCard data="veille-porte-annonces" ic={<IcoMaison />} titre="Les annonces"
          desc="Vos alertes Radar : une nouvelle annonce, une baisse de prix ou un retour, selon vos critères."
          resume={<>{alertes} alerte{alertes > 1 ? 's' : ''} · {nouveaux} nouveau{nouveaux > 1 ? 'x' : ''} bien{nouveaux > 1 ? 's' : ''}</>}
          onClick={() => setRadarEcran('veille-annonces')} />
      </div>

      {/* réglage du mail — une seule source (Mon compte) */}
      <div className="mt-6 flex flex-wrap items-center justify-between gap-4 rounded-lg border border-line-2 bg-surface-2 px-6 py-4">
        <span className="text-[13px] text-txt">Recevoir le résumé par mail</span>
        <div className="flex flex-wrap gap-2">
          {frequences.map((v) => (
            <button key={v} data-veille-freq={v} onClick={() => setFreq.mutate(v)}
              className={`h-8 rounded-full border px-3.5 text-[12.5px] transition-colors duration-quick ${
                freq === v ? 'border-mint bg-mint text-mint-on font-medium' : 'border-line-2 text-txt hover:border-mint/50'}`}>
              {freq === v && <span className="mr-1">✓</span>}{FREQ_LABEL[v] ?? v}
            </button>
          ))}
        </div>
      </div>
     </div>
    </div>
  )
}

// ══════════════ VEILLE · LE FONCIER — les parcelles suivies ══════════════
export function VeilleFoncier() {
  const { setRadarEcran, focusParcelle } = useApp()
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['suivis'], queryFn: getSuivis })
  const suivis = q.data?.suivis ?? []
  const [msg, setMsg] = useState<string | null>(null)
  const suivre = useMutation({
    mutationFn: (idu: string) => toggleWatch(idu),
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ['suivis'] }); qc.invalidateQueries({ queryKey: ['watch'] })
      qc.invalidateQueries({ queryKey: ['radar-apercu'] })
      setMsg(r.watched ? '✓ Parcelle ajoutée au suivi.' : 'Parcelle retirée du suivi.')
    },
    onError: (err) => setMsg(err instanceof ApiError && err.detail ? err.detail : 'Impossible de suivre cette parcelle.'),
  })
  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
     <div className="mx-auto w-full max-w-[1060px] px-8 py-10">
      <EcranTete surtitre="VEILLE · LE FONCIER" titre="Vos parcelles suivies"
        sous="Ajoutez une parcelle ici, ou avec la cloche de sa fiche."
        retour={<Retour label="Veille" data-veille-retour onClick={() => setRadarEcran('veille')} />} />
      <div className="mb-4 max-w-[560px]">
        {/* RADAR-2 (retouches 2) — pas de carte sur cette page : `withCarte={false}` retire l'invite
            « ou cliquez une parcelle sur la carte » (et le geste clic-carte, sans objet ici). */}
        <ParcelInput dataAttr="veille-parcelle" placeholder="Adresse, IDU ou référence (BW0917)" withCarte={false}
          onPick={(idu) => suivre.mutate(idu)}
          onAddress={() => setMsg("Cette adresse n'a pas de parcelle rattachée — précisez un IDU pour la suivre.")} />
        {msg && <p className="mt-1.5 text-[11px] text-txt-mut">{msg}</p>}
      </div>

      {q.isLoading && <Squelette lignes={4} />}
      {!q.isLoading && suivis.length === 0 && (
        <EmptyState className="rounded-lg border border-dashed border-line-2"
          title="Aucune parcelle suivie."
          hint={<>Ajoutez-en une ci-dessus, ou ouvrez une fiche et cliquez la <b className="text-txt">cloche « Suivre »</b>.</>} />
      )}
      {suivis.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-line-2">
          <table className="w-full border-collapse text-[12.5px]">
            <thead>
              <tr className="border-b border-line-2 bg-surface-2 font-mono text-[9.5px] uppercase tracking-wider text-txt-dim">
                <th className="px-4 py-2.5 text-left">Parcelle</th><th className="px-2 py-2.5 text-left">Commune</th>
                <th className="px-2 py-2.5 text-left">Secteur</th><th className="px-2 py-2.5 text-left">Dernier événement</th>
                <th className="px-2 py-2.5 text-left">Date</th><th className="px-4 py-2.5" />
              </tr>
            </thead>
            <tbody>
              {suivis.map((s) => (
                <tr key={s.idu} data-suivi className="border-b border-line-2 last:border-0">
                  <td className="px-4 py-3">
                    <button data-suivi-idu onClick={() => focusParcelle(s.idu, { fiche: true })}
                      className="font-mono text-[12px] text-mint underline decoration-mint/40 underline-offset-2 hover:decoration-mint">
                      {iduCourt(s.idu)}
                    </button>
                  </td>
                  <td className="px-2 py-3 text-txt">{s.commune ?? '—'}</td>
                  <td className="px-2 py-3 text-txt-mut">{s.secteur ?? '—'}</td>
                  <td className="px-2 py-3">
                    {s.dernier_evenement ? (
                      <span className="inline-flex items-center gap-1.5">
                        <span className={s.nouveau ? 'text-mint' : 'text-txt'}>{s.dernier_evenement}</span>
                        {s.nouveau && <Badge ton="vert">Nouveau</Badge>}
                      </span>
                    ) : <span className="text-txt-dim">Rien depuis le début du suivi</span>}
                  </td>
                  <td className="px-2 py-3 tabular-nums text-txt-mut">{s.dernier_changement ? new Date(s.dernier_changement).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' }) : '—'}</td>
                  <td className="px-4 py-3 text-right">
                    <Bouton niveau="secondaire" ton="vert" data-suivi-retirer onClick={() => suivre.mutate(s.idu)}>Ne plus suivre</Bouton>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="mt-4 text-[11px] leading-relaxed text-txt-dim">
        Surveillé pour chaque parcelle : vente (DVF), permis (Sitadel), changement de propriétaire (société, DGFiP),
        mise en vente sur un portail (mail immédiat).
      </p>
     </div>
    </div>
  )
}

// criteria → chips (pour l'affichage d'une alerte)
function alerteChips(a: RadarAlerte): string[] {
  const c = a.criteria as Record<string, unknown>
  const out: string[] = []
  if (c.type_bien) out.push(String(c.type_bien).charAt(0).toUpperCase() + String(c.type_bien).slice(1))
  const communes = Array.isArray(c.communes) ? (c.communes as string[]) : (a.commune ? [String(a.commune)] : [])
  if (communes.length) out.push(communes.join(' · '))
  if (c.surface_min) out.push(`≥ ${Number(c.surface_min)} m²`)
  if (c.prix_max) out.push(`≤ ${Number(c.prix_max).toLocaleString('fr-FR')} €`)
  if (c.particulier_only) out.push('Particulier')
  return out.length ? out : ['Tous les biens']
}

// criteria → RadarFiltres (pour « Voir dans Radar »)
function alerteVersFiltres(a: RadarAlerte): Record<string, unknown> {
  const c = a.criteria as Record<string, unknown>
  const communes = Array.isArray(c.communes) ? (c.communes as string[]) : []
  return {
    commune: communes.length === 1 ? communes[0] : (a.commune ?? undefined),
    type_bien: c.type_bien ?? undefined,
    prix_max: c.prix_max ?? undefined, prix_min: c.prix_min ?? undefined,
    surface_terrain_min: c.surface_min ?? undefined,
    particulier_pro: c.particulier_only ? 'particulier' : undefined,
  }
}

// RADAR-2 (retouches 2) — le FORMULAIRE de création d'alerte, dans la Veille (commune(s), type, prix max,
// surface min, vendeur). Au moins une commune OU un type est exigé ; le refus d'un doublon (message du
// serveur, HTTP 409) et l'erreur de validation s'affichent sous le formulaire.
function FormulaireAlerte({ onCreee, onAnnuler }: { onCreee: () => void; onAnnuler: () => void }) {
  const [communes, setCommunes] = useState<string[]>([])
  const [ajout, setAjout] = useState('')
  const [type, setType] = useState('')
  const [prixMax, setPrixMax] = useState('')
  const [surfMin, setSurfMin] = useState('')
  const [vendeur, setVendeur] = useState('')
  const [msg, setMsg] = useState<string | null>(null)
  const inp = 'h-8 rounded-md border border-line-2 bg-surface-1 px-2.5 text-[12.5px] text-txt focus:border-mint focus:outline-none'

  const creer = useMutation({
    mutationFn: () => creerRadarVeille({
      communes: communes.length ? communes : undefined,
      type_bien: type || undefined,
      prix_max: prixMax ? Number(prixMax) : undefined,
      surface_min: surfMin ? Number(surfMin) : undefined,
      particulier_only: vendeur === 'particulier' || undefined,
    }),
    onSuccess: onCreee,
    onError: (err) => setMsg(err instanceof ApiError && err.detail ? err.detail : "Impossible de créer l'alerte."),
  })
  const soumettre = () => {
    // au moins une commune OU un type (une alerte « tous biens de l'île » n'a pas de sens ici).
    if (!communes.length && !type) { setMsg('Choisissez au moins une commune ou un type de bien.'); return }
    setMsg(null); creer.mutate()
  }
  const ajouterCommune = (c: string) => { if (c && !communes.includes(c)) setCommunes((p) => [...p, c]); setAjout('') }

  return (
    <div data-veille-form className="mb-6 rounded-lg border border-mint/40 bg-mint/[0.04] px-5 py-4">
      <div className="mb-3 text-[13px] font-semibold text-txt-hi">Nouvelle alerte</div>
      {/* commune(s) — on ajoute une commune à la fois, chips retirables */}
      <div className="mb-3">
        <label className="mb-1 block text-[11px] text-txt-dim">Commune(s)</label>
        <div className="flex flex-wrap items-center gap-2">
          {communes.map((c) => (
            <span key={c} data-veille-form-commune className="inline-flex items-center gap-1 rounded-full bg-mint/12 px-2.5 py-1 text-[11.5px] text-mint">
              {c}
              <button aria-label={`Retirer ${c}`} onClick={() => setCommunes((p) => p.filter((x) => x !== c))} className="text-mint/70 hover:text-mint">✕</button>
            </span>
          ))}
          <select data-veille-form-ajout-commune value={ajout} onChange={(e) => ajouterCommune(e.target.value)} className={`${inp} min-w-[170px]`}>
            <option value="">+ Ajouter une commune…</option>
            {COMMUNES_24.filter((c) => !communes.includes(c)).map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Segment label="Type" value={type} onChange={setType} options={TYPES_ALERTE} data="veille-form-type" />
        <Segment label="Vendeur" value={vendeur} onChange={setVendeur} options={VENDEURS_ALERTE} data="veille-form-vendeur" />
        <input data-veille-form-prix type="number" min={0} placeholder="Prix max" value={prixMax} onChange={(e) => setPrixMax(e.target.value)} className={`${inp} w-[120px]`} />
        <input data-veille-form-surface type="number" min={0} placeholder="Surface min" value={surfMin} onChange={(e) => setSurfMin(e.target.value)} className={`${inp} w-[120px]`} />
      </div>
      {msg && <p data-veille-form-msg className="mt-2.5 text-[11.5px] text-amber">{msg}</p>}
      <div className="mt-3.5 flex items-center gap-2">
        <Bouton niveau="primaire" ton="vert" data-veille-form-creer disabled={creer.isPending} onClick={soumettre}>Créer l’alerte</Bouton>
        <Bouton niveau="secondaire" ton="vert" data-veille-form-annuler onClick={onAnnuler}>Annuler</Bouton>
      </div>
    </div>
  )
}

// petit sélecteur segmenté (repris de l'écran Radar), pour Type / Vendeur du formulaire d'alerte.
function Segment({ label, value, onChange, options, data }: {
  label: string; value: string; onChange: (v: string) => void; options: readonly (readonly [string, string])[]; data: string
}) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-[11px] text-txt-dim">{label}</span>
      <div data-seg={data} className="flex h-8 overflow-hidden rounded-md border border-line-2">
        {options.map(([v, l], i) => (
          <button key={v || 'tous'} data-seg-opt={v || 'tous'} onClick={() => onChange(v)}
            className={`flex items-center justify-center whitespace-nowrap px-2.5 text-[12px] ${i ? 'border-l border-line-2' : ''} ${value === v ? 'bg-mint/12 font-medium text-mint' : 'text-txt-mut hover:text-txt'}`}>{l}</button>
        ))}
      </div>
    </div>
  )
}

// ══════════════ VEILLE · LES ANNONCES — les alertes ══════════════
export function VeilleAnnonces() {
  const { setRadarEcran, setRadarPrefill } = useApp()
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['radar-alertes'], queryFn: getRadarAlertes })
  const alertes = q.data?.alertes ?? []
  const [formOuvert, setFormOuvert] = useState(false)
  const inval = () => { qc.invalidateQueries({ queryKey: ['radar-alertes'] }); qc.invalidateQueries({ queryKey: ['radar-apercu'] }) }
  const pause = useMutation({ mutationFn: ({ id, p }: { id: number; p: boolean }) => pauseRadarVeille(id, p), onSuccess: inval })
  const suppr = useMutation({ mutationFn: (id: number) => supprimerRadarVeille(id), onSuccess: inval })
  const voirDansRadar = (a: RadarAlerte) => { setRadarPrefill(alerteVersFiltres(a)); setRadarEcran('radar') }

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
     <div className="mx-auto w-full max-w-[1060px] px-8 py-10">
      <div className="mb-6 flex items-start justify-between gap-4">
        <EcranTete surtitre="VEILLE · LES ANNONCES" titre="Vos alertes"
          sous="Une nouvelle annonce, une baisse de prix ou un retour, selon vos critères."
          retour={<Retour label="Veille" data-veille-retour onClick={() => setRadarEcran('veille')} />} />
        <Bouton niveau="primaire" ton="vert" data-veille-nouvelle-alerte className="mt-10 shrink-0" onClick={() => setFormOuvert((v) => !v)}>
          + Nouvelle alerte
        </Bouton>
      </div>

      {formOuvert && <FormulaireAlerte onCreee={() => { inval(); setFormOuvert(false) }} onAnnuler={() => setFormOuvert(false)} />}

      {q.isLoading && <Squelette lignes={3} />}
      {!q.isLoading && alertes.length === 0 && (
        <EmptyState className="rounded-lg border border-dashed border-line-2"
          title="Aucune alerte." hint={<>Cliquez <b className="text-txt">« + Nouvelle alerte »</b> pour surveiller des annonces selon vos critères.</>} />
      )}
      <div className="flex flex-col gap-3">
        {alertes.map((a) => (
          <div key={a.id} data-veille-alerte className="rounded-lg border border-line-2 bg-surface-2 px-5 py-4">
            <div className="flex flex-wrap items-center gap-1.5">
              {alerteChips(a).map((chip, i) => <Badge key={i} ton="neutre">{chip}</Badge>)}
            </div>
            <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-3 text-[12px]">
                <span className={a.en_pause ? 'text-amber' : a.nouveaux > 0 ? 'text-mint' : 'text-txt-dim'}>
                  {a.en_pause ? 'En pause' : a.nouveaux > 0 ? `${a.nouveaux} nouveau${a.nouveaux > 1 ? 'x' : ''} depuis hier` : 'Rien de neuf'}
                </span>
                <span className="text-txt-dim">
                  {a.en_pause
                    ? (a.paused_at ? `En pause depuis le ${new Date(a.paused_at).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' })}` : 'En pause')
                    : (a.created_at ? `Créée le ${new Date(a.created_at).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' })}` : '')}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Bouton niveau="secondaire" ton="vert" data-alerte-voir onClick={() => voirDansRadar(a)}>Voir dans Radar</Bouton>
                <Bouton niveau="secondaire" ton="vert" data-alerte-pause onClick={() => pause.mutate({ id: a.id, p: !a.en_pause })}>
                  {a.en_pause ? 'Reprendre' : 'Mettre en pause'}
                </Bouton>
                <Bouton niveau="secondaire" ton="danger" icone data-alerte-supprimer aria-label="Supprimer l’alerte" onClick={() => suppr.mutate(a.id)}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M4 7h16M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2M6 7l1 13a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1l1-13" /></svg>
                </Bouton>
              </div>
            </div>
          </div>
        ))}
      </div>
     </div>
    </div>
  )
}
