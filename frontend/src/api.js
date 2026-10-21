const baseUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

async function request(path, options = {}) {
  let response
  try {
    response = await fetch(`${baseUrl}${path}`, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    })
  } catch {
    throw new Error('The local application server is not reachable. Please try again.')
  }

  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(payload.detail || 'The request could not be completed.')
  }
  return payload
}

export const api = {
  info: () => request('/api/info'),
  history: () => request('/api/history'),
  startSession: (practiceId) => request('/api/sessions', {
    method: 'POST',
    body: JSON.stringify({ practice_id: practiceId }),
  }),
  updateSession: (id, session) => request(`/api/sessions/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: JSON.stringify(session),
  }),
  sendMessage: (message, conversationId) => request('/api/chat', {
    method: 'POST',
    body: JSON.stringify({ message, conversation_id: conversationId || null }),
  }),
  clearHistory: () => request('/api/history', { method: 'DELETE' }),
}
