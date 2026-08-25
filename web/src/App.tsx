import { useEffect, useMemo, useState } from "react";
import { demoSnapshot } from "./demo";
import { RRGChart } from "./RRGChart";
import type { Quadrant, RotationEvent, SectorState, Snapshot } from "./types";

const labels: Record<Quadrant, string> = { leading: "Leading", weakening: "Weakening", lagging: "Lagging", improving: "Improving" };
const shortLabels: Record<Quadrant, string> = { leading: "Lead", weakening: "Weak", lagging: "Lag", improving: "Improve" };
const tailChoices = [4, 8, 12];

function formatDate(value: string) {
  return new Intl.DateTimeFormat("ko-KR", { year: "numeric", month: "short", day: "numeric", timeZone: "UTC" }).format(new Date(`${value}T00:00:00Z`));
}

function freshness(snapshot: Snapshot) {
  const days = Math.floor((Date.now() - new Date(`${snapshot.as_of_week}T00:00:00Z`).getTime()) / 86_400_000);
  return { days, stale: snapshot.status !== "verified" || days > 10 };
}

function eventLabel(event: RotationEvent) {
  if (event.kind === "quadrant_change") return "사분면 전환";
  if (event.kind === "boundary_approach") return "100선 접근";
  return "강한 이동";
}

function eventDetail(event: RotationEvent) {
  if (event.kind === "quadrant_change") return `${String(event.previous.quadrant)} → ${String(event.current.quadrant)}`;
  if (event.kind === "boundary_approach") return "다음 사분면을 주시하세요";
  return "이번 주 이동 폭 상위권";
}

function direction(heading: number | null) {
  if (heading === null) return "정체";
  if (heading >= 337.5 || heading < 22.5) return "강도 개선";
  if (heading < 67.5) return "동반 개선";
  if (heading < 112.5) return "모멘텀 개선";
  if (heading < 157.5) return "강도 약화";
  if (heading < 202.5) return "동반 약화";
  if (heading < 247.5) return "강도 회복";
  if (heading < 292.5) return "강도 회복";
  return "강세 유지";
}

function SectorDetail({ sector }: { sector: SectorState }) {
  const previous = sector.trail.at(-2);
  const ratioChange = previous ? sector.ratio - previous.ratio : 0;
  const momentumChange = previous ? sector.momentum - previous.momentum : 0;
  return <section className="detail-card" aria-live="polite">
    <div className="detail-top"><div><p className="section-kicker">SELECTED SECTOR</p><h2>{sector.ticker}</h2><p>{sector.name}</p></div><span className={`quadrant-badge ${sector.quadrant}`}>{labels[sector.quadrant]}</span></div>
    <div className="direction-line"><span className="direction-arrow" aria-hidden="true">↗</span><span>{direction(sector.heading_degrees)}</span><span>·</span><span>속도 {sector.velocity?.toFixed(2) ?? "—"}</span></div>
    <div className="metric-grid"><div><span>RS-RATIO</span><strong>{sector.ratio.toFixed(2)}</strong><small className={ratioChange >= 0 ? "positive" : "negative"}>{ratioChange >= 0 ? "+" : ""}{ratioChange.toFixed(2)} 주간</small></div><div><span>RS-MOMENTUM</span><strong>{sector.momentum.toFixed(2)}</strong><small className={momentumChange >= 0 ? "positive" : "negative"}>{momentumChange >= 0 ? "+" : ""}{momentumChange.toFixed(2)} 주간</small></div></div>
  </section>;
}

