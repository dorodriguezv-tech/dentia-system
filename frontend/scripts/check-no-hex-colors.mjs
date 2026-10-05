#!/usr/bin/env node
// CLAUDE.md sec. 6: "El frontend no lleva colores fijos: usa siempre var(--color-...)".
// Busca literales de color hex fuera de src/theme/ (donde SI deben vivir, como valores
// por defecto y catalogo de presets) y fuera de las pruebas (que validan formulas de
// color con valores concretos a proposito).

import { readdirSync, readFileSync, statSync } from 'node:fs'
import { extname, join, relative, sep } from 'node:path'

const ROOT = new URL('..', import.meta.url).pathname.replace(/^\/([a-zA-Z]:)/, '$1')
const SRC_DIR = join(ROOT, 'src')
const SCANNED_EXTENSIONS = new Set(['.ts', '.tsx', '.css'])
const EXCLUDED_DIR_SEGMENTS = new Set(['theme'])
const HEX_COLOR_PATTERN = /#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b/g

function isExcluded(path) {
  const parts = relative(SRC_DIR, path).split(sep)
  return parts.some((part) => EXCLUDED_DIR_SEGMENTS.has(part)) || /\.test\.(ts|tsx)$/.test(path)
}

function walk(dir, found) {
  for (const entry of readdirSync(dir)) {
    const fullPath = join(dir, entry)
    const stats = statSync(fullPath)
    if (stats.isDirectory()) {
      walk(fullPath, found)
      continue
    }
    if (!SCANNED_EXTENSIONS.has(extname(fullPath)) || isExcluded(fullPath)) continue

    const content = readFileSync(fullPath, 'utf8')
    const matches = content.match(HEX_COLOR_PATTERN)
    if (matches) {
      found.push({ file: relative(ROOT, fullPath), matches })
    }
  }
}

const found = []
walk(SRC_DIR, found)

if (found.length > 0) {
  console.error('Colores fijos (#hex) fuera de src/theme/:\n')
  for (const { file, matches } of found) {
    console.error(`  ${file}: ${matches.join(', ')}`)
  }
  console.error('\nUsa var(--color-...) en su lugar (CLAUDE.md sec. 6).')
  process.exit(1)
}

console.log('OK: ningun color fijo fuera de src/theme/.')
