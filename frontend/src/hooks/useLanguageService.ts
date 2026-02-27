import type { LanguageService } from '../services/LanguageService';

// Phase 1: no-op. pyright/dist/pyright.browser.js is not available in the
// installed package (Node-only bundles). Phase 2 will wire in a browser LSP.
const nullService: LanguageService = {
  getDiagnostics: async () => [],
};

export function useLanguageService(): LanguageService {
  return nullService;
}
