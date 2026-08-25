import { useEffect, useMemo, useState } from "react";
import { demoSnapshot } from "./demo";
import { RRGChart } from "./RRGChart";
import type { Quadrant, RotationEvent, SectorState, Snapshot } from "./types";

const tailChoices = [4, 8, 12, 16];
const quadrantLabels: Record<Quadrant, string> = { leading: "상승주도", weakening: "둔화", lagging: "약세", improving: "개선" };
const filterLabels: Record<Quadrant, string> = { leading: "주도", weakening: "둔화", lagging: "약세", improving: "개선" };
const sectorLabels: Record<string, string> = {
  XLB: "소재", XLC: "커뮤니케이션", XLY: "경기소비재", XLP: "필수소비재", XLE: "에너지", XLF: "금융",
  XLV: "헬스케어", XLI: "산업재", XLK: "정보기술", XLRE: "부동산", XLU: "유틸리티",
};
const sectorLabel = (ticker: string, fallback = ticker) => sectorLabels[ticker] ?? fallback;

function formatDate(value: string) {
  return new Intl.DateTimeFormat("ko-KR", { year: "numeric", month: "long", day: "numeric", timeZone: "UTC" }).format(new Date(`${value}T00:00:00Z`));
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
  if (event.kind === "quadrant_change") return `${quadrantLabels[event.previous.quadrant as Quadrant]} → ${quadrantLabels[event.current.quadrant as Quadrant]}`;
  if (event.kind === "boundary_approach") return "다음 사분면 진입 여부를 확인하세요";
  return "이번 주 이동 폭 상위권";
}

function direction(heading: number | null) {
  if (heading === null) return "방향 관찰";
  if (heading >= 337.5 || heading < 22.5) return "상대 강도 개선";
  if (heading < 67.5) return "동반 개선";
  if (heading < 112.5) return "상대 모멘텀 개선";
  if (heading < 157.5) return "상대 강도 둔화";
  if (heading < 202.5) return "동반 약화";
  if (heading < 247.5) return "상대 강도 회복";
  if (heading < 292.5) return "모멘텀 회복";
  return "강세 유지";
}

function quadrantFor(ratio: number, momentum: number): Quadrant {
  if (ratio >= 100 && momentum >= 100) return "leading";
  if (ratio >= 100) return "weakening";
  if (momentum >= 100) return "improving";
  return "lagging";
}

function arrowForHeading(heading: number | null) {
  if (heading === null) return "—";
  const arrows = ["→", "↗", "↑", "↖", "←", "↙", "↓", "↘"];
  return arrows[Math.round(heading / 45) % 8];
}

function SignedDelta({ value }: { value: number }) {
  return <span className={value >= 0 ? "positive" : "negative"}>{value >= 0 ? "+" : ""}{value.toFixed(2)}</span>;
}

function SectorDetail({ sector, tail }: { sector: SectorState; tail: number }) {
  const previous = sector.trail.at(-2);
  const start = sector.trail.at(-(tail + 1)) ?? sector.trail[0]!;
  const ratioChange = previous ? sector.ratio - previous.ratio : 0;
  const momentumChange = previous ? sector.momentum - previous.momentum : 0;
  const ratioWindow = sector.ratio - start.ratio;
  const momentumWindow = sector.momentum - start.momentum;
  const startQuadrant = quadrantFor(start.ratio, start.momentum);
  const distance = Math.hypot(ratioWindow, momentumWindow);

  return <section className="detail-card" aria-live="polite">
    <div className="panel-label">선택 섹터</div>
    <div className="detail-top"><div><h2>{sectorLabel(sector.ticker, sector.name)}</h2><p><code>{sector.ticker}</code> · {sector.name}</p></div><span className={`quadrant-badge ${sector.quadrant}`}>{quadrantLabels[sector.quadrant]}</span></div>
    <div className="direction-line"><span className="direction-arrow" aria-hidden="true">{arrowForHeading(sector.heading_degrees)}</span><strong>{direction(sector.heading_degrees)}</strong><span>속도 {sector.velocity?.toFixed(2) ?? "—"}</span></div>
    <dl className="metric-grid"><div><dt>RS-RATIO</dt><dd>{sector.ratio.toFixed(2)}</dd><small><SignedDelta value={ratioChange} /> 최근 1주</small></div><div><dt>RS-MOMENTUM</dt><dd>{sector.momentum.toFixed(2)}</dd><small><SignedDelta value={momentumChange} /> 최근 1주</small></div></dl>
    <div className="trajectory-summary"><div><span>최근 {tail}주</span><strong>{quadrantLabels[startQuadrant]} <b>→</b> {quadrantLabels[sector.quadrant]}</strong></div><div><span>이동 거리</span><strong>{distance.toFixed(2)}</strong></div><div className="trajectory-deltas"><span>Ratio <SignedDelta value={ratioWindow} /></span><span>Momentum <SignedDelta value={momentumWindow} /></span></div></div>
  </section>;
}

