import { describe, expect, it } from 'vitest'
import { formatDate, formatMoney, formatPct, formatRatio, humanize, MONEY_PATTERN } from './format'

describe('formatMoney', () => {
  it('formats decimal strings in the given currency', () => {
    expect(formatMoney('1500000.00', 'INR')).toBe('₹1,500,000')
    expect(formatMoney('85000.50', 'USD')).toBe('$85,001')
    expect(formatMoney('1200', 'EUR')).toBe('€1,200')
  })

  it('keeps precision past what a float can hold', () => {
    // 2^53 + 1 is not representable as a double; the string path keeps it exact.
    expect(formatMoney('9007199254740993', 'USD')).toBe('$9,007,199,254,740,993')
  })

  it('shows a dash for missing values', () => {
    expect(formatMoney(null, 'USD')).toBe('—')
  })
})

describe('formatDate', () => {
  it('formats calendar dates without shifting the day across time zones', () => {
    expect(formatDate('2026-04-01')).toBe('1 Apr 2026')
    expect(formatDate('2026-09-26T10:00:00')).toBe('26 Sept 2026')
  })
})

describe('small formatters', () => {
  it('formats ratios, percents and enum labels', () => {
    expect(formatRatio('1.0015')).toBe('1.00')
    expect(formatPct('95.99')).toBe('96.0%')
    expect(formatPct(null)).toBe('—')
    expect(humanize('market_adjustment')).toBe('Market adjustment')
  })
})

describe('MONEY_PATTERN', () => {
  it.each(['0', '85000', '85000.5', '85000.50', '999999999999.99'])('accepts %s', (value) => {
    expect(MONEY_PATTERN.test(value)).toBe(true)
  })

  it.each(['', '-1', '1.234', '1,000', 'abc', '1e5', '1234567890123'])('rejects %s', (value) => {
    expect(MONEY_PATTERN.test(value)).toBe(false)
  })
})
