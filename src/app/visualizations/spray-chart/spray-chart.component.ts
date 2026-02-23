import {
  Component,
  AfterViewInit,
  OnInit,
  ElementRef,
  viewChild,
  PLATFORM_ID,
  inject,
} from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { SeoService } from '../../core/services/seo.service';
import { ShareButtonsComponent } from '../../shared/components/share-buttons/share-buttons.component';
import { environment } from '../../../environments/environment';
import { prefersReducedMotion } from '../viz-utils';

interface HitData {
  x: number;
  y: number;
  type: 'single' | 'double' | 'triple' | 'homerun' | 'out';
}

@Component({
  selector: 'app-spray-chart',
  standalone: true,
  imports: [ShareButtonsComponent],
  templateUrl: './spray-chart.component.html',
  styleUrl: './spray-chart.component.css',
})
export class SprayChartComponent implements OnInit, AfterViewInit {
  chartContainer = viewChild<ElementRef>('chartContainer');
  private platformId = inject(PLATFORM_ID);
  private seo = inject(SeoService);
  isBrowser = false;

  private sampleData: HitData[] = [
    { x: 120, y: 280, type: 'single' },
    { x: 200, y: 150, type: 'double' },
    { x: 350, y: 100, type: 'homerun' },
    { x: 280, y: 200, type: 'out' },
    { x: 80, y: 180, type: 'triple' },
    { x: 300, y: 280, type: 'single' },
    { x: 250, y: 120, type: 'double' },
    { x: 150, y: 100, type: 'homerun' },
    { x: 320, y: 250, type: 'out' },
    { x: 180, y: 230, type: 'single' },
    { x: 220, y: 80, type: 'homerun' },
    { x: 100, y: 220, type: 'out' },
    { x: 260, y: 160, type: 'double' },
    { x: 340, y: 180, type: 'out' },
    { x: 140, y: 140, type: 'triple' },
  ];

  constructor() {
    this.isBrowser = isPlatformBrowser(this.platformId);
  }

  ngOnInit(): void {
    this.seo.setPageMeta({
      title: 'Spray Chart — Birdland Metrics',
      description: 'Interactive spray chart visualization for baseball hit data.',
      path: '/visualizations/spray-chart',
      image: `${environment.s3.ogImages}/spray-chart.png`,
    });
    this.seo.setJsonLd(this.seo.getOrganizationSchema());
  }

  async ngAfterViewInit(): Promise<void> {
    if (!this.isBrowser) return;

    const d3 = await import('d3');
    this.renderChart(d3);
  }

  private renderChart(d3: typeof import('d3')): void {
    const container = this.chartContainer()?.nativeElement;
    if (!container) return;

    const width = 400;
    const height = 400;
    const margin = { top: 20, right: 20, bottom: 20, left: 20 };

    const svg = d3
      .select(container)
      .append('svg')
      .attr('viewBox', `0 0 ${width} ${height}`)
      .attr('preserveAspectRatio', 'xMidYMid meet');

    // Draw field outline
    const cx = width / 2;
    const cy = height - margin.bottom;

    // Outfield arc
    const arcGenerator = d3.arc()
      .innerRadius(0)
      .outerRadius(350)
      .startAngle(-Math.PI / 4)
      .endAngle(Math.PI / 4);

    svg
      .append('path')
      .attr('d', arcGenerator as unknown as string)
      .attr('transform', `translate(${cx}, ${cy})`)
      .attr('fill', '#2d5016')
      .attr('opacity', 0.15);

    // Infield diamond
    const diamondSize = 80;
    const diamond = [
      [cx, cy - diamondSize],
      [cx + diamondSize * 0.7, cy - diamondSize * 0.5],
      [cx, cy],
      [cx - diamondSize * 0.7, cy - diamondSize * 0.5],
    ];

    svg
      .append('polygon')
      .attr('points', diamond.map((d) => d.join(',')).join(' '))
      .attr('fill', '#c4956a')
      .attr('opacity', 0.3)
      .attr('stroke', '#8b7355')
      .attr('stroke-width', 1);

    // Foul lines
    svg
      .append('line')
      .attr('x1', cx).attr('y1', cy)
      .attr('x2', margin.left).attr('y2', margin.top)
      .attr('stroke', '#fff')
      .attr('stroke-width', 1.5)
      .attr('opacity', 0.5);

    svg
      .append('line')
      .attr('x1', cx).attr('y1', cy)
      .attr('x2', width - margin.right).attr('y2', margin.top)
      .attr('stroke', '#fff')
      .attr('stroke-width', 1.5)
      .attr('opacity', 0.5);

    // Hit type colors
    const colorMap: Record<string, string> = {
      single: '#4CAF50',
      double: '#2196F3',
      triple: '#FF9800',
      homerun: '#df4a00',
      out: '#999',
    };

    // Plot hits
    const hits = svg
      .selectAll('circle.hit')
      .data(this.sampleData)
      .enter()
      .append('circle')
      .attr('class', 'hit')
      .attr('cx', (d) => d.x)
      .attr('cy', (d) => d.y)
      .attr('fill', (d) => colorMap[d.type])
      .attr('stroke', '#fff')
      .attr('stroke-width', 1.5)
      .attr('opacity', 0.85);

    if (prefersReducedMotion()) {
      hits.attr('r', 6);
    } else {
      hits.attr('r', 0)
        .transition()
        .duration(500)
        .delay((_, i) => i * 50)
        .attr('r', 6);
    }

    // Legend
    const legendData = ['single', 'double', 'triple', 'homerun', 'out'];
    const legend = svg
      .append('g')
      .attr('transform', `translate(${margin.left + 5}, ${margin.top + 5})`);

    legendData.forEach((type, i) => {
      const g = legend.append('g').attr('transform', `translate(0, ${i * 20})`);
      g.append('circle').attr('r', 5).attr('cx', 5).attr('cy', 0).attr('fill', colorMap[type]);
      g.append('text')
        .attr('x', 16)
        .attr('y', 4)
        .attr('font-size', '11px')
        .attr('fill', '#666')
        .text(type === 'homerun' ? 'HR' : type.charAt(0).toUpperCase() + type.slice(1));
    });
  }
}
