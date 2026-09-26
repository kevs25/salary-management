import {
  Alert,
  Button,
  Group,
  Modal,
  Pagination,
  Paper,
  Select,
  Stack,
  Text,
  Title,
} from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { useState } from 'react'
import { type BandQuery, useBands, useDeleteBand } from '../api/bands'
import type { Schemas } from '../api/client'
import { BandFormModal } from '../components/bands/BandFormModal'
import { BandTable } from '../components/bands/BandTable'
import { DimensionFilters } from '../components/DimensionFilters'
import { QueryStatus } from '../components/QueryStatus'
import { intParam, useUrlParams } from '../hooks/useUrlParams'
import { formatCount } from '../lib/format'
import { SCOPE_LABEL } from '../lib/labels'

type Band = Schemas['BandOut']
type Scope = Band['scope']
const PAGE_SIZE = 50

export function BandsPage() {
  const [params, update] = useUrlParams()
  const [editing, setEditing] = useState<Band | null>(null)
  const [creating, setCreating] = useState(false)
  const [deleting, setDeleting] = useState<Band | null>(null)
  const remove = useDeleteBand()

  const query: BandQuery = {
    department_id: intParam(params.department_id),
    role_id: intParam(params.role_id),
    level_id: intParam(params.level_id),
    country_id: intParam(params.country_id),
    scope: (params.scope as Scope) || undefined,
    page: intParam(params.page) ?? 1,
    page_size: PAGE_SIZE,
  }
  const { data, isPending, error, isFetching } = useBands(query)

  const confirmDelete = async () => {
    if (!deleting) return
    try {
      await remove.mutateAsync(deleting.id)
      notifications.show({ color: 'teal', message: 'Band deleted' })
      setDeleting(null)
    } catch {
      // shown in the dialog
    }
  }

  return (
    <Stack>
      <Group justify="space-between">
        <div>
          <Title order={2}>Salary bands</Title>
          <Text c="dimmed" size="sm">
            Min / mid / max annual base per cell. An employee is measured against the most specific
            band that exists: role + country, then all roles in the country, then department-wide.
          </Text>
        </div>
        <Button onClick={() => setCreating(true)}>New band</Button>
      </Group>

      <Paper withBorder p="md">
        <Group gap="sm" align="flex-end">
          <DimensionFilters values={query} onChange={update} />
          <Select
            aria-label="Scope"
            placeholder="Any scope"
            clearable
            data={(Object.keys(SCOPE_LABEL) as Scope[]).map((s) => ({
              value: s,
              label: SCOPE_LABEL[s],
            }))}
            value={query.scope ?? null}
            onChange={(scope) => update({ scope })}
            w={220}
          />
        </Group>
      </Paper>

      <QueryStatus isPending={isPending} error={error}>
        <Text size="sm" c="dimmed">
          {data ? `${formatCount(data.total)} bands` : ''}
        </Text>
        <Paper withBorder style={{ opacity: isFetching ? 0.6 : 1 }}>
          <BandTable
            rows={data?.items ?? []}
            onEdit={setEditing}
            onDelete={(band) => {
              remove.reset()
              setDeleting(band)
            }}
          />
        </Paper>
        <Group justify="center">
          <Pagination
            total={data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1}
            value={query.page ?? 1}
            onChange={(page) => update({ page })}
          />
        </Group>
      </QueryStatus>

      <BandFormModal opened={creating} onClose={() => setCreating(false)} />
      <BandFormModal opened={editing != null} onClose={() => setEditing(null)} band={editing} />
      <Modal opened={deleting != null} onClose={() => setDeleting(null)} title="Delete band?">
        <Stack>
          {remove.error && (
            <Alert color="red" title="Band kept">
              {remove.error.message}
            </Alert>
          )}
          <Text size="sm">
            Employees in this cell will fall back to the next broader band, if there is one.
          </Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setDeleting(null)}>
              Cancel
            </Button>
            <Button color="red" onClick={confirmDelete} loading={remove.isPending}>
              Delete
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  )
}
