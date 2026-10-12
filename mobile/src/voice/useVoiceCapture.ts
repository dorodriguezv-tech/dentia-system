import {
  RecordingPresets,
  requestRecordingPermissionsAsync,
  setAudioModeAsync,
  useAudioRecorder,
  useAudioRecorderState,
  type RecordingOptions,
} from 'expo-audio';
import * as Haptics from 'expo-haptics';
import { useCallback, useRef, useState } from 'react';

import { errorMessage } from '@/api/client';
import { transcribe } from '@/api/endpoints';

/**
 * Graba del micrófono y transcribe con el faster-whisper del servidor de la clínica
 * (POST /ai/transcribe). El audio NO se manda a ningún servicio externo y se borra
 * del teléfono en cuanto termina la transcripción (el archivo vive en la caché).
 *
 * Preset propio para voz: mono, 16 kHz, AAC 64 kbps → archivos ~8 KB/s, suficientes
 * para Whisper y rápidos de subir por Wi-Fi.
 */
const VOICE_PRESET: RecordingOptions = {
  ...RecordingPresets.HIGH_QUALITY,
  sampleRate: 16000,
  numberOfChannels: 1,
  bitRate: 64000,
  android: {
    ...RecordingPresets.HIGH_QUALITY.android,
    audioSource: 'voice_recognition',
  },
};

export type CaptureState = 'idle' | 'recording' | 'transcribing' | 'error';

export function useVoiceCapture() {
  const recorder = useAudioRecorder(VOICE_PRESET);
  const recState = useAudioRecorderState(recorder, 250);
  const [state, setState] = useState<CaptureState>('idle');
  const [error, setError] = useState<string | null>(null);
  const busy = useRef(false);

  const start = useCallback(async () => {
    if (busy.current) return;
    busy.current = true;
    setError(null);
    try {
      const perm = await requestRecordingPermissionsAsync();
      if (!perm.granted) {
        throw new Error('Sin permiso de micrófono. Actívalo en Ajustes del teléfono → Apps → DENT-IA → Permisos.');
      }
      await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true });
      await recorder.prepareToRecordAsync();
      recorder.record();
      await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
      setState('recording');
    } catch (e) {
      setError(errorMessage(e));
      setState('error');
    } finally {
      busy.current = false;
    }
  }, [recorder]);

  /** Detiene y devuelve el texto transcrito ('' si no hubo voz). */
  const stopAndTranscribe = useCallback(async (): Promise<string> => {
    if (busy.current) return '';
    busy.current = true;
    try {
      await recorder.stop();
      await setAudioModeAsync({ allowsRecording: false, playsInSilentMode: true });
      await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
      const uri = recorder.uri;
      if (!uri) return '';
      setState('transcribing');
      const { text } = await transcribe(uri);
      setState('idle');
      return text.trim();
    } catch (e) {
      setError(errorMessage(e));
      setState('error');
      return '';
    } finally {
      busy.current = false;
    }
  }, [recorder]);

  const cancel = useCallback(async () => {
    try {
      if (recState.isRecording) await recorder.stop();
    } finally {
      setState('idle');
    }
  }, [recorder, recState.isRecording]);

  return {
    state,
    error,
    seconds: Math.floor((recState.durationMillis ?? 0) / 1000),
    isRecording: recState.isRecording,
    start,
    stopAndTranscribe,
    cancel,
  };
}
