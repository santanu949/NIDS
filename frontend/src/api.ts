export type PredictionResponse = {
  prediction: number
  label: string
  confidence: number
  attack_category: string
  multiclass_confidence: number
  severity: string
  model_version: string
}

export type PredictionEvent = {
  id: number
  timestamp: string
  mode: string
  source_ip: string | null
  destination_ip: string | null
  protocol: string | null
  binary_prediction: number
  binary_label: string
  binary_confidence: number
  attack_category: string
  multiclass_confidence: number
  severity: string
  model_version: string
}

export type AnalyticsResponse = {
  total_events: number
  normal_events: number
  attack_events: number
  attack_rate: number
  average_binary_confidence: number
  average_multiclass_confidence: number
  attack_categories: Record<string, number>
}

export type DashboardSummaryResponse = {
  total_events: number
  malicious_events: number
  normal_events: number
  threat_rate: number
  high_severity_events: number
  live_capture_running: boolean
  recent_events: PredictionEvent[]
}

export type AttackCategoryMetric = {
  category: string
  count: number
}

export type ModelMetric = {
  model: string
  accuracy: number
  precision: number
  recall: number
  f1: number
  false_positive_rate: number
}

export type ModelMetricsResponse = {
  dataset: string
  primary_model: string
  model_selection_metric: string
  official_test_set_used: boolean
  training_rows: number
  validation_rows: number
  transformed_feature_count: number
  binary_models: ModelMetric[]
  multiclass_accuracy: number
  multiclass_weighted_precision: number
  multiclass_weighted_recall: number
  multiclass_weighted_f1: number
  multiclass_macro_f1: number
}

export type ModelFeature = {
  name: string
  importance: number
  rank: number
}

export type ModelFeaturesResponse = {
  model: string
  feature_count: number
  features: ModelFeature[]
}

export type DetectionListResponse = {
  items: PredictionEvent[]
  total: number
  limit: number
  offset: number
}

export type LiveStatusResponse = {
  running: boolean
  interface_configured: boolean
  interface: string
  flow_timeout: number
  last_error: string | null
}

export type WebSocketAlert = {
  event: string
  detection: PredictionEvent
}

const API_BASE_URL = 'http://127.0.0.1:8000'
const WS_BASE_URL = 'ws://127.0.0.1:8000'

async function getErrorDetail(
  response: Response,
): Promise<string> {
  try {
    const body = await response.json()

    if (typeof body?.detail === 'string') {
      return body.detail
    }

    return JSON.stringify(body)
  } catch {
    return await response.text()
  }
}

export async function checkHealth(): Promise<{
  status: string
  service: string
}> {
  const response = await fetch(`${API_BASE_URL}/health`)

  if (!response.ok) {
    throw new Error(
      `Health check failed: ${response.status}`,
    )
  }

  return response.json()
}

