import '@testing-library/jest-dom/vitest'

// jsdom no implementa ResizeObserver (lo usa SignaturePad para ajustar el canvas
// a su tamano real en pantalla).
if (typeof globalThis.ResizeObserver === 'undefined') {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
}
