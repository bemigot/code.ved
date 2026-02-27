import type { editor } from 'monaco-editor';

/**
 * Abstraction over a language intelligence backend.
 * Phase 1: NullLanguageService (no-op — Monaco provides syntax highlighting).
 * Phase 2: swap in PyrightLanguageService when a browser LSP bundle is available.
 */
export interface LanguageService {
  getDiagnostics(model: editor.ITextModel): Promise<editor.IMarkerData[]>;
}
