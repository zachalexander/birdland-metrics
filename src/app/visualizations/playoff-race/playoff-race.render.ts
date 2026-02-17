import {
  TEAM_COLORS, createResponsiveSvg, createTooltip,
  FONT_MONO, FONT_SANS, COLOR_TEXT, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_BORDER,
} from '../viz-utils';
import { TEAM_NAMES, PlayoffOddsHistoryPoint } from '../../shared/models/mlb.models';

export interface PlayoffRaceConfig {
  teams: string[];
}

export function renderPlayoffRace(
  container: HTMLElement,
  data: Record<string, PlayoffOddsHistoryPoint[]>,
  config: PlayoffRaceConfig,
  d3: typeof import('d3'),
): void {
  container.innerHTML = '';

  const teams = config.teams.filter(t => data[t]?.length);
  if (!teams.length) {
    const msg = document.createElement('p');
    msg.className = 'viz-empty-state';
    msg.textContent = 'No playoff odds history available yet. Data will appear once the season begins.';
    container.appendChild(msg);
    return;
  }

  const width = 700;
  const height = 380;
  const margin = { top: 12, right: 16, bottom: 56, left: 48 };

  const { svg, g, innerWidth, innerHeight } = createResponsiveSvg(d3, container, width, height, margin);

  // Parse dates and build typed arrays
  const parsedData: Record<string, { date: Date; playoff_pct: number }[]> = {};
  let allDates: Date[] = [];

  for (const team of teams) {
    const points = data[team].map(d => ({
      date: new Date(d.date),
      playoff_pct: d.playoff_pct,
    }));
    points.sort((a, b) => a.date.getTime() - b.date.getTime());
    parsedData[team] = points;
    allDates = allDates.concat(points.map(p => p.date));
  }

  const x = d3.scaleTime()
    .domain(d3.extent(allDates) as [Date, Date])
    .range([0, innerWidth]);

  const y = d3.scaleLinear()
    .domain([0, 100])
    .range([innerHeight, 0]);

  // Grid lines
  g.append('g')
    .attr('class', 'grid')
    .call(d3.axisLeft(y).ticks(5).tickSize(-innerWidth).tickFormat(() => ''))
    .call(g => g.select('.domain').remove())
    .call(g => g.selectAll('.tick line').attr('stroke', COLOR_BORDER).attr('stroke-dasharray', 'none'));

  // X axis
  g.append('g')
    .attr('transform', `translate(0,${innerHeight})`)
    .call(d3.axisBottom(x).ticks(6).tickFormat(d3.timeFormat('%b') as any).tickSize(0))
    .call(g => g.select('.domain').attr('stroke', COLOR_TEXT))
    .call(g => g.selectAll('.tick text')
      .attr('fill', COLOR_TEXT_MUTED)
      .attr('font-family', FONT_MONO)
      .attr('font-size', '10px')
      .attr('font-weight', '600')
      .attr('text-transform', 'uppercase')
      .attr('dy', '1em'));

  // Y axis
  g.append('g')
    .call(d3.axisLeft(y).ticks(5).tickSize(0).tickFormat(d => `${d}%`))
    .call(g => g.select('.domain').remove())
    .call(g => g.selectAll('.tick text')
      .attr('fill', COLOR_TEXT_MUTED)
      .attr('font-family', FONT_MONO)
      .attr('font-size', '10px')
      .attr('dx', '-0.5em'));

  // Y axis label
  g.append('text')
    .attr('transform', 'rotate(-90)')
    .attr('y', -38)
    .attr('x', -innerHeight / 2)
    .attr('text-anchor', 'middle')
    .attr('fill', COLOR_TEXT_MUTED)
    .attr('font-family', FONT_MONO)
    .attr('font-size', '9px')
    .attr('font-weight', '600')
    .attr('letter-spacing', '0.06em')
    .text('PLAYOFF ODDS');

  // Lines
  const line = d3.line<{ date: Date; playoff_pct: number }>()
    .x(d => x(d.date))
    .y(d => y(d.playoff_pct))
    .curve(d3.curveMonotoneX);

  for (const team of teams) {
    const color = TEAM_COLORS[team] ?? COLOR_TEXT_SECONDARY;
    const pts = parsedData[team];

    if (pts.length === 1) {
      // Single data point — draw a dot instead of a line
      g.append('circle')
        .attr('cx', x(pts[0].date))
        .attr('cy', y(pts[0].playoff_pct))
        .attr('r', 4)
        .attr('fill', color)
        .attr('stroke', '#fff')
        .attr('stroke-width', 1.5)
        .style('opacity', 0)
        .transition()
        .duration(600)
        .style('opacity', 1);
    } else {
      const path = g.append('path')
        .datum(pts)
        .attr('fill', 'none')
        .attr('stroke', color)
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
  }

  // Tooltip + hover interaction
  const tooltip = createTooltip(d3, container);
  const bisect = d3.bisector<{ date: Date; playoff_pct: number }, Date>(d => d.date).left;

  const focus = g.append('g').style('display', 'none');
  focus.append('line')
    .attr('class', 'focus-line')
    .attr('y1', 0)
    .attr('y2', innerHeight)
    .attr('stroke', COLOR_BORDER)
    .attr('stroke-width', 1);

  for (const team of teams) {
    focus.append('circle')
      .attr('class', `focus-dot-${team}`)
      .attr('r', 3.5)
      .attr('fill', TEAM_COLORS[team] ?? COLOR_TEXT_SECONDARY)
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

      let html = `<span style="font-family:${FONT_MONO};font-size:10px;font-weight:600;color:${COLOR_TEXT_MUTED};text-transform:uppercase;letter-spacing:0.04em">${d3.timeFormat('%b %d, %Y')(hoveredDate)}</span>`;

      // Sort teams by playoff_pct descending at this date
      const teamValues: { team: string; pct: number; d: { date: Date; playoff_pct: number } }[] = [];
      for (const team of teams) {
        const pts = parsedData[team];
        const i = bisect(pts, hoveredDate, 1);
        const d0 = pts[i - 1];
        const d1 = pts[i];
        if (!d0) continue;
        const d = d1 && (hoveredDate.getTime() - d0.date.getTime() > d1.date.getTime() - hoveredDate.getTime()) ? d1 : d0;
        teamValues.push({ team, pct: d.playoff_pct, d });
      }
      teamValues.sort((a, b) => b.pct - a.pct);

      for (const { team, pct, d } of teamValues) {
        focus.select(`.focus-dot-${team}`)
          .attr('cx', x(d.date))
          .attr('cy', y(d.playoff_pct));

        const color = TEAM_COLORS[team] ?? COLOR_TEXT_SECONDARY;
        const name = TEAM_NAMES[team] ?? team;
        html += `<div style="display:flex;align-items:center;gap:6px;margin-top:4px">`;
        html += `<span style="width:8px;height:8px;border-radius:50%;background:${color};flex-shrink:0"></span>`;
        html += `<span style="font-weight:500;color:${COLOR_TEXT}">${name}</span>`;
        html += `<span style="font-family:${FONT_MONO};font-weight:700;color:${COLOR_TEXT};margin-left:auto">${pct.toFixed(1)}%</span>`;
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
    const color = TEAM_COLORS[team] ?? COLOR_TEXT_SECONDARY;
    const name = TEAM_NAMES[team] ?? team;
    const lg = legend.append('g').attr('transform', `translate(${legendX}, 0)`);

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
      .attr('fill', COLOR_TEXT_SECONDARY)
      .text(name);

    legendX += name.length * 7 + 40;
  }
}
