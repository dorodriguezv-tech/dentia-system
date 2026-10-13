import { telUrl, toWhatsAppDigits, whatsappUrl } from './links';

describe('toWhatsAppDigits', () => {
  it('antepone 52 a un número local de México (10 dígitos)', () => {
    expect(toWhatsAppDigits('5512345678')).toBe('525512345678');
  });

  it('respeta un número que ya trae código de país', () => {
    expect(toWhatsAppDigits('525512345678')).toBe('525512345678');
  });

  it('quita espacios, guiones y paréntesis antes de decidir', () => {
    expect(toWhatsAppDigits('55 1234-5678')).toBe('525512345678');
    expect(toWhatsAppDigits('(55) 1234 5678')).toBe('525512345678');
  });

  it('un número que ya trae "+" y país no se altera más allá de quitar el +', () => {
    expect(toWhatsAppDigits('+52 55 1234 5678')).toBe('525512345678');
  });
});

describe('whatsappUrl / telUrl', () => {
  it('whatsappUrl usa el número normalizado con código de país', () => {
    expect(whatsappUrl('5512345678')).toBe('https://wa.me/525512345678');
  });

  it('telUrl conserva el "+" si lo trae, pero quita espacios y guiones', () => {
    expect(telUrl('+52 55 1234 5678')).toBe('tel:+525512345678');
    expect(telUrl('55-1234-5678')).toBe('tel:5512345678');
  });
});
