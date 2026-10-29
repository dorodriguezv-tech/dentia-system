import type { SignerRelationship, TemplateCategory, TemplateCode } from './types'

/**
 * Copia minima, solo para la interfaz, del catalogo de
 * backend/app/modules/documents/rules.py (fuente de verdad real: TEMPLATE_CODES,
 * TEMPLATE_CATEGORIES, TEMPLATE_CATEGORY_LABELS). Los 24 formatos oficiales de
 * docs/formatos (ver plan aprobado), agrupados para el selector en 3 categorias.
 */
export const TEMPLATE_CODE_LABELS: Record<TemplateCode, string> = {
  protesis_fija: 'Prótesis fija',
  aplicacion_fluor: 'Aplicación de flúor',
  anestesia_local_oral: 'Aplicación de anestesia local oral',
  exodoncia: 'Exodoncia simple / cirugía de extracción dental',
  incrustacion_dental: 'Incrustación dental',
  obturacion_dental: 'Obturación dental (resina y/o amalgama)',
  endodoncia: 'Procedimiento endodóntico',
  protesis_removible: 'Prótesis removible',
  sellado_fosetas_fisuras: 'Sellado de fosetas y fisuras',
  toma_radiografias: 'Toma de radiografías',
  limpieza_dental: 'Limpieza dental y/o eliminación de sarro',
  aplicacion_fluor_pediatrico: 'Aplicación de flúor (paciente pediátrico)',
  anestesia_local_pediatrico: 'Colocación de anestesia local (paciente pediátrico)',
  corona_metalica_pediatrico: 'Colocación de corona metálica y/o estética (paciente pediátrico)',
  sellado_fosetas_pediatrico: 'Colocación de sellador de fosetas y fisuras (paciente pediátrico)',
  obturacion_resina_pediatrico: 'Obturación con resina (paciente pediátrico)',
  profilaxis_pediatrico: 'Profilaxis (paciente pediátrico)',
  toma_radiografias_pediatrico: 'Toma de radiografías (paciente pediátrico)',
  tratamiento_pulpar_pediatrico:
    'Tratamiento pulpar: pulpotomía o pulpectomía (paciente pediátrico)',
  aviso_privacidad: 'Aviso de privacidad',
  carta_tratamiento_concluido: 'Carta de aceptación de tratamiento concluido',
  carta_tratamiento_suspendido: 'Carta de suspensión de tratamiento',
  carta_autorizacion_uso_imagen: 'Carta de autorización de uso de imagen',
  carta_caso_medico_legal: 'Carta de notificación de caso médico legal',
}

export const TEMPLATE_CODES = Object.keys(TEMPLATE_CODE_LABELS) as TemplateCode[]

export const TEMPLATE_CATEGORY_LABELS: Record<TemplateCategory, string> = {
  consentimiento: 'Consentimientos informados',
  aviso_privacidad: 'Avisos de privacidad',
  carta: 'Cartas',
}

const PEDIATRIC_SUFFIX = '_pediatrico'
const CARTA_PREFIX = 'carta_'

export function categoryForTemplateCode(code: TemplateCode): TemplateCategory {
  if (code === 'aviso_privacidad') return 'aviso_privacidad'
  if (code.startsWith(CARTA_PREFIX)) return 'carta'
  return 'consentimiento'
}

export const TEMPLATE_CODES_BY_CATEGORY: Record<TemplateCategory, TemplateCode[]> = (() => {
  const grouped: Record<TemplateCategory, TemplateCode[]> = {
    consentimiento: [],
    aviso_privacidad: [],
    carta: [],
  }
  for (const code of TEMPLATE_CODES) {
    grouped[categoryForTemplateCode(code)].push(code)
  }
  return grouped
})()

export function isPediatricTemplateCode(code: TemplateCode): boolean {
  return code.endsWith(PEDIATRIC_SUFFIX)
}

export const SIGNER_RELATIONSHIP_LABELS: Record<SignerRelationship, string> = {
  paciente: 'Paciente',
  tutor: 'Tutor',
  otro: 'Otro',
}
