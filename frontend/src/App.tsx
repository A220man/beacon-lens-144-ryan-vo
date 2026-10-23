import { useEffect, useState } from 'react'

interface HealthResponse {
  status: string
  version: string
  service: string
}

function App() {
  const [backendHealth, setBackendHealth] = useState<HealthResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchHealth = async () => {
    try {
      const response = await fetch('/api/v1/health')
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`)
      }
      const data = await response.json()
      setBackendHealth(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
      setBackendHealth(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchHealth()
  }, [])

  return (
    <div className="container">
      <header style={{ marginBottom: '2rem' }}>
        <h1>Beacon Lens</h1>
        <p className="muted">AI/ML Knowledge Platform — RAG · Agent · Wiki</p>
      </header>

      <section className="card">
        <h2>System Status</h2>
        {loading ? (
          <p className="muted">Checking backend health...</p>
        ) : error ? (
          <div>
            <p className="status-error">Backend unreachable</p>
            <p className="muted">{error}</p>
            <button className="btn btn-secondary" onClick={() => { setLoading(true); fetchHealth(); }}>
              Retry
            </button>
          </div>
        ) : backendHealth ? (
          <div>
            <p>
              <span className="status-ok">● Online</span> {' '}
              <span className="muted">| {backendHealth.service} v{backendHealth.version}</span>
            </p>
            <p className="muted">Status: {backendHealth.status}</p>
          </div>
        ) : null}
      </section>

      <section className="card">
        <h2>Workflows</h2>
        <div className="grid">
          <div className="card">
            <h3>RAG Query</h3>
            <p className="muted">Upload documents, chunk, embed, and query with semantic search.</p>
            <button className="btn btn-primary" disabled>Coming Soon</button>
          </div>
          <div className="card">
            <h3>Wiki Generation</h3>
            <p className="muted">Auto-generate structured wiki from documents with extract/reduce pipeline.</p>
            <button className="btn btn-primary" disabled>Coming Soon</button>
          </div>
          <div className="card">
            <h3>Reasoning Agent</h3>
            <p className="muted">Autonomous agent with tool use for multi-step question answering.</p>
            <button className="btn btn-primary" disabled>Coming Soon</button>
          </div>
        </div>
      </section>

      <footer style={{ marginTop: '2rem', textAlign: 'center' }}>
        <p className="muted">
          Beacon Lens — Ryan Vo | AI & Machine Learning
          <br />
          <a href="mailto:ryandtvo@gmail.com" className="muted">ryandtvo@gmail.com</a>
        </p>
      </footer>
    </div>
  )
}

export default App