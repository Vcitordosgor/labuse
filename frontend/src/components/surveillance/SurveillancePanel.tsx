// RV2-V3 (retours visuels 2) — LA VEILLE, catégorie plein écran (patron Radar) : panneau gauche
// (434px, DEUX portes) + carte, à la place de l'ancien overlay à droite. Deux portes : « Le foncier »
// (parcelles suivies + critères) et « Les annonces » (veilles Radar). L'outil « Secteur » a été retiré
// (l'entrée n'a plus d'objet) ; l'entrée IA de la création de veille aussi (décision Vic). Back intact.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { lazy, Suspense, useState } from 'react'
import { ApiError, creerRadarVeille, getRadarVeilles, getSuivis, renommerRadarVeille, supprimerRadarVeille, toggleWatch, type RadarVeille } from '../../lib/api'
import { CP_COMMUNES } from '../panel/FiltreLabuse'
import { trierCommunes } from '../../lib/communes'
import { useApp } from '../../store/useApp'
import { ParcelInput } from '../ParcelInput'
import { iduCourt } from '../../lib/format'
import { Bouton } from '../ui/Bouton'

// RV2-V3 — la carte est montée par la vue Veille (patron Radar) ; lazy comme dans App.
const MapView = lazy(() => import('../map/MapView').then((m) => ({ default: m.MapView })))

export function SurveillancePanel() {
  const { surveillancePorte, setSurveillancePorte } = useApp()
  return (
    <>
      <aside data-surveillance-panel className="flex w-[434px] shrink-0 flex-col border-r border-line bg-surface-1">
        <div className="flex items-center justify-between border-b border-line-2 px-5 pb-3 pt-5">
          <div>
            <div className="font-mono text-[10.5px] tracking-[0.2em] text-txt-mut">VEILLE</div>
            {/* V1 — sur l'écran d'entrée, plus de titre « Deux veilles » : le contenu (les deux portes) se
                suffit. Le titre n'apparaît qu'une fois une porte choisie. */}
            {surveillancePorte !== 'accueil' && (
              <h3 className="mt-1.5 text-[18px] font-semibold text-txt-hi">
                {surveillancePorte === 'externe' ? 'Les annonces' : 'Le foncier'}
              </h3>
            )}
          </div>
          {surveillancePorte !== 'accueil' && (
            <button data-veille-retour onClick={() => setSurveillancePorte('accueil')} className="text-[11px] text-mint hover:underline">‹ retour</button>
          )}
        </div>
        {surveillancePorte === 'accueil' && <DeuxPortes onChoisir={setSurveillancePorte} />}
        {surveillancePorte === 'interne' && <VeilleInterne />}
        {surveillancePorte === 'externe' && <VeilleExterne />}
      </aside>
      <Suspense fallback={<div className="flex-1 bg-bg" />}><MapView /></Suspense>
    </>
  )
}

// ── L'écran d'entrée : deux gros boutons (gabarit door-hot, patron Communes R3). ──
function DeuxPortes({ onChoisir }: { onChoisir: (p: 'interne' | 'externe') => void }) {
  return (
    <div className="flex flex-col gap-2.5 p-4">
      <p className="text-[12px] leading-snug text-txt-mut">Choisissez ce que vous voulez surveiller.</p>
      <button data-veille-porte="interne" onClick={() => onChoisir('interne')}
        className="door door-hot hover-fill w-full text-left">
        {/* RECETTE-1 R30 — survol vert opaque, comme les autres portes de l'app */}
        {/* VEILLE-2 (Lot 4) — le chemin PARCELLE : uniquement les parcelles suivies (critères retirés). */}
        <div className="text-[13px] font-medium text-txt">Le foncier</div>
        <div className="mt-0.5 text-[11px] leading-snug text-txt-dim">Vos parcelles suivies — vente, permis, procédure, changement de propriétaire, bascule du score.</div>
      </button>
      <button data-veille-porte="externe" onClick={() => onChoisir('externe')}
        className="door door-hot hover-fill w-full text-left">
        {/* RECETTE-1 R30 — survol vert opaque, comme les autres portes de l'app */}
        <div className="text-[13px] font-medium text-txt">Les annonces</div>
        <div className="mt-0.5 text-[11px] leading-snug text-txt-dim">Vos veilles Radar — soyez alerté sur une nouvelle annonce, une baisse de prix ou un retour, selon vos critères.</div>
      </button>
    </div>
  )
}

