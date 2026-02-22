import {
  createResponsiveSvg, createTooltip, getActiveTheme,
  FONT_MONO, FONT_SANS, prefersReducedMotion,
} from '../viz-utils';
import { PlayerSeasonStats } from '../../shared/models/mlb.models';

export interface PlayerStatsVizConfig {
  playerId: string;
  metrics: string[];
  title?: string;
}

interface MetricMeta {
  label: string;
  shortLabel: string;
  format: (v: number) => string;
  color: string;
  unit: string;
  isPercentage: boolean;
}

const METRIC_REGISTRY: Record<string, MetricMeta> = {
  war:        { label: 'Wins Above Replacement', shortLabel: 'WAR',     color: '#df4a00', unit: '',  isPercentage: false, format: v => v.toFixed(1) },
  wrc_plus:   { label: 'wRC+',                   shortLabel: 'wRC+',    color: '#003087', unit: '',  isPercentage: false, format: v => `${Math.round(v)}` },
  hard_pct:   { label: 'Hard Hit %',             shortLabel: 'Hard%',   color: '#C41E3A', unit: '%', isPercentage: true,  format: v => `${(v * 100).toFixed(1)}%` },
  barrel_pct: { label: 'Barrel %',               shortLabel: 'Barrel%', color: '#005A9C', unit: '%', isPercentage: true,  format: v => `${(v * 100).toFixed(1)}%` },
  gb_pct:     { label: 'Ground Ball %',          shortLabel: 'GB%',     color: '#6b7280', unit: '%', isPercentage: true,  format: v => `${(v * 100).toFixed(1)}%` },
  sb:         { label: 'Stolen Bases',           shortLabel: 'SB',      color: '#CE1141', unit: '',  isPercentage: false, format: v => `${Math.round(v)}` },
  bsr:        { label: 'Base Running Runs',      shortLabel: 'BsR',     color: '#002D62', unit: '',  isPercentage: false, format: v => v >= 0 ? `+${v.toFixed(1)}` : v.toFixed(1) },
  avg:        { label: 'Batting Average',        shortLabel: 'AVG',     color: '#df4a00', unit: '',  isPercentage: false, format: v => v.toFixed(3).replace(/^0/, '') },
  obp:        { label: 'On-Base Percentage',     shortLabel: 'OBP',     color: '#003087', unit: '',  isPercentage: false, format: v => v.toFixed(3).replace(/^0/, '') },
  slg:        { label: 'Slugging',               shortLabel: 'SLG',     color: '#C41E3A', unit: '',  isPercentage: false, format: v => v.toFixed(3).replace(/^0/, '') },
  ops:        { label: 'OPS',                    shortLabel: 'OPS',     color: '#005A9C', unit: '',  isPercentage: false, format: v => v.toFixed(3).replace(/^0/, '') },
  hr:         { label: 'Home Runs',              shortLabel: 'HR',      color: '#df4a00', unit: '',  isPercentage: false, format: v => `${Math.round(v)}` },
  iso:        { label: 'Isolated Power',         shortLabel: 'ISO',     color: '#003087', unit: '',  isPercentage: false, format: v => v.toFixed(3).replace(/^0/, '') },
  babip:      { label: 'BABIP',                  shortLabel: 'BABIP',   color: '#6b7280', unit: '',  isPercentage: false, format: v => v.toFixed(3).replace(/^0/, '') },
  k_pct:      { label: 'Strikeout %',            shortLabel: 'K%',      color: '#C41E3A', unit: '%', isPercentage: true,  format: v => `${(v * 100).toFixed(1)}%` },
  bb_pct:     { label: 'Walk %',                 shortLabel: 'BB%',     color: '#005A9C', unit: '%', isPercentage: true,  format: v => `${(v * 100).toFixed(1)}%` },
  ev:         { label: 'Exit Velocity',          shortLabel: 'EV',      color: '#df4a00', unit: ' mph', isPercentage: false, format: v => v.toFixed(1) },
  spd:        { label: 'Speed Score',            shortLabel: 'Spd',     color: '#CE1141', unit: '',  isPercentage: false, format: v => v.toFixed(1) },
};

