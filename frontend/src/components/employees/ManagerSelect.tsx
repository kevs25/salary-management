import { Select } from '@mantine/core'
import { useDebouncedValue } from '@mantine/hooks'
import { useState } from 'react'
import { useEmployees } from '../../api/employees'

interface Props {
  value: string | null
  onChange: (value: string | null) => void
  /** Shown before any search, so the current manager has a label. */
  current?: { id: number; full_name: string; employee_code: string } | null
  excludeId?: number
}

/** Pick a manager by searching the employee list server-side (10k rows, never all loaded). */
export function ManagerSelect({ value, onChange, current, excludeId }: Props) {
  const [search, setSearch] = useState('')
  const [debounced] = useDebouncedValue(search, 250)
  const { data } = useEmployees({ q: debounced || undefined, page_size: 10, status: 'active' })

  const options = new Map<string, string>()
  if (current) options.set(String(current.id), `${current.full_name} (${current.employee_code})`)
  for (const e of data?.items ?? []) {
    if (e.id !== excludeId) {
      options.set(String(e.id), `${e.first_name} ${e.last_name} (${e.employee_code}, ${e.level})`)
    }
  }

  return (
    <Select
      label="Manager"
      placeholder="Search by name or code"
      searchable
      clearable
      searchValue={search}
      onSearchChange={setSearch}
      filter={({ options }) => options} // the server already filtered
      data={[...options].map(([optionValue, label]) => ({ value: optionValue, label }))}
      value={value}
      onChange={onChange}
      nothingFoundMessage="No active employee matches"
    />
  )
}
