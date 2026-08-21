import { create } from 'zustand'
import type { FicheLine } from '../lib/types'
import type { FilterTier } from '../lib/status'

// M26-B : 'copilote' = l'écran Copilote (instruction de dossier, event log SSE) — vue de
// premier niveau, la maquette B4 est pleine largeur (pas un module du panneau 320 px).
// M65 P4 : la vue 'ia' (IAStub « Recherche ») est retirée du rail et de l'app — la recherche NL
// vit dans l'omnibox du header, le montage de projet dans le Copilote.
export type View = 'cartes' | 'crm' | 'sources' | 'projets' | 'copilote'

export interface LayerToggles {
  zonage: boolean
  zonage_parcelle: boolean // M6.1 / M55-A : couche parcellaire UNIQUE — colore toutes les parcelles
                           // par famille PLU (U/AU/A/N), + étiquette du code au zoom et popup au clic
                           // (l'ancienne case « colorisation » y est fusionnée, M55-A fusion A)
  parcelles: boolean
  ppr: boolean
  parc: boolean
  znieff: boolean       // M137-U : ZNIEFF (inventaire patrimoine naturel, type I/II) — CONTRAINTE
  limites: boolean
  anru: boolean
  equipements: boolean         // équipements OpenStreetMap (kind 'amenite')
  equipements_bpe: boolean     // M137-U : équipements INSEE BPE (kind 'amenite_bpe') — item séparé
  communes: boolean   // P11 : limites communales (ligne verte, contours officiels)
  cinquante_pas: boolean // M6.1 : réserve des 50 pas géométriques (bande littorale outre-mer)
  alea_inondation: boolean // M106 P1 : aléa inondation DEAL (kind=georisque_alea, subtype dédié) —
  alea_mvt: boolean        // le zonage PPR réglementaire reste agrégé (multirisque insécable)
  transport: boolean       // M106 P4 : transport public (tracés GTFS + pôles d'échange + Papang)
  lignes_ht: boolean       // M106 P4 : lignes haute tension BD TOPO (contrainte, tireté anthracite)
  axes: boolean            // M106-B P3 : axes structurants BD TOPO (importance IGN 1-2, ardoise)
  renouv: boolean     // M-RENOUV : segment Renouvellement (occupées, potentiel) — OFF par défaut
  couleurs_verdict: boolean // M55-G point 8 : palette des tiers en COUCHE activable — imposée
                            // seulement en mode analyse ; en tri factuel rien n'est imposé
  // M134 — couche « Dispositifs et périmètres » (anru y est déjà réuni)
  qpv: boolean         // quartiers prioritaires (QPV 2024, géométrie)
  tva_primo: boolean   // bande TVA réduite primo-accédant (QPV + 500 m, dérivé LABUSE)
  zfang: boolean       // zone franche d'activité (aplat commune, régime renforcé/standard)
  frr: boolean         // france ruralités revitalisation (aplat commune)
}

// Filtres actifs — appliqués EN MÊME TEMPS à la carte, la liste et les compteurs, et
// SÉRIALISÉS DANS L'URL (#f=…) : une recherche = un lien partageable.
// M5.1 : le PILOTAGE passe aux TIERS v2 (`tiers`) — le filtre `statuts` (matrice) et le
// tier v1.3 `brulantes` disparaissent de l'app (API : deprecated, servis par legacy=1).
export interface Filters {
  tiers: FilterTier[]        // vide = univers v2 hors étage 0 servi (M30 : déclassements inclus)
  scoreMin: number | null
  surfaceMin: number | null
  surfaceMax: number | null
  sdpMin: number | null      // SDP résiduelle minimale (m²)
  evenement: boolean         // seulement les parcelles à événement (BODACC rouge)
  veille: boolean            // veille succession (radar patrimonial)
  horsCopro: boolean         // toggle copro : masquer les copropriétés
  flags: string[]            // flags actifs requis (au moins un)
  flagsExclus: string[]      // copilote-projet : contraintes RÉDHIBITOIRES (aucun de ces flags)
  communes: string[]         // R2 : secteur du cadreur (multi-communes, mode île)
  personneMorale: boolean    // M11 B2 : détenue par une personne morale (DGFiP public — SCI/société/…)
  zonagePlu: string[]        // M11 B2 : zonage PLU par famille (U/AU/A/N) — au moins une
  // M45 (P2a) — barre niveau 1 + tiroir « Puis-je construire ? »
  sdpMax: number | null              // SDP résiduelle maximale (m²)
  constructibilite: string[]         // constructible / au_conditionnelle / fermee / inconstructible / rnu
  etatSol: string[]                  // nu / bati_marginal / bati_sature / bati_revele
  capaciteMin: number | null         // capacité logements ESTIMÉE >= N (dérivée SDP)
  zonePlu: string[]                  // zone PLU EXACTE (libellés, ex. UA, UB, 2AU)
  analyseLabuse: boolean             // interrupteur : appliquer le classement LABUSE (tiers). ON par défaut.
  // M45 (P2d) — tiroirs éco / mutation / propriété / veille
  sousDensite: boolean
  multMin: number | null
  rangMax: number | null
  renouvellement: boolean
  proprietaireType: string[]
  droitsResiduels: string[]   // M129-D P3 : 'encore' | 'maximum' (fait M125)         // pm / bailleur / pp
  etatSociete: string[]              // cessee / radiee / procedure (M43 factuel)
  copro: string[]                    // avec / sans (RNIC)
  npnru: boolean
  adresseAbsente: boolean
  // M45-B (Lot 1) — tiroir Économie
  budgetMax: number | null           // prix d'achat max admissible ≤ budget (Mon budget)
  chargeMin: number | null
  chargeMax: number | null
  prixMarcheMin: number | null       // €/m² terrain DVF
  prixMarcheMax: number | null
  marcheFiable: boolean              // secteur n≥3 ventes
  caMin: number | null               // bilan CA indicatif ≥ N
  modeBRentable: boolean             // mode B rentable au paramètre courant (curseur session)
  // M55-D stage 6 — SIGNAUX DE VIE (8 validés Vic) : événements SOURCÉS, filtrables sans analyse.
  // OU entre signaux du groupe, ET avec le reste. Clés : procedure, permis_actif, permis_caduc,
  // defisc, nu_pm, friche, cession, assemblage.
  signaux: string[]
}

