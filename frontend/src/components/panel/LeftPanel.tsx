import { useEffect, useRef } from 'react'
import { useApp, type LayerToggles } from '../../store/useApp'
import { Legend } from '../map/Legend'
import { LAYER_INFO } from '../../lib/layers'
import { countActiveFilters } from '../../lib/filters'
import { getAccueilChiffres } from '../../lib/api'
import { useQuery } from '@tanstack/react-query'
import { Tip } from '../Tip'
import { ChevronSection, CroixEntete } from './ChevronSection'
import { ResultsSection } from './ResultsSection'
import { FiltreLabuse } from './FiltreLabuse'
import { CLIENT } from '../../lib/strings'
import { TIER_DECLASSE_META, TIER_V2_META } from '../../lib/status'

// M55-J point 5 : COQUILLE de modale partagée (overlay + Échap + croix) — deux contenus
// distincts s'y logent : « classement » (la méthode) et « scoring » (le sens des paliers).
// data-algo-overlay conservé (hook QA) ; data-modale porte l'identité (classement/scoring).
function Modale({ id, titre, onClose, children }: { id: string; titre: string; onClose: () => void; children: React.ReactNode }) {
  useEffect(() => {
    const h = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [onClose])
  return (
    <div data-algo-overlay data-modale={id} className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}>
      <div className="max-h-[80vh] w-full max-w-md overflow-y-auto rounded-xl border border-line-2 bg-surface-2 p-5 shadow-elev-2"
        onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-3">
          <h3 className="font-display text-sm font-bold text-txt-hi">{titre}</h3>
          <CroixEntete onClick={onClose} title="Fermer" />
        </div>
        {children}
      </div>
    </div>
  )
}

// « Comprendre le classement » — la MÉTHODE (ce qui est mesuré, le ×N, l'entraînement). Contenu
// centralisé dans strings.ts (CLIENT.algo.corps), validé par Vic. M55-H p11 : plus de ligne de date.
function AlgoExplainer({ onClose }: { onClose: () => void }) {
  return (
    <Modale id="classement" titre={CLIENT.algo.titre} onClose={onClose}>
      <div className="mt-3 flex flex-col gap-3">
        {CLIENT.algo.corps.map((s) => (
          <div key={s.h}>
            <p className="label-caps text-[9.5px]">{s.h}</p>
            <p className="mt-0.5 text-[12px] leading-relaxed text-txt-mut">{s.p}</p>
          </div>
        ))}
      </div>
    </Modale>
  )
}

// M55-J point 5 : « Comprendre le scoring » — le SENS des paliers. Les définitions viennent de
// l'échelle verbale EXISTANTE (CLIENT.revelation.defTiers, source unique aussi utilisée par les
// tooltips de la carte d'analyse) : une définition de palier, un seul endroit. Les couleurs
// viennent de la palette unique (status.ts). Les 6 tiers de déclassement sont regroupés sous
// « Potentiel épuisé » (comme la ventilation).
const SCORING_PALIERS: { key: string; color: string }[] = [
  { key: 'brulante', color: TIER_V2_META.brulante.color },
  { key: 'chaude', color: TIER_V2_META.chaude.color },
  { key: 'reserve_fonciere', color: TIER_V2_META.reserve_fonciere.color },
  { key: 'a_creuser', color: TIER_V2_META.a_creuser.color },
  { key: 'declassees', color: TIER_DECLASSE_META.declasse_bati_sature.color },
  { key: 'ecartee', color: TIER_V2_META.ecartee.color },
]
function ScoringExplainer({ onClose }: { onClose: () => void }) {
  return (
    <Modale id="scoring" titre={CLIENT.algo.scoringTitre} onClose={onClose}>
      <p className="mt-2 text-[12px] leading-relaxed text-txt-mut">{CLIENT.algo.scoringIntro}</p>
      <div className="mt-3 flex flex-col gap-2.5">
        {SCORING_PALIERS.map(({ key, color }) => (
          <div key={key} className="flex items-start gap-2">
            <span className="mt-[5px] h-2 w-2 shrink-0 rounded-full" style={{ background: color }} />
            <p className="text-[12px] leading-relaxed text-txt-mut">{CLIENT.revelation.defTiers[key]}</p>
          </div>
        ))}
      </div>
    </Modale>
  )
}

