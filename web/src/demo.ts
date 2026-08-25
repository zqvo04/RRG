import type { Quadrant, Snapshot } from "./types";

const source = [["XLB", "Materials", "leading"], ["XLC", "Communication Services", "weakening"], ["XLY", "Consumer Discretionary", "improving"], ["XLP", "Consumer Staples", "leading"], ["XLE", "Energy", "lagging"], ["XLF", "Financials", "weakening"], ["XLV", "Health Care", "leading"], ["XLI", "Industrials", "improving"], ["XLK", "Information Technology", "weakening"], ["XLRE", "Real Estate", "lagging"], ["XLU", "Utilities", "improving"]] as const;
const centers: Record<Quadrant, [number, number]> = { leading: [101.9, 101.6], weakening: [101.7, 98.8], lagging: [98.1, 98.3], improving: [98.4, 101.2] };

export const demoSnapshot: Snapshot = {
  snapshot_id: "LOCAL-PREVIEW",
  status: "verified",
  as_of_week: "2026-08-21",
  generated_at: "2026-08-22T08:49:16.000Z",
  universe_id: "demo_fixture",
  benchmark: "SPY",
  frequency: "weekly",
  price_basis: "fixture",
  formula_version: "rrg_proxy_v2",
  tail_weeks: 26,
  default_tail_weeks: 12,
  quality: {
    symbols_expected: 12,
    symbols_received: 12,
    dates_aligned: true,
    publishable: true,
    checks: {
      date_alignment: { passed: true, message: "모든 섹터가 동일한 완료 주차에 정렬되었습니다." },
      history_length: { passed: true, message: "모든 시리즈가 최소 이력을 충족합니다." },
    },
  },
  events: [
    { event_id: "demo-transition", kind: "quadrant_change", severity: "high", ticker: "XLK", message: "XLK moved to weakening.", previous: { quadrant: "leading" }, current: { quadrant: "weakening" } },
    { event_id: "demo-boundary", kind: "boundary_approach", severity: "medium", ticker: "XLY", message: "XLY is close to the 100 baseline.", previous: {}, current: {} },
  ],
  sectors: source.map(([ticker, name, quadrant], index) => {
    const [ratio, momentum] = centers[quadrant];
    const sign = index % 2 ? 1 : -1;
    const trail = Array.from({ length: 27 }, (_, i) => ({ week: `2026-W${i}`, ratio: ratio - sign * (26 - i) * 0.07 + (index % 3) * 0.03, momentum: momentum - sign * (26 - i) * 0.05 + (index % 4) * 0.02 }));
    const now = trail.at(-1)!;
    return { ticker, name, quadrant, ratio: now.ratio, momentum: now.momentum, heading_degrees: sign > 0 ? 42 : 218, velocity: 0.27, trail };
  }),
};