export const EMPTY_FILTERS: Filters = {
  tiers: [], scoreMin: null, surfaceMin: null, surfaceMax: null, sdpMin: null,
  evenement: false, veille: false, horsCopro: false,
  flags: [], flagsExclus: [], communes: [],
  personneMorale: false, zonagePlu: [],
  sdpMax: null, constructibilite: [], etatSol: [], capaciteMin: null, zonePlu: [],
  analyseLabuse: false,   // M55-D stage 4 : interrupteur « regard LABUSE » ÉTEINT par défaut (tri factuel)
  sousDensite: false, multMin: null, rangMax: null, renouvellement: false,
  proprietaireType: [], droitsResiduels: [], etatSociete: [], copro: [], npnru: false, adresseAbsente: false,
  budgetMax: null, chargeMin: null, chargeMax: null, prixMarcheMin: null, prixMarcheMax: null,
  marcheFiable: false, caMin: null, modeBRentable: false,
  signaux: [],
}

// M45-B (Lot 2) — curseur mode B PARTAGÉ (session unique, rien persisté) : travaux + loyer +
// rendement, lus par la fiche ET le filtre (mode_b_rentable). Défauts = plafond BOFiP base + repères.
export interface ModeBParams { travauxM2: number; loyerM2: number; rendementPct: number }
// M59-P1 (bug défaut travaux) : SOURCE UNIQUE = le back (bilan.py MODE_B_TRAVAUX_M2_DEFAUT = 1500,
// ce qui a servi à la mesure P0 : fiche initiale = compute_mode_b sans paramètre). Ce miroir front
// DOIT suivre cette valeur — sinon le montant initial (1500) et le montant après premier mouvement
// de curseur (ex-1200) divergeaient. Toute évolution se fait côté back.
export const MODE_B_DEFAUT: ModeBParams = { travauxM2: 1500, loyerM2: 12.21, rendementPct: 6 }

// brouillon d'un projet issu de l'entretien : la fiche + la dérivation moteur (filtres, SDP
// besoin) — porté jusqu'à la restitution où « Enregistrer ce projet » le persiste (V3).
export interface ProjetBrouillon {
  fiche: Record<string, unknown>
  nom: string
  filtres: Record<string, unknown>
  sdp_besoin_m2: number | null
}

// restitution : compteur + top cliquables ; V3 : « pourquoi » par parcelle + contexte projet.
export interface IaTop { idu: string; commune: string; q_score: number; mult_v2?: number | null; rang_v2?: number | null; pourquoi?: string[] }
export interface IaRestitution {
  n: number
  phrase: string
  top: IaTop[]
  // présent = restitution de PROJET : active « Enregistrer ce projet » + « Exporter PDF »
  projet?: { nom: string; fiche: Record<string, unknown>; id?: number; programme?: Record<string, unknown> | null } | null
  // Item 2 (UX V1) : la traduction EXACTE du serveur voyage jusqu'à la restitution — l'utilisateur
  // ne prend JAMAIS un repli mots-clés pour une vraie traduction (badge « mode mots-clés »).
  explanation?: string | null
  stub?: boolean
  // M11 B1 : critères compris mais hors des 14 champs — voyagent jusqu'ici (on quitte la vue IA),
  // affichés en bannière ⚠ sur la restitution : jamais avalés, jamais confondus avec un résultat servi.
  criteres_non_appliques?: string[]
  // Ajout C (UX V1) : à 0 résultat, proposition de relâchement — le critère numérique le plus
  // serré est retiré et la recherche relancée d'un clic (jamais un zéro sec).
  relance?: { label: string; raw: Record<string, unknown> } | null
}

