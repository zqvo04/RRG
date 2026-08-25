import { useMemo } from "react";
import type { SectorState } from "./types";

const quadrantLabels = { leading: "LEADING", weakening: "WEAKENING", lagging: "LAGGING", improving: "IMPROVING" } as const;

type PlotPoint = { ratio: number; momentum: number };

type Series = {
  sector: SectorState;
  displayTrail: PlotPoint[];
  start: PlotPoint;
  previous: PlotPoint;
  latest: PlotPoint;
};

function smoothTrail(points: PlotPoint[]) {
  if (points.length < 9) return points;
  return points.map((point, index) => {
    if (index === 0 || index === points.length - 1) return point;
    const window = points.slice(Math.max(0, index - 1), Math.min(points.length, index + 2));
    return {
      ratio: window.reduce((sum, item) => sum + item.ratio, 0) / window.length,
      momentum: window.reduce((sum, item) => sum + item.momentum, 0) / window.length,
    };
  });
}

function compactLongTrail(points: PlotPoint[]) {
  if (points.length < 15) return points;
  return points.filter((_, index) => index === 0 || index === points.length - 1 || index % 2 === 0);
}

function domainFor(trails: PlotPoint[][]) {
  const values = trails.flatMap((trail) => trail.flatMap((point) => [point.ratio, point.momentum]));
  const rawMin = Math.min(100, ...values);
  const rawMax = Math.max(100, ...values);
  const padding = Math.max(1.5, (rawMax - rawMin) * 0.12);
  return { min: Math.floor((rawMin - padding) * 10) / 10, max: Math.ceil((rawMax + padding) * 10) / 10 };
}

function arrowHead(from: PlotPoint, to: PlotPoint, x: (value: number) => number, y: (value: number) => number) {
  const x1 = x(from.ratio); const y1 = y(from.momentum); const x2 = x(to.ratio); const y2 = y(to.momentum);
  const length = Math.hypot(x2 - x1, y2 - y1);
  if (!length) return "";
  const ux = (x2 - x1) / length; const uy = (y2 - y1) / length;
  const size = 1.25; const wing = 0.68;
  const baseX = x2 - ux * size; const baseY = y2 - uy * size;
  return `${x2},${y2} ${baseX - uy * wing},${baseY + ux * wing} ${baseX + uy * wing},${baseY - ux * wing}`;
}

function linePath(points: PlotPoint[], x: (value: number) => number, y: (value: number) => number) {
  return points.map((point, index) => `${index ? "L" : "M"}${x(point.ratio)} ${y(point.momentum)}`).join(" ");
}

export function RRGChart({ sectors, active, tail, onPick }: { sectors: SectorState[]; active: string | null; tail: number; onPick: (ticker: string) => void }) {
  const { domain, series, averaged, longHorizon } = useMemo(() => {
    const averaged = tail === 12;
    const longHorizon = tail >= 16;
    const prepared = sectors.map((sector) => {
      const rawTrail = sector.trail.slice(-(tail + 1));
      const displayTrail = longHorizon ? compactLongTrail(rawTrail) : averaged ? smoothTrail(rawTrail) : rawTrail;
      return { sector, rawTrail, displayTrail };
    });
    const domain = domainFor(prepared.map((item) => item.displayTrail));
    const series: Series[] = prepared.map(({ sector, rawTrail, displayTrail }) => ({
      sector,
      displayTrail,
      start: rawTrail[0]!,
      previous: rawTrail.at(-2) ?? rawTrail[0]!,
      latest: rawTrail.at(-1)!,
    }));
    return { domain, series, averaged, longHorizon };
  }, [sectors, tail]);
  const x = (value: number) => 8 + ((value - domain.min) / (domain.max - domain.min)) * 84;
  const y = (value: number) => 92 - ((value - domain.min) / (domain.max - domain.min)) * 84;
  const ratioBaseline = x(100);
  const momentumBaseline = y(100);
  const description = longHorizon
    ? `최근 ${tail}주 궤적입니다. 중간 경로는 2주 간격의 실제 주간 관측점을 순서대로 연결했으며, 시작점·최신 위치·최근 이동은 실제 값입니다.`
    : averaged
      ? `최근 ${tail}주 궤적입니다. 중간 경로는 3주 중심 평균을 직선으로 연결했으며, 시작점·최신 위치·최근 이동은 실제 값입니다.`
      : `최근 ${tail}주 실제 궤적입니다.`;

  return <svg className={`rrg-canvas ${longHorizon ? "long-horizon" : ""}`} viewBox="0 0 100 100" role="img" aria-label={`SPY 대비 주간 섹터 RRG 지도. ${description}`}>
    <defs><clipPath id="plot-clip"><rect x="8" y="8" width="84" height="84" rx="1" /></clipPath></defs>
    <rect x="8" y="8" width="84" height="84" rx="1" className="paper" />
    <g clipPath="url(#plot-clip)">
      <rect x={ratioBaseline} y="8" width={92 - ratioBaseline} height={momentumBaseline - 8} className="q lead" />
      <rect x={ratioBaseline} y={momentumBaseline} width={92 - ratioBaseline} height={92 - momentumBaseline} className="q weak" />
      <rect x="8" y={momentumBaseline} width={ratioBaseline - 8} height={92 - momentumBaseline} className="q lag" />
      <rect x="8" y="8" width={ratioBaseline - 8} height={momentumBaseline - 8} className="q improve" />
      <line x1={ratioBaseline} x2={ratioBaseline} y1="8" y2="92" className="origin" />
      <line x1="8" x2="92" y1={momentumBaseline} y2={momentumBaseline} className="origin" />
      {series.map(({ sector, displayTrail, start, previous, latest }) => <g key={sector.ticker} className={`sector ${sector.quadrant} ${active && active !== sector.ticker ? "muted" : ""} ${active === sector.ticker ? "selected" : ""}`} tabIndex={0} role="button" onClick={() => onPick(sector.ticker)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") onPick(sector.ticker); }} aria-label={`${sector.ticker}, ${sector.quadrant}, ${description} Ratio ${sector.ratio.toFixed(2)}, Momentum ${sector.momentum.toFixed(2)}`}>
        <path className="tail" d={linePath(displayTrail, x, y)} />
        <circle className="start-dot" cx={x(start.ratio)} cy={y(start.momentum)} r="0.72" />
        <line className="recent-leg" x1={x(previous.ratio)} y1={y(previous.momentum)} x2={x(latest.ratio)} y2={y(latest.momentum)} />
        <polygon className="direction-tip" points={arrowHead(previous, latest, x, y)} />
        <circle className="dot" cx={x(latest.ratio)} cy={y(latest.momentum)} r={active === sector.ticker ? 1.02 : 0.68} />
      </g>)}
    </g>
    <text x="10.5" y="12.5" className="qlabel">{quadrantLabels.improving}</text><text x="89.5" y="12.5" textAnchor="end" className="qlabel">{quadrantLabels.leading}</text>
    <text x="10.5" y="89.5" className="qlabel">{quadrantLabels.lagging}</text><text x="89.5" y="89.5" textAnchor="end" className="qlabel">{quadrantLabels.weakening}</text>
    <text x="50" y="98" textAnchor="middle" className="axis">RS-RATIO</text><text x="3" y="50" textAnchor="middle" transform="rotate(-90 3 50)" className="axis">RS-MOMENTUM</text>
  </svg>;
}