export default function App() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(import.meta.env.DEV ? demoSnapshot : null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<Quadrant | "all">("all");
  const [tail, setTail] = useState(8);
  const [active, setActive] = useState<string | null>(null);

  useEffect(() => {
    fetch("./data/latest.json", { cache: "no-store" }).then((response) => response.ok ? response.json() : Promise.reject(new Error("No published snapshot"))).then((value: Snapshot) => setSnapshot(value)).catch((reason: Error) => { if (!import.meta.env.DEV) setError(reason.message); });
  }, []);

  const availableTail = useMemo(() => snapshot ? Math.min(snapshot.tail_weeks ?? 12, ...snapshot.sectors.map((sector) => Math.max(0, sector.trail.length - 1))) : 12, [snapshot]);
  const visible = useMemo(() => snapshot?.sectors.filter((sector) => filter === "all" || sector.quadrant === filter) ?? [], [snapshot, filter]);
  useEffect(() => { if (tail > availableTail) setTail(Math.max(...tailChoices.filter((choice) => choice <= availableTail), 4)); }, [tail, availableTail]);
  useEffect(() => { if ((!active || !visible.some((sector) => sector.ticker === active)) && visible[0]) setActive(visible[0].ticker); }, [visible, active]);

  if (!snapshot) return <main className="empty-state"><h1>검증된 스냅샷을 기다리고 있습니다.</h1><p>{error ?? "새 주간 스냅샷이 발행되면 RRG 지도가 열립니다."}</p></main>;
  const status = freshness(snapshot);
  const selected = snapshot.sectors.find((sector) => sector.ticker === active) ?? visible[0];
  const signals = (snapshot.events ?? []).slice(0, 3);

  return <main className="atlas-shell">
    <header className="app-header"><div className="identity"><span className="brand-mark" aria-hidden="true"><i /></span><div><p>SECTOR RELATIVE STRENGTH</p><h1>RRG Atlas</h1></div></div><div className={`status-block ${status.stale ? "stale" : ""}`}><span className="status-light" /><div><strong>{status.stale ? "Data stale" : "Data verified"}</strong><small>{formatDate(snapshot.as_of_week)} · {status.days}일 전</small></div></div></header>

    <section className="signal-band" aria-labelledby="signals-title"><div className="signal-intro"><p className="section-kicker">THIS WEEK</p><h2 id="signals-title">핵심 신호</h2><span className={snapshot.quality.publishable ? "data-check pass" : "data-check hold"}>{snapshot.quality.publishable ? "검증 통과" : "검증 보류"} · {snapshot.quality.symbols_received}/{snapshot.quality.symbols_expected}</span></div><div className="signal-list">{signals.length ? signals.map((event) => <button key={event.event_id} className="signal-item" onClick={() => { setFilter("all"); setActive(event.ticker); }}><span className={`event-pin ${event.severity}`} aria-hidden="true" /><div><strong>{event.ticker}</strong><span>{eventLabel(event)}</span></div><small>{eventDetail(event)}</small></button>) : <p className="no-signal">표시할 비교 신호가 없습니다.</p>}</div></section>

    <section className="workspace-grid"><section className="chart-panel" aria-label="RRG sector map"><div className="panel-header"><div><p className="section-kicker">MARKET MAP</p><h2>섹터 회전</h2><span>점은 현재 위치, 선은 최근 {tail}주 흐름입니다.</span></div><div className="legend" aria-label="사분면 범례"><span className="leading">Leading</span><span className="weakening">Weakening</span><span className="lagging">Lagging</span><span className="improving">Improving</span></div></div><div className="control-stack"><div className="segmented-control" role="group" aria-label="사분면 필터">{(["all", "leading", "weakening", "lagging", "improving"] as const).map((value) => <button key={value} className={filter === value ? "active" : ""} aria-pressed={filter === value} onClick={() => setFilter(value)}>{value === "all" ? "All" : shortLabels[value]}</button>)}</div><div className="segmented-control compact" role="group" aria-label="표시 기간">{tailChoices.map((value) => <button key={value} disabled={value > availableTail} className={tail === value ? "active" : ""} aria-pressed={tail === value} onClick={() => setTail(value)}>{value}W</button>)}</div></div><div className="chart-frame"><RRGChart sectors={visible} active={selected?.ticker ?? null} tail={tail} onPick={setActive} /></div><div className="chart-note"><span>{visible.length}개 섹터 표시</span><span>기준선 100 · SPY 대비</span></div></section>

      <aside className="inspector-panel">{selected && <SectorDetail sector={selected} />}<section className="sector-navigator"><div className="navigator-head"><p className="section-kicker">SECTOR NAVIGATOR</p><span>{snapshot.sectors.length}</span></div><div className="sector-grid">{snapshot.sectors.map((sector) => <button key={sector.ticker} className={`${sector.ticker === selected?.ticker ? "active" : ""} ${sector.quadrant}`} aria-pressed={sector.ticker === selected?.ticker} onClick={() => { setFilter("all"); setActive(sector.ticker); }}><span className="sector-dot" /><strong>{sector.ticker}</strong><small>{shortLabels[sector.quadrant]}</small></button>)}</div></section></aside>
    </section>

    <footer className="app-footer"><span>Snapshot {snapshot.snapshot_id}</span><span>Weekly adjusted close · RRG-style proxy</span></footer>
  </main>;
}
