/**
 * Intérprete de órdenes de voz para el asistente "Dentia" en el teléfono.
 *
 * Es deliberadamente determinista (expresiones regulares, sin LLM): las órdenes de
 * navegación son pocas y tienen que responder en menos de un segundo. El dictado
 * clínico NO pasa por aquí: va a /ai/transcribe + /ai/interpret (Ollama) y se revisa
 * propuesta por propuesta (regla 9). Este archivo no tiene dependencias de React
 * Native para poder probarlo con Jest o con `npx tsx`.
 */

export type Intent =
  | { type: 'OPEN_PATIENT'; name: string }
  | { type: 'SHOW_AGENDA'; dayOffset: number }
  | { type: 'NEXT_APPOINTMENT' }
  | { type: 'CHECK_IN'; name: string }
  | { type: 'START_DICTATION' }
  | { type: 'CANCEL' }
  | { type: 'CONFIRM' }
  | { type: 'HELP' }
  | { type: 'UNKNOWN'; text: string };

/** Minúsculas, sin acentos, sin signos, espacios simples. */
export function normalize(text: string): string {
  return text
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[¿?¡!.,;:"']/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

/** Quita la palabra de activación ("Dentia", "oye Dentia", y errores típicos de Whisper). */
export function stripWakeWord(text: string): string {
  return text.replace(/^(oye |hola |ok )?(dentia|dentya|dentía|dencia|dentista|denthia)\b[ ,]*/i, '').trim();
}

const NAME_CONNECTORS = /^(de la |del |de |a la |al |a )/;

function cleanName(raw: string): string {
  return raw
    .replace(NAME_CONNECTORS, '')
    .replace(/\b(por favor|porfa|gracias)\b/g, '')
    .replace(/^(paciente|senor|senora|senorita|sr|sra|don|dona|doctor|doctora|dr|dra) /, '')
    .replace(/\s+/g, ' ')
    .trim();
}

export function parseIntent(rawText: string): Intent {
  const text = stripWakeWord(normalize(rawText));

  if (!text) return { type: 'HELP' };

  // Cancelar tiene prioridad: "no, cancela" durante la cuenta regresiva de 3 s
  if (/^(no|cancela|cancelar|cancelalo|detente|alto|para|olvidalo|espera|eso no)\b/.test(text)) {
    return { type: 'CANCEL' };
  }
  if (/^(si|confirmo|correcto|adelante|hazlo|ok|okay|va)\b$/.test(text) || /^(si|confirmo|correcto),? (hazlo|adelante)$/.test(text)) {
    return { type: 'CONFIRM' };
  }
  if (/^(ayuda|que puedes hacer|que sabes hacer|comandos)\b/.test(text)) return { type: 'HELP' };

  // "abre (el) expediente / la ficha / al paciente de Juan Pérez"
  const open = text.match(
    /^(abre|abrir|abreme|muestra|muestrame|busca|buscar|ver|enseñame|ensename)( el| la| al)? (expediente|ficha|paciente|historia clinica|odontograma)( del paciente| de la paciente)? (.+)$/,
  );
  if (open?.[5]) {
    const name = cleanName(open[5]);
    if (name.length >= 2) return { type: 'OPEN_PATIENT', name };
  }
  // "busca a Juan Pérez"
  const busca = text.match(/^(busca|buscar|abre) (a |al |a la )?(.+)$/);
  if (busca?.[3] && !/agenda|citas?/.test(busca[3])) {
    const name = cleanName(busca[3]);
    if (name.length >= 2) return { type: 'OPEN_PATIENT', name };
  }

  // Agenda
  if (/\b(agenda|citas?|pacientes)\b/.test(text) && /\b(manana)\b/.test(text) && !/pasado manana/.test(text)) {
    return { type: 'SHOW_AGENDA', dayOffset: 1 };
  }
  if (/\b(agenda|citas?)\b/.test(text) && /pasado manana/.test(text)) return { type: 'SHOW_AGENDA', dayOffset: 2 };
  if (/\b(agenda|citas?)\b/.test(text) && /\b(ayer)\b/.test(text)) return { type: 'SHOW_AGENDA', dayOffset: -1 };
  if (/^(muestra|abre|ver|cual es|como esta|que tengo)?( la| mi)? ?(agenda|citas)( de hoy| del dia)?$/.test(text) || /que (citas|pacientes) tengo( hoy)?/.test(text)) {
    return { type: 'SHOW_AGENDA', dayOffset: 0 };
  }

  if (/(siguiente|proximo|proxima) (paciente|cita)|quien sigue/.test(text)) return { type: 'NEXT_APPOINTMENT' };

  // "Juan Pérez ya llegó" / "pasa a sala a Juan Pérez" / "llegó Juan Pérez"
  const llego1 = text.match(/^(.+?) (ya )?(llego|esta en sala|esta aqui)$/);
  if (llego1?.[1] && !/^(el|la|ya)$/.test(llego1[1])) return { type: 'CHECK_IN', name: cleanName(llego1[1]) };
  const llego2 = text.match(/^(pasa|pasar|registra|marca)( a)? (sala|llegada)( a| de)? (.+)$/) ?? text.match(/^(llego) (.+)$/);
  if (llego2) {
    const name = cleanName(llego2[llego2.length - 1] ?? '');
    if (name.length >= 2) return { type: 'CHECK_IN', name };
  }

  if (/(empieza|empezar|inicia|iniciar|comienza|comenzar) (el |un )?(dictado|nota|a dictar)|^dictado$|^dictar$/.test(text)) {
    return { type: 'START_DICTATION' };
  }

  return { type: 'UNKNOWN', text };
}

/** Frase que Dentia dice antes de ejecutar (confirmación implícita de 3 s). */
export function describeIntent(intent: Intent): string {
  switch (intent.type) {
    case 'OPEN_PATIENT':
      return `Abriendo el expediente de ${intent.name}.`;
    case 'SHOW_AGENDA':
      return intent.dayOffset === 0
        ? 'Mostrando la agenda de hoy.'
        : intent.dayOffset === 1
          ? 'Mostrando la agenda de mañana.'
          : intent.dayOffset === -1
            ? 'Mostrando la agenda de ayer.'
            : 'Mostrando la agenda de pasado mañana.';
    case 'NEXT_APPOINTMENT':
      return 'Buscando la siguiente cita.';
    case 'CHECK_IN':
      return `Registrando la llegada de ${intent.name}.`;
    case 'START_DICTATION':
      return 'Iniciando el dictado.';
    case 'CANCEL':
      return 'Cancelado.';
    case 'CONFIRM':
      return 'Hecho.';
    case 'HELP':
      return HELP_TEXT;
    case 'UNKNOWN':
      return 'No entendí la orden. Puedes decir, por ejemplo: abre el expediente de Ana López, o: agenda de hoy.';
  }
}

/** Órdenes que se ejecutan solas tras 3 s salvo que el usuario diga "cancela". */
export function needsImplicitConfirm(intent: Intent): boolean {
  return intent.type === 'OPEN_PATIENT' || intent.type === 'CHECK_IN';
}

export const HELP_TEXT =
  'Puedes decirme: abre el expediente de un paciente, agenda de hoy o de mañana, siguiente paciente, ' +
  'el nombre del paciente y ya llegó, o empieza el dictado. Para cancelar di: cancela.';
