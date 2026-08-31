import type { PDFDocumentProxy, RenderTask } from 'pdfjs-dist';

export interface PreviewData {
  sem: string;
  className: string;
  batch: string;
  rollNo: string;
  name: string;
  subject: string;
  isAssignment: boolean;
  expNo: string;
  title: string;
  perfDate: string;
  subDate: string;
  textColor: string;
  strikethroughEnabled: boolean;
}

export class PdfPreviewEngine {
  private activeRenderTask: RenderTask | null = null;
  private cachedTemplateDoc: PDFDocumentProxy | null = null;

  async loadTemplate(pdfUrl: string = '/Header.pdf'): Promise<void> {
    if (this.cachedTemplateDoc) return;

    const pdfjsLib = await import('pdfjs-dist');
    // Set worker source via Vite asset resolver
    pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
      'pdfjs-dist/build/pdf.worker.min.mjs',
      import.meta.url
    ).toString();

    try {
      this.cachedTemplateDoc = await pdfjsLib.getDocument(pdfUrl).promise;
    } catch {
      // Fallback: if running against Flask backend /api/download/Header.pdf
      this.cachedTemplateDoc = await pdfjsLib.getDocument('/Header.pdf').promise;
    }
  }

  async renderPreview(
    canvas: HTMLCanvasElement,
    data: PreviewData,
    scale: number = 1.3
  ): Promise<void> {
    if (!this.cachedTemplateDoc) {
      await this.loadTemplate();
    }
    if (!this.cachedTemplateDoc) return;

    // 1. Cancel in-flight render task safely
    if (this.activeRenderTask) {
      try {
        await this.activeRenderTask.cancel();
      } catch (err: any) {
        if (err?.name !== 'RenderingCancelledException') {
          console.warn('PDF.js render notice:', err);
        }
      }
      this.activeRenderTask = null;
    }

    const page = await this.cachedTemplateDoc.getPage(1);
    const dpr = window.devicePixelRatio || 1;
    const viewport = page.getViewport({ scale: scale * dpr });

    // 2. Set backing store dimensions for HiDPI sharpness
    canvas.width = Math.floor(viewport.width);
    canvas.height = Math.floor(viewport.height);

    // 3. Set CSS display dimensions
    canvas.style.width = `${Math.floor(viewport.width / dpr)}px`;
    canvas.style.height = `${Math.floor(viewport.height / dpr)}px`;

    const ctx = canvas.getContext('2d', { alpha: false });
    if (!ctx) return;

    // 4. Render PDF background
    this.activeRenderTask = page.render({
      canvasContext: ctx,
      viewport: viewport,
    });

    try {
      await this.activeRenderTask.promise;
      // 5. Draw overlay text on top of PDF at exact scaled coordinates
      this.drawCanvasOverlay(ctx, data, scale * dpr);
    } catch (err: any) {
      if (err?.name !== 'RenderingCancelledException') {
        throw err;
      }
    } finally {
      this.activeRenderTask = null;
    }
  }

  private drawCanvasOverlay(
    ctx: CanvasRenderingContext2D,
    data: PreviewData,
    scale: number
  ): void {
    ctx.save();
    const color = data.textColor || '#0000bf';
    ctx.fillStyle = color;
    ctx.textBaseline = 'alphabetic';

    const fontSize = 11 * scale;
    ctx.font = `${fontSize}px Helvetica, Arial, sans-serif`;

    // Coordinates matching PyMuPDF:
    // 1. SEM, CLASS, BATCH, ROLL NO
    ctx.fillText(data.sem || '', 100 * scale, 225 * scale);
    ctx.fillText(data.className || '', 205 * scale, 225 * scale);
    ctx.fillText(data.batch || '', 330 * scale, 225 * scale);
    ctx.fillText(data.rollNo || '', 470 * scale, 225 * scale);

    // 2. NAME & SUBJECT
    ctx.fillText(data.name || '', 110 * scale, 266 * scale);
    ctx.fillText(data.subject || '', 125 * scale, 287 * scale);

    // 3. STRIKETHROUGH TOGGLE
    if (data.strikethroughEnabled) {
      ctx.lineWidth = 1.5 * scale;
      ctx.strokeStyle = color;
      ctx.beginPath();
      if (data.isAssignment) {
        // Strike through 'EXPERIMENT NO. /'
        ctx.moveTo(62.9 * scale, 327.9 * scale);
        ctx.lineTo(174.3 * scale, 327.9 * scale);
      } else {
        // Strike through '/ ASSIGNMENT NO.'
        ctx.moveTo(170.0 * scale, 327.9 * scale);
        ctx.lineTo(285.0 * scale, 327.9 * scale);
      }
      ctx.stroke();
    }

    // 4. EXPERIMENT NO. / ASSIGNMENT NO. (Just clean number/label)
    const rawExpNo = data.expNo || '';
    const cleanExpNo = rawExpNo.replace(/^(?:Exp|Experiment|Assign|Assgn|Assignment)[\s:_.\-]*/i, '').trim();
    ctx.fillText(cleanExpNo, 290 * scale, 330 * scale);

    // 5. TITLE WRAPPING
    const title = data.title || '';
    if (title) {
      this.drawWrappedTitle(ctx, title, scale, fontSize, color);
    }

    // 6. DATES
    if (data.perfDate) {
      ctx.fillText(data.perfDate, 220 * scale, 414 * scale);
    }
    if (data.subDate) {
      ctx.fillText(data.subDate, 205 * scale, 435 * scale);
    }

    ctx.restore();
  }

  private drawWrappedTitle(
    ctx: CanvasRenderingContext2D,
    title: string,
    scale: number,
    baseFontSize: number,
    color: string
  ): void {
    let currentFontSize = baseFontSize;
    const minFontSize = 8 * scale;
    const maxW1 = 435 * scale;
    const maxW2 = 475 * scale;

    while (currentFontSize >= minFontSize) {
      ctx.font = `${currentFontSize}px Helvetica, Arial, sans-serif`;
      const words = title.split(' ');
      const line1Words: string[] = [];
      let line2Words: string[] = [];
      let w1 = 0;

      for (let i = 0; i < words.length; i++) {
        const w = words[i];
        const ww = ctx.measureText(w + ' ').width;
        if (w1 + ww <= maxW1) {
          line1Words.push(w);
          w1 += ww;
        } else {
          line2Words = words.slice(i);
          break;
        }
      }

      const str1 = line1Words.join(' ');
      let str2 = line2Words.join(' ');
      const w2 = line2Words.length > 0 ? ctx.measureText(str2).width : 0;

      if (w2 <= maxW2 || currentFontSize <= minFontSize) {
        if (w2 > maxW2) {
          while (line2Words.length > 0 && ctx.measureText(line2Words.join(' ') + '...').width > maxW2) {
            line2Words.pop();
          }
          str2 = line2Words.join(' ') + '...';
        }

        ctx.fillStyle = color;
        ctx.fillText(str1, 106 * scale, 351 * scale);
        if (str2) {
          ctx.fillText(str2, 63 * scale, 372 * scale);
        }
        return;
      }

      currentFontSize -= 0.5 * scale;
    }
  }

  cleanup(): void {
    if (this.activeRenderTask) {
      this.activeRenderTask.cancel();
      this.activeRenderTask = null;
    }
    if (this.cachedTemplateDoc) {
      this.cachedTemplateDoc.destroy();
      this.cachedTemplateDoc = null;
    }
  }
}
