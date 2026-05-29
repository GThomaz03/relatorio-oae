import { useId, useRef } from 'react'
import type { ReactNode } from 'react'
import { CheckCircle2, FileText, FolderOpen, ImageIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import type { FileRef } from '@/types/project'
import { formatDate, formatFileSize } from '@/utils/project-status'
import { cn } from '@/utils/cn'

type FileCardIcon = 'excel' | 'photos' | 'output'

/** Propósito da seleção de pasta — afeta validação e API utilizada. */
export type FolderPurpose = 'images' | 'output'

interface FileUploadCardProps {
  title: string
  description: string
  icon: FileCardIcon
  accept?: string
  directory?: boolean
  /** Quando `directory=true`, define se é pasta de fotos ou pasta de saída. */
  folderPurpose?: FolderPurpose
  buttonLabel: string
  fileRef: FileRef | null
  extraInfo?: string
  onSelect: (fileRef: FileRef, extra?: { photoCount?: number }) => void
  /** Arquivo(s) brutos para envio à API (não persiste no localStorage). */
  onRawFiles?: (files: File | File[]) => void
  /** Caminhos locais no desktop (upload feito pelo processo principal do Electron). */
  onDesktopPaths?: (paths: {
    excelPath?: string
    imagesDirPath?: string
    outputDirPath?: string
    photoCount?: number
  }) => void
}

const ICONS: Record<FileCardIcon, ReactNode> = {
  excel: <FileText className="h-5 w-5 text-petrol-600" />,
  photos: <ImageIcon className="h-5 w-5 text-petrol-600" />,
  output: <FolderOpen className="h-5 w-5 text-petrol-600" />,
}

const IMAGE_EXT = /\.(jpe?g|png|webp|gif|bmp|tiff?)$/i

function fileFromPayload(payload: { name: string; data: ArrayBuffer; size: number; lastModified: number }): File {
  return new File([payload.data], payload.name, {
    type: 'application/octet-stream',
    lastModified: payload.lastModified,
  })
}

async function readFilesFromDirectoryHandle(
  handle: FileSystemDirectoryHandle,
): Promise<File[]> {
  const files: File[] = []
  for await (const entry of handle.values()) {
    if (entry.kind === 'file' && IMAGE_EXT.test(entry.name)) {
      const fileHandle = entry as FileSystemFileHandle
      files.push(await fileHandle.getFile())
    }
  }
  return files
}

function folderNameFromWebkitFiles(files: FileList): string | null {
  const first = files[0]
  if (!first) return null
  const relativePath = (first as File & { webkitRelativePath?: string }).webkitRelativePath
  return relativePath?.split('/')[0] ?? first.name
}

export function FileUploadCard({
  title,
  description,
  icon,
  accept,
  directory = false,
  folderPurpose = 'images',
  buttonLabel,
  fileRef,
  extraInfo,
  onSelect,
  onRawFiles,
  onDesktopPaths,
}: FileUploadCardProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const inputId = useId()

  const emitFolderSelection = (name: string, photoCount?: number) => {
    onSelect(
      { name, path: name, size: undefined },
      photoCount !== undefined ? { photoCount } : undefined,
    )
  }

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    if (!files?.length) return

    if (!directory) {
      const file = files[0]
      if (!file) return
      onRawFiles?.(file)
      onSelect({
        name: file.name,
        path: file.name,
        size: file.size,
        lastModified: file.lastModified,
      })
      event.target.value = ''
      return
    }

    if (!files.length) {
      window.alert(
        'Não foi possível ler a pasta selecionada. Tente novamente ou use Chrome/Edge.',
      )
      event.target.value = ''
      return
    }

    const imageFiles = Array.from(files).filter((f) => IMAGE_EXT.test(f.name))
    onRawFiles?.(imageFiles)

    const folderName = folderNameFromWebkitFiles(files)
    if (!folderName) {
      event.target.value = ''
      return
    }

    if (folderPurpose === 'images') {
      const imageCount = Array.from(files).filter((f) => IMAGE_EXT.test(f.name)).length
      emitFolderSelection(folderName, imageCount)
    } else {
      emitFolderSelection(folderName)
    }
    event.target.value = ''
  }

  const openDirectoryPicker = async () => {
    if (window.electronAPI?.selectFolder) {
      try {
        const result = await window.electronAPI.selectFolder(folderPurpose)
        if (!result) return

        if (folderPurpose === 'images') {
          const count = result.fileCount ?? result.files?.length ?? 0
          onDesktopPaths?.({ imagesDirPath: result.path, photoCount: count })
          emitFolderSelection(result.name, count)
        } else {
          onDesktopPaths?.({ outputDirPath: result.path })
          onSelect({
            name: result.name,
            path: result.path,
          })
        }
      } catch {
        window.alert('Não foi possível ler a pasta selecionada.')
      }
      return
    }

    if (typeof window.showDirectoryPicker !== 'function') {
      inputRef.current?.click()
      return
    }

    try {
      const handle = await window.showDirectoryPicker({ mode: 'read' })
      if (folderPurpose === 'images') {
        const imageFiles = await readFilesFromDirectoryHandle(handle)
        onRawFiles?.(imageFiles)
        emitFolderSelection(handle.name, imageFiles.length)
      } else {
        emitFolderSelection(handle.name)
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        return
      }
      inputRef.current?.click()
    }
  }

  const openFilePicker = async () => {
    if (window.electronAPI?.selectFile) {
      const filters = accept
        ? [{ name: 'Arquivos', extensions: accept.split(',').map((part) => part.trim().replace(/^\./, '')) }]
        : undefined
      const result = await window.electronAPI.selectFile(filters)
      if (!result) return
      onDesktopPaths?.({ excelPath: result.path })
      const file = fileFromPayload(result)
      onRawFiles?.(file)
      onSelect({
        name: file.name,
        path: result.path,
        size: file.size,
        lastModified: file.lastModified,
      })
      return
    }
    inputRef.current?.click()
  }

  return (
    <Card className={cn(fileRef && 'border-petrol-200 bg-petrol-50/30')}>
      <CardHeader className="pb-3">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-petrol-100">
            {ICONS[icon]}
          </div>
          <div>
            <CardTitle className="text-sm">{title}</CardTitle>
            <CardDescription className="mt-1">{description}</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {fileRef ? (
          <div className="rounded-lg border border-petrol-200 bg-white p-3">
            <div className="flex items-start gap-2">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-success" />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-graphite-800">{fileRef.name}</p>
                <p className="mt-1 text-xs text-graphite-500">
                  {extraInfo ?? (fileRef.size ? formatFileSize(fileRef.size) : fileRef.path)}
                </p>
                {fileRef.lastModified ? (
                  <p className="text-xs text-graphite-400">
                    {formatDate(new Date(fileRef.lastModified).toISOString())}
                  </p>
                ) : null}
              </div>
            </div>
          </div>
        ) : null}

        <input
          ref={inputRef}
          id={inputId}
          type="file"
          className="sr-only"
          accept={directory ? undefined : accept}
          multiple={directory || undefined}
          {...(directory
            ? ({ webkitdirectory: 'true', directory: 'true' } as React.InputHTMLAttributes<HTMLInputElement>)
            : {})}
          onChange={handleChange}
        />

        {directory ? (
          <Button
            variant={fileRef ? 'secondary' : 'default'}
            size="sm"
            type="button"
            onClick={() => void openDirectoryPicker()}
          >
            {fileRef ? 'Alterar seleção' : buttonLabel}
          </Button>
        ) : (
          <Button
            variant={fileRef ? 'secondary' : 'default'}
            size="sm"
            type="button"
            onClick={() => void openFilePicker()}
          >
            {fileRef ? 'Alterar seleção' : buttonLabel}
          </Button>
        )}
      </CardContent>
    </Card>
  )
}

