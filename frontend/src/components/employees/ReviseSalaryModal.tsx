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
import type { Schemas } from '../../api/client'
import { useReviseSalary } from '../../api/employees'
import { formatDate, formatMoney, formatPct, humanize, MONEY_PATTERN } from '../../lib/format'

type Reason = Schemas['SalaryRevisionCreate']['reason']
const REASONS: Reason[] = ['merit', 'promotion', 'market_adjustment', 'correction']

interface Props {
  opened: boolean
  onClose: () => void
  employeeId: number
  current: Schemas['SalaryRecordOut']
}

export function ReviseSalaryModal({ opened, onClose, employeeId, current }: Props) {
  return (
    <Modal opened={opened} onClose={onClose} title="Revise salary" size="md">
      {/* Mounted only while open, so every opening starts from the current pay. */}
      <ReviseSalaryForm onClose={onClose} employeeId={employeeId} current={current} />
    </Modal>
  )
}

interface FormValues {
  base_amount: string
  bonus_amount: string
  effective_from: string
  reason: Reason
  note: string
}

/**
 * New pay from a date onwards. The current record is closed, never edited, so the
 * earliest allowed date is the day after it started; the API also refuses future dates.
 */
function ReviseSalaryForm({ onClose, employeeId, current }: Omit<Props, 'opened'>) {
  const revise = useReviseSalary(employeeId)
  const form = useForm<FormValues>({
    initialValues: {
      base_amount: current.base_amount,
      bonus_amount: current.bonus_amount,
      effective_from: '',
      reason: 'merit',
      note: '',
    },
    validate: {
      base_amount: (v) => (MONEY_PATTERN.test(v) && Number(v) > 0 ? null : 'Enter an amount'),
      bonus_amount: (v) => (MONEY_PATTERN.test(v) ? null : 'Enter an amount (0 for none)'),
      effective_from: (v) =>
        !v
          ? 'Pick a date'
          : v <= current.effective_from
            ? 'Must be after the current pay started'
            : null,
    },
  })

  const submit = form.onSubmit(async (values) => {
    try {
      const result = await revise.mutateAsync({
        base_amount: values.base_amount,
        bonus_amount: values.bonus_amount,
        currency_code: current.currency_code,
        effective_from: values.effective_from,
        reason: values.reason,
        note: values.note || null,
      })
      notifications.show({
        color: 'teal',
        message: `Base pay ${formatPct(result.base_change_pct)} from ${formatDate(values.effective_from)}`,
      })
      onClose()
    } catch {
      // shown from revise.error below
    }
  })

  return (
    <form onSubmit={submit}>
      <Stack>
        <Text size="sm" c="dimmed">
          Current: {formatMoney(current.base_amount, current.currency_code)} base since{' '}
          {formatDate(current.effective_from)}. Amounts are annual, in {current.currency_code}.
        </Text>
        {revise.error && <Alert color="red">{revise.error.message}</Alert>}
        <SimpleGrid cols={2}>
          <TextInput label="New base" inputMode="decimal" {...form.getInputProps('base_amount')} />
          <TextInput
            label="New bonus"
            inputMode="decimal"
            {...form.getInputProps('bonus_amount')}
          />
          <TextInput label="Effective from" type="date" {...form.getInputProps('effective_from')} />
          <Select
            label="Reason"
            data={REASONS.map((r) => ({ value: r, label: humanize(r) }))}
            allowDeselect={false}
            {...form.getInputProps('reason')}
          />
        </SimpleGrid>
        <TextInput
          label="Note"
          placeholder="Optional"
          maxLength={255}
          {...form.getInputProps('note')}
        />
        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={revise.isPending}>
            Save revision
          </Button>
        </Group>
      </Stack>
    </form>
  )
}
