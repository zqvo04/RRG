import { useMemo } from "react";
import type { SectorState } from "./types";

const quadrantLabels = { leading: "LEADING", weakening: "WEAKENING", lagging: "LAGGING", improving: "IMPROVING" } as const;

type PlotPoint = { ratio: number; momentum: number };

function domainFor(sectors: SectorState[], tail: number) {
  const values = sectors.flatMap((sector) => sector.trail.slice(-(tail + 1)).flatMap((point) => [point.ratio, point.momentum]));
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

export function RRGChart({ sectors, active, tail, onPick }: { sectors: SectorState[]; active: string | null; tail: number; onPick: (ticker: string) => void }) {
  const { domain, series } = useMemo(() => {
    const domain = domainFor(sectors, tail);
    const x = (value: number) => 8 + ((value - domain.min) / (domain.max - domain.min)) * 84;
    const y = (value: number) => 92 - ((value - domain.min) / (domain.max - domain.min)) * 84;
    const series = sectors.map((sector) => {
      const trail = sector.trail.slice(-(tail + 1));
      return { sector, trail, start: trail[0]!, previous: trail.at(-2) ?? trail[0]!, latest: trail.at(-1)! };
    });
    return { domain, series };
  }, [sectors, tail]);
  const x = (value: number) => 8 + ((value - domain.min) / (domain.max - domain.min)) * 84;
  const y = (value: number) => 92 - ((value - domain.min) / (domain.max - domain.min)) * 84;
  const ratioBaseline = x(100);
  const momentumBaseline = y(100);

  return <svg className="rrg-canvas" viewBox="0 0 100 100" role="img" aria-label="SPY 대비 주간 섹터 RRG 지도. 속이 빈 점은 표시 기간의 시작점, 선 끝의 작은 화살촉과 점은 현재 이동 방향과 최신 위치를 뜻합니다.">
    <defs><clipPath id="plot-clip"><rect x="8" y="8" width="84" height="84" rx="1" /></clipPath></defs>
    <rect x="8" y="8" width="84" height="84" rx="1" className="paper" />
    <g clipPath="url(#plot-clip)">
      <rect x={ratioBaseline} y="8" width={92 - ratioBaseline} height={momentumBaseline - 8} className="q lead" />
      <rect x={ratioBaseline} y={momentumBaseline} width={92 - ratioBaseline} height={92 - momentumBaseline} className="q weak" />
      <rect x="8" y={momentumBaseline} width={ratioBaseline - 8} height={92 - momentumBaseline} className="q lag" />
      <rect x="8" y="8" width={ratioBaseline - 8} height={momentumBaseline - 8} className="q improve" />
      <line x1={ratioBaseline} x2={ratioBaseline} y1="8" y2="92" className="origin" />
      <line x1="8" x2="92" y1={momentumBaseline} y2={momentumBaseline} className="origin" />
      {series.map(({ sector, trail, start, previous, latest }) => <g key={sector.ticker} className={`sector ${sector.quadrant} ${active && active !== sector.ticker ? "muted" : ""} ${active === sector.ticker ? "selected" : ""}`} tabIndex={0} role="button" onClick={() => onPick(sector.ticker)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") onPick(sector.ticker); }} aria-label={`${sector.ticker}, ${sector.quadrant}, 최근 ${tail}주 궤적, Ratio ${sector.ratio.toFixed(2)}, Momentum ${sector.momentum.toFixed(2)}`}>
        <path className="tail" d={trail.map((point, index) => `${index ? "L" : "M"}${x(point.ratio)} ${y(point.momentum)}`).join(" ")} />
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
