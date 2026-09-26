import {
  Alert,
  Button,
  Group,
  Modal,
  Select,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
} from '@mantine/core'
import { useForm } from '@mantine/form'
import { notifications } from '@mantine/notifications'
import { useCreateBand, useUpdateBand } from '../../api/bands'
import type { Schemas } from '../../api/client'
import { useReferenceData } from '../../api/reference'
import { MONEY_PATTERN } from '../../lib/format'
import { SCOPE_LABEL } from '../../lib/labels'
import { bandAmountsError } from '../../lib/pay'

type Band = Schemas['BandOut']

interface Props {
  opened: boolean
  onClose: () => void
  /** Edit this band's amounts; create a new band when absent. */
  band?: Band | null
}

export function BandFormModal({ opened, onClose, band }: Props) {
  return (
    <Modal opened={opened} onClose={onClose} title={band ? 'Edit band' : 'New band'} size="lg">
      {/* Mounted only while open, so every opening starts from fresh form state. */}
      <BandForm onClose={onClose} band={band} />
    </Modal>
  )
}

interface FormValues {
  department_id: string | null
  role_id: string | null
  level_id: string | null
  country_id: string | null
  min_amount: string
  mid_amount: string
  max_amount: string
}

const amount = (v: string) => (MONEY_PATTERN.test(v) && Number(v) > 0 ? null : 'Enter an amount')

function BandForm({ onClose, band }: Omit<Props, 'opened'>) {
  const editing = band != null
  const { data: reference } = useReferenceData()
  const create = useCreateBand()
  const update = useUpdateBand()
  const mutation = editing ? update : create

  const form = useForm<FormValues>({
    initialValues: {
      department_id: null,
      role_id: null,
      level_id: null,
      country_id: null,
      min_amount: band?.min_amount ?? '',
      mid_amount: band?.mid_amount ?? '',
      max_amount: band?.max_amount ?? '',
    },
    validate: {
      department_id: (v) => (editing || v ? null : 'Department is required'),
      level_id: (v) => (editing || v ? null : 'Level is required'),
      country_id: (v, values) =>
        editing || v || !values.role_id ? null : 'A role-specific band needs a country',
      min_amount: amount,
      mid_amount: amount,
      max_amount: (v, values) =>
        amount(v) ?? bandAmountsError(values.min_amount, values.mid_amount, v),
    },
  })

  const roles = (reference?.roles ?? []).filter(
    (r) =>
      form.values.department_id != null && r.department_id === Number(form.values.department_id),
  )
  const country = reference?.countries.find((c) => String(c.id) === form.values.country_id)
  const currency = editing ? band.currency_code : (country?.currency_code ?? 'USD')

  const submit = form.onSubmit(async (values) => {
    const amounts = {
      min_amount: values.min_amount,
      mid_amount: values.mid_amount,
      max_amount: values.max_amount,
    }
    try {
      if (editing) {
        await update.mutateAsync({ bandId: band.id, body: amounts })
      } else {
        await create.mutateAsync({
          department_id: Number(values.department_id),
          level_id: Number(values.level_id),
          role_id: values.role_id ? Number(values.role_id) : null,
          country_id: values.country_id ? Number(values.country_id) : null,
          ...amounts,
        })
      }
      notifications.show({ color: 'teal', message: editing ? 'Band updated' : 'Band created' })
      onClose()
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
        {editing ? (
          <Text size="sm">
            {band.department.name} · {band.role?.name ?? 'all roles'} · {band.level.code} ·{' '}
            {band.country?.name ?? 'all countries'}{' '}
            <Text span c="dimmed">
              ({SCOPE_LABEL[band.scope]})
            </Text>
          </Text>
        ) : (
          <>
            <Text size="sm" c="dimmed">
              Leave role empty for a band covering every role in the department, and country empty
              for a department-wide band in USD. The most specific band wins.
            </Text>
            <SimpleGrid cols={2}>
              <Select
                label="Department"
                data={option(reference?.departments, (d) => d.name)}
                {...form.getInputProps('department_id')}
                onChange={(value) => {
                  form.setFieldValue('department_id', value)
                  form.setFieldValue('role_id', null)
                }}
              />
              <Select
                label="Level"
                data={option(reference?.levels, (l) => `${l.code} · ${l.name}`)}
                {...form.getInputProps('level_id')}
              />
              <Select
                label="Role"
                placeholder="All roles"
                clearable
                data={option(roles, (r) => r.name)}
                disabled={form.values.department_id == null}
                {...form.getInputProps('role_id')}
              />
              <Select
                label="Country"
                placeholder="All countries (USD)"
                clearable
                data={option(reference?.countries, (c) => `${c.name} (${c.currency_code})`)}
                {...form.getInputProps('country_id')}
              />
            </SimpleGrid>
          </>
        )}
        <SimpleGrid cols={3}>
          <TextInput
            label={`Min (${currency})`}
            inputMode="decimal"
            {...form.getInputProps('min_amount')}
          />
          <TextInput
            label={`Mid (${currency})`}
            inputMode="decimal"
            {...form.getInputProps('mid_amount')}
          />
          <TextInput
            label={`Max (${currency})`}
            inputMode="decimal"
            {...form.getInputProps('max_amount')}
          />
        </SimpleGrid>
        {editing && (
          <Text size="xs" c="dimmed">
            Changes apply from now on: compliance and compa-ratios use today's band. Salary records
            are not changed.
          </Text>
        )}
        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={mutation.isPending}>
            {editing ? 'Save band' : 'Create band'}
          </Button>
        </Group>
      </Stack>
    </form>
  )
}
