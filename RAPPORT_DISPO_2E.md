# RAPPORT DE DISPONIBILITÉ — 2.E Assainissement (collectif vs autonome)

> §7 / brief 2.E. Sonde multi-sources le 2026-06-14 (data.gouv joignable). Le brief anticipait :
> « TCO via PEIGEO probablement → dépend du whitelist ». Vérification avant tout loader.

## La donnée recherchée
**Zonage d'assainissement** : découpage réglementaire qui distingue, parcelle par parcelle, les
secteurs en **assainissement collectif** (raccordement au réseau public d'eaux usées) des secteurs
en **assainissement non collectif** (ANC — fosse/filière autonome, contrôle SPANC). C'est une
**compétence locale** : à Saint-Paul elle relève du **TCO** (Territoire de la Côte Ouest). C'est
une **délimitation administrative discrète** (un plan de zonage voté), **PAS** un proxy dérivable
de la distance à un réseau ni d'un quelconque calcul géométrique.

Usage LA BUSE visé : driver de coût / faisabilité (collectif = raccordable ; autonome = surface de
dispersion à réserver + perméabilité + majoration VRD), affiché en clair sur la fiche.

## Sondage multi-sources (Réunion / INSEE 97415)
| Source | État (2026-06-14) | Zonage assainissement Réunion ? |
|---|---|---|
| **PEIGEO** (`peigeo.re/geoserver`) — source autoritaire TCO/DEAL/AGORAH | ❌ timeout (HTTP 000) | — (bloqué) |
| **data.gouv.fr** (joignable) | ✅ / ⚠️ | ❌ « zonage assainissement » → **9 jeux, tous métropole** (GrandSoissons, Somme, Puy-de-Dôme, Rennes Métropole) ; « assainissement 974 » → **0** ; « …réunion » / « …TCO » → HTTP 503 (serveur, non énumérable) |
| **Région ODS** (`data.regionreunion.com`) | ✅ joignable | ❌ aucun jeu pertinent (résultats : lignes haute tension, budget, PNRun…) |
| **Géoplateforme WFS** (`data.geopf.fr`, capabilities 5,1 Mo, national) | ✅ HTTP 200 | ❌ **0 couche** « assainissement » (compétence locale, non agrégée au niveau national) |

## Conclusion : ⛔ STOP sur l'item
Le zonage d'assainissement de **Saint-Paul / La Réunion** n'est disponible en SIG sur **aucune
source joignable** ; la source autoritaire (PEIGEO, qui porte les couches TCO) reste **bloquée** —
exactement le risque anticipé par le brief 2.E.

Conformément au brief : **introuvable partout → rapport + STOP, sans bricoler**. Je n'approxime
**PAS** le zonage par un buffer autour du réseau d'eaux usées ni par une heuristique de densité :
le découpage collectif/autonome est un acte réglementaire voté, pas une grandeur calculable — une
approximation serait une donnée fabriquée, interdite (§0.4).

**Reprise dès que le whitelisting PEIGEO (action Vic, en cours) est effectif** — le même
déblocage lève 2.D et 2.E. Le loader sera direct : couche surfacique TCO → attribut
`assainissement = collectif | non_collectif` sur la fiche + majoration VRD côté bilan pour l'ANC
(paramètre déjà prévu : `majoration_vrd_assainissement_pct`, placeholder non calibré).

**Recette prévue (à exécuter au déblocage)** : 1 parcelle en collectif + 1 parcelle en autonome,
verdict lisible des deux côtés.
