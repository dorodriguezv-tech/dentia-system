import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as agendaApi from '../agenda/api'
import type { ResourceOut } from '../agenda/types'
import * as authApi from '../auth/api'
import { useAuthStore } from '../auth/store'
import * as catalogsApi from './api'
import type { CatalogImportSummary, CatalogItemOut } from './types'
import * as treatmentApi from '../treatment/api'
import type { ProcedureCatalogOut } from '../treatment/types'
import styles from '../patients/PatientDetailPage.module.css'

/** B1 (Parte B, Fase 12.2): "Configuracion -> Catalogos". Antes, estos catalogos
 * vivian fijos en codigo (agenda/rules.py, odontogram/finding_catalog.py,
 * diagnosis/rules.py, records/rules.py): un administrador no podia agregar ni
 * desactivar un elemento sin pedir un cambio de codigo. Un solo componente
 * generico cubre los 6 catalogos del backend (app/modules/catalogs) -- cada uno
 * solo cambia en que campos "extra" tiene, mas importar/exportar por CSV.
 * "Procedimientos y precios" reutiliza su propia tabla (ya existia, Fase 7).
 * "Gabinetes" (`resources`) y "Sucursal" (datos basicos de la propia sucursal,
 * `clinics`) tienen su pestana propia -- ya eran sus propias tablas, solo les
 * faltaba el endpoint para editar/desactivar. */

interface ExtraFieldSpec {
  key: string
  label: string
  type: 'text' | 'number' | 'checkbox' | 'color'
}

interface CatalogTabSpec {
  key: string
  label: string
  extraFields: ExtraFieldSpec[]
}

const CATALOG_TABS: CatalogTabSpec[] = [
  {
    key: 'appointment_type',
    label: 'Tipos de consulta/cita',
    extraFields: [
      { key: 'default_minutes', label: 'Duracion por defecto (min)', type: 'number' },
      { key: 'color', label: 'Color', type: 'color' },
    ],
  },
  {
    key: 'odontogram_finding',
    label: 'Hallazgos del odontograma',
    extraFields: [
      { key: 'symbol', label: 'Simbolo', type: 'text' },
      { key: 'color', label: 'Color', type: 'color' },
      { key: 'requires_surface', label: 'Requiere superficie', type: 'checkbox' },
    ],
  },
  { key: 'diagnosis', label: 'Diagnosticos', extraFields: [] },
  { key: 'history_category', label: 'Categorias de antecedentes', extraFields: [] },
  {
    key: 'condition_alert_keyword',
    label: 'Palabras clave de alerta (antecedentes)',
    extraFields: [{ key: 'alert_label', label: 'Texto de la alerta', type: 'text' }],
  },
  {
    key: 'medication_alert_keyword',
    label: 'Palabras clave de alerta (medicamentos)',
    extraFields: [{ key: 'alert_label', label: 'Texto de la alerta', type: 'text' }],
  },
]

function extraFieldInputValue(spec: ExtraFieldSpec, raw: string): unknown {
  if (spec.type === 'number') return raw === '' ? undefined : Number(raw)
  if (spec.type === 'checkbox') return raw === 'true'
  return raw || undefined
}

function ExtraFieldValue({ spec, value }: { spec: ExtraFieldSpec; value: unknown }) {
  if (spec.type === 'checkbox') return <span>{value ? 'Si' : 'No'}</span>
  if (spec.type === 'color' && typeof value === 'string' && value) {
    return (
      <span>
        <span
          aria-hidden
          style={{
            display: 'inline-block',
            width: 12,
            height: 12,
            borderRadius: 3,
            backgroundColor: value,
            marginRight: 4,
          }}
        />
        {value}
      </span>
    )
  }
  return <span>{value == null || value === '' ? '-' : String(value)}</span>
}

