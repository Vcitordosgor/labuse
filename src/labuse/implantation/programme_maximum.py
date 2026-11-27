"""Composition du programme pour une recherche du plus grand nombre de logements."""
from collections import Counter
from dataclasses import dataclass


@dataclass
class ProgrammeMaximum:
    fixes: dict[str, int]
    parts: dict[str, int]

    @classmethod
    def lire(cls, programme):
        def lire_table(champ, borne):
            valeurs = programme.get(champ, {})
            if not isinstance(valeurs, dict) or any(
                t not in ("T1", "T2", "T3", "T4") or type(n) is not int or not 0 <= n <= borne
                for t, n in valeurs.items()
            ):
                raise ValueError(f"Valeurs incorrectes pour {champ}.")
            return {t: valeurs[t] for t in sorted(valeurs) if valeurs[t]}

        fixes = lire_table("fixes", 200)
        parts = lire_table("parts", 100)
        if sum(parts.values()) != 100 or fixes.keys() & parts.keys():
            raise ValueError("Répartissez 100 % du complément entre les typologies sans quantité imposée.")
        return cls(fixes, parts)

    def cible(self, total):
        reste = max(0, total - sum(self.fixes.values()))
        # Arrondi au plus fort reste sur le programme entier, même avec plusieurs bâtiments.
        quotas = {t: reste * part for t, part in self.parts.items()}
        complement = {t: q // 100 for t, q in quotas.items()}
        ordre = sorted(quotas, key=lambda t: (quotas[t] % 100, self.parts[t], t), reverse=True)
        for t in ordre[:reste - sum(complement.values())]:
            complement[t] += 1
        return {**self.fixes, **complement}

    def ajuster(self, scene):
        """Conserve le RDC entier et enlève uniquement des modules dessinés aux étages."""

        modules = sorted((o for o in scene.objets if o.kind == "module"), key=lambda o: o.niveau)
        disponibles = Counter(o.type_logement for o in modules)
        rdc = Counter(o.type_logement for o in modules if o.niveau == 0)
        for total in range(len(modules), max(1, sum(self.fixes.values())) - 1, -1):
            cible = self.cible(total)
            if all(rdc[t] <= n <= disponibles[t] for t, n in cible.items()):
                retirer = set()
                for o in modules:
                    if cible[o.type_logement]:
                        cible[o.type_logement] -= 1
                    else:
                        retirer.add(id(o))
                scene.objets = [o for o in scene.objets if id(o) not in retirer]
                return True
        return False

    def description(self):
        elements = [f"{n} {t} imposés" for t, n in self.fixes.items()]
        elements.extend(f"{n} % de {t}" for t, n in self.parts.items())
        return "Maximum de logements · " + " · ".join(elements) + (" (sur le complément)" if self.fixes else "")
