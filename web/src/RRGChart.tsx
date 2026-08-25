import { useMemo } from "react";
import type { SectorState } from "./types";

const quadrantLabels = { leading: "LEADING", weakening: "WEAKENING", lagging: "LAGGING", improving: "IMPROVING" } as const;

type PlotPoint = { ratio: number; momentum: number };

type Series = {
  sector: SectorState;
  displayTrail: PlotPoint[];
  start: PlotPoint;
  latest: PlotPoint;
};

function sampleTrail(points: PlotPoint[], step: number) {
  if (step <= 1 || points.length <= step + 1) return points;
  return points.filter((_, index) => index === 0 || index === points.length - 1 || index % step === 0);
}

function domainFor(trails: PlotPoint[][]) {
  const values = trails.flatMap((trail) => trail.flatMap((point) => [point.ratio, point.momentum]));
  const rawMin = Math.min(100, ...values);
  const rawMax = Math.max(100, ...values);
  const padding = Math.max(1.5, (rawMax - rawMin) * 0.12);
  return { min: Math.floor((rawMin - padding) * 10) / 10, max: Math.ceil((rawMax + padding) * 10) / 10 };
}

function linePath(points: PlotPoint[], x: (value: number) => number, y: (value: number) => number) {
  return points.map((point, index) => `${index ? "L" : "M"}${x(point.ratio)} ${y(point.momentum)}`).join(" ");
}

export function RRGChart({ sectors, active, tail, onPick }: { sectors: SectorState[]; active: string | null; tail: number; onPick: (ticker: string) => void }) {
  const { domain, series, samplingWeeks } = useMemo(() => {
    const samplingWeeks = tail >= 16 ? 4 : tail >= 12 ? 2 : 1;
    const prepared = sectors.map((sector) => {
      const rawTrail = sector.trail.slice(-(tail + 1));
      return { sector, rawTrail, displayTrail: sampleTrail(rawTrail, samplingWeeks) };
    });
    const domain = domainFor(prepared.map((item) => item.displayTrail));
    const series: Series[] = prepared.map(({ sector, rawTrail, displayTrail }) => ({
      sector,
      displayTrail,
      start: rawTrail[0]!,
      latest: rawTrail.at(-1)!,
    }));
    return { domain, series, samplingWeeks };
  }, [sectors, tail]);
  const x = (value: number) => 8 + ((value - domain.min) / (domain.max - domain.min)) * 84;
  const y = (value: number) => 92 - ((value - domain.min) / (domain.max - domain.min)) * 84;
  const ratioBaseline = x(100);
  const momentumBaseline = y(100);
  const simplified = samplingWeeks > 1;
  const description = simplified
    ? `최근 ${tail}주 궤적입니다. 중간 경로는 ${samplingWeeks}주 간격의 실제 주간 관측점만 시간 순서대로 연결했으며, 시작점과 최신 위치는 실제 값입니다.`
    : `최근 ${tail}주 실제 궤적입니다.`;

  return <svg className={`rrg-canvas ${simplified ? "simplified-horizon" : ""}`} viewBox="0 0 100 100" role="img" aria-label={`SPY 대비 주간 섹터 RRG 지도. ${description}`}>
    <defs><clipPath id="plot-clip"><rect x="8" y="8" width="84" height="84" rx="1" /></clipPath></defs>
    <rect x="8" y="8" width="84" height="84" rx="1" className="paper" />
    <g clipPath="url(#plot-clip)">
      <rect x={ratioBaseline} y="8" width={92 - ratioBaseline} height={momentumBaseline - 8} className="q lead" />
      <rect x={ratioBaseline} y={momentumBaseline} width={92 - ratioBaseline} height={92 - momentumBaseline} className="q weak" />
      <rect x="8" y={momentumBaseline} width={ratioBaseline - 8} height={92 - momentumBaseline} className="q lag" />
      <rect x="8" y="8" width={ratioBaseline - 8} height={momentumBaseline - 8} className="q improve" />
      <line x1={ratioBaseline} x2={ratioBaseline} y1="8" y2="92" className="origin" />
      <line x1="8" x2="92" y1={momentumBaseline} y2={momentumBaseline} className="origin" />
      {series.map(({ sector, displayTrail, start, latest }) => <g key={sector.ticker} className={`sector ${sector.quadrant} ${active && active !== sector.ticker ? "muted" : ""} ${active === sector.ticker ? "selected" : ""}`} tabIndex={0} role="button" onClick={() => onPick(sector.ticker)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") onPick(sector.ticker); }} aria-label={`${sector.ticker}, ${sector.quadrant}, ${description} Ratio ${sector.ratio.toFixed(2)}, Momentum ${sector.momentum.toFixed(2)}`}>
        <path className="tail" d={linePath(displayTrail, x, y)} />
        <circle className="start-dot" cx={x(start.ratio)} cy={y(start.momentum)} r="0.72" />
        <circle className="dot" cx={x(latest.ratio)} cy={y(latest.momentum)} r={active === sector.ticker ? 1.02 : 0.68} />
      </g>)}
    </g>
    <text x="10.5" y="12.5" className="qlabel">{quadrantLabels.improving}</text><text x="89.5" y="12.5" textAnchor="end" className="qlabel">{quadrantLabels.leading}</text>
    <text x="10.5" y="89.5" className="qlabel">{quadrantLabels.lagging}</text><text x="89.5" y="89.5" textAnchor="end" className="qlabel">{quadrantLabels.weakening}</text>
    <text x="50" y="98" textAnchor="middle" className="axis">RS-RATIO</text><text x="3" y="50" textAnchor="middle" transform="rotate(-90 3 50)" className="axis">RS-MOMENTUM</text>
  </svg>;
}
