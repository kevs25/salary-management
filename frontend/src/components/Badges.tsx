import { Badge } from '@mantine/core'
import type { Schemas } from '../api/client'
import { humanize } from '../lib/format'

type Status = Schemas['EmployeeDetail']['status']

const STATUS_COLOR: Record<Status, string> = {
  active: 'teal',
  on_leave: 'yellow',
  terminated: 'gray',
}

export function StatusBadge({ status }: { status: Status }) {
  return (
    <Badge color={STATUS_COLOR[status]} variant="dot">
      {humanize(status)}
    </Badge>
  )
}
