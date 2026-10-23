import { useId } from 'react'
import { usePack } from '../../i18n/pack'
import type { UploadResult } from '../../shared/types'
import { intakeMessages } from './intakeMessages'

export function WorkbookSheetPicker({ result, onSelect }: { result: UploadResult; onSelect: (sheet: string) => void }) {
  const { t } = usePack(intakeMessages)
  const id = useId()
  if (result.sheets.length < 2) return null
  const details = new Map(result.sheet_details?.map((d) => [d.name, d]))
  return <div className="field">
    <label className="field__label" htmlFor={id}>{t('intake.sheet')}</label>
    <select id={id} className="field__select" value={result.selected_sheet ?? ''} onChange={(event) => onSelect(event.target.value)} aria-describedby={`${id}-help`}>
      {!result.selected_sheet && <option value="" disabled>{t('intake.sheet')}</option>}
      {result.sheets.map((sheet) => { const d = details.get(sheet); return <option key={sheet} value={sheet}>{sheet}{d?.rows ? ` · ${d.rows}×${d.columns}` : ''}{d && !d.tabular ? ` · ${t('intake.sheetNotTable')}` : ''}</option> })}
    </select>
    <span id={`${id}-help`} className="field__help">{t('intake.sheetHelp')}</span>
  </div>
}
