import { TextInput, type TextInputProps } from '@mantine/core'
import { useDebouncedValue } from '@mantine/hooks'
import { useEffect, useState } from 'react'

interface Props extends Omit<TextInputProps, 'value' | 'onChange'> {
  value: string
  onCommit: (value: string) => void
  delay?: number
}

/**
 * A text input that reports its value only after typing pauses, so each keystroke
 * does not fire a request. An outside change to `value` (back button, cleared
 * filters) replaces the draft.
 */
export function DebouncedInput({ value, onCommit, delay = 300, ...props }: Props) {
  const [draft, setDraft] = useState(value)
  const [seen, setSeen] = useState(value)
  if (value !== seen) {
    // adjust state while rendering, React's pattern for resetting on a prop change
    setSeen(value)
    setDraft(value)
  }
  const [debounced] = useDebouncedValue(draft, delay)

  useEffect(() => {
    // Commit only once typing has settled (debounced caught up with the draft),
    // so a stale debounced value never overwrites an outside change.
    if (debounced === draft && debounced !== value) onCommit(debounced)
  }, [debounced, draft, value, onCommit])

  return <TextInput {...props} value={draft} onChange={(e) => setDraft(e.currentTarget.value)} />
}
