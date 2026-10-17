import { useId } from 'react'
import { usePack } from '../../i18n/pack'
import type { UploadResult } from '../../shared/types'
import { intakeMessages } from './intakeMessages'

export function WorkbookSheetPicker({ result, onSelect }: { result: UploadResult; onSelect: (sheet: string) => void }) {
  const { t } = usePack(intakeMessages)
  const id = useId()
  if (result.sheets.length < 2) return null
  return <div className="field">
    <label className="field__label" htmlFor={id}>{t('intake.sheet')}</label>
    <select id={id} className="field__select" value={result.selected_sheet ?? ''} onChange={(event) => onSelect(event.target.value)} aria-describedby={`${id}-help`}>
      {!result.selected_sheet && <option value="" disabled>{t('intake.sheet')}</option>}
      {result.sheets.map((sheet) => <option key={sheet} value={sheet}>{sheet}</option>)}
    </select>
    <span id={`${id}-help`} className="field__help">{t('intake.sheetHelp')}</span>
  </div>
}
