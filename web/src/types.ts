export type Quadrant = "leading" | "weakening" | "lagging" | "improving";
export type SnapshotStatus = "verified" | "stale" | "partial" | "recalculating" | "failed";
export type EventKind = "quadrant_change" | "boundary_approach" | "strong_move";
export type EventSeverity = "high" | "medium" | "low";

export interface RRGPoint { week: string; ratio: number; momentum: number; }
export interface SectorState { ticker: string; name: string; ratio: number; momentum: number; quadrant: Quadrant; heading_degrees: number | null; velocity: number | null; trail: RRGPoint[]; }
export interface QualityCheck { passed: boolean; observed?: unknown; expected?: unknown; message?: string; }
export interface Quality { symbols_expected: number; symbols_received: number; dates_aligned: boolean; publishable: boolean; checks?: Record<string, QualityCheck>; }
export interface RotationEvent { event_id: string; kind: EventKind; severity: EventSeverity; ticker: string; message: string; previous: Record<string, unknown>; current: Record<string, unknown>; }
export interface Snapshot {
  snapshot_id: string;
  status: SnapshotStatus;
  as_of_week: string;
  generated_at: string;
  universe_id: string;
  benchmark: string;
  frequency: "weekly";
  price_basis: string;
  formula_version: string;
  tail_weeks: number;
  default_tail_weeks?: number;
  sectors: SectorState[];
  quality: Quality;
  events?: RotationEvent[];
  previous_snapshot_id?: string | null;
  provenance?: Record<string, unknown>;
}
