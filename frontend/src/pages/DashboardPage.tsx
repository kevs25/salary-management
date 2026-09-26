import { Group, Paper, Stack, Text, Title } from '@mantine/core'
import { type AnalyticsFilter, useBreakdown, usePaySummary } from '../api/analytics'
import { BreakdownSection } from '../components/analytics/BreakdownSection'
import { KpiTiles } from '../components/analytics/KpiTiles'
import { DimensionFilters } from '../components/DimensionFilters'
import { QueryStatus } from '../components/QueryStatus'
import { intParam, useUrlParams } from '../hooks/useUrlParams'
import { isDimension } from '../lib/labels'

export function DashboardPage() {
  const [params, update] = useUrlParams()
  // One filter row scopes every tile, chart and table on the page.
  const filters: AnalyticsFilter = {
    department_id: intParam(params.department_id),
    role_id: intParam(params.role_id),
    level_id: intParam(params.level_id),
    country_id: intParam(params.country_id),
  }
  const by = isDimension(params.by) ? params.by : 'department'

  const summary = usePaySummary(filters)
  const breakdown = useBreakdown({ ...filters, by })

  return (
    <Stack>
      <div>
        <Title order={2}>How ACME pays people</Title>
        <Text c="dimmed" size="sm">
          Current pay of everyone not terminated. USD figures use the committed FX snapshot.
        </Text>
      </div>
      <Paper withBorder p="md">
        <Group>
          <DimensionFilters values={filters} onChange={update} />
        </Group>
      </Paper>

      <QueryStatus isPending={summary.isPending} error={summary.error}>
        {summary.data && <KpiTiles summary={summary.data} />}
      </QueryStatus>
      <QueryStatus isPending={breakdown.isPending} error={breakdown.error}>
        {breakdown.data && (
          <BreakdownSection
            breakdown={breakdown.data}
            onDimensionChange={(value) => update({ by: value, page: undefined })}
            stale={breakdown.isPlaceholderData}
          />
        )}
      </QueryStatus>
    </Stack>
  )
}
