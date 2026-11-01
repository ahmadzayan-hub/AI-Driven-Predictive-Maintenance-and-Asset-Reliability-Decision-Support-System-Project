import '../../shared/styles/analytics.css'
import { useI18n } from '../../i18n'
import type { UploadResult } from '../../shared/types'

/** The first rows of a table, as an upload or a merge preview shows them. */
export function PreviewTable({ columns, preview, label }: { columns: string[]; preview: string[][]; label: string }) {
  return <div className="evidence__table" role="region" aria-label={label} tabIndex={0}><table className="datatable"><thead><tr>{columns.map((name) => <th key={name} scope="col" dir="auto">{name}</th>)}</tr></thead><tbody>{preview.map((row, index) => <tr key={index}>{row.map((cell, column) => <td key={column} dir="auto">{cell}</td>)}</tr>)}</tbody></table></div>
}

export function UploadPreview({ result }: { result: UploadResult }) {
  const { t } = useI18n()
  return <details className="upload-preview"><summary>{t('datasets.previewTitle')}</summary>
    {result.sheets.length ? <p className="card__meta">{t('datasets.sheets')}: {result.sheets.map((sheet, index) => <span key={sheet}>{index ? ' · ' : ''}<bdi>{sheet}</bdi></span>)}</p> : null}
    <PreviewTable columns={result.columns} preview={result.preview} label={t('datasets.previewTitle')} />
  </details>
}
