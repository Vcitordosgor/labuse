import { useEffect, useRef, useState } from 'react'
import { useApp, type LayerToggles } from '../../store/useApp'
import { Legend } from '../map/Legend'
import { LAYER_INFO } from '../../lib/layers'
import { countActiveFilters } from '../../lib/filters'
import { getAccueilChiffres } from '../../lib/api'
import { MODULES } from '../outils/registry'
import { useQuery } from '@tanstack/react-query'
import { Tip } from '../Tip'
import { ChevronSection, CroixEntete } from './ChevronSection'
import { ResultsSection } from './ResultsSection'
import { FiltreLabuse } from './FiltreLabuse'
import { CLIENT } from '../../lib/strings'
import { TIER_DECLASSE_META, TIER_V2_META, tierChipLabel } from '../../lib/status'

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
            {/* M137 — LE CHIP D'ABORD (mot servi partout), puis son explication ; le libellé long
                ne vit que dans cette phrase, accolé à son chip. Le chip prend la couleur du palier. */}
            <p className="text-[12px] leading-relaxed text-txt-mut">
              <b className="font-semibold" style={{ color }}>{tierChipLabel(key)}</b>
              {' — '}{CLIENT.revelation.defTiers[key]}
            </p>
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
  // M62-P1 (g) : les toggles « Verdict — toute l'île » (couleurs_verdict) et « Renouvellement »
  // (renouv) sont RETIRÉS du panneau (P5, diagnostic P0-3 : sûr — OFF par défaut, seuls setters =
  // ce panneau ; le filtre `renouvellement`, le module et le bloc fiche sont indépendants). Les clés
  // de store `layers.couleurs_verdict`/`layers.renouv` sont CONSERVÉES (défaut false) → MapView/Legend
  // compilent et lisent false (mode opinion reste accessible par verdict && analyseLabuse).
  // M55-A (fusion A) : couche PARCELLAIRE UNIQUE — colore d'emblée toutes les parcelles par famille
  // ET révèle le code exact au zoom / au clic (l'ancienne case « Colorisation » est fusionnée ici).
  { key: 'zonage_parcelle', label: 'Zonage PLU par parcelle (calibré)' },
  // M55-A : zones OFFICIELLES du GPU (polygones bruts du document opposable) — distinctes du
  // rattachement calibré à la parcelle ; couvrent aussi l'espace non parcellaire (voirie, domaine public).
  { key: 'zonage', label: 'Zones du PLU officiel (brut)' },
  { key: 'ppr', label: 'PPR multirisque' },
  // M106 P1 : les aléas DEAL séparés — la séparation inondation/mouvement de terrain n'existe
  // PAS dans le zonage réglementaire PPR (document multirisque) ; elle vit dans la carte d'aléas.
  { key: 'alea_inondation', label: 'Aléa inondation' },
  { key: 'alea_mvt', label: 'Aléa mouvement de terrain' },
  // M137-U — deux items ÉQUIPEMENTS étiquetés par source (jamais fusionnés → pas de doublon caché).
  { key: 'equipements', label: 'Équipements (OpenStreetMap)' },
  { key: 'equipements_bpe', label: 'Équipements (INSEE BPE)' },
  { key: 'communes', label: 'Limites communes' },
  { key: 'parc', label: 'Parc national' },
  // M137-U — ZNIEFF : contrainte (patrimoine naturel), à côté de Parc national / PPR.
  { key: 'znieff', label: 'ZNIEFF — patrimoine naturel' },
  // M6.1 item 2 : réserve domaniale littorale — libellé métier exact exigé par le mandat
  { key: 'cinquante_pas', label: '50 pas géométriques' },
  // M106 P4 : transport public (tracés + pôles + téléphérique) et lignes HT (contrainte)
  { key: 'transport', label: 'Transport public' },
  { key: 'axes', label: 'Axes structurants' },
  { key: 'lignes_ht', label: 'Lignes haute tension' },
  // M134 — couche « Dispositifs et périmètres ». Jamais un sigle nu : chaque libellé développe.
  { key: 'qpv', label: 'QPV — quartier prioritaire' },
  { key: 'tva_primo', label: 'TVA réduite primo-accédant (QPV + 500 m)' },
  { key: 'anru', label: 'NPNRU / ANRU — renouvellement urbain' },
  { key: 'zfang', label: 'ZFANG — zone franche d’activité' },
  { key: 'frr', label: 'FRR — France Ruralités Revitalisation' },
]

