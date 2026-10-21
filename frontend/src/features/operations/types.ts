export type OperationsRole = 'owner' | 'manager' | 'technician' | 'viewer'
export type Priority = 'low' | 'medium' | 'high' | 'critical'
export type OrderStatus = 'draft' | 'authorized' | 'in_progress' | 'completed' | 'cancelled'
export interface Organization { id: string; name: string; version: number; role: OperationsRole }
export interface Member { subject: string; role: OperationsRole }
export interface Site { id: string; name: string; code: string }
export interface Asset { id: string; site_id: string; name: string; external_id: string; source_system: string; criticality: Priority }
export interface Completion { outcome: string; notes: string; labor_hours: number; parts: Array<{ part: string; quantity: number }> }
export interface WorkOrder {
  id: string; asset_id: string; title: string; rationale: string; priority: Priority;
  status: OrderStatus; assignee: string | null; due_date: string | null; version: number;
  evidence: { run_id: string; run_updated_at: string; dataset_sha256: string; asset_column: string; source_asset_id: string; matching_records: number; captured_at: string }; completion: Partial<Completion>;
  audit: Array<{ id: string; action: string; actor: string; created_at: string; version: number; detail: unknown }>;
}
export interface OperationsOverview {
  principal_subject: string;
  organization: Organization; members: Member[]; sites: Site[]; assets: Asset[];
  work_orders: WorkOrder[];
  work_order_count: number; work_orders_truncated: boolean;
  permissions: { read: boolean; write: boolean; manage: boolean; authorize: boolean };
}
export interface DraftOrder {
  asset_id: string; title: string; rationale: string; run_id: string; asset_column: string;
  source_asset_id: string; priority: Priority; assignee: string; due_date: string;
}
export interface OrderChange {
  expected_version: number; status?: OrderStatus; assignee?: string; due_date?: string;
  priority?: Priority; completion?: Completion;
}
export interface Readiness {
  execution: { mode: 'client' | 'worker'; ready: boolean; last_seen_at: string | null };
  checks: Array<{ id: 'managed_identity' | 'background_execution' | 'registered_assets' | 'maintenance_action_closed' | 'validation_protocol_registered'; observed: boolean }>;
}
