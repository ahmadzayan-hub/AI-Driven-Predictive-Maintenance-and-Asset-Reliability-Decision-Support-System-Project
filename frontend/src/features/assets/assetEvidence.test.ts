import { describe, expect, it } from 'vitest'
import { findAssetEvidence } from './assetEvidence'
import type { RunDetail } from '../../shared/types'

function run(id: string, date: string, role: string, state = 'succeeded'): RunDetail {
  return { id, updated_at: date,
    tasks: [{ id: role, title: role, role, state, summary: role,
      quality_checks: [], claims: [] }],
  } as unknown as RunDetail
}
describe('asset domain evidence', () => {
  it('never invents a railway screen without a successful specialist stage', () => {
    expect(findAssetEvidence([run('a','2026-10-17','predictive')])).toBeNull()
    expect(findAssetEvidence([run('a','2026-10-17','rail_asset_manager','failed')])).toBeNull()
  })
  it('selects the newest successful railway observation analysis', () => {
    const found = findAssetEvidence([
      run('old','2026-10-15','rail_asset_manager'),
      run('irrelevant','2026-10-18','descriptive'),
      run('latest','2026-10-17','rail_asset_manager')
    ])
    expect(found?.run.id).toBe('latest')
    expect(found?.risk).toBeNull()
  })
  it('carries the decision stages in order, and the data health line in the run language', () => {
    const task = (role: string, claims: object[], state = 'succeeded') =>
      ({ id: role, title: role, role, state, summary: role, quality_checks: [], claims })
    const claim = { id: 'c', text: 'en', type: 'calculation', evidence: [], status: 'verified' }
    const found = findAssetEvidence([{ id: 'r', updated_at: '2026-10-31', tasks: [
      task('rail_asset_manager', []),
      task('what_if_scenarios', [claim]),
      task('risk_ranking', [], 'succeeded'),
      task('reliability_model', [claim]),
      task('cleaner', [{ ...claim, id: 'cl_health', text_ar: 'صحة البيانات' }]),
    ] } as unknown as RunDetail])
    expect(found?.decisions.map((t) => t.role)).toEqual(['reliability_model', 'what_if_scenarios'])
    expect(found?.health).toBe('صحة البيانات')
    expect(findAssetEvidence([run('a', '2026-10-17', 'rail_asset_manager')])?.health).toBeNull()
  })
})