// M12 C4 — ORDRE des couches, du PLUS UTILISÉ au moins utilisé (justif. au rapport) :
//  1. parcelles       — la couche de travail (verdict coloré) — vue à chaque session
//  2. limites         — contour cadastral, référence constante posée sur le fond
//  3. zonage_parcelle — couche PARCELLAIRE UNIQUE (M55-A fusion A) : colore toutes les parcelles
//                       par famille + code au zoom/clic — remplace « colorisation » + « par parcelle »
//  4. zonage          — zones officielles brutes du GPU (document opposable) — moins fréquent
//  5. ppr             — écran risques, filtre d'exclusion précoce fréquent
//  6. equipements     — contexte de proximité, courant en due diligence
//  7. communes        — repère communal (défaut ON, rarement basculé)
//  8. parc            — Parc national, situationnel (relief/mi-pentes)
//  9. anru            — périmètres de renouvellement, de niche
// 10. cinquante_pas   — bande littorale, la plus rare (communes côtières uniquement)
const LAYERS: { key: keyof LayerToggles; label: string }[] = [
  { key: 'parcelles', label: 'Parcelles' },
  { key: 'limites', label: 'Limites parcelles' },
  // M55-G point 8 / suite point 1 : l'avis LABUSE en couche — le libellé DIT la portée :
  // toute l'île, indépendant des filtres (en mode analyse, la palette suit le résultat).
  { key: 'couleurs_verdict', label: 'Verdict — toute l’île (indépendant des filtres)' },
  // M55-A (fusion A) : couche PARCELLAIRE UNIQUE — colore d'emblée toutes les parcelles par famille
  // ET révèle le code exact au zoom / au clic (l'ancienne case « Colorisation » est fusionnée ici).
  { key: 'zonage_parcelle', label: 'Zonage PLU par parcelle (calibré)' },
  // M55-A : zones OFFICIELLES du GPU (polygones bruts du document opposable) — distinctes du
  // rattachement calibré à la parcelle ; couvrent aussi l'espace non parcellaire (voirie, domaine public).
  { key: 'zonage', label: 'Zones du PLU officiel (brut)' },
  { key: 'ppr', label: 'PPR multirisque' },
  { key: 'equipements', label: 'Équipements' },
  { key: 'communes', label: 'Limites communes' },
  { key: 'parc', label: 'Parc national' },
  { key: 'anru', label: 'ANRU (NPNRU)' },
  // M6.1 item 2 : réserve domaniale littorale — libellé métier exact exigé par le mandat
  { key: 'cinquante_pas', label: '50 pas géométriques' },
  // M-RENOUV : segment Renouvellement (occupées, potentiel) — OFF par défaut, teinte cuivre
  { key: 'renouv', label: 'Renouvellement' },
]

// M12 C2 — pastille « i » d'une couche : au survol OU au clic, l'explication CLIENT (LAYER_INFO,
// centralisée) apparaît. Le clic sur la pastille NE bascule PAS la couche (stopPropagation dans Tip).
function LayerInfoPill({ info }: { info: string }) {
  if (!info) return null
  return (
    <Tip side="top" tip={info} className="shrink-0">
      <span
        role="button"
        tabIndex={0}
        aria-label="En savoir plus sur cette couche"
        className="flex h-[15px] w-[15px] items-center justify-center rounded-full border border-line-2 text-[9px] font-bold leading-none text-txt-dim transition-colors duration-quick hover:border-mint hover:text-mint"
      >
        i
      </span>
    </Tip>
  )
}

