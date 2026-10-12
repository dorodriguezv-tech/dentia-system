import { resolveApiAssetUrl } from '../../api/client'
import { useThemeStore } from '../../theme/store'
import logoColor from '../../assets/brand/dentia-logo.png'
import logoWhite from '../../assets/brand/dentia-logo-blanco.png'
import isotipoColor from '../../assets/brand/dentia-isotipo.png'
import isotipoWhite from '../../assets/brand/dentia-isotipo-blanco.png'
import styles from './Brand.module.css'

/**
 * Logos de marca (docs/CAMBIOS_WEB_MARCA.md W7, docs/MARCA_DENT-IA.md).
 *
 * - DENT-IA es la marca del PRODUCTO (logo oficial en src/assets/brand/, el mismo
 *   que usa la app movil en mobile/assets/brand/).
 * - Cada clinica puede subir su propio logo en Configuracion -> Apariencia; se sirve
 *   en GET /branding/logo (siempre responde algo: el propio o el de DENT-IA, W2).
 * - En modo oscuro (branding.dark_mode) se usa la version blanca del logo DENT-IA.
 */

function useDarkMode(): boolean {
  return useThemeStore((s) => s.branding?.dark_mode ?? false)
}

export function DentiaLogo({ width = 220 }: { width?: number }) {
  const dark = useDarkMode()
  // Proporcion del logo completo: 667 x 468
  return (
    <img
      className={styles.logo}
      src={dark ? logoWhite : logoColor}
      width={width}
      height={Math.round(width * (468 / 667))}
      alt="DENT-IA · Sistema Inteligente de Gestión Odontológica"
    />
  )
}

/** Isotipo solo (diente con circuitos), para usos pequeños como "con tecnologia". */
export function DentiaIsotipo({ size = 20 }: { size?: number }) {
  const dark = useDarkMode()
  return (
    <img
      className={styles.isotipo}
      src={dark ? isotipoWhite : isotipoColor}
      width={size}
      height={size}
      alt=""
    />
  )
}

/** Logo de la clinica si subio uno propio; si no, el logo DENT-IA. */
export function ClinicLogo({
  logoUrl,
  hasCustomLogo,
  clinicName,
  width = 220,
}: {
  logoUrl: string | null
  hasCustomLogo: boolean
  clinicName: string
  width?: number
}) {
  if (hasCustomLogo && logoUrl) {
    return (
      <img
        className={styles.logo}
        src={resolveApiAssetUrl(logoUrl)}
        width={width}
        alt={`Logo de ${clinicName}`}
      />
    )
  }
  return <DentiaLogo width={width} />
}

/** "con tecnologia DENT-IA": visible cuando la clinica usa su propia marca. */
export function PoweredByDentia() {
  const dark = useDarkMode()
  return (
    <p className={styles.poweredBy} aria-label="Con tecnología DENT-IA">
      <span>con tecnología</span>
      <DentiaIsotipo size={16} />
      <span className={dark ? styles.poweredByNameDark : styles.poweredByName}>DENT-IA</span>
    </p>
  )
}

/** Franja de 4px con el degradado del logo (cian -> azul), arriba de la tarjeta de login. */
export function BrandStripe() {
  return <div className={styles.stripe} aria-hidden="true" />
}