// ── Veille interne — le CHEMIN PARCELLE : uniquement les parcelles suivies (VEILLE-2 Lot 4 : le volet
//    « Critères » / recherche sauvegardée est retiré ; la page Veille n'a plus que PARCELLE et RADAR). ──
function VeilleInterne() {
  return (
    <>
      <p data-surveillance-boucle className="border-b border-line bg-surface-2 px-4 py-2 text-[10.5px] leading-snug text-txt-mut">
        Ce que vous suivez ici arrive <b className="text-txt">à la cloche</b> et dans le
        <b className="text-txt"> mail du matin</b> — un seul par jour.
      </p>
      <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-3 text-[12px]">
        <VoletParcelles />
      </div>
    </>
  )
}

// ── Volet PARCELLES : barre IDU+adresse pour suivre une parcelle + liste des suivis. ──
function VoletParcelles() {
  // RETOURS-11 A7 — cliquer un suivi OUVRE la fiche SANS fermer la Veille : on pose simplement
  // `select(idu)` (la fiche est un overlay rendu tant que `selectedIdu` est posé, même en vue 'veille'
  // — cf. App.tsx). On NE change PAS de vue (`setView('cartes')` refermait le panneau).
  const { select } = useApp()
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['suivis'], queryFn: getSuivis })
  const suivis = q.data?.suivis ?? []
  const [msg, setMsg] = useState<string | null>(null)
  // RV2-V3 — toggleWatch : suit (ou dé-suit) une parcelle, cloisonné au compte (events.py).
  const suivre = useMutation({
    mutationFn: (idu: string) => toggleWatch(idu),
    // RETOURS-11F M10 — sens Veille → fiche : retirer ici éteint la cloche de la fiche (clé ['watch']).
    onSuccess: (r) => { qc.invalidateQueries({ queryKey: ['suivis'] }); qc.invalidateQueries({ queryKey: ['watch'] }); setMsg(r.watched ? '✓ Parcelle ajoutée au suivi.' : 'Parcelle retirée du suivi.') },
    // VEILLE-2 (Lot 1) — le REFUS de la barre IDU se dit avec son MOTIF (IDU invalide, hors des 24
    // communes, parcelle inconnue, plafond) : on remonte le détail serveur, jamais un message générique.
    onError: (err) => setMsg(err instanceof ApiError && err.detail ? err.detail : 'Impossible de suivre cette parcelle.'),
  })
  return (
    <div data-volet-parcelles className="flex flex-col gap-2">
      {/* RV2-V3 — barre IDU + adresse (composant partagé, comme l'outil Étudier un bien). */}
      <ParcelInput dataAttr="veille-parcelle" placeholder="Adresse ou IDU — la parcelle à surveiller"
        onPick={(idu) => suivre.mutate(idu)}
        onAddress={() => setMsg("Cette adresse n'a pas de parcelle rattachée — précisez un IDU pour la suivre.")} />
      {msg && <p className="text-[10.5px] text-txt-mut">{msg}</p>}
      {/* RETOURS-11 A7 — plus de fraction « /50 » : on suit autant de parcelles qu'on veut (le back
          garde un plafond de sécurité, sans le brandir ici). Simple décompte. */}
      <p className="label-caps mt-1">Parcelles suivies <span className="text-txt-dim">· {suivis.length}</span></p>
      {suivis.length === 0 && (
        <p className="rounded-lg border border-dashed border-line-2 p-3 text-[11.5px] leading-snug text-txt-dim">
          Aucune parcelle suivie. Ajoutez-en une ci-dessus, ou ouvrez une fiche et cliquez la <b className="text-txt">cloche « Suivre »</b>.
        </p>
      )}
      {suivis.map((s) => (
        <div key={s.idu} data-suivi className="hover-fill flex items-start gap-2 rounded-lg border border-line-2 px-3 py-2">
          <button onClick={() => select(s.idu)} className="min-w-0 flex-1 text-left">
            {/* RECETTE-2 LOT E : l'IDU (identifiant de ce qu'on suit) prend le style de TITRE ; la
                commune passe en secondaire. Échange de CONTENUS — chaque position garde sa typo. */}
            <span className="text-xs font-medium text-txt">
              {iduCourt(s.idu)} <span className="font-mono text-[10px] text-txt-dim">{s.commune ?? 'Parcelle'}</span>
            </span>
            <span className="mt-0.5 block text-[10.5px] text-txt-dim">
              {s.dernier_changement
                ? <>Dernier changement : <b className="text-txt-mut">{new Date(s.dernier_changement).toLocaleDateString('fr-FR')}</b></>
                : 'Aucun changement détecté depuis le suivi.'}
            </span>
          </button>
          <button data-suivi-retirer onClick={() => suivre.mutate(s.idu)} className="shrink-0 text-[11px] text-txt-dim hover:text-st-ecartee">retirer</button>
        </div>
      ))}
    </div>
  )
}

