import { MutationCache } from '@tanstack/react-query'
import { ApiRequestError } from '../api/client'
import { useErrorToastStore } from './errorToastStore'

export function mutationErrorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) return error.message
  return 'Ocurrio un error inesperado. Intenta de nuevo.'
}

/** A4 (red de seguridad): hasta esta fase, un boton "Agregar" cuya mutacion fallara
 * (403 por permisos, 422 de validacion, 500...) sin un manejo de error propio en esa
 * pantalla simplemente no hacia nada visible -- la causa raiz no era un boton roto a
 * la vez, sino que no habia una red de seguridad comun. Esta MutationCache la provee:
 * toda mutacion de la app que no defina su propio `onError` cae aqui. */
export function createGlobalMutationCache(): MutationCache {
  return new MutationCache({
    onError: (error, _variables, _context, mutation) => {
      if (mutation.options.onError) return
      useErrorToastStore.getState().show(mutationErrorMessage(error))
    },
  })
}
