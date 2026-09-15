import { useEffect, useState } from 'react'
import {
  checkHealth,
  getAnalytics,
  getEvents,
  getLiveStatus,
  predict,
  startLiveCapture,
  stopLiveCapture,
  type AnalyticsResponse,
  type LiveStatusResponse,
  type PredictionEvent,
  type PredictionResponse,
} from './api'
import './App.css'

const demoFeatures: Record<string, unknown> = {
  dur: 0.121478,
  proto: 'tcp',
  service: '-',
  state: 'FIN',
  spkts: 6,
  dpkts: 4,
  sbytes: 258,
  dbytes: 172,
  rate: 74.08749,
  sttl: 252,
  dttl: 254,
  sload: 14158.94238,
  dload: 8495.365234,
  sloss: 0,
  dloss: 0,
  sinpkt: 24.2956,
  dinpkt: 8.375,
  sjit: 30.177547,
  djit: 11.830604,
  swin: 255,
  stcpb: 621772692,
  dtcpb: 2202533631,
  dwin: 255,
  tcprtt: 0,
  synack: 0,
  ackdat: 0,
  smean: 43,
  dmean: 43,
  trans_depth: 0,
  response_body_len: 0,
  ct_srv_src: 1,
  ct_state_ttl: 0,
  ct_dst_ltm: 1,
  ct_src_dport_ltm: 1,
  ct_dst_sport_ltm: 1,
  ct_dst_src_ltm: 1,
  is_ftp_login: 0,
  ct_ftp_cmd: 0,
  ct_flw_http_mthd: 0,
  ct_src_ltm: 1,
  ct_srv_dst: 1,
  is_sm_ips_ports: 0,
}

