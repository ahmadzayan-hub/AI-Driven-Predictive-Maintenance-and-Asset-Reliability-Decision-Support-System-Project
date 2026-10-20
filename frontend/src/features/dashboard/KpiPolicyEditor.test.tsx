import { act, cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { applyLocale } from '../../i18n'
import { api, ApiError } from '../../shared/api'
import type { KpiMeasure, KpiPolicy } from '../../shared/types'
import KpiPolicyEditor from './KpiPolicyEditor'
import { policyMessages } from './policyMessages'

vi.mock('../../shared/api', async (original) => ({ ...await original<typeof import('../../shared/api')>(), api: { kpiPolicy: vi.fn(), saveKpiPolicy: vi.fn(), identity: vi.fn() } }))
const rule = { direction: 'higher' as const, scale: 'percent', good_at: 80, okay_at: 60, source_ref: 'Fictional test plan' }
const policy: KpiPolicy = { revision: 'a'.repeat(64), rules: { repeat: { ...rule, direction: 'lower', good_at: 5, okay_at: 20 } } }
const measures = [{ key: 'first_fix', title: 'First-time fix', scale: 'percent' }, { key: 'repeat', title: 'Repeat failures', scale: 'percent' }] as KpiMeasure[]
const mount = () => {
  const onSaved = vi.fn()
  return { ...render(<KpiPolicyEditor runId="r1" measures={measures} onSaved={onSaved} onClose={vi.fn()} />), onSaved }
}
beforeEach(() => {
  applyLocale('en')
  vi.mocked(api.kpiPolicy).mockResolvedValue(policy)
  vi.mocked(api.identity).mockResolvedValue({ principal: { permissions: ['read', 'write'] } } as Awaited<ReturnType<typeof api.identity>>)
  vi.mocked(api.saveKpiPolicy).mockResolvedValue({ ...policy, revision: 'b'.repeat(64) })
})
afterEach(() => { cleanup(); act(() => applyLocale('en')); vi.resetAllMocks() })

it('saves explicit percentage-point boundaries and preserves other rules with the current revision', async () => {
  const user = userEvent.setup()
  const { onSaved } = mount()
  const good = await screen.findByRole('spinbutton', { name: 'Good boundary (inclusive)' })
  expect(good).toHaveValue(null)
  await user.type(good, '80.001')
  await user.type(screen.getByRole('spinbutton', { name: 'Okay boundary (inclusive)' }), '60')
  await user.type(screen.getByRole('textbox', { name: 'Target source / rationale' }), 'Plant plan v2')
  await user.click(screen.getByRole('button', { name: 'Save target' }))
  expect(api.saveKpiPolicy).toHaveBeenCalledWith('r1', { revision: policy.revision, rules: { ...policy.rules, first_fix: { ...rule, good_at: 80.001, source_ref: 'Plant plan v2' } } }, 'en', expect.any(AbortSignal))
  expect(onSaved).toHaveBeenCalledOnce()
})

it('rejects a reversed nested range before saving and recovers when the bounds are corrected', async () => {
  const user = userEvent.setup()
  mount()
  await user.selectOptions(await screen.findByRole('combobox', { name: 'Desired direction' }), 'range')
  for (const [name, value] of [['Good minimum (inclusive)', '8'], ['Good maximum (inclusive)', '12'], ['Okay minimum (inclusive)', '10'], ['Okay maximum (inclusive)', '16']]) {
    await user.type(screen.getByRole('spinbutton', { name }), value)
  }
  await user.type(screen.getByRole('textbox', { name: 'Target source / rationale' }), 'Test range')
  await user.click(screen.getByRole('button', { name: 'Save target' }))
  expect(screen.getByRole('alert')).toHaveTextContent('required order')
  expect(screen.getByRole('alert')).toHaveFocus()
  expect(api.saveKpiPolicy).not.toHaveBeenCalled()
  await user.clear(screen.getByRole('spinbutton', { name: 'Okay minimum (inclusive)' }))
  await user.type(screen.getByRole('spinbutton', { name: 'Okay minimum (inclusive)' }), '4')
  await user.click(screen.getByRole('button', { name: 'Save target' }))
  expect(api.saveKpiPolicy).toHaveBeenCalledOnce()
})

it('refuses a lost update, reloads the winning policy and removes only the selected target', async () => {
  const user = userEvent.setup()
  vi.mocked(api.saveKpiPolicy).mockRejectedValueOnce(new ApiError('Changed elsewhere', 409))
  mount()
  await user.selectOptions(await screen.findByRole('combobox', { name: 'Measure' }), 'repeat')
  await user.click(screen.getByRole('button', { name: 'Save target' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('changed elsewhere')
  expect(screen.getByRole('button', { name: 'Save target' })).toBeDisabled()
  vi.mocked(api.kpiPolicy).mockResolvedValueOnce({ revision: 'c'.repeat(64), rules: { ...policy.rules, first_fix: rule } })
  await user.click(screen.getByRole('button', { name: 'Reload targets' }))
  await waitFor(() => expect(screen.getByRole('button', { name: 'Remove target' })).toBeEnabled())
  await user.click(screen.getByRole('button', { name: 'Remove target' }))
  expect(api.saveKpiPolicy).toHaveBeenLastCalledWith('r1', { revision: 'c'.repeat(64), rules: { first_fix: rule } }, 'en', expect.any(AbortSignal))
})

it('disables writes for a reader and ships all target labels in Arabic', async () => {
  applyLocale('ar')
  vi.mocked(api.identity).mockResolvedValue({ principal: { permissions: ['read'] } } as Awaited<ReturnType<typeof api.identity>>)
  mount()
  expect(await screen.findByText('يمكن لدورك قراءة الأهداف. يلزم إذن الكتابة لتغييرها.')).toBeVisible()
  expect(screen.getByRole('button', { name: 'حفظ الهدف' })).toBeDisabled()
  expect(api.saveKpiPolicy).not.toHaveBeenCalled()
  expect(Object.keys(policyMessages.en)).toEqual(Object.keys(policyMessages.ar))
})

it('aborts a pending save when the editor unmounts and ignores its late result', async () => {
  const user = userEvent.setup()
  let finish!: (value: KpiPolicy) => void
  vi.mocked(api.saveKpiPolicy).mockImplementationOnce(() => new Promise((resolve) => { finish = resolve }))
  const { unmount, onSaved } = mount()
  await user.selectOptions(await screen.findByRole('combobox', { name: 'Measure' }), 'repeat')
  await user.click(screen.getByRole('button', { name: 'Save target' }))
  const signal = vi.mocked(api.saveKpiPolicy).mock.calls[0][3]!
  expect(screen.getByRole('button', { name: 'Close targets' })).toBeDisabled()
  unmount()
  expect(signal.aborted).toBe(true)
  await act(async () => finish(policy))
  expect(onSaved).not.toHaveBeenCalled()
})