export type Basemap = 'dark' | 'clair' | 'plan' | 'ortho'   // M63-P1 : + fond clair
// M65 P8 (précision Vic) : le SOMBRE est le fond par défaut — au chargement à froid COMME après un
// rechargement. « Clair » est une BASCULE MANUELLE, jamais l'état initial → on NE restaure PLUS le
// choix depuis localStorage (la persistance M63 aurait rouvert la carte en Clair après un reload).
// Le choix vit dans le store le temps de la session ; un reload repart toujours en Sombre.
const readBasemap = (): Basemap => 'dark'
export type OrthoYear = 'now' | '2000' | '1950'
export type MapTool = 'distance' | 'surface' | 'alti' | 'zone'

interface AppState {
  // Commune active — null = « Toute l'île » (défaut). Pilote carte, compteurs, liste, modules,
  // et vit dans l'URL (#…&c=…). Sélecteur dans le header.
  commune: string | null
  setCommune: (c: string | null) => void
  setCommunesFilter: (list: string[]) => void
  // M55-D stage 9 bloc 4 : l'ACCORDÉON est une propriété de l'ÉTAT — UNE seule section ouverte
  // à la fois, quel que soit le chemin d'ouverture (titre, chevron, header, « Commencer → »,
  // programmatique). M55-H point 8 (décision Vic) : hors listing, TOUJOURS une section ouverte.
  // M55-M point 1 (décision Vic) : l'automate gagne un TROISIÈME état — `'listing'` = les DEUX
  // sections rétractées, légal UNIQUEMENT quand un listing est affiché (tri factuel ou analyse
  // révélée) → le listing prend toute la hauteur. Hors listing l'invariant M55-I tient (exactement
  // une ouverte : 'couches' ou 'filtres'). Champ UNIQUE, jamais deux booléens.
  panneauSection: 'couches' | 'filtres' | 'listing'
  setPanneauSection: (s: 'couches' | 'filtres' | 'listing') => void
  // M55-D stage 8 : l'écran d'accueil (présentation) disparaît après le PREMIER geste de la
  // session (Commencer, ouverture d'une section, analyse) — état de session, jamais persisté.
  accueilVu: boolean
  setAccueilVu: () => void
  mobilePanelOpen: boolean
  setMobilePanelOpen: (v: boolean) => void
  openFiltres: () => void
  openListing: () => void
  // volet CONTEXTE COMMUNE (SRU/ANRU/PLH/marché) — ouvert depuis le sélecteur ou le header
  contexteCommune: string | null
  setContexteCommune: (c: string | null) => void
  // M55-C point 4 : cliquer un NOM de commune = UN seul geste à trois effets — ouvrir la fiche,
  // caler le PÉRIMÈTRE sur la commune (comme le sélecteur : liste/compteurs/filtres suivent) et
  // recadrer la carte (l'effet de fit sur `commune` s'en charge). À câbler partout où un nom de
  // commune est cliquable, pour un comportement identique.
  focusCommune: (c: string) => void
  // toast produit (C6) : une action utilisateur ne tombe JAMAIS dans le vide
  toast: string | null
  setToast: (t: string | null) => void
  // M55-J point 5 : DEUX modales distinctes, une seule ouverte à la fois — « classement » (la
  // méthode : tri, ×N, validation) et « scoring » (le sens des paliers). null = fermée.
  algoModale: 'classement' | 'scoring' | null
  setAlgoModale: (v: 'classement' | 'scoring' | null) => void
  // M55-M point 3 : le RÉCAP des critères DU RUN d'analyse (« 2 communes, zone U, terrain nu, … »),
  // FIGÉ au lancement depuis le SNAPSHOT (jamais l'état courant des filtres — même invariant que la
  // carte d'analyse M55-J p1). Écrit par FiltreLabuse.lancer(), lu par le bandeau (VerdictHero) qui
  // porte désormais les critères (le bloc « ANALYSE EN COURS » a disparu). null = pas d'analyse décrite.
  analyseRecap: string | null
  setAnalyseRecap: (s: string | null) => void
  // M55-G point 10 : ce que la carte PEINT réellement à l'écran (zoom, mode île/commune,
  // couches) — écrit par MapView, lu par la légende. Règle : une légende n'existe que si
  // ses couleurs sont effectivement à l'écran (jamais de légende orpheline).
  mapPeint: { parcelles: boolean; equipements: boolean; zonage: boolean }
  setMapPeint: (p: { parcelles: boolean; equipements: boolean; zonage: boolean }) => void
  // R1 (revue Vic n°2) : le VERDICT est un GESTE — la carte s'ouvre en cadastre neutre,
  // « Afficher l'analyse LABUSE » (P2, revue n°3) allume couleurs + entonnoir + liste. URL : v=1.
  verdict: boolean
  setVerdict: (v: boolean) => void
  // M55-J point 7 : « Retour » (ex-« Masquer ») — LA destination unique, définie ICI (pas
  // recopiée dans chaque handler) : sortir de la vue verdict (analyse OU tri factuel) et
  // atterrir sur Filtres OUVERT et éditable (analyse coupée), jamais sur Couches.
  retourFiltres: () => void
  // R2 : restitution chorégraphiée du copilote (compteur animé + top 3 cliquables).
  // V3 : le top peut porter le « pourquoi » relié au projet ; `projet` active « Enregistrer / PDF ».
  iaRestitution: IaRestitution | null
  setIaRestitution: (r: IaRestitution | null) => void
  // copilote-projet : brouillon issu de l'entretien (« Lancer la recherche ») → « Enregistrer ce projet » (V3)
  projetBrouillon: ProjetBrouillon | null
  setProjetBrouillon: (b: ProjetBrouillon | null) => void
  // Parcours de sélection (Tinder) : projet en cours de tri — la carte passe en fond plein,
  // la carte de décision flotte par-dessus. null = pas de parcours actif.
  parcours: { id: number; nom: string } | null
  setParcours: (p: { id: number; nom: string } | null) => void
  // entrée dans le parcours : bascule sur la carte (fond) ET arme le parcours en un seul geste
  // (setView nettoierait parcours — nav exclusive) ; ferme les panneaux de la vue quittée.
  // NB : openParcours PRÉSERVE openProjet → « Quitter » le tri revient sur le kanban du projet.
  openParcours: (p: { id: number; nom: string }) => void
  // Projet UNIFIÉ : le projet OUVERT (kanban 3 colonnes) dans la vue Projets. null = liste « Mes
  // projets ». setView/nav principale le remet à null (retour à la liste). setOpenProjet(null) aussi.
  openProjet: { id: number; nom: string } | null
  setOpenProjet: (p: { id: number; nom: string } | null) => void
  view: View
  setView: (v: View) => void
  // F2 (M12) : « + Décrire un projet » ouvre l'entretien « Votre projet » DIRECTEMENT (pas l'écran
  // à deux portes). La valeur = amorce de l'entretien ; consommée (remise à null) par le copilote
  // à l'ouverture de l'entretien. null = accès normal au copilote (deux portes).
  entretienDirect: string | null
  ouvrirEntretien: (amorce?: string) => void
  clearEntretienDirect: () => void
  outilsOpen: boolean
  toggleOutils: () => void
  selectedIdu: string | null
  select: (idu: string | null) => void
  // M55-L point 5 — verdict À LA DEMANDE : la fiche s'ouvre sur un bouton « Demander l'analyse
  // LABUSE » ; au clic, le bloc verdict se déploie. Choix MÉMORISÉ PAR PARCELLE pour la SESSION
  // (jamais persisté) : rouvrir la même fiche ne redemande pas le clic ; nouvelle session = retour
  // au bouton. Idu → true = analyse demandée.
  verdictRevele: Record<string, boolean>
  revelerVerdict: (idu: string) => void
  // M61 P2 — le bloc Analyse est un TIROIR repliable : déplié par défaut à la première demande,
  // l'état de repli est mémorisé PAR PARCELLE pour la session (idu → true = replié). INDÉPENDANT
  // de l'accordéon exclusif des 7 tiroirs (le replier/déplier ne ferme aucun autre tiroir).
  analyseReplie: Record<string, boolean>
  toggleAnalyseReplie: (idu: string) => void
  // M55-L point 10 — TIROIRS de la fiche en accordéon EXCLUSIF : un seul ouvert à la fois, zéro
  // ouvert légal (état initial). État à champ unique PAR PARCELLE (session) : idu → id du tiroir
  // ouvert, ou null (tout fermé).
  ficheTiroir: Record<string, string | null>
  setFicheTiroir: (idu: string, tiroir: string | null) => void
  layers: LayerToggles
  toggleLayer: (k: keyof LayerToggles) => void
  panelOpen: boolean
  togglePanel: () => void
  query: string
  setQuery: (q: string) => void
  filters: Filters
  setFilter: <K extends keyof Filters>(k: K, v: Filters[K]) => void
  setFilters: (f: Filters) => void
  resetFilters: () => void
  modeB: ModeBParams                                   // M45-B (L2) : curseur session partagé fiche/filtre
  setModeB: (p: Partial<ModeBParams>) => void
  sourcesFocus: string | null // nom de source à surligner sur la page Sources
  openSources: (focus?: string | null) => void
  // M104 — LA section SURVEILLANCE (fusion Suivis + Secteurs + Critères, arbitrage 17/08) :
  // une entrée, trois volets. En surimpression de la carte (l'outil de dessin reste dispo).
  surveillanceOpen: boolean
  surveillanceVolet: 'parcelles' | 'secteurs' | 'criteres'
  openSurveillance: (volet?: 'parcelles' | 'secteurs' | 'criteres') => void
  setSurveillanceOpen: (v: boolean) => void
  toggleSurveillance: () => void
  // anciennes entrées (Secteurs / Suivis) : REDIRECTIONS vers la section unifiée — jamais un 404.
  toggleVeilles: () => void
  toggleSuivis: () => void
  // M54-EXPO-3 A8 — comparateur : 2 à 3 parcelles côte à côte (GET /compare). Sélection cumulative
  // depuis la fiche (« Comparer ») et la shortlist ; panneau en surimpression.
  compareIdus: string[]
  compareOpen: boolean
  addToCompare: (idu: string) => void
  removeFromCompare: (idu: string) => void
  clearCompare: () => void
  setCompareOpen: (v: boolean) => void
  // M82 — mode « cliquer sur la carte » : la carte reste cliquable (barre compacte), le clic AJOUTE
  // une parcelle à la comparaison (motif du clic-sélection d'Assemblage).
  comparePicking: boolean
  setComparePicking: (v: boolean) => void
  // Drawer source (depuis une ligne de fiche) : jamais un cul-de-sac, la fiche reste ouverte dessous.
  sourceLine: FicheLine | null
  openSourceDrawer: (line: FicheLine) => void
  closeSourceDrawer: () => void
  // Carto : fond de plan, ortho historique, relief 3D, outil de mesure, zone dessinée (filtre).
  basemap: Basemap
  setBasemap: (b: Basemap) => void
  orthoYear: OrthoYear
  setOrthoYear: (y: OrthoYear) => void
  terrain3d: boolean
  toggleTerrain: () => void
  tool: MapTool | null
  setTool: (t: MapTool | null) => void
  zone: [number, number][] | null // polygone [lng,lat] dessiné → filtre les résultats
  setZone: (z: [number, number][] | null) => void
  // ── Modules outils (filtres savants, accent violet) ──
  module: string | null
  setModule: (m: string | null) => void
  // M15 D1 : comparateur « Remonter le temps » — les DEUX fonds choisis vivent dans le store
  // pour que les sélecteurs soient rendus dans le BANDEAU GAUCHE (M08), pas en surimpression carte.
  cmpLeft: string
  cmpRight: string
  setCmpLeft: (k: string) => void
  setCmpRight: (k: string) => void
  // ce que le module affiche sur la carte : parcelles surlignées (idus) + géométries propres (lots, permis)
  moduleMap: { idus: string[]; extra: unknown | null }
  setModuleMap: (m: { idus: string[]; extra: unknown | null }) => void
  // bloc module en tête de fiche : idu → lignes [libellé, valeur]
  moduleFiche: Record<string, { module: string; lines: [string, string][] }>
  setModuleFiche: (f: Record<string, { module: string; lines: [string, string][] }>) => void
  flyTo: { center: [number, number]; zoom: number } | null
  setFlyTo: (f: { center: [number, number]; zoom: number } | null) => void
  msel: string[] // sélection multi-parcelles (module assemblage M16)
  setMsel: (m: string[]) => void
  m22Prefill: Record<string, unknown> | null // copilote → formulaire programme (M22)
  setM22Prefill: (p: Record<string, unknown> | null) => void
  m02Prefill: string | null // fiche → scan patrimoine du propriétaire (SIREN)
  setM02Prefill: (s: string | null) => void
  pluPrefill: { insee: string; zone: string | null } | null // fiche → annuaire PLU (O13) : commune + zone
  setPluPrefill: (p: { insee: string; zone: string | null } | null) => void
  // M137-P — l'outil PLU unifié ouvre directement une de ses 3 vues (consommé-puis-remis-à-null par le hub).
  pluVue: 'annuaire' | 'procedure' | 'changement' | null
  setPluVue: (v: 'annuaire' | 'procedure' | 'changement' | null) => void
  // M60 P1a — fiche → outil Calculette foncière (M23) : IDU pré-rempli (saute le ParcelPicker).
  calcPrefill: string | null
  setCalcPrefill: (s: string | null) => void
  // M-ENTREE — amorçage parcelle PARTAGÉ (un seul motif, plusieurs consommateurs) : Faisabilité
  // (M22, mode « par parcelle ») et Assemblage (M16, 1ʳᵉ du lot). Consommation-puis-reset : la porte
  // fait setParcelPrefill(idu)+setModule(clé) ; l'outil lit parcelPrefill AU MONTAGE, l'amorce à sa
  // façon, puis setParcelPrefill(null). Ouvert sans porte (page Outils) → reste null → inchangé.
  // BACKLOG : à terme calcPrefill (M23) devrait rejoindre ce champ — pas dans ce mandat (on ne
  // refactore pas ce qui marche pendant qu'on ajoute).
  parcelPrefill: string | null
  setParcelPrefill: (s: string | null) => void
  // calculette de charge foncière (mandat bilan-calculette) : les hypothèses courantes du
  // promoteur, partagées avec le bouton PDF (l'export reflète « selon vos hypothèses »)
  calculette: { cout_construction_m2: number; marge_frais_pct: number; prix_demande_eur: number | null } | null
  setCalculette: (c: { cout_construction_m2: number; marge_frais_pct: number; prix_demande_eur: number | null } | null) => void
}