export function renderPlayerStats(
  container: HTMLElement,
  data: PlayerSeasonStats[],
  config: PlayerStatsVizConfig,
  d3: typeof import('d3'),
): void {
  container.innerHTML = '';
  const theme = getActiveTheme();

  const metrics = config.metrics.filter(m => m in METRIC_REGISTRY);
  if (!metrics.length || !data.length) {
    const msg = document.createElement('p');
    msg.className = 'viz-empty-state';
    msg.textContent = 'No player stats data available.';
    container.appendChild(msg);
    return;
  }

  const sorted = [...data].sort((a, b) => a.season - b.season);

  const width = 700;
  const height = 380;
  const margin = { top: 36, right: 80, bottom: 56, left: 16 };

  const { svg, g, innerWidth, innerHeight } = createResponsiveSvg(d3, container, width, height, margin);

  // Title
  if (config.title) {
    svg.append('text')
      .attr('x', width / 2)
      .attr('y', 22)
      .attr('text-anchor', 'middle')
      .attr('font-family', FONT_MONO)
      .attr('font-size', '11px')
      .attr('font-weight', '700')
      .attr('letter-spacing', '0.06em')
      .attr('fill', theme.textSecondary)
      .text(config.title.toUpperCase());
  }

  // X scale — scalePoint for discrete seasons
  const seasons = sorted.map(d => d.season);
  const x = d3.scalePoint<number>()
    .domain(seasons)
    .range([0, innerWidth])
    .padding(0.1);

  // Per-metric y scales with 15% padding
  const yScales: Record<string, d3.ScaleLinear<number, number>> = {};
  for (const key of metrics) {
    const values = sorted.map(d => (d as any)[key] as number);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const pad = (max - min) * 0.15 || 1;
    yScales[key] = d3.scaleLinear()
      .domain([min - pad, max + pad])
      .range([innerHeight, 0]);
  }

  // Vertical grid lines
  g.append('g')
    .attr('class', 'grid')
    .selectAll('line')
    .data(seasons)
    .join('line')
    .attr('x1', d => x(d)!)
    .attr('x2', d => x(d)!)
    .attr('y1', 0)
    .attr('y2', innerHeight)
    .attr('stroke', theme.border)
    .attr('stroke-width', 1);

  // X axis
  g.append('g')
    .attr('transform', `translate(0,${innerHeight})`)
    .call(d3.axisBottom(x).tickSize(0).tickFormat(d => `${d}`))
    .call(g => g.select('.domain').attr('stroke', theme.text))
    .call(g => g.selectAll('.tick text')
      .attr('fill', theme.textMuted)
      .attr('font-family', FONT_MONO)
      .attr('font-size', '10px')
      .attr('font-weight', '600')
      .attr('dy', '1em'));

  // Lines + dots + end labels for each metric
  for (const key of metrics) {
    const meta = METRIC_REGISTRY[key];
    const yScale = yScales[key];

    const line = d3.line<PlayerSeasonStats>()
      .x(d => x(d.season)!)
      .y(d => yScale((d as any)[key]))
      .curve(d3.curveMonotoneX);

    // Line path with draw-on animation
    const path = g.append('path')
      .datum(sorted)
      .attr('fill', 'none')
      .attr('stroke', meta.color)
      .attr('stroke-width', 2.5)
      .attr('d', line);

    const totalLength = (path.node() as SVGPathElement).getTotalLength();
    const noMotion = prefersReducedMotion();
    if (noMotion) {
      path.attr('stroke-dashoffset', 0);
    } else {
      path
        .attr('stroke-dasharray', `${totalLength} ${totalLength}`)
        .attr('stroke-dashoffset', totalLength)
        .transition()
        .duration(1200)
        .ease(d3.easeCubicOut)
        .attr('stroke-dashoffset', 0);
    }

    // Dots
    const dots = g.selectAll(`.dot-${key}`)
      .data(sorted)
      .join('circle')
      .attr('class', `dot-${key}`)
      .attr('cx', d => x(d.season)!)
      .attr('cy', d => yScale((d as any)[key]))
      .attr('r', 4)
      .attr('fill', meta.color)
      .attr('stroke', '#fff')
      .attr('stroke-width', 1.5);
    if (noMotion) {
      dots.style('opacity', 1);
    } else {
      dots.style('opacity', 0)
        .transition()
        .delay(1000)
        .duration(300)
        .style('opacity', 1);
    }

    // End-of-line label
    const lastPt = sorted[sorted.length - 1];
    const lastVal = (lastPt as any)[key] as number;

    const label = g.append('text')
      .attr('x', x(lastPt.season)! + 10)
      .attr('y', yScale(lastVal))
      .attr('dy', '0.35em')
      .attr('font-family', FONT_MONO)
      .attr('font-size', '10px')
      .attr('font-weight', '700')
      .attr('fill', meta.color)
      .text(`${meta.shortLabel} ${meta.format(lastVal)}`);
    if (noMotion) {
      label.style('opacity', 1);
    } else {
      label.style('opacity', 0)
        .transition()
        .delay(1200)
        .duration(300)
        .style('opacity', 1);
    }
  }

  // Tooltip + hover interaction
  const tooltip = createTooltip(d3, container);

  const focus = g.append('g').style('display', 'none');
  focus.append('line')
    .attr('class', 'focus-line')
    .attr('y1', 0)
    .attr('y2', innerHeight)
    .attr('stroke', theme.border)
    .attr('stroke-width', 1);

  for (const key of metrics) {
    focus.append('circle')
      .attr('class', `focus-dot-${key}`)
      .attr('r', 3.5)
      .attr('fill', METRIC_REGISTRY[key].color)
      .attr('stroke', '#fff')
      .attr('stroke-width', 1.5);
  }

  // Invisible hover rects per season for snapping
  g.append('rect')
    .attr('width', innerWidth)
    .attr('height', innerHeight)
    .attr('fill', 'none')
    .attr('pointer-events', 'all')
    .on('mouseover', () => focus.style('display', null))
    .on('mouseout', () => {
      focus.style('display', 'none');
      tooltip.hide();
    })
    .on('mousemove', (event: MouseEvent) => {
      const [mx] = d3.pointer(event);

      // Snap to nearest season
      let closestSeason = seasons[0];
      let closestDist = Infinity;
      for (const s of seasons) {
        const dist = Math.abs(mx - x(s)!);
        if (dist < closestDist) {
          closestDist = dist;
          closestSeason = s;
        }
      }

      const seasonX = x(closestSeason)!;
      const datum = sorted.find(d => d.season === closestSeason);
      if (!datum) return;

      focus.select('.focus-line').attr('x1', seasonX).attr('x2', seasonX);

      let html = `<span style="font-family:${FONT_MONO};font-size:10px;font-weight:600;color:${theme.textMuted};text-transform:uppercase;letter-spacing:0.04em">${closestSeason} SEASON</span>`;

      for (const key of metrics) {
        const meta = METRIC_REGISTRY[key];
        const val = (datum as any)[key] as number;

        focus.select(`.focus-dot-${key}`)
          .attr('cx', seasonX)
          .attr('cy', yScales[key](val));

        html += `<div style="display:flex;align-items:center;gap:6px;margin-top:4px">`;
        html += `<span style="width:8px;height:8px;border-radius:50%;background:${meta.color};flex-shrink:0"></span>`;
        html += `<span style="font-weight:500;color:${theme.text}">${meta.shortLabel}</span>`;
        html += `<span style="font-family:${FONT_MONO};font-weight:700;color:${theme.text};margin-left:auto">${meta.format(val)}</span>`;
        html += `</div>`;
      }

      tooltip.show(html);
      tooltip.move(event);
    });

  // Legend (below chart, inline)
  const legend = g.append('g')
    .attr('transform', `translate(0, ${innerHeight + 32})`);

  let legendX = 0;
  for (const key of metrics) {
    const meta = METRIC_REGISTRY[key];
    const lg = legend.append('g').attr('transform', `translate(${legendX}, 0)`);

    lg.append('line')
      .attr('x1', 0).attr('x2', 16)
      .attr('y1', 0).attr('y2', 0)
      .attr('stroke', meta.color)
      .attr('stroke-width', 2.5);

    lg.append('text')
      .attr('x', 22)
      .attr('y', 4)
      .attr('font-family', FONT_SANS)
      .attr('font-size', '11px')
      .attr('font-weight', '500')
      .attr('fill', theme.textSecondary)
      .text(meta.label);

    legendX += meta.label.length * 6.5 + 40;
  }
}
