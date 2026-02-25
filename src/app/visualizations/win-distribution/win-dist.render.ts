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
  prevMedian?: Record<string, number>;
  updated?: string;
}

interface BarData { wins: number; freq: number; density: number; }
interface TeamBarEntry { team: string; bars: BarData[]; projection: TeamProjection; }

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

/** Area-curve renderer used when 3+ teams are displayed. */
function renderCurves(
  g: d3.Selection<SVGGElement, unknown, null, undefined>,
  teamBars: TeamBarEntry[],
  x: d3.ScaleBand<number>,
  y: d3.ScaleLinear<number, number, never>,
  xMin: number,
  xMax: number,
  innerWidth: number,
  innerHeight: number,
  theme: VizColorTheme,
  d3: typeof import('d3'),
  container: HTMLElement,
  config: WinDistributionConfig,
): void {
  // Prevent tooltip overflow from causing scrollbars
  container.style.overflow = 'hidden';

  const bandwidth = x.bandwidth();

  const areaGen = d3.area<BarData>()
    .x(d => (x(d.wins) ?? 0) + bandwidth / 2)
    .y0(innerHeight)
    .y1(d => y(d.freq))
    .curve(d3.curveMonotoneX);

  const lineGen = d3.line<BarData>()
    .x(d => (x(d.wins) ?? 0) + bandwidth / 2)
    .y(d => y(d.freq))
    .curve(d3.curveMonotoneX);

  // Draw filled areas + stroke lines for each team
  for (const { team, bars } of teamBars) {
    const color = TEAM_COLORS[team] ?? theme.textSecondary;

    g.append('path')
      .datum(bars)
      .attr('d', areaGen)
      .attr('fill', color)
      .attr('opacity', 0.15);

    g.append('path')
      .datum(bars)
      .attr('d', lineGen)
      .attr('fill', 'none')
      .attr('stroke', color)
      .attr('stroke-width', 2)
      .attr('opacity', 0.8);
  }

  // Median dashed lines
  for (const { team, projection: td } of teamBars) {
    const color = TEAM_COLORS[team] ?? theme.textSecondary;
    const medianWin = Math.round(td.avg_wins);
    const medianX = (x(medianWin) ?? 0) + bandwidth / 2;

    g.append('line')
      .attr('x1', medianX).attr('x2', medianX)
      .attr('y1', 0).attr('y2', innerHeight)
      .attr('stroke', color)
      .attr('stroke-width', 1.5)
      .attr('stroke-dasharray', '6,4')
      .attr('opacity', 0.6);
  }

  // Annotation arrows — labels offset to alternating sides, curved arrows to each peak
  const sorted = [...teamBars].sort((a, b) => a.projection.avg_wins - b.projection.avg_wins);
  const svgEl = d3.select(container).select('svg');
  svgEl.select('defs').empty() && svgEl.append('defs');

  // Pre-defined layout per slot — sides chosen so no arrow crosses another label
  // Sorted order: TB, BAL, BOS, TOR, NYY
  const layouts = [
    { dir: -1, xOff: 68, yBump: 0 },    // TB: left, low
    { dir: -1, xOff: 65, yBump: 28 },   // BAL: left, high (clears TB)
    { dir: -1, xOff: 50, yBump: 50 },   // BOS: tall, bent left
    { dir:  1, xOff: 70, yBump: 42 },   // TOR: right, high
    { dir:  1, xOff: 58, yBump: 20 },   // NYY: right, mid
  ];

  // Collect all annotation rects for collision resolution
  const charW = 7.2;
  const rowH = 18;
  const placedAnnotations: { lx: number; ly: number; halfW: number }[] = [];

  for (let i = 0; i < sorted.length; i++) {
    const { team, bars, projection: td } = sorted[i];
    const color = TEAM_COLORS[team] ?? theme.textSecondary;
    const medianWin = Math.round(td.avg_wins);
    const medianX = (x(medianWin) ?? 0) + bandwidth / 2;

    // Find peak of this team's curve
    const peakBar = bars.reduce((a, b) => b.freq > a.freq ? b : a);
    const peakY = y(peakBar.freq);

    const layout = layouts[i % layouts.length];
    let labelX = medianX + layout.xOff * layout.dir;
    let labelY = -18 - layout.yBump;

    let label = `${team} ${medianWin}W`;
    if (config.prevMedian?.[team] != null) {
      const delta = medianWin - config.prevMedian[team];
      if (delta > 0) label += ` \u2191${delta}`;
      else if (delta < 0) label += ` \u2193${Math.abs(delta)}`;
    }

    const halfW = (label.length * charW) / 2;
    const anchor = layout.dir === -1 ? 'end' : 'start';

    // Nudge if colliding with an already-placed annotation
    for (const placed of placedAnnotations) {
      const hOverlap = layout.dir === -1
        ? Math.abs((labelX - halfW) - (placed.lx - placed.halfW)) < halfW + placed.halfW
        : Math.abs((labelX + halfW) - (placed.lx + placed.halfW)) < halfW + placed.halfW;
      if (hOverlap && Math.abs(labelY - placed.ly) < rowH) {
        labelY = placed.ly - rowH;
      }
    }
    placedAnnotations.push({ lx: labelX, ly: labelY, halfW });

    // Clamp label X within chart area
    if (layout.dir === -1 && labelX - halfW * 2 < -30) labelX = halfW * 2 - 30;
    if (layout.dir === 1 && labelX + halfW * 2 > innerWidth + 30) labelX = innerWidth + 30 - halfW * 2;

    // Arrow marker for this team
    const arrowId = `curve-arrow-${team}`;
    svgEl.select('defs').append('marker')
      .attr('id', arrowId)
      .attr('viewBox', '0 0 10 10')
      .attr('refX', 8).attr('refY', 5)
      .attr('markerWidth', 5).attr('markerHeight', 5)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M 0 1 L 10 5 L 0 9 Z')
      .attr('fill', color);

    // Curved arrow from label to top of median line (y=0)
    const arrowStartX = layout.dir === 1 ? labelX - 6 : labelX + 6;
    const arrowStartY = labelY;
    const arrowEndX = medianX;
    const arrowEndY = -2;

    // Control point — arc upward between label and median top
    const midX = (arrowStartX + arrowEndX) / 2;
    const arcLift = 10 + layout.yBump * 0.2;
    const ctrlX = midX + ((i * 5 + 3) % 7 - 3); // slight horizontal jitter
    const ctrlY = Math.min(arrowStartY, arrowEndY) - arcLift;

    g.append('path')
      .attr('d', `M ${arrowStartX} ${arrowStartY} Q ${ctrlX} ${ctrlY} ${arrowEndX} ${arrowEndY}`)
      .attr('fill', 'none')
      .attr('stroke', color)
      .attr('stroke-width', 1.5)
      .attr('marker-end', `url(#${arrowId})`)
      .attr('opacity', 0.7);

    // Sketch double-stroke for hand-drawn feel
    g.append('path')
      .attr('d', `M ${arrowStartX + 0.6} ${arrowStartY + 0.5} Q ${ctrlX + 0.9} ${ctrlY + 0.4} ${arrowEndX + 0.4} ${arrowEndY + 0.3}`)
      .attr('fill', 'none')
      .attr('stroke', color)
      .attr('stroke-width', 0.6)
      .attr('opacity', 0.18);

    // Label text — vertically centered at the arrow tail
    g.append('text')
      .attr('x', labelX)
      .attr('y', labelY)
      .attr('text-anchor', anchor)
      .attr('dominant-baseline', 'central')
      .attr('font-family', FONT_SANS)
      .attr('font-size', '13px')
      .attr('font-weight', '700')
      .attr('fill', color)
      .text(label);
  }

  // Hover interaction — vertical line + clamped tooltip
  const tooltipEl = d3.select(container)
    .append('div')
    .style('position', 'absolute')
    .style('pointer-events', 'none')
    .style('z-index', '10')
    .style('background', theme.bg)
    .style('border', `1px solid ${theme.border}`)
    .style('border-radius', '4px')
    .style('padding', '8px 12px')
    .style('font-family', FONT_SANS)
    .style('font-size', '12px')
    .style('line-height', '1.5')
    .style('color', theme.text)
    .style('white-space', 'nowrap')
    .style('opacity', '0')
    .style('transition', 'opacity 150ms ease');

  const hoverLine = g.append('line')
    .attr('y1', 0).attr('y2', innerHeight)
    .attr('stroke', theme.textMuted)
    .attr('stroke-width', 1)
    .attr('stroke-dasharray', '4,3')
    .attr('opacity', 0);

  g.append('rect')
    .attr('width', innerWidth)
    .attr('height', innerHeight)
    .attr('fill', 'none')
    .attr('pointer-events', 'all')
    .on('mousemove', (event: MouseEvent) => {
      const [mx] = d3.pointer(event);
      const hoveredWin = Math.round(xMin + (mx / innerWidth) * (xMax - xMin));
      const clampedWin = Math.max(xMin, Math.min(xMax, hoveredWin));
      const hoverX = (x(clampedWin) ?? 0) + bandwidth / 2;

      hoverLine.attr('x1', hoverX).attr('x2', hoverX).attr('opacity', 0.5);

      let html = `<span style="font-family:${FONT_MONO};font-size:10px;font-weight:600;color:${theme.textMuted};text-transform:uppercase;letter-spacing:0.04em">${clampedWin} WINS</span>`;

      const entries = teamBars.map(({ team, bars }) => {
        const bar = bars.find(b => b.wins === clampedWin);
        return { team, freq: bar?.freq ?? 0, pct: (bar?.density ?? 0) * 100 };
      }).sort((a, b) => b.freq - a.freq);

      for (const { team, freq, pct } of entries) {
        const color = TEAM_COLORS[team] ?? theme.textSecondary;
        html += `<div style="margin-top:4px;font-family:${FONT_MONO};font-size:12px">`;
        html += `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${color};margin-right:6px;vertical-align:middle"></span>`;
        html += `<span style="font-weight:600;color:${color}">${TEAM_NAMES[team] ?? team}</span>`;
        html += `<span style="font-weight:500;color:${theme.textSecondary}"> ${freq} </span>`;
        html += `<span style="font-weight:500;color:${theme.textMuted}">(${pct.toFixed(1)}%)</span>`;
        html += `</div>`;
      }

      tooltipEl.html(html).style('opacity', '1');

      // Clamp tooltip position within container bounds
      const rect = container.getBoundingClientRect();
      const cursorX = event.clientX - rect.left;
      const cursorY = event.clientY - rect.top;
      const node = tooltipEl.node() as HTMLElement;
      const tw = node.offsetWidth;
      const th = node.offsetHeight;

      let left = cursorX + 14;
      if (left + tw > rect.width) left = cursorX - tw - 14;
      if (left < 0) left = 0;

      let top = cursorY - 12;
      if (top + th > rect.height) top = rect.height - th;
      if (top < 0) top = 0;

      tooltipEl.style('left', `${left}px`).style('top', `${top}px`);
    })
    .on('mouseout', () => {
      hoverLine.attr('opacity', 0);
      tooltipEl.style('opacity', '0');
    });
}

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
  const isCurveMode = teamData.length > 2;

  const width = isCurveMode ? 860 : 700;
  const hasTitle = !!config.title;
  const height = compact ? 380 : isCurveMode ? 500 : (hasTitle ? 480 : 450);
  const margin = compact
    ? { top: 68, right: 36, bottom: 56, left: 48 }
    : { top: (hasTitle ? 36 : 28) + (isCurveMode ? 90 : 0), right: 48, bottom: 80, left: 64 };

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

  if (config.updated && isCurveMode) {
    const d = new Date(config.updated + 'Z');
    const month = d.toLocaleDateString('en-US', { month: 'short', timeZone: 'America/New_York' });
    const day = d.getDate();
    const suffix = ['th','st','nd','rd'][(day % 100 - 20) % 10] || ['th','st','nd','rd'][day % 100] || 'th';
    const time = d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', timeZone: 'America/New_York' });
    svg.append('text')
      .attr('x', width / 2)
      .attr('y', 10)
      .attr('text-anchor', 'middle')
      .attr('font-family', FONT_MONO)
      .attr('font-size', '10px')
      .attr('font-weight', '700')
      .attr('fill', theme.textSecondary)
      .text(`Last updated ${month} ${day}${suffix}, ${d.getFullYear()} · ${time} ET`);
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
  const teamBars: TeamBarEntry[] = [];
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
      .attr('font-size', compact ? '16px' : '14px')
      .attr('font-weight', '600')
      .attr('dy', '1.2em'));

  // X axis label
  g.append('text')
    .attr('x', innerWidth / 2)
    .attr('y', innerHeight + (compact ? 44 : 56))
    .attr('text-anchor', 'middle')
    .attr('fill', theme.textMuted)
    .attr('font-family', FONT_MONO)
    .attr('font-size', compact ? '13px' : '12px')
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
      .attr('font-size', compact ? '13px' : '12px')
      .attr('dx', '-0.4em'));

  // Y axis label
  g.append('text')
    .attr('transform', 'rotate(-90)')
    .attr('y', compact ? -36 : -42)
    .attr('x', -innerHeight / 2)
    .attr('text-anchor', 'middle')
    .attr('fill', theme.textMuted)
    .attr('font-family', FONT_MONO)
    .attr('font-size', compact ? '13px' : '12px')
    .attr('font-weight', '600')
    .attr('letter-spacing', '0.06em')
    .text(`FREQUENCY (${(NUM_SIMULATIONS).toLocaleString()} sims)`);

  // --- Curve mode for 3+ teams ---
  if (isCurveMode) {
    renderCurves(g, teamBars, x, y, xMin, xMax, innerWidth, innerHeight, theme, d3, container, config);
    return;
  }

  // --- Bar mode for 1-2 teams ---

  // 90% confidence interval (mean +/- 1.645 sigma)
  for (const { team, projection: td } of teamBars) {
    const color = TEAM_COLORS[team] ?? theme.textSecondary;
    const ciLo = Math.round(td.avg_wins - 1.645 * td.std_dev);
    const ciHi = Math.round(td.avg_wins + 1.645 * td.std_dev);

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
        .text(`90% CI: ${ciLo}\u2013${ciHi} Wins`);
    } else {
      g.append('text')
        .attr('x', ciMidX)
        .attr('y', -4)
        .attr('text-anchor', 'middle')
        .attr('font-family', FONT_MONO)
        .attr('font-size', '12px')
        .attr('font-weight', '600')
        .attr('fill', theme.textMuted)
        .text(`90% Confidence Interval: ${ciLo}\u2013${ciHi} Wins`);
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

    let medianLabel = `${medianWin} wins`;
    if (config.prevMedian?.[team] != null) {
      const delta = medianWin - config.prevMedian[team];
      if (delta > 0) medianLabel += ` \u2191${delta}`;
      else if (delta < 0) medianLabel += ` \u2193${Math.abs(delta)}`;
    }

    g.append('text')
      .attr('x', labelX + 3)
      .attr('y', curveBottomY - 24)
      .attr('text-anchor', 'start')
      .attr('dominant-baseline', 'central')
      .attr('font-family', FONT_SANS)
      .attr('font-size', compact ? '18px' : '16px')
      .attr('font-weight', '700')
      .attr('fill', color)
      .text(medianLabel);
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
