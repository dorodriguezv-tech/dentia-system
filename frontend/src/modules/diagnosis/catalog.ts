import type { DiagnosisCode } from './types'

/**
 * Copia minima, solo para la interfaz, de backend/app/modules/diagnosis/rules.py
 * (fuente de verdad real). El texto de cada diagnostico siempre es libre; este
 * catalogo solo ofrece un selector rapido de codigo + etiqueta.
 */
export const DIAGNOSIS_CATALOG: Record<DiagnosisCode, string> = {
  caries: 'Caries dental',
  caries_recurrente: 'Caries recurrente',
  pulpitis_reversible: 'Pulpitis reversible',
  pulpitis_irreversible: 'Pulpitis irreversible',
  necrosis_pulpar: 'Necrosis pulpar',
  absceso_periapical: 'Absceso periapical',
  gingivitis: 'Gingivitis',
  periodontitis: 'Periodontitis',
  fractura_dental: 'Fractura dental',
  edentulismo_parcial: 'Edentulismo parcial',
  maloclusion: 'Maloclusion',
  sin_hallazgos: 'Sin hallazgos patologicos',
}

export const DIAGNOSIS_CODES = Object.keys(DIAGNOSIS_CATALOG) as DiagnosisCode[]
