// RV2-V3 (retours visuels 2) — LA VEILLE, catégorie plein écran (patron Radar) : panneau gauche
// (434px, DEUX portes) + carte, à la place de l'ancien overlay à droite. Deux portes : « Le foncier »
// (parcelles suivies + critères) et « Les annonces » (veilles Radar). L'outil « Secteur » a été retiré
// (l'entrée n'a plus d'objet) ; l'entrée IA de la création de veille aussi (décision Vic). Back intact.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { creerRadarVeille, deleteSearch, getRadarVeilles, getSavedSearches, getSuivis, supprimerRadarVeille, toggleWatch, type RadarVeille } from '../../lib/api'
import { CP_COMMUNES, FiltreLabuse } from '../panel/FiltreLabuse'
import { trierCommunes } from '../../lib/communes'
import { useApp } from '../../store/useApp'
import { ParcelInput } from '../ParcelInput'
import { iduCourt } from '../../lib/format'

// RV2-V3 — la carte est montée par la vue Veille (patron Radar) ; lazy comme dans App.
const MapView = lazy(() => import('../map/MapView').then((m) => ({ default: m.MapView })))

// RV2-V3 — volets du Foncier : Parcelles + Critères (« Secteurs » RETIRÉ — l'outil secteur n'existe plus).
const VOLETS = [
  { key: 'parcelles', label: 'Parcelles' },
  { key: 'criteres', label: 'Critères' },
] as const

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
        className="door door-hot w-full text-left transition-colors duration-quick hover:border-line-3">
        <div className="text-[13px] font-medium text-txt">Le foncier</div>
        <div className="mt-0.5 text-[11px] leading-snug text-txt-dim">Parcelles suivies et critères enregistrés — vente, permis, procédure, zonage, classement.</div>
      </button>
      <button data-veille-porte="externe" onClick={() => onChoisir('externe')}
        className="door door-hot w-full text-left transition-colors duration-quick hover:border-line-3">
        <div className="text-[13px] font-medium text-txt">Les annonces</div>
        <div className="mt-0.5 text-[11px] leading-snug text-txt-dim">Vos veilles Radar — soyez alerté sur une nouvelle annonce, une baisse de prix ou un retour, selon vos critères.</div>
      </button>
    </div>
  )
}

// ── Veille interne — le foncier : Parcelles + Critères (Secteurs retiré). ──
function VeilleInterne() {
  const { surveillanceVolet, openSurveillance } = useApp()
  const volet = surveillanceVolet === 'criteres' ? 'criteres' : 'parcelles'
  return (
    <>
      <p data-surveillance-boucle className="border-b border-line bg-surface-2 px-4 py-2 text-[10.5px] leading-snug text-txt-mut">
        Ce que vous surveillez ici produit des alertes — elles arrivent <b className="text-txt">à la cloche</b>,
        au <b className="text-txt">brief du matin</b> et par <b className="text-txt">e-mail au compte</b>.
      </p>
      <div className="flex shrink-0 gap-1 border-b border-line px-3 py-2">
        {VOLETS.map((v) => (
          <button key={v.key} data-volet={v.key} onClick={() => openSurveillance(v.key)}
            className={`rounded-full px-3 py-1 text-[11px] transition-colors duration-quick ${
              volet === v.key ? 'bg-mint/15 text-mint' : 'text-txt-mut hover:text-txt'}`}>
            {v.label}
          </button>
        ))}
      </div>
      <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-3 text-[12px]">
        {volet === 'parcelles' ? <VoletParcelles /> : <VoletCriteres />}
      </div>
    </>
  )
}