export async function getDashboardSummary(): Promise<DashboardSummaryResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/dashboard/summary`,
  )

  if (!response.ok) {
    const detail = await getErrorDetail(response)

    throw new Error(
      `Dashboard summary failed: ${detail}`,
    )
  }

  return response.json()
}

export async function predict(
  features: Record<string, unknown>,
  mode: 'dataset' | 'live' = 'dataset',
): Promise<PredictionResponse> {
  const response = await fetch(`${API_BASE_URL}/predict`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      features,
      mode,
    }),
  })

  if (!response.ok) {
    const detail = await getErrorDetail(response)

    throw new Error(
      `Prediction failed: ${detail}`,
    )
  }

  return response.json()
}

export async function getEvents(): Promise<PredictionEvent[]> {
  const response = await fetch(`${API_BASE_URL}/events`)

  if (!response.ok) {
    const detail = await getErrorDetail(response)

    throw new Error(
      `Event history failed: ${detail}`,
    )
  }

  return response.json()
}

export async function getDetections(options?: {
  limit?: number
  offset?: number
  category?: string
  severity?: string
  protocol?: string
  mode?: string
  maliciousOnly?: boolean
}): Promise<DetectionListResponse> {
  const params = new URLSearchParams()

  if (options?.limit !== undefined) {
    params.set('limit', String(options.limit))
  }

  if (options?.offset !== undefined) {
    params.set('offset', String(options.offset))
  }

  if (
    options?.category &&
    options.category !== 'all'
  ) {
    params.set('category', options.category)
  }

  if (
    options?.severity &&
    options.severity !== 'all'
  ) {
    params.set('severity', options.severity)
  }

  if (
    options?.protocol &&
    options.protocol !== 'all'
  ) {
    params.set('protocol', options.protocol)
  }

  if (
    options?.mode &&
    options.mode !== 'all'
  ) {
    params.set('mode', options.mode)
  }

  if (options?.maliciousOnly !== undefined) {
    params.set(
      'malicious_only',
      String(options.maliciousOnly),
    )
  }

  const query = params.toString()

  const response = await fetch(
    `${API_BASE_URL}/api/detections${
      query ? `?${query}` : ''
    }`,
  )

  if (!response.ok) {
    const detail = await getErrorDetail(response)

    throw new Error(
      `Detection query failed: ${detail}`,
    )
  }

  return response.json()
}

export async function getDetection(
  id: number,
): Promise<PredictionEvent> {
  const response = await fetch(
    `${API_BASE_URL}/api/detections/${id}`,
  )

  if (!response.ok) {
    const detail = await getErrorDetail(response)

    throw new Error(
      `Detection lookup failed: ${detail}`,
    )
  }

  return response.json()
}

export async function getAnalytics(): Promise<AnalyticsResponse> {
  const response = await fetch(
    `${API_BASE_URL}/analytics`,
  )

  if (!response.ok) {
    const detail = await getErrorDetail(response)

    throw new Error(
      `Analytics failed: ${detail}`,
    )
  }

  return response.json()
}

export async function getAttackAnalytics(): Promise<AttackCategoryMetric[]> {
  const response = await fetch(
    `${API_BASE_URL}/api/analytics/attacks`,
  )

  if (!response.ok) {
    const detail = await getErrorDetail(response)

    throw new Error(
      `Attack analytics failed: ${detail}`,
    )
  }

  return response.json()
}

export async function getModelMetrics(): Promise<ModelMetricsResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/model/metrics`,
  )

  if (!response.ok) {
    const detail = await getErrorDetail(response)

    throw new Error(
      `Model metrics failed: ${detail}`,
    )
  }

  return response.json()
}

export async function getModelFeatures(): Promise<ModelFeaturesResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/model/features`,
  )

  if (!response.ok) {
    const detail = await getErrorDetail(response)

    throw new Error(
      `Model features failed: ${detail}`,
    )
  }

  return response.json()
}

export function getDetectionsExportUrl(): string {
  return `${API_BASE_URL}/api/detections/export.csv`
}

export async function getLiveStatus(): Promise<LiveStatusResponse> {
  const response = await fetch(
    `${API_BASE_URL}/live/status`,
  )

  if (!response.ok) {
    const detail = await getErrorDetail(response)

    throw new Error(
      `Live status failed: ${detail}`,
    )
  }

  return response.json()
}

export async function startLiveCapture(): Promise<LiveStatusResponse> {
  const response = await fetch(
    `${API_BASE_URL}/live/start`,
    {
      method: 'POST',
    },
  )

  if (!response.ok) {
    const detail = await getErrorDetail(response)

    throw new Error(
      `Live capture start failed: ${detail}`,
    )
  }

  return response.json()
}

export async function stopLiveCapture(): Promise<LiveStatusResponse> {
  const response = await fetch(
    `${API_BASE_URL}/live/stop`,
    {
      method: 'POST',
    },
  )

  if (!response.ok) {
    const detail = await getErrorDetail(response)

    throw new Error(
      `Live capture stop failed: ${detail}`,
    )
  }

  return response.json()
}

export function connectToAlerts(
  onAlert: (alert: WebSocketAlert) => void,
  onStatusChange?: (connected: boolean) => void,
): WebSocket {
  const websocket = new WebSocket(
    `${WS_BASE_URL}/ws/alerts`,
  )

  websocket.onopen = () => {
    onStatusChange?.(true)
  }

  websocket.onmessage = (message) => {
    try {
      const alert = JSON.parse(
        message.data,
      ) as WebSocketAlert

      onAlert(alert)
    } catch {
      // Ignore malformed WebSocket messages.
    }
  }

  websocket.onerror = () => {
    onStatusChange?.(false)
  }

  websocket.onclose = () => {
    onStatusChange?.(false)
  }

  return websocket
}