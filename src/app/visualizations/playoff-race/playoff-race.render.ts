import {
  TEAM_COLORS, createResponsiveSvg, createTooltip,
  FONT_MONO, FONT_SANS, COLOR_TEXT, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_BORDER,
} from '../viz-utils';
import { TEAM_NAMES, PlayoffOddsHistoryPoint, TeamProjection, PlayoffOdds, AL_EAST } from '../../shared/models/mlb.models';

export interface PlayoffRaceConfig {
  teams: string[];
}

export function renderPlayoffRace(
  container: HTMLElement,
  data: Record<string, PlayoffOddsHistoryPoint[]>,
  config: PlayoffRaceConfig,
  d3: typeof import('d3'),
  projections?: TeamProjection[],
  odds?: PlayoffOdds[],
  showAllTeams = false,
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

  const isCurrent = projections !== undefined || odds !== undefined;
  const containerWidth = container.getBoundingClientRect().width || 700;
  const isMobile = containerWidth < 500;
  const width = isMobile ? 380 : 700;
  const height = isMobile ? 280 : 260;
  const margin = isMobile
    ? { top: 10, right: 44, bottom: 24, left: 32 }
    : { top: 12, right: 62, bottom: 28, left: 38 };
  const axisFontSize = isMobile ? '10px' : '13px';
  const labelFontSize = isMobile ? '10px' : '13px';
  const xTickCount = isMobile ? 6 : 6;
  const balStroke = isMobile ? 2.5 : 3.5;
  const otherStroke = isMobile ? 2 : 3;
  const endDotR = isMobile ? 3.5 : 5;
  const endDotStroke = isMobile ? 1.5 : 2;
  const focusDotR = isMobile ? 3 : 3.5;
  const labelSpacing = isMobile ? 12 : 15;

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

  // Extend domain to full season so early-season data starts at the left edge
  const [minDate, maxDate] = d3.extent(allDates) as [Date, Date];
  const seasonEnd = new Date(maxDate);
  // If the data spans less than 4 months, extend to late September of the same year
  const spanMonths = (maxDate.getTime() - minDate.getTime()) / (1000 * 60 * 60 * 24 * 30);
  if (spanMonths < 4) {
    seasonEnd.setFullYear(minDate.getFullYear());
    seasonEnd.setMonth(8, 28); // Sep 28
  }
  const x = d3.scaleTime()
    .domain([minDate, seasonEnd > maxDate ? seasonEnd : maxDate])
    .range([0, innerWidth]);

  const y = d3.scaleLinear()
    .domain([0, 100])
    .range([innerHeight, 0]);

  // Grid lines
  g.append('g')
    .attr('class', 'grid')
    .attr('transform', `translate(${innerWidth},0)`)
    .call(d3.axisRight(y).ticks(5).tickSize(-innerWidth).tickFormat(() => ''))
    .call(g => g.select('.domain').remove())
    .call(g => g.selectAll('.tick line').attr('stroke', COLOR_BORDER).attr('stroke-dasharray', 'none'));

  // X axis
  g.append('g')
    .attr('transform', `translate(0,${innerHeight})`)
    .call(d3.axisBottom(x).ticks(xTickCount).tickFormat(d3.timeFormat('%b') as any).tickSize(0))
    .call(g => g.select('.domain').attr('stroke', COLOR_TEXT))
    .call(g => g.selectAll('.tick text')
      .attr('fill', COLOR_TEXT_MUTED)
      .attr('font-family', FONT_MONO)
      .attr('font-size', axisFontSize)
      .attr('font-weight', '600')
      .attr('text-transform', 'uppercase')
      .attr('dy', '1em'));

  // Y axis (right side)
  g.append('g')
    .attr('transform', `translate(${innerWidth},0)`)
    .call(d3.axisRight(y).ticks(5).tickSize(0).tickFormat(d => `${d}%`))
    .call(g => g.select('.domain').remove())
    .call(g => g.selectAll('.tick text')
      .attr('fill', COLOR_TEXT_MUTED)
      .attr('font-family', FONT_MONO)
      .attr('font-size', axisFontSize)
      .attr('font-weight', '700')
      .attr('dx', '0.5em'));

  // Y axis label (right side)
  g.append('text')
    .attr('transform', 'rotate(90)')
    .attr('y', -(innerWidth + margin.right * 0.8))
    .attr('x', innerHeight / 2)
    .attr('text-anchor', 'middle')
    .attr('fill', COLOR_TEXT_MUTED)
    .attr('font-family', FONT_MONO)
    .attr('font-size', isMobile ? '9px' : '11px')
    .attr('font-weight', '600')
    .attr('letter-spacing', '0.06em')
    .text('PLAYOFF ODDS');

  // --- Team visibility state ---
  const otherTeams = teams.filter(t => t !== 'BAL');

  // Lines
  const line = d3.line<{ date: Date; playoff_pct: number }>()
    .x(d => x(d.date))
    .y(d => y(d.playoff_pct))
    .curve(d3.curveMonotoneX);

  const teamPaths: Record<string, d3.Selection<SVGPathElement | SVGCircleElement, any, any, any>> = {};

  for (const team of teams) {
    const color = TEAM_COLORS[team] ?? COLOR_TEXT_SECONDARY;
    const pts = parsedData[team];
    const isOther = team !== 'BAL';

    if (pts.length === 1) {
      // Pulsing ring behind BAL dot (current season only)
      if (!isOther && isCurrent) {
        const pulseRing = g.append('circle')
          .attr('cx', x(pts[0].date))
          .attr('cy', y(pts[0].playoff_pct))
          .attr('fill', 'none')
          .attr('stroke', color)
          .attr('stroke-width', 2)
          .attr('r', endDotR + 2.5)
          .style('opacity', '0.6');

        function pulseSingle() {
          pulseRing
            .attr('r', endDotR + 2.5)
            .style('opacity', '0.6')
            .transition()
            .duration(1200)
            .ease(d3.easeCubicOut)
            .attr('r', isMobile ? 14 : 18)
            .style('opacity', '0')
            .on('end', pulseSingle);
        }
        pulseSingle();
      }

      const dot = g.append('circle')
        .attr('cx', x(pts[0].date))
        .attr('cy', y(pts[0].playoff_pct))
        .attr('r', !isOther ? endDotR + 1 : 4)
        .attr('fill', color)
        .attr('stroke', !isOther ? '#000' : '#fff')
        .attr('stroke-width', !isOther ? 2.5 : 1.5)
        .style('opacity', (isOther && !showAllTeams) ? '0' : '1');

      if (!isOther || showAllTeams) {
        dot.style('opacity', 0)
          .transition().duration(600).style('opacity', 1);
      }
      teamPaths[team] = dot as any;
    } else {
      const path = g.append('path')
        .datum(pts)
        .attr('fill', 'none')
        .attr('stroke', color)
        .attr('stroke-width', team === 'BAL' ? balStroke : otherStroke)
        .attr('d', line);

      if (isOther && !showAllTeams) {
        path.style('opacity', 0);
      } else if (isOther) {
        path.style('opacity', 1);
      } else {
        // Animate BAL line drawing
        const totalLength = (path.node() as SVGPathElement).getTotalLength();
        path
          .attr('stroke-dasharray', `${totalLength} ${totalLength}`)
          .attr('stroke-dashoffset', totalLength)
          .transition()
          .duration(1200)
          .ease(d3.easeCubicOut)
          .attr('stroke-dashoffset', 0);
      }
      teamPaths[team] = path as any;

      // Endpoint dot on the last data point
      const lastPt = pts[pts.length - 1];

      // Pulsing ring behind BAL end dot (current season only, inserted first so it renders beneath)
      if (!isOther && isCurrent) {
        const pulseRing = g.append('circle')
          .attr('cx', x(lastPt.date))
          .attr('cy', y(lastPt.playoff_pct))
          .attr('r', endDotR)
          .attr('fill', 'none')
          .attr('stroke', color)
          .attr('stroke-width', 2)
          .style('opacity', '0.6');

        function pulse() {
          pulseRing
            .attr('r', endDotR + 2.5)
            .style('opacity', '0.6')
            .transition()
            .duration(1200)
            .ease(d3.easeCubicOut)
            .attr('r', isMobile ? 14 : 18)
            .style('opacity', '0')
            .on('end', pulse);
        }
        pulse();
      }

      const endDot = g.append('circle')
        .attr('cx', x(lastPt.date))
        .attr('cy', y(lastPt.playoff_pct))
        .attr('r', !isOther ? endDotR + 1 : endDotR)
        .attr('fill', color)
        .attr('stroke', !isOther ? '#000' : '#fff')
        .attr('stroke-width', !isOther ? 2.5 : endDotStroke);

      if (isOther && !showAllTeams) {
        endDot.style('opacity', '0');
      } else if (!isOther) {
        endDot.style('opacity', '0')
          .transition().delay(1200).duration(300).style('opacity', '1');
      }

      // Store for toggling
      teamPaths[team + '_dot'] = endDot as any;
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
      .attr('r', focusDotR)
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

      const visibleTeams = showAllTeams ? teams : ['BAL'];
      const teamValues: { team: string; pct: number; d: { date: Date; playoff_pct: number } }[] = [];
      for (const team of visibleTeams) {
        const pts = parsedData[team];
        if (!pts) continue;
        const i = bisect(pts, hoveredDate, 1);
        const d0 = pts[i - 1];
        const d1 = pts[i];
        if (!d0) continue;
        const d = d1 && (hoveredDate.getTime() - d0.date.getTime() > d1.date.getTime() - hoveredDate.getTime()) ? d1 : d0;
        teamValues.push({ team, pct: d.playoff_pct, d });
      }
      teamValues.sort((a, b) => b.pct - a.pct);

      for (const team of teams) {
        const isVisible = visibleTeams.includes(team);
        focus.select(`.focus-dot-${team}`).style('display', isVisible ? 'inline' : 'none');
      }

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

  // Team labels on the left y-axis, positioned at each team's first data point
  // Resolve overlapping labels by nudging them apart
  const labelHeight = labelSpacing;
  const labelPositions = teams
    .map(team => ({ team, rawY: y(parsedData[team][0].playoff_pct) }))
    .sort((a, b) => a.rawY - b.rawY); // sort top-to-bottom (smallest y = top)

  // Push overlapping labels apart
  for (let i = 1; i < labelPositions.length; i++) {
    const prev = labelPositions[i - 1];
    const curr = labelPositions[i];
    if (curr.rawY - prev.rawY < labelHeight) {
      curr.rawY = prev.rawY + labelHeight;
    }
  }
  // If last label pushed below chart, shift everything up
  const maxY = innerHeight;
  if (labelPositions.length && labelPositions[labelPositions.length - 1].rawY > maxY) {
    const overflow = labelPositions[labelPositions.length - 1].rawY - maxY;
    for (const lp of labelPositions) {
      lp.rawY -= overflow;
    }
    // Re-enforce minimum spacing top-down after shift
    for (let i = 1; i < labelPositions.length; i++) {
      if (labelPositions[i].rawY - labelPositions[i - 1].rawY < labelHeight) {
        labelPositions[i].rawY = labelPositions[i - 1].rawY + labelHeight;
      }
    }
  }

  const resolvedY: Record<string, number> = {};
  for (const lp of labelPositions) {
    resolvedY[lp.team] = lp.rawY;
  }

  const teamLabels: Record<string, d3.Selection<SVGTextElement, unknown, null, undefined>> = {};
  for (const team of teams) {
    const color = TEAM_COLORS[team] ?? COLOR_TEXT_SECONDARY;
    const isOther = team !== 'BAL';

    const label = g.append('text')
      .attr('x', -8)
      .attr('y', resolvedY[team])
      .attr('dy', '0.35em')
      .attr('text-anchor', 'end')
      .attr('font-family', FONT_MONO)
      .attr('font-size', labelFontSize)
      .attr('font-weight', '800')
      .attr('fill', color)
      .style('opacity', (isOther && !showAllTeams) ? '0' : '1')
      .text(team);

    teamLabels[team] = label;
  }

  // --- Standings table below chart ---
  // Build odds lookup: use provided odds, or fall back to latest snapshot from history data
  const oddsMap: Record<string, { playoff_pct: number; division_pct: number; wildcard_pct: number }> = {};
  if (odds?.length) {
    for (const o of odds) {
      if (teams.includes(o.team)) {
        oddsMap[o.team] = { playoff_pct: o.playoff_pct, division_pct: o.division_pct, wildcard_pct: o.wildcard_pct };
      }
    }
  } else {
    // Fallback: use the last data point from history
    for (const team of teams) {
      const pts = data[team];
      if (pts?.length) {
        const last = pts[pts.length - 1];
        oddsMap[team] = {
          playoff_pct: last.playoff_pct,
          division_pct: last.division_pct ?? 0,
          wildcard_pct: last.wildcard_pct ?? 0,
        };
      }
    }
  }

  // Build projections lookup
  const projMap: Record<string, TeamProjection> = {};
  const hasProjections = !!projections?.length;
  if (hasProjections) {
    for (const p of projections!) {
      if (teams.includes(p.team)) {
        projMap[p.team] = p;
      }
    }
  }

  // Sort teams by playoff % descending
  const sortedTeams = [...teams].sort((a, b) => (oddsMap[b]?.playoff_pct ?? 0) - (oddsMap[a]?.playoff_pct ?? 0));

  // Only render if we have odds data
  if (Object.keys(oddsMap).length === 0) return;

  const cellPad = isMobile ? '0.35rem 0.35rem' : '0.5rem 0.6rem';
  const tdCellPad = isMobile ? '0.3rem 0.35rem' : '0.45rem 0.6rem';
  const thFontSize = isMobile ? '0.58rem' : '0.7rem';
  const tdNumFontSize = isMobile ? '0.7rem' : '0.8rem';
  const thStyle = `font-family:${FONT_MONO};font-size:${thFontSize};font-weight:500;text-transform:uppercase;letter-spacing:0.06em;color:${COLOR_TEXT_MUTED};padding:${cellPad};border-bottom:2px solid ${COLOR_BORDER};text-align:right`;
  const thTeamStyle = `${thStyle};text-align:left`;
  const tdStyle = `padding:${tdCellPad};border-bottom:1px solid ${COLOR_BORDER};color:${COLOR_TEXT}`;
  const tdTeamStyle = `${tdStyle};font-weight:400;white-space:nowrap`;
  const tdNumStyle = `${tdStyle};text-align:right;font-family:${FONT_MONO};font-size:${tdNumFontSize};font-weight:400`;
  const dotStyle = (c: string) => `display:inline-block;width:8px;height:8px;border-radius:50%;background:${c};margin-right:6px;vertical-align:middle`;

  const tableDiv = d3.select(container).append('div')
    .style('max-width', '480px')
    .style('margin', '24px auto 0');

  tableDiv.append('h3')
    .style('font-family', FONT_MONO)
    .style('font-size', '0.78rem')
    .style('font-weight', '500')
    .style('color', COLOR_TEXT_MUTED)
    .style('margin', '0 0 8px')
    .style('text-align', 'center')
    .text(hasProjections ? 'Projected AL East Standings' : 'AL East Standings');

  let headerHtml = `<tr><th style="${thTeamStyle}">Team</th>`;
  if (hasProjections) {
    headerHtml += `<th style="${thStyle}">W</th><th style="${thStyle}">L</th>`;
  }
  headerHtml += `<th style="${thStyle}">Playoff %</th><th style="${thStyle}">Div %</th><th style="${thStyle}">WC %</th></tr>`;

  let bodyHtml = '';
  for (const team of sortedTeams) {
    const o = oddsMap[team];
    if (!o) continue;
    const color = TEAM_COLORS[team] ?? COLOR_TEXT_SECONDARY;
    const name = TEAM_NAMES[team] ?? team;
    const isBAL = team === 'BAL';
    const bgHighlight = isBAL ? 'background:rgba(223,74,0,0.06);' : '';
    const teamColor = isBAL ? 'color:#df4a00;' : '';

    bodyHtml += '<tr>';
    bodyHtml += `<td style="${tdTeamStyle};${bgHighlight}${teamColor}"><span style="${dotStyle(color)}"></span>${name}</td>`;
    if (hasProjections) {
      const proj = projMap[team];
      const wins = proj ? Math.round(proj.median_wins) : '\u2014';
      const losses = proj ? 162 - Math.round(proj.median_wins) : '\u2014';
      bodyHtml += `<td style="${tdNumStyle};${bgHighlight}">${wins}</td><td style="${tdNumStyle};${bgHighlight}">${losses}</td>`;
    }
    bodyHtml += `<td style="${tdNumStyle};${bgHighlight}">${Math.round(o.playoff_pct)}%</td>`;
    bodyHtml += `<td style="${tdNumStyle};${bgHighlight}">${Math.round(o.division_pct)}%</td>`;
    bodyHtml += `<td style="${tdNumStyle};${bgHighlight}">${Math.round(o.wildcard_pct)}%</td>`;
    bodyHtml += '</tr>';
  }

  tableDiv.append('table')
    .attr('style', `width:100%;border-collapse:collapse;font-family:${FONT_SANS};font-size:${isMobile ? '0.75rem' : '0.85rem'}`)
    .html(`<thead>${headerHtml}</thead><tbody>${bodyHtml}</tbody>`);
}
