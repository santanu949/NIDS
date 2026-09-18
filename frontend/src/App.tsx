import { useEffect, useMemo, useState } from 'react'
import {
  checkHealth,
  connectToAlerts,
  getAnalytics,
  getEvents,
  getLiveStatus,
  getModelFeatures,
  getModelMetrics,
  predict,
  startLiveCapture,
  stopLiveCapture,
  type AnalyticsResponse,
  type LiveStatusResponse,
  type ModelFeaturesResponse,
  type ModelMetricsResponse,
  type PredictionEvent,
  type PredictionResponse,
  type WebSocketAlert,
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

const severityOrder: Record<string, number> = {
  critical: 4,
  high: 3,
  medium: 2,
  low: 1,
}

type ViewName =
  | 'dashboard'
  | 'detections'
  | 'analytics'
  | 'model'
  | 'system'

function formatPercent(value: number) {
  return `${(value * 100).toFixed(1)}%`
}

function formatMetric(value: number) {
  return value.toFixed(4)
}

function formatFeatureName(name: string) {
  return name
    .replace(/^num__/, '')
    .replace(/^cat__/, '')
    .replace(/_/g, ' ')
}

function App() {
  const [activeView, setActiveView] =
    useState<ViewName>('dashboard')

  const [apiOnline, setApiOnline] = useState(false)
  const [websocketConnected, setWebsocketConnected] =
    useState(false)

  const [result, setResult] =
    useState<PredictionResponse | null>(null)

  const [events, setEvents] = useState<PredictionEvent[]>([])
  const [analytics, setAnalytics] =
    useState<AnalyticsResponse | null>(null)

  const [modelMetrics, setModelMetrics] =
    useState<ModelMetricsResponse | null>(null)

  const [modelFeatures, setModelFeatures] =
    useState<ModelFeaturesResponse | null>(null)

  const [liveStatus, setLiveStatus] =
    useState<LiveStatusResponse | null>(null)

  const [loading, setLoading] = useState(false)
  const [liveLoading, setLiveLoading] = useState(false)
  const [modelLoading, setModelLoading] = useState(false)
  const [error, setError] = useState('')

  const [categoryFilter, setCategoryFilter] = useState('all')
  const [severityFilter, setSeverityFilter] = useState('all')
  const [modeFilter, setModeFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [searchFilter, setSearchFilter] = useState('')

  const [selectedEvent, setSelectedEvent] =
    useState<PredictionEvent | null>(null)

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
          multiclass_confidence:
            latest.multiclass_confidence,
          severity: latest.severity,
          model_version: latest.model_version,
        })
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Failed to load dashboard data',
      )
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

  const loadModelData = async () => {
    setModelLoading(true)

    try {
      const [metrics, features] = await Promise.all([
        getModelMetrics(),
        getModelFeatures(),
      ])

      setModelMetrics(metrics)
      setModelFeatures(features)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Failed to load model data',
      )
    } finally {
      setModelLoading(false)
    }
  }

  useEffect(() => {
    let websocket: WebSocket | null = null

    checkHealth()
      .then(() => {
        setApiOnline(true)

        void loadDashboardData()
        void loadLiveStatus()
        void loadModelData()

        websocket = connectToAlerts(
          (alert: WebSocketAlert) => {
            if (alert.event !== 'prediction') {
              return
            }

            const detection = alert.detection

            setEvents((currentEvents) => {
              const withoutDuplicate =
                currentEvents.filter(
                  (event) => event.id !== detection.id,
                )

              return [
                detection,
                ...withoutDuplicate,
              ].slice(0, 100)
            })

            setResult({
              prediction: detection.binary_prediction,
              label: detection.binary_label,
              confidence:
                detection.binary_confidence,
              attack_category:
                detection.attack_category,
              multiclass_confidence:
                detection.multiclass_confidence,
              severity: detection.severity,
              model_version:
                detection.model_version,
            })

            setAnalytics((currentAnalytics) => {
              if (!currentAnalytics) {
                return currentAnalytics
              }

              const isAttack =
                detection.binary_prediction === 1

              const category =
                detection.attack_category

              const nextTotal =
                currentAnalytics.total_events + 1

              const nextAttackCount =
                currentAnalytics.attack_events +
                (isAttack ? 1 : 0)

              return {
                ...currentAnalytics,
                total_events: nextTotal,
                normal_events:
                  currentAnalytics.normal_events +
                  (isAttack ? 0 : 1),
                attack_events: nextAttackCount,
                attack_rate:
                  nextTotal > 0
                    ? nextAttackCount / nextTotal
                    : 0,
                attack_categories: {
                  ...currentAnalytics.attack_categories,
                  [category]:
                    (currentAnalytics
                      .attack_categories[category] ?? 0) + 1,
                },
              }
            })
          },
          (connected: boolean) => {
            setWebsocketConnected(connected)
          },
        )
      })
      .catch(() => {
        setApiOnline(false)
        setWebsocketConnected(false)
      })

    return () => {
      websocket?.close()
    }
  }, [])

  useEffect(() => {
    const interval = window.setInterval(() => {
      if (apiOnline) {
        void loadLiveStatus()
        void loadDashboardData()
      }
    }, 2000)

    return () => window.clearInterval(interval)
  }, [apiOnline])

  const runDemoPrediction = async () => {
    setLoading(true)
    setError('')

    try {
      const prediction = await predict(
        demoFeatures,
        'dataset',
      )

      setResult(prediction)
      setApiOnline(true)

      await loadDashboardData()
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Prediction failed',
      )
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

  const filteredEvents = useMemo(() => {
    const search =
      searchFilter.trim().toLowerCase()

    return events
      .filter((event) => {
        if (
          categoryFilter !== 'all' &&
          event.attack_category !== categoryFilter
        ) {
          return false
        }

        if (
          severityFilter !== 'all' &&
          event.severity !== severityFilter
        ) {
          return false
        }

        if (
          modeFilter !== 'all' &&
          event.mode !== modeFilter
        ) {
          return false
        }

        if (
          statusFilter === 'attack' &&
          event.binary_prediction !== 1
        ) {
          return false
        }

        if (
          statusFilter === 'normal' &&
          event.binary_prediction !== 0
        ) {
          return false
        }

        if (!search) {
          return true
        }

        const searchable = [
          String(event.id),
          event.mode,
          event.source_ip ?? '',
          event.destination_ip ?? '',
          event.protocol ?? '',
          event.binary_label,
          event.attack_category,
          event.severity,
          event.model_version,
        ]
          .join(' ')
          .toLowerCase()

        return searchable.includes(search)
      })
      .sort((a, b) => {
        const severityDifference =
          (severityOrder[b.severity] ?? 0) -
          (severityOrder[a.severity] ?? 0)

        if (severityDifference !== 0) {
          return severityDifference
        }

        return (
          new Date(b.timestamp).getTime() -
          new Date(a.timestamp).getTime()
        )
      })
  }, [
    events,
    categoryFilter,
    severityFilter,
    modeFilter,
    statusFilter,
    searchFilter,
  ])

  const categories = useMemo(() => {
    return Array.from(
      new Set(
        events.map(
          (event) => event.attack_category,
        ),
      ),
    ).sort()
  }, [events])

  const highSeverityCount = events.filter(
    (event) =>
      event.severity === 'high' ||
      event.severity === 'critical',
  ).length

  const liveRunning =
    liveStatus?.running ?? false

  const sortedAttackCategories = useMemo(() => {
    if (!analytics) {
      return []
    }

    return Object.entries(
      analytics.attack_categories,
    )
      .map(([category, count]) => ({
        category,
        count,
      }))
      .sort((a, b) => b.count - a.count)
  }, [analytics])

  const maxAttackCategoryCount =
    sortedAttackCategories.length > 0
      ? Math.max(
          ...sortedAttackCategories.map(
            (item) => item.count,
          ),
        )
      : 1

  const topFeatures = useMemo(() => {
    if (!modelFeatures) {
      return []
    }

    return [...modelFeatures.features]
      .sort((a, b) => b.importance - a.importance)
      .slice(0, 15)
  }, [modelFeatures])

  const maxFeatureImportance =
    topFeatures.length > 0
      ? Math.max(
          ...topFeatures.map(
            (feature) => feature.importance,
          ),
        )
      : 1

  const resetFilters = () => {
    setCategoryFilter('all')
    setSeverityFilter('all')
    setModeFilter('all')
    setStatusFilter('all')
    setSearchFilter('')
  }

  const exportEvents = () => {
    const headers = [
      'id',
      'timestamp',
      'mode',
      'source_ip',
      'destination_ip',
      'protocol',
      'binary_prediction',
      'binary_label',
      'binary_confidence',
      'attack_category',
      'multiclass_confidence',
      'severity',
      'model_version',
    ]

    const escapeCsv = (value: unknown) => {
      const stringValue =
        value == null ? '' : String(value)

      return `"${stringValue.replaceAll('"', '""')}"`
    }

    const rows = filteredEvents.map((event) =>
      [
        event.id,
        event.timestamp,
        event.mode,
        event.source_ip,
        event.destination_ip,
        event.protocol,
        event.binary_prediction,
        event.binary_label,
        event.binary_confidence,
        event.attack_category,
        event.multiclass_confidence,
        event.severity,
        event.model_version,
      ]
        .map(escapeCsv)
        .join(','),
    )

    const csv = [
      headers.join(','),
      ...rows,
    ].join('\n')

    const blob = new Blob([csv], {
      type: 'text/csv;charset=utf-8;',
    })

    const url =
      URL.createObjectURL(blob)

    const anchor =
      document.createElement('a')

    anchor.href = url
    anchor.download =
      'nids-detections.csv'
    anchor.click()

    URL.revokeObjectURL(url)
  }

  const navigation = [
    {
      id: 'dashboard' as const,
      label: 'Dashboard',
    },
    {
      id: 'detections' as const,
      label: 'Detections',
    },
    {
      id: 'analytics' as const,
      label: 'Analytics',
    },
    {
      id: 'model' as const,
      label: 'Model',
    },
    {
      id: 'system' as const,
      label: 'System',
    },
  ]

  return (
    <main className="dashboard">
      <header className="topbar">
        <div>
          <span className="brand">
            NETWORK SECURITY
          </span>
          <h1>NIDS Monitor</h1>
        </div>

        <div
          className={`status ${
            apiOnline
              ? 'online'
              : 'offline'
          }`}
        >
          <span className="status-dot" />
          API {apiOnline ? 'online' : 'offline'}
        </div>
      </header>

      <nav className="navigation-panel">
        {navigation.map((item) => (
          <button
            key={item.id}
            className={
              activeView === item.id
                ? 'navigation-button active'
                : 'navigation-button'
            }
            onClick={() =>
              setActiveView(item.id)
            }
          >
            {item.label}
          </button>
        ))}
      </nav>

      {activeView === 'dashboard' && (
        <>
          <section className="hero-card">
            <div>
              <p className="eyebrow">
                INTRUSION DETECTION SYSTEM
              </p>

              <h2>
                Network activity at a glance.
              </h2>

              <p className="muted">
                ML-powered binary and
                multiclass traffic
                classification.
              </p>
            </div>

            <div className="hero-actions">
              <button
                onClick={runDemoPrediction}
                disabled={
                  loading ||
                  !apiOnline ||
                  liveRunning
                }
              >
                {loading
                  ? 'Running...'
                  : 'Run prediction'}
              </button>

              <button
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
              <div className="metric-label">
                API STATUS
              </div>

              <strong>
                {apiOnline
                  ? 'ONLINE'
                  : 'OFFLINE'}
              </strong>

              <span>
                FastAPI backend
              </span>
            </article>

            <article className="metric-card">
              <div className="metric-label">
                ALERT STREAM
              </div>

              <strong>
                {websocketConnected
                  ? 'CONNECTED'
                  : 'DISCONNECTED'}
              </strong>

              <span>
                WebSocket /ws/alerts
              </span>
            </article>

            <article className="metric-card">
              <div className="metric-label">
                LIVE STATUS
              </div>

              <strong>
                {liveRunning
                  ? 'CAPTURING'
                  : 'STOPPED'}
              </strong>

              <span>
                {liveStatus?.interface_configured
                  ? 'Npcap interface ready'
                  : 'Interface not configured'}
              </span>
            </article>

            <article className="metric-card">
              <div className="metric-label">
                BINARY MODEL
              </div>

              <strong>
                {result?.label ?? '—'}
              </strong>

              <span>
                {result
                  ? `${formatPercent(
                      result.confidence,
                    )} confidence`
                  : 'No prediction yet'}
              </span>
            </article>

            <article className="metric-card">
              <div className="metric-label">
                ATTACK CATEGORY
              </div>

              <strong>
                {result?.attack_category ??
                  '—'}
              </strong>

              <span>
                {result
                  ? `${formatPercent(
                      result.multiclass_confidence,
                    )} confidence`
                  : 'No prediction yet'}
              </span>
            </article>

            <article className="metric-card">
              <div className="metric-label">
                MODE
              </div>

              <strong>
                {liveRunning
                  ? 'LIVE'
                  : 'DATASET'}
              </strong>

              <span>
                {liveRunning
                  ? 'Packet capture'
                  : 'UNSW-NB15'}
              </span>
            </article>

            <article className="metric-card">
              <div className="metric-label">
                TOTAL EVENTS
              </div>

              <strong>
                {analytics?.total_events ??
                  0}
              </strong>

              <span>
                Stored predictions
              </span>
            </article>

            <article className="metric-card">
              <div className="metric-label">
                ATTACKS
              </div>

              <strong>
                {analytics?.attack_events ??
                  0}
              </strong>

              <span>
                Binary detections
              </span>
            </article>

            <article className="metric-card">
              <div className="metric-label">
                THREAT RATE
              </div>

              <strong>
                {analytics
                  ? formatPercent(
                      analytics.attack_rate,
                    )
                  : '0.0%'}
              </strong>

              <span>
                Database-wide rate
              </span>
            </article>

            <article className="metric-card">
              <div className="metric-label">
                HIGH SEVERITY
              </div>

              <strong>
                {highSeverityCount}
              </strong>

              <span>
                High + critical events
              </span>
            </article>
          </section>

          <section className="content-grid">
            <article className="panel">
              <div className="panel-heading">
                <span className="eyebrow">
                  DETECTION
                </span>

                <h3>
                  Latest classification
                </h3>
              </div>

              <div className="classification">
                <div>
                  <span>
                    Binary result
                  </span>

                  <strong>
                    {result?.label ??
                      'Waiting'}
                  </strong>
                </div>

                <div>
                  <span>
                    Attack category
                  </span>

                  <strong>
                    {result?.attack_category ??
                      'Waiting'}
                  </strong>
                </div>

                <div>
                  <span>
                    Binary confidence
                  </span>

                  <strong>
                    {result
                      ? formatPercent(
                          result.confidence,
                        )
                      : '—'}
                  </strong>
                </div>

                <div>
                  <span>
                    Multiclass confidence
                  </span>

                  <strong>
                    {result
                      ? formatPercent(
                          result.multiclass_confidence,
                        )
                      : '—'}
                  </strong>
                </div>

                <div>
                  <span>
                    Severity
                  </span>

                  <strong>
                    {result?.severity ??
                      '—'}
                  </strong>
                </div>

                <div>
                  <span>
                    Model version
                  </span>

                  <strong>
                    {result?.model_version ??
                      '—'}
                  </strong>
                </div>
              </div>
            </article>

            <article className="panel">
              <div className="panel-heading">
                <span className="eyebrow">
                  SYSTEM
                </span>

                <h3>
                  Pipeline
                </h3>
              </div>

              <div className="pipeline">
                <div className="pipeline-step">
                  <span>01</span>{' '}
                  Packet capture
                </div>

                <div className="pipeline-step">
                  <span>02</span>{' '}
                  Flow aggregation
                </div>

                <div className="pipeline-step">
                  <span>03</span>{' '}
                  Feature preprocessing
                </div>

                <div className="pipeline-step">
                  <span>04</span>{' '}
                  XGBoost classification
                </div>

                <div className="pipeline-step">
                  <span>05</span>{' '}
                  Database persistence
                </div>

                <div className="pipeline-step">
                  <span>06</span>{' '}
                  WebSocket alert
                </div>
              </div>
            </article>
          </section>
        </>
      )}

      {activeView === 'detections' && (
        <section className="panel events-panel">
          <div className="panel-heading">
            <span className="eyebrow">
              DETECTION HISTORY
            </span>

            <h3>
              Search and filter events
            </h3>

            <p>
              Filter stored predictions
              by classification,
              category, severity,
              mode, or network
              metadata.
            </p>
          </div>

          <div className="filter-grid">
            <label>
              Search

              <input
                type="search"
                value={searchFilter}
                onChange={(event) =>
                  setSearchFilter(
                    event.target.value,
                  )
                }
                placeholder="ID, IP, protocol, category..."
              />
            </label>

            <label>
              Status

              <select
                value={statusFilter}
                onChange={(event) =>
                  setStatusFilter(
                    event.target.value,
                  )
                }
              >
                <option value="all">
                  All
                </option>

                <option value="attack">
                  Attack
                </option>

                <option value="normal">
                  Normal
                </option>
              </select>
            </label>

            <label>
              Category

              <select
                value={categoryFilter}
                onChange={(event) =>
                  setCategoryFilter(
                    event.target.value,
                  )
                }
              >
                <option value="all">
                  All categories
                </option>

                {categories.map(
                  (category) => (
                    <option
                      key={category}
                      value={category}
                    >
                      {category}
                    </option>
                  ),
                )}
              </select>
            </label>

            <label>
              Severity

              <select
                value={severityFilter}
                onChange={(event) =>
                  setSeverityFilter(
                    event.target.value,
                  )
                }
              >
                <option value="all">
                  All severities
                </option>

                <option value="critical">
                  Critical
                </option>

                <option value="high">
                  High
                </option>

                <option value="medium">
                  Medium
                </option>

                <option value="low">
                  Low
                </option>
              </select>
            </label>

            <label>
              Mode

              <select
                value={modeFilter}
                onChange={(event) =>
                  setModeFilter(
                    event.target.value,
                  )
                }
              >
                <option value="all">
                  All modes
                </option>

                <option value="dataset">
                  Dataset
                </option>

                <option value="live">
                  Live
                </option>
              </select>
            </label>

            <div className="filter-actions">
              <button
                onClick={resetFilters}
              >
                Reset
              </button>

              <button
                onClick={exportEvents}
              >
                Export CSV
              </button>
            </div>
          </div>

          <div className="events-summary">
            <span>
              Showing{' '}
              <strong>
                {filteredEvents.length}
              </strong>{' '}
              of{' '}
              <strong>
                {events.length}
              </strong>{' '}
              loaded events
            </span>

            <span>
              WebSocket:{' '}
              <strong>
                {websocketConnected
                  ? 'connected'
                  : 'fallback polling'}
              </strong>
            </span>
          </div>

          {filteredEvents.length === 0 ? (
            <p className="muted empty-state">
              No events match the
              current filters.
            </p>
          ) : (
            <div className="events-list">
              {filteredEvents
                .slice(0, 50)
                .map((event) => (
                  <button
                    className="event-row event-row-button"
                    key={event.id}
                    onClick={() =>
                      setSelectedEvent(
                        event,
                      )
                    }
                  >
                    <span>
                      #{event.id}
                    </span>

                    <span>
                      {event.mode.toUpperCase()}
                    </span>

                    <div>
                      <strong>
                        {event.binary_label}
                      </strong>

                      <small>
                        Binary{' '}
                        {formatPercent(
                          event.binary_confidence,
                        )}
                      </small>
                    </div>

                    <div>
                      <strong>
                        {
                          event.attack_category
                        }
                      </strong>

                      <small>
                        Category{' '}
                        {formatPercent(
                          event.multiclass_confidence,
                        )}
                      </small>
                    </div>

                    <div>
                      <strong>
                        {event.severity.toUpperCase()}
                      </strong>

                      <small>
                        {
                          event.model_version
                        }
                      </small>
                    </div>

                    <span>
                      {event.binary_prediction
                        ? 'ATTACK'
                        : 'NORMAL'}
                    </span>

                    <time>
                      {new Date(
                        event.timestamp,
                      ).toLocaleTimeString()}
                    </time>
                  </button>
                ))}
            </div>
          )}
        </section>
      )}

      {activeView === 'analytics' && (
        <>
          <section className="metrics">
            <article className="metric-card">
              <div className="metric-label">
                TOTAL EVENTS
              </div>

              <strong>
                {analytics?.total_events ??
                  0}
              </strong>

              <span>
                Persisted predictions
              </span>
            </article>

            <article className="metric-card">
              <div className="metric-label">
                NORMAL
              </div>

              <strong>
                {analytics?.normal_events ??
                  0}
              </strong>

              <span>
                Binary normal
                classifications
              </span>
            </article>

            <article className="metric-card">
              <div className="metric-label">
                ATTACKS
              </div>

              <strong>
                {analytics?.attack_events ??
                  0}
              </strong>

              <span>
                Binary attack
                classifications
              </span>
            </article>

            <article className="metric-card">
              <div className="metric-label">
                THREAT RATE
              </div>

              <strong>
                {analytics
                  ? formatPercent(
                      analytics.attack_rate,
                    )
                  : '0.0%'}
              </strong>

              <span>
                Attack / total
              </span>
            </article>

            <article className="metric-card">
              <div className="metric-label">
                BINARY CONFIDENCE
              </div>

              <strong>
                {analytics
                  ? formatPercent(
                      analytics.average_binary_confidence,
                    )
                  : '0.0%'}
              </strong>

              <span>
                Average stored
                confidence
              </span>
            </article>

            <article className="metric-card">
              <div className="metric-label">
                MULTICLASS CONFIDENCE
              </div>

              <strong>
                {analytics
                  ? formatPercent(
                      analytics.average_multiclass_confidence,
                    )
                  : '0.0%'}
              </strong>

              <span>
                Average category
                confidence
              </span>
            </article>
          </section>

          <section className="panel analytics-panel">
            <div className="panel-heading">
              <span className="eyebrow">
                ATTACK DISTRIBUTION
              </span>

              <h3>
                Stored attack categories
              </h3>

              <p>
                Counts come directly
                from the prediction
                database.
              </p>
            </div>

            {sortedAttackCategories.length ===
            0 ? (
              <p className="muted">
                No attack-category
                data available.
              </p>
            ) : (
              <div className="bar-list">
                {sortedAttackCategories.map(
                  (item) => {
                    const width =
                      (item.count /
                        maxAttackCategoryCount) *
                      100

                    return (
                      <div
                        className="bar-row"
                        key={item.category}
                      >
                        <div className="bar-label">
                          <strong>
                            {item.category}
                          </strong>

                          <span>
                            {item.count}
                          </span>
                        </div>

                        <div className="bar-track">
                          <div
                            className="bar-fill"
                            style={{
                              width: `${width}%`,
                            }}
                          />
                        </div>
                      </div>
                    )
                  },
                )}
              </div>
            )}
          </section>
        </>
      )}

      {activeView === 'model' && (
        <>
          {modelLoading && (
            <section className="panel">
              <p className="muted">
                Loading model
                evaluation...
              </p>
            </section>
          )}

          {!modelLoading &&
            modelMetrics && (
              <>
                <section className="metrics">
                  <article className="metric-card">
                    <div className="metric-label">
                      DATASET
                    </div>

                    <strong>
                      {modelMetrics.dataset}
                    </strong>

                    <span>
                      Primary training
                      dataset
                    </span>
                  </article>

                  <article className="metric-card">
                    <div className="metric-label">
                      PRIMARY MODEL
                    </div>

                    <strong>
                      {modelMetrics.primary_model}
                    </strong>

                    <span>
                      Selected by{' '}
                      {
                        modelMetrics.model_selection_metric
                      }
                    </span>
                  </article>

                  <article className="metric-card">
                    <div className="metric-label">
                      FEATURES
                    </div>

                    <strong>
                      {
                        modelMetrics.transformed_feature_count
                      }
                    </strong>

                    <span>
                      After preprocessing
                    </span>
                  </article>

                  <article className="metric-card">
                    <div className="metric-label">
                      VALIDATION ROWS
                    </div>

                    <strong>
                      {modelMetrics.validation_rows.toLocaleString()}
                    </strong>

                    <span>
                      Held-out validation
                    </span>
                  </article>

                  <article className="metric-card">
                    <div className="metric-label">
                      MULTICLASS ACCURACY
                    </div>

                    <strong>
                      {formatPercent(
                        modelMetrics.multiclass_accuracy,
                      )}
                    </strong>

                    <span>
                      Validation result
                    </span>
                  </article>

                  <article className="metric-card">
                    <div className="metric-label">
                      MULTICLASS MACRO F1
                    </div>

                    <strong>
                      {formatPercent(
                        modelMetrics.multiclass_macro_f1,
                      )}
                    </strong>

                    <span>
                      Imbalance-sensitive
                      metric
                    </span>
                  </article>

                  <article className="metric-card">
                    <div className="metric-label">
                      WEIGHTED F1
                    </div>

                    <strong>
                      {formatPercent(
                        modelMetrics.multiclass_weighted_f1,
                      )}
                    </strong>

                    <span>
                      Multiclass validation
                    </span>
                  </article>

                  <article className="metric-card">
                    <div className="metric-label">
                      OFFICIAL TEST
                    </div>

                    <strong>
                      {modelMetrics.official_test_evaluation_available
                        ? 'EVALUATED'
                        : 'NOT AVAILABLE'}
                    </strong>

                    <span>
                      {modelMetrics.official_test_set_used
                        ? 'Used during model development'
                        : 'Held out for training and selection'}
                    </span>
                  </article>

                </section>

                <section className="panel model-panel">
                  <div className="panel-heading">
                    <span className="eyebrow">
                      BINARY EVALUATION
                    </span>

                    <h3>
                      Model comparison
                    </h3>

                    <p>
                      Validation metrics
                      used during model
                      selection.
                    </p>
                  </div>

                  <div className="model-table-wrapper">
                    <table className="model-table">
                      <thead>
                        <tr>
                          <th>
                            Model
                          </th>

                          <th>
                            Accuracy
                          </th>

                          <th>
                            Precision
                          </th>

                          <th>
                            Recall
                          </th>

                          <th>
                            F1
                          </th>

                          <th>
                            FPR
                          </th>
                        </tr>
                      </thead>

                      <tbody>
                        {modelMetrics.binary_models.map(
                          (model) => (
                            <tr
                              key={
                                model.model
                              }
                            >
                              <td>
                                <strong>
                                  {
                                    model.model
                                  }
                                </strong>
                              </td>

                              <td>
                                {formatPercent(
                                  model.accuracy,
                                )}
                              </td>

                              <td>
                                {formatPercent(
                                  model.precision,
                                )}
                              </td>

                              <td>
                                {formatPercent(
                                  model.recall,
                                )}
                              </td>

                              <td>
                                {formatPercent(
                                  model.f1,
                                )}
                              </td>

                              <td>
                                {formatPercent(
                                  model.false_positive_rate,
                                )}
                              </td>
                            </tr>
                          ),
                        )}
                      </tbody>
                    </table>
                  </div>
                </section>

                <section className="panel model-panel">
                  <div className="panel-heading">
                    <span className="eyebrow">
                      MULTICLASS EVALUATION
                    </span>

                    <h3>
                      Validation summary
                    </h3>
                  </div>

                  <div className="classification">
                    <div>
                      <span>
                        Accuracy
                      </span>

                      <strong>
                        {formatPercent(
                          modelMetrics.multiclass_accuracy,
                        )}
                      </strong>
                    </div>

                    <div>
                      <span>
                        Weighted precision
                      </span>

                      <strong>
                        {formatPercent(
                          modelMetrics.multiclass_weighted_precision,
                        )}
                      </strong>
                    </div>

                    <div>
                      <span>
                        Weighted recall
                      </span>

                      <strong>
                        {formatPercent(
                          modelMetrics.multiclass_weighted_recall,
                        )}
                      </strong>
                    </div>

                    <div>
                      <span>
                        Weighted F1
                      </span>

                      <strong>
                        {formatPercent(
                          modelMetrics.multiclass_weighted_f1,
                        )}
                      </strong>
                    </div>

                    <div>
                      <span>
                        Macro F1
                      </span>

                      <strong>
                        {formatPercent(
                          modelMetrics.multiclass_macro_f1,
                        )}
                      </strong>
                    </div>

                    <div>
                      <span>
                        Training rows
                      </span>

                      <strong>
                        {modelMetrics.training_rows.toLocaleString()}
                      </strong>
                    </div>
                  </div>
                </section>
              </>
            )}

          {modelFeatures && (
            <section className="panel model-panel">
              <div className="panel-heading">
                <span className="eyebrow">
                  FEATURE IMPORTANCE
                </span>

                <h3>
                  Top model features
                </h3>

                <p>
                  XGBoost feature
                  importance from the
                  trained binary model.
                </p>
              </div>

              <div className="feature-list">
                {topFeatures.map(
                  (feature) => {
                    const width =
                      (feature.importance /
                        maxFeatureImportance) *
                      100

                    return (
                      <div
                        className="feature-row"
                        key={feature.name}
                      >
                        <div className="feature-heading">
                          <span>
                            #{feature.rank}
                          </span>

                          <strong>
                            {formatFeatureName(
                              feature.name,
                            )}
                          </strong>

                          <small>
                            {formatMetric(
                              feature.importance,
                            )}
                          </small>
                        </div>

                        <div className="bar-track">
                          <div
                            className="bar-fill"
                            style={{
                              width: `${width}%`,
                            }}
                          />
                        </div>
                      </div>
                    )
                  },
                )}
              </div>
            </section>
          )}
        </>
      )}

      {activeView === 'system' && (
        <>
          <section className="metrics">
            <article className="metric-card">
              <div className="metric-label">
                API
              </div>

              <strong>
                {apiOnline
                  ? 'ONLINE'
                  : 'OFFLINE'}
              </strong>

              <span>
                FastAPI inference
                service
              </span>
            </article>

            <article className="metric-card">
              <div className="metric-label">
                WEBSOCKET
              </div>

              <strong>
                {websocketConnected
                  ? 'CONNECTED'
                  : 'DISCONNECTED'}
              </strong>

              <span>
                Real-time alert
                channel
              </span>
            </article>

            <article className="metric-card">
              <div className="metric-label">
                CAPTURE
              </div>

              <strong>
                {liveRunning
                  ? 'RUNNING'
                  : 'STOPPED'}
              </strong>

              <span>
                Live packet
                monitoring
              </span>
            </article>

            <article className="metric-card">
              <div className="metric-label">
                FLOW TIMEOUT
              </div>

              <strong>
                {liveStatus
                  ? `${liveStatus.flow_timeout}s`
                  : '—'}
              </strong>

              <span>
                Live flow
                aggregation
              </span>
            </article>
          </section>

          <section className="content-grid">
            <article className="panel">
              <div className="panel-heading">
                <span className="eyebrow">
                  LIVE CAPTURE
                </span>

                <h3>
                  Capture configuration
                </h3>
              </div>

              <div className="classification">
                <div>
                  <span>
                    Interface
                  </span>

                  <strong>
                    {liveStatus
                      ?.interface ||
                      'Not configured'}
                  </strong>
                </div>

                <div>
                  <span>
                    Interface configured
                  </span>

                  <strong>
                    {liveStatus?.interface_configured
                      ? 'YES'
                      : 'NO'}
                  </strong>
                </div>

                <div>
                  <span>
                    Flow timeout
                  </span>

                  <strong>
                    {liveStatus
                      ? `${liveStatus.flow_timeout}s`
                      : '—'}
                  </strong>
                </div>

                <div>
                  <span>
                    Current state
                  </span>

                  <strong>
                    {liveRunning
                      ? 'CAPTURING'
                      : 'STOPPED'}
                  </strong>
                </div>
              </div>

              {liveStatus?.last_error && (
                <p className="error">
                  {liveStatus.last_error}
                </p>
              )}
            </article>

            <article className="panel">
              <div className="panel-heading">
                <span className="eyebrow">
                  DATA FLOW
                </span>

                <h3>
                  System architecture
                </h3>
              </div>

              <div className="pipeline">
                <div className="pipeline-step">
                  <span>01</span>{' '}
                  UNSW-NB15 / live
                  traffic
                </div>

                <div className="pipeline-step">
                  <span>02</span>{' '}
                  Feature extraction
                </div>

                <div className="pipeline-step">
                  <span>03</span>{' '}
                  Preprocessor
                  artifact
                </div>

                <div className="pipeline-step">
                  <span>04</span>{' '}
                  Binary XGBoost
                </div>

                <div className="pipeline-step">
                  <span>05</span>{' '}
                  Multiclass XGBoost
                </div>

                <div className="pipeline-step">
                  <span>06</span>{' '}
                  SQLAlchemy
                  persistence
                </div>

                <div className="pipeline-step">
                  <span>07</span>{' '}
                  React +
                  WebSocket
                </div>
              </div>
            </article>
          </section>
        </>
      )}

      {error && (
        <p className="error">{error}</p>
      )}

      {selectedEvent && (
        <section className="panel detail-panel">
          <div className="panel-heading">
            <span className="eyebrow">
              DETECTION DETAIL
            </span>

            <h3>
              Event #{selectedEvent.id}
            </h3>

            <p>
              Full stored
              classification record.
            </p>
          </div>

          <div className="detail-grid">
            <div>
              <span>
                Timestamp
              </span>

              <strong>
                {new Date(
                  selectedEvent.timestamp,
                ).toLocaleString()}
              </strong>
            </div>

            <div>
              <span>
                Mode
              </span>

              <strong>
                {selectedEvent.mode}
              </strong>
            </div>

            <div>
              <span>
                Source IP
              </span>

              <strong>
                {selectedEvent.source_ip ??
                  'Not available'}
              </strong>
            </div>

            <div>
              <span>
                Destination IP
              </span>

              <strong>
                {selectedEvent.destination_ip ??
                  'Not available'}
              </strong>
            </div>

            <div>
              <span>
                Protocol
              </span>

              <strong>
                {selectedEvent.protocol ??
                  'Not available'}
              </strong>
            </div>

            <div>
              <span>
                Binary prediction
              </span>

              <strong>
                {selectedEvent.binary_label}
              </strong>
            </div>

            <div>
              <span>
                Binary confidence
              </span>

              <strong>
                {formatPercent(
                  selectedEvent.binary_confidence,
                )}
              </strong>
            </div>

            <div>
              <span>
                Attack category
              </span>

              <strong>
                {
                  selectedEvent.attack_category
                }
              </strong>
            </div>

            <div>
              <span>
                Multiclass confidence
              </span>

              <strong>
                {formatPercent(
                  selectedEvent.multiclass_confidence,
                )}
              </strong>
            </div>

            <div>
              <span>
                Severity
              </span>

              <strong>
                {selectedEvent.severity}
              </strong>
            </div>

            <div>
              <span>
                Model version
              </span>

              <strong>
                {
                  selectedEvent.model_version
                }
              </strong>
            </div>
          </div>

          <button
            className="detail-close"
            onClick={() =>
              setSelectedEvent(null)
            }
          >
            Close detail
          </button>
        </section>
      )}
    </main>
  )
}

export default App