// VEILLE-2 (Lot 4) — le volet CRITÈRES (recherche sauvegardée) est RETIRÉ : la page Veille n'a plus que
// PARCELLE (parcelles suivies) et RADAR (annonces). Plus aucun bouton « Créer une veille » depuis les
// filtres carte (FiltreLabuse) ni depuis les projets.

// ── Veille externe — les annonces Radar : créer + gérer ses veilles (back type 'radar' réutilisé). ──
// RETOURS-11 T6 — tri sans tenir compte de l'article (« Le Port » se range à P).
const V_COMMUNES = trierCommunes(CP_COMMUNES.map(([, nom]) => nom), (n) => n)
const V_TYPES = [['', 'Tous types'], ['maison', 'Maison'], ['appartement', 'Appartement'], ['terrain', 'Terrain'], ['immeuble', 'Immeuble']] as const

function resumeVeille(v: RadarVeille): string {
  const c = v.criteria as Record<string, unknown>
  const bouts: string[] = []
  // VEILLE-2 (Lot 2) — commune(s) : liste `communes` (jointes par « ou ») sinon la commune unique.
  const communes = Array.isArray(c.communes) ? (c.communes as string[]) : []
  if (communes.length) bouts.push(communes.join(' ou '))
  else if (v.commune) bouts.push(String(v.commune))
  if (c.type_bien) bouts.push(String(c.type_bien))
  if (c.prix_min || c.prix_max) bouts.push(`${c.prix_min ? Number(c.prix_min).toLocaleString('fr-FR') : '0'}–${c.prix_max ? Number(c.prix_max).toLocaleString('fr-FR') + ' €' : '∞'}`)
  // surface min/max (modèle VEILLE-2) — + rétro-compat de l'ancien surface_terrain_min.
  if (c.surface_min || c.surface_max) bouts.push(`${c.surface_min ? Number(c.surface_min) : 0}–${c.surface_max ? Number(c.surface_max) + ' m²' : '∞'}`)
  else if (c.surface_terrain_min) bouts.push(`terrain ≥ ${c.surface_terrain_min} m²`)
  if (c.particulier_only) bouts.push('particulier')
  return bouts.length ? bouts.join(' · ') : 'Tous les biens'
}

