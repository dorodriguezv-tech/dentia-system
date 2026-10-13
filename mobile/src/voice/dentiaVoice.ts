import * as Speech from 'expo-speech';

/**
 * Voz de Dentia: síntesis del propio teléfono (sin internet), en español de México,
 * preferentemente con voz femenina.
 *
 * Android no expone el "género" de una voz; el motor de Google nombra sus voces como
 * "es-us-x-esc-local" / "es-us-x-esf-network", etc. Elegimos por idioma y preferimos
 * voces locales (no "network", que mandarían texto a internet) y las conocidas como
 * femeninas. Si el teléfono no tiene ninguna, usa la predeterminada del idioma.
 * El usuario puede fijar otra en Ajustes → Voz de Dentia.
 */

const PREFERRED_LANGS = ['es-MX', 'es-US', 'es-419', 'es-ES'];
// Identificadores de voces femeninas frecuentes en el motor de Google y en iOS
const FEMALE_HINTS = ['esc', 'esf', 'female', 'mujer', 'paulina', 'monica', 'mónica', 'helena', 'sabina', 'dalia', 'esd'];

let cachedVoice: string | null | undefined;
let userVoice: string | null = null;
let userRate = 1.0;
let userVolume = 1.0;

export function setPreferredVoice(id: string | null) {
  userVoice = id;
}

/** M2: "Mis preferencias" → velocidad y volumen de la voz de Dentia. */
export function setSpeechRate(rate: number) {
  userRate = rate;
}

export function setSpeechVolume(volume: number) {
  userVolume = volume;
}

export async function listSpanishVoices(): Promise<Speech.Voice[]> {
  const voices = await Speech.getAvailableVoicesAsync();
  return voices.filter((v) => v.language.toLowerCase().startsWith('es'));
}

async function pickVoice(): Promise<string | null> {
  if (userVoice) return userVoice;
  if (cachedVoice !== undefined) return cachedVoice;
  try {
    const voices = await listSpanishVoices();
    const local = voices.filter((v) => !/network/i.test(v.identifier));
    const pool = local.length ? local : voices;
    const byLang = (v: Speech.Voice) => {
      const i = PREFERRED_LANGS.findIndex((l) => v.language.replace('_', '-').toLowerCase() === l.toLowerCase());
      return i === -1 ? 99 : i;
    };
    const isFemale = (v: Speech.Voice) => FEMALE_HINTS.some((h) => `${v.identifier} ${v.name}`.toLowerCase().includes(h));
    const sorted = [...pool].sort((a, b) => Number(isFemale(b)) - Number(isFemale(a)) || byLang(a) - byLang(b));
    cachedVoice = sorted[0]?.identifier ?? null;
  } catch {
    cachedVoice = null;
  }
  return cachedVoice;
}

export async function say(text: string, onDone?: () => void): Promise<void> {
  await Speech.stop();
  const voice = await pickVoice();
  Speech.speak(text, {
    language: 'es-MX',
    voice: voice ?? undefined,
    rate: userRate,
    volume: userVolume,
    pitch: 1.05,
    onDone,
    onStopped: onDone,
    onError: () => onDone?.(),
  });
}

export const stopSpeaking = () => Speech.stop();