function SignalDocket({ events, sectors, onPick }: { events: RotationEvent[]; sectors: SectorState[]; onPick: (ticker: string) => void }) {
  return <section className="signal-docket" aria-labelledby="signal-title">
    <div className="docket-head"><div><div className="panel-label">주간 관찰</div><h2 id="signal-title">우선 확인</h2></div><span>{events.length}</span></div>
    {events.length ? <div className="docket-list">{events.map((event) => <button key={event.event_id} className="signal-row" onClick={() => onPick(event.ticker)}><span className={`event-pin ${event.severity}`} aria-hidden="true" /><span className="signal-copy"><strong>{sectorLabel(event.ticker, sectors.find((sector) => sector.ticker === event.ticker)?.name)}</strong><small><code>{event.ticker}</code> · {eventLabel(event)}</small></span><span className="signal-detail">{eventDetail(event)}</span></button>)}</div> : <p className="empty-docket">이번 주에 표시할 별도 이벤트가 없습니다.</p>}
  </section>;
}

function SectorNavigator({ sectors, selected, onPick }: { sectors: SectorState[]; selected: string | undefined; onPick: (ticker: string) => void }) {
  return <section className="sector-navigator" aria-labelledby="navigator-title">
    <div className="docket-head"><div><div className="panel-label">전체 섹터</div><h2 id="navigator-title">Sector list</h2></div><span>{sectors.length}</span></div>
    <div className="sector-list">{sectors.map((sector) => <button key={sector.ticker} className={`${sector.ticker === selected ? "active" : ""} ${sector.quadrant}`} aria-pressed={sector.ticker === selected} onClick={() => onPick(sector.ticker)}><span className="sector-dot" /><span className="sector-name"><strong>{sectorLabel(sector.ticker, sector.name)}</strong><small>{sector.ticker}</small></span><span className="sector-state">{filterLabels[sector.quadrant]}</span></button>)}</div>
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
  const usesSmoothedTrail = tail >= 12;
  const smoothingLabel = tail >= 16 ? " · 2주 간격 실제 관측점" : " · 3주 평균 직선 경로";
  const selectSector = (ticker: string) => { setFilter("all"); setActive(ticker); };

  return <main className="atlas-shell">
    <header className="topbar"><a className="brand" href="./" aria-label="RRG Atlas 처음으로"><span>RRG</span><strong>Sector Monitor</strong></a><div className="top-meta"><span>US SECTORS / SPY</span><span className={`status-dot ${status.stale ? "stale" : ""}`}><i />{status.stale ? "검증 필요" : "검증 완료"}</span></div></header>
    <section className="page-title"><div><p className="eyebrow">WEEKLY RELATIVE STRENGTH</p><h1>US Sector Rotation</h1><p>SPY 대비 11개 섹터의 상대 강도와 변화를 추적합니다.</p></div><dl className="snapshot-meta"><div><dt>기준일</dt><dd>{formatDate(snapshot.as_of_week)}</dd></div><div><dt>스냅샷</dt><dd>{snapshot.snapshot_id}</dd></div><div><dt>데이터</dt><dd>{snapshot.quality.symbols_received}/{snapshot.quality.symbols_expected} series</dd></div></dl></section>

    <section className="dashboard-grid">
      <section className="map-workspace" aria-label="RRG 섹터 지도">
        <header className="workspace-head"><div><div className="panel-label">RRG MAP</div><h2>섹터 상대 회전</h2><p><b>○</b> 시작 · <b>→</b> 최근 이동 · <b>●</b> 최신 위치{usesSmoothedTrail && <em>{smoothingLabel}</em>}</p></div><div className="legend" aria-label="사분면 범례"><span className="leading">주도</span><span className="weakening">둔화</span><span className="lagging">약세</span><span className="improving">개선</span></div></header>
        <div className="workspace-controls"><div className="filter-control" role="group" aria-label="사분면 필터">{(["all", "leading", "weakening", "lagging", "improving"] as const).map((value) => <button key={value} className={filter === value ? "active" : ""} aria-pressed={filter === value} onClick={() => setFilter(value)}>{value === "all" ? "전체" : filterLabels[value]}</button>)}</div><div className="tail-control" role="group" aria-label="표시 기간">{tailChoices.map((value) => <button key={value} disabled={value > availableTail} className={tail === value ? "active" : ""} aria-pressed={tail === value} onClick={() => setTail(value)}>{value}주</button>)}</div></div>
        <div className="chart-frame"><RRGChart sectors={visible} active={selected?.ticker ?? null} tail={tail} onPick={setActive} /></div>
        <footer className="map-footer"><span>{visible.length}개 섹터 표시</span><span>기준선 100 · 주간 조정종가</span></footer>
      </section>
      <aside className="analysis-rail">{selected && <SectorDetail sector={selected} tail={tail} />}<SignalDocket events={signals} sectors={snapshot.sectors} onPick={selectSector} /><SectorNavigator sectors={snapshot.sectors} selected={selected?.ticker} onPick={selectSector} /></aside>
    </section>
    <footer className="app-footer"><span>Relative strength proxy · weekly adjusted close</span><span>Data refreshed {status.days}일 전</span></footer>
  </main>;
}
