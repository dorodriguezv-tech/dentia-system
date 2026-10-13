import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useState } from 'react';
import { Alert, KeyboardAvoidingView, Linking, Modal, Platform, Pressable, TextInput, View } from 'react-native';

import { errorMessage } from '@/api/client';
import { getPatient, setAppointmentStatus } from '@/api/endpoints';
import type { Appointment } from '@/api/types';
import { canTransition, isEditable } from '@/agenda/rules';
import { Body, Button, ErrorBox, Row, Title } from '@/components/ui';
import { telUrl, whatsappUrl } from '@/contact/links';
import { hasPermission } from '@/store/session';
import { useTheme } from '@/theme/theme';

function openOrWarn(url: string, failureMessage: string) {
  void Linking.openURL(url).catch(() => Alert.alert('No se pudo abrir', failureMessage));
}

/** M3 (docs/06_APP_MOVIL_V1_1_PARIDAD.md §3, R1): acciones de una cita más allá de
 * "Llegó"/"Iniciar atención" (ya en la tarjeta de la agenda) — solo se muestran las
 * transiciones válidas según la máquina de estados (src/agenda/rules.ts, copiada de
 * backend/app/modules/agenda/rules.py). Llamar/WhatsApp están siempre disponibles si
 * el paciente tiene teléfono, sin importar el permiso (no son una acción clínica). */
export function AppointmentActionsSheet({
  appointment,
  onClose,
}: {
  appointment: Appointment | null;
  onClose: () => void;
}) {
  const t = useTheme();
  const qc = useQueryClient();
  const visible = !!appointment;
  const [showCancelReason, setShowCancelReason] = useState(false);
  const [cancelReason, setCancelReason] = useState('');

  const patient = useQuery({
    queryKey: ['patient-phone', appointment?.patient_id],
    queryFn: () => getPatient(appointment!.patient_id),
    enabled: visible,
  });

  const changeStatus = useMutation({
    mutationFn: (vars: { status: Appointment['status']; reason?: string }) =>
      setAppointmentStatus(appointment!.id, vars.status, vars.reason),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['appointments'] });
      close();
    },
  });

  function close() {
    setShowCancelReason(false);
    setCancelReason('');
    onClose();
  }

  if (!appointment) return null;
  const canWrite = hasPermission('agenda.write');
  const phone = patient.data?.phone ?? null;

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={close}>
      <Pressable style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.35)' }} onPress={close} accessibilityLabel="Cerrar" />
      {/* Un Modal de RN en Android no ajusta su tamaño cuando aparece el teclado
          (limitación conocida, a diferencia de la actividad principal): sin esto,
          el teclado tapaba el campo de motivo. */}
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
      <View style={{ backgroundColor: t.colors.surface, padding: 16, gap: 10, borderTopLeftRadius: 16, borderTopRightRadius: 16 }}>
        <Title>{appointment.patient_full_name}</Title>

        {changeStatus.error ? <ErrorBox message={errorMessage(changeStatus.error)} /> : null}

        {canWrite && canTransition(appointment.status, 'CONFIRMADA') ? (
          <Button title="Confirmar" variant="secondary" onPress={() => changeStatus.mutate({ status: 'CONFIRMADA' })} loading={changeStatus.isPending} />
        ) : null}

        {canWrite && isEditable(appointment.status) ? (
          <Button
            title="Reprogramar"
            variant="secondary"
            onPress={() => {
              close();
              router.push({
                pathname: '/cita/reprogramar',
                params: {
                  id: appointment.id,
                  patientName: appointment.patient_full_name,
                  providerId: appointment.provider_id,
                  startsAt: appointment.starts_at,
                  endsAt: appointment.ends_at,
                },
              });
            }}
          />
        ) : null}

        {canWrite && canTransition(appointment.status, 'NO_SHOW') ? (
          <Button
            title="No asistió"
            variant="ghost"
            onPress={() => changeStatus.mutate({ status: 'NO_SHOW', reason: 'No se presentó' })}
            loading={changeStatus.isPending}
          />
        ) : null}

        {canWrite && canTransition(appointment.status, 'CANCELADA') ? (
          showCancelReason ? (
            <View style={{ gap: 8 }}>
              <Body style={{ fontWeight: '700' }}>Motivo de la cancelación</Body>
              <TextInput
                value={cancelReason}
                onChangeText={setCancelReason}
                placeholder="Obligatorio"
                placeholderTextColor={t.colors.textMuted}
                accessibilityLabel="Motivo de la cancelación"
                style={{ minHeight: 48, borderWidth: 1, borderColor: t.colors.border, borderRadius: t.radius, paddingHorizontal: 12, color: t.colors.text, fontSize: 16 }}
              />
              <Row>
                <Button
                  title="Confirmar cancelación"
                  variant="danger"
                  disabled={!cancelReason.trim()}
                  loading={changeStatus.isPending}
                  onPress={() => changeStatus.mutate({ status: 'CANCELADA', reason: cancelReason.trim() })}
                />
                <Button title="Ya no" variant="ghost" onPress={() => setShowCancelReason(false)} />
              </Row>
            </View>
          ) : (
            <Button title="Cancelar cita" variant="danger" onPress={() => setShowCancelReason(true)} />
          )
        ) : null}

        {phone ? (
          <Row>
            <Button title="Llamar" variant="secondary" onPress={() => openOrWarn(telUrl(phone), 'Verifica que el teléfono del paciente sea correcto.')} />
            <Button
              title="WhatsApp"
              variant="secondary"
              onPress={() => openOrWarn(whatsappUrl(phone), 'Verifica que WhatsApp esté instalado y que el teléfono del paciente sea correcto.')}
            />
          </Row>
        ) : null}

        <Button title="Cerrar" variant="ghost" onPress={close} />
      </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}
