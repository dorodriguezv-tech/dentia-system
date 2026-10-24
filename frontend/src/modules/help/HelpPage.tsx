import styles from './HelpPage.module.css'

const SECTIONS = [
  { id: 'roles', label: 'Que hace cada usuario' },
  { id: 'entrar', label: '1. Entrar al sistema' },
  { id: 'tablero', label: '2. Tablero de inicio' },
  { id: 'buscar', label: '3. Buscar un paciente' },
  { id: 'pacientes', label: '4. Pacientes' },
  { id: 'atender', label: '5. Atender a un paciente' },
  { id: 'agenda', label: '6. Agenda' },
  { id: 'caja', label: '7. Caja y cobranza' },
  { id: 'ia-voz', label: '8. Asistente de IA por voz' },
  { id: 'reportes', label: '9. Reportes' },
  { id: 'catalogos', label: '10. Catalogos' },
  { id: 'horarios', label: '11. Horarios' },
  { id: 'apariencia', label: '12. Apariencia' },
  { id: 'dentia', label: '13. Dentia (orbe de voz)' },
  { id: 'faq', label: '14. Preguntas frecuentes' },
]

export function HelpPage() {
  return (
    <section>
      <h1>Ayuda</h1>
      <div className={styles.layout}>
        <nav className={styles.toc} aria-label="Indice de ayuda">
          <h2>Contenido</h2>
          <ul>
            {SECTIONS.map((s) => (
              <li key={s.id}>
                <a href={`#${s.id}`}>{s.label}</a>
              </li>
            ))}
          </ul>
        </nav>

        <div className={styles.content}>
          <section id="roles">
            <h2>Que hace cada usuario</h2>
            <p>
              Lo que ves en el sistema depende de tu rol: el menu de la izquierda, el
              tablero de inicio y los botones disponibles cambian solos segun lo que tu
              rol puede hacer. Esto es lo que hace cada uno:
            </p>
            <div className={styles.roleBox}>
              <h4>Administrador de la clinica</h4>
              <p>
                Gestiona usuarios (altas, roles), catalogos, apariencia, horarios,
                cobranza y reportes. Da de alta y edita pacientes. <strong>No ve el
                expediente clinico</strong> (notas, odontograma) ni cobra directamente
                en caja — esa separacion es intencional.
              </p>
            </div>
            <div className={styles.roleBox}>
              <h4>Odontologo / Especialista</h4>
              <p>
                El flujo clinico completo: dar de alta pacientes, expediente, nota SOAP,
                odontograma, diagnosticos, planes de tratamiento, documentos y
                consentimientos, y su propia agenda. No ve cobranza ni administra
                usuarios o catalogos.
              </p>
            </div>
            <div className={styles.roleBox}>
              <h4>Asistente dental</h4>
              <p>
                Ve pacientes y el odontograma, sube imagenes/radiografias, y consulta la
                agenda. No edita el expediente ni da de alta pacientes.
              </p>
            </div>
            <div className={styles.roleBox}>
              <h4>Recepcion</h4>
              <p>
                Da de alta y edita pacientes, administra la agenda (crear, confirmar,
                reprogramar citas). Solo puede <strong>ver</strong> la cobranza, no
                cobrar.
              </p>
            </div>
            <div className={styles.roleBox}>
              <h4>Caja</h4>
              <p>
                Abre y cierra sesiones de caja, registra cargos y pagos, emite recibos,
                y ve reportes. No tiene acceso al expediente clinico.
              </p>
            </div>
            <p className={styles.note}>
              Si crees que deberias ver algo y no aparece, pide a un administrador de la
              clinica que revise tu rol — la lista tecnica completa, permiso por
              permiso, esta en <code>docs/MATRIZ_PERMISOS.md</code> del proyecto.
            </p>
          </section>

          <section id="entrar">
            <h2>1. Entrar al sistema</h2>
            <p>
              Abre la direccion que te de tu clinica. Escribe tu correo y contrasena y
              presiona <strong>Entrar</strong>.
            </p>
            <img src="/manual/01-login.png" alt="Pantalla de login" />
            <p>
              Si olvidaste tu contrasena, pide a un <strong>administrador de la
              clinica</strong> que te cree una cuenta nueva desde Usuarios — todavia no
              hay un flujo de "olvide mi contrasena" por correo.
            </p>
          </section>

          <section id="tablero">
            <h2>2. El tablero de inicio</h2>
            <p>
              Al entrar ves tu tablero de inicio, distinto segun tu rol: cada tarjeta
              (Pacientes, Agenda de hoy, Tratamientos, Cobranza) solo aparece si tu rol
              puede ver esa informacion.
            </p>
            <img src="/manual/02-tablero.png" alt="Tablero de inicio" />
            <p>
              El menu de la izquierda tambien cambia segun tu rol. El logo (o nombre) de
              la clinica, arriba a la izquierda, es un enlace a este tablero desde
              cualquier pantalla.
            </p>
          </section>

          <section id="buscar">
            <h2>3. Buscar un paciente</h2>
            <p>
              Desde cualquier pantalla, presiona <strong>Ctrl+K</strong> (o haz clic en
              "Buscar paciente...") para abrir la busqueda rapida: por nombre, telefono,
              correo o numero de expediente, aunque escribas con errores o sin acentos.
            </p>
          </section>

          <section id="pacientes">
            <h2>4. Pacientes</h2>
            <h3>4.1 Listado y alta de un paciente nuevo</h3>
            <p>
              Si tu rol puede dar de alta pacientes, veras el boton{' '}
              <strong>Nuevo paciente</strong>. Si eres odontologo o especialista, ademas
              veras la casilla <strong>Mis pacientes</strong>.
            </p>
            <img src="/manual/04-pacientes.png" alt="Listado de pacientes" />
            <p>Dar de alta a un paciente tiene 3 pasos:</p>
            <ol>
              <li>
                <strong>Datos</strong> — nombre, apellidos y fecha de nacimiento son
                obligatorios; el resto es opcional.
              </li>
              <li>
                <strong>Posibles duplicados</strong> — si ya existe alguien parecido
                (mismo nombre y fecha de nacimiento o telefono), el sistema te avisa
                antes de seguir.
              </li>
              <li>
                <strong>Contactos</strong> — un tutor o contacto de emergencia (opcional).
              </li>
            </ol>
            <h3>4.2 La ficha del paciente</h3>
            <p>
              El encabezado (nombre, edad, expediente, alertas criticas en rojo) siempre
              esta visible sin importar la pestana en la que estes.
            </p>
            <img src="/manual/05-paciente-resumen.png" alt="Resumen del paciente" />
            <p>Pestanas: Resumen, Expediente, Odontograma, Tratamientos, Consentimientos, Imagenes, y Cuenta (solo con acceso a cobranza).</p>
          </section>

          <section id="atender">
            <h2>5. Atender a un paciente</h2>
            <h3>5.1 Expediente</h3>
            <img src="/manual/06-paciente-expediente.png" alt="Expediente del paciente" />
            <p>
              Cada seccion (antecedentes, alergias, medicamentos, signos vitales) se liga
              a una atencion concreta. Cualquier alergia activa, y ciertas palabras clave
              en medicamentos o antecedentes, generan una alerta critica que{' '}
              <strong>siempre</strong> se muestra antes de finalizar una nota o registrar
              un procedimiento.
            </p>
            <h3>5.2 La nota clinica (SOAP)</h3>
            <p>Estados de una nota: Borrador (editable) → Finalizada (congelada, ya no se edita) → Corregida (si hubo un error, se crea una version nueva sin perder la original) o Cancelada (con motivo).</p>
            <h3>5.3 Odontograma</h3>
            <img src="/manual/07-odontograma.png" alt="Odontograma" />
            <p>
              Notacion FDI (cuadrante + posicion). Haz clic en una superficie para
              registrar un hallazgo. Tres vistas: Permanente, Temporal, Mixta. "Historial
              a fecha" reconstruye como se veia el odontograma en el pasado.
            </p>
            <h3>5.4 Diagnostico y plan de tratamiento</h3>
            <img src="/manual/08-tratamientos.png" alt="Planes de tratamiento" />
            <p>
              Flujo: crear el plan con sus procedimientos → presentarlo al paciente
              (genera un PDF) → el paciente acepta (no es un pago todavia) → al
              realizarse, genera un cargo para cobranza. Lo planificado y lo realizado
              son siempre cosas separadas.
            </p>
            <h3>5.5 Consentimientos</h3>
            <p>
              El paciente firma en pantalla sobre una plantilla configurable. Al firmar
              se genera un PDF que ya no se puede modificar.
            </p>
            <h3>5.6 Imagenes y radiografias</h3>
            <p>Subir fotos/radiografias; el visor permite zoom y ajustar brillo/contraste sin tocar el archivo original.</p>
          </section>

          <section id="agenda">
            <h2>6. Agenda</h2>
            <img src="/manual/03-agenda.png" alt="Agenda" />
            <p>
              Vista por dia, semana o mes; agrupar por profesional o gabinete. Para
              agendar: clic en un espacio libre, buscar al paciente y confirmar.
              Arrastrar una cita la reprograma (la anterior queda marcada
              "Reprogramada", no se pierde el historial).
            </p>
          </section>

          <section id="caja">
            <h2>7. Caja y cobranza</h2>
            <img src="/manual/09-cuenta.png" alt="Cuenta de un paciente" />
            <p>
              La pestana "Cuenta" de un paciente muestra cargos y pagos. Un pago puede
              ser efectivo, tarjeta o transferencia, y aplicarse completo, repartido o
              como anticipo. La pantalla "Caja" abre/cierra una sesion de cobro (turno).
            </p>
          </section>

          <section id="ia-voz">
            <h2>8. Asistente de IA por voz</h2>
            <p>
              En la pantalla de Atencion, el microfono (<code>Alt+M</code>) transcribe tu
              dictado en el propio equipo y propone acciones. <strong>Nunca guarda nada
              por si solo</strong>: cada propuesta se acepta, se edita y acepta, o se
              rechaza, una por una.
            </p>
          </section>

          <section id="reportes">
            <h2>9. Reportes</h2>
            <img src="/manual/10-reportes.png" alt="Reportes" />
            <p>
              Seis reportes de solo lectura con exportacion a CSV: pacientes, citas,
              produccion por profesional, planes de tratamiento, cuentas por cobrar y
              uso del asistente de IA.
            </p>
          </section>

          <section id="catalogos">
            <h2>10. Configuracion → Catalogos</h2>
            <p>
              Solo para administradores. Aqui se administran, por sucursal, los tipos de
              cita, hallazgos del odontograma, diagnosticos, categorias de antecedentes,
              palabras clave de alerta, procedimientos y precios, gabinetes, y los datos
              de la propia sucursal.
            </p>
            <p>
              Un elemento nuevo queda disponible de inmediato. Desactivar no borra: deja
              de ofrecerse para elegir, pero los registros que ya lo usaron lo siguen
              mostrando igual.
            </p>
          </section>

          <section id="horarios">
            <h2>11. Configuracion → Horarios</h2>
            <p>
              Solo para administradores. Define en que dias y horas aparece cada
              profesional como disponible en la Agenda — es informativo (sombrea el
              calendario) pero <strong>no bloquea</strong> agendar fuera de esas horas.
              El boton "Horario abierto toda la semana" deja a un profesional
              disponible las 24 horas, los 7 dias, de un solo clic.
            </p>
          </section>

          <section id="apariencia">
            <h2>12. Configuracion → Apariencia</h2>
            <p>
              Solo para administradores. Cambia el nombre comercial, subtitulo, logo,
              colores, modo oscuro y radio de bordes de tu clinica. Al subir tu propio
              logo, el logo de DENT-IA no desaparece: queda como "con tecnologia
              DENT-IA" al pie del menu lateral y en el login.
            </p>
          </section>

          <section id="dentia">
            <h2>13. Dentia (el orbe de voz)</h2>
            <p>
              Si tu rol es odontologo, especialista o recepcion, veras un circulo en la
              esquina inferior derecha. Dile <strong>"Dentia"</strong> para activarla:
              puede navegar por el sistema, iniciar una consulta, dictar hallazgos del
              odontograma, registrar diagnosticos y procedimientos, y (para recepcion)
              agendar, confirmar, reprogramar o cancelar citas por voz. Siempre pide
              confirmar con un "si" antes de aplicar un cambio.
            </p>
          </section>

          <section id="faq">
            <h2>14. Preguntas frecuentes</h2>
            <dl className={styles.faq}>
              <dt>¿Por que no puedo editar una nota que ya finalice?</dt>
              <dd>
                Es una regla del sistema: una nota finalizada no se modifica. Usa
                "Corregir" — crea una version nueva con el motivo, sin perder la
                original.
              </dd>
              <dt>¿Por que no veo el boton para dar de alta un paciente / registrar un pago?</dt>
              <dd>Depende de tu rol. Pide a un administrador que revise tus permisos.</dd>
              <dt>Acepte una propuesta de la IA por error. ¿Puedo deshacerla?</dt>
              <dd>
                No hay boton "deshacer": corrige el dato manualmente donde haya quedado,
                igual que corregirias un error propio.
              </dd>
              <dt>El asistente de IA no responde.</dt>
              <dd>
                Revisa con quien administre el sistema si el servicio de IA local esta
                encendido (Configuracion → Asistente IA). Mientras tanto, puedes seguir
                escribiendo el texto libre a mano en la nota.
              </dd>
            </dl>
          </section>
        </div>
      </div>
    </section>
  )
}
