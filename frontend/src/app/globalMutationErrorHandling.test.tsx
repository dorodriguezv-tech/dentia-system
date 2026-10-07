import { QueryClient, useMutation } from '@tanstack/react-query'
import { QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { ApiRequestError } from '../api/client'
import { useErrorToastStore } from './errorToastStore'
import { createGlobalMutationCache } from './globalMutationErrorHandling'

function renderMutation(onError?: (error: unknown) => void) {
  const queryClient = new QueryClient({ mutationCache: createGlobalMutationCache() })
  return renderHook(
    () =>
      useMutation({
        mutationFn: () => {
          throw new ApiRequestError(422, { code: 'VALIDATION_ERROR', message: 'Dato invalido' })
        },
        onError,
      }),
    {
      wrapper: ({ children }) => (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      ),
    },
  )
}

describe('createGlobalMutationCache (A4, red de seguridad)', () => {
  beforeEach(() => {
    useErrorToastStore.setState({ message: null })
  })

  it('muestra el mensaje del backend cuando la mutacion no maneja su propio error', async () => {
    const { result } = renderMutation()

    result.current.mutate()

    await waitFor(() => expect(useErrorToastStore.getState().message).toBe('Dato invalido'))
  })

  it('no duplica el mensaje si la pantalla ya define su propio onError', async () => {
    let localError: unknown
    const { result } = renderMutation((error) => {
      localError = error
    })

    result.current.mutate()

    await waitFor(() => expect(localError).toBeInstanceOf(ApiRequestError))
    expect(useErrorToastStore.getState().message).toBeNull()
  })
})
