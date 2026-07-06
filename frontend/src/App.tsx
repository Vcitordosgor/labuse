import { Header } from './components/header/Header'
import { FicheShell } from './components/fiche/FicheShell'
import { LeftPanel } from './components/panel/LeftPanel'
import { MapView } from './components/map/MapView'
import { Rail } from './components/Rail'
import { useApp } from './store/useApp'

export default function App() {
  const selectedIdu = useApp((s) => s.selectedIdu)
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-bg text-txt font-sans">
      <Rail />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <div className="relative flex flex-1 overflow-hidden">
          <LeftPanel />
          <MapView />
          {selectedIdu && <FicheShell idu={selectedIdu} />}
        </div>
      </div>
    </div>
  )
}
