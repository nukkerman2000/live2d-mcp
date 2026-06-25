/**
 * Parse HTML content and extract main content as Markdown
 *
 * Flow:
 * 1. HTML string → JSDOM (DOM creation)
 * 2. JSDOM → Readability (main content extraction, noise removal)
 * 3. Readability result → Turndown (Markdown conversion)
 * 4. Title extracted separately via extractHtmlTitle (NOT prepended to content)
 *
 * @param html - Raw HTML string
 * @param url - Source URL (used for resolving relative links)
 * @returns Object with content (markdown) and title (extracted separately)
 */
export declare function parseHtml(html: string, url: string): Promise<{
    content: string;
    title: string;
}>;
//# sourceMappingURL=html-parser.d.ts.map