import { describe, expect, it } from 'vitest'
import { voiceWebSocketUrl } from './connection'

describe('voiceWebSocketUrl', () => {
  it('convierte el origen http(s) de la API a ws(s)', () => {
    const url = voiceWebSocketUrl()
    expect(url).toMatch(/^ws:\/\//)
    expect(url).toMatch(/\/voice\/ws$/)
  })
})
