/**
 * Enlaces de "Llamar"/"WhatsApp" (M3/M4, docs/06_APP_MOVIL_V1_1_PARIDAD.md §3).
 * Pura (sin React Native) para poder probarla.
 *
 * wa.me exige el formato internacional completo. Un teléfono capturado como
 * number local de México (10 dígitos, sin "52" al inicio) no abre el chat
 * correcto en WhatsApp si se manda tal cual — bug real encontrado al probar
 * en un teléfono ("los permisos para WhatsApp no aparecen", en realidad el
 * enlace no abría nada reconocible).
 */
export function toWhatsAppDigits(phone: string): string {
  const digits = phone.replace(/\D/g, '');
  if (digits.length === 10) return `52${digits}`;
  return digits;
}

export function whatsappUrl(phone: string): string {
  return `https://wa.me/${toWhatsAppDigits(phone)}`;
}

export function telUrl(phone: string): string {
  return `tel:${phone.replace(/[^\d+]/g, '')}`;
}
