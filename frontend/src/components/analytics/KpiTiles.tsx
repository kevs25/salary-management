import { Paper, SimpleGrid, Text } from '@mantine/core'
import type { Schemas } from '../../api/client'
import { formatCount, formatPct, formatRatio, formatUsd, formatUsdCompact } from '../../lib/format'

function Tile({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <Paper withBorder p="md">
      <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
        {label}
      </Text>
      <Text fz={28} fw={600} mt={4}>
        {value}
      </Text>
      <Text size="xs" c="dimmed">
        {hint}
      </Text>
    </Paper>
  )
}

/** The headline numbers: stat tiles, not charts (each is one value). */
export function KpiTiles({ summary }: { summary: Schemas['PaySummary'] }) {
  const { band_compliance: compliance } = summary
  const outside = compliance.below + compliance.above
  return (
    <SimpleGrid cols={{ base: 2, md: 3, xl: 6 }}>
      <Tile label="Headcount" value={formatCount(summary.headcount)} hint="Excludes terminated" />
      <Tile
        label="Payroll cost"
        value={formatUsdCompact(summary.payroll_cost_usd)}
        hint="Annual base + bonus, USD"
      />
      <Tile
        label="Median base"
        value={formatUsd(summary.base_salary_usd.median)}
        hint={`Average ${formatUsd(summary.base_salary_usd.avg)}`}
      />
      <Tile
        label="Within band"
        value={formatPct(compliance.compliance_pct)}
        hint={`${formatCount(outside)} outside · ${formatCount(compliance.no_band)} no band`}
      />
      <Tile
        label="Median compa-ratio"
        value={formatRatio(summary.compa_ratio_median)}
        hint="Base pay ÷ band mid"
      />
      <Tile
        label="FX snapshot"
        value={summary.fx_as_of ?? '—'}
        hint="Rates behind every USD figure"
      />
    </SimpleGrid>
  )
}
