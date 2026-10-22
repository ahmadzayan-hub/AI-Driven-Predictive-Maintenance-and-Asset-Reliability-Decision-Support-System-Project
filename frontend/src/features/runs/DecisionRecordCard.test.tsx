import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { applyLocale } from '../../i18n'
import type { DecisionRecord } from '../../shared/types'
import { DecisionInputs, toAssumptions } from './DecisionInputs'
import { DecisionRecordCard } from './DecisionRecordCard'

afterEach(() => applyLocale('en'))

const record: DecisionRecord = {
  decision_id: 'run-1:lift_south',
  issue: 'South trails North',
  scope: 'South',
  evidence: ['c_option_lift_south'],
  risk: { measure: 'revenue', observed: 1200, basis: 'current total of the target in the data; not a probability' },
  alternatives: [
    { key: 'lift_south', title: 'Lift South', target: 'South', base_value: 1200, uplift: 0.15, uplift_source: 'stated', cost: 100, expected_gain: 80, evidence: [] },
    { key: 'lift_north', title: 'Lift North', target: 'North', base_value: 1400, uplift: 0.1, uplift_source: 'assumed', cost: null, expected_gain: 140, evidence: [] },
  ],
  expected_impact: { low: 60, high: 140, uplift_range: [0.05, 0.2], label: 'stated' },
  cost: { stated_for: ['South'], not_stated_for: ['North'] },
  constraints: [],
  uncertainty: { stable_within_ranges: false, uplift_range: [0.05, 0.2], break_even_ratio: null,
    flip_points: [{ key: 'lift_north', target: 'North', flip_at_uplift: 0.12, inside_range: true, can_overtake: true }] },
  recommended_action: 'Lift South',
  recommendation_basis: 'size_no_cost',
  approval: null,
  audit: { run_id: 'run-1', snapshot: null, report_language: 'en' },
}

it('shows which inputs were stated, the flip point and that no one has decided yet', () => {
  render(<DecisionRecordCard decision={record} language="en" />)
  expect(screen.getByRole('heading', { name: 'Decision record' })).toBeInTheDocument()
  expect(screen.getByText('Lift South', { selector: 'strong' })).toBeInTheDocument()
  expect(screen.getByText('stated', { selector: 'small' })).toBeInTheDocument()
  expect(screen.getByText('assumed', { selector: 'small' })).toBeInTheDocument()
  expect(screen.getByText('not stated')).toBeInTheDocument()
  expect(screen.getByText(/Close call: the ranking flips if “North” improves by 12% or more/)).toBeInTheDocument()
  expect(screen.getByText('Awaiting the approver.')).toBeInTheDocument()
  expect(screen.queryByText(/decision\./)).not.toBeInTheDocument()
})

it('names the approver and the date once the gate has decided, in Arabic', () => {
  applyLocale('ar')
  const decided: DecisionRecord = { ...record, approval: { state: 'approved_once', decided_at: '2026-10-22T10:00:00Z', decided_by: 'Layla' } }
  render(<DecisionRecordCard decision={decided} language="en" />)
  expect(screen.getByRole('heading', { name: 'سجل القرار' })).toBeInTheDocument()
  expect(screen.getByText(/معتمد بواسطة Layla في/)).toBeInTheDocument()
  expect(screen.queryByText(/NaN|undefined|decision\./)).not.toBeInTheDocument()
})

it('turns the form into assumptions the API accepts, and nothing when nothing is stated', () => {
  expect(toAssumptions([{ target: '', uplift: '', cost: '' }], { low: '5', high: '20' })).toBeUndefined()
  expect(toAssumptions([{ target: 'South', uplift: '15', cost: '' }, { target: 'North', uplift: '', cost: '1000' }], { low: '5', high: '20' }))
    .toEqual({ uplift: { South: 0.15 }, costs: { North: 1000 } })
  expect(toAssumptions([{ target: '', uplift: '', cost: '' }], { low: '10', high: '30' })).toEqual({ uplift_range: [0.1, 0.3] })
  expect(toAssumptions([{ target: '', uplift: '15', cost: '' }], { low: '5', high: '20' })).toBeNull()
  expect(toAssumptions([{ target: 'South', uplift: '-1', cost: '' }], { low: '5', high: '20' })).toBeNull()
  expect(toAssumptions([{ target: 'South', uplift: '5', cost: '' }], { low: '20', high: '5' })).toBeNull()
})

it('reports every change to the parent and flags input it cannot read', () => {
  const onChange = vi.fn()
  render(<DecisionInputs onChange={onChange} />)
  fireEvent.click(screen.getByText('Improvement and cost (optional)'))
  fireEvent.change(screen.getByLabelText('Group, as the data spells it'), { target: { value: 'South' } })
  fireEvent.change(screen.getByLabelText('Improvement, %'), { target: { value: '15' } })
  expect(onChange).toHaveBeenLastCalledWith({ uplift: { South: 0.15 } })
  fireEvent.change(screen.getByLabelText('Improvement, %'), { target: { value: 'lots' } })
  expect(onChange).toHaveBeenLastCalledWith(null)
  expect(screen.getByRole('alert')).toHaveTextContent(/Each improvement must be a number/)
})
