import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as encountersApi from './api'

function isSameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
  )
}

/** A3/A4 (CLAUDE.md doc 06): toda pantalla que necesita un `encounter_id` (expediente,
 * planes de tratamiento) comparte este selector en vez de reinventar el mismo patron
 * roto por separado -- antes cada pantalla mantenia su propio estado sin preseleccion,
 * sin salida para un paciente sin atenciones, y sin mostrar un error si la carga
 * fallaba. Usar este hook es la correccion de raiz: una pantalla nueva que necesite
 * un `encounter_id` ya no puede repetir el bug con solo copiar y pegar. */
export function useEncounterPicker(patientId: string, canCreateNew: boolean, enabled = true) {
  const queryClient = useQueryClient()
  const encountersQuery = useQuery({
    queryKey: ['patient-encounters', patientId],
    queryFn: () => encountersApi.listPatientEncounters(patientId),
    enabled,
  })
  const [selectedEncounterId, setSelectedEncounterId] = useState('')

  const encounters = encountersQuery.data ?? []
  // Preseleccion (sin useEffect): mientras el usuario no haya elegido nada a mano, la
  // atencion de hoy (si existe) es el valor efectivo. En cuanto elige una distinta (o
  // crea una nueva), selectedEncounterId manda.
  const today = new Date()
  const todaysEncounter = encounters.find((e) => isSameDay(new Date(e.started_at), today))
  const encounterId = selectedEncounterId || todaysEncounter?.id || ''

  const createMutation = useMutation({
    mutationFn: () => encountersApi.createEncounter({ patient_id: patientId }),
    onSuccess: (encounter) => {
      setSelectedEncounterId(encounter.id)
      queryClient.invalidateQueries({ queryKey: ['patient-encounters', patientId] })
    },
  })

  return {
    encounters,
    loadError: encountersQuery.isError,
    encounterId,
    setEncounterId: setSelectedEncounterId,
    canCreateNew,
    createNew: () => createMutation.mutate(),
    isCreating: createMutation.isPending,
    createError: createMutation.isError,
  }
}

export type EncounterPicker = ReturnType<typeof useEncounterPicker>