// ── Volet PARCELLES : barre IDU+adresse pour suivre une parcelle + liste des suivis. ──
function VoletParcelles() {
  const { select, setView } = useApp()
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['suivis'], queryFn: getSuivis })
  const suivis = q.data?.suivis ?? []
  const plafond = q.data?.plafond ?? 50
  const [msg, setMsg] = useState<string | null>(null)
  // RV2-V3 — toggleWatch : suit (ou dé-suit) une parcelle, cloisonné au compte (events.py).
  const suivre = useMutation({
    mutationFn: (idu: string) => toggleWatch(idu),
    onSuccess: (r) => { qc.invalidateQueries({ queryKey: ['suivis'] }); setMsg(r.watched ? '✓ Parcelle ajoutée au suivi.' : 'Parcelle retirée du suivi.') },
    onError: () => setMsg('Impossible de suivre cette parcelle (plafond atteint ?).'),
  })
  return (
    <div data-volet-parcelles className="flex flex-col gap-2">
      {/* RV2-V3 — barre IDU + adresse (composant partagé, comme l'outil Étudier un bien). */}
      <ParcelInput dataAttr="veille-parcelle" placeholder="Adresse ou IDU — la parcelle à surveiller"
        onPick={(idu) => suivre.mutate(idu)}
        onAddress={() => setMsg("Cette adresse n'a pas de parcelle rattachée — précisez un IDU pour la suivre.")} />
      {msg && <p className="text-[10.5px] text-txt-mut">{msg}</p>}
      <p className="label-caps mt-1">Parcelles suivies <span className="text-txt-dim">· {suivis.length}/{plafond}</span></p>
      {suivis.length === 0 && (
        <p className="p-1 text-[11.5px] leading-snug text-txt-dim">
          Aucune parcelle suivie. Ajoutez-en une ci-dessus, ou ouvrez une fiche et cliquez la <b className="text-txt">cloche « Suivre »</b>.
        </p>
      )}
      {suivis.map((s) => (
        <div key={s.idu} data-suivi className="flex items-start gap-2 rounded-lg border border-line-2 px-3 py-2">
          <button onClick={() => { setView('cartes'); select(s.idu) }} className="min-w-0 flex-1 text-left transition-colors duration-quick hover:text-txt-hi">
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
          <button data-suivi-retirer onClick={() => suivre.mutate(s.idu)} title="Ne plus suivre" className="shrink-0 text-[11px] text-txt-dim hover:text-st-ecartee">retirer</button>
        </div>
      ))}
    </div>
  )
}

// ── Volet CRITÈRES : les MÊMES filtres que la carte (FiltreLabuse) + critères enregistrés. Sans IA. ──
function VoletCriteres() {
  const qc = useQueryClient()
  const criteres = useQuery({ queryKey: ['searches'], queryFn: getSavedSearches })
  const del = useMutation({ mutationFn: deleteSearch, onSuccess: () => qc.invalidateQueries({ queryKey: ['searches'] }) })
  // FICHE-COMMUNE-2 (C4) — même modèle que la veille annonces (RADAR-VEILLE-1) : à l'ouverture, le
  // bouton « Créer une veille » + « Vos critères enregistrés » ; les filtres n'apparaissent qu'APRÈS
  // clic (avant, ils étaient dépliés d'emblée). Après une création réussie (la liste grandit), on
  // revient à la liste.
  const [creating, setCreating] = useState(false)
  const liste = criteres.data ?? []
  const prevN = useRef(liste.length)
  useEffect(() => {
    if (creating && liste.length > prevN.current) setCreating(false)
    prevN.current = liste.length
  }, [liste.length, creating])
  return (
    <div data-volet-criteres className="flex flex-col gap-3">
      {!creating ? (
        <>
          <button data-veille-fonc-creer-ouvrir onClick={() => setCreating(true)}
            className="rounded-md bg-mint py-2 text-[12.5px] font-medium text-mint-ink transition-[filter] duration-quick hover:brightness-110">
            + Créer une veille
          </button>
          <p className="text-[10.5px] leading-snug text-txt-mut">Une veille foncière vous <b className="text-txt">alerte dès qu'une parcelle bascule</b> et correspond à vos critères (les mêmes que la recherche carte).</p>
          <div className="flex flex-col gap-1.5">
            <p className="label-caps">Vos critères enregistrés <span className="text-txt-dim">· {liste.length}</span></p>
            {criteres.isLoading && <p className="text-[10.5px] text-txt-dim">Chargement…</p>}
            {!criteres.isLoading && liste.length === 0 && <p className="text-[10.5px] leading-snug text-txt-dim">Aucun critère enregistré. Créez-en un avec le bouton ci-dessus.</p>}
            {liste.map((v) => (
              <div key={v.id} data-critere className="flex items-center gap-2 rounded-lg border border-line-2 px-3 py-2 text-[11px]">
                <a href={'/socle/' + v.hash} className="min-w-0 flex-1 truncate text-txt hover:text-mint" title={v.hash}>{v.nom}</a>
                <button onClick={() => del.mutate(v.id)} aria-label="Supprimer le critère"
                  className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-txt-dim transition-colors duration-quick hover:bg-surface-3 hover:text-st-ecartee">×</button>
              </div>
            ))}
          </div>
        </>
      ) : (
        // C4 — le formulaire de création : les filtres (FiltreLabuse) n'apparaissent qu'ICI, après clic.
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <p className="label-caps">Nouvelle veille</p>
            <button data-veille-fonc-annuler onClick={() => setCreating(false)} className="text-[11px] text-txt-mut hover:text-txt">annuler</button>
          </div>
          <p className="text-[10.5px] leading-snug text-txt-dim">Réglez les filtres (les mêmes que la recherche carte), puis « Créer une veille » en bas.</p>
          {/* RV2-V3 — le VRAI panneau de filtres de la carte (pas un jeu réduit) ; son bouton
              « Créer une veille » enregistre la recherche. L'entrée IA (traduction NL) est RETIRÉE. */}
          <FiltreLabuse enVeille />
        </div>
      )}
    </div>
  )
}

