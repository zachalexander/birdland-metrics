import {
  TEAM_COLORS, createResponsiveSvg, createTooltip, getActiveTheme,
  FONT_MONO, FONT_SANS,
} from '../viz-utils';
import { TEAM_NAMES } from '../../shared/models/mlb.models';

export interface EloTrendConfig {
  teams: string[];
  season: number;
  title?: string;
}

export interface EloTrendDataPoint {
  date: string;
  elo: number;
}

export function renderEloTrend(
  container: HTMLElement,
  data: Record<string, EloTrendDataPoint[]>,
  config: EloTrendConfig,
  d3: typeof import('d3'),
): void {
  container.innerHTML = '';
  const theme = getActiveTheme();

  const teams = config.teams.filter(t => data[t]?.length);
  if (!teams.length) {
    const msg = document.createElement('p');
    msg.className = 'viz-empty-state';
    msg.textContent = 'No ELO data available for the selected teams and season.';
    container.appendChild(msg);
    return;
  }

  const width = 700;
  const height = 380;
  const margin = { top: 12, right: 16, bottom: 56, left: 48 };

  const { svg, g, innerWidth, innerHeight } = createResponsiveSvg(d3, container, width, height, margin);

  // Parse dates and build typed arrays
  const parsedData: Record<string, { date: Date; elo: number }[]> = {};
  let allDates: Date[] = [];
  let allElos: number[] = [];

  for (const team of teams) {
    const points = data[team].map(d => ({
      date: new Date(d.date),
      elo: d.elo,
    }));
    points.sort((a, b) => a.date.getTime() - b.date.getTime());
    parsedData[team] = points;
    allDates = allDates.concat(points.map(p => p.date));
    allElos = allElos.concat(points.map(p => p.elo));
  }

  const eloMin = Math.min(...allElos);
  const eloMax = Math.max(...allElos);

  const x = d3.scaleTime()
    .domain(d3.extent(allDates) as [Date, Date])
    .range([0, innerWidth]);

  const y = d3.scaleLinear()
    .domain([eloMin - 40, eloMax + 40])
    .range([innerHeight, 0]);

  // Grid lines (drawn first, behind everything)
  g.append('g')
    .attr('class', 'grid')
    .call(d3.axisLeft(y).ticks(5).tickSize(-innerWidth).tickFormat(() => ''))
    .call(g => g.select('.domain').remove())
    .call(g => g.selectAll('.tick line').attr('stroke', theme.border).attr('stroke-dasharray', 'none'));

  // X axis
  g.append('g')
    .attr('transform', `translate(0,${innerHeight})`)
    .call(d3.axisBottom(x).ticks(6).tickFormat(d3.timeFormat('%b') as any).tickSize(0))
    .call(g => g.select('.domain').attr('stroke', theme.text))
    .call(g => g.selectAll('.tick text')
      .attr('fill', theme.textMuted)
      .attr('font-family', FONT_MONO)
      .attr('font-size', '10px')
      .attr('font-weight', '600')
      .attr('text-transform', 'uppercase')
      .attr('dy', '1em'));

  // Y axis
  g.append('g')
    .call(d3.axisLeft(y).ticks(5).tickSize(0))
    .call(g => g.select('.domain').remove())
    .call(g => g.selectAll('.tick text')
      .attr('fill', theme.textMuted)
      .attr('font-family', FONT_MONO)
      .attr('font-size', '10px')
      .attr('dx', '-0.5em'));

  // Y axis label
  g.append('text')
    .attr('transform', 'rotate(-90)')
    .attr('y', -38)
    .attr('x', -innerHeight / 2)
    .attr('text-anchor', 'middle')
    .attr('fill', theme.textMuted)
    .attr('font-family', FONT_MONO)
    .attr('font-size', '9px')
    .attr('font-weight', '600')
    .attr('letter-spacing', '0.06em')
    .text('ELO RATING');

  // 1500 baseline
  if (y.domain()[0] < 1500 && y.domain()[1] > 1500) {
    g.append('line')
      .attr('x1', 0)
      .attr('x2', innerWidth)
      .attr('y1', y(1500))
      .attr('y2', y(1500))
      .attr('stroke', theme.textMuted)
      .attr('stroke-dasharray', '4,3')
      .attr('stroke-width', 1);

    g.append('text')
      .attr('x', innerWidth)
      .attr('y', y(1500))
      .attr('dx', '4')
      .attr('dy', '0.35em')
      .attr('fill', theme.textMuted)
      .attr('font-family', FONT_MONO)
      .attr('font-size', '9px')
      .attr('font-weight', '600')
      .text('AVG');
  }

  // Lines
  const line = d3.line<{ date: Date; elo: number }>()
    .x(d => x(d.date))
    .y(d => y(d.elo))
    .curve(d3.curveMonotoneX);

  for (const team of teams) {
    const path = g.append('path')
      .datum(parsedData[team])
      .attr('fill', 'none')
      .attr('stroke', TEAM_COLORS[team] ?? theme.textSecondary)
      .attr('stroke-width', 2)
      .attr('d', line);

    // Animate line drawing
    const totalLength = (path.node() as SVGPathElement).getTotalLength();
    path
      .attr('stroke-dasharray', `${totalLength} ${totalLength}`)
      .attr('stroke-dashoffset', totalLength)
      .transition()
      .duration(1200)
      .ease(d3.easeCubicOut)
      .attr('stroke-dashoffset', 0);
  }

  // Tooltip + hover interaction
  const tooltip = createTooltip(d3, container);
  const bisect = d3.bisector<{ date: Date; elo: number }, Date>(d => d.date).left;

  const focus = g.append('g').style('display', 'none');
  focus.append('line')
    .attr('class', 'focus-line')
    .attr('y1', 0)
    .attr('y2', innerHeight)
    .attr('stroke', theme.border)
    .attr('stroke-width', 1);

  for (const team of teams) {
    focus.append('circle')
      .attr('class', `focus-dot-${team}`)
      .attr('r', 3.5)
      .attr('fill', TEAM_COLORS[team] ?? theme.textSecondary)
      .attr('stroke', '#fff')
      .attr('stroke-width', 1.5);
  }

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
      const hoveredDate = x.invert(mx);

      focus.select('.focus-line').attr('x1', mx).attr('x2', mx);

      let html = `<span style="font-family:${FONT_MONO};font-size:10px;font-weight:600;color:${theme.textMuted};text-transform:uppercase;letter-spacing:0.04em">${d3.timeFormat('%b %d, %Y')(hoveredDate)}</span>`;
      for (const team of teams) {
        const pts = parsedData[team];
        const i = bisect(pts, hoveredDate, 1);
        const d0 = pts[i - 1];
        const d1 = pts[i];
        if (!d0) continue;
        const d = d1 && (hoveredDate.getTime() - d0.date.getTime() > d1.date.getTime() - hoveredDate.getTime()) ? d1 : d0;

        focus.select(`.focus-dot-${team}`)
          .attr('cx', x(d.date))
          .attr('cy', y(d.elo));

        const color = TEAM_COLORS[team] ?? theme.textSecondary;
        const name = TEAM_NAMES[team] ?? team;
        html += `<div style="display:flex;align-items:center;gap:6px;margin-top:4px">`;
        html += `<span style="width:8px;height:8px;border-radius:50%;background:${color};flex-shrink:0"></span>`;
        html += `<span style="font-weight:500;color:${theme.text}">${name}</span>`;
        html += `<span style="font-family:${FONT_MONO};font-weight:700;color:${theme.text};margin-left:auto">${Math.round(d.elo)}</span>`;
        html += `</div>`;
      }

      tooltip.show(html);
      tooltip.move(event);
    });

  // Legend (below chart, inline)
  const legend = g.append('g')
    .attr('transform', `translate(0, ${innerHeight + 32})`);

  let legendX = 0;
  for (const team of teams) {
    const color = TEAM_COLORS[team] ?? theme.textSecondary;
    const name = TEAM_NAMES[team] ?? team;
    const lg = legend.append('g').attr('transform', `translate(${legendX}, 0)`);

    // Small line segment instead of circle (matches line chart visual)
    lg.append('line')
      .attr('x1', 0).attr('x2', 16)
      .attr('y1', 0).attr('y2', 0)
      .attr('stroke', color)
      .attr('stroke-width', 2);

    lg.append('text')
      .attr('x', 22)
      .attr('y', 4)
      .attr('font-family', FONT_SANS)
      .attr('font-size', '11px')
      .attr('font-weight', '500')
      .attr('fill', theme.textSecondary)
      .text(name);

    legendX += name.length * 7 + 40;
  }
}
