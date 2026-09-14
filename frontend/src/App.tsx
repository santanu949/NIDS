import { useEffect, useState } from 'react'
import { checkHealth, predictBinary, predictMulticlass } from './api'
import './App.css'

type Status = 'checking' | 'online' | 'offline'

function App() {
  const [status, setStatus] = useState<Status>('checking')
  const [binaryResult, setBinaryResult] = useState<{
    label: string
    confidence: number
  } | null>(null)
  const [multiclassResult, setMulticlassResult] = useState<{
    label: string
    confidence: number
  } | null>(null)

  useEffect(() => {
    checkHealth()
      .then(() => setStatus('online'))
      .catch(() => setStatus('offline'))
  }, [])

  const runDemoPrediction = async () => {
    try {
      // Real first row from UNSW-NB15 training-set.csv.
      // Ground truth: Normal, label 0.
      const sample = {
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

      const [binary, multiclass] = await Promise.all([
        predictBinary(sample),
        predictMulticlass(sample),
      ])

      setBinaryResult(binary)
      setMulticlassResult(multiclass)
      setStatus('online')
    } catch {
      setStatus('offline')
    }
  }

  return (
    <main className="dashboard">
      <header className="topbar">
        <div>
          <p className="eyebrow">NETWORK SECURITY</p>
          <h1>NIDS Monitor</h1>
        </div>

        <div className={`status ${status}`}>
          <span />
          API {status}
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

        <button type="button" onClick={runDemoPrediction}>
          Run prediction
        </button>
      </section>

      <section className="metrics">
        <article className="metric-card">
          <span className="metric-label">API STATUS</span>
          <strong>{status === 'online' ? 'ONLINE' : status.toUpperCase()}</strong>
          <small>FastAPI backend</small>
        </article>

        <article className="metric-card">
          <span className="metric-label">BINARY MODEL</span>
          <strong>{binaryResult?.label ?? '—'}</strong>
          <small>
            {binaryResult
              ? `${(binaryResult.confidence * 100).toFixed(1)}% confidence`
              : 'No prediction yet'}
          </small>
        </article>

        <article className="metric-card">
          <span className="metric-label">ATTACK CATEGORY</span>
          <strong>{multiclassResult?.label ?? '—'}</strong>
          <small>
            {multiclassResult
              ? `${(multiclassResult.confidence * 100).toFixed(1)}% confidence`
              : 'No prediction yet'}
          </small>
        </article>

        <article className="metric-card">
          <span className="metric-label">MODE</span>
          <strong>DATASET</strong>
          <small>UNSW-NB15</small>
        </article>
      </section>

      <section className="content-grid">
        <article className="panel">
          <div className="panel-heading">
            <div>
              <span className="metric-label">DETECTION</span>
              <h3>Latest classification</h3>
            </div>
          </div>

          <div className="classification">
            <div>
              <span>Binary result</span>
              <strong>{binaryResult?.label ?? 'Waiting'}</strong>
            </div>

            <div>
              <span>Attack category</span>
              <strong>{multiclassResult?.label ?? 'Waiting'}</strong>
            </div>

            <div>
              <span>Confidence</span>
              <strong>
                {multiclassResult
                  ? `${(multiclassResult.confidence * 100).toFixed(1)}%`
                  : '—'}
              </strong>
            </div>
          </div>
        </article>

        <article className="panel">
          <span className="metric-label">SYSTEM</span>
          <h3>Pipeline</h3>

          <div className="pipeline">
            <span>UNSW-NB15</span>
            <b>→</b>
            <span>Preprocessor</span>
            <b>→</b>
            <span>XGBoost</span>
            <b>→</b>
            <span>FastAPI</span>
            <b>→</b>
            <span>SQLite</span>
          </div>
        </article>
      </section>
    </main>
  )
}

export default App