function GenericCatalogSection({ tab }: { tab: CatalogTabSpec }) {
  const queryClient = useQueryClient()
  const itemsQuery = useQuery({
    queryKey: ['catalog-items', tab.key],
    queryFn: () => catalogsApi.listCatalogItems(tab.key, true),
  })

  const [code, setCode] = useState('')
  const [name, setName] = useState('')
  const [extraInputs, setExtraInputs] = useState<Record<string, string>>({})

  const createMutation = useMutation({
    mutationFn: () => {
      const extra: Record<string, unknown> = {}
      for (const spec of tab.extraFields) {
        const value = extraFieldInputValue(spec, extraInputs[spec.key] ?? '')
        if (value !== undefined) extra[spec.key] = value
      }
      return catalogsApi.createCatalogItem(tab.key, { code, name, extra })
    },
    onSuccess: () => {
      setCode('')
      setName('')
      setExtraInputs({})
      queryClient.invalidateQueries({ queryKey: ['catalog-items', tab.key] })
    },
  })

  const toggleMutation = useMutation({
    mutationFn: ({ item }: { item: CatalogItemOut }) =>
      catalogsApi.updateCatalogItem(tab.key, item.id, { is_active: !item.is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['catalog-items', tab.key] }),
  })

  const fileInputRef = useRef<HTMLInputElement>(null)
  const [importSummary, setImportSummary] = useState<CatalogImportSummary | null>(null)
  const importMutation = useMutation({
    mutationFn: (file: File) => catalogsApi.importCatalogItems(tab.key, file),
    onSuccess: (summary) => {
      setImportSummary(summary)
      queryClient.invalidateQueries({ queryKey: ['catalog-items', tab.key] })
    },
  })

  const items = itemsQuery.data ?? []

  return (
    <div className={styles.card}>
      <h2>{tab.label}</h2>
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '0.5rem' }}>
        <button
          className={styles.linkButton}
          type="button"
          onClick={() => void catalogsApi.exportCatalogItems(tab.key)}
        >
          Exportar CSV
        </button>
        <button
          className={styles.linkButton}
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={importMutation.isPending}
        >
          {importMutation.isPending ? 'Importando...' : 'Importar CSV'}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,text/csv"
          hidden
          onChange={(e) => {
            const file = e.target.files?.[0]
            e.target.value = ''
            if (file) importMutation.mutate(file)
          }}
        />
      </div>
      {importSummary && (
        <div style={{ marginBottom: '0.5rem' }}>
          <span>
            Importacion: {importSummary.created} creado(s), {importSummary.updated} actualizado(s)
            {importSummary.errors.length > 0 && `, ${importSummary.errors.length} con error`}.
          </span>
          {importSummary.errors.length > 0 && (
            <ul>
              {importSummary.errors.map((err, i) => (
                <li key={i}>{err}</li>
              ))}
            </ul>
          )}
        </div>
      )}
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={{ textAlign: 'left' }}>Codigo</th>
            <th style={{ textAlign: 'left' }}>Nombre</th>
            {tab.extraFields.map((spec) => (
              <th key={spec.key} style={{ textAlign: 'left' }}>
                {spec.label}
              </th>
            ))}
            <th style={{ textAlign: 'left' }}>Activo</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id} style={{ opacity: item.is_active ? 1 : 0.5 }}>
              <td>{item.code}</td>
              <td>{item.name}</td>
              {tab.extraFields.map((spec) => (
                <td key={spec.key}>
                  <ExtraFieldValue spec={spec} value={item.extra[spec.key]} />
                </td>
              ))}
              <td>{item.is_active ? 'Si' : 'No'}</td>
              <td>
                <button
                  className={styles.linkButton}
                  type="button"
                  onClick={() => toggleMutation.mutate({ item })}
                  disabled={toggleMutation.isPending}
                >
                  {item.is_active ? 'Desactivar' : 'Activar'}
                </button>
              </td>
            </tr>
          ))}
          {items.length === 0 && (
            <tr>
              <td colSpan={tab.extraFields.length + 4}>Sin elementos todavia.</td>
            </tr>
          )}
        </tbody>
      </table>

      <form
        className={styles.form}
        onSubmit={(e) => {
          e.preventDefault()
          createMutation.mutate()
        }}
      >
        <input
          type="text"
          placeholder="Codigo interno (minusculas, sin espacios)"
          required
          pattern="[a-z0-9_]+"
          value={code}
          onChange={(e) => setCode(e.target.value)}
        />
        <input
          type="text"
          placeholder="Nombre visible"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        {tab.extraFields.map((spec) =>
          spec.type === 'checkbox' ? (
            <label key={spec.key}>
              <input
                type="checkbox"
                checked={extraInputs[spec.key] === 'true'}
                onChange={(e) =>
                  setExtraInputs((prev) => ({ ...prev, [spec.key]: String(e.target.checked) }))
                }
              />
              {spec.label}
            </label>
          ) : (
            <input
              key={spec.key}
              type={spec.type === 'number' ? 'number' : spec.type === 'color' ? 'color' : 'text'}
              placeholder={spec.label}
              value={extraInputs[spec.key] ?? ''}
              onChange={(e) =>
                setExtraInputs((prev) => ({ ...prev, [spec.key]: e.target.value }))
              }
            />
          ),
        )}
        <button
          className={styles.primaryButton}
          type="submit"
          disabled={!code.trim() || !name.trim() || createMutation.isPending}
        >
          Agregar
        </button>
      </form>
      {createMutation.isError && (
        <div className={styles.errorBox}>
          No se pudo agregar (revisa si el codigo ya existe en este catalogo).
        </div>
      )}
    </div>
  )
}