function VeilleExterne() {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['radar-veilles'], queryFn: getRadarVeilles })
  const veilles = q.data?.veilles ?? []
  // V2 — même ergonomie que la veille parcelle : on ouvre sur ce que le client a DÉJÀ créé ; les filtres
  // n'apparaissent qu'après « Créer une veille ».
  const [creating, setCreating] = useState(false)
  // VEILLE-2 (Lot 2) — critères du modèle : commune(s), type de bien, surface min/max, prix max.
  const [communes, setCommunes] = useState<string[]>([])
  const [type, setType] = useState('')
  const [prixMin, setPrixMin] = useState('')
  const [prixMax, setPrixMax] = useState('')
  const [surfMin, setSurfMin] = useState('')
  const [surfMax, setSurfMax] = useState('')
  const [particulier, setParticulier] = useState(false)
  const inval = () => qc.invalidateQueries({ queryKey: ['radar-veilles'] })
  const reset = () => { setCommunes([]); setType(''); setPrixMin(''); setPrixMax(''); setSurfMin(''); setSurfMax(''); setParticulier(false) }
  const creer = useMutation({
    // V3 — plus de filtres d'événement : une veille notifie sur TOUT événement d'un bien correspondant.
    mutationFn: () => creerRadarVeille({
      communes: communes.length ? communes : undefined, type_bien: type || undefined,
      prix_min: prixMin ? Number(prixMin) : undefined, prix_max: prixMax ? Number(prixMax) : undefined,
      surface_min: surfMin ? Number(surfMin) : undefined, surface_max: surfMax ? Number(surfMax) : undefined,
      particulier_only: particulier || undefined,
    }),
    onSuccess: () => { inval(); reset(); setCreating(false) },
  })
  const suppr = useMutation({ mutationFn: (id: number) => supprimerRadarVeille(id), onSuccess: inval })
  // RETOURS-11 A7 — renommer une veille en place : un seul champ édité à la fois (`renomId`).
  const [renomId, setRenomId] = useState<number | null>(null)
  const [renomVal, setRenomVal] = useState('')
  const renommer = useMutation({
    mutationFn: ({ id, nom }: { id: number; nom: string }) => renommerRadarVeille(id, nom),
    onSuccess: () => { inval(); setRenomId(null) },
  })
  const ouvrirRenom = (v: RadarVeille) => { setRenomId(v.id); setRenomVal(v.nom ?? '') }
  const sel = 'h-8 rounded-md border border-line-2 bg-surface-1 px-2 text-[11.5px] text-txt'

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-3 text-[12px]">
      {!creating ? (
        <>
          {/* V2 — en tête, le bouton de création ; en dessous, les critères déjà enregistrés. */}
          <Bouton niveau="primaire" ton="vert" data-veille-ext-creer-ouvrir className="w-full" onClick={() => setCreating(true)}>
            + Créer une veille
          </Bouton>
          <p className="text-[10.5px] leading-snug text-txt-mut">
            Une veille sur les annonces produit une <b className="text-txt">alerte de fin de journée</b> dès qu'un bien
            correspond à vos critères — nouvelle mise en vente, baisse de prix ou retour en ligne. Des faits et un lien,
            jamais le contenu de l'annonce.
          </p>
          <div className="flex flex-col gap-1.5">
            <p className="label-caps">Vos critères enregistrés <span className="text-txt-dim">· {veilles.length}</span></p>
            {q.isLoading && <p className="text-[11px] text-txt-dim">Chargement…</p>}
            {!q.isLoading && veilles.length === 0 && (
              <p className="rounded-lg border border-dashed border-line-2 p-3 text-[11px] leading-snug text-txt-dim">Aucune veille annonce. Créez-en une avec le bouton ci-dessus.</p>
            )}
            {veilles.map((v) => (
              // RETOURS-11 A7 — quand on renomme, la ligne PLEINE reste neutre (formulaire) ; sinon
              // survol vert (.hover-fill). Le nom donné prime, sinon le résumé des critères (toujours
              // affiché en second pour ne pas perdre le sens de la veille).
              renomId === v.id ? (
                <div key={v.id} data-veille-ext-item className="flex flex-col gap-1.5 rounded-lg border border-line-3 bg-surface-2 px-3 py-2">
                  <input autoFocus data-veille-ext-renom-champ value={renomVal} onChange={(e) => setRenomVal(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter') renommer.mutate({ id: v.id, nom: renomVal }); if (e.key === 'Escape') setRenomId(null) }}
                    placeholder="Nom de la veille" maxLength={120}
                    className="h-8 rounded-md border border-line-2 bg-surface-1 px-2 text-[11.5px] text-txt" />
                  <div className="flex items-center gap-2">
                    <Bouton niveau="primaire" ton="vert" data-veille-ext-renom-ok disabled={renommer.isPending} onClick={() => renommer.mutate({ id: v.id, nom: renomVal })}>Renommer</Bouton>
                    <button onClick={() => setRenomId(null)} className="text-[11px] text-txt-mut hover:text-txt">annuler</button>
                  </div>
                </div>
              ) : (
                <div key={v.id} data-veille-ext-item className="hover-fill flex items-start gap-2 rounded-lg border border-line-2 px-3 py-2">
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-[12px] text-txt">{v.nom || resumeVeille(v)}</div>
                    {/* Le nom donné coiffe le résumé des critères ; sans nom, seul « Tous les événements ». */}
                    <div className="mt-0.5 truncate text-[10px] text-txt-dim">{v.nom ? resumeVeille(v) : 'Tous les événements'}</div>
                  </div>
                  <button data-veille-ext-renom onClick={() => ouvrirRenom(v)} className="shrink-0 text-[11px] text-txt-mut hover:text-txt">renommer</button>
                  <button onClick={() => suppr.mutate(v.id)} className="shrink-0 text-[11px] text-txt-mut hover:text-st-ecartee">supprimer</button>
                </div>
              )
            ))}
          </div>
        </>
      ) : (
        // V2 — le formulaire de création : les filtres n'apparaissent qu'ICI.
        <div className="flex flex-col gap-2 rounded-lg border border-line-2 bg-surface-2 p-2.5">
          <div className="flex items-center justify-between">
            <p className="label-caps">Nouvelle veille</p>
            <button data-veille-ext-annuler onClick={() => setCreating(false)} className="text-[11px] text-txt-mut hover:text-txt">annuler</button>
          </div>
          {/* VEILLE-2 (Lot 2) — commune(s) : sélection MULTIPLE (aucune = toute l'île). */}
          <select data-veille-ext-communes multiple value={communes} size={4}
            onChange={(e) => setCommunes(Array.from(e.target.selectedOptions, (o) => o.value))}
            className="rounded-md border border-line-2 bg-surface-1 px-2 py-1 text-[11.5px] text-txt">
            {V_COMMUNES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <p className="-mt-1 text-[10px] text-txt-dim">Commune(s) — aucune sélection = toute l’île. Ctrl/Cmd pour plusieurs.</p>
          <div className="grid grid-cols-2 gap-1.5">
            <select value={type} onChange={(e) => setType(e.target.value)} className={`col-span-2 ${sel}`}>
              {V_TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
            <input type="number" min={0} placeholder="prix min" value={prixMin} onChange={(e) => setPrixMin(e.target.value)} className={`min-w-0 ${sel}`} />
            <input type="number" min={0} placeholder="prix max" value={prixMax} onChange={(e) => setPrixMax(e.target.value)} className={`min-w-0 ${sel}`} />
            <input type="number" min={0} placeholder="surface min (m²)" value={surfMin} onChange={(e) => setSurfMin(e.target.value)} className={`min-w-0 ${sel}`} />
            <input type="number" min={0} placeholder="surface max (m²)" value={surfMax} onChange={(e) => setSurfMax(e.target.value)} className={`min-w-0 ${sel}`} />
          </div>
          <label className="flex items-center gap-2 text-[11.5px] text-txt-mut">
            <input type="checkbox" checked={particulier} onChange={(e) => setParticulier(e.target.checked)} className="h-3.5 w-3.5 accent-mint" />
            Particuliers seulement
          </label>
          <p className="text-[10px] leading-snug text-txt-dim">Cette veille vous alertera sur <b className="text-txt-mut">tout événement</b> d'un bien correspondant — le mail dit lequel (nouvelle annonce, baisse, retour).</p>
          <Bouton niveau="primaire" ton="vert" data-veille-ext-creer className="w-full" disabled={creer.isPending} onClick={() => creer.mutate()}>
            {creer.isPending ? 'Création…' : 'Créer la veille'}
          </Bouton>
        </div>
      )}
    </div>
  )
}
