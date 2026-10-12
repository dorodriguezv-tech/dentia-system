import type { ExpoConfig } from 'expo/config';

/**
 * Configuración de la app DENT-IA (Android primero; iOS listo para después).
 *
 * APP_VARIANT lo pone eas.json en cada perfil:
 *   development -> apk de desarrollo (dev client), permite http:// en la red local
 *   preview     -> apk de pruebas internas, solo https://
 *   production  -> .aab para Google Play, solo https://
 */
const VARIANT = (process.env.APP_VARIANT ?? 'development') as
  | 'development'
  | 'preview'
  | 'production';

const IS_DEV = VARIANT === 'development';

// El identificador de Android NO se puede cambiar después de publicar en Google Play.
// Cámbialo ANTES del primer build por un dominio tuyo (al revés): mx.tuclinica.dentia
const BASE_PACKAGE = 'mx.dentia.app';
const PACKAGE = IS_DEV ? `${BASE_PACKAGE}.dev` : VARIANT === 'preview' ? `${BASE_PACKAGE}.preview` : BASE_PACKAGE;

const config: ExpoConfig = {
  // Marca del producto: DENT-IA (logo oficial en assets/brand/). Los identificadores
  // técnicos (slug, scheme, package) siguen como "dentia" sin guion.
  name: IS_DEV ? 'DENT-IA (dev)' : 'DENT-IA',
  slug: 'dentia-mobile',
  scheme: 'dentia',
  version: '1.0.0',
  orientation: 'default', // tablets en el sillón dental: permitir horizontal
  icon: './assets/icon.png',
  userInterfaceStyle: 'automatic',
  android: {
    package: PACKAGE,
    // versionCode lo incrementa EAS automáticamente (eas.json -> autoIncrement)
    adaptiveIcon: {
      foregroundImage: './assets/adaptive-icon.png', // isotipo DENT-IA (diente con circuitos)
      monochromeImage: './assets/adaptive-icon-monochrome.png', // íconos temáticos de Android 13+
      backgroundColor: '#FFFFFF',
    },
    // Solo los permisos que la app usa de verdad. Google Play revisa cada uno.
    permissions: ['android.permission.RECORD_AUDIO', 'android.permission.CAMERA'],
    blockedPermissions: [
      'android.permission.READ_EXTERNAL_STORAGE',
      'android.permission.WRITE_EXTERNAL_STORAGE',
      'android.permission.SYSTEM_ALERT_WINDOW',
      'android.permission.ACCESS_FINE_LOCATION',
      'android.permission.ACCESS_COARSE_LOCATION',
    ],
    // Datos clínicos: no respaldar en Google Drive del teléfono
    allowBackup: false,
  },
  ios: {
    bundleIdentifier: PACKAGE,
    supportsTablet: true,
    infoPlist: {
      NSMicrophoneUsageDescription:
        'DENT-IA usa el micrófono para que el odontólogo dicte la nota clínica y hable con el asistente.',
      NSCameraUsageDescription: 'DENT-IA usa la cámara para tomar fotografías clínicas del paciente.',
    },
  },
  plugins: [
    'expo-router',
    'expo-secure-store',
    'expo-font',
    'expo-asset',
    [
      'expo-splash-screen',
      {
        image: './assets/splash.png', // logo DENT-IA completo
        imageWidth: 260,
        resizeMode: 'contain',
        backgroundColor: '#FFFFFF',
        dark: { image: './assets/splash-dark.png', backgroundColor: '#0B1A24' },
      },
    ],
    [
      'expo-audio',
      {
        microphonePermission:
          'DENT-IA usa el micrófono para que el odontólogo dicte la nota clínica y hable con el asistente.',
        recordAudioAndroid: true,
        enableBackgroundRecording: false,
        enableBackgroundPlayback: false,
      },
    ],
    [
      'expo-image-picker',
      {
        cameraPermission: 'DENT-IA usa la cámara para tomar fotografías clínicas del paciente.',
        photosPermission: false,
        microphonePermission: false,
      },
    ],
    [
      'expo-local-authentication',
      { faceIDPermission: 'DENT-IA usa Face ID para desbloquear la sesión.' },
    ],
    [
      'expo-build-properties',
      {
        android: {
          compileSdkVersion: 36,
          targetSdkVersion: 36, // requisito de Google Play desde el 31-ago-2026
          minSdkVersion: 26,
          // http:// sin cifrar SOLO en el build de desarrollo (servidor de la clínica en la LAN).
          // preview/production exigen https://.
          usesCleartextTraffic: IS_DEV,
        },
      },
    ],
  ],
  experiments: {
    typedRoutes: true,
  },
  extra: {
    variant: VARIANT,
    eas: {
      // Lo llena `eas init` la primera vez
      projectId: process.env.EAS_PROJECT_ID,
    },
  },
};

export default config;
