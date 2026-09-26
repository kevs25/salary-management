import createClient from 'openapi-fetch'
import type { components, paths } from './schema'

/** Typed client generated from the backend's OpenAPI schema (npm run api:types). */
export const api = createClient<paths>({ baseUrl: '' })

export type Schemas = components['schemas']

/** One error shape for the UI, whatever the backend sent. */
export class ApiError extends Error {
  readonly status: number
  readonly code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

interface DomainErrorBody {
  error: { code: string; message: string }
}
interface ValidationErrorBody {
  detail: { loc: (string | number)[]; msg: string }[]
}

/**
 * The backend answers with either a domain error ({error: {code, message}}) from
 * the service layer, or FastAPI's request-validation error ({detail: [...]}).
 */
export function toApiError(status: number, body: unknown): ApiError {
  if (body && typeof body === 'object') {
    if ('error' in body) {
      const { code, message } = (body as DomainErrorBody).error
      return new ApiError(status, code, message)
    }
    if ('detail' in body && Array.isArray((body as ValidationErrorBody).detail)) {
      const message = (body as ValidationErrorBody).detail
        .map((d) => `${d.loc.filter((part) => part !== 'body').join('.')}: ${d.msg}`)
        .join('; ')
      return new ApiError(status, 'validation_error', message)
    }
  }
  return new ApiError(status, 'unknown_error', `Request failed (${status})`)
}

/** Turn an openapi-fetch result into data or a thrown ApiError, for TanStack Query. */
export async function unwrap<T>(
  request: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  const { data, error, response } = await request
  if (error !== undefined || !response.ok) {
    throw toApiError(response.status, error)
  }
  return data as T
}
