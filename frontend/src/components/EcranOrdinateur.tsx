import { Oiseau } from './States'

// CHARGEMENT-1 (point 6) — l'écran UNIQUE affiché sur téléphone/tablette (cf. lib/appareil.ts).
// DA de l'app (fond nuit, menthe de marque). Aucune autre page n'est accessible depuis ici.
export function EcranOrdinateur() {
  return (
    <div data-ecran-ordinateur
      className="flex min-h-screen flex-col items-center justify-center gap-5 bg-bg-0 px-7 text-center">
      <div className="flex flex-col items-center gap-3">
        <Oiseau className="h-9 w-auto" dim={false} />
        <span className="font-display text-2xl font-bold tracking-[0.04em] text-txt-hi">LABUSE</span>
      </div>
      <p className="text-base font-medium text-txt-hi">LABUSE est disponible sur ordinateur.</p>
      <p className="max-w-[360px] text-sm leading-relaxed text-txt-mut">
        Ouvrez <span className="font-medium text-mint">app.labuse.immo</span> depuis votre ordinateur.
      </p>
      <a href="mailto:contact@labuse.immo?subject=Contact%20LABUSE"
        className="mt-1 text-sm font-medium text-mint hover:underline">
        Contact
      </a>
    </div>
  )
}
