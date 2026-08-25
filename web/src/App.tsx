import { useEffect, useMemo, useState } from "react";
import { demoSnapshot } from "./demo";
import type { Quadrant, RotationEvent, SectorState, Snapshot } from "./types";

const labels: Record<Quadrant, string> = { leading: "Leading", weakening: "Weakening", lagging: "Lagging", improving: "Improving" };
const descriptions: Record<Quadrant, string> = {
  leading: "상대강세 · 모멘텀 우위",
  weakening: "상대강세 유지 · 둔화",
  lagging: "상대약세 · 모멘텀 약세",
  improving: "상대약세 · 모멘텀 회복",
};
const tailChoices = [4, 8, 12, 26];
const mark = <span className="atlas-mark" aria-hidden="true" />;

function formatDate(value: string) {
  return new Intl.DateTimeFormat("ko-KR", { year: "numeric", month: "short", day: "numeric", timeZone: "UTC" }).format(new Date(`${value}T00:00:00Z`));
}

function displayStatus(snapshot: Snapshot) {
  const ageDays = Math.floor((Date.now() - new Date(`${snapshot.as_of_week}T00:00:00Z`).getTime()) / 86_400_000);
  if (snapshot.status !== "verified") return { label: snapshot.status.toUpperCase(), tone: "alert", ageDays };
  if (ageDays > 10) return { label: "STALE", tone: "alert", ageDays };
  return { label: "VERIFIED", tone: "verified", ageDays };
}

function getBounds(sectors: SectorState[], tail: number, fixed: boolean) {
  if (fixed) return { min: 92, max: 108 };
  const values = sectors.flatMap((sector) => sector.trail.slice(-(tail + 1)).flatMap((point) => [point.ratio, point.momentum]));
  return { min: Math.min(98, ...values) - 0.45, max: Math.max(102, ...values) + 0.45 };
}

function headingText(heading: number | null) {
  if (heading === null) return "정체";
  if (heading >= 337.5 || heading < 22.5) return "상대강도 개선";
  if (heading < 67.5) return "상대강세·모멘텀 동반 개선";
  if (heading < 112.5) return "모멘텀 개선";
  if (heading < 157.5) return "상대약세 확대";
  if (heading < 202.5) return "동반 약화";
  if (heading < 247.5) return "모멘텀 약화";
  if (heading < 292.5) return "상대강도 회복";
  return "상대강세 유지";
}

function eventTitle(event: RotationEvent) {
  if (event.kind === "quadrant_change") return "사분면 전환";
  if (event.kind === "boundary_approach") return "100선 접근";
  return "강한 회전 이동";
}

function eventText(event: RotationEvent) {
  if (event.kind === "quadrant_change") return `${event.ticker}이(가) ${String(event.previous.quadrant)}에서 ${String(event.current.quadrant)}으로 이동했습니다.`;
  if (event.kind === "boundary_approach") return `${event.ticker}이(가) 100 기준선에 가까워 다음 사분면 전환을 주시할 구간입니다.`;
  return `${event.ticker}이(가) 이번 주 가장 큰 회전 이동군에 포함되었습니다.`;
}

