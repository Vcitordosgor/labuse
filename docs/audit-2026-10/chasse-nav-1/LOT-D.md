# LOT D — boutons morts, doublons, impasses

## Liens vers fonctions retirées (Street View, pages supprimées)
- Recherche `street view / mapillary / pegman / cyclomedia` dans le front : **AUCUNE occurrence**. Pas de lien mort vers une fonction retirée.
- `/map/layers.geojson` : client `getMapLayer` **RETIRÉ** (api.ts:816, COUCHES-RETRAIT-1) — ne restent que des commentaires, aucun bouton ne l'appelle. ✓

## Boutons → endpoint absent (croisement front api.ts ↔ 413 routes back + curl)
- 290 chemins front extraits ; après normalisation, tous les endpoints **réellement appelés** répondent **200** : vérifiés en live `/admin/programmes` 200, `/radar/marche-tableau` 200, `/modules/bailleur` 200, `/modules/velocite` 200, `/parcels/{idu}/mode-b` 200, `/parcels/{pid}/export.csv`, `/map/tiles/{kind}/…`, `/moi*` (hors-schéma, 200). Aucun bouton vivant ne vise un endpoint absent.
- **SEULE anomalie → ÉCART N-5 ⚪** : constante `etudeZonePdfUrl = '/outils/etude-zone/export.pdf'` (api.ts:483) pointe une route **404** (la vraie est `/etude-zone.pdf`, 200). Mais la constante n'est **référencée par AUCUN bouton** (grep hors api.ts = vide) → code mort. Inoffensif aujourd'hui, casserait un PDF si un jour on la câblait.

## Endpoints orphelins (appelés par aucun bouton)
- Le back expose 413 routes ; beaucoup ne sont PAS liées à un bouton **par conception** : CLI/ingestion, webhooks Stripe, `/admin/circuit/*` (tour de contrôle), `/admin/cron/*`, `/readyz`, `/healthz`, sondes. Ce n'est pas un écart (surface API > surface boutons = normal).

## Doublons au même endroit
- Suspicion « Densifier l'existant » présent 2× dans la fiche : **NON confirmée**. Le libellé-bouton n'apparaît qu'UNE fois (`Fiche.tsx:1954`) ; l'autre occurrence (`:1169`) est un COMMENTAIRE sur un badge « Densifier l'existant — rang N/M » (autre composant). Pas de doublon.

## Écrans sans sortie (impasses)
- Vue Admin (plein écran, rail client masqué) : sortie par « Ouvrir l'app cliente → » (AdminView.tsx:493) — **testé OK** (retour à l'app, `#admin=1` effacé).
- Radar / Veille : boutons « Retour Radar » / « Retour Veille » présents (VeilleEcrans/RadarEcran). Fiches : « ✕ » / « Fermer ». Outils : « ← Outils » / « ✕ ». Aucune impasse constatée.

## Boutons grisés sans raison
- Tuiles d'export grisées (Dossier/Pré-dossier PC) : **affichent la raison** en infobulle `title` (`Fiche.tsx` DossierTile: `title={d.raison ?? 'Générateur de dossier indisponible'}`). ✓
- Autres `disabled` : transitoires (chargement `busy`/`envoi`) ou conditionnés à une saisie (`msel.length < 2` pour Assemblage, `!reponse.trim()` Copilote) — état attendu, non trompeur.

## Verdict Lot D
Chasse quasi vide : **1 écart ⚪** (constante morte N-5, sans bouton). Pas de lien retiré, pas de bouton vivant vers endpoint absent, pas de doublon confirmé, pas d'impasse, grisés justifiés.