// ── Veille externe — les annonces Radar : créer + gérer ses veilles (back type 'radar' réutilisé). ──
// RETOURS-11 T6 — tri sans tenir compte de l'article (« Le Port » se range à P).
const V_COMMUNES = trierCommunes(CP_COMMUNES.map(([, nom]) => nom), (n) => n)
const V_TYPES = [['', 'Tous types'], ['maison', 'Maison'], ['appartement', 'Appartement'], ['terrain', 'Terrain'], ['immeuble', 'Immeuble']] as const

function resumeVeille(v: RadarVeille): string {
  const c = v.criteria as Record<string, unknown>
  const bouts: string[] = []
  if (v.commune) bouts.push(String(v.commune))
  if (c.type_bien) bouts.push(String(c.type_bien))
  if (c.prix_min || c.prix_max) bouts.push(`${c.prix_min ? Number(c.prix_min).toLocaleString('fr-FR') : '0'}–${c.prix_max ? Number(c.prix_max).toLocaleString('fr-FR') + ' €' : '∞'}`)
  if (c.surface_terrain_min) bouts.push(`terrain ≥ ${c.surface_terrain_min} m²`)
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
  const [commune, setCommune] = useState('')
  const [type, setType] = useState('')
  const [prixMin, setPrixMin] = useState('')
  const [prixMax, setPrixMax] = useState('')
  const [surfMin, setSurfMin] = useState('')
  const [particulier, setParticulier] = useState(false)
  const inval = () => qc.invalidateQueries({ queryKey: ['radar-veilles'] })
  const reset = () => { setCommune(''); setType(''); setPrixMin(''); setPrixMax(''); setSurfMin(''); setParticulier(false) }
  const creer = useMutation({
    // V3 — plus de filtres d'événement : une veille notifie sur TOUT événement d'un bien correspondant.
    mutationFn: () => creerRadarVeille({
      commune: commune || undefined, type_bien: type || undefined,
      prix_min: prixMin ? Number(prixMin) : undefined, prix_max: prixMax ? Number(prixMax) : undefined,
      surface_terrain_min: surfMin ? Number(surfMin) : undefined,
      particulier_only: particulier || undefined,
    }),
    onSuccess: () => { inval(); reset(); setCreating(false) },
  })
  const suppr = useMutation({ mutationFn: (id: number) => supprimerRadarVeille(id), onSuccess: inval })
  const sel = 'h-8 rounded-md border border-line-2 bg-surface-1 px-2 text-[11.5px] text-txt'

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-3 text-[12px]">
      {!creating ? (
        <>
          {/* V2 — en tête, le bouton de création ; en dessous, les critères déjà enregistrés. */}
          <button data-veille-ext-creer-ouvrir onClick={() => setCreating(true)}
            className="rounded-md bg-mint py-2 text-[12.5px] font-medium text-mint-ink transition-[filter] duration-quick hover:brightness-110">
            + Créer une veille
          </button>
          <p className="text-[10.5px] leading-snug text-txt-mut">
            Une veille sur les annonces produit une <b className="text-txt">alerte de fin de journée</b> dès qu'un bien
            correspond à vos critères — nouvelle mise en vente, baisse de prix ou retour en ligne. Des faits et un lien,
            jamais le contenu de l'annonce.
          </p>
          <div className="flex flex-col gap-1.5">
            <p className="label-caps">Vos critères enregistrés <span className="text-txt-dim">· {veilles.length}</span></p>
            {q.isLoading && <p className="text-[11px] text-txt-dim">Chargement…</p>}
            {!q.isLoading && veilles.length === 0 && <p className="text-[11px] leading-snug text-txt-dim">Aucune veille annonce. Créez-en une avec le bouton ci-dessus.</p>}
            {veilles.map((v) => (
              <div key={v.id} data-veille-ext-item className="flex items-start gap-2 rounded-lg border border-line-2 px-3 py-2">
                <div className="min-w-0 flex-1">
                  <div className="truncate text-[12px] text-txt">{resumeVeille(v)}</div>
                  {/* V3 — plus d'événements affichés : la veille suit tout événement du bien. */}
                  <div className="mt-0.5 text-[10px] text-txt-dim">Tous les événements</div>
                </div>
                <button onClick={() => suppr.mutate(v.id)} className="shrink-0 text-[11px] text-txt-mut hover:text-st-ecartee">supprimer</button>
              </div>
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
          <div className="grid grid-cols-2 gap-1.5">
            <select data-veille-ext-commune value={commune} onChange={(e) => setCommune(e.target.value)} className={sel}>
              <option value="">Toute l’île</option>
              {V_COMMUNES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
            <select value={type} onChange={(e) => setType(e.target.value)} className={sel}>
              {V_TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
            <input type="number" min={0} placeholder="prix min" value={prixMin} onChange={(e) => setPrixMin(e.target.value)} className={`min-w-0 ${sel}`} />
            <input type="number" min={0} placeholder="prix max" value={prixMax} onChange={(e) => setPrixMax(e.target.value)} className={`min-w-0 ${sel}`} />
            <input type="number" min={0} placeholder="surface terrain min" value={surfMin} onChange={(e) => setSurfMin(e.target.value)} className={`col-span-2 min-w-0 ${sel}`} />
          </div>
          <label className="flex items-center gap-2 text-[11.5px] text-txt-mut">
            <input type="checkbox" checked={particulier} onChange={(e) => setParticulier(e.target.checked)} className="h-3.5 w-3.5 accent-mint" />
            Particuliers seulement
          </label>
          <p className="text-[10px] leading-snug text-txt-dim">Cette veille vous alertera sur <b className="text-txt-mut">tout événement</b> d'un bien correspondant — le mail dit lequel (nouvelle annonce, baisse, retour).</p>
          <button data-veille-ext-creer disabled={creer.isPending} onClick={() => creer.mutate()}
            className="rounded-md bg-mint py-1.5 text-[12px] font-medium text-mint-ink transition-[filter] duration-quick hover:brightness-110 disabled:opacity-40">
            {creer.isPending ? 'Création…' : 'Créer la veille'}
          </button>
        </div>
      )}
    </div>
  )
}
