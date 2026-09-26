import { Anchor, Group, Pagination, Paper, Stack, Table, Text, Title } from '@mantine/core'
import { Link } from 'react-router-dom'
import { type ComplianceQuery, useBandCompliance, usePaySummary } from '../api/analytics'
import { PositionBadge } from '../components/Badges'
import { DimensionFilters } from '../components/DimensionFilters'
import { QueryStatus } from '../components/QueryStatus'
import { intParam, useUrlParams } from '../hooks/useUrlParams'
import { formatCount, formatMoney, formatPct, formatRatio } from '../lib/format'

const PAGE_SIZE = 50

/** Everyone paid outside their band, most severe first, each one link from a fix. */
export function CompliancePage() {
  const [params, update] = useUrlParams()
  const filters = {
    department_id: intParam(params.department_id),
    role_id: intParam(params.role_id),
    level_id: intParam(params.level_id),
    country_id: intParam(params.country_id),
  }
  const query: ComplianceQuery = {
    ...filters,
    page: intParam(params.page) ?? 1,
    page_size: PAGE_SIZE,
  }
  const { data, isPending, error, isPlaceholderData } = useBandCompliance(query)
  const summary = usePaySummary(filters).data?.band_compliance

  return (
    <Stack>
      <div>
        <Title order={2}>Band compliance</Title>
        <Text c="dimmed" size="sm">
          Base pay compared with the band that applies to each employee today. Sorted by how far
          outside the band they are.
          {summary &&
            ` ${formatCount(summary.below)} below minimum, ${formatCount(summary.above)} above maximum, ${formatPct(summary.compliance_pct)} within band.`}
        </Text>
      </div>

      <Paper withBorder p="md">
        <DimensionFilters values={filters} onChange={update} />
      </Paper>

      <QueryStatus isPending={isPending} error={error}>
        <Paper withBorder style={{ opacity: isPlaceholderData ? 0.6 : 1 }}>
          <Table.ScrollContainer minWidth={1000}>
            <Table
              striped
              highlightOnHover
              verticalSpacing="xs"
              style={{ fontVariantNumeric: 'tabular-nums' }}
            >
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Employee</Table.Th>
                  <Table.Th>Department · role</Table.Th>
                  <Table.Th>Level</Table.Th>
                  <Table.Th>Country</Table.Th>
                  <Table.Th ta="right">Base pay</Table.Th>
                  <Table.Th ta="right">Band (min – max)</Table.Th>
                  <Table.Th ta="right">Compa-ratio</Table.Th>
                  <Table.Th ta="right">Outside by</Table.Th>
                  <Table.Th>Position</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {(data?.items ?? []).map((e) => {
                  const { band } = e.assessment
                  return (
                    <Table.Tr key={e.employee_id}>
                      <Table.Td>
                        <Anchor component={Link} to={`/employees/${e.employee_id}`} fw={500}>
                          {e.full_name}
                        </Anchor>
                        <Text size="xs" c="dimmed">
                          {e.employee_code}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        {e.department} · {e.role}
                      </Table.Td>
                      <Table.Td>{e.level}</Table.Td>
                      <Table.Td>{e.country_code}</Table.Td>
                      <Table.Td ta="right">
                        {formatMoney(e.assessment.salary_in_band_currency, band.currency_code)}
                      </Table.Td>
                      <Table.Td ta="right">
                        {formatMoney(band.min_amount, band.currency_code)} –{' '}
                        {formatMoney(band.max_amount, band.currency_code)}
                      </Table.Td>
                      <Table.Td ta="right">{formatRatio(e.assessment.compa_ratio)}</Table.Td>
                      <Table.Td ta="right">
                        {formatMoney(e.assessment.gap_amount, band.currency_code)} (
                        {formatPct(e.assessment.gap_pct)})
                      </Table.Td>
                      <Table.Td>
                        <PositionBadge position={e.assessment.position} />
                      </Table.Td>
                    </Table.Tr>
                  )
                })}
                {data?.items.length === 0 && (
                  <Table.Tr>
                    <Table.Td colSpan={9}>
                      <Text c="dimmed" ta="center" py="md">
                        Everyone in this selection is paid within their band.
                      </Text>
                    </Table.Td>
                  </Table.Tr>
                )}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        </Paper>
        <Group justify="space-between">
          <Text size="sm" c="dimmed">
            {data ? `${formatCount(data.total)} employees` : ''}
          </Text>
          <Pagination
            total={data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1}
            value={query.page ?? 1}
            onChange={(page) => update({ page })}
          />
        </Group>
      </QueryStatus>
    </Stack>
  )
}
