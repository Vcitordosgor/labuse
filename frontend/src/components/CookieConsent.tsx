import { useEffect, useState } from 'react'

// NU5-FIX-1 (C-F4) — bannière de consentement aux cookies / traceurs tiers (ePrivacy / CNIL),
// exigée avant exploitation commerciale en France. LABUSE n'a pas de pub ni de traceur analytique,
// mais la politique de confidentialité déclare des tiers non essentiels (Google Street View/Fonts,
// Cloudflare) : l'utilisateur doit pouvoir ACCEPTER ou REFUSER les tiers non essentiels, et son
// choix est mémorisé. Le socle (session, préférences) est fonctionnel-nécessaire (pas de consentement).
const CLE = 'labuse_consent_cookies_v1'

export function CookieConsent() {
  const [choix, setChoix] = useState<string | null>(() => {
    try { return localStorage.getItem(CLE) } catch { return 'accepte' }  // stockage indispo → ne bloque pas
  })
  useEffect(() => {
    if (choix) { try { localStorage.setItem(CLE, choix) } catch { /* noop */ } }
  }, [choix])
  if (choix) return null
  return (
    <div data-cookie-consent role="dialog" aria-label="Consentement aux cookies"
         className="fixed inset-x-0 bottom-0 z-[1000] border-t border-line bg-surface-2 px-4 py-3 shadow-elev-2">
      <div className="mx-auto flex max-w-[1100px] flex-col gap-2 sm:flex-row sm:items-center">
        <p className="flex-1 text-[12px] leading-relaxed text-txt">
          LABUSE utilise des cookies strictement nécessaires (session, préférences). Des services
          tiers non essentiels (fonds de carte, vue immersive) peuvent déposer des traceurs.{' '}
          <a href="https://labuse.immo/confidentialite/" target="_blank" rel="noreferrer"
             className="underline text-mint">En savoir plus</a>.
        </p>
        <div className="flex shrink-0 gap-2">
          <button onClick={() => setChoix('refuse')}
                  className="min-h-[36px] rounded-md border border-line-2 px-3 text-[12px] text-txt hover:bg-surface-3">
            Refuser les tiers
          </button>
          <button onClick={() => setChoix('accepte')}
                  className="min-h-[36px] rounded-md bg-mint px-3 text-[12px] font-medium text-bg-0 hover:opacity-90">
            Tout accepter
          </button>
        </div>
      </div>
    </div>
  )
}
