import { expect } from '@playwright/test'
import type { APIRequestContext } from '@playwright/test'
import type { ColumnMapping, DatasetDetail, UploadResult } from '../src/shared/types'

/** Persist the deliberate schema shared by the fictional maintenance fixtures.
 * A single-dataset run snapshots its saved mapping; run.breakdown is join-only. */
export async function storeMaintenanceDataset(
  request: APIRequestContext,
  csv: string,
  name: string,
  language: 'en' | 'ar',
  lossMeasured = true,
  currency?: string,
) {
  const uploaded = await request.post('/api/datasets', {
    params: { name, language },
    headers: { 'Content-Type': 'text/csv' },
    data: csv,
  })
  await expect(uploaded).toBeOK()
  const { dataset } = await uploaded.json() as UploadResult
  const mapping: ColumnMapping = {
    roles: {
      month: 'date',
      Site: 'dimension',
      Record_ID: 'ignore',
      Work_Order_Type: 'dimension',
      Downtime_Hours: 'measure',
      Operating_Hours: 'measure',
      Planned_Operating_Hours: 'measure',
      Preventive_WO_Count: 'measure',
      Corrective_WO_Count: 'measure',
      Completed_WO_Count: 'measure',
      First_Time_Fix_Count: 'measure',
      Repeat_Repair_Count: 'measure',
      Overdue_WO_Count: 'measure',
      Maintenance_Cost_USD: 'measure',
      // An entirely blank column cannot be declared a numeric measure.
      // Its raw empty cells remain available to the KPI missingness checks.
      Production_Loss_USD: lossMeasured ? 'measure' : 'ignore',
    },
    measure: 'Downtime_Hours',
    dimension: 'Site',
    date_order: 'auto',
    grain: 'month',
    ...(currency ? { currency } : {}),
  }
  const saved = await request.put(`/api/datasets/${dataset.id}/mapping`, {
    params: { language },
    data: mapping,
  })
  await expect(saved).toBeOK()
  const detail = await saved.json() as DatasetDetail
  expect(detail.mapping).toMatchObject({ ...mapping })
  return dataset.id
}
