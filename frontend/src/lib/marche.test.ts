// OUTIL-COMMUNES-FIX-11 LOT 0/1 — filet : l'en-tête Marché tire prix + type + effectif + périmètre
// d'UNE SEULE série. ROUGE avant le fix (fonction absente / ancien mélange bâti-prix × terrain-effectif).
import { describe, expect, it } from 'vitest'
import { enteteMarche } from './marche'

describe('enteteMarche — les 4 éléments d\'une seule série', () => {
  it('terrain sous le seuil → repli ANCIEN (bâti) avec SON effectif/rayon/type, terrain dit à part', () => {
    // cas Saint-Joseph AY0082 : terrain 1 vente masqué, maisons 2947 €/m² sur 10 ventes à 500 m
    const e = enteteMarche(
      { mediane_prix_m2: null, n_ventes: 1, perimetre: 'section cadastrale' },
      { median: 2947, n: 10, radius_m: 500, commune_fallback: false, type_prix: 'maison' },
    )
    expect(e.serie).toBe('ancien')
    expect(e.valeur).toBe('2 947 €/m²')             // fr-FR : espace fine insécable des milliers
    expect(e.contexte).toContain('maison')
    expect(e.contexte).toContain('10 ventes')
    expect(e.contexte).toContain('rayon 500 m')
    expect(e.contexte).not.toContain('section cadastrale')  // JAMAIS le périmètre du terrain avec le prix bâti
    expect(e.terrainInsuffisant).toBe('terrain : échantillon insuffisant, 1 vente (section cadastrale)')
  })

  it('terrain diffusable → série TERRAIN cohérente (prix + n + section), rien à part', () => {
    const e = enteteMarche(
      { mediane_prix_m2: 418, n_ventes: 69, perimetre: 'section cadastrale' },
      { median: 3000, n: 20, radius_m: 1500, type_prix: 'mixte (appart+maison)' },
    )
    expect(e.serie).toBe('terrain')
    expect(e.valeur).toBe('418 €/m²')
    expect(e.contexte).toBe('terrain nu · 69 ventes · section cadastrale · DVF')
    expect(e.terrainInsuffisant).toBeNull()
  })

  it('mixte appart+maison au rayon 1500 m (cas Saint-Paul CD) : type + rayon de la MÊME série', () => {
    const e = enteteMarche(
      { mediane_prix_m2: null, n_ventes: 1, perimetre: 'section cadastrale' },
      { median: 3188, n: 12, radius_m: 1500, type_prix: 'mixte (appart+maison)' },
    )
    expect(e.serie).toBe('ancien')
    expect(e.contexte).toContain('mixte (appart+maison)')
    expect(e.contexte).toContain('12 ventes')
    expect(e.contexte).toContain('rayon 1 500 m')   // fmtInt : séparateur de milliers fr-FR
  })

  it('élargissement commune (cas Cilaos AC0139) : commune_fallback → « commune entière », JAMAIS le rayon', () => {
    // FIX-12 LOT 1 — l'en-tête est PRÊT à afficher le périmètre réel ; le défaut ASTRA-9 §1 était que la
    // ROUTE (modules.py:1981) omettait commune_fallback → mb.commune_fallback undefined → rayon affiché.
    // 82 ventes de maison à 1 300 €/m² agrégées sur la COMMUNE (pas dans les 1 500 m).
    const e = enteteMarche(
      { mediane_prix_m2: null, n_ventes: 2, perimetre: 'section cadastrale' },
      { median: 1300, n: 82, radius_m: 1500, commune_fallback: true, type_prix: 'maison' },
    )
    expect(e.serie).toBe('ancien')
    expect(e.contexte).toContain('maison')
    expect(e.contexte).toContain('82 ventes')
    expect(e.contexte).toContain('commune entière')
    expect(e.contexte).not.toContain('1 500')       // jamais le rayon quand l'effectif vient de la commune
    expect(e.contexte).not.toContain('rayon')
  })

  it('aucune donnée → tiret, pas d\'invention', () => {
    const e = enteteMarche(null, null)
    expect(e.serie).toBe('aucune')
    expect(e.valeur).toBe('—')
  })

  // fmtInt (fr-FR) sépare les milliers par une ESPACE FINE INSÉCABLE (U+202F) : on normalise pour comparer.
  const norm = (s: string) => s.replace(/[\u202f\u00a0]/g, ' ')

  // OUTIL-COMMUNES-FIX-13 LOT 5 — « maisons (recherche mixte) » : l'en-tête RACCOURCIT en « 10 maisons »
  // (ce qui est retenu) ; la MÉTHODE « recherche mixte » descend au DÉTAIL. Cas Saint-Louis CT0691.
  it('recherche mixte homogène (Saint-Louis CT0691) : en-tête « 10 maisons », méthode au détail', () => {
    const e = enteteMarche(
      { mediane_prix_m2: null, n_ventes: 0, perimetre: 'section cadastrale' },
      { median: 2604, n: 10, radius_m: 500, commune_fallback: false, type_prix: 'maisons (recherche mixte)' },
    )
    expect(e.serie).toBe('ancien')
    expect(norm(e.valeur)).toBe('2 604 €/m²')
    expect(norm(e.contexte)).toBe('10 maisons · rayon 500 m · DVF')   // court : compte + type, SANS « (recherche mixte) »
    expect(e.contexte).not.toContain('recherche mixte')               // la méthode n'est plus dans l'en-tête
    expect(e.methode).toBe('recherche mixte')                         // … elle part au détail
  })

  it('appartements (recherche mixte) : même raccourci « N appartements »', () => {
    const e = enteteMarche(null,
      { median: 2200, n: 7, radius_m: 1000, type_prix: 'appartements (recherche mixte)' })
    expect(norm(e.contexte)).toBe('7 appartements · rayon 1 000 m · DVF')
    expect(e.methode).toBe('recherche mixte')
  })

  it('vraiment mixte (Saint-Paul CD) : PAS de raccourci, pas de méthode au détail', () => {
    const e = enteteMarche(null,
      { median: 3757, n: 12, radius_m: 1500, type_prix: 'mixte (appart+maison)' })
    expect(e.contexte).toContain('mixte (appart+maison)')
    expect(e.methode).toBeNull()
  })
})
