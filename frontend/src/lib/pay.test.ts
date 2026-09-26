import { describe, expect, it } from 'vitest'
import { bandAmountsError, markerPosition } from './pay'

describe('markerPosition', () => {
  // Track spans min - 20% of width .. max + 20%: 80 -> 120 shows 72 -> 128.
  it('places min, mid and max proportionally inside the padded track', () => {
    expect(markerPosition(80, 80, 120)).toBeCloseTo(14.29, 1)
    expect(markerPosition(100, 80, 120)).toBeCloseTo(50, 5)
    expect(markerPosition(120, 80, 120)).toBeCloseTo(85.71, 1)
  })

  it('pins far out-of-band pay to the edges', () => {
    expect(markerPosition(10, 80, 120)).toBe(0)
    expect(markerPosition(500, 80, 120)).toBe(100)
  })

  it('handles a flat band', () => {
    expect(markerPosition(100, 100, 100)).toBeCloseTo(50, 5)
  })
})

describe('bandAmountsError', () => {
  it('accepts ordered and flat bands', () => {
    expect(bandAmountsError('80000', '100000', '120000')).toBeNull()
    expect(bandAmountsError('100', '100', '100')).toBeNull()
  })

  it('rejects min above mid or mid above max', () => {
    expect(bandAmountsError('100001', '100000', '120000')).toMatch(/min ≤ mid ≤ max/)
    expect(bandAmountsError('80000', '120000.01', '120000')).toMatch(/min ≤ mid ≤ max/)
  })

  it('leaves malformed amounts to the per-field checks', () => {
    expect(bandAmountsError('abc', '100', '1')).toBeNull()
  })
})
