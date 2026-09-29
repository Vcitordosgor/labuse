import { useQuery } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'
import { getScoringFraction } from '../../lib/api'
import { useApp } from '../../store/useApp'
import { Legend } from '../map/Legend'
import { NouvellesCouches } from '../map/CouchesTuyau'  // COUCHES-TUYAU-1 lot 2
import { countActiveFilters } from '../../lib/filters'
import { MODULES } from '../outils/registry'
import { ChevronSection, CroixEntete } from './ChevronSection'
import { ResultsSection } from './ResultsSection'
import { FiltreLabuse } from './FiltreLabuse'
import { CLIENT } from '../../lib/strings'
import { BANDE_META, LEGEND_V2_ORDER, SIGNAL_META, TIER_V2_META, tierChipLabel } from '../../lib/status'

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
export function AlgoExplainer({ onClose }: { onClose: () => void }) {
  // FRONT-CHIFFRES-2 (F26) — seuil bas + paliers SERVIS (config scoring_client) : le bloc « fraction »
  // du modal les interpole au lieu de coder « 1/50 » / la liste des paliers en dur.
  const sf = useQuery({ queryKey: ['scoring-fraction'], queryFn: getScoringFraction, staleTime: 60 * 60 * 1000 }).data
  return (
    <Modale id="classement" titre={CLIENT.algo.titre} onClose={onClose}>
      <div className="mt-3 flex flex-col gap-3">
        {CLIENT.algo.corps(sf?.seuil_bas_denominateur ?? 50, sf?.paliers ?? [2, 3, 4, 5, 10, 20, 50]).map((s) => (
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
// PALIERS-1 — le « i » des paliers montre LE vocabulaire unique : les quatre paliers, aucun autre.
const SCORING_PALIERS: { key: string; color: string }[] = LEGEND_V2_ORDER.map((key) => ({
  key, color: TIER_V2_META[key].color,
}))
// ANALYSE-2 — LE PANNEAU UNIQUE « Comprendre l'analyse » (remplace Info classement / Info scoring).
// Trois sections en français client, dans l'ordre : le classement (bande + les 6 catégories, colorées
// depuis BANDE_META), le signal de mutation, la logique. Aucun mot de l'ancien moteur, aucune proba.
const _COMPRENDRE_BANDE_COLOR: Record<string, string> = {
  Excellente: BANDE_META.A.color, Bonne: BANDE_META.B.color, 'À étudier': BANDE_META.C.color,
  Faible: BANDE_META.D.color, 'Non retenue': BANDE_META['0'].color, 'Analyse incomplète': BANDE_META.NC.color,
}
export function ComprendreAnalyse({ onClose }: { onClose: () => void }) {
  const c = CLIENT.comprendre
  return (
    <Modale id="comprendre" titre={c.titre} onClose={onClose}>
      <div className="mt-3 flex flex-col gap-4">
        {/* 1 · le classement */}
        <div>
          <p className="label-caps text-[9.5px]">{c.classement.h}</p>
          <p className="mt-1 text-[12px] leading-relaxed text-txt-mut">{c.classement.p}</p>
          <div className="mt-2 flex flex-col gap-1.5">
            {c.classement.bandes.map((b) => (
              <div key={b.label} className="flex items-start gap-2">
                <span className="mt-[5px] h-2 w-2 shrink-0 rounded-full" style={{ background: _COMPRENDRE_BANDE_COLOR[b.label] }} />
                <p className="text-[12px] leading-relaxed text-txt-mut">
                  <b className="font-semibold" style={{ color: _COMPRENDRE_BANDE_COLOR[b.label] }}>{b.label}</b>{' — '}{b.d}
                </p>
              </div>
            ))}
          </div>
          <p className="mt-2 text-[11.5px] leading-relaxed text-txt-dim">{c.classement.monte}</p>
          <p className="mt-1 text-[11.5px] leading-relaxed text-txt-dim">{c.classement.descend}</p>
        </div>
        {/* 2 · le signal */}
        <div>
          <p className="label-caps text-[9.5px]">{c.signal.h}</p>
          <p className="mt-1 text-[12px] leading-relaxed text-txt-mut">{c.signal.p}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {(['fort', 'moyen', 'faible'] as const).map((s) => (
              <span key={s} className="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10.5px] font-medium"
                style={{ borderColor: `${SIGNAL_META[s].color}66`, color: SIGNAL_META[s].color }}>
                {SIGNAL_META[s].label}
              </span>
            ))}
          </div>
        </div>
        {/* 3 · la logique */}
        <div>
          <p className="label-caps text-[9.5px]">{c.logique.h}</p>
          <p className="mt-1 text-[12px] leading-relaxed text-txt-mut">{c.logique.p}</p>
        </div>
      </div>
    </Modale>
  )
}

export function ScoringExplainer({ onClose }: { onClose: () => void }) {
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





// M12 C1 / M14 B3 (QA-64, reprise M13-D1/QA-47) — « Couches » est un TIROIR REPLIABLE, OUVERT
// PAR DÉFAUT tant que l'analyse LABUSE n'est pas affichée. Il se referme quand on clique
// « Afficher l'analyse LABUSE » (bascule `verdict`), pour libérer la place. Plus d'auto-fermeture
// 10 s. Ouvert, il POUSSE le contenu du dessous (flux flex : jamais de recouvrement).
// M55-K point 5 : `fill` — quand la section ouverte est le DERNIER contenu du panneau (ni accueil
// ni résultats en dessous), elle occupe la hauteur restante (flex-1) et son tiroir remplit
// (pas de plafond max-h) → plus de gros gap vide sous le contenu, le fond reste continu jusqu'en
// bas. Sinon (accueil/résultats présents = eux flex-1), comportement plafonné inchangé.

function LayersSection({ open, onToggle, fill }: {
  open: boolean
  onToggle: () => void
  fill?: boolean
  closable?: boolean   // M55-M point 1 : un listing existe → la section ouverte peut se refermer (→ listing)
}) {
  return (
    <div className={`px-5 pt-4 ${open && fill ? 'flex min-h-0 flex-1 flex-col' : 'shrink-0'}`}>
      <button
        data-couches-toggle
        onClick={onToggle}
        aria-expanded={open}
        className="group flex w-full items-center justify-between gap-2 text-left"
      >
        <span className="label-caps">Couches</span>
        <ChevronSection open={open} />
      </button>
      {open && (
        // plafonné + scrollable : sur un volet court, la liste des résultats garde sa hauteur.
        // QA-46 (M13-C) : overflow-x-clip — un `overflow-y-auto` calcule overflow-x=auto, si bien
        // que les tooltips absolus (Tip, `w-max`) débordant du volet étroit y déclenchaient une
        // BARRE HORIZONTALE fantôme. `clip` sur x supprime la barre sans créer de conteneur de
        // défilement, le tooltip reste peint. Défaut identique corrigé partout (fiche/CRM/tri).
        <div data-couches-drawer className={`mt-3 overflow-y-auto overflow-x-clip ${fill ? 'min-h-0 flex-1' : 'max-h-[38vh]'}`}>
          <div className="flex flex-col gap-3.5">
            {/* COUCHES-RETRAIT-1 lot 2 — l'ancien panneau de bascules V1 (LAYER_FAMILIES / getMapLayer)
                est retiré ; le tuyau (« Couches », 56 couches en tuiles vectorielles, rangées par
                famille, cochables) est désormais le SEUL panneau de couches. */}
            <NouvellesCouches />
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
function FiltresSection({ open, onToggle, onRetract, fill }: { open: boolean; onToggle: () => void; onRetract?: () => void; fill?: boolean; closable?: boolean }) {
  const { filters } = useApp()
  const n = countActiveFilters(filters)
  return (
    <div className={`px-5 pt-4 ${open && fill ? 'flex min-h-0 flex-1 flex-col' : 'shrink-0'}`}>
      <button data-filtres-toggle onClick={onToggle} aria-expanded={open}
        className="group flex w-full items-center justify-between gap-2 text-left">
        <span className="label-caps">Filtres</span>
        <span className="flex items-center gap-3">
          {/* DA-029 — pastille VERTE (aplat opaque `bg-mint text-mint-on`) du nombre de filtres actifs. */}
          {n > 0 && (
            <span className="rounded-full bg-mint px-1.5 py-0.5 text-[10px] font-medium text-mint-on">{n} actif{n > 1 ? 's' : ''}</span>
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
  // ANALYSE-3 (§1) — le récap des critères (analyseRecap) a QUITTÉ le bandeau (le nom de commune y
  // faisait doublon avec les filtres globaux et les cartes) : l'en-tête tient sur une ligne.
  // M55-J point 5 : DEUX modales distinctes (classement / scoring), état partagé au store.
  const algoModale = useApp((s) => s.algoModale)
  const setAlgoModale = useApp((s) => s.setAlgoModale)
  // ANALYSE-3 (§1) — l'en-tête tient sur UNE ligne (~50 px) : « ✓ Analyse LABUSE » à gauche, le bouton
  // « Comprendre » (icône i) et « Retour » à droite. Le nom de commune (analyseRecap) et le mot
  // « affichée » sont retirés (doublon filtres globaux + cartes) ; le bouton pleine largeur devient une
  // pastille en ligne. Le titre « RÉSULTATS » disparaît (ResultsSection).
  if (verdict) {
    return (
      <div className={`mx-5 mb-1 flex shrink-0 items-center gap-2 rounded-lg px-3 py-1.5 shadow-elev-1 ${analyse ? 'bg-mint/[0.08]' : 'bg-surface-2'}`}>
        {algoModale === 'classement' && <AlgoExplainer onClose={() => setAlgoModale(null)} />}
        {algoModale === 'scoring' && <ScoringExplainer onClose={() => setAlgoModale(null)} />}
        {algoModale === 'comprendre' && <ComprendreAnalyse onClose={() => setAlgoModale(null)} />}
        <span className={`min-w-0 flex-1 truncate text-[11.5px] font-medium ${analyse ? 'text-mint' : 'text-txt-mut'}`}>
          {analyse ? '✓ Analyse LABUSE' : 'Tri factuel — sans analyse'}</span>
        {analyse && (
          <button data-comprendre-open onClick={() => setAlgoModale('comprendre')}
            className="inline-flex shrink-0 items-center gap-1 rounded-ctl border border-mint/40 px-2 py-0.5 text-[11px] font-medium text-mint hover:bg-mint/10">
            <span className="flex h-[13px] w-[13px] items-center justify-center rounded-full border border-mint/50 text-[9px] font-bold leading-none">i</span>
            Comprendre
          </button>
        )}
        {/* M55-J point 7 : « Retour » — destination UNIQUE (store.retourFiltres). */}
        <button data-verdict-off onClick={retourFiltres}
          className="shrink-0 rounded-ctl border border-line-2 px-2 py-0.5 text-[10.5px] text-txt-mut hover:border-txt-dim hover:text-txt">
          Retour
        </button>
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
// RETOURS-5 T1 — le COMPTEUR animé et les helpers de format (nfFr/prefersReducedMotion) servaient la
// ligne de chiffres, retirée : supprimés avec elle.

// RETOURS-4 S8 — les 3 chiffres SERVIS sont désormais une LIGNE sous le titre (statline dans
// AccueilPreuves) ; le composant CaseChiffre (grille v2/v4) est retiré. La ligne ne peut plus être rognée
// à aucun zoom (fin définitive du bug S1.2) et reste servie par /accueil/chiffres (jamais en dur).

// RETOURS-3 R1 (maquette-accueil-v2) — une CARTE d'entrée du bloc « PAR OÙ COMMENCER ». Tuile 44 px
// unique, glyphe SVG 23 px trait 2.1, teinte franche au repos (vert, mauve pour l'IA), survol plein
// (classes .acc-entry, cf. index.css). Les 4 cartes sont VERTES sauf le Copilote (mauve, seule surface IA).
const ACC_ICONS: Record<string, JSX.Element> = {
  carte: <><circle cx="11" cy="11" r="7" /><path d="m16.2 16.2 4.3 4.3" /></>,
  radar: <><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="2.6" fill="currentColor" stroke="none" /></>,
  copilote: <path d="M12 2.5 14 9l6.5 2L14 13l-2 6.5L10 13l-6.5-2L10 9l2-6.5Z" strokeLinejoin="round" />,
  outil: <><circle cx="12" cy="12" r="3" /><path d="M19.4 13a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V20a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 18.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z" /></>,
  // RECETTE-5 (V13) — horloge « Remonter le temps » (5e porte de l'accueil).
  temps: <><circle cx="12" cy="12" r="8.5" /><path d="M12 7.3V12l3.1 1.9" /></>,
}
function AccEntry({ ton, icone, titre, sous, onClick }: {
  ton: 'mint' | 'mauve'; icone: keyof typeof ACC_ICONS; titre: string; sous: string; onClick: () => void
}) {
  // RETOURS-4 S8 — AUCUN tooltip sur les cartes (le libellé est déjà écrit dessus).
  return (
    <button data-accueil-porte={ton} onClick={onClick} className={`acc-entry ${ton}`}>
      <span className="acc-tile">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">{ACC_ICONS[icone]}</svg>
      </span>
      {/* RETOURS-4 S1.3 — titres ET descriptions sur UNE ligne (truncate = nowrap + ellipse) : tiennent à 360 px. */}
      <span className="min-w-0 flex-1">
        <span className="block truncate text-[14px] font-medium">{titre}</span>
        <span className="acc-desc mt-0.5 block truncate text-[11.5px] text-txt-dim">{sous}</span>
      </span>
      <span className="acc-arrow">→</span>
    </button>
  )
}

function AccueilPreuves({ onCommencer }: { onCommencer: () => void }) {
  const { setView, setAccueilVu, toggleOutils } = useApp()
  // PAGES-RANGEMENT-1 (lot 3) — la ligne de FRAÎCHEUR (pastille ok/warn/error + phrase d'état, lue de
  // /accueil/fraicheur) est RETIRÉE de l'accueil client : c'est de l'exploitation, elle vit au dashboard
  // admin. L'appel /accueil/fraicheur est supprimé du front ; il ne reste que la porte vers Sources.
  // M87 P1 — le bloc « Cette semaine » (M83) était déjà retiré (composant + appel /accueil/cette-semaine).
  return (
    <div data-accueil className="flex min-h-0 flex-1 flex-col overflow-y-auto px-5 py-5">
      {/* B1 — la promesse (2e ligne en --mint) */}
      <p className="text-[17px] font-medium leading-tight text-txt">Tout le foncier de La Réunion.</p>
      <p className="mb-5 text-[17px] font-medium leading-tight text-mint">Au même endroit.</p>

      {/* RETOURS-5 T1 — la LIGNE de chiffres est RETIRÉE (« 64 sources » passait à la ligne, et une donnée
          coupée est pire qu'absente). Le titre est suivi directement de « PAR OÙ COMMENCER ». L'appel
          /accueil/chiffres est supprimé du front (endpoint utilisé UNIQUEMENT ici — cf. compte-rendu). */}
      <p className="mb-2 font-mono text-[9px] uppercase tracking-[.14em] text-[#5C6A63]">Par où commencer</p>
      <div className="mb-5 flex flex-col gap-2">
        <AccEntry ton="mint" icone="carte" titre="Explorer la carte" sous="couches, filtres, parcelles"
          onClick={onCommencer} />
        {/* OUTILS-1 B1 — le Radar est une porte : vue de premier niveau, consomme l'accueil comme les autres. */}
        <AccEntry ton="mint" icone="radar" titre="Suivre le marché — Radar" sous="les biens en vente"
          onClick={() => { setAccueilVu(); setView('radar') }} />
        <AccEntry ton="mauve" icone="copilote" titre="Demander au Copilote" sous="« terrain 1 000 m² à Saint-Paul »"
          onClick={() => { setAccueilVu(); setView('copilote') }} />{/* seule surface IA → mauve */}
        {/* GB-001 : compte des outils VISIBLES (comme le tiroir Rail), dynamique — S7 : 15 après la fusion Veille→Scan. */}
        <AccEntry ton="mint" icone="outil" titre="Ouvrir un outil" sous={`${MODULES.filter((m) => !m.hidden).length} outils fonciers`}
          onClick={() => { setAccueilVu(); toggleOutils() }} />
        {/* RECETTE-6 (D2, décision Vic) — « Remonter le temps » RETIRÉ de l'accueil : il vit désormais
            comme 6e bouton de la rangée d'outils de la fiche parcelle (pré-rempli sur la parcelle). */}
      </div>

      {/* M87 P1 — bloc « Cette semaine » RETIRÉ (M83). */}

      {/* PAGES-RANGEMENT-1 (lot 3) — la pastille d'état (ok/warn/error) et la phrase de fraîcheur sont
          retirées ; reste une ligne neutre + la porte vers la page Sources (quelles données, pas leur état). */}
      <div className="mt-auto flex items-center gap-2 border-t border-[#1E2622] pt-3">
        <span className="text-[10.5px] leading-snug text-[#7C8A83]">Toutes les données au même endroit.</span>
        <button data-accueil-sources onClick={() => { setAccueilVu(); setView('sources') }}
          className="ml-auto shrink-0 whitespace-nowrap text-[10.5px] text-mint hover:underline">voir les données →</button>
      </div>
    </div>
  )
}

export function LeftPanel() {
  const { panelOpen, togglePanel, verdict } = useApp()
  // DA-029 — nombre de filtres actifs, visible sur la languette même panneau FERMÉ.
  const nFiltresActifs = countActiveFilters(useApp((st) => st.filters))
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
  // FINITIONS-1 (P2, décision Vic) — « cliquer referme » : cliquer la section OUVERTE la referme
  // VRAIMENT (état 'listing' = les deux rétractées), même sans verdict. On lève donc la coercion
  // RECETTE-5 (V11) qui rouvrait Couches dès qu'aucune section n'était ouverte — elle EMPÊCHAIT la
  // fermeture. Les chemins automatiques posent la section EXPLICITEMENT (démarrage = 'couches' au store ;
  // « retirer l'analyse » = 'filtres' via retourFiltres ; verdict = 'listing' avec un vrai listing) :
  // aucun ne dépend de cette coercion, donc rien ne régresse. Quand les deux sont fermées sans verdict,
  // le VerdictHero occupe la place (jamais un vide noir).
  const couchesOpen = !enAccueil && panneauSection === 'couches'
  const filtresOpen = !enAccueil && panneauSection === 'filtres'
  // GB-031 — Échap ferme le panneau Filtres (retour à Couches, section par défaut), comme le patron
  // overlay (Modale, ModulePanel). Gardes : on ne ferme pas si l'utilisateur tape dans un champ, ni
  // si une modale algo est ouverte (elle a la priorité sur Échap).
  useEffect(() => {
    if (!filtresOpen) return
    const h = (e: KeyboardEvent) => {
      if (e.key !== 'Escape' || document.querySelector('[data-algo-overlay]')) return
      const el = document.activeElement
      if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA')) return
      setPanneauSection('couches')
    }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [filtresOpen, setPanneauSection])
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
          className="hidden h-full w-8 shrink-0 flex-col items-center justify-start gap-1.5 border-r border-line bg-surface-1 pt-5 text-txt-dim hover:text-txt sm:flex"
          aria-label="Déplier le panneau"
        >
          ›
          {/* DA-029 — pastille VERTE du nombre de filtres actifs, visible panneau fermé. */}
          {nFiltresActifs > 0 && (
            <span className="rounded-full bg-mint px-1 py-0.5 text-[10px] font-medium leading-none text-mint-on">{nFiltresActifs}</span>
          )}
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
          {/* RETOURS-7 Z9 — « Voir les N parcelles » REFERME le panneau Filtres (→ 'listing') et
              rend la place à la liste. L'état ouvert/fermé suit l'action, pas l'historique de nav. */}
          <FiltresSection open={filtresOpen} onToggle={toggleFiltres} onRetract={() => setPanneauSection('listing')} fill={sectionFill} closable />
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
          <aside className="apparition relative flex h-full w-[300px] max-w-[86%] flex-col border-r border-line bg-surface-1 shadow-elev-3">
            <div className="flex shrink-0 items-center justify-between px-5 pt-4">
              <h2 className="text-sm font-medium text-txt-hi">Cartes</h2>
              <CroixEntete dataAttr="data-couches-fermer" onClick={() => setMobileOpen(false)} title="Revenir à la carte" />
            </div>
            <LayersSection open={couchesOpen} onToggle={toggleCouches} fill={sectionFill} closable />
            {/* RETOURS-7 Z9 — « Voir les N parcelles » REFERME le panneau Filtres (→ 'listing') et
              rend la place à la liste. L'état ouvert/fermé suit l'action, pas l'historique de nav. */}
          <FiltresSection open={filtresOpen} onToggle={toggleFiltres} onRetract={() => setPanneauSection('listing')} fill={sectionFill} closable />
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
