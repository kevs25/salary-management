import { MantineProvider } from '@mantine/core'
import { render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'
import type { Schemas } from '../../api/client'
import { PayAssessmentCard } from './PayAssessmentCard'

const wrap = (ui: ReactNode) => render(<MantineProvider>{ui}</MantineProvider>)

describe('PayAssessmentCard', () => {
  const assessment: Schemas['PayAssessment'] = {
    band: {
      id: 9,
      scope: 'department+role+level+country',
      currency_code: 'INR',
      min_amount: '1600000.00',
      mid_amount: '2000000.00',
      max_amount: '2400000.00',
    },
    salary_in_band_currency: '1440000.00',
    compa_ratio: '0.7200',
    position: 'below',
    gap_amount: '160000.00',
    gap_pct: '10.00',
  }

  it('shows position, compa-ratio and the gap in the band currency', () => {
    wrap(<PayAssessmentCard assessment={assessment} />)

    expect(screen.getByText('Below band')).toBeInTheDocument()
    expect(screen.getByText('0.72')).toBeInTheDocument()
    expect(screen.getByText('₹160,000 (10.0%)')).toBeInTheDocument()
    expect(screen.getByText('Min ₹1,600,000')).toBeInTheDocument()
    expect(screen.getByText('Role + country')).toBeInTheDocument()
  })

  it('explains when no band covers the employee', () => {
    wrap(<PayAssessmentCard assessment={null} />)

    expect(screen.getByText(/No salary band covers/)).toBeInTheDocument()
  })
})
