import { describe, expect, it } from 'vitest'
import { applyPatch, intParam } from './useUrlParams'

const params = (query: string) => new URLSearchParams(query)

describe('applyPatch', () => {
  it('sets values and drops empty ones', () => {
    const next = applyPatch(params('q=rao&country_id=2'), {
      q: '',
      department_id: 3,
      country_id: null,
    })
    expect(next.toString()).toBe('department_id=3')
  })

  it('goes back to page 1 when a filter or sort changes', () => {
    const next = applyPatch(params('page=4&q=rao'), { level_id: 2 })
    expect(next.get('page')).toBeNull()
    expect(next.get('q')).toBe('rao')
  })

  it('keeps other params when only the page changes', () => {
    const next = applyPatch(params('q=rao&sort=level'), { page: 3 })
    expect(next.toString()).toBe('q=rao&sort=level&page=3')
  })

  it('does not mutate the current params', () => {
    const current = params('q=rao')
    applyPatch(current, { q: 'lee' })
    expect(current.get('q')).toBe('rao')
  })
})

describe('intParam', () => {
  it('parses whole numbers only', () => {
    expect(intParam('42')).toBe(42)
    expect(intParam(undefined)).toBeUndefined()
    expect(intParam('abc')).toBeUndefined()
    expect(intParam('-1')).toBeUndefined()
    expect(intParam('1.5')).toBeUndefined()
  })
})
