import { buildNotePrefill } from './notePrefill';
import type { AiSuggestion, ProcedurePerformedSummary, ToothFinding } from '@/api/types';

const ENCOUNTER_ID = 'enc-1';
const describeSuggestion = (s: AiSuggestion) => `sugerencia:${s.action_type}`;

describe('buildNotePrefill (M6: nota prellenada con lo hecho hoy)', () => {
  it('usa el motivo de la cita como S', () => {
    const { soapS } = buildNotePrefill({
      encounterId: ENCOUNTER_ID,
      chiefComplaint: 'Dolor al masticar',
      findings: [],
      proceduresPerformed: [],
      suggestions: [],
      describeSuggestion,
    });
    expect(soapS).toBe('Dolor al masticar');
  });

  it('sin motivo capturado, S queda vacío (no "undefined" ni "null")', () => {
    const { soapS } = buildNotePrefill({
      encounterId: ENCOUNTER_ID,
      chiefComplaint: null,
      findings: [],
      proceduresPerformed: [],
      suggestions: [],
      describeSuggestion,
    });
    expect(soapS).toBe('');
  });

  it('incluye en O solo los hallazgos de ESTA atención, no de otras', () => {
    const findings: ToothFinding[] = [
      { id: 'f1', encounter_id: ENCOUNTER_ID, tooth_fdi: 36, surface: 'O', finding_code: 'caries', kind: 'EXISTING', origin: 'MANUAL', created_at: '2026-01-01' },
      { id: 'f2', encounter_id: 'otra-atencion', tooth_fdi: 11, surface: null, finding_code: 'ausente', kind: 'EXISTING', origin: 'MANUAL', created_at: '2026-01-01' },
    ];
    const { soapO } = buildNotePrefill({
      encounterId: ENCOUNTER_ID,
      chiefComplaint: null,
      findings,
      proceduresPerformed: [],
      suggestions: [],
      describeSuggestion,
    });
    expect(soapO).toContain('Pieza 36 O: caries');
    expect(soapO).not.toContain('11');
  });

  it('incluye los procedimientos realizados hoy en esta atención', () => {
    const procs: ProcedurePerformedSummary[] = [
      { id: 'p1', encounter_id: ENCOUNTER_ID, tooth_fdi: 36, surface: 'O', procedure_name: 'Resina' },
      { id: 'p2', encounter_id: 'otra-atencion', tooth_fdi: null, surface: null, procedure_name: 'Limpieza' },
    ];
    const { soapO } = buildNotePrefill({
      encounterId: ENCOUNTER_ID,
      chiefComplaint: null,
      findings: [],
      proceduresPerformed: procs,
      suggestions: [],
      describeSuggestion,
    });
    expect(soapO).toContain('Procedimiento realizado: Resina en pieza 36');
    expect(soapO).not.toContain('Limpieza');
  });

  it('incluye solo las propuestas de IA ACEPTADAS, no las pendientes ni rechazadas', () => {
    const suggestions: AiSuggestion[] = [
      { id: 's1', batch_id: 'b1', action_type: 'add_diagnosis', payload: {}, status: 'ACCEPTED' },
      { id: 's2', batch_id: 'b1', action_type: 'add_allergy', payload: {}, status: 'PENDING' },
      { id: 's3', batch_id: 'b1', action_type: 'add_medication', payload: {}, status: 'REJECTED' },
    ];
    const { soapO } = buildNotePrefill({
      encounterId: ENCOUNTER_ID,
      chiefComplaint: null,
      findings: [],
      proceduresPerformed: [],
      suggestions,
      describeSuggestion,
    });
    expect(soapO).toBe('- (IA aceptada) sugerencia:add_diagnosis');
  });

  it('sin nada que prellenar, O queda como cadena vacía', () => {
    const { soapO } = buildNotePrefill({
      encounterId: ENCOUNTER_ID,
      chiefComplaint: null,
      findings: [],
      proceduresPerformed: [],
      suggestions: [],
      describeSuggestion,
    });
    expect(soapO).toBe('');
  });
});
