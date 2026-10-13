import type { AiSuggestion, ProcedurePerformedSummary, ToothFinding } from '@/api/types';

/**
 * M6 (docs/06_APP_MOVIL_V1_1_PARIDAD.md §3): "Nota de consulta prellenada con lo
 * hecho hoy: motivo, hallazgos nuevos, procedimientos realizados, propuestas IA
 * aceptadas." Pura (sin React Native) para poder probarla sin montar la pantalla.
 */
export function buildNotePrefill(args: {
  encounterId: string;
  chiefComplaint: string | null | undefined;
  findings: ToothFinding[];
  proceduresPerformed: ProcedurePerformedSummary[];
  suggestions: AiSuggestion[];
  describeSuggestion: (s: AiSuggestion) => string;
}): { soapS: string; soapO: string } {
  const newFindings = args.findings.filter((f) => f.encounter_id === args.encounterId);
  const performedToday = args.proceduresPerformed.filter((p) => p.encounter_id === args.encounterId);
  const accepted = args.suggestions.filter((s) => s.status === 'ACCEPTED');

  const oLines = [
    ...newFindings.map((f) => `- Pieza ${f.tooth_fdi}${f.surface ? ` ${f.surface}` : ''}: ${f.finding_code}`),
    ...performedToday.map((p) => `- Procedimiento realizado: ${p.procedure_name}${p.tooth_fdi ? ` en pieza ${p.tooth_fdi}` : ''}`),
    ...accepted.map((s) => `- (IA aceptada) ${args.describeSuggestion(s)}`),
  ];

  return { soapS: args.chiefComplaint ?? '', soapO: oLines.join('\n') };
}
