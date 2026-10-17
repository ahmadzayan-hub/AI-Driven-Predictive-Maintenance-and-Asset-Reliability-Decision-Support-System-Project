/** Entirely fictional design fixtures. No course, customer or live asset data. */
export const SAMPLE_MONTHS = ['2026-04', '2026-05', '2026-06', '2026-07', '2026-08', '2026-09']
export const SITES = ['north', 'central', 'south'] as const
export type Site = typeof SITES[number]
export type Period = 'current' | 'previous' | 'all'
export type EquipmentKind = 'pump' | 'motor' | 'compressor' | 'fan'
export interface SampleAsset { id: string; kind: EquipmentKind; site: Site; health: number; downtime: number[] }
export const SAMPLE_ASSETS: SampleAsset[] = [
  { id: 'PMP-101', kind: 'pump', site: 'north', health: 48, downtime: [12, 11, 14, 18, 21, 24] },
  { id: 'MTR-202', kind: 'motor', site: 'central', health: 57, downtime: [8, 9, 12, 14, 17, 18] },
  { id: 'CMP-301', kind: 'compressor', site: 'south', health: 69, downtime: [14, 12, 13, 11, 10, 9] },
  { id: 'FAN-102', kind: 'fan', site: 'north', health: 72, downtime: [7, 6, 8, 6, 5, 4] },
  { id: 'PMP-203', kind: 'pump', site: 'central', health: 79, downtime: [6, 7, 5, 5, 4, 3] },
  { id: 'MTR-302', kind: 'motor', site: 'south', health: 85, downtime: [4, 5, 4, 3, 3, 2] },
  { id: 'CMP-103', kind: 'compressor', site: 'north', health: 89, downtime: [5, 4, 5, 3, 2, 2] },
  { id: 'FAN-204', kind: 'fan', site: 'central', health: 93, downtime: [3, 3, 2, 2, 1, 1] },
  { id: 'PMP-303', kind: 'pump', site: 'south', health: 88, downtime: [4, 3, 4, 3, 2, 2] },
  { id: 'MTR-104', kind: 'motor', site: 'north', health: 95, downtime: [2, 3, 2, 1, 1, 1] },
  { id: 'CMP-205', kind: 'compressor', site: 'central', health: 91, downtime: [3, 2, 3, 2, 2, 1] },
  { id: 'FAN-304', kind: 'fan', site: 'south', health: 96, downtime: [2, 2, 1, 1, 1, 0] },
]
export const periodIndices = (period: Period) => period === 'current' ? [3, 4, 5] : period === 'previous' ? [0, 1, 2] : [0, 1, 2, 3, 4, 5]
export const severity = (asset: SampleAsset) => asset.health < 60 ? 'critical' : asset.health < 80 ? 'watch' : 'healthy'
export const assetDowntime = (asset: SampleAsset, period: Period) => periodIndices(period).reduce((sum, index) => sum + asset.downtime[index], 0)
export const assetCost = (asset: SampleAsset, period: Period) => periodIndices(period).length * 420 + assetDowntime(asset, period) * 185
export function summarize(assets: SampleAsset[], period: Period) {
  const months = periodIndices(period)
  const downtime = assets.reduce((sum, asset) => sum + assetDowntime(asset, period), 0)
  const planned = assets.length * months.length * 160
  return {
    count: assets.length, downtime,
    availability: planned ? (planned - downtime) / planned * 100 : null,
    cost: assets.reduce((sum, asset) => sum + assetCost(asset, period), 0),
    attention: assets.filter((asset) => severity(asset) !== 'healthy').length,
    series: months.map((index) => ({ month: SAMPLE_MONTHS[index], value: assets.reduce((sum, asset) => sum + asset.downtime[index], 0) })),
  }
}
