import axios from 'axios'

const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL,
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
})

export async function analyzeCase(payload) {
  const { data } = await api.post('/analyze', payload)
  return data
}

/**
 * Stream `/analyze/stream`. Calls handlers as SSE events arrive.
 *
 * @param {object} payload
 * @param {{
 *   onRetrieval?: (info: { candidates:number, language:string, top_score:number }) => void,
 *   onDelta?: (chunk: string) => void,
 *   onComplete: (response: object) => void,
 *   onError?: (msg: string) => void,
 *   signal?: AbortSignal,
 * }} handlers
 */
export async function analyzeCaseStream(payload, handlers) {
  const res = await fetch(`${baseURL}/analyze/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify(payload),
    signal: handlers.signal,
  })

  if (!res.ok || !res.body) {
    let msg = `HTTP ${res.status}`
    try {
      const j = await res.json()
      msg = j.detail || msg
    } catch {}
    handlers.onError?.(msg)
    return
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buf = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })

    // SSE events are separated by a blank line ("\n\n").
    let sep
    while ((sep = buf.indexOf('\n\n')) !== -1) {
      const raw = buf.slice(0, sep)
      buf = buf.slice(sep + 2)
      const ev = parseSseFrame(raw)
      if (!ev) continue
      switch (ev.event) {
        case 'retrieval':
          handlers.onRetrieval?.(safeJson(ev.data))
          break
        case 'delta': {
          const obj = safeJson(ev.data)
          if (obj?.text) handlers.onDelta?.(obj.text)
          break
        }
        case 'complete':
          handlers.onComplete(safeJson(ev.data))
          return
        case 'error':
          handlers.onError?.(safeJson(ev.data)?.message || 'stream error')
          return
      }
    }
  }
}

function parseSseFrame(raw) {
  let event = 'message'
  const dataLines = []
  for (const line of raw.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim()
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
  }
  if (!dataLines.length) return null
  return { event, data: dataLines.join('\n') }
}

function safeJson(s) {
  try {
    return JSON.parse(s)
  } catch {
    return null
  }
}
