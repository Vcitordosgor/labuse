import { CookieConsent } from '../CookieConsent'
import { MapView } from '../map/MapView'
import { Gabarit } from './Gabarit'

export default function GabaritMobile() {
  return (
    <main className="flex h-dvh flex-col overflow-hidden bg-bg text-txt">
      <header className="flex items-center justify-between border-b border-line px-3 py-2">
        <h1 className="font-semibold">Gabarit</h1>
        <a className="text-sm text-mint" href={window.location.pathname}>Fermer</a>
      </header>
      <div className="flex min-h-0 flex-[2]"><MapView /></div>
      <div className="flex min-h-0 flex-[3] flex-col border-t border-line p-3"><Gabarit /></div>
      <CookieConsent />
    </main>
  )
}
