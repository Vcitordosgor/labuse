# AUDIT M86 — Le centre de notifications (véracité)

> **Restitution.** 5 types au registre (M85-B). **OK : 3** (veille_zone, systeme_pilote, annonce_produit)
> · **À CORRIGER : 1** (parcelle_suivie — texte d'en-tête obsolète) · **MORTE : 0** (aucun type sans
> producteur). Événements RÉELS en base (hors démo) : `veille` 15 (dont 13 Copilote), `systeme` 1 (DPE
> en retard) ; **tous les autres types = producteur prêt mais 0 événement réel** (les crons d'ingestion
> et le cron `notifications` ne sont pas déployés sur le VPS → aucun producteur ne tourne en automatique).
> **Corrections factuelles faites : 0** dans ce fichier (la reformulation de l'en-tête cloche relève de
> M87 Phase 5 « reformuler avec Vic » — signalée ici, non écrite). Mesuré le 2026-08-14.

---

## Tableau par type (registre M85-B)

| type | producteur (job · table · cron) | événement RÉEL produit ? | texte affiché = ce qui est détecté ? | promesse tenue ? | verdict |
|---|---|---|---|---|---|
| **parcelle_suivie** | `events.evaluer_suivis` (CLI `evaluer-suivis`) + `detect_events` (bascule de tier) · `event_log` · cron `notifications` **non déployé** | **NON** — 0 ligne `parcelle_suivie` (producteur prêt ; nécessite des suivis + données récentes + cron) | **NON** — l'en-tête cloche dit « permis neuf **à proximité** » : FAUX depuis M85-B (maille = SUR la parcelle, la proximité ≤300 m a été retirée → BACKLOG). Le texte OMET aussi la **mutation** (vente, l'événement majeur) et le **zonage**, tous deux détectés. | **NON** | **À CORRIGER** (en-tête cloche à reformuler — M87/Vic) |
| **veille_zone** | `veilles.evaluer_toutes` (Copilote) + `events._veilles_match` (saved_searches) · `event_log` kind=`veille` | **OUI** — 15 réels (13 « Copilote · veille », 1 Test, 1 migré) | OK — « nouveau permis à \<commune\> » correspond au producteur (permis à la commune veillée) | OUI | **OK** |
| **annonce_produit** | CLI `labuse annonce` (manuel, mandant) · `event_log` + trace `annonces` | **NON** — 0 annonce envoyée (jamais utilisée ; normal, à la demande) | n/a (le pilote saisit le texte ; aperçu obligatoire) | n/a | **OK** (producteur manuel, 0 usage = normal) |
| **maintenance** | CLI `labuse annonce --type maintenance` (manuel) · gabarit distinct | **NON** — 0 | n/a | n/a | **OK** (manuel, non désactivable, gabarit dédié) |
| **systeme_pilote** | `events.notifier_fraicheur` + `trace_ingestion` (échec) · `event_log` kind=`systeme` · cron `notifications` non déployé | **OUI** — 1 réel (« Source en retard : DPE ») | OK — « Source en retard … » correspond à `check_fraicheur` | OUI (pilote/admin seulement, cloche seule) | **OK** |

## Kinds historiques (mappés au registre, produits par `detect_events` sur diff de run)
- `bascule` / `bodacc` / `match` (marché partagé) : **0 événement réel** — `detect_events` exige un DIFF de
  deux runs servis (rare, grande passe). Non émis entre deux passes. Restent des kinds valides (cloche
  informatif), hors des 3 chaînes de mail (M85-B).
- `permis` (ancien « ≤300 m ») : **RETIRÉ** en M85-B (remplacé par parcelle_suivie SUR la parcelle).

## Détail de la faute `parcelle_suivie` (en-tête de la cloche)
`frontend/src/components/header/Header.tsx` (l. 322-325) affiche :
> « les changements sur les parcelles que vous suivez — **bascule de statut, procédure BODACC, permis
> neuf à proximité** — et les alertes de vos veilles. On ne vous prévient que sur ce qu'on sait
> réellement détecter. »

Ce que `evaluer_suivis` détecte RÉELLEMENT (M85-B) sur une parcelle suivie : **mutation (vente)** ·
**permis SUR la parcelle** · **BODACC (propriétaire)** · **zonage** · **bascule de tier** (notre verdict).
→ Écarts : « à proximité » n'est plus vrai ; « mutation » et « zonage » manquent ; « bascule de statut »
est OK. **La promesse n'est donc PAS tenue au mot près.** Reformulation = M87 Phase 5 (avec Vic), pas M86.

## Producteurs : existence vérifiée (code présent)
Tous les producteurs EXISTENT en code (M85/M85-B) : `evaluer_suivis`, `evaluer_toutes`/`_veilles_match`,
`notifier_fraicheur`/`trace_ingestion`, CLI `annonce`. **Aucun type MORT (sans producteur).** Le seul
vrai frein au contenu réel = **les crons ne sont pas déployés sur le VPS** (dépendance M84/M85) : sans
eux, `evaluer-suivis`/`evaluer-veilles`/`notifier-fraicheur` ne tournent pas en automatique, d'où le
faible volume d'événements réels mesuré. Ce n'est pas un défaut de producteur, c'est un défaut de
déploiement — à dire, pas à confondre.
