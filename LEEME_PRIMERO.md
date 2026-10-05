# Kit de construcción — Sistema Clínico Dental con IA local

## Contenido
| Archivo | Para qué |
|---|---|
| `CLAUDE.md` | Reglas permanentes que Claude Code lee automáticamente (stack, reglas clínicas, convenciones) |
| `docs/01_ANALISIS_Y_DECISIONES.md` | Análisis de tus 3 documentos y decisiones tomadas |
| `docs/02_ARQUITECTURA.md` | Modelo de datos, API y pantallas |
| `docs/03_AGENTE_IA_VOZ.md` | Diseño del asistente que escucha al odontólogo |
| `docs/04_TEMAS_Y_MARCA.md` | Colores y logo configurables |
| `prompts/PROMPTS_CLAUDE_CODE.md` | 13 prompts en orden (Fase 0 a 12) para pegar en Claude Code |
| `docs/PENDIENTES_CLINICOS.md` | Lista de decisiones a validar con el odontólogo |

## 1. Instala en el equipo
1. **Git**
2. **Python 3.12** (marca “Add to PATH” en Windows)
3. **Node.js 20 LTS** o superior
4. **PostgreSQL 16** (instalador nativo o Docker Desktop)
5. **Visual Studio Code**
6. **Ollama**: https://ollama.com. Después, en una terminal:
   ```
   ollama pull qwen2.5:7b
   ```
   Si el equipo tiene poca memoria (menos de 16 GB de RAM y sin GPU), usa `qwen2.5:3b`.
7. **Claude Code**: sigue la guía oficial en https://docs.claude.com (sección Claude Code).

Requisitos orientativos del equipo para la IA: 16 GB de RAM recomendados. Una GPU NVIDIA acelera mucho Whisper y Ollama, pero no es obligatoria.

## 2. Arranca
1. Crea una carpeta `dental-clinic`, copia dentro **todo** el contenido de este kit y ábrela en VS Code.
2. Abre la terminal de VS Code y ejecuta `claude`.
3. Pega el prompt de la **FASE 0**. Revisa el resultado y haz commit.
4. Repite con las fases 1 a 12. Ejecuta `/clear` entre fases.

## 3. Recomendaciones
- No uses datos reales de pacientes mientras desarrollas.
- Valida con el odontólogo, antes de la Fase 5, los estados del odontograma; antes de la Fase 8, sus frases típicas de dictado.
- Revisión jurídica (NOM-004, NOM-024, LFPDPPP 2025) antes de usar el sistema con pacientes reales.
