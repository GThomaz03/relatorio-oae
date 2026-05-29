import { useEffect, useState } from 'react'
import { FileSpreadsheet, Upload } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  getInputSchema,
  validateExcelFile,
  type ExcelValidateResponse,
  type InputSchemaResponse,
} from '@/services/management-api'

export function InputDataTab() {
  const [schema, setSchema] = useState<InputSchemaResponse | null>(null)
  const [validating, setValidating] = useState(false)
  const [result, setResult] = useState<ExcelValidateResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void getInputSchema().then(setSchema).catch(() => setSchema(null))
  }, [])

  const handleTest = async (file: File) => {
    setValidating(true)
    setError(null)
    try {
      const data = await validateExcelFile(file)
      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao validar planilha')
      setResult(null)
    } finally {
      setValidating(false)
    }
  }

  const columns = schema
    ? [...schema.required_columns, ...schema.optional_columns]
    : []

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Modelo de planilha Excel</CardTitle>
          <CardDescription>
            Colunas esperadas na aba de inspeção (ex.: db_ficha). Aliases aceites são normalizados
            automaticamente.
          </CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full min-w-[520px] text-left text-sm">
            <thead>
              <tr className="border-b border-graphite-200 text-xs uppercase text-graphite-500">
                <th className="py-2 pr-4">Coluna</th>
                <th className="py-2 pr-4">Obrigatória</th>
                <th className="py-2 pr-4">Aliases</th>
                <th className="py-2">Exemplo</th>
              </tr>
            </thead>
            <tbody>
              {columns.map((col) => (
                <tr key={col.name} className="border-b border-graphite-100">
                  <td className="py-2 pr-4 font-medium text-graphite-800">{col.name}</td>
                  <td className="py-2 pr-4">{col.required ? 'Sim' : 'Não'}</td>
                  <td className="py-2 pr-4 text-xs text-graphite-600">
                    {col.aliases.length ? col.aliases.join(', ') : '—'}
                  </td>
                  <td className="py-2 text-xs text-graphite-600">{col.example || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {schema?.default_sheet_names.length ? (
            <p className="mt-3 text-xs text-graphite-500">
              Abas preferidas: {schema.default_sheet_names.join(', ')}
            </p>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <FileSpreadsheet className="h-4 w-4 text-petrol-600" />
            <CardTitle>Testar planilha</CardTitle>
          </div>
          <CardDescription>
            Envie um .xlsx de amostra para verificar colunas, aba detectada e prévia das linhas.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <label className="inline-flex cursor-pointer">
            <input
              type="file"
              accept=".xlsx,.xls"
              className="sr-only"
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (file) void handleTest(file)
                e.target.value = ''
              }}
            />
            <span className="inline-flex items-center gap-2 rounded-lg border border-graphite-200 bg-white px-4 py-2 text-sm font-medium text-graphite-700 hover:bg-graphite-50">
              <Upload className="h-4 w-4" />
              {validating ? 'Validando...' : 'Selecionar planilha'}
            </span>
          </label>

          {error ? <p className="text-sm text-error">{error}</p> : null}

          {result ? (
            <div
              className={`rounded-lg border p-4 text-sm ${
                result.ok
                  ? 'border-success/40 bg-success-bg text-graphite-800'
                  : 'border-error/30 bg-red-50 text-graphite-800'
              }`}
            >
              <p className="font-medium">
                {result.ok ? 'Planilha compatível' : 'Planilha com pendências'}
              </p>
              {result.sheet_name ? (
                <p className="mt-1 text-xs">Aba usada: {result.sheet_name}</p>
              ) : null}
              {result.missing_columns.length > 0 ? (
                <p className="mt-2 text-xs">
                  Colunas ausentes: {result.missing_columns.join(', ')}
                </p>
              ) : null}
              {result.extra_columns.length > 0 ? (
                <p className="mt-1 text-xs text-graphite-600">
                  Colunas extras (ignoradas): {result.extra_columns.join(', ')}
                </p>
              ) : null}
              {result.parse_warnings > 0 ? (
                <p className="mt-1 text-xs text-warning">
                  {result.parse_warnings} aviso(s) ao interpretar linhas.
                </p>
              ) : null}
              {result.preview_rows.length > 0 ? (
                <pre className="mt-3 max-h-40 overflow-auto rounded bg-white/80 p-2 text-xs">
                  {JSON.stringify(result.preview_rows[0], null, 2)}
                </pre>
              ) : null}
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  )
}
