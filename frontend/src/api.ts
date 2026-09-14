export type PredictionResponse = {
  prediction: number
  label: string
  confidence: number
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

export async function predictBinary(
  features: Record<string, unknown>,
): Promise<PredictionResponse> {
  const response = await fetch(`${API_BASE_URL}/predict/binary`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ features }),
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(`Binary prediction failed: ${detail}`)
  }

  return response.json()
}

export async function predictMulticlass(
  features: Record<string, unknown>,
): Promise<PredictionResponse> {
  const response = await fetch(`${API_BASE_URL}/predict/multiclass`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ features }),
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(`Multiclass prediction failed: ${detail}`)
  }

  return response.json()
}