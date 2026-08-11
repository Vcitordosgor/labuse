import { create } from 'zustand'
import type { FicheLine } from '../lib/types'
import type { FilterTier } from '../lib/status'

// M26-B : 'copilote' = l'écran Copilote (instruction de dossier, event log SSE) — vue de
// premier niveau, la maquette B4 est pleine largeur (pas un module du panneau 320 px).
export type View = 'ia' | 'cartes' | 'crm' | 'sources' | 'projets' | 'copilote'

export interface LayerToggles {
  zonage: boolean
  zonage_parcelle: boolean // M6.1 / M55-A : couche parcellaire UNIQUE — colore toutes les parcelles
                           // par famille PLU (U/AU/A/N), + étiquette du code au zoom et popup au clic
                           // (l'ancienne case « colorisation » y est fusionnée, M55-A fusion A)
  parcelles: boolean
  ppr: boolean
  parc: boolean
  limites: boolean
  anru: boolean
  equipements: boolean
  communes: boolean   // P11 : limites communales (ligne verte, contours officiels)
  cinquante_pas: boolean // M6.1 : réserve des 50 pas géométriques (bande littorale outre-mer)
  renouv: boolean     // M-RENOUV : segment Renouvellement (occupées, potentiel) — OFF par défaut
  couleurs_verdict: boolean // M55-G point 8 : palette des tiers en COUCHE activable — imposée
                            // seulement en mode analyse ; en tri factuel rien n'est imposé
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
  divisionOr: boolean
  proprietaireType: string[]         // pm / bailleur / pp
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
  sousDensite: false, multMin: null, rangMax: null, renouvellement: false, divisionOr: false,
  proprietaireType: [], etatSociete: [], copro: [], npnru: false, adresseAbsente: false,
  budgetMax: null, chargeMin: null, chargeMax: null, prixMarcheMin: null, prixMarcheMax: null,
  marcheFiable: false, caMin: null, modeBRentable: false,
  signaux: [],
}

// M45-B (Lot 2) — curseur mode B PARTAGÉ (session unique, rien persisté) : travaux + loyer +
// rendement, lus par la fiche ET le filtre (mode_b_rentable). Défauts = plafond BOFiP base + repères.
export interface ModeBParams { travauxM2: number; loyerM2: number; rendementPct: number }
export const MODE_B_DEFAUT: ModeBParams = { travauxM2: 1200, loyerM2: 12.21, rendementPct: 6 }

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

export type Basemap = 'dark' | 'plan' | 'ortho'
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
  // programmatique). M55-H point 8 (décision Vic) : TOUJOURS une section ouverte — l'état
  // « aucune » n'existe plus (plus jamais le panneau vide) ; fermer la section ouverte est
  // impossible, ouvrir l'autre la remplace.
  panneauSection: 'couches' | 'filtres'
  setPanneauSection: (s: 'couches' | 'filtres') => void
  // M55-D stage 8 : l'écran d'accueil (présentation) disparaît après le PREMIER geste de la
  // session (Commencer, ouverture d'une section, analyse) — état de session, jamais persisté.
  accueilVu: boolean
  setAccueilVu: () => void
  mobilePanelOpen: boolean
  setMobilePanelOpen: (v: boolean) => void
  openFiltres: () => void
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
  // M54-EXPO-3 — panneau « Mes veilles » en surimpression de la carte (vue cartes conservée pour
  // dessiner). Pas une View exclusive : la carte + l'outil zone restent dispo.
  veillesOpen: boolean
  toggleVeilles: () => void
  setVeillesOpen: (v: boolean) => void
  // M54-EXPO-3 A8 — comparateur : 2 à 3 parcelles côte à côte (GET /compare). Sélection cumulative
  // depuis la fiche (« Comparer ») et la shortlist ; panneau en surimpression.
  compareIdus: string[]
  compareOpen: boolean
  addToCompare: (idu: string) => void
  removeFromCompare: (idu: string) => void
  clearCompare: () => void
  setCompareOpen: (v: boolean) => void
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
  toast: null,
  setToast: (toast) => set({ toast }),
  algoModale: null,
  setAlgoModale: (algoModale) => set({ algoModale }),
  mapPeint: { parcelles: false, equipements: false, zonage: false },
  // garde d'égalité : le handler zoom de la carte appelle à chaque frame — pas de re-render inutile
  setMapPeint: (p) => set((s) =>
    s.mapPeint.parcelles === p.parcelles && s.mapPeint.equipements === p.equipements
      && s.mapPeint.zonage === p.zonage ? {} : { mapPeint: p }),
  verdict: false,
  setVerdict: (verdict) => set({ verdict }),
  retourFiltres: () => set((s) => ({
    verdict: false, panneauSection: 'filtres',
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
  setView: (view) => set({ view, outilsOpen: false, selectedIdu: null, module: null,
    contexteCommune: null, sourceLine: null, iaRestitution: null, parcours: null, openProjet: null,
    entretienDirect: null }),
  // F2 (M12) : bascule sur la vue copilote ET arme l'entretien direct (même nettoyage exclusif que setView).
  entretienDirect: null,
  ouvrirEntretien: (amorce = '') => set({ entretienDirect: amorce, view: 'ia', outilsOpen: false,
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
  toggleOutils: () => set((s) => s.outilsOpen
    ? { outilsOpen: false }
    : { outilsOpen: true, view: 'cartes', selectedIdu: null, module: null,
        contexteCommune: null, sourceLine: null, iaRestitution: null, parcours: null, openProjet: null }),
  selectedIdu: null,
  // G1 (M12) : filet de sécurité global — un idu vide ou la chaîne « undefined » (issue d'un
  // `String(undefined)` sur une feature sans propriété idu) n'ouvre JAMAIS la fiche. Elle
  // afficherait un titre « undefined » et un faux « serveur injoignable ». `null` ferme la fiche.
  select: (idu) => set({ selectedIdu: idu === '' || idu === 'undefined' ? null : idu }),
  // M55-A (fusion A) : plus de `zonage_colorise` — la couche parcellaire unique `zonage_parcelle`
  // colore d'emblée toutes les parcelles ET révèle le code au zoom/clic.
  layers: { zonage: false, zonage_parcelle: false, parcelles: true, ppr: false, parc: false, limites: true, anru: false, equipements: false, communes: true, cinquante_pas: false, renouv: false, couleurs_verdict: false },
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
  veillesOpen: false,
  setVeillesOpen: (v) => set({ veillesOpen: v }),
  toggleVeilles: () => set((s) => ({ veillesOpen: !s.veillesOpen, view: 'cartes' })),
  compareIdus: [],
  compareOpen: false,
  addToCompare: (idu) => set((s) => ({
    compareIdus: s.compareIdus.includes(idu) ? s.compareIdus : [...s.compareIdus, idu].slice(0, 3),
    compareOpen: true, view: 'cartes' })),
  removeFromCompare: (idu) => set((s) => { const r = s.compareIdus.filter((x) => x !== idu); return { compareIdus: r, compareOpen: r.length > 0 && s.compareOpen } }),
  clearCompare: () => set({ compareIdus: [], compareOpen: false }),
  setCompareOpen: (v) => set({ compareOpen: v }),
  sourceLine: null,
  openSourceDrawer: (line) => set({ sourceLine: line }),
  closeSourceDrawer: () => set({ sourceLine: null }),
  basemap: 'dark',
  setBasemap: (basemap) => set({ basemap }),
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
  calculette: null,
  setCalculette: (calculette) => set({ calculette }),
}))