export const useApp = create<AppState>((set) => ({
  commune: null,
  // changer de commune remet la zone dessinée à zéro (elle appartenait à l'ancienne emprise)
  // M55-D stage 6 : le MAÎTRE du périmètre est le filtre `filters.communes` (multi). `commune`
  // (mono) est DÉRIVÉE — elle pilote la carte (fit/mode commune) et les endpoints existants :
  // 1 commune sélectionnée → mode commune ; 0 ou ≥2 → mode île (le filtre borne les résultats).
  // M55-D stage 9 bloc 3 : le panneau ne touche QUE le filtre — la carte reste où elle est
  // (décocher ≠ dézoomer). Lien à SENS UNIQUE : setCommune (header/clic-commune) propose
  // (zoom + pré-coche) ; le filtre dispose. « Toute l'île » au header dézoome ET décoche.
  setCommunesFilter: (list) => set((s) => ({
    filters: { ...s.filters, communes: list },
    zone: null,
  })),
  // compat : tous les appelants existants (header-reflet, omnibox, clic-commune M55-C, outils)
  // passent par ici — un seul état, plus de parallèle.
  setCommune: (commune) => set((s) => ({
    filters: { ...s.filters, communes: commune ? [commune] : [] },
    commune, zone: null,
  })),
  contexteCommune: null,
  setContexteCommune: (contexteCommune) => set({ contexteCommune }),
  // M55-C point 4 : périmètre + fiche en un geste ; le recadrage carte suit (effet fit sur `commune`).
  // M55-D stage 6 : écrit dans le filtre communes (maître) — un seul état.
  focusCommune: (c) => set((s) => ({
    filters: { ...s.filters, communes: [c] }, commune: c, contexteCommune: c, zone: null,
  })),
  panneauSection: 'couches',   // Couches ouverte par défaut (comportement historique M14)
  setPanneauSection: (panneauSection) => set({ panneauSection }),
  accueilVu: false,
  setAccueilVu: () => set({ accueilVu: true }),
  mobilePanelOpen: false,
  setMobilePanelOpen: (mobilePanelOpen) => set({ mobilePanelOpen }),
  openFiltres: () => set({ panelOpen: true, panneauSection: 'filtres', mobilePanelOpen: true, accueilVu: true }),
  // M137-I — le panneau OUVERT sur le LISTING (les parcelles retenues). Utilisé quand on arrive sur la
  // carte avec un résultat DÉJÀ prêt à voir (ex. « Voir sur la carte » du Copilote) : plus de filtre à
  // confirmer. Doit aller de pair avec `verdict: true` (c'est lui qui monte ResultsSection).
  openListing: () => set({ panelOpen: true, panneauSection: 'listing', mobilePanelOpen: true, accueilVu: true }),
  toast: null,
  setToast: (toast) => set({ toast }),
  algoModale: null,
  setAlgoModale: (algoModale) => set({ algoModale }),
  analyseRecap: null,
  setAnalyseRecap: (analyseRecap) => set({ analyseRecap }),
  mapPeint: { parcelles: false, equipements: false, zonage: false },
  // garde d'égalité : le handler zoom de la carte appelle à chaque frame — pas de re-render inutile
  setMapPeint: (p) => set((s) =>
    s.mapPeint.parcelles === p.parcelles && s.mapPeint.equipements === p.equipements
      && s.mapPeint.zonage === p.zonage ? {} : { mapPeint: p }),
  verdict: false,
  setVerdict: (verdict) => set({ verdict }),
  retourFiltres: () => set((s) => ({
    verdict: false, panneauSection: 'filtres', analyseRecap: null,
    filters: { ...s.filters, analyseLabuse: false },
  })),
  iaRestitution: null,
  setIaRestitution: (iaRestitution) => set({ iaRestitution }),
  projetBrouillon: null,
  setProjetBrouillon: (projetBrouillon) => set({ projetBrouillon }),
  view: 'cartes',
  // B2 (mandat bilan-calculette) — NAVIGATION EXCLUSIVE : changer de vue principale FERME la
  // fiche parcelle et tout panneau secondaire de la vue quittée (module, contexte commune,
  // drawer source, restitution IA, tiroir outils). Une seule vue active à la fois — plus de
  // fiche/kanban fantôme qui persiste à travers les vues. Les flux « ouvrir une fiche depuis
  // X » appellent setView('cartes') PUIS select(idu) (ordre respecté partout).
  // M87 P3 — bug de fermeture : les panneaux Secteurs (« Mes veilles ») et Suivis se FERMENT à tout
  // changement de section, sans exception (sinon ils réapparaissent au retour sur Cartes).
  setView: (view) => set({ view, outilsOpen: false, selectedIdu: null, module: null,
    contexteCommune: null, sourceLine: null, iaRestitution: null, parcours: null, openProjet: null,
    entretienDirect: null, surveillanceOpen: false }),
  // M65 P4 : « Décrire un projet » bascule sur le Copilote ET arme l'amorce (même nettoyage
  // exclusif que setView). L'IAStub (view 'ia') est retiré ; CopiloteView lit `entretienDirect`
  // au montage et l'amorce prend place dans le brief (la recherche NL reste dans l'omnibox header).
  entretienDirect: null,
  ouvrirEntretien: (amorce = '') => set({ entretienDirect: amorce, view: 'copilote', outilsOpen: false,
    selectedIdu: null, module: null, contexteCommune: null, sourceLine: null, iaRestitution: null,
    parcours: null, openProjet: null }),
  clearEntretienDirect: () => set({ entretienDirect: null }),
  parcours: null,
  setParcours: (parcours) => set({ parcours }),
  openParcours: (parcours) => set({ parcours, view: 'cartes', outilsOpen: false,
    selectedIdu: null, module: null, contexteCommune: null, sourceLine: null, iaRestitution: null }),
  // Ouvrir un projet = la vue kanban unifiée (nav exclusive) ; retour du tri via cette même action.
  openProjet: null,
  setOpenProjet: (openProjet) => set({ openProjet, view: 'projets', outilsOpen: false,
    selectedIdu: null, module: null, contexteCommune: null, sourceLine: null,
    iaRestitution: null, parcours: null }),
  outilsOpen: false,
  // P1 (dernière passe) — NAV EXCLUSIVE : ouvrir Outils bascule sur le fond CARTE (le tiroir
  // outils vit au-dessus de la carte) et FERME la vue précédente (IA/Projets/CRM) + ses panneaux.
  // Sans ça, ouvrir Outils depuis Projets laissait « Mes projets » en fond derrière le tiroir.
  // M60 P1e — `selectedIdu:null` RETIRÉ : la fiche (carte-overlay) n'est PAS une « vue » ; le rationale
  // nav-exclusive vise view/module/parcours/openProjet/iaRestitution. Effacer la parcelle en ouvrant le
  // tiroir Outils était un vestige du reset large (dette M55-L) — un outil doit pouvoir lire la parcelle
  // regardée (M09/M10 la pré-remplissent), et la fiche doit se retrouver à la fermeture de l'outil.
  toggleOutils: () => set((s) => s.outilsOpen
    ? { outilsOpen: false }
    : { outilsOpen: true, view: 'cartes', module: null,
        contexteCommune: null, sourceLine: null, iaRestitution: null, parcours: null, openProjet: null }),
  selectedIdu: null,
  // G1 (M12) : filet de sécurité global — un idu vide ou la chaîne « undefined » (issue d'un
  // `String(undefined)` sur une feature sans propriété idu) n'ouvre JAMAIS la fiche. Elle
  // afficherait un titre « undefined » et un faux « serveur injoignable ». `null` ferme la fiche.
  select: (idu) => set({ selectedIdu: idu === '' || idu === 'undefined' ? null : idu }),
  verdictRevele: {},
  revelerVerdict: (idu) => set((s) => ({ verdictRevele: { ...s.verdictRevele, [idu]: true } })),
  analyseReplie: {},
  toggleAnalyseReplie: (idu) => set((s) => ({ analyseReplie: { ...s.analyseReplie, [idu]: !s.analyseReplie[idu] } })),
  ficheTiroir: {},
  setFicheTiroir: (idu, tiroir) => set((s) => ({ ficheTiroir: { ...s.ficheTiroir, [idu]: tiroir } })),
  // M55-A (fusion A) : plus de `zonage_colorise` — la couche parcellaire unique `zonage_parcelle`
  // colore d'emblée toutes les parcelles ET révèle le code au zoom/clic.
  layers: { zonage: false, zonage_parcelle: false, parcelles: true, ppr: false, parc: false, znieff: false, limites: true, anru: false, equipements: false, equipements_bpe: false, communes: true, cinquante_pas: false, alea_inondation: false, alea_mvt: false, transport: false, lignes_ht: false, axes: false, renouv: false, couleurs_verdict: false, qpv: false, tva_primo: false, zfang: false, frr: false },
  // M55-B point 6 : la couche « Zonage par parcelle » COLORE la couche Parcelles (elle repeint
  // parcels-fill). L'activer seule ne montrait RIEN si « Parcelles » était décochée. On active
  // donc automatiquement sa dépendance (parcelles) au clic — dépendance technique, dite dans le « i ».
  toggleLayer: (k) => set((s) => {
    const next = { ...s.layers, [k]: !s.layers[k] }
    if (k === 'zonage_parcelle' && next.zonage_parcelle) next.parcelles = true
    return { layers: next }
  }),
  panelOpen: true,
  togglePanel: () => set((s) => ({ panelOpen: !s.panelOpen })),
  query: '',
  setQuery: (query) => set({ query }),
  filters: EMPTY_FILTERS,
  setFilter: (k, v) => set((s) => ({ filters: { ...s.filters, [k]: v } })),
  setFilters: (filters) => set({ filters }),
  resetFilters: () => set({ filters: EMPTY_FILTERS, zone: null }),
  modeB: MODE_B_DEFAUT,
  setModeB: (p) => set((s) => ({ modeB: { ...s.modeB, ...p } })),
  sourcesFocus: null,
  // B2 : ouvrir Sources est un changement de vue principale → même nettoyage exclusif
  openSources: (focus = null) => set({ view: 'sources', sourcesFocus: focus, outilsOpen: false,
    selectedIdu: null, module: null, contexteCommune: null, sourceLine: null, iaRestitution: null,
    parcours: null, openProjet: null }),
  // M104 — Surveillance : une entrée, trois volets (parcelles / secteurs / critères).
  surveillanceOpen: false,
  surveillanceVolet: 'parcelles',
  openSurveillance: (volet) => set((s) => ({ surveillanceOpen: true, view: 'cartes',
    surveillanceVolet: volet ?? s.surveillanceVolet })),
  setSurveillanceOpen: (v) => set({ surveillanceOpen: v }),
  toggleSurveillance: () => set((s) => ({ surveillanceOpen: !s.surveillanceOpen, view: 'cartes' })),
  // anciennes entrées : elles REDIRIGENT vers la section unifiée, volet correspondant.
  toggleVeilles: () => set({ surveillanceOpen: true, surveillanceVolet: 'secteurs', view: 'cartes' }),
  toggleSuivis: () => set({ surveillanceOpen: true, surveillanceVolet: 'parcelles', view: 'cartes' }),
  compareIdus: [],
  compareOpen: false,
  addToCompare: (idu) => set((s) => ({
    compareIdus: s.compareIdus.includes(idu) ? s.compareIdus : [...s.compareIdus, idu].slice(0, 3),
    compareOpen: true, view: 'cartes' })),
  removeFromCompare: (idu) => set((s) => { const r = s.compareIdus.filter((x) => x !== idu); return { compareIdus: r, compareOpen: r.length > 0 && s.compareOpen } }),
  clearCompare: () => set({ compareIdus: [], compareOpen: false, comparePicking: false }),
  setCompareOpen: (v) => set((s) => ({ compareOpen: v, comparePicking: v ? s.comparePicking : false })),
  comparePicking: false,
  setComparePicking: (comparePicking) => set({ comparePicking }),
  sourceLine: null,
  openSourceDrawer: (line) => set({ sourceLine: line }),
  closeSourceDrawer: () => set({ sourceLine: null }),
  basemap: readBasemap(),   // M65 P8 : toujours 'dark' au boot/reload (Sombre = défaut).
  setBasemap: (basemap) => set({ basemap }),   // M65 P8 : bascule de session, non persistée.
  orthoYear: 'now',
  setOrthoYear: (orthoYear) => set({ orthoYear, basemap: 'ortho' }),
  terrain3d: false,
  toggleTerrain: () => set((s) => ({ terrain3d: !s.terrain3d })),
  tool: null,
  setTool: (tool) => set({ tool }),
  zone: null,
  setZone: (zone) => set({ zone }),
  module: null,
  setModule: (module) => set({ module, view: 'cartes', outilsOpen: false, moduleMap: { idus: [], extra: null }, moduleFiche: {}, parcours: null, openProjet: null }),
  moduleMap: { idus: [], extra: null },
  setModuleMap: (moduleMap) => set({ moduleMap }),
  cmpLeft: 'bm-ortho-1950',
  cmpRight: 'bm-ortho-now',
  setCmpLeft: (cmpLeft) => set({ cmpLeft }),
  setCmpRight: (cmpRight) => set({ cmpRight }),
  moduleFiche: {},
  setModuleFiche: (moduleFiche) => set({ moduleFiche }),
  flyTo: null,
  setFlyTo: (flyTo) => set({ flyTo }),
  msel: [],
  setMsel: (msel) => set({ msel }),
  m22Prefill: null,
  setM22Prefill: (m22Prefill) => set({ m22Prefill }),
  m02Prefill: null,
  setM02Prefill: (m02Prefill) => set({ m02Prefill }),
  pluPrefill: null,
  setPluPrefill: (pluPrefill) => set({ pluPrefill }),
  pluVue: null,
  setPluVue: (pluVue) => set({ pluVue }),
  calcPrefill: null,
  setCalcPrefill: (calcPrefill) => set({ calcPrefill }),
  parcelPrefill: null,
  setParcelPrefill: (parcelPrefill) => set({ parcelPrefill }),
  calculette: null,
  setCalculette: (calculette) => set({ calculette }),
}))
