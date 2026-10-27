/** Fase E (Historia Clinica Pediatrica): helper puro (sin JSX) separado de
 * historyShared.tsx solo para que ese archivo quede compuesto unicamente por
 * componentes (evita el warning de react-refresh/only-export-components de
 * mezclar componentes y funciones en el mismo modulo). */

/** Fila para DetailList de un campo `bool | null`: omite la fila si no se
 * respondio (null) -- distinto de un checkbox simple, aqui "No" es una
 * respuesta capturada que si debe verse. */
export function triStateRow(label: string, value: boolean | null | undefined): [string, string] | null {
  if (value === null || value === undefined) return null
  return [label, value ? 'Sí' : 'No']
}

// --------------------------------------------------------------------------------
// Correccion UX (ronda 2.2, docs/clinica): patron "editar" generico para
// secciones "una fila por encuentro" (p.ej. PathologicalHistorySection,
// OdontologicalExamSection, PerinatalHistorySection, Interrogation de
// Endodoncia, etc.) -- por dentro sigue siendo anular+recapturar (regla 2 de
// CLAUDE.md: nunca borrado fisico), pero se siente como "editar" para el
// usuario: si ya existe una entrada activa, el formulario aparece pre-llenado
// y el guardado anula automaticamente esa entrada (motivo fijo, sin pedirselo
// al usuario) antes de crear la nueva con los datos corregidos. Viven aqui
// (no en historyShared.tsx) porque son funciones puras, no componentes --
// mismo criterio que triStateRow de arriba.
// --------------------------------------------------------------------------------

/** Motivo automatico de anulacion al "editar" -- no es una anulacion clinica
 * excepcional, es una correccion de datos normal, asi que no se le pide al
 * usuario que lo escriba. */
export const AUTO_CORRECTION_REASON = 'Corrección de datos'

/** Entrada activa mas reciente de una lista -- es la que se considera "la
 * actual" a editar en las secciones de una sola entrada vigente por vez. */
export function latestActive<T extends { is_active: boolean; created_at: string }>(
  items: T[] | undefined,
): T | undefined {
  const active = (items ?? []).filter((item) => item.is_active)
  if (active.length === 0) return undefined
  return [...active].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  )[0]
}

/** Envuelve la creacion con la anulacion automatica de `current` (si existe)
 * -- usar como `mutationFn` del `useMutation` de guardado de cada seccion. */
export async function saveWithAutoCorrection<TOut>(
  current: { id: string } | undefined,
  annul: (itemId: string, reason: string) => Promise<unknown>,
  create: () => Promise<TOut>,
): Promise<TOut> {
  if (current) {
    await annul(current.id, AUTO_CORRECTION_REASON)
  }
  return create()
}