// M56-C · DA §5 — les couches groupées par FAMILLES silencieuses (une .gcard par famille,
// micro-label au-dessus). L'ordre des couches et les libellés sont INCHANGÉS ; seul le
// regroupement visuel est ajouté. M62-P1 (g) : la famille « L'analyse LABUSE » (couleurs_verdict +
// renouv) est retirée ; les 10 clés restantes sont couvertes une et une seule fois.
const LAYER_FAMILIES: { famille: string; keys: (keyof LayerToggles)[] }[] = [
  { famille: 'Le fond', keys: ['parcelles', 'limites', 'communes'] },
  { famille: 'Les zonages', keys: ['zonage_parcelle', 'zonage'] },
  { famille: 'Risques et protections', keys: ['ppr', 'alea_inondation', 'alea_mvt', 'equipements', 'equipements_bpe', 'parc', 'znieff', 'cinquante_pas'] },
  // M106 P4 — nouvelle famille : l'accès (transport) et les réseaux contraignants (HT)
  { famille: 'Accès et réseaux', keys: ['transport', 'axes', 'lignes_ht'] },
  // M134 — Dispositifs et périmètres : opérationnels (QPV + sa bande TVA, NPNRU/ANRU) puis
  // fiscaux à la maille COMMUNE (ZFANG, FRR). L'ANRU quitte « Risques » pour ici (un seul endroit).
  { famille: 'Dispositifs et périmètres', keys: ['qpv', 'tva_primo', 'anru', 'zfang', 'frr'] },
]
const LAYER_LABEL: Record<string, string> = Object.fromEntries(LAYERS.map((l) => [l.key, l.label]))

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
          <div className="flex flex-col gap-3.5">
            {LAYER_FAMILIES.map(({ famille, keys }) => (
              <div key={famille}>
                <p className="layer-cat mb-1.5 block">{famille}</p>
                <div className="gcard">
                  {keys.map((key) => {
                    const on = layers[key]
                    const info = LAYER_INFO[key] ?? ''
                    const label = LAYER_LABEL[key] ?? key
                    return (
                      <div key={key} className="flex items-center justify-between gap-2 border-b border-line px-3 py-2.5 last:border-b-0">
                        <button
                          data-layer={key}
                          onClick={() => toggleLayer(key)}
                          className="flex min-h-[24px] flex-1 items-center gap-3 text-left transition-colors duration-quick"
                        >
                          <span className={`flex h-[13px] w-[13px] shrink-0 items-center justify-center rounded-[3px] ${on ? 'bg-mint' : 'border border-line-3'}`}>
                            {on && (
                              <svg viewBox="0 0 10 10" className="h-2.5 w-2.5">
                                <polyline points="2,5.5 4,7.5 8,3" fill="none" stroke="#06301A" strokeWidth="1.8" />
                              </svg>
                            )}
                          </span>
                          <span className={`text-xs ${on ? 'text-txt-hi' : 'text-[#97A39B]'}`}>{label}</span>
                        </button>
                        <LayerInfoPill info={info} />
                      </div>
                    )
                  })}
                </div>
              </div>
            ))}
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
              title="La méthode : le tri, la fraction « 1/5 sous 1 an », la validation">
              {CLIENT.algo.bouton}
            </button>
            <button data-scoring-open onClick={() => setAlgoModale('scoring')}
              className="flex-1 whitespace-nowrap rounded-full border border-mint/40 px-1.5 py-0.5 text-[10px] font-medium text-mint hover:bg-mint/10"
              title="Le sens des paliers : Priorité, À suivre, Long terme, Neutre, Faible, Écartée">
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
const nfFr = (n: number) => n.toLocaleString('fr-FR')   // séparateur = espace fine (U+202F)
const prefersReducedMotion = () =>
  typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

