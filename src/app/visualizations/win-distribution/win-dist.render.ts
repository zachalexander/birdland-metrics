import {
  TEAM_COLORS, createResponsiveSvg, createTooltip, getActiveTheme,
  FONT_MONO, FONT_SANS,
  VizColorTheme,
} from '../viz-utils';
import { TEAM_NAMES, TeamProjection } from '../../shared/models/mlb.models';

export interface WinDistributionConfig {
  teams: string[];
  title?: string;
  theme?: VizColorTheme;
  compact?: boolean;
}

function normalPdf(x: number, mean: number, std: number): number {
  return Math.exp(-0.5 * ((x - mean) / std) ** 2) / (std * Math.sqrt(2 * Math.PI));
}

/** Probability of exactly `w` wins = integral of normal PDF from w-0.5 to w+0.5 (continuity correction). */
function winProbability(w: number, mean: number, std: number): number {
  return normalPdf(w, mean, std);
}

/** Convert density to a simulated frequency out of `n` simulations. */
function densityToFrequency(density: number, n: number): number {
  return Math.round(density * n);
}

const NUM_SIMULATIONS = 10000;

export function renderWinDistribution(
  container: HTMLElement,
  projections: TeamProjection[],
  config: WinDistributionConfig,
  d3: typeof import('d3'),
): void {
  container.innerHTML = '';
  const activeTheme = getActiveTheme();

  const teamData = config.teams
    .map(t => projections.find(p => p.team === t))
    .filter((p): p is TeamProjection => !!p);

  if (!teamData.length) {
    const msg = document.createElement('p');
    msg.className = 'viz-empty-state';
    msg.textContent = 'No projection data available for the selected teams.';
    container.appendChild(msg);
    return;
  }

  const theme = config.theme ?? activeTheme;
  const compact = config.compact ?? false;

  const width = 700;
  const hasTitle = !!config.title;
  const height = compact ? 380 : hasTitle ? 480 : 450;
  const margin = compact
    ? { top: 68, right: 36, bottom: 56, left: 48 }
    : { top: hasTitle ? 36 : 28, right: 48, bottom: 80, left: 64 };

  const { svg, g, innerWidth, innerHeight } = createResponsiveSvg(d3, container, width, height, margin);

  // Title (rendered inside SVG above the chart area)
  if (hasTitle) {
    svg.append('text')
      .attr('x', width / 2)
      .attr('y', 22)
      .attr('text-anchor', 'middle')
      .attr('font-family', FONT_MONO)
      .attr('font-size', '14px')
      .attr('font-weight', '700')
      .attr('letter-spacing', '0.04em')
      .attr('fill', theme.text)
      .text(config.title!);
  }

  // Compact title (rendered after we know median, but we need teamData now for the text)
  if (compact && teamData.length) {
    const medianForTitle = Math.round(teamData[0].avg_wins);
    const titleY = 24;
    const fontSize = 20;
    const prefix = 'A majority of simulations predict an ';
    const highlight = `${medianForTitle}-win`;
    const suffix = ' season.';

    // Render the text first so we can measure the tspan
    const titleText = svg.append('text')
      .attr('x', width / 2)
      .attr('y', titleY)
      .attr('text-anchor', 'middle')
      .attr('font-family', FONT_SANS)
      .attr('font-size', `${fontSize}px`)
      .attr('font-weight', '700')
      .attr('fill', theme.text);

    titleText.append('tspan').text(prefix);
    const hlSpan = titleText.append('tspan')
      .attr('font-weight', '800')
      .attr('fill', '#ffffff')
      .text(highlight);
    titleText.append('tspan').text(suffix);

    // Measure the highlight tspan and insert pill behind
    const hlNode = hlSpan.node() as SVGTSpanElement;
    if (hlNode) {
      const startPos = hlNode.getStartPositionOfChar(0);
      const hlW = hlNode.getComputedTextLength();
      const padX = 3;
      const padY = 2;
      svg.insert('rect', 'text')
        .attr('x', startPos.x - padX)
        .attr('y', startPos.y - fontSize + 3 - padY)
        .attr('width', hlW + padX * 2)
        .attr('height', fontSize + padY * 2)
        .attr('rx', 5)
        .attr('fill', '#df4a00');
    }
  }

  // Compute x domain from all teams (whole win numbers)
  let xMin = Infinity;
  let xMax = -Infinity;
  for (const td of teamData) {
    const lo = td.avg_wins - 3 * td.std_dev;
    const hi = td.avg_wins + 3 * td.std_dev;
    if (lo < xMin) xMin = lo;
    if (hi > xMax) xMax = hi;
  }
  xMin = Math.max(40, Math.floor(xMin));
  xMax = Math.min(120, Math.ceil(xMax));

  // Generate bar data for each whole win value per team
  interface BarData { wins: number; freq: number; density: number; }
  const teamBars: { team: string; bars: BarData[]; projection: TeamProjection }[] = [];
  let yMaxFreq = 0;

  for (const td of teamData) {
    const bars: BarData[] = [];
    for (let w = xMin; w <= xMax; w++) {
      const density = winProbability(w, td.avg_wins, td.std_dev);
      const freq = densityToFrequency(density, NUM_SIMULATIONS);
      bars.push({ wins: w, freq, density });
      if (freq > yMaxFreq) yMaxFreq = freq;
    }
    teamBars.push({ team: td.team, bars, projection: td });
  }

  // Scales
  const winValues = d3.range(xMin, xMax + 1);
  const x = d3.scaleBand<number>()
    .domain(winValues)
    .range([0, innerWidth])
    .padding(teamData.length > 1 ? 0.08 : 0.15);

  const y = d3.scaleLinear()
    .domain([0, yMaxFreq * 1.12])
    .nice()
    .range([innerHeight, 0]);

  // Horizontal grid lines
  g.append('g')
    .attr('class', 'grid')
    .call(d3.axisLeft(y).ticks(5).tickSize(-innerWidth).tickFormat(() => ''))
    .call(g => g.select('.domain').remove())
    .call(g => g.selectAll('.tick line').attr('stroke', theme.border));

  // X axis — show every Nth tick to avoid crowding
  const winCount = xMax - xMin + 1;
  const tickInterval = winCount > 40 ? 5 : winCount > 20 ? 3 : 2;

  g.append('g')
    .attr('transform', `translate(0,${innerHeight})`)
    .call(
      d3.axisBottom(x)
        .tickValues(winValues.filter(w => w % tickInterval === 0))
        .tickSize(0),
    )
    .call(g => g.select('.domain').attr('stroke', theme.text))
    .call(g => g.selectAll('.tick text')
      .attr('fill', theme.textMuted)
      .attr('font-family', FONT_MONO)
      .attr('font-size', compact ? '16px' : '22px')
      .attr('font-weight', '600')
      .attr('dy', '1.2em'));

  // X axis label
  g.append('text')
    .attr('x', innerWidth / 2)
    .attr('y', innerHeight + (compact ? 44 : 68))
    .attr('text-anchor', 'middle')
    .attr('fill', theme.textMuted)
    .attr('font-family', FONT_MONO)
    .attr('font-size', compact ? '13px' : '18px')
    .attr('font-weight', '600')
    .attr('letter-spacing', '0.06em')
    .text('PROJECTED WINS');

  // Y axis with frequency counts
  g.append('g')
    .call(d3.axisLeft(y).ticks(5).tickSize(0).tickFormat(d3.format(',.0f')))
    .call(g => g.select('.domain').remove())
    .call(g => g.selectAll('.tick text')
      .attr('fill', theme.textMuted)
      .attr('font-family', FONT_MONO)
      .attr('font-size', compact ? '13px' : '16px')
      .attr('dx', '-0.4em'));

  // Y axis label
  g.append('text')
    .attr('transform', 'rotate(-90)')
    .attr('y', compact ? -36 : -50)
    .attr('x', -innerHeight / 2)
    .attr('text-anchor', 'middle')
    .attr('fill', theme.textMuted)
    .attr('font-family', FONT_MONO)
    .attr('font-size', compact ? '13px' : '18px')
    .attr('font-weight', '600')
    .attr('letter-spacing', '0.06em')
    .text(`FREQUENCY (${(NUM_SIMULATIONS).toLocaleString()} sims)`);

  // 95% confidence interval (mean ± 1.96σ)
  for (const { team, projection: td } of teamBars) {
    const color = TEAM_COLORS[team] ?? theme.textSecondary;
    const ciLo = Math.round(td.avg_wins - 1.96 * td.std_dev);
    const ciHi = Math.round(td.avg_wins + 1.96 * td.std_dev);

    // Shaded background region
    const ciLoX = x(Math.max(ciLo, xMin)) ?? 0;
    const ciHiX = (x(Math.min(ciHi, xMax)) ?? 0) + x.bandwidth();
    g.append('rect')
      .attr('x', ciLoX)
      .attr('y', 0)
      .attr('width', ciHiX - ciLoX)
      .attr('height', innerHeight)
      .attr('fill', color)
      .attr('opacity', compact ? 0.08 : 0.04);

    // Dashed boundary lines
    for (const bound of [ciLo, ciHi]) {
      if (bound < xMin || bound > xMax) continue;
      const bx = bound === ciLo
        ? (x(bound) ?? 0)
        : (x(bound) ?? 0) + x.bandwidth();
      g.append('line')
        .attr('x1', bx).attr('x2', bx)
        .attr('y1', 0).attr('y2', innerHeight)
        .attr('stroke', color)
        .attr('stroke-width', 1.5)
        .attr('stroke-dasharray', '6,4')
        .attr('opacity', 0.5);
    }

    // Label + bracket above the CI region
    const ciMidX = (ciLoX + ciHiX) / 2;
    if (compact) {
      // Bracket: left tick, horizontal line, right tick
      const bracketY = -10;
      const tickH = 6;
      g.append('line')
        .attr('x1', ciLoX).attr('x2', ciLoX)
        .attr('y1', bracketY).attr('y2', bracketY + tickH)
        .attr('stroke', theme.textMuted).attr('stroke-width', 1.2);
      g.append('line')
        .attr('x1', ciLoX).attr('x2', ciHiX)
        .attr('y1', bracketY).attr('y2', bracketY)
        .attr('stroke', theme.textMuted).attr('stroke-width', 1.2);
      g.append('line')
        .attr('x1', ciHiX).attr('x2', ciHiX)
        .attr('y1', bracketY).attr('y2', bracketY + tickH)
        .attr('stroke', theme.textMuted).attr('stroke-width', 1.2);
      // Text above bracket
      g.append('text')
        .attr('x', ciMidX)
        .attr('y', bracketY - 8)
        .attr('text-anchor', 'middle')
        .attr('font-family', FONT_MONO)
        .attr('font-size', '12px')
        .attr('font-weight', '600')
        .attr('fill', theme.textMuted)
        .text(`95% CI: ${ciLo}–${ciHi} Wins`);
    } else {
      g.append('text')
        .attr('x', ciMidX)
        .attr('y', -4)
        .attr('text-anchor', 'middle')
        .attr('font-family', FONT_MONO)
        .attr('font-size', '18px')
        .attr('font-weight', '600')
        .attr('fill', theme.textMuted)
        .text(`95% Confidence Interval: ${ciLo}–${ciHi} Wins`);
    }
  }

  // Draw bars
  const OPACITY_DEFAULT = 0.45;
  const OPACITY_MEDIAN = 0.85;
  const OPACITY_HOVER = 1;
  const OPACITY_HOVER_REST = 0.35;

  for (let ti = 0; ti < teamBars.length; ti++) {
    const { team, bars, projection: td } = teamBars[ti];
    const color = TEAM_COLORS[team] ?? theme.textSecondary;
    const medianWin = Math.round(td.avg_wins);

    // Bars — median gets full color, others are more transparent
    g.selectAll(`.bar-${team}`)
      .data(bars)
      .join('rect')
      .attr('class', `bar-${team}`)
      .attr('x', d => x(d.wins) ?? 0)
      .attr('y', d => y(d.freq))
      .attr('width', x.bandwidth())
      .attr('height', d => innerHeight - y(d.freq))
      .attr('fill', color)
      .attr('opacity', d => d.wins === medianWin ? OPACITY_MEDIAN : OPACITY_DEFAULT)
      .attr('stroke', 'none')
      .attr('stroke-width', 0)
      .style('transition', 'opacity 100ms ease');

    // Median label above the highlighted bar
    const avgBandX = (x(medianWin) ?? 0) + x.bandwidth() / 2;
    const avgFreq = densityToFrequency(winProbability(medianWin, td.avg_wins, td.std_dev), NUM_SIMULATIONS);
    const avgBarTop = y(avgFreq);

    // Curved arrow from label to bar top
    const arrowId = `arrow-${team}`;
    svg.select('defs').empty() && svg.append('defs');
    svg.select('defs').append('marker')
      .attr('id', arrowId)
      .attr('viewBox', '0 0 10 10')
      .attr('refX', 5).attr('refY', 5)
      .attr('markerWidth', 5).attr('markerHeight', 5)
      .attr('orient', 'auto-start-reverse')
      .append('path')
      .attr('d', 'M 0 1 L 10 5 L 0 9 Z')
      .attr('fill', color);

    const labelOffsetX = compact ? 55 : 60;
    const labelX = avgBandX + labelOffsetX;
    const curveTopY = avgBarTop - 28;
    const curveBottomY = avgBarTop - 4;
    g.append('path')
      .attr('d', `M ${labelX} ${curveTopY} Q ${avgBandX} ${curveTopY} ${avgBandX} ${curveBottomY}`)
      .attr('fill', 'none')
      .attr('stroke', color)
      .attr('stroke-width', 1.5)
      .attr('marker-end', `url(#${arrowId})`);

    g.append('text')
      .attr('x', avgBandX + 58)
      .attr('y', curveBottomY - 24)
      .attr('text-anchor', 'start')
      .attr('dominant-baseline', 'central')
      .attr('font-family', FONT_SANS)
      .attr('font-size', compact ? '18px' : '24px')
      .attr('font-weight', '700')
      .attr('fill', color)
      .text(`${medianWin} wins`);
  }

  // Helper to reset bars to default state
  function resetBars() {
    for (const { team, projection: td } of teamBars) {
      const medianWin = Math.round(td.avg_wins);
      g.selectAll(`.bar-${team}`)
        .attr('opacity', (d: any) => d.wins === medianWin ? OPACITY_MEDIAN : OPACITY_DEFAULT)
        .attr('stroke', 'none')
        .attr('stroke-width', 0);
    }
  }

  // Tooltip + hover interaction
  const tooltip = createTooltip(d3, container);

  g.append('rect')
    .attr('width', innerWidth)
    .attr('height', innerHeight)
    .attr('fill', 'none')
    .attr('pointer-events', 'all')
    .on('mousemove', (event: MouseEvent) => {
      const [mx] = d3.pointer(event);
      const hoveredWin = Math.round(
        xMin + (mx / innerWidth) * (xMax - xMin),
      );
      const clampedWin = Math.max(xMin, Math.min(xMax, hoveredWin));

      // Update bar opacities + stroke on hovered bar
      for (const { team } of teamBars) {
        const color = TEAM_COLORS[team] ?? theme.textSecondary;
        g.selectAll(`.bar-${team}`)
          .attr('opacity', (d: any) => d.wins === clampedWin ? OPACITY_HOVER : OPACITY_HOVER_REST)
          .attr('stroke', (d: any) => d.wins === clampedWin ? color : 'none')
          .attr('stroke-width', (d: any) => d.wins === clampedWin ? 2 : 0);
      }

      let html = `<span style="font-family:${FONT_MONO};font-size:10px;font-weight:600;color:${theme.textMuted};text-transform:uppercase;letter-spacing:0.04em">${clampedWin} WINS</span>`;
      for (const { bars } of teamBars) {
        const bar = bars.find(b => b.wins === clampedWin);
        const freq = bar?.freq ?? 0;
        const pct = (bar?.density ?? 0) * 100;
        html += `<div style="margin-top:4px;font-family:${FONT_MONO};font-size:12px">`;
        html += `<span style="font-weight:700;color:${theme.text}">${freq}</span>`;
        html += `<span style="font-weight:500;color:${theme.textSecondary}"> times </span>`;
        html += `<span style="font-weight:500;color:${theme.textMuted}">(${pct.toFixed(1)}%)</span>`;
        html += `</div>`;
      }
      tooltip.show(html);
      tooltip.move(event);
    })
    .on('mouseout', () => {
      resetBars();
      tooltip.hide();
    });

}
