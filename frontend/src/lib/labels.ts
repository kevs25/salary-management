import type { Schemas } from '../api/client'

type Scope = Schemas['BandOut']['scope']

export const SCOPE_LABEL: Record<Scope, string> = {
  'department+role+level+country': 'Role + country',
  'department+level+country': 'All roles, one country',
  'department+level': 'Department-wide (USD)',
}
