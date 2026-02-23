import {
  TEAM_COLORS, createResponsiveSvg, createTooltip, getActiveTheme,
  FONT_MONO, prefersReducedMotion,
} from '../viz-utils';
import { TEAM_NAMES, PlayoffOddsHistoryPoint, TeamProjection, PlayoffOdds } from '../../shared/models/mlb.models';

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
  const theme = getActiveTheme();

  const teams = config.teams.filter(t => data[t]?.length);
  if (!teams.length) {
    const msg = document.createElement('p');
    msg.className = 'viz-empty-state';
    msg.textContent = 'No playoff odds history available yet. Data will appear once the season begins.';
    container.appendChild(msg);
    return;
  }

  const isCurrent = projections !== undefined || odds !== undefined;
  const noMotion = prefersReducedMotion();
  const containerWidth = container.getBoundingClientRect().width || 700;
  const isMobile = containerWidth < 500;
  const width = isMobile ? 380 : Math.min(containerWidth * 0.75, 720);
  const height = isMobile ? 280 : 260;
  const margin = isMobile
    ? { top: 28, right: 44, bottom: 24, left: 32 }
    : { top: 30, right: 62, bottom: 28, left: 38 };
  const axisFontSize = isMobile ? '9px' : '11px';
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
    .call(g => g.selectAll('.tick line').attr('stroke', theme.border).attr('stroke-dasharray', 'none'));

  // X axis
  g.append('g')
    .attr('transform', `translate(0,${innerHeight})`)
    .call(d3.axisBottom(x).ticks(xTickCount).tickFormat(d3.timeFormat('%b') as any).tickSize(0))
    .call(g => g.select('.domain').attr('stroke', theme.text))
    .call(g => g.selectAll('.tick text')
      .attr('fill', theme.textMuted)
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
      .attr('fill', theme.textMuted)
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
    .attr('fill', theme.textMuted)
    .attr('font-family', FONT_MONO)
    .attr('font-size', isMobile ? '9px' : '11px')
    .attr('font-weight', '600')
    .attr('letter-spacing', '0.06em')
    .text('PLAYOFF ODDS');

  // --- Chart annotations ---
  const seasonYear = minDate.getFullYear();
  const balColor = TEAM_COLORS['BAL'];

  // 2026: Opening Day dashed line + muted arrow/label above chart
  if (isCurrent) {
    const openingDay = new Date(seasonYear, 2, 26);
    const oxPos = x(openingDay);
    if (oxPos >= 0 && oxPos <= innerWidth) {
      g.append('line')
        .attr('x1', oxPos).attr('x2', oxPos)
        .attr('y1', 0).attr('y2', innerHeight)
        .attr('stroke', theme.textMuted)
        .attr('stroke-width', 1)
        .attr('stroke-dasharray', '4,3')
        .attr('opacity', 0.6);

      const labelY = isMobile ? -18 : -22;
      const curveOffset = isMobile ? 30 : 40;
      const arrowPath = `M${oxPos + curveOffset},${labelY} C${oxPos + curveOffset * 0.5},${labelY - 6} ${oxPos + 6},${labelY - 2} ${oxPos},${-2}`;

      svg.append('defs').append('marker')
        .attr('id', 'arrow-opening')
        .attr('viewBox', '0 0 6 6')
        .attr('refX', 5).attr('refY', 3)
        .attr('markerWidth', 5).attr('markerHeight', 5)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,0 L6,3 L0,6 Z')
        .attr('fill', theme.textMuted);

      g.append('path')
        .attr('d', arrowPath)
        .attr('fill', 'none')
        .attr('stroke', theme.textMuted)
        .attr('stroke-width', 1)
        .attr('opacity', 0.7)
        .attr('marker-end', 'url(#arrow-opening)');

      g.append('text')
        .attr('x', oxPos + curveOffset + 2)
        .attr('y', labelY + 4)
        .attr('font-family', FONT_MONO)
        .attr('font-size', isMobile ? '8px' : '9px')
        .attr('font-weight', '600')
        .attr('fill', theme.textMuted)
        .attr('text-anchor', 'start')
        .text('(3/26) Regular season starts');
    }
  }

  // 2025: Brandon Hyde annotation — orange arrow pointing at BAL line (Orioles view only)
  if (seasonYear === 2025 && !showAllTeams) {
    const hydeDate = new Date(2025, 4, 17);
    const hxPos = x(hydeDate);
    if (hxPos >= 0 && hxPos <= innerWidth) {
      const balPts = parsedData['BAL'];
      const bisectDate = d3.bisector<{ date: Date; playoff_pct: number }, Date>(d => d.date).left;
      let targetY = y(50);
      if (balPts?.length) {
        const i = bisectDate(balPts, hydeDate, 1);
        const d0 = balPts[i - 1];
        const d1 = balPts[i];
        const closest = d1 && (hydeDate.getTime() - d0.date.getTime() > d1.date.getTime() - hydeDate.getTime()) ? d1 : (d0 ?? balPts[0]);
        targetY = y(closest.playoff_pct);
      }

      svg.append('defs').append('marker')
        .attr('id', 'arrow-hyde')
        .attr('viewBox', '0 0 6 6')
        .attr('refX', 5).attr('refY', 3)
        .attr('markerWidth', 5).attr('markerHeight', 5)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,0 L6,3 L0,6 Z')
        .attr('fill', balColor);

      const curveOffset = isMobile ? 40 : 50;
      const labelY = targetY - (isMobile ? 38 : 48);
      const arrowPath = `M${hxPos + curveOffset},${labelY} C${hxPos + curveOffset * 0.5},${labelY + 10} ${hxPos + 8},${targetY - 12} ${hxPos + 2},${targetY - 6}`;

      g.append('path')
        .attr('d', arrowPath)
        .attr('fill', 'none')
        .attr('stroke', balColor)
        .attr('stroke-width', 1)
        .attr('opacity', 0.8)
        .attr('marker-end', 'url(#arrow-hyde)');

      g.append('text')
        .attr('x', hxPos + curveOffset + 2)
        .attr('y', labelY + 4)
        .attr('font-family', FONT_MONO)
        .attr('font-size', isMobile ? '8px' : '9px')
        .attr('font-weight', '700')
        .attr('fill', balColor)
        .attr('text-anchor', 'start')
        .text('(5/17) Brandon Hyde fired');
    }

    // Bracket annotation helper
    const drawBracket = (startDate: Date, endDate: Date, line1: string, line2: string, rotateOffset: number | null = -0.08, extraX = 0, extraY = 0, curveLeft = false, barBend: number | null = null) => {
      const bsx1 = x(startDate);
      const bsx2 = x(endDate);
      if (bsx1 < 0 || bsx2 > innerWidth) return;

      const balPts = parsedData['BAL'];
      const bisectDate = d3.bisector<{ date: Date; playoff_pct: number }, Date>(d => d.date).left;
      let by1Val = y(50), by2Val = y(50);
      if (balPts?.length) {
        const i1 = bisectDate(balPts, startDate, 1);
        const p1 = balPts[i1 - 1] ?? balPts[0];
        by1Val = y(p1.playoff_pct);
        const i2 = bisectDate(balPts, endDate, 1);
        const p2 = balPts[i2] ?? balPts[i2 - 1] ?? balPts[balPts.length - 1];
        by2Val = y(p2.playoff_pct);
      }

      const rawAngle = Math.atan2(by2Val - by1Val, bsx2 - bsx1);
      const bAngle = rotateOffset === null ? 0 : rawAngle + rotateOffset;
      const perpDist = isMobile ? 9 : 12;
      const perpX = Math.sin(bAngle) * perpDist;
      const perpY = -Math.cos(bAngle) * perpDist;
      const shiftLeft = isMobile ? 2 : 4;
      // When flattened, use average y so the bar is truly horizontal
      const flatY = rotateOffset === null ? (by1Val + by2Val) / 2 - (isMobile ? 6 : 8) : null;
      const bx1 = bsx1 + perpX - shiftLeft + extraX;
      const bby1 = (flatY ?? by1Val) + perpY + extraY;
      const bx2 = bsx2 + perpX - shiftLeft + extraX + (rotateOffset === null && curveLeft ? (isMobile ? -8 : -12) : rotateOffset === null ? (isMobile ? -3 : -4) : 0);
      const bby2 = (flatY ?? by2Val) + perpY + extraY + (rotateOffset === null && curveLeft ? (isMobile ? 10 : 14) : rotateOffset === null ? (isMobile ? 4 : 5) : 0);
      const tickLen = isMobile ? 3 : 4;
      const tickDx = -Math.sin(bAngle) * tickLen;
      const tickDy = Math.cos(bAngle) * tickLen;

      g.append('line').attr('x1', bx1).attr('y1', bby1).attr('x2', bx1 + tickDx).attr('y2', bby1 + tickDy)
        .attr('stroke', theme.textMuted).attr('stroke-width', 1).attr('stroke-dasharray', '3,2').attr('opacity', 0.8);
      g.append('line').attr('x1', bx2).attr('y1', bby2).attr('x2', bx2 + tickDx).attr('y2', bby2 + tickDy)
        .attr('stroke', theme.textMuted).attr('stroke-width', 1).attr('stroke-dasharray', '3,2').attr('opacity', 0.8);
      const bendH = barBend ?? (isMobile ? 4 : 6);
      const cpx = (bx1 + bx2) / 2 + Math.sin(bAngle) * bendH;
      const cpy = (bby1 + bby2) / 2 - Math.cos(bAngle) * bendH;
      // Actual peak of quadratic Bezier at t=0.5: B(0.5) = 0.25*P0 + 0.5*CP + 0.25*P2
      const bmx = 0.25 * bx1 + 0.5 * cpx + 0.25 * bx2;
      const bmy = 0.25 * bby1 + 0.5 * cpy + 0.25 * bby2;
      g.append('path')
        .attr('d', `M${bx1},${bby1} Q${cpx},${cpy} ${bx2},${bby2}`)
        .attr('fill', 'none').attr('stroke', theme.textMuted).attr('stroke-width', 1).attr('stroke-dasharray', '3,2').attr('opacity', 0.8);
      const stemH = isMobile ? 38 : 52;
      const curveOffsetX = curveLeft ? (isMobile ? 12 : 18) : (isMobile ? 25 : 35);
      const dir = curveLeft ? -1 : 1;
      const tipX = bmx + curveOffsetX * dir;
      const tipY = bmy - stemH;

      g.append('path')
        .attr('d', `M${bmx},${bmy} C${bmx},${bmy - stemH * 0.4} ${tipX - curveOffsetX * 0.3 * dir},${tipY + stemH * 0.2} ${tipX},${tipY}`)
        .attr('fill', 'none').attr('stroke', theme.textMuted).attr('stroke-width', 1).attr('stroke-dasharray', '3,2').attr('opacity', 0.8);

      g.append('text').attr('x', tipX).attr('y', tipY - (isMobile ? 10 : 12))
        .attr('font-family', FONT_MONO).attr('font-size', isMobile ? '8px' : '9px')
        .attr('font-weight', '600').attr('fill', theme.textMuted).attr('text-anchor', 'middle').text(line1);
      g.append('text').attr('x', tipX).attr('y', tipY - (isMobile ? 2 : 3))
        .attr('font-family', FONT_MONO).attr('font-size', isMobile ? '8px' : '9px')
        .attr('font-weight', '600').attr('fill', theme.textMuted).attr('text-anchor', 'middle').text(line2);
    };

    drawBracket(new Date(2025, 3, 20), new Date(2025, 3, 28), 'Lost 7', 'out of 9', 0, 0, -14, true, isMobile ? 18 : 26);
    drawBracket(new Date(2025, 4, 4), new Date(2025, 4, 11), '5-game losing', 'streak', null);
    drawBracket(new Date(2025, 4, 14), new Date(2025, 4, 20), '8-game losing', 'streak', -0.08);
  }

  // --- Team visibility state ---
  const otherTeams = teams.filter(t => t !== 'BAL');

  // Lines
  const line = d3.line<{ date: Date; playoff_pct: number }>()
    .x(d => x(d.date))
    .y(d => y(d.playoff_pct))
    .curve(d3.curveMonotoneX);

  const teamPaths: Record<string, d3.Selection<SVGPathElement | SVGCircleElement, any, any, any>> = {};

  for (const team of teams) {
    const color = TEAM_COLORS[team] ?? theme.textSecondary;
    const pts = parsedData[team];
    const isOther = team !== 'BAL';

    if (pts.length === 1) {
      // Pulsing ring behind BAL dot (current season only)
      if (!isOther && isCurrent && !noMotion) {
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

      if ((!isOther || showAllTeams) && !noMotion) {
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
      } else if (noMotion) {
        // Show immediately
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
      if (!isOther && isCurrent && !noMotion) {
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
      } else if (!isOther && !noMotion) {
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

  // For 2026 (current season), find the last date with actual data
  const maxDataDate = isCurrent
    ? d3.max(teams, team => {
        const pts = parsedData[team];
        return pts?.length ? pts[pts.length - 1].date : undefined;
      }) ?? null
    : null;

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
      .attr('r', focusDotR)
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

      if (maxDataDate && hoveredDate > maxDataDate) {
        focus.style('display', 'none');
        tooltip.hide();
        return;
      }
      focus.style('display', null);

      focus.select('.focus-line').attr('x1', mx).attr('x2', mx);

      let html = `<span style="font-family:${FONT_MONO};font-size:10px;font-weight:600;color:${theme.textMuted};text-transform:uppercase;letter-spacing:0.04em">${d3.timeFormat('%b %d, %Y')(hoveredDate)}</span>`;

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

        const color = TEAM_COLORS[team] ?? theme.textSecondary;
        const name = TEAM_NAMES[team] ?? team;
        html += `<div style="display:flex;align-items:center;gap:6px;margin-top:4px">`;
        html += `<span style="width:8px;height:8px;border-radius:50%;background:${color};flex-shrink:0"></span>`;
        html += `<span style="font-weight:500;color:${theme.text}">${name}</span>`;
        html += `<span style="font-family:${FONT_MONO};font-weight:700;color:${theme.text};margin-left:auto">${pct.toFixed(1)}%</span>`;
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
    const color = TEAM_COLORS[team] ?? theme.textSecondary;
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

}
