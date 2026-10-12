import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * Confirmación implícita (decisión del proyecto: 3 segundos).
 * Dentia anuncia la acción, muestra una cuenta regresiva con botón "Cancelar" y,
 * si nadie la cancela, la ejecuta sola. Evita el "¿confirmas?" en cada orden sin
 * perder la posibilidad de corregir una orden mal entendida.
 *
 * La cuenta vive en refs (no dentro de un updater de setState) para que la acción
 * se ejecute exactamente una vez, incluso en React StrictMode.
 */
export function useImplicitConfirm(seconds = 3) {
  const [pending, setPending] = useState<{ label: string; remaining: number } | null>(null);
  const action = useRef<(() => void | Promise<void>) | null>(null);
  const remaining = useRef(0);
  const label = useRef('');
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const clear = useCallback(() => {
    if (timer.current) clearInterval(timer.current);
    timer.current = null;
    action.current = null;
    setPending(null);
  }, []);

  const schedule = useCallback(
    (text: string, run: () => void | Promise<void>) => {
      clear();
      action.current = run;
      remaining.current = seconds;
      label.current = text;
      setPending({ label: text, remaining: seconds });
      timer.current = setInterval(() => {
        remaining.current -= 1;
        if (remaining.current <= 0) {
          const fn = action.current;
          clear();
          void fn?.();
        } else {
          setPending({ label: label.current, remaining: remaining.current });
        }
      }, 1000);
    },
    [clear, seconds],
  );

  /** Ejecuta ya, sin esperar (el usuario dijo "sí" o tocó "Hacerlo ya"). */
  const confirmNow = useCallback(() => {
    const fn = action.current;
    clear();
    void fn?.();
  }, [clear]);

  useEffect(() => clear, [clear]);

  return { pending, schedule, cancel: clear, confirmNow };
}
