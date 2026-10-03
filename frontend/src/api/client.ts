import type { ApiErrorBody, JsonValue } from './types'

export const API_BASE = '/api'

/**
 * A failed request, carrying the server's finance-user message so the UI can show it verbatim.
 * status 0 means the server could not be reached at all.
 */
export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly messageForUser: string
  readonly detail: JsonValue

  constructor(status: number, code: string, messageForUser: string, detail: JsonValue = null) {
    super(messageForUser)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.messageForUser = messageForUser
    this.detail = detail
  }

  get isNotFound(): boolean {
    return this.status === 404
  }
}

const NETWORK_MESSAGE =
  "Can't reach the review server. Check that `finagent serve` is running, then retry."

function isErrorBody(value: unknown): value is ApiErrorBody {
  if (typeof value !== 'object' || value === null || !('error' in value)) return false
  const err = (value as { error: unknown }).error
  return typeof err === 'object' && err !== null && 'message_for_user' in err
}

function fallbackMessage(status: number): string {
  if (status === 404) return 'That page or record was not found.'
  if (status >= 500) return 'The server hit an error while loading this. Retry, and if it persists check the server log.'
  return 'The request could not be completed.'
}

async function toApiError(res: Response): Promise<ApiError> {
  let body: unknown = null
  try {
    body = await res.json()
  } catch {
    body = null
  }
  if (isErrorBody(body)) {
    const { code, message_for_user, detail } = body.error
    return new ApiError(res.status, code, message_for_user, detail ?? null)
  }
  return new ApiError(res.status, 'http_error', fallbackMessage(res.status))
}

async function send(path: string, init?: RequestInit): Promise<Response> {
  let res: Response
  try {
    res = await fetch(`${API_BASE}${path}`, init)
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') throw e
    throw new ApiError(0, 'network_error', NETWORK_MESSAGE)
  }
  if (!res.ok) throw await toApiError(res)
  return res
}

/** GET a JSON endpoint. `path` is relative to /api and must start with "/". */
export async function apiGet<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await send(path, { headers: { Accept: 'application/json' }, signal })
  return (await res.json()) as T
}

/** GET a text endpoint (e.g. the architecture markdown). */
export async function apiGetText(path: string, signal?: AbortSignal): Promise<string> {
  const res = await send(path, { headers: { Accept: 'text/plain, text/markdown' }, signal })
  return res.text()
}

/** POST JSON and parse the JSON response. */
export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await send(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify(body),
  })
  return (await res.json()) as T
}

/** Normalise anything thrown into an ApiError for display. */
export function toDisplayError(error: unknown): ApiError {
  if (error instanceof ApiError) return error
  return new ApiError(-1, 'unexpected', 'Something went wrong in the page. Retry, or reload.')
}

/** Encode one URL path segment (JE ids and account codes are user data). */
export function seg(value: string): string {
  return encodeURIComponent(value)
}
