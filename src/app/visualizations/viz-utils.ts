export const TEAM_COLORS: Record<string, string> = {
  BAL: '#df4a00', NYY: '#003087', BOS: '#BD3039', TB: '#092C5C', TOR: '#134A8E',
  CLE: '#00385D', CWS: '#27251F', DET: '#0C2340', KC: '#004687', MIN: '#002B5C',
  HOU: '#002D62', LAA: '#BA0021', ATH: '#003831', SEA: '#0C2C56', TEX: '#003278',
  ATL: '#CE1141', MIA: '#00A3E0', NYM: '#002D72', PHI: '#E81828', WSH: '#AB0003',
  CHC: '#0E3386', CIN: '#C6011F', MIL: '#FFC52F', PIT: '#27251F', STL: '#C41E3A',
  ARI: '#A71930', COL: '#333366', LAD: '#005A9C', SD: '#2F241D', SF: '#FD5A1E',
};

// Design tokens matching styles.css :root
const FONT_MONO = "'JetBrains Mono', 'SF Mono', 'Fira Code', monospace";
const FONT_SANS = "'DM Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
const COLOR_TEXT = '#1a1a1a';
const COLOR_TEXT_SECONDARY = '#6b7280';
const COLOR_TEXT_MUTED = '#9ca3af';
const COLOR_BORDER = '#e5e7eb';
const COLOR_BG = '#ffffff';

export { FONT_MONO, FONT_SANS, COLOR_TEXT, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_BORDER, COLOR_BG };

export interface Margin {
  top: number;
  right: number;
  bottom: number;
  left: number;
}

export function createResponsiveSvg(
  d3: typeof import('d3'),
  container: HTMLElement,
  width: number,
  height: number,
  margin: Margin,
) {
  const svg = d3
    .select(container)
    .append('svg')
    .attr('viewBox', `0 0 ${width} ${height}`)
    .attr('preserveAspectRatio', 'xMidYMid meet')
    .style('width', '100%')
    .style('height', 'auto');

  const g = svg
    .append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`);

  return { svg, g, innerWidth: width - margin.left - margin.right, innerHeight: height - margin.top - margin.bottom };
}

export interface TooltipHelper {
  show: (html: string) => void;
  move: (event: MouseEvent) => void;
  hide: () => void;
}

export function createTooltip(d3: typeof import('d3'), container: HTMLElement): TooltipHelper {
  const el = d3
    .select(container)
    .append('div')
    .attr('class', 'viz-tooltip')
    .style('position', 'absolute')
    .style('pointer-events', 'none')
    .style('z-index', '10')
    .style('background', COLOR_BG)
    .style('border', `1px solid ${COLOR_BORDER}`)
    .style('border-radius', '4px')
    .style('padding', '8px 12px')
    .style('font-family', FONT_SANS)
    .style('font-size', '12px')
    .style('line-height', '1.5')
    .style('color', COLOR_TEXT)
    .style('opacity', '0')
    .style('transition', 'opacity 150ms ease');

  return {
    show(html: string) {
      el.html(html).style('opacity', '1');
    },
    move(event: MouseEvent) {
      const rect = container.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      el.style('left', `${x + 14}px`).style('top', `${y - 12}px`);
    },
    hide() {
      el.style('opacity', '0');
    },
  };
}
