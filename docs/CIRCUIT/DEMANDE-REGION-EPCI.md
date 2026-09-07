# DEMANDES DE DONNÉES — Région, EPCI, Département, AGORAH, DEAL, communes

*Préparé par SOURCES-1 lot 7 (07/09/2026), prêt à envoyer. Chaque section = un destinataire :
ce qui est demandé, pourquoi (l'usage concret dans LABUSE), sous quel format souhaité.
Les constats de disponibilité cités ont tous été vérifiés par des appels réels (compte-rendu
SOURCES-1, lots 1 à 6).*

Format souhaité par défaut : **SIG vecteur** (GeoPackage ou shapefile, EPSG:2975 ou 4326,
avec date de validité et acte de référence) ; à défaut CSV avec identifiants (INSEE, IDU,
IRIS). Un simple lien de téléchargement ou un dépôt ponctuel conviennent — LABUSE ne demande
aucun accès à des systèmes.

---

## Région Réunion

1. **La couche SIG officielle du SAR en vigueur** (zonages : espaces naturels remarquables du
   littoral, coupures d'urbanisation, continuités écologiques, zones préférentielles
   d'urbanisation, espaces agricoles) **et le calendrier de la révision SAR 2050**.
   *Pourquoi : nous n'avons trouvé AUCUN vecteur SAR diffusé (vérifié le 07/09/2026 sur
   Carmen/DEAL, Lizmap DEAL, Sextant — image seule — et data.regionreunion.com) ; le SAR
   encadre les PLU et nos analyses de constructibilité l'affichent aujourd'hui par un proxy
   de vocations, avec la mention « indication non opposable ».*
2. **Les SIG communaux rassemblés sur PEIGEO** : emplacements réservés, EBC, DPU, zonages
   d'assainissement, périmètres de ZAC, OPAH — pour les communes absentes du Géoportail de
   l'urbanisme. *Pourquoi : le GPU ne porte le DPU que pour 4 communes sur 24 et
   l'assainissement SIG pour 4 sur 24 (mesuré) ; le reste n'existe qu'en PDF ou pas du tout.*
3. **Le cadastre solaire régional** (la-reunion.cadastre-solaire.fr) en données brutes.
   *Pourquoi : notre module Solaire calcule le productible par toiture (LiDAR + PVGIS) ; la
   comparaison avec le cadastre régional serait un contrôle qualité mutuel.*
4. **Les données TCSP de PEIGEO / AGORAH** (tracés en projet, Réunion Express).
   *Pourquoi : la proximité d'un TCSP change la constructibilité (stationnement allégé
   L151-36) et la valeur — nous ne servons aujourd'hui que l'existant OSM/GTFS et les
   hypothèses du débat public.*
5. **Le LiDAR régional** s'il diffère de celui de l'IGN. *Pourquoi : hauteurs de bâti et
   pentes plus fraîches = meilleures capacités constructibles.*
6. **DVF Région** : le jeu `demande-de-valeurs-foncierespublic` est figé à mi-2021 (vérifié) —
   une republication à jour nous servirait d'échantillon de contrôle producteur permanent.

## CINOR · TCO · CIVIS · CASUD · CIREST (chaque EPCI)

1. **Zonage d'assainissement** (collectif / non collectif) en SIG, avec la délibération.
   *Pourquoi : hors zone collective, l'ANC impose une surface minimale et un sol filtrant —
   c'est un critère de constructibilité que nous ne pouvons servir que pour 4 communes
   aujourd'hui (annexes GPU).*
2. **Inventaire des zones d'activité économique** (L.318-8-2 du code de l'urbanisme) : état
   parcellaire, occupants, vacance. *Pourquoi : le foncier économique est aveugle dans nos
   analyses ; l'inventaire est une obligation légale déjà réalisée.*
3. **Périmètres des ZAC** en vigueur (création/réalisation). *Pourquoi : concurrence, lots à
   bâtir à venir et prix de sortie autour d'un terrain analysé.*
4. **Périmètres exacts des OPAH / PIG actifs** (annexes des conventions Anah).
   *Pourquoi : les aides Anah changent l'équation d'une rénovation — nous ne savons dire
   aujourd'hui que « la commune est couverte », jamais si l'adresse l'est.*
5. **Périmètres infra-communaux des conventions ORT** (annexes cartographiques).
   *Pourquoi : l'éligibilité Denormandie se joue au périmètre, pas à la commune — nous
   servons l'éligibilité communale (liste DGALN) et devons dire « périmètre non publié ».*
6. **Pour les communes membres : les périmètres de DPU** (délibérations + SIG) des 20
   communes absentes du GPU (liste au dos — mesurée le 06/09/2026). *Pourquoi : la
   préemption pèse sur toute transaction ; nous l'affichons « non déterminée — non publié
   par la commune » partout ailleurs.*

## Conseil départemental de La Réunion

1. **Les périmètres des espaces naturels sensibles (ENS)** et les **zones de préemption ENS**.
   *Pourquoi : l'INPN ne les porte pas (vérifié) ; le GPU n'en montre que des traces éparses.
   Un terrain en zone de préemption ENS ne s'analyse pas comme un autre.*

## AGORAH (et ADIL pour l'OLL)

1. **Accès aux données brutes des observatoires** (foncier, habitat, ZAE) — pas aux PDF.
2. **Micro-données de l'observatoire local des loyers** (convention réseau OLL).
   *Pourquoi : nous servons déjà les agrégats par zone 2024 (loyer médian canonique) ; les
   micro-données affineraient les 8 communes multi-zones restées au repli DHUP.*

## DEAL Réunion

1. **La couche du domaine privé de l'État sur les ravines (DPE, ~1 700 km)**. *Pourquoi : le
   DPF (1 800 km) est servi depuis le WFS Carmen (arrêté 06-3077) ; le DPE n'est pas diffusé
   — sans lui, la moitié des reculs de ravines reste invisible.*
2. **Le classement sonore en SIG consolidé** si une version plus fine que le flux Cerema
   existe, et **la couche ZPPA du 974** dès que l'Atlas des patrimoines répond (injoignable
   à nos tests depuis le 06/09/2026 — avec la DAC).

## Communes (via EPCI ou en direct) — DPU non publié au GPU

Bras-Panon, Cilaos, Entre-Deux, L'Étang-Salé, La Plaine-des-Palmistes, La Possession,
Le Port, Les Avirons, Les Trois-Bassins, Petite-Île, Saint-André, Saint-Benoît,
Saint-Joseph, Saint-Leu, Saint-Louis, Saint-Philippe, Saint-Pierre, Sainte-Rose,
Sainte-Suzanne, Salazie. *(Le Tampon, Saint-Denis, Saint-Paul et Sainte-Marie publient
déjà — mesuré en base le 07/09/2026 ; merci à elles.)*

---

*Contact retour : un lien de téléchargement suffit. LABUSE cite systématiquement le
producteur et le millésime de chaque donnée servie.*