function Canvas({ sectors, active, onPick, tail, fixed }: { sectors: SectorState[]; active: string | null; onPick: (ticker: string) => void; tail: number; fixed: boolean }) {
  const { min, max } = useMemo(() => getBounds(sectors, tail, fixed), [sectors, tail, fixed]);
  const scale = (value: number) => 12 + ((value - min) / (max - min)) * 76;
  const center = scale(100);
  return <svg className="rrg-canvas" viewBox="0 0 100 100" role="img" aria-label="SPY 대비 주간 RRG-style 섹터 지도">
    <rect width="100" height="100" className="paper" />
    <rect x={center} y="8" width={92 - center} height={92 - center} className="q lead" />
    <rect x={center} y={center} width={92 - center} height={92 - center} className="q weak" />
    <rect x="8" y={center} width={center - 8} height={92 - center} className="q lag" />
    <rect x="8" y="8" width={center - 8} height={center - 8} className="q improve" />
    <line x1={center} x2={center} y1="8" y2="92" className="origin" />
    <line x1="8" x2="92" y1={100 - center} y2={100 - center} className="origin" />
    <text x="10" y="13" className="qlabel">IMPROVING</text><text x="90" y="13" textAnchor="end" className="qlabel">LEADING</text>
    <text x="10" y="90" className="qlabel">LAGGING</text><text x="90" y="90" textAnchor="end" className="qlabel">WEAKENING</text>
    {sectors.map((sector) => {
      const display = sector.trail.slice(-(tail + 1));
      const last = display.at(-1)!;
      const previous = display.at(-2);
      const selected = active === sector.ticker;
      return <g key={sector.ticker} className={`sector ${sector.quadrant} ${active && !selected ? "faded" : ""} ${selected ? "selected" : ""}`} tabIndex={0} role="button" onClick={() => onPick(sector.ticker)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") onPick(sector.ticker); }} aria-label={`${sector.ticker}, ${labels[sector.quadrant]}, Ratio ${sector.ratio.toFixed(2)}, Momentum ${sector.momentum.toFixed(2)}`}>
        <title>{`${sector.ticker}: ${labels[sector.quadrant]} · ${headingText(sector.heading_degrees)}`}</title>
        <path className="tail" d={display.map((point, index) => `${index ? "L" : "M"}${scale(point.ratio)} ${100 - scale(point.momentum)}`).join(" ")} />
        {previous && <line className="direction" x1={scale(previous.ratio)} y1={100 - scale(previous.momentum)} x2={scale(last.ratio)} y2={100 - scale(last.momentum)} />}
        <circle className="dot" cx={scale(last.ratio)} cy={100 - scale(last.momentum)} r={selected ? 2.55 : 1.7} />
        <text className="ticker" x={scale(last.ratio) + 2.2} y={100 - scale(last.momentum) - 1.8}>{sector.ticker}</text>
      </g>;
    })}
    <text x="50" y="98" textAnchor="middle" className="axis">RS-RATIO →</text><text x="3" y="50" textAnchor="middle" transform="rotate(-90 3 50)" className="axis">RS-MOMENTUM →</text>
  </svg>;
}

function Detail({ sector, snapshot, tail }: { sector: SectorState; snapshot: Snapshot; tail: number }) {
  const previous = sector.trail.at(-2);
  const ratioChange = previous ? sector.ratio - previous.ratio : null;
  const momentumChange = previous ? sector.momentum - previous.momentum : null;
  return <section className="detail" aria-live="polite">
    <div className="eyebrow">SELECTED SECTOR</div>
    <div className="detail-title"><strong>{sector.ticker}</strong><span>{sector.name}</span></div>
    <span className={`pill ${sector.quadrant}`}>{labels[sector.quadrant]}</span>
    <p>{descriptions[sector.quadrant]} · {headingText(sector.heading_degrees)}</p>
    <dl><div><dt>Ratio</dt><dd>{sector.ratio.toFixed(2)}</dd>{ratioChange !== null && <small>{ratioChange >= 0 ? "+" : ""}{ratioChange.toFixed(2)} WoW</small>}</div><div><dt>Momentum</dt><dd>{sector.momentum.toFixed(2)}</dd>{momentumChange !== null && <small>{momentumChange >= 0 ? "+" : ""}{momentumChange.toFixed(2)} WoW</small>}</div><div><dt>Heading</dt><dd>{sector.heading_degrees?.toFixed(0) ?? "—"}°</dd></div><div><dt>Velocity</dt><dd>{sector.velocity?.toFixed(2) ?? "—"}</dd></div></dl>
    <small>{tail}주 표시 · 기준일 {formatDate(snapshot.as_of_week)}</small>
  </section>;
}

function QualityPanel({ snapshot }: { snapshot: Snapshot }) {
  const checks = Object.entries(snapshot.quality.checks ?? {});
  return <details className="quality-panel"><summary>데이터 검증 내역 <span>{snapshot.quality.publishable ? "전체 통과" : "점검 필요"}</span></summary><div className="quality-list">
    {checks.length ? checks.map(([name, check]) => <div key={name}><b className={check.passed ? "pass" : "fail"}>{check.passed ? "PASS" : "FAIL"}</b><span>{check.message ?? name}</span></div>) : <p>기존 스냅샷입니다. 다음 검증 발행부터 세부 항목이 제공됩니다.</p>}
  </div></details>;
}

export default function App() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(import.meta.env.DEV ? demoSnapshot : null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<Quadrant | "all">("all");
  const [tail, setTail] = useState(12);
  const [active, setActive] = useState<string | null>(null);
  const [fixedScale, setFixedScale] = useState(false);

  useEffect(() => {
    fetch("./data/latest.json", { cache: "no-store" }).then((response) => response.ok ? response.json() : Promise.reject(new Error("No published snapshot"))).then((value: Snapshot) => setSnapshot(value)).catch((value: Error) => { if (!import.meta.env.DEV) setError(value.message); });
  }, []);

  const availableTail = useMemo(() => snapshot ? Math.min(snapshot.tail_weeks ?? 12, ...snapshot.sectors.map((sector) => Math.max(0, sector.trail.length - 1))) : 12, [snapshot]);
  useEffect(() => { if (tail > availableTail) setTail(Math.max(...tailChoices.filter((choice) => choice <= availableTail), 4)); }, [tail, availableTail]);
  const visible = useMemo(() => snapshot?.sectors.filter((sector) => filter === "all" || sector.quadrant === filter) ?? [], [snapshot, filter]);
  useEffect(() => { if ((!active || !visible.some((sector) => sector.ticker === active)) && visible[0]) setActive(visible[0].ticker); }, [visible, active]);

  if (!snapshot) return <main className="empty">{mark}<h1>검증된 스냅샷을 기다리고 있습니다.</h1><p>{error ?? "새 주간 스냅샷이 발행되면 RRG 상황판이 열립니다."}</p></main>;
  const selected = snapshot.sectors.find((sector) => sector.ticker === active) ?? visible[0];
  const status = displayStatus(snapshot);
  const events = snapshot.events ?? [];
  const quadrantCounts = (quadrant: Quadrant) => snapshot.sectors.filter((sector) => sector.quadrant === quadrant).length;
  const transitions = events.filter((event) => event.kind === "quadrant_change").length;
  const boundaries = events.filter((event) => event.kind === "boundary_approach").length;

  return <main className="shell">
    <header><div className="brand">{mark}<span>RRG / ATLAS</span></div><div className={`status ${status.tone}`}><b>{status.label}</b><span>기준일 {formatDate(snapshot.as_of_week)}</span></div></header>
    <section className="intro"><div><div className="eyebrow">US SECTORS · SPY RELATIVE</div><h1>이번 주, 상대강도는<br /><em>어디로 회전했는가.</em></h1><p>{snapshot.frequency} · {snapshot.price_basis.replaceAll("_", " ")} · {snapshot.formula_version}</p></div><div className="freshness"><b>{status.ageDays <= 1 ? "최신" : `${status.ageDays}일 전`}</b><span>{status.tone === "alert" ? "새 검증 스냅샷이 필요합니다." : "검증된 데이터가 공개되었습니다."}</span></div></section>
    {import.meta.env.DEV && <div className="fixture">LOCAL PREVIEW FIXTURE · 실제 시장 데이터가 아닙니다.</div>}
    {status.tone === "alert" && <section className="alert-banner"><b>데이터 신선도 점검 필요</b><span>마지막 정상 스냅샷은 {formatDate(snapshot.as_of_week)} 기준입니다. 새 발행 전까지 이 값을 유지합니다.</span></section>}

    <section className="summary-grid" aria-label="이번 주 요약"><article><span>LEADING</span><strong>{quadrantCounts("leading")}</strong><small>상대강세·모멘텀 우위</small></article><article><span>사분면 전환</span><strong>{transitions}</strong><small>이전 검증 주 대비</small></article><article><span>100선 접근</span><strong>{boundaries}</strong><small>다음 전환 주시</small></article><article><span>품질 게이트</span><strong>{snapshot.quality.publishable ? "PASS" : "HOLD"}</strong><small>{snapshot.quality.symbols_received}/{snapshot.quality.symbols_expected} 시리즈</small></article></section>

    <section className="event-section"><div className="section-heading"><div><div className="eyebrow">THIS WEEK'S SIGNALS</div><h2>먼저 확인할 회전 이벤트</h2></div><span>{events.length} events</span></div>{events.length ? <div className="event-grid">{events.slice(0, 6).map((event) => <button key={event.event_id} className={`event-card ${event.severity}`} onClick={() => { setFilter("all"); setActive(event.ticker); }}><span className="event-kind">{eventTitle(event)}</span><strong>{event.ticker}</strong><p>{eventText(event)}</p></button>)}</div> : <div className="event-empty">이전 검증 스냅샷과의 비교 이벤트는 다음 발행부터 누적됩니다.</div>}</section>

    <nav className="controls" aria-label="RRG 표시 제어"><div className="filters">{(["all", "leading", "weakening", "lagging", "improving"] as const).map((value) => <button className={filter === value ? "active" : ""} key={value} onClick={() => setFilter(value)}>{value === "all" ? "All" : labels[value]}</button>)}</div><div className="tails"><span>Tail</span>{tailChoices.map((value) => <button disabled={value > availableTail} className={tail === value ? "active" : ""} key={value} onClick={() => setTail(value)}>{value}</button>)}<button className={fixedScale ? "active" : ""} onClick={() => setFixedScale((value) => !value)}>{fixedScale ? "Fixed scale" : "Auto scale"}</button></div></nav>

    <section className="layout"><div className="map"><Canvas sectors={visible} active={selected?.ticker ?? null} onPick={setActive} tail={tail} fixed={fixedScale} /><small>{visible.length} sectors shown · {tail}W display · {fixedScale ? "fixed 92–108 scale" : "auto scale"}</small></div><aside>{selected && <Detail sector={selected} snapshot={snapshot} tail={tail} />}<section className="ledger"><div className="eyebrow">ROTATION LEDGER</div>{snapshot.sectors.map((sector) => <button className={`row ${sector.ticker === selected?.ticker ? "active" : ""}`} key={sector.ticker} onClick={() => { setFilter("all"); setActive(sector.ticker); }}><i className={sector.quadrant} /><strong>{sector.ticker}</strong><span>{labels[sector.quadrant]}</span><em>{sector.ratio.toFixed(1)} / {sector.momentum.toFixed(1)}</em></button>)}</section></aside></section>
    {selected && <section className="mobile-detail"><Detail sector={selected} snapshot={snapshot} tail={tail} /></section>}
    <QualityPanel snapshot={snapshot} />
    <footer><span>Snapshot {snapshot.snapshot_id} · benchmark {snapshot.benchmark}</span><span>기준일·검증·회전 이벤트를 함께 확인하세요.</span></footer>
  </main>;
}
