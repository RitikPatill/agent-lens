import { Routes, Route, Link } from 'react-router-dom'
import RunList from './pages/RunList'
import RunDetail from './pages/RunDetail'

export default function App() {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <header className="border-b border-zinc-800 px-6 py-3 flex items-center gap-4">
        <Link to="/" className="text-lg font-bold tracking-tight text-zinc-100 hover:text-white">
          AgentLens
        </Link>
        <span className="text-zinc-500 text-sm">trace & eval dashboard</span>
      </header>
      <main className="px-6 py-6">
        <Routes>
          <Route path="/" element={<RunList />} />
          <Route path="/runs/:runId" element={<RunDetail />} />
        </Routes>
      </main>
    </div>
  )
}
