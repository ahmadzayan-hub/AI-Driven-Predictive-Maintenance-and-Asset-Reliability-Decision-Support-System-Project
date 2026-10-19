import { render, screen } from '@testing-library/react'
import { afterEach, expect, it } from 'vitest'
import { applyLocale } from '../../i18n'
import type { FittedModelCard, ModelCard } from '../../shared/types'
import { ModelCards } from './ModelCards'

afterEach(() => applyLocale('en'))

const fitted: FittedModelCard = {
  role: 'maintenance_risk', title: 'Maintenance risk', kind: 'maintenance_risk',
  target: 'Repeat repair', inputs: ['Known_before'], train_records: 100, test_records: 60,
  split: { kind: 'time', first_held_out: '2026-01' },
  metric: { name: 'balanced accuracy', model: 0.53, baseline: 0.5, baseline_name: 'always the commonest label' },
  improvement: 0.06, beats_baseline: true,
  details: { verdict: 'weak', horizon: 'the same maintenance record', decision: 'Review the job' },
}

it('does not call a maintenance model useful when it misses the absolute acceptance floor', () => {
  render(<ModelCards models={[fitted]} language="en" />)
  expect(screen.getByText('Weak: acceptance criteria are not met. Do not use it.')).toBeInTheDocument()
  expect(screen.getByText('the same maintenance record')).toBeInTheDocument()
  expect(screen.getByText(/53.*50/)).toBeInTheDocument()
  expect(screen.queryByText(/Beats its baseline/)).not.toBeInTheDocument()
  expect(screen.queryByText(/models\./)).not.toBeInTheDocument()
})

it('shows unsupported maintenance targets without fabricating scores or populations in Arabic', () => {
  applyLocale('ar')
  const unsupported: ModelCard = { role: 'maintenance_risk', title: 'مخاطر الصيانة', kind: 'maintenance_risk',
    target: 'تكرار الإصلاح', fitted: false, details: { verdict: 'not_supported', reason: 'لا توجد سجلات كافية' } }
  render(<ModelCards models={[unsupported]} language="ar" />)
  expect(screen.getByText('لم يُبنَ النموذج: الأدلة المطلوبة غير متاحة.')).toBeInTheDocument()
  expect(screen.getByText('لا توجد سجلات كافية')).toBeInTheDocument()
  expect(screen.queryByText(/0%|NaN|undefined/)).not.toBeInTheDocument()
  expect(screen.queryByRole('definition')).not.toBeInTheDocument()
})
