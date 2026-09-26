import { createTheme } from '@mantine/core'

export const theme = createTheme({
  primaryColor: 'indigo',
  defaultRadius: 'md',
  fontFamily: 'Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif',
  headings: { fontWeight: '600' },
})

/** Band position colours, shared by badges and charts. */
export const positionColor = {
  below: 'red',
  within: 'teal',
  above: 'orange',
  no_band: 'gray',
} as const
