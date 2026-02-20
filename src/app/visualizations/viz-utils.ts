export const TEAM_COLORS: Record<string, string> = {
  BAL: '#df4a00', NYY: '#7a7a7a', BOS: '#8b1a2b', TB: '#5bb5e8', TOR: '#134A8E',
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

export interface VizColorTheme {
  text: string;
  textSecondary: string;
  textMuted: string;
  border: string;
  bg: string;
}

export const LIGHT_THEME: VizColorTheme = {
  text: COLOR_TEXT,
  textSecondary: COLOR_TEXT_SECONDARY,
  textMuted: COLOR_TEXT_MUTED,
  border: COLOR_BORDER,
  bg: COLOR_BG,
};

export const DARK_THEME: VizColorTheme = {
  text: '#e8e8ed',
  textSecondary: '#a0a0ab',
  textMuted: '#6b6b78',
  border: '#2a2a32',
  bg: '#1a1a1f',
};

/** Read the current theme from the DOM data-theme attribute */
export function getActiveTheme(): VizColorTheme {
  if (typeof document === 'undefined') return LIGHT_THEME;
  return document.documentElement.getAttribute('data-theme') === 'dark' ? DARK_THEME : LIGHT_THEME;
}

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
  const theme = getActiveTheme();
  const el = d3
    .select(container)
    .append('div')
    .attr('class', 'viz-tooltip')
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

  return {
    show(html: string) {
      el.html(html).style('opacity', '1');
    },
    move(event: MouseEvent) {
      const rect = container.getBoundingClientRect();
      const cursorX = event.clientX - rect.left;
      const cursorY = event.clientY - rect.top;
      const tooltipNode = el.node() as HTMLElement;
      const tooltipW = tooltipNode.offsetWidth;

      // Flip to left side if tooltip would overflow container
      const leftPos = cursorX + 14 + tooltipW > rect.width
        ? cursorX - tooltipW - 14
        : cursorX + 14;

      el.style('left', `${leftPos}px`).style('top', `${cursorY - 12}px`);
    },
    hide() {
      el.style('opacity', '0');
    },
  };
}
