/**
 * Registro global de "quién está grabando ahora".
 *
 * `useVoiceCapture` se usa de forma independiente en más de una pantalla a la vez
 * (pestaña Dentia, Atención con dictado) y cada instancia tiene su propio estado de
 * React. Para poder detener una grabación en curso desde otra pantalla (p. ej. al
 * cerrar sesión desde Ajustes mientras Dentia sigue escuchando en su pestaña) se
 * necesita un punto de referencia fuera de React. Solo puede haber una grabación
 * activa a la vez en la app, así que un único "slot" es suficiente.
 */

type StopFn = () => void;

let activeStop: StopFn | null = null;

export function registerActiveRecording(stop: StopFn | null): void {
  activeStop = stop;
}

export function stopActiveRecording(): void {
  activeStop?.();
}
