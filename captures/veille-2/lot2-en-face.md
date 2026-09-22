# VEILLE-2 · Lot 2 — « La page en face » : le __NEXT_DATA__ réel de chaque dépôt

Les pages leboncoin sauvegardées sont des SPA : hors ligne, le DOM ne s'hydrate pas (capture visuelle = logo seul). La VÉRITÉ de la page est son bloc `__NEXT_DATA__` (données serveur embarquées) + son `<title>` rendu serveur. Voici, pour chaque annonce d'ancrage, les champs BRUTS de la page en regard de ce que l'extracteur en tire — ils coïncident, aucun fait inventé.

## ECH-1.html (résultats · 35 annonces)
- `<title>` (rendu serveur) : **Baisse de prix**

**Annonce 3143092379** — brut de la page :

```json
{
  "list_id": 3143092379,
  "subject": "Maison Villa 7 pièces 202 m² à Saint-Denis",
  "price": [
    655000
  ],
  "location.city": "Saint-Denis",
  "attributes.real_estate_type": "1",
  "attributes.square": "202",
  "attributes.land_plot_surface": "265",
  "first_publication_date": "2026-08-17 19:58:29",
  "url": "https://www.leboncoin.fr/ad/ventes_immobilieres/3143092379"
}
```
extrait par LABUSE :

```json
{
  "commune": "Saint-Denis",
  "type": "maison",
  "prix": 655000,
  "surface_hab": 202,
  "surface_terrain": 265,
  "date_pub": "2026-08-17 19:58:29",
  "lien": "https://www.leboncoin.fr/ad/ventes_immobilieres/3143092379"
}
```

**Annonce 3253364472** — brut de la page :

```json
{
  "list_id": 3253364472,
  "subject": "Charmante VILLA Bourbon bois 350000, refaite astucieuse T 4/5",
  "price": [
    350000
  ],
  "location.city": "Saint-Denis",
  "attributes.real_estate_type": "1",
  "attributes.square": "170",
  "attributes.land_plot_surface": "1494",
  "first_publication_date": "2026-08-20 12:45:44",
  "url": "https://www.leboncoin.fr/ad/ventes_immobilieres/3253364472"
}
```
extrait par LABUSE :

```json
{
  "commune": "Saint-Denis",
  "type": "maison",
  "prix": 350000,
  "surface_hab": 170,
  "surface_terrain": 1494,
  "date_pub": "2026-08-20 12:45:44",
  "lien": "https://www.leboncoin.fr/ad/ventes_immobilieres/3253364472"
}
```

**Annonce 3184708502** — brut de la page :

```json
{
  "list_id": 3184708502,
  "subject": "Villa 4 pièces 102 m²",
  "price": [
    384000
  ],
  "location.city": "La Possession",
  "attributes.real_estate_type": "1",
  "attributes.square": "102",
  "attributes.land_plot_surface": "232",
  "first_publication_date": "2026-08-12 18:15:35",
  "url": "https://www.leboncoin.fr/ad/ventes_immobilieres/3184708502"
}
```
extrait par LABUSE :

```json
{
  "commune": "La Possession",
  "type": "maison",
  "prix": 384000,
  "surface_hab": 102,
  "surface_terrain": 232,
  "date_pub": "2026-08-12 18:15:35",
  "lien": "https://www.leboncoin.fr/ad/ventes_immobilieres/3184708502"
}
```

## T-camelias.html (page d'annonce)
- `<title>` (rendu serveur) : **Lien vers le calculateur**

**Annonce 3055991753** — brut de la page :

```json
{
  "list_id": 3055991753,
  "subject": "Terrain 1 108 m² Saint Denis Camelias",
  "price": [
    367500
  ],
  "location.city": "Saint-Denis",
  "attributes.real_estate_type": "3",
  "attributes.square": null,
  "attributes.land_plot_surface": "1108",
  "first_publication_date": "2025-09-11 12:49:00",
  "url": "https://www.leboncoin.fr/ad/ventes_immobilieres/3055991753"
}
```
extrait par LABUSE :

```json
{
  "commune": "Saint-Denis",
  "type": "terrain",
  "prix": 367500,
  "surface_hab": null,
  "surface_terrain": 1108,
  "date_pub": "2025-09-11 12:49:00",
  "lien": "https://www.leboncoin.fr/ad/ventes_immobilieres/3055991753"
}
```

## T-possession.html (page d'annonce)
- `<title>` (rendu serveur) : **Lien vers le calculateur**

**Annonce 3241879744** — brut de la page :

```json
{
  "list_id": 3241879744,
  "subject": "Terrain 419 m² La Possession",
  "price": [
    195000
  ],
  "location.city": "La Possession",
  "attributes.real_estate_type": "3",
  "attributes.square": null,
  "attributes.land_plot_surface": "419",
  "first_publication_date": "2026-07-30 13:02:41",
  "url": "https://www.leboncoin.fr/ad/ventes_immobilieres/3241879744"
}
```
extrait par LABUSE :

```json
{
  "commune": "La Possession",
  "type": "terrain",
  "prix": 195000,
  "surface_hab": null,
  "surface_terrain": 419,
  "date_pub": "2026-07-30 13:02:41",
  "lien": "https://www.leboncoin.fr/ad/ventes_immobilieres/3241879744"
}
```

## T-saintemarie.html (page d'annonce)
- `<title>` (rendu serveur) : **Lien vers le calculateur**

**Annonce 3200222934** — brut de la page :

```json
{
  "list_id": 3200222934,
  "subject": "Terrain 1 600 m² Sainte Marie",
  "price": [
    825000
  ],
  "location.city": "Sainte-Marie",
  "attributes.real_estate_type": "3",
  "attributes.square": null,
  "attributes.land_plot_surface": "1600",
  "first_publication_date": "2026-07-13 01:37:01",
  "url": "https://www.leboncoin.fr/ad/ventes_immobilieres/3200222934"
}
```
extrait par LABUSE :

```json
{
  "commune": "Sainte-Marie",
  "type": "terrain",
  "prix": 825000,
  "surface_hab": null,
  "surface_terrain": 1600,
  "date_pub": "2026-07-13 01:37:01",
  "lien": "https://www.leboncoin.fr/ad/ventes_immobilieres/3200222934"
}
```

## ECH-2-varianteB.html (variante B DOM)
- `<title>` (rendu serveur) : **Baisse de prix**

