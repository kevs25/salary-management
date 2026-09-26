import { Alert, Center, Loader } from '@mantine/core'
import type { ReactNode } from 'react'

interface Props {
  isPending: boolean
  error: Error | null
  children: ReactNode
}

/** Loader while the first fetch runs, the error message if it failed, else the content. */
export function QueryStatus({ isPending, error, children }: Props) {
  if (error) {
    return (
      <Alert color="red" title="Could not load data">
        {error.message}
      </Alert>
    )
  }
  if (isPending) {
    return (
      <Center py="xl">
        <Loader />
      </Center>
    )
  }
  return <>{children}</>
}
