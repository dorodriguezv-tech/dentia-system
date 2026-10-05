import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as encountersApi from '../encounters/api'
import * as api from './api'
import { STUDY_TYPE_LABELS, STUDY_TYPES } from './catalog'
import styles from './ImagesTab.module.css'
import type { ImageOut, StudyType } from './types'

function EncounterSelect({
  encounters,
  value,
  onChange,
}: {
  encounters: { id: string; started_at: string; chief_complaint: string | null }[]
  value: string
  onChange: (encounterId: string) => void
}) {
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)}>
      <option value="">Selecciona una atencion...</option>
      {encounters.map((encounter) => (
        <option key={encounter.id} value={encounter.id}>
          {new Date(encounter.started_at).toLocaleDateString('es-MX')} —{' '}
          {encounter.chief_complaint ?? 'Sin motivo'}
        </option>
      ))}
    </select>
  )
}

function UploadForm({ patientId }: { patientId: string }) {
  const queryClient = useQueryClient()
  const encountersQuery = useQuery({
    queryKey: ['patient-encounters', patientId],
    queryFn: () => encountersApi.listPatientEncounters(patientId),
  })

  const [encounterId, setEncounterId] = useState('')
  const [studyType, setStudyType] = useState<StudyType>('intraoral')
  const [toothFdi, setToothFdi] = useState('')
  const [notes, setNotes] = useState('')
  const [files, setFiles] = useState<File[]>([])

  const uploadMutation = useMutation({
    mutationFn: () =>
      api.uploadImages(patientId, {
        encounter_id: encounterId,
        study_type: studyType,
        tooth_fdi: toothFdi ? Number(toothFdi) : null,
        notes: notes || null,
        files,
      }),
    onSuccess: () => {
      setFiles([])
      setNotes('')
      queryClient.invalidateQueries({ queryKey: ['images', patientId] })
    },
  })

  return (
    <form
      className={styles.form}
      onSubmit={(e) => {
        e.preventDefault()
        uploadMutation.mutate()
      }}
    >
      <EncounterSelect encounters={encountersQuery.data ?? []} value={encounterId} onChange={setEncounterId} />
      <select value={studyType} onChange={(e) => setStudyType(e.target.value as StudyType)}>
        {STUDY_TYPES.map((type) => (
          <option key={type} value={type}>
            {STUDY_TYPE_LABELS[type]}
          </option>
        ))}
      </select>
      <input
        type="number"
        placeholder="Pieza FDI (opcional)"
        min={11}
        max={85}
        value={toothFdi}
        onChange={(e) => setToothFdi(e.target.value)}
      />
      <input
        type="text"
        placeholder="Notas (opcional)"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
      />
      <input
        type="file"
        multiple
        accept="image/jpeg,image/png,application/pdf"
        onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
      />
      <button
        className={styles.primaryButton}
        type="submit"
        disabled={!encounterId || files.length === 0 || uploadMutation.isPending}
      >
        Subir {files.length > 1 ? `${files.length} archivos` : 'archivo'}
      </button>
      {uploadMutation.isError && <p className={styles.errorBox}>No se pudo subir el archivo.</p>}
    </form>
  )
}

function Thumbnail({ image, onClick }: { image: ImageOut; onClick: () => void }) {
  const thumbQuery = useQuery({
    queryKey: ['image-thumbnail', image.id],
    queryFn: () => (image.has_thumbnail ? api.getThumbnailBlobUrl(image.id) : Promise.resolve(null)),
  })

  return (
    <button className={styles.thumbCard} type="button" onClick={onClick}>
      {thumbQuery.data ? (
        <img src={thumbQuery.data} alt={image.original_filename} className={styles.thumbImg} />
      ) : (
        <div className={styles.thumbPlaceholder}>PDF</div>
      )}
      <span className={styles.thumbLabel}>
        {STUDY_TYPE_LABELS[image.study_type]}
        {image.tooth_fdi && ` · Pieza ${image.tooth_fdi}`}
      </span>
      {!image.is_active && <span className={styles.annulledBadge}>Anulada</span>}
    </button>
  )
}

function Viewer({
  patientId,
  image,
  canWrite,
  onClose,
}: {
  patientId: string
  image: ImageOut
  canWrite: boolean
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const fullQuery = useQuery({
    queryKey: ['image-full', image.id],
    queryFn: () => api.getImageBlobUrl(image.id),
  })
  const [zoom, setZoom] = useState(1)
  const [brightness, setBrightness] = useState(100)
  const [contrast, setContrast] = useState(100)
  const [reason, setReason] = useState('')
  const [annulling, setAnnulling] = useState(false)

  const annulMutation = useMutation({
    mutationFn: () => api.annulImage(image.id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['images', patientId] })
      onClose()
    },
  })

  const isPdf = image.content_type === 'application/pdf'

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.modalHeader}>
          <span>
            {STUDY_TYPE_LABELS[image.study_type]}
            {image.tooth_fdi && ` · Pieza ${image.tooth_fdi}`}
            {image.notes && ` · ${image.notes}`}
          </span>
          <button className={styles.linkButton} type="button" onClick={onClose}>
            Cerrar
          </button>
        </div>

        {fullQuery.data &&
          (isPdf ? (
            <iframe src={fullQuery.data} title={image.original_filename} className={styles.pdfFrame} />
          ) : (
            <div className={styles.viewerFrame}>
              <img
                src={fullQuery.data}
                alt={image.original_filename}
                style={{
                  transform: `scale(${zoom})`,
                  filter: `brightness(${brightness}%) contrast(${contrast}%)`,
                }}
              />
            </div>
          ))}

        {!isPdf && (
          <div className={styles.controls}>
            <label>
              Zoom
              <input
                type="range"
                min={0.5}
                max={3}
                step={0.1}
                value={zoom}
                onChange={(e) => setZoom(Number(e.target.value))}
              />
            </label>
            <label>
              Brillo
              <input
                type="range"
                min={50}
                max={150}
                value={brightness}
                onChange={(e) => setBrightness(Number(e.target.value))}
              />
            </label>
            <label>
              Contraste
              <input
                type="range"
                min={50}
                max={150}
                value={contrast}
                onChange={(e) => setContrast(Number(e.target.value))}
              />
            </label>
          </div>
        )}

        {canWrite && image.is_active && (
          <div className={styles.annulRow}>
            {!annulling ? (
              <button className={styles.linkButton} type="button" onClick={() => setAnnulling(true)}>
                Anular imagen
              </button>
            ) : (
              <>
                <input
                  type="text"
                  placeholder="Motivo de anulacion"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
                <button
                  className={styles.linkButton}
                  type="button"
                  disabled={!reason.trim()}
                  onClick={() => annulMutation.mutate()}
                >
                  Confirmar
                </button>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export function ImagesTab({
  patientId,
  canWrite,
}: {
  patientId: string
  canWrite: boolean
}) {
  const imagesQuery = useQuery({
    queryKey: ['images', patientId],
    queryFn: () => api.listImages(patientId),
  })
  const [selected, setSelected] = useState<ImageOut | null>(null)

  return (
    <div className={styles.page}>
      {canWrite && <UploadForm patientId={patientId} />}

      <div className={styles.gallery}>
        {imagesQuery.data?.map((image) => (
          <Thumbnail key={image.id} image={image} onClick={() => setSelected(image)} />
        ))}
      </div>
      {!imagesQuery.data?.length && <p>Sin imagenes registradas.</p>}

      {selected && (
        <Viewer
          patientId={patientId}
          image={selected}
          canWrite={canWrite}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  )
}