// M65 P2c — COMPTEUR : la valeur monte de 0 à sa cible en 1,2 s (sortie cubique) AU MONTAGE, une
// seule fois par session (drapeau sessionStorage). Sous prefers-reduced-motion → valeur directe.
function Compteur({ value }: { value: number }) {
  const CLE = 'labuse.accueil.compteur'
  const dejaVu = () => { try { return sessionStorage.getItem(CLE) === '1' } catch { return false } }
  const [n, setN] = useState(() => (dejaVu() || prefersReducedMotion() ? value : 0))
  useEffect(() => {
    if (dejaVu() || prefersReducedMotion()) { setN(value); return }
    try { sessionStorage.setItem(CLE, '1') } catch { /* mode privé : on anime quand même */ }
    let raf = 0
    const t0 = performance.now(), dur = 1200
    const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 3)
    const tick = (now: number) => {
      const p = Math.min(1, (now - t0) / dur)
      setN(Math.round(easeOutCubic(p) * value))
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [value])
  return <>{nfFr(n)}</>
}

// M65 P2a — une CASE du bandeau : chiffre (servi) au-dessus, libellé court en dessous. Masquée
// (cellule vide) si le chiffre est null — jamais inventé.
function CaseChiffre({ n, label, anime }: { n: number | null | undefined; label: string; anime?: boolean }) {
  if (n == null) return <div className="bg-[#121815]" />
  return (
    <div className="flex flex-col items-center justify-center bg-[#121815] py-3">
      <span className="text-[19px] font-medium tabular-nums text-[#F4F6F5]">
        {anime ? <Compteur value={n} /> : nfFr(n)}
      </span>
      <span className="mt-1 text-[11px] text-[#7C8A83]">{label}</span>
    </div>
  )
}

// M83 B — une PORTE du bloc « PAR OÙ COMMENCER » (gabarit .porte-outil). Tranche mint / mauve / neutre.
function Porte({ ton, icone, titre, sous, onClick }: {
  ton: 'verte' | 'ia' | 'neutre'; icone: string; titre: string; sous: string; onClick: () => void
}) {
  const bord = ton === 'verte' ? 'border-l-mint' : ton === 'ia' ? 'border-l-[#7F77DD]' : 'border-l-[#2A362F]'
  const icoBg = ton === 'verte' ? 'bg-[#12291D] text-mint' : ton === 'ia' ? 'bg-[#1A1730] text-[#AFA9EC]' : 'bg-[#141B17] text-[#8B9990]'
  const fleche = ton === 'verte' ? 'text-mint' : ton === 'ia' ? 'text-[#AFA9EC]' : 'text-[#8B9990]'
  return (
    <button data-accueil-porte={ton} onClick={onClick}
      className={`flex w-full items-center gap-3 rounded-r-[9px] border-l-2 ${bord} bg-[#101612] px-3.5 py-3 text-left transition-colors duration-quick hover:brightness-110`}>
      <span className={`flex h-[30px] w-[30px] shrink-0 items-center justify-center rounded-[7px] text-[15px] ${icoBg}`}>{icone}</span>
      <span className="min-w-0 flex-1">
        <span className="block text-[13px] font-medium text-txt">{titre}</span>
        <span className="block text-[10.5px] leading-snug text-txt-dim">{sous}</span>
      </span>
      <span className={`text-[14px] ${fleche}`}>→</span>
    </button>
  )
}

function AccueilPreuves({ onCommencer }: { onCommencer: () => void }) {
  const q = useQuery({ queryKey: ['accueil-chiffres'], queryFn: getAccueilChiffres, staleTime: 3_600_000, retry: 1 })
  const d = q.data
  const A = CLIENT.accueil
  const { setView, setAccueilVu, toggleOutils } = useApp()
  // M87 P1 — le bloc « Cette semaine » (M83) est RETIRÉ (composant + appel /accueil/cette-semaine + calcul
  // d'activité). Le claim et la ligne de fraîcheur restent : le foncier vit sans compteur 7 jours en tête.
  return (
    <div data-accueil className="flex min-h-0 flex-1 flex-col overflow-y-auto px-5 py-5">
      {/* B1 — la promesse (2e ligne en --mint) */}
      <p className="text-[17px] font-medium leading-tight text-txt">Tout le foncier de La Réunion.</p>
      <p className="mb-4 text-[17px] font-medium leading-tight text-mint">Au même endroit.</p>

      {/* B2 — les chiffres descendent d'un cran (compacts, dynamiques) */}
      <div className="mb-5 grid grid-cols-3 gap-px overflow-hidden rounded-[9px] bg-[#1E2622]">
        <CaseChiffre n={d?.parcelles} label={A.labelParcelles} anime />
        <CaseChiffre n={d?.communes} label={A.labelCommunes} />
        <CaseChiffre n={d?.sources} label={A.labelSources} />
      </div>

      {/* B3 — trois portes */}
      <p className="mb-2 font-mono text-[9px] uppercase tracking-[.14em] text-[#5C6A63]">Par où commencer</p>
      <div className="mb-5 flex flex-col gap-1.5">
        <Porte ton="verte" icone="⌕" titre="Explorer la carte" sous="activez une couche, cliquez une parcelle"
          onClick={onCommencer} />
        <Porte ton="ia" icone="✦" titre="Demander au Copilote" sous="« terrain 1 000 m² à Saint-Paul »"
          onClick={() => { setAccueilVu(); setView('copilote') }} />{/* FIX-ACCUEIL A2 : consomme l'accueil comme les 2 autres portes (plus de ré-affichage au retour) */}
        <Porte ton="neutre" icone="⚙" titre="Ouvrir un outil" sous={`${MODULES.filter((m) => !m.hidden).length} outils — trouver, instruire, agir, comprendre, suivre`}
          onClick={() => { setAccueilVu(); toggleOutils() }} />{/* GB-001 : compte des outils VISIBLES (comme le tiroir Rail), plus de « 16 » qui incluait 3 alias hidden */}
      </div>

      {/* M87 P1 — bloc « Cette semaine » RETIRÉ (M83). */}

      {/* B5 — la ligne de fraîcheur */}
      <div className="mt-auto flex items-center gap-2 border-t border-[#1E2622] pt-3">
        <span className="h-[5px] w-[5px] shrink-0 rounded-full bg-mint" />
        {/* FIX-ACCUEIL A1 : les 3 chiffres n'affichent pas de date (« i » par chiffre retiré en M87) —
            on n'en re-promet donc plus une ICI. La phrase reste honnête à l'échelle de l'app : chaque
            donnée est datée à sa source (fiche : statut Sourcé/Estimé + date ; page Sources : millésime). */}
        <span className="text-[10.5px] leading-snug text-[#7C8A83]">Données à jour — cadastre, PLU, permis, ventes, risques. Chaque donnée est datée à sa source.</span>
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
  const accueilVu = useApp((st) => st.accueilVu)
  // M55-N point 7 (décision Vic) : à l'état ACCUEIL (page de présentation affichée : !accueilVu &&
  // !verdict), les DEUX sections (Couches et Filtres) sont RÉTRACTÉES → l'accueil prend la pleine
  // hauteur (fin du clip mesuré M55-L P1). Même esprit que le `listing` de M55-M : « deux sections
  // fermées » est un état LÉGAL aussi pour l'accueil. `panneauSection` (champ unique) reste
  // 'couches' par défaut EN COULISSE ; l'accueil est un CONTEXTE d'entrée (dérivé de accueilVu, un
  // signal déjà existant) qui prime tant qu'il est affiché. Le quitter (Commencer/openFiltres, ou
  // rouvrir une section à la main → setAccueilVu) lève l'override → la section reprend (défaut Couches).
  const enAccueil = !accueilVu && !verdict
  const couchesOpen = !enAccueil && panneauSection === 'couches'
  const filtresOpen = !enAccueil && panneauSection === 'filtres'
  // M55-K point 5 : `sectionFill` — quand rien ne suit les sections (ni accueil ni résultats),
  // la section OUVERTE est le dernier contenu → elle remplit la hauteur (et le séparateur
  // orphelin disparaît), fond continu jusqu'en bas. Sinon accueil/résultats (eux flex-1) filent.
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
  // Les toggles : cliquer une section FERMÉE l'ouvre (exclusivité) ; cliquer la section OUVERTE la
  // REFERME (→ 'listing', état C). M62-P1 (f) : la fermeture n'est PLUS conditionnée à `verdict` —
  // le chevron bascule dans les DEUX sens même sans listing (le bug « ouvre mais ne ferme pas » venait
  // du no-op pré-verdict). Les 3 états M55-M restent (couches / filtres / listing) ; 'listing'
  // pré-verdict = les deux sections rétractées (le VerdictHero prend la place, aucun résultat encore).
  const toggleCouches = () => { setAccueilVu(); setPanneauSection(couchesOpen ? 'listing' : 'couches') }
  const toggleFiltres = () => { setAccueilVu(); setPanneauSection(filtresOpen ? 'listing' : 'filtres') }
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
          <LayersSection open={couchesOpen} onToggle={toggleCouches} fill={sectionFill} closable />
          <FiltresSection open={filtresOpen} onToggle={toggleFiltres} fill={sectionFill} closable />
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
            <LayersSection open={couchesOpen} onToggle={toggleCouches} fill={sectionFill} closable />
            <FiltresSection open={filtresOpen} onToggle={toggleFiltres} fill={sectionFill} closable />
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
