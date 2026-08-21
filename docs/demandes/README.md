# Demandes de données — index

Registre des demandes de communication / réutilisation de données publiques adressées aux
administrations, quand la donnée n'est **pas ouverte en self-service** mais existe (produite par
l'administration). Fondement commun : droit de réutilisation des informations publiques
(**CRPA, art. L. 321-1 et s.**), réutilisation par défaut sous **Licence Ouverte** (décret n° 2017-638).

Règle : tant qu'une donnée demandée n'est pas reçue, l'écran reste **honnête** (bloc « NON COUVERT »
de l'outil Risques, jamais un faux « RAS »). On n'ingère rien d'obsolète, de partiel ou de bricolé.

**Statuts** : 🟠 à envoyer · 🔵 envoyée · 🟡 relancée · 🟢 reçue · 🔴 refusée

| Demande | Destinataire (copie) | Date d'envoi | Statut | Débloque dans le produit | Fichier |
|---|---|---|---|---|---|
| PEB Roland-Garros — vecteur zones A/B/C/D (+ question Pierrefonds) | DSAC-OI (copie DEAL Réunion) | — | 🟠 à envoyer | Sort le **PEB du NON COUVERT** (outil Risques / Servitudes) : détection du **bruit aérien** sous le couloir Roland-Garros ; couche cascade candidate | [DEMANDE_PEB_DSAC-OI.md](DEMANDE_PEB_DSAC-OI.md) |
| Assainissement — zonage SIG (collectif/non collectif) + tracé réseau collectif | 5 EPCI : CINOR, TCO, CIVIS, CASUD, CIREST | — | 🟠 à envoyer | Fiabilise la couche `zonage_assainissement` (couverture partielle aujourd'hui) → **raccordable au collectif vs ANC obligatoire** = facteur de coût/faisabilité par parcelle | [DEMANDE_ASSAINISSEMENT_EPCI.md](DEMANDE_ASSAINISSEMENT_EPCI.md) |
| PLU — zonage SIG de Sainte-Marie et Sainte-Suzanne | CINOR | — | 🟠 à envoyer | Complète le **zonage PLU (GPU)** sur ces communes → scoring cascade zonage, faisabilité, simulateur PLU | [DEMANDE_PLU_CINOR_SAINTE-MARIE_SAINTE-SUZANNE.md](DEMANDE_PLU_CINOR_SAINTE-MARIE_SAINTE-SUZANNE.md) |

## Tenue du registre

- À chaque envoi : renseigner **Date d'envoi** + passer au statut 🔵, et noter la date/canal dans
  l'en-tête « Suivi » du fichier de la demande.
- Relance conseillée à **~1 mois** sans réponse (CRPA : l'administration répond à une demande de
  réutilisation ; silence > 1 mois = refus implicite ouvrant recours **CADA**).
- À réception : statut 🟢, consigner la **licence**, le **millésime** et le **format** reçus dans le
  fichier de la demande — ce sont les métadonnées à porter dans le catalogue/radar à l'ingestion.
- En cas de refus : statut 🔴, motif consigné ; option recours CADA (Commission d'accès aux
  documents administratifs) sous 2 mois.
