/**
 * Display formatting. Money arrives from the API as decimal strings and is never
 * parsed into a float for arithmetic; Intl.NumberFormat formats the string itself
 * (ES2023 accepts numeric strings and keeps their exact value).
 */

type Numeric = `${number}` | string

const moneyFormatters = new Map<string, Intl.NumberFormat>()

export function formatMoney(amount: Numeric | null | undefined, currency: string): string {
  if (amount == null) return '—'
  let formatter = moneyFormatters.get(currency)
  if (!formatter) {
    formatter = new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
      maximumFractionDigits: 0,
    })
    moneyFormatters.set(currency, formatter)
  }
  return formatter.format(amount as Intl.StringNumericLiteral)
}

export const formatUsd = (amount: Numeric | null | undefined) => formatMoney(amount, 'USD')

const compactUsd = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  notation: 'compact',
  maximumFractionDigits: 1,
})

/** $740.1M: for KPI tiles where the full figure is noise. */
export function formatUsdCompact(amount: Numeric | null | undefined): string {
  return amount == null ? '—' : compactUsd.format(amount as Intl.StringNumericLiteral)
}

export function formatRatio(ratio: Numeric | null | undefined): string {
  return ratio == null ? '—' : Number(ratio).toFixed(2)
}

export function formatPct(pct: Numeric | null | undefined): string {
  return pct == null ? '—' : `${Number(pct).toFixed(1)}%`
}

const count = new Intl.NumberFormat('en-US')
export const formatCount = (n: number) => count.format(n)

const dates = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  timeZone: 'UTC',
})

/** API dates are calendar dates (YYYY-MM-DD); format them without a timezone shift. */
export function formatDate(isoDate: string | null | undefined): string {
  return isoDate ? dates.format(new Date(`${isoDate.slice(0, 10)}T00:00:00Z`)) : '—'
}

export function humanize(value: string): string {
  const text = value.replaceAll('_', ' ')
  return text.charAt(0).toUpperCase() + text.slice(1)
}

/** Validates a money input the same way the API does: up to 2 decimal places. */
export const MONEY_PATTERN = /^\d{1,12}(\.\d{1,2})?$/
