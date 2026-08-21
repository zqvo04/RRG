export type Quadrant = "leading" | "weakening" | "lagging" | "improving";
export type SnapshotStatus = "verified" | "stale" | "partial" | "recalculating";
export interface RRGPoint { week: string; ratio: number; momentum: number; }
export interface SectorState { ticker: string; name: string; ratio: number; momentum: number; quadrant: Quadrant; heading_degrees: number | null; velocity: number | null; trail: RRGPoint[]; }
export interface Snapshot { snapshot_id: string; status: SnapshotStatus; as_of_week: string; generated_at: string; universe_id: string; benchmark: string; frequency: "weekly"; price_basis: string; formula_version: string; tail_weeks: number; sectors: SectorState[]; quality: Record<string, unknown>; }