function ProceduresSection() {
  const queryClient = useQueryClient()
  const itemsQuery = useQuery({
    queryKey: ['procedure-catalog'],
    queryFn: treatmentApi.listProcedureCatalog,
  })

  const [code, setCode] = useState('')
  const [name, setName] = useState('')
  const [price, setPrice] = useState('')

  const createMutation = useMutation({
    mutationFn: () => treatmentApi.createProcedureCatalogItem({ code, name, default_price: price }),
    onSuccess: () => {
      setCode('')
      setName('')
      setPrice('')
      queryClient.invalidateQueries({ queryKey: ['procedure-catalog'] })
    },
  })

  const items: ProcedureCatalogOut[] = itemsQuery.data ?? []

  return (
    <div className={styles.card}>
      <h2>Procedimientos y precios</h2>
      <p>Ya vive en su propia tabla desde la Fase 7 -- aqui solo se integra a la pantalla.</p>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={{ textAlign: 'left' }}>Codigo</th>
            <th style={{ textAlign: 'left' }}>Nombre</th>
            <th style={{ textAlign: 'left' }}>Precio</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id} style={{ opacity: item.is_active ? 1 : 0.5 }}>
              <td>{item.code}</td>
              <td>{item.name}</td>
              <td>${item.default_price}</td>
            </tr>
          ))}
          {items.length === 0 && (
            <tr>
              <td colSpan={3}>Sin procedimientos todavia.</td>
            </tr>
          )}
        </tbody>
      </table>

      <form
        className={styles.form}
        onSubmit={(e) => {
          e.preventDefault()
          createMutation.mutate()
        }}
      >
        <input
          type="text"
          placeholder="Codigo interno"
          required
          value={code}
          onChange={(e) => setCode(e.target.value)}
        />
        <input
          type="text"
          placeholder="Nombre visible"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <input
          type="number"
          step="0.01"
          placeholder="Precio"
          required
          value={price}
          onChange={(e) => setPrice(e.target.value)}
        />
        <button
          className={styles.primaryButton}
          type="submit"
          disabled={!code.trim() || !name.trim() || !price || createMutation.isPending}
        >
          Agregar
        </button>
      </form>
    </div>
  )
}

function ResourcesSection() {
  const queryClient = useQueryClient()
  const resourcesQuery = useQuery({
    queryKey: ['resources', 'active', 'with-inactive'],
    queryFn: () => agendaApi.listResources(undefined, true),
  })

  const [name, setName] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editingName, setEditingName] = useState('')

  const createMutation = useMutation({
    mutationFn: () => agendaApi.createResource(name),
    onSuccess: () => {
      setName('')
      queryClient.invalidateQueries({ queryKey: ['resources'] })
    },
  })

  const renameMutation = useMutation({
    mutationFn: ({ id, newName }: { id: string; newName: string }) =>
      agendaApi.updateResource(id, { name: newName }),
    onSuccess: () => {
      setEditingId(null)
      queryClient.invalidateQueries({ queryKey: ['resources'] })
    },
  })

  const toggleMutation = useMutation({
    mutationFn: ({ resource }: { resource: ResourceOut }) =>
      agendaApi.updateResource(resource.id, { is_active: !resource.is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['resources'] }),
  })

  const resources = resourcesQuery.data ?? []

  return (
    <div className={styles.card}>
      <h2>Gabinetes</h2>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={{ textAlign: 'left' }}>Nombre</th>
            <th style={{ textAlign: 'left' }}>Activo</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {resources.map((resource) => (
            <tr key={resource.id} style={{ opacity: resource.is_active ? 1 : 0.5 }}>
              <td>
                {editingId === resource.id ? (
                  <input
                    type="text"
                    value={editingName}
                    onChange={(e) => setEditingName(e.target.value)}
                  />
                ) : (
                  resource.name
                )}
              </td>
              <td>{resource.is_active ? 'Si' : 'No'}</td>
              <td>
                {editingId === resource.id ? (
                  <button
                    className={styles.linkButton}
                    type="button"
                    disabled={!editingName.trim() || renameMutation.isPending}
                    onClick={() =>
                      renameMutation.mutate({ id: resource.id, newName: editingName })
                    }
                  >
                    Guardar
                  </button>
                ) : (
                  <button
                    className={styles.linkButton}
                    type="button"
                    onClick={() => {
                      setEditingId(resource.id)
                      setEditingName(resource.name)
                    }}
                  >
                    Renombrar
                  </button>
                )}{' '}
                <button
                  className={styles.linkButton}
                  type="button"
                  onClick={() => toggleMutation.mutate({ resource })}
                  disabled={toggleMutation.isPending}
                >
                  {resource.is_active ? 'Desactivar' : 'Activar'}
                </button>
              </td>
            </tr>
          ))}
          {resources.length === 0 && (
            <tr>
              <td colSpan={3}>Sin gabinetes todavia.</td>
            </tr>
          )}
        </tbody>
      </table>

      <form
        className={styles.form}
        onSubmit={(e) => {
          e.preventDefault()
          createMutation.mutate()
        }}
      >
        <input
          type="text"
          placeholder="Nombre del gabinete"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <button
          className={styles.primaryButton}
          type="submit"
          disabled={!name.trim() || createMutation.isPending}
        >
          Agregar
        </button>
      </form>
    </div>
  )
}

