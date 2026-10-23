/** The decision inputs a run may state (slice three, A2): an improvement
 *  per group, a cost per group and the improvement range the sensitivity
 *  stage explores. Blank rows send nothing, so the report keeps and names
 *  its assumed uniform improvement. The server validates every field. */
import { useState } from 'react'
import { usePack } from '../../i18n/pack'
import type { RunAssumptions } from '../../shared/types'
import { decisionMessages } from './messages'
import './decision.css'

interface Row { target: string; uplift: string; cost: string }

const EMPTY: Row = { target: '', uplift: '', cost: '' }
const DEFAULT_RANGE = { low: '5', high: '20' }

/** The assumptions a form state describes, `undefined` when it states
 *  nothing, or `null` when it cannot be read as numbers in range. */
export function toAssumptions(rows: Row[], range: { low: string; high: string }): RunAssumptions | null | undefined {
  const number = (text: string) => (text.trim() === '' ? undefined : Number(text))
  const uplift: Record<string, number> = {}
  const costs: Record<string, number> = {}
  for (const row of rows) {
    const target = row.target.trim()
    const up = number(row.uplift)
    const cost = number(row.cost)
    if (!target && up === undefined && cost === undefined) continue
    if (!target) return null
    if (up !== undefined) {
      if (!Number.isFinite(up) || up < 0 || up > 1000) return null
      uplift[target] = up / 100
    }
    if (cost !== undefined) {
      if (!Number.isFinite(cost) || cost < 0) return null
      costs[target] = cost
    }
  }
  const low = number(range.low)
  const high = number(range.high)
  const out: RunAssumptions = {}
  if (Object.keys(uplift).length) out.uplift = uplift
  if (Object.keys(costs).length) out.costs = costs
  // The range travels only when it differs from the server's default, so
  // a run that states nothing about it carries nothing about it.
  const custom = (low !== undefined && low !== Number(DEFAULT_RANGE.low)) || (high !== undefined && high !== Number(DEFAULT_RANGE.high))
  if (custom) {
    const lo = low ?? Number(DEFAULT_RANGE.low)
    const hi = high ?? Number(DEFAULT_RANGE.high)
    if (!Number.isFinite(lo) || !Number.isFinite(hi) || lo < 0 || hi > 1000 || lo >= hi) return null
    out.uplift_range = [lo / 100, hi / 100]
  }
  return Object.keys(out).length ? out : undefined
}

export function DecisionInputs({ disabled, onChange }: {
  disabled?: boolean
  onChange: (assumptions: RunAssumptions | null | undefined) => void
}) {
  const { t, formatNumber } = usePack(decisionMessages)
  const [rows, setRows] = useState<Row[]>([EMPTY])
  const [range, setRange] = useState(DEFAULT_RANGE)
  const [invalid, setInvalid] = useState(false)

  function update(nextRows: Row[], nextRange: { low: string; high: string }) {
    setRows(nextRows)
    setRange(nextRange)
    const next = toAssumptions(nextRows, nextRange)
    setInvalid(next === null)
    onChange(next)
  }
  const edit = (index: number, patch: Partial<Row>) =>
    update(rows.map((row, i) => (i === index ? { ...row, ...patch } : row)), range)

  return (
    <details className="run-more decision-inputs">
      <summary>{t('decision.inputsTitle')}</summary>
      <p className="field__help">{t('decision.inputsHelp')}</p>
      {rows.map((row, index) => (
        <fieldset className="decision-inputs__row" key={index} disabled={disabled}>
          <legend className="visually-hidden">{t('decision.row', { n: formatNumber(index + 1) })}</legend>
          <label className="field">
            <span className="field__label">{t('decision.target')}</span>
            <input className="field__input" dir="auto" value={row.target} maxLength={200}
              onChange={(event) => edit(index, { target: event.target.value })} />
          </label>
          <label className="field decision-inputs__number">
            <span className="field__label">{t('decision.uplift')}</span>
            <input className="field__input" inputMode="decimal" value={row.uplift}
              onChange={(event) => edit(index, { uplift: event.target.value })} />
          </label>
          <label className="field decision-inputs__number">
            <span className="field__label">{t('decision.cost')}</span>
            <input className="field__input" inputMode="decimal" value={row.cost}
              onChange={(event) => edit(index, { cost: event.target.value })} />
          </label>
          {rows.length > 1 ? (
            <button type="button" className="btn btn--ghost decision-inputs__remove"
              aria-label={t('decision.removeRow', { n: formatNumber(index + 1) })}
              onClick={() => update(rows.filter((_, i) => i !== index), range)}>×</button>
          ) : null}
        </fieldset>
      ))}
      <div className="field">
        <button type="button" className="btn btn--ghost" disabled={disabled}
          onClick={() => update([...rows, EMPTY], range)}>{t('decision.addRow')}</button>
      </div>
      <div className="decision-inputs__range">
        <label className="field decision-inputs__number">
          <span className="field__label">{t('decision.rangeLow')}</span>
          <input className="field__input" inputMode="decimal" value={range.low} disabled={disabled}
            onChange={(event) => update(rows, { ...range, low: event.target.value })} />
        </label>
        <label className="field decision-inputs__number">
          <span className="field__label">{t('decision.rangeHigh')}</span>
          <input className="field__input" inputMode="decimal" value={range.high} disabled={disabled}
            onChange={(event) => update(rows, { ...range, high: event.target.value })} />
        </label>
      </div>
      <p className="field__help">{t('decision.rangeHelp')}</p>
      {invalid ? <p className="statusline statusline--error" role="alert">{t('decision.invalid')}</p> : null}
    </details>
  )
}