function App() {
  const [apiOnline, setApiOnline] = useState(false)
  const [result, setResult] = useState<PredictionResponse | null>(null)
  const [events, setEvents] = useState<PredictionEvent[]>([])
  const [analytics, setAnalytics] = useState<AnalyticsResponse | null>(null)
  const [liveStatus, setLiveStatus] = useState<LiveStatusResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [liveLoading, setLiveLoading] = useState(false)
  const [error, setError] = useState('')

  const loadDashboardData = async () => {
    try {
      const [eventData, analyticsData] = await Promise.all([
        getEvents(),
        getAnalytics(),
      ])

      setEvents(eventData)
      setAnalytics(analyticsData)

      if (eventData.length > 0) {
        const latest = eventData[0]

        setResult({
          prediction: latest.binary_prediction,
          label: latest.binary_label,
          confidence: latest.binary_confidence,
          attack_category: latest.attack_category,
          multiclass_confidence: latest.multiclass_confidence,
        })
      }
    } catch {
      setEvents([])
      setAnalytics(null)
    }
  }

  const loadLiveStatus = async () => {
    try {
      const status = await getLiveStatus()
      setLiveStatus(status)
    } catch {
      setLiveStatus(null)
    }
  }

  useEffect(() => {
    checkHealth()
      .then(() => {
        setApiOnline(true)
        loadDashboardData()
        loadLiveStatus()
      })
      .catch(() => {
        setApiOnline(false)
      })
  }, [])

  useEffect(() => {
    const interval = window.setInterval(() => {
      if (apiOnline) {
        loadLiveStatus()
        loadDashboardData()
      }
    }, 2000)

    return () => window.clearInterval(interval)
  }, [apiOnline])

  const runDemoPrediction = async () => {
    setLoading(true)
    setError('')

    try {
      const prediction = await predict(demoFeatures)

      setResult(prediction)
      setApiOnline(true)

      await loadDashboardData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Prediction failed')
      setApiOnline(false)
    } finally {
      setLoading(false)
    }
  }

  const handleLiveToggle = async () => {
    setLiveLoading(true)
    setError('')

    try {
      const status = liveStatus?.running
        ? await stopLiveCapture()
        : await startLiveCapture()

      setLiveStatus(status)
      setApiOnline(true)

      await loadDashboardData()
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Live capture operation failed',
      )

      await loadLiveStatus()
    } finally {
      setLiveLoading(false)
    }
  }

  const liveRunning = liveStatus?.running ?? false

  return (
    <main className="dashboard">
      <header className="topbar">
        <div>
          <span className="brand">NETWORK SECURITY</span>
          <h1>NIDS Monitor</h1>
        </div>

        <div className={`status ${apiOnline ? 'online' : 'offline'}`}>
          <span className="status-dot" />
          API {apiOnline ? 'online' : 'offline'}
        </div>
      </header>

      <section className="hero-card">
        <div>
          <p className="eyebrow">INTRUSION DETECTION SYSTEM</p>
          <h2>Network activity at a glance.</h2>
          <p className="muted">
            ML-powered binary and multiclass traffic classification.
          </p>
        </div>

        <div>
          <button
            className="primary-button"
            onClick={runDemoPrediction}
            disabled={loading || !apiOnline || liveRunning}
          >
            {loading ? 'Running...' : 'Run prediction'}
          </button>

          <button
            className="primary-button"
            onClick={handleLiveToggle}
            disabled={
              liveLoading ||
              !apiOnline ||
              !liveStatus?.interface_configured
            }
          >
            {liveLoading
              ? 'Working...'
              : liveRunning
                ? 'Stop live capture'
                : 'Start live capture'}
          </button>
        </div>
      </section>

      <section className="metrics">
        <article className="metric-card">
          <span className="metric-label">API STATUS</span>
          <strong>{apiOnline ? 'ONLINE' : 'OFFLINE'}</strong>
          <small>FastAPI backend</small>
        </article>

        <article className="metric-card">
          <span className="metric-label">LIVE STATUS</span>
          <strong>{liveRunning ? 'CAPTURING' : 'STOPPED'}</strong>
          <small>
            {liveStatus?.interface_configured
              ? 'Npcap interface ready'
              : 'Interface not configured'}
          </small>
        </article>

        <article className="metric-card">
          <span className="metric-label">BINARY MODEL</span>
          <strong>{result?.label ?? '—'}</strong>
          <small>
            {result
              ? `${(result.confidence * 100).toFixed(1)}% confidence`
              : 'No prediction yet'}
          </small>
        </article>

        <article className="metric-card">
          <span className="metric-label">ATTACK CATEGORY</span>
          <strong>{result?.attack_category ?? '—'}</strong>
          <small>
            {result
              ? `${(result.multiclass_confidence * 100).toFixed(1)}% confidence`
              : 'No prediction yet'}
          </small>
        </article>

        <article className="metric-card">
          <span className="metric-label">MODE</span>
          <strong>{liveRunning ? 'LIVE' : 'DATASET'}</strong>
          <small>{liveRunning ? 'Packet capture' : 'UNSW-NB15'}</small>
        </article>

        <article className="metric-card">
          <span className="metric-label">RECENT EVENTS</span>
          <strong>{analytics?.total_events ?? 0}</strong>
          <small>All stored events</small>
        </article>

        <article className="metric-card">
          <span className="metric-label">NORMAL</span>
          <strong>{analytics?.normal_events ?? 0}</strong>
          <small>Stored classifications</small>
        </article>

        <article className="metric-card">
          <span className="metric-label">ATTACKS</span>
          <strong>{analytics?.attack_events ?? 0}</strong>
          <small>Stored binary detections</small>
        </article>

        <article className="metric-card">
          <span className="metric-label">ATTACK RATE</span>
          <strong>
            {analytics
              ? `${(analytics.attack_rate * 100).toFixed(1)}%`
              : '0.0%'}
          </strong>
          <small>Database-wide rate</small>
        </article>
      </section>

      <section className="content-grid">
        <article className="panel">
          <div className="panel-heading">
            <span className="eyebrow">DETECTION</span>
            <h3>Latest classification</h3>
          </div>

          <div className="classification">
            <div>
              <span>Binary result</span>
              <strong>{result?.label ?? 'Waiting'}</strong>
            </div>

            <div>
              <span>Attack category</span>
              <strong>{result?.attack_category ?? 'Waiting'}</strong>
            </div>

            <div>
              <span>Binary confidence</span>
              <strong>
                {result
                  ? `${(result.confidence * 100).toFixed(1)}%`
                  : '—'}
              </strong>
            </div>

            <div>
              <span>Multiclass confidence</span>
              <strong>
                {result
                  ? `${(result.multiclass_confidence * 100).toFixed(1)}%`
                  : '—'}
              </strong>
            </div>
          </div>
        </article>

        <article className="panel">
          <div className="panel-heading">
            <span className="eyebrow">SYSTEM</span>
            <h3>Pipeline</h3>
          </div>

          <div className="pipeline">
            <span>Packets</span>
            <span>→</span>
            <span>Flows</span>
            <span>→</span>
            <span>Preprocessor</span>
            <span>→</span>
            <span>XGBoost</span>
            <span>→</span>
            <span>SQLite</span>
          </div>
        </article>
      </section>

      {error && <p className="error">{error}</p>}

      <section className="panel events-panel">
        <div className="panel-heading">
          <span className="eyebrow">DATABASE</span>
          <h3>Recent prediction events</h3>
        </div>

        {events.length === 0 ? (
          <p className="muted">No prediction events stored yet.</p>
        ) : (
          <div className="events-list">
            {events.slice(0, 10).map((event) => (
              <div className="event-row" key={event.id}>
                <span>#{event.id}</span>
                <span>{event.mode.toUpperCase()}</span>

                <div>
                  <strong>{event.binary_label}</strong>
                  <small>
                    Binary {(event.binary_confidence * 100).toFixed(1)}%
                  </small>
                </div>

                <div>
                  <strong>{event.attack_category}</strong>
                  <small>
                    Category{' '}
                    {(event.multiclass_confidence * 100).toFixed(1)}%
                  </small>
                </div>

                <span>
                  {event.binary_prediction ? 'ATTACK' : 'NORMAL'}
                </span>

                <time>
                  {new Date(event.timestamp).toLocaleTimeString()}
                </time>
              </div>
            ))}
          </div>
        )}
      </section>
    </main>
  )
}

export default App