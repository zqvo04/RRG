import { useEffect, useMemo, useState } from "react";
import { demoSnapshot } from "./demo";
import { RRGChart } from "./RRGChart";
import type { Quadrant, RotationEvent, SectorState, Snapshot } from "./types";

const labels: Record<Quadrant, string> = { leading: "Leading", weakening: "Weakening", lagging: "Lagging", improving: "Improving" };
const tailChoices = [4, 8, 12];
const mark = <span className="atlas-mark" aria-hidden="true" />;

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

function eventCopy(event: RotationEvent) {
  if (event.kind === "quadrant_change") return `${String(event.previous.quadrant)} → ${String(event.current.quadrant)}`;
  if (event.kind === "boundary_approach") return "기준선 인접";
  return "주간 이동 상위권";
}

function direction(heading: number | null) {
  if (heading === null) return "정체";
  if (heading >= 337.5 || heading < 22.5) return "강도 개선";
  if (heading < 67.5) return "동반 개선";
  if (heading < 112.5) return "모멘텀 개선";
  if (heading < 157.5) return "강도 약화";
  if (heading < 202.5) return "동반 약화";
  if (heading < 247.5) return "모멘텀 약화";
  if (heading < 292.5) return "강도 회복";
  return "강세 유지";
}

function SectorDetail({ sector }: { sector: SectorState }) {
  const prior = sector.trail.at(-2);
  const ratioDelta = prior ? sector.ratio - prior.ratio : 0;
  const momentumDelta = prior ? sector.momentum - prior.momentum : 0;
  return <section className="sector-detail">
    <div className="detail-heading"><div><span className="eyebrow">SELECTED</span><h2>{sector.ticker}</h2></div><span className={`quadrant ${sector.quadrant}`}>{labels[sector.quadrant]}</span></div>
    <p className="sector-name">{sector.name} · {direction(sector.heading_degrees)}</p>
    <dl><div><dt>Ratio</dt><dd>{sector.ratio.toFixed(2)} <small className={ratioDelta >= 0 ? "up" : "down"}>{ratioDelta >= 0 ? "+" : ""}{ratioDelta.toFixed(2)}</small></dd></div><div><dt>Momentum</dt><dd>{sector.momentum.toFixed(2)} <small className={momentumDelta >= 0 ? "up" : "down"}>{momentumDelta >= 0 ? "+" : ""}{momentumDelta.toFixed(2)}</small></dd></div></dl>
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
  useEffect(() => { if (tail > availableTail) setTail(Math.max(...tailChoices.filter((choice) => choice <= availableTail), 4)); }, [tail, availableTail]);
  const visible = useMemo(() => snapshot?.sectors.filter((sector) => filter === "all" || sector.quadrant === filter) ?? [], [snapshot, filter]);
  useEffect(() => { if ((!active || !visible.some((sector) => sector.ticker === active)) && visible[0]) setActive(visible[0].ticker); }, [visible, active]);

  if (!snapshot) return <main className="empty">{mark}<h1>검증된 스냅샷을 기다리고 있습니다.</h1><p>{error ?? "새 주간 스냅샷이 발행되면 RRG 지도가 열립니다."}</p></main>;
  const selected = snapshot.sectors.find((sector) => sector.ticker === active) ?? visible[0];
  const status = freshness(snapshot);
  const events = (snapshot.events ?? []).slice(0, 3);

  return <main className="app-shell">
    <header className="topbar"><div className="brand">{mark}<span>RRG / ATLAS</span></div><div className={`data-status ${status.stale ? "stale" : ""}`}><b>{status.stale ? "STALE" : "VERIFIED"}</b><span>{formatDate(snapshot.as_of_week)} · {status.days}d</span></div></header>
    <section className="context"><div><p className="eyebrow">US SECTORS · SPY RELATIVE</p><h1>섹터 회전 지도</h1></div><p>점은 현재 위치, 선은 지난 {tail}주 궤적입니다.</p></section>
    {status.stale && <div className="stale-note">최신 검증 스냅샷이 지연되었습니다. 마지막 정상 데이터는 {formatDate(snapshot.as_of_week)} 기준입니다.</div>}

    <section className="workspace">
      <section className="chart-card"><div className="chart-toolbar"><div className="filters" aria-label="사분면 필터">{(["all", "leading", "weakening", "lagging", "improving"] as const).map((value) => <button key={value} className={filter === value ? "active" : ""} onClick={() => setFilter(value)}>{value === "all" ? "All" : labels[value]}</button>)}</div><div className="tail-control" aria-label="표시 기간"><span>Tail</span>{tailChoices.map((value) => <button key={value} disabled={value > availableTail} className={tail === value ? "active" : ""} onClick={() => setTail(value)}>{value}W</button>)}</div></div><RRGChart sectors={visible} active={selected?.ticker ?? null} tail={tail} onPick={setActive} /><div className="chart-caption"><span>{visible.length} sectors</span><span>Ratio · Momentum 기준선 100</span></div></section>
      <aside className="side-card"><div className="sector-list"><p className="eyebrow">SECTORS</p>{snapshot.sectors.map((sector) => <button key={sector.ticker} className={sector.ticker === selected?.ticker ? "selected" : ""} onClick={() => { setFilter("all"); setActive(sector.ticker); }}><i className={sector.quadrant} /><strong>{sector.ticker}</strong><span>{labels[sector.quadrant]}</span></button>)}</div>{selected && <SectorDetail sector={selected} />}</aside>
    </section>

    <section className="signal-strip"><div className="signal-heading"><div><p className="eyebrow">THIS WEEK</p><h2>주요 신호</h2></div><span className={snapshot.quality.publishable ? "quality-pass" : "quality-hold"}>{snapshot.quality.publishable ? "DATA CHECKED" : "DATA HOLD"} · {snapshot.quality.symbols_received}/{snapshot.quality.symbols_expected}</span></div>{events.length ? <div className="signals">{events.map((event) => <button key={event.event_id} onClick={() => { setFilter("all"); setActive(event.ticker); }}><span className={`signal-dot ${event.severity}`} /><strong>{event.ticker}</strong><span>{eventLabel(event)}</span><em>{eventCopy(event)}</em></button>)}</div> : <p className="no-signals">이전 검증 스냅샷과의 비교 신호가 아직 없습니다.</p>}</section>
    <footer><span>Snapshot {snapshot.snapshot_id}</span><span>RRG-style proxy · weekly adjusted close</span></footer>
  </main>;
}