// M12 C1 / M14 B3 (QA-64, reprise M13-D1/QA-47) — « Couches » est un TIROIR REPLIABLE, OUVERT
// PAR DÉFAUT tant que l'analyse LABUSE n'est pas affichée. Il se referme quand on clique
// « Afficher l'analyse LABUSE » (bascule `verdict`), pour libérer la place. Plus d'auto-fermeture
// 10 s. Ouvert, il POUSSE le contenu du dessous (flux flex : jamais de recouvrement).
// M55-K point 5 : `fill` — quand la section ouverte est le DERNIER contenu du panneau (ni accueil
// ni résultats en dessous), elle occupe la hauteur restante (flex-1) et son tiroir remplit
// (pas de plafond max-h) → plus de gros gap vide sous le contenu, le fond reste continu jusqu'en
// bas. Sinon (accueil/résultats présents = eux flex-1), comportement plafonné inchangé.
function LayersSection({ open, onToggle, fill, closable }: {
  open: boolean
  onToggle: () => void
  fill?: boolean
  closable?: boolean   // M55-M point 1 : un listing existe → la section ouverte peut se refermer (→ listing)
}) {
  const { layers, toggleLayer } = useApp()
  const activeCount = LAYERS.reduce((n, { key }) => n + (layers[key] ? 1 : 0), 0)
  return (
    <div className={`px-5 pt-4 ${open && fill ? 'flex min-h-0 flex-1 flex-col' : 'shrink-0'}`}>
      <button
        data-couches-toggle
        onClick={onToggle}
        aria-expanded={open}
        className="group flex w-full items-center justify-between gap-2 text-left"
        title={open ? (closable ? 'Refermer — rendre la place au listing' : 'Section ouverte (une section reste toujours ouverte)') : 'Ouvrir les couches — replie Filtres'}
      >
        <span className="label-caps">Couches</span>
        {/* M55-C point 3bis : le badge « N actives » respire (gap-3 = 12 px) — la zone de clic
            du chevron n'est plus ambiguë. */}
        <span className="flex items-center gap-3">
          {activeCount > 0 && (
            <span className="rounded-full bg-mint/15 px-1.5 py-0.5 text-[9.5px] font-medium text-mint">{activeCount} active{activeCount > 1 ? 's' : ''}</span>
          )}
          <ChevronSection open={open} />
        </span>
      </button>
      {open && (
        // plafonné + scrollable : sur un volet court, la liste des résultats garde sa hauteur.
        // QA-46 (M13-C) : overflow-x-clip — un `overflow-y-auto` calcule overflow-x=auto, si bien
        // que les tooltips absolus (Tip, `w-max`) débordant du volet étroit y déclenchaient une
        // BARRE HORIZONTALE fantôme. `clip` sur x supprime la barre sans créer de conteneur de
        // défilement, le tooltip reste peint. Défaut identique corrigé partout (fiche/CRM/tri).
        <div data-couches-drawer className={`mt-3 overflow-y-auto overflow-x-clip ${fill ? 'min-h-0 flex-1' : 'max-h-[38vh]'}`}>
          <div className="flex flex-col gap-0.5">
            {LAYERS.map(({ key, label }) => {
              const on = layers[key]
              const info = LAYER_INFO[key] ?? ''
              return (
                <div key={key} className="flex items-center gap-2">
                  <button
                    onClick={() => toggleLayer(key)}
                    className="flex min-h-[28px] flex-1 items-center gap-3 rounded-md py-1 text-left transition-colors duration-quick"
                  >
                    <span className={`flex h-[13px] w-[13px] shrink-0 items-center justify-center rounded-[3px] ${on ? 'bg-mint' : 'border border-line-2'}`}>
                      {on && (
                        <svg viewBox="0 0 10 10" className="h-2.5 w-2.5">
                          <polyline points="2,5.5 4,7.5 8,3" fill="none" stroke="#06130C" strokeWidth="1.8" />
                        </svg>
                      )}
                    </span>
                    <span className={`text-xs ${on ? 'text-txt' : 'text-txt-mut'}`}>{label}</span>
                  </button>
                  <LayerInfoPill info={info} />
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

// M55-D stage 3 — « Filtres » = SECTION REPLIABLE du panneau gauche, MÊME carrosserie que « Couches »
// (titre + badge « N actifs » + chevron fermé→gauche/ouvert→bas). Ouverte : les 3 RAPIDES
// (Verdict / Surface / SDP, mêmes champs du store) + « Tous les filtres → » qui déplie le panneau
// EXPERT complet (FiltreLabuse, contenu du stage 2 inchangé). Accroche HONNÊTE : les filtres trient,
// ils ne recalculent pas (mesuré en phase 1). Le bouton header « Filtres (N) » a disparu.
function FiltresSection({ open, onToggle, onRetract, fill, closable }: { open: boolean; onToggle: () => void; onRetract?: () => void; fill?: boolean; closable?: boolean }) {
  const { filters } = useApp()
  const n = countActiveFilters(filters)
  return (
    <div className={`px-5 pt-4 ${open && fill ? 'flex min-h-0 flex-1 flex-col' : 'shrink-0'}`}>
      <button data-filtres-toggle onClick={onToggle} aria-expanded={open}
        className="group flex w-full items-center justify-between gap-2 text-left"
        title={open ? (closable ? 'Refermer — rendre la place au listing' : 'Section ouverte (une section reste toujours ouverte)') : 'Ouvrir les filtres — replie Couches'}>
        <span className="label-caps">Filtres</span>
        <span className="flex items-center gap-3">
          {n > 0 && (
            <span className="rounded-full bg-mint/15 px-1.5 py-0.5 text-[9.5px] font-medium text-mint">{n} actif{n > 1 ? 's' : ''}</span>
          )}
          <ChevronSection open={open} />
        </span>
      </button>
      {open && (
        // plafonné + scrollable (comme le tiroir Couches) : les deux étages du panneau sont hauts,
        // ils scrollent DANS la section au lieu de casser la colonne flex de l'aside.
        <div data-filtres-drawer className={`mt-3 overflow-y-auto overflow-x-clip ${fill ? 'min-h-0 flex-1' : 'max-h-[64vh]'}`}>
          {/* M55-D stage 8 : l'accroche chiffrée a disparu — UN SEUL nombre à l'écran, porté par
              le bandeau + compteur de FiltreLabuse (état partagé `live`). */}
          <FiltreLabuse onRetract={onRetract} />
        </div>
      )}
    </div>
  )
}

// P2 (revue Vic n°3) : le geste signature affirme un AVIS argumenté, pas une décision prise à
// votre place. « Afficher l'analyse LABUSE » — rien n'est masqué, le cadastre reste entier,
// chaque parcelle garde son verdict cliquable. L'utilisateur garde la main.
function VerdictHero() {
  const { verdict, accueilVu, setAccueilVu, openFiltres, retourFiltres } = useApp()
  // M55-F point 3 : deux entrées possibles dans les résultats — l'analyse LABUSE (opinion) OU le
  // tri factuel (« je cherche moi-même »). Le bandeau DIT laquelle est affichée (honnête).
  const analyse = useApp((s) => s.filters.analyseLabuse)
  // M55-M point 3 : le bandeau porte les CRITÈRES DU RUN (figés au lancement, jamais les filtres
  // courants) — le bloc « ANALYSE EN COURS » a disparu du panneau Filtres.
  const analyseRecap = useApp((s) => s.analyseRecap)
  // M55-J point 5 : DEUX modales distinctes (classement / scoring), état partagé au store.
  const algoModale = useApp((s) => s.algoModale)
  const setAlgoModale = useApp((s) => s.setAlgoModale)
  if (verdict) {
    return (
      <div className={`mx-5 mb-1 flex shrink-0 flex-col gap-1.5 rounded-lg px-3 py-2 shadow-elev-1 ${analyse ? 'bg-mint/[0.08]' : 'bg-surface-2'}`}>
        {algoModale === 'classement' && <AlgoExplainer onClose={() => setAlgoModale(null)} />}
        {algoModale === 'scoring' && <ScoringExplainer onClose={() => setAlgoModale(null)} />}
        <div className="flex items-center justify-between gap-2">
          <span className={`min-w-0 truncate text-[11px] font-medium ${analyse ? 'text-mint' : 'text-txt-mut'}`}>
            {analyse ? '✓ Analyse LABUSE affichée' : 'Tri factuel — sans analyse'}</span>
          {/* M55-J point 7 : « Masquer » → « Retour » — destination UNIQUE (store.retourFiltres) :
              sortir de la vue verdict et atterrir sur Filtres ouvert, jamais sur Couches. */}
          <button data-verdict-off onClick={retourFiltres}
            className="shrink-0 rounded-full border border-line-2 px-2 py-0.5 text-[10.5px] text-txt-mut hover:border-txt-dim hover:text-txt"
            title="Retour — revenir aux filtres">
            Retour
          </button>
        </div>
        {/* M55-M point 3 : la phrase de critères DU RUN, juste sous le titre. Compacte : tronquée
            proprement (truncate CSS) avec le détail complet au survol (title = récap complet, sans
            « … ») — jamais de débordement qui casse le bandeau. Vient de store.analyseRecap (snapshot
            du lancement), pas des filtres courants. Absente en tri factuel (pas de run décrit). */}
        {analyse && analyseRecap && (
          <p data-analyse-criteres className="truncate text-[10px] leading-snug text-txt-mut" title={analyseRecap}>{analyseRecap}</p>
        )}
        {/* M55-J point 5 : DEUX entrées JUMELLES, côte à côte, même traitement — deux questions
            distinctes, deux modales. Seulement en mode analyse (hors-sujet en tri factuel). */}
        {/* M55-K point 2 : text-[10px] + px-1.5 + whitespace-nowrap — « Info classement » /
            « Info scoring » tiennent côte à côte sur UNE ligne même au panneau le plus étroit
            (240 px). flex-1 = deux moitiés égales, texte centré, jamais coupé. */}
        {analyse && (
          <div className="flex gap-1.5">
            <button data-algo-open onClick={() => setAlgoModale('classement')}
              className="flex-1 whitespace-nowrap rounded-full border border-mint/40 px-1.5 py-0.5 text-[10px] font-medium text-mint hover:bg-mint/10"
              title="La méthode : le tri, le « ×N plus probable », la validation">
              {CLIENT.algo.bouton}
            </button>
            <button data-scoring-open onClick={() => setAlgoModale('scoring')}
              className="flex-1 whitespace-nowrap rounded-full border border-mint/40 px-1.5 py-0.5 text-[10px] font-medium text-mint hover:bg-mint/10"
              title="Le sens des paliers : brûlante, chaude, potentiel long terme, à creuser, potentiel épuisé, écartée">
              {CLIENT.algo.boutonScoring}
            </button>
          </div>
        )}
      </div>
    )
  }
  // M55-D stage 8 (décision Vic) : l'accueil devient une PAGE DE PRÉSENTATION — l'UNIQUE CTA
  // d'analyse vit dans le panneau Filtres (la Révélation). Ici : ce que LABUSE fait, sobrement,
  // et UN lien « Commencer → » qui ouvre la section Filtres. Disparaît après le premier geste.
  if (accueilVu) return null
  return <AccueilPreuves onCommencer={() => { setAccueilVu(); openFiltres() }} />
}

// M55-D stage 9 ter — ACCUEIL FINAL (texte figé Vic 10/08) : DEUX blocs et le lien, rien
// d'autre. Les chiffres du bloc 1 restent SERVIS par /accueil/chiffres (dynamiques, « i »
// sourcé chacun) — un chiffre null est masqué, jamais inventé. Aucune chaîne en dur (strings.ts).
// M55-H point 2 — refonte VISUELLE de l'accueil, contenu EXACT (texte figé Vic 9 ter) :
// hiérarchie titre → chiffres → ligne descriptive (tailles/graisses/interlignes étagés),
// « i » centrés sur leur chiffre (items-center, plus de flottement baseline), bouton
// « Commencer → » en pièce maîtresse : proportions généreuses, texte centré, FLÈCHE
// DESSINÉE (le caractère → flottait), hover (halo + glissement de flèche) et active
// (enfoncement) soignés. Tokens LABUSE inchangés (mint / surfaces / display).
function AccueilPreuves({ onCommencer }: { onCommencer: () => void }) {
  const q = useQuery({ queryKey: ['accueil-chiffres'], queryFn: getAccueilChiffres, staleTime: 3_600_000, retry: 1 })
  const d = q.data
  const nf = (n: number) => n.toLocaleString('fr-FR')
  const A = CLIENT.accueil
  // M55-J point 3 (décision Vic) : les trois « i » (parcelles / communes / sources) sont RETIRÉS.
  // Garde-fou fait : aucune des trois infobulles ne portait de réserve d'honnêteté (millésime,
  // « partiel », estimation) — c'étaient une paraphrase du chiffre (parcelles), une couverture
  // POSITIVE + source DGFiP (communes) et un pointeur vers la page Sources (sources). Le sourcing
  // détaillé (DEAL, DGFiP, INSEE, BODACC, Sitadel…) vit déjà sur la page Sources (accessible au
  // Rail). Suppression franche ; les chaînes CLIENT.accueil.src deviennent 0-caller.
  const Seg = ({ n, l }: { n: number | null | undefined; l: (s: string) => string }) => (
    n == null ? null : <span className="font-medium text-txt tabular-nums whitespace-nowrap">{l(nf(n))}</span>
  )
  // M55-I point 1 — CAUSE de la troncature du logo : un conteneur `flex justify-center` clippait
  // le haut du contenu qui déborde. Correctif conservé : le CONTENU est centré par marges
  // automatiques (`my-auto`) — elles centrent quand il y a de la place ET se réduisent à 0 quand
  // ça déborde, laissant le logo (en tête) TOUJOURS visible depuis le haut.
  // M55-L point 1 (décision Vic) : la section d'accueil est FIXE — pas de défilement, pas de
  // barre. `overflow-hidden` (au lieu de `overflow-y-auto`) : clip propre, aucune barre. Padding
  // vertical GÉNÉREUX (py-8, valeur DS) pour que la composition respire. Contrepartie assumée : à
  // une taille où le contenu dépasserait, le bas se clippe (my-auto garde le haut/logo visible) —
  // mesuré taille par taille (rapport), jamais de scroll réintroduit.
  return (
    <div data-accueil className="flex min-h-0 flex-1 flex-col items-center overflow-hidden px-7 py-6 text-center">
      {/* M55-J point 4 : titre ET paragraphe tirent leur largeur maximale d'UNE SEULE valeur
          partagée (--accueil-w) — plus deux largeurs en dur côte à côte. Le paragraphe, jadis
          plus étroit (max-w-[32ch]), s'aligne sur le titre → moins de retours à la ligne, moins
          de hauteur. L'acquis M55-I (justify-start + my-auto) reste : ce point réduit la hauteur
          du contenu, il ne remet PAS le conteneur en justify-center. */}
      <div data-accueil-contenu className="my-auto flex w-full flex-col items-center"
        style={{ ['--accueil-w' as string]: '240px' }}>
        <svg viewBox="0 0 240 82" className="h-7 w-[72px] shrink-0" fill="#2FE0A0" style={{ filter: 'drop-shadow(0 0 10px rgba(47,224,160,0.4))' }}>
          <path d="M2 15 C58 10 100 18 120 27 C140 18 182 10 238 15 C202 29 162 40 135 46 C127 49 122 53 120 60 C118 53 113 49 105 46 C78 40 38 29 2 15 Z" />
        </svg>
        {/* Ajustement Vic (9 ter) : le BOUTON d'abord — LE geste de la page. Contenu exact
            « Commencer → » : le libellé garde sa flèche, rendue en SVG aligné. */}
        <button data-commencer onClick={onCommencer}
          className="group mt-7 flex w-full shrink-0 items-center justify-center gap-2 rounded-xl bg-mint px-5 py-4 font-display text-[15px] font-bold text-mint-ink shadow-[0_0_24px_rgba(92,230,161,0.35)] transition-[box-shadow,filter,transform] duration-soft ease-cockpit hover:shadow-[0_0_38px_rgba(92,230,161,0.55)] hover:brightness-105 active:translate-y-[1px] active:brightness-95">
          <span>{A.commencer.replace(/\s*→\s*$/, '')}</span>
          <svg viewBox="0 0 16 16" aria-hidden="true"
            className="h-[15px] w-[15px] transition-transform duration-quick group-hover:translate-x-0.5">
            <path d="M2.5 8 H13 M9.5 3.5 L14 8 L9.5 12.5" fill="none" stroke="currentColor"
              strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
        <h3 className="mt-8 max-w-[var(--accueil-w)] font-display text-[13px] font-semibold leading-snug text-txt-hi">{A.b1Titre}</h3>
        <p className="mt-3 flex flex-wrap items-center justify-center gap-x-2.5 gap-y-1.5 text-[11px] leading-relaxed text-txt-mut">
          <Seg n={d?.parcelles} l={A.segParcelles} />
          <span aria-hidden className="text-mint">·</span>
          <Seg n={d?.communes} l={A.segCommunes} />
          <span aria-hidden className="text-mint">·</span>
          <Seg n={d?.sources} l={A.segSources} />
        </p>
        <p className="mt-3 max-w-[var(--accueil-w)] text-[9.5px] leading-relaxed text-txt-dim">{A.b1Suite.replace(' — ', '')}</p>
      </div>
    </div>
  )
}

export function LeftPanel() {
  const { panelOpen, togglePanel, verdict } = useApp()
  // Item 1 (UX V1, mobile) : sous 640 px le panneau occupait 100 % de l'écran — la carte
  // n'existait pas. Désormais la CARTE est l'écran d'accueil mobile ; COUCHES + légende
  // VERDICT vivent dans un tiroir escamotable (bouton « Couches » flottant).
  // M55-D stage 6 : tiroir mobile piloté par le store (le header-reflet l'ouvre aussi)
  const mobileOpen = useApp((st) => st.mobilePanelOpen)
  const setMobileOpen = useApp((st) => st.setMobilePanelOpen)
  // M14 B3 (QA-64) : « Couches » OUVERT PAR DÉFAUT tant que l'analyse LABUSE n'est pas affichée.
  // État partagé desktop/mobile. Plus d'auto-fermeture 10 s : c'est la BASCULE vers l'analyse
  // (`verdict` false→true) qui replie les couches, une seule fois — l'utilisateur peut rouvrir.
  // M55-D stage 9 bloc 4 : plus d'état LOCAL couchesOpen — l'exclusivité vit dans le store
  // (panneauSection), aucun chemin ne peut la contourner (le bug : openFiltres/« Commencer → »
  // ouvraient Filtres sans replier Couches, restée sur son état local par défaut).
  const panneauSection = useApp((st) => st.panneauSection)
  const setPanneauSection = useApp((st) => st.setPanneauSection)
  const couchesOpen = panneauSection === 'couches'
  const filtresOpen = panneauSection === 'filtres'
  // M55-K point 5 : `sectionFill` — quand rien ne suit les sections (ni accueil ni résultats),
  // la section OUVERTE est le dernier contenu → elle remplit la hauteur (et le séparateur
  // orphelin disparaît), fond continu jusqu'en bas. Sinon accueil/résultats (eux flex-1) filent.
  const accueilVu = useApp((st) => st.accueilVu)
  const sectionFill = accueilVu && !verdict
  const prevVerdict = useRef(verdict)
  useEffect(() => {
    // ═══ M55-M point 1 — TRANSITION DE L'AUTOMATE (explicite, à champ unique) ═══
    // L'affichage d'un listing (verdict false→true, tri factuel OU analyse révélée) est une ENTRÉE
    // de l'automate : Couches ET Filtres se RÉTRACTENT (`'listing'`) → le listing prend toute la
    // hauteur. Remplace la cible M55-J (« analyse ⇒ Filtres ouverte ») : la cible a évolué, c'est
    // le LISTING qui prime. Couvre aussi le RECHARGEMENT (al=1 / v=1) : le store boote verdict=false
    // puis l'effet de boot (App.tsx) l'allume → cette transition restaure l'état listing (pas Couches).
    if (verdict && !prevVerdict.current) { setPanneauSection('listing'); setAccueilVu() }
    prevVerdict.current = verdict
  }, [verdict])
  const setAccueilVu = useApp((st) => st.setAccueilVu)
  // ═══ M55-I point 2 / M55-M point 1 — ACCORDÉON = AUTOMATE À TROIS ÉTATS (règle Vic) ═══
  // `panneauSection` ('couches' | 'filtres' | 'listing' — JAMAIS null) : A = Couches ouverte, B =
  // Filtres ouverte, C = LISTING (les deux rétractées, uniquement quand `verdict` — un listing est
  // affiché). `couchesOpen`/`filtresOpen` DÉRIVENT (=== 'couches'/'filtres') ; en C les deux sont
  // false. Il reste STRUCTURELLEMENT impossible d'avoir deux sections ouvertes (le type l'interdit).
  // Les toggles ci-dessous : cliquer une section FERMÉE l'ouvre (exclusivité) ; cliquer la section
  // OUVERTE la REFERME vers le listing (C) — mais SEULEMENT si un listing existe (`verdict`) ; hors
  // listing, refermer est impossible (invariant M55-I : exactement une ouverte) → no-op.
  const toggleCouches = () => { setAccueilVu(); setPanneauSection(couchesOpen ? (verdict ? 'listing' : 'couches') : 'couches') }
  const toggleFiltres = () => { setAccueilVu(); setPanneauSection(filtresOpen ? (verdict ? 'listing' : 'filtres') : 'filtres') }
  return (
    <>
      {/* ── desktop ≥ 640 px : panneau latéral inchangé ── */}
      {!panelOpen ? (
        <button
          onClick={togglePanel}
          className="hidden h-full w-8 shrink-0 items-start justify-center border-r border-line bg-surface-1 pt-5 text-txt-dim hover:text-txt sm:flex"
          title="Déplier le panneau"
        >
          ›
        </button>
      ) : (
        <aside className="hidden h-full w-[clamp(240px,24vw,340px)] shrink-0 flex-col border-r border-line bg-surface-1 sm:flex">
          <div className="flex shrink-0 items-center justify-between px-5 pt-4">
            <h2 className="text-sm font-medium text-txt-hi">Cartes</h2>
            {/* M55-B point 5 : une FERMETURE, pas un repli → croix (×), cohérent avec la fiche
                parcelle et le contexte commune (croix partout). Le ré-affichage se fait par la
                languette « › » quand le panneau est masqué. */}
            <CroixEntete onClick={togglePanel} title="Fermer le panneau" />
          </div>
          <LayersSection open={couchesOpen} onToggle={toggleCouches} fill={sectionFill} closable={verdict} />
          <FiltresSection open={filtresOpen} onToggle={toggleFiltres} fill={sectionFill} closable={verdict} />
          {!sectionFill && <div className="mx-5 my-3 shrink-0 border-t border-line" />}
          <VerdictHero />
          {verdict && <ResultsSection />}
        </aside>
      )}

      {/* ── mobile < 640 px : carte plein écran, panneau en tiroir ── */}
      {!mobileOpen && (
        <button
          data-couches-mobile
          onClick={() => setMobileOpen(true)}
          className="absolute bottom-16 left-4 z-30 flex items-center gap-2 rounded-full border border-line-2 bg-surface-2 px-4 py-2 text-xs font-medium text-txt shadow-elev-2 sm:hidden"
          title="Couches, analyse et résultats"
        >
          <svg viewBox="0 0 20 20" className="h-4 w-4 text-mint">
            <path d="M10 3.5 L17 7 L10 10.5 L3 7 Z" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
            <path d="M3 10.5 L10 14 L17 10.5" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
            <path d="M3 13.5 L10 17 L17 13.5" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" opacity="0.55" />
          </svg>
          Couches
        </button>
      )}
      {mobileOpen && (
        <div data-couches-drawer className="absolute inset-0 z-40 flex sm:hidden">
          <div className="absolute inset-0 bg-black/55" onClick={() => setMobileOpen(false)} />
          <aside className="relative flex h-full w-[300px] max-w-[86%] flex-col border-r border-line bg-surface-1 shadow-elev-3">
            <div className="flex shrink-0 items-center justify-between px-5 pt-4">
              <h2 className="text-sm font-medium text-txt-hi">Cartes</h2>
              <CroixEntete dataAttr="data-couches-fermer" onClick={() => setMobileOpen(false)} title="Revenir à la carte" />
            </div>
            <LayersSection open={couchesOpen} onToggle={toggleCouches} fill={sectionFill} closable={verdict} />
            <FiltresSection open={filtresOpen} onToggle={toggleFiltres} fill={sectionFill} closable={verdict} />
            {!sectionFill && <div className="mx-5 my-3 shrink-0 border-t border-line" />}
            <div className="shrink-0 px-5 pb-1"><Legend inline /></div>
            <VerdictHero />
            {verdict && <ResultsSection />}
          </aside>
        </div>
      )}
    </>
  )
}