function ClinicSection() {
  const activeClinic = useAuthStore((s) => s.clinics.find((c) => c.clinic.id === s.activeClinicId))

  const [name, setName] = useState(activeClinic?.clinic.name ?? '')
  const [address, setAddress] = useState(activeClinic?.clinic.address ?? '')
  const [phone, setPhone] = useState(activeClinic?.clinic.phone ?? '')
  // Bug #42 de docs/PENDIENTES_CLINICOS.md: de que zona horaria es "hoy" para
  // las citas/atenciones de esta sucursal -- el backend valida que sea un
  // nombre IANA real (zoneinfo), el <datalist> solo sugiere las mas
  // frecuentes para una clinica en Mexico, sin impedir escribir otra.
  const [timezone, setTimezone] = useState(activeClinic?.clinic.timezone ?? 'America/Mexico_City')

  const updateMutation = useMutation({
    mutationFn: () => authApi.updateCurrentClinic({ name, address, phone, timezone }),
    onSuccess: () => {
      // El nombre de la sucursal se muestra en el menu lateral (useAuthStore.clinics,
      // un store de Zustand, no de TanStack Query) -- hay que recargarlo ahi para
      // que no se quede desactualizado.
      void useAuthStore.getState().loadClinics()
    },
  })

  return (
    <div className={styles.card}>
      <h2>Datos de la sucursal</h2>
      <p>
        Nombre, direccion y telefono de esta sucursal -- distinto de crear o administrar
        sucursales entre organizaciones, que sigue siendo exclusivo de quien administra el
        sistema.
      </p>
      <form
        className={styles.form}
        onSubmit={(e) => {
          e.preventDefault()
          updateMutation.mutate()
        }}
      >
        <input
          type="text"
          placeholder="Nombre"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <input
          type="text"
          placeholder="Direccion"
          value={address}
          onChange={(e) => setAddress(e.target.value)}
        />
        <input
          type="text"
          placeholder="Telefono"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
        />
        <label htmlFor="clinic-timezone">Zona horaria</label>
        <input
          id="clinic-timezone"
          type="text"
          list="clinic-timezone-options"
          required
          value={timezone}
          onChange={(e) => setTimezone(e.target.value)}
        />
        <datalist id="clinic-timezone-options">
          <option value="America/Mexico_City">Ciudad de Mexico (centro)</option>
          <option value="America/Tijuana">Tijuana (pacifico)</option>
          <option value="America/Hermosillo">Hermosillo (sin horario de verano)</option>
          <option value="America/Chihuahua">Chihuahua</option>
          <option value="America/Cancun">Cancun (este)</option>
        </datalist>
        <button
          className={styles.primaryButton}
          type="submit"
          disabled={!name.trim() || !timezone.trim() || updateMutation.isPending}
        >
          {updateMutation.isPending ? 'Guardando...' : 'Guardar'}
        </button>
      </form>
      {updateMutation.isSuccess && <p>Datos actualizados.</p>}
      {updateMutation.isError && (
        <div className={styles.errorBox}>No se pudieron guardar los datos.</div>
      )}
    </div>
  )
}

export function CatalogsPage() {
  const [activeTab, setActiveTab] = useState<string>(CATALOG_TABS[0].key)

  return (
    <section>
      <h1>Catalogos</h1>
      <div className={styles.tabs}>
        {CATALOG_TABS.map((tab) => (
          <button
            key={tab.key}
            className={activeTab === tab.key ? styles.tabActive : styles.tab}
            type="button"
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
        <button
          className={activeTab === 'procedures' ? styles.tabActive : styles.tab}
          type="button"
          onClick={() => setActiveTab('procedures')}
        >
          Procedimientos y precios
        </button>
        <button
          className={activeTab === 'resources' ? styles.tabActive : styles.tab}
          type="button"
          onClick={() => setActiveTab('resources')}
        >
          Gabinetes
        </button>
        <button
          className={activeTab === 'clinic' ? styles.tabActive : styles.tab}
          type="button"
          onClick={() => setActiveTab('clinic')}
        >
          Sucursal
        </button>
      </div>

      {activeTab === 'procedures' ? (
        <ProceduresSection />
      ) : activeTab === 'resources' ? (
        <ResourcesSection />
      ) : activeTab === 'clinic' ? (
        <ClinicSection />
      ) : (
        <GenericCatalogSection
          key={activeTab}
          tab={CATALOG_TABS.find((t) => t.key === activeTab) ?? CATALOG_TABS[0]}
        />
      )}
    </section>
  )
}
