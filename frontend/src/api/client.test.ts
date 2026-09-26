import { describe, expect, it } from 'vitest'
import { ApiError, toApiError, unwrap } from './client'

describe('toApiError', () => {
  it('reads domain errors from the service layer', () => {
    const error = toApiError(409, {
      error: { code: 'duplicate_employee', message: 'Employee code E00001 is already in use' },
    })
    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(409)
    expect(error.code).toBe('duplicate_employee')
    expect(error.message).toBe('Employee code E00001 is already in use')
  })

  it('flattens FastAPI validation errors into one message', () => {
    const error = toApiError(422, {
      detail: [
        { loc: ['body', 'base_amount'], msg: 'Input should be greater than 0' },
        { loc: ['query', 'page'], msg: 'Input should be greater than or equal to 1' },
      ],
    })
    expect(error.code).toBe('validation_error')
    expect(error.message).toBe(
      'base_amount: Input should be greater than 0; query.page: Input should be greater than or equal to 1',
    )
  })

  it('falls back to the status for anything else', () => {
    expect(toApiError(502, 'Bad Gateway').message).toBe('Request failed (502)')
  })
})

describe('unwrap', () => {
  const response = (status: number) => new Response(null, { status })

  it('returns data on success', async () => {
    await expect(
      unwrap(Promise.resolve({ data: { id: 1 }, response: response(200) })),
    ).resolves.toEqual({
      id: 1,
    })
  })

  it('throws an ApiError on failure', async () => {
    const failed = unwrap(
      Promise.resolve({
        error: { error: { code: 'band_in_use', message: 'Band 3 is linked to salary records' } },
        response: response(409),
      }),
    )
    await expect(failed).rejects.toMatchObject({ status: 409, code: 'band_in_use' })
  })
})
