import { Alert, Button, Group, Modal, Select, SimpleGrid, Stack, TextInput } from '@mantine/core'
import { useForm } from '@mantine/form'
import { notifications } from '@mantine/notifications'
import type { Schemas } from '../../api/client'
import { useCreateEmployee, useUpdateEmployee } from '../../api/employees'
import { useReferenceData } from '../../api/reference'
import { humanize, MONEY_PATTERN } from '../../lib/format'
import {
  blankEmployee,
  changedFields,
  type EmployeeFormValues,
  fromEmployee,
  toCreateBody,
} from './employeeForm'
import { ManagerSelect } from './ManagerSelect'

type Employee = Schemas['EmployeeDetail']

interface Props {
  opened: boolean
  onClose: () => void
  /** Edit this employee; create a new one when absent. */
  employee?: Employee
  onSaved?: (employee: Employee) => void
}

export function EmployeeFormModal({ opened, onClose, employee, onSaved }: Props) {
  const title = employee ? `Edit ${employee.first_name} ${employee.last_name}` : 'New employee'
  return (
    <Modal opened={opened} onClose={onClose} title={title} size="lg">
      {/* Mounted only while open, so every opening starts from fresh form state. */}
      <EmployeeForm employee={employee} onClose={onClose} onSaved={onSaved} />
    </Modal>
  )
}

const required = (label: string) => (value: string | null) =>
  value ? null : `${label} is required`

function EmployeeForm({ employee, onClose, onSaved }: Omit<Props, 'opened'>) {
  const editing = employee != null
  const { data: reference } = useReferenceData()
  const create = useCreateEmployee()
  const update = useUpdateEmployee(employee?.id ?? 0)
  const mutation = editing ? update : create

  const form = useForm<EmployeeFormValues>({
    initialValues: employee ? fromEmployee(employee) : blankEmployee,
    validate: {
      employee_code: (v) =>
        editing || /^[A-Za-z0-9-]{3,16}$/.test(v) ? null : '3-16 letters, digits or dashes',
      first_name: required('First name'),
      last_name: required('Last name'),
      email: (v) => (/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v) ? null : 'Enter a valid email'),
      department_id: required('Department'),
      role_id: required('Role'),
      level_id: required('Level'),
      country_id: required('Country'),
      hire_date: (v) => (editing || v ? null : 'Hire date is required'),
      base_amount: (v) =>
        editing || (MONEY_PATTERN.test(v) && Number(v) > 0)
          ? null
          : 'Enter an amount, e.g. 85000 or 85000.50',
      bonus_amount: (v) =>
        editing || MONEY_PATTERN.test(v) ? null : 'Enter an amount (0 for none)',
    },
  })

  const roles = (reference?.roles ?? []).filter(
    (r) =>
      form.values.department_id != null && r.department_id === Number(form.values.department_id),
  )
  const currency = reference?.countries.find(
    (c) => String(c.id) === form.values.country_id,
  )?.currency_code

  const submit = form.onSubmit(async (values) => {
    try {
      let saved: Employee
      if (editing) {
        const patch = changedFields(employee, values)
        if (Object.keys(patch).length === 0) return onClose()
        saved = await update.mutateAsync(patch)
      } else {
        saved = await create.mutateAsync(toCreateBody(values))
      }
      notifications.show({
        color: 'teal',
        message: `${saved.first_name} ${saved.last_name} ${editing ? 'updated' : 'created'}`,
      })
      onClose()
      onSaved?.(saved)
    } catch {
      // shown from mutation.error below
    }
  })

  const option = <T extends { id: number }>(items: T[] | undefined, label: (item: T) => string) =>
    (items ?? []).map((item) => ({ value: String(item.id), label: label(item) }))

  return (
    <form onSubmit={submit}>
      <Stack>
        {mutation.error && <Alert color="red">{mutation.error.message}</Alert>}
        <SimpleGrid cols={2}>
          <TextInput label="First name" {...form.getInputProps('first_name')} />
          <TextInput label="Last name" {...form.getInputProps('last_name')} />
          <TextInput label="Email" {...form.getInputProps('email')} />
          <TextInput
            label="Employee code"
            disabled={editing}
            {...form.getInputProps('employee_code')}
          />
          <Select
            label="Department"
            data={option(reference?.departments, (d) => d.name)}
            {...form.getInputProps('department_id')}
            onChange={(value) => {
              form.setFieldValue('department_id', value)
              form.setFieldValue('role_id', null) // roles belong to one department
            }}
          />
          <Select
            label="Role"
            data={option(roles, (r) => r.name)}
            disabled={form.values.department_id == null}
            {...form.getInputProps('role_id')}
          />
          <Select
            label="Level"
            data={option(reference?.levels, (l) => `${l.code} · ${l.name}`)}
            {...form.getInputProps('level_id')}
          />
          <Select
            label="Country"
            data={option(reference?.countries, (c) => `${c.name} (${c.currency_code})`)}
            disabled={editing}
            description={
              editing ? 'Moving country needs a salary revision in the new currency' : undefined
            }
            {...form.getInputProps('country_id')}
          />
          <ManagerSelect
            value={form.values.manager_id}
            onChange={(value) => form.setFieldValue('manager_id', value)}
            current={employee?.manager}
            excludeId={employee?.id}
          />
          {editing ? (
            <Select
              label="Status"
              data={(reference?.statuses ?? []).map((s) => ({ value: s, label: humanize(s) }))}
              allowDeselect={false}
              {...form.getInputProps('status')}
            />
          ) : (
            <TextInput label="Hire date" type="date" {...form.getInputProps('hire_date')} />
          )}
        </SimpleGrid>
        {!editing && (
          <SimpleGrid cols={2}>
            <TextInput
              label={`Annual base${currency ? ` (${currency})` : ''}`}
              inputMode="decimal"
              {...form.getInputProps('base_amount')}
            />
            <TextInput
              label={`Annual bonus${currency ? ` (${currency})` : ''}`}
              inputMode="decimal"
              {...form.getInputProps('bonus_amount')}
            />
          </SimpleGrid>
        )}
        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={mutation.isPending}>
            {editing ? 'Save changes' : 'Create employee'}
          </Button>
        </Group>
      </Stack>
    </form>
  )
}
