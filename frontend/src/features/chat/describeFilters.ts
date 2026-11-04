import type { DataContext } from '../../shared/types'

/** Filters as a reader says them: "Site: North, South · Cost ≥ 100". */
export function describeFilters(filters: DataContext['filters'] | undefined): string {
  const ops: Record<string, string> = { ne: '≠', gt: '>', gte: '≥', lt: '<', lte: '≤', not_in: '∉', empty: '= ∅', not_empty: '≠ ∅' }
  return (filters ?? []).map(f => {
    const values = (f.values ?? (f.value === undefined ? [] : [f.value])).join(', ')
    return ops[f.op] ? `${f.column} ${ops[f.op]} ${values}`.trim() : `${f.column}: ${values}`
  }).join(' · ')
}
