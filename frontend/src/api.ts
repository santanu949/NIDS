export type PredictionResponse = {
  prediction: number
  label: string
  confidence: number
  attack_category: string
  multiclass_confidence: number
}

export type PredictionEvent = {
  id: number
  timestamp: string
  mode: string
  binary_prediction: number
  binary_label: string
  binary_confidence: number
  attack_category: string
  multiclass_confidence: number
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

export type LiveStatusResponse = {
  running: boolean
  interface_configured: boolean
  interface: string
  flow_timeout: number
  last_error: string | null
}

const API_BASE_URL = 'http://127.0.0.1:8000'

export async function checkHealth(): Promise<{
  status: string
  service: string
}> {
  const response = await fetch(`${API_BASE_URL}/health`)

  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`)
  }

  return response.json()
}

export async function predict(
  features: Record<string, unknown>,
): Promise<PredictionResponse> {
  const response = await fetch(`${API_BASE_URL}/predict`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ features }),
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(`Prediction failed: ${detail}`)
  }

  return response.json()
}

export async function getEvents(): Promise<PredictionEvent[]> {
  const response = await fetch(`${API_BASE_URL}/events`)

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(`Event history failed: ${detail}`)
  }

  return response.json()
}

export async function getAnalytics(): Promise<AnalyticsResponse> {
  const response = await fetch(`${API_BASE_URL}/analytics`)

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(`Analytics failed: ${detail}`)
  }

  return response.json()
}

export async function getLiveStatus(): Promise<LiveStatusResponse> {
  const response = await fetch(`${API_BASE_URL}/live/status`)

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(`Live status failed: ${detail}`)
  }

  return response.json()
}

export async function startLiveCapture(): Promise<LiveStatusResponse> {
  const response = await fetch(`${API_BASE_URL}/live/start`, {
    method: 'POST',
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(`Live capture start failed: ${detail}`)
  }

  return response.json()
}

export async function stopLiveCapture(): Promise<LiveStatusResponse> {
  const response = await fetch(`${API_BASE_URL}/live/stop`, {
    method: 'POST',
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(`Live capture stop failed: ${detail}`)
  }

  return response.json()
}