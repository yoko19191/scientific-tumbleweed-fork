import assert from "node:assert/strict";
import test from "node:test";

const {
  buildCitationNumbering,
  buildCitationRegistry,
  extractFetchedCitation,
  getCanonicalCitationUrl,
  getCitationDisplayTitle,
  getCitationLabelFromNode,
  getToolCardCitationHref,
  lookupCitationMetadata,
  normalizeCitationUrl,
  parseMarkdownLinks,
  stripCitationPrefix,
} = await import(new URL("./citations.ts", import.meta.url).href);

void test("detects citation labels from strings and text node arrays", () => {
  assert.equal(
    stripCitationPrefix("citation:O'Donnell et al., 2013"),
    "O'Donnell et al., 2013",
  );
  assert.equal(
    getCitationLabelFromNode(["citation:", "Bell & Labib, 2016"]),
    "Bell & Labib, 2016",
  );
  assert.equal(getCitationLabelFromNode("plain link"), null);
});

void test("uses canonical citationUrl and ignores non-URL fallbacks", () => {
  assert.equal(
    getCanonicalCitationUrl({
      citationUrl: "https://openalex.org/W123",
      title: "Paper",
    }),
    "https://openalex.org/W123",
  );
  assert.equal(getCanonicalCitationUrl({ title: "Paper" }), null);
  assert.equal(getCanonicalCitationUrl({ citationUrl: "W123" }), null);
});

void test("prefers citationTitle over title", () => {
  assert.equal(
    getCitationDisplayTitle({
      citationTitle: "Canonical title",
      title: "Fallback title",
    }),
    "Canonical title",
  );
});

void test("tool cards use citationUrl instead of manufacturing academic links", () => {
  assert.equal(
    getToolCardCitationHref({
      paperId: "W123456",
      citationUrl: "https://openalex.org/W123456",
      title: "OpenAlex work",
    }),
    "https://openalex.org/W123456",
  );
  assert.equal(
    getToolCardCitationHref({
      paperId: "W123456",
      title: "OpenAlex work without canonical URL",
    }),
    null,
  );
});

void test("web search cards require canonical citationUrl", () => {
  assert.equal(
    getToolCardCitationHref({
      url: "https://example.com/old-field",
      title: "Old field only",
    }),
    null,
  );
  assert.equal(
    getToolCardCitationHref({
      url: "https://example.com/old-field",
      citationUrl: "https://example.com/canonical",
      title: "Canonical",
    }),
    "https://example.com/canonical",
  );
});

void test("extracts citation provenance from web_fetch markdown", () => {
  const parsed = extractFetchedCitation(`# Example

citationUrl: https://example.com/source
citationTitle: Example Source
citationProvider: jina
fetchedAt: 2026-06-04T00:00:00Z

Body`);

  assert.equal(parsed.citationUrl, "https://example.com/source");
  assert.equal(parsed.citationTitle, "Example Source");
});

void test("normalizeCitationUrl trims and drops trailing slash", () => {
  assert.equal(
    normalizeCitationUrl("  https://doi.org/10.1/x/  "),
    "https://doi.org/10.1/x",
  );
  assert.equal(normalizeCitationUrl(undefined), "");
});

void test("buildCitationRegistry indexes academic results by every url alias", () => {
  const registry = buildCitationRegistry([
    {
      type: "tool",
      name: "academic_search_papers",
      content: JSON.stringify({
        results: [
          {
            paperId: "W123",
            citationUrl: "https://doi.org/10.1073/pnas.2211947120",
            doiUrl: "https://doi.org/10.1073/pnas.2211947120",
            providerUrl: "https://openalex.org/W123",
            citationTitle: "A conserved mechanism",
            title: "A conserved mechanism",
            authors: ["Smith", "Lee"],
            year: 2021,
            venue: "Nature",
            citationCount: 550,
            citationProvider: "openalex",
            citationType: "academic_paper",
          },
        ],
      }),
    },
  ]);

  const byDoi = lookupCitationMetadata(
    registry,
    "https://doi.org/10.1073/pnas.2211947120",
  );
  assert.equal(byDoi?.citationCount, 550);
  assert.equal(byDoi?.venue, "Nature");
  // Provider URL alias resolves to the same metadata record.
  const byProvider = lookupCitationMetadata(registry, "https://openalex.org/W123/");
  assert.equal(byProvider?.title, "A conserved mechanism");
  assert.deepEqual(byProvider?.authors, ["Smith", "Lee"]);
});

void test("buildCitationRegistry reads web_fetch provenance headers", () => {
  const registry = buildCitationRegistry([
    {
      type: "tool",
      name: "web_fetch",
      content: `# Example\n\ncitationUrl: https://example.com/source\ncitationTitle: Example Source\ncitationProvider: jina\n\nBody`,
    },
  ]);
  const meta = lookupCitationMetadata(registry, "https://example.com/source");
  assert.equal(meta?.title, "Example Source");
  assert.equal(meta?.provider, "jina");
});

void test("parseMarkdownLinks keeps external links and skips images", () => {
  const links = parseMarkdownLinks(
    "See [citation:Smith 2021](https://doi.org/10.1/x) and ![img](https://e.com/p.png) and [rel](./local).",
  );
  assert.equal(links.length, 1);
  assert.equal(links[0].href, "https://doi.org/10.1/x");
  assert.equal(links[0].isCitationPrefixed, true);
});

void test("buildCitationNumbering numbers citations in order, de-duplicating", () => {
  const registry = buildCitationRegistry([
    {
      type: "tool",
      name: "web_search",
      content: JSON.stringify({
        results: [{ citationUrl: "https://b.com", title: "B" }],
      }),
    },
  ]);
  const content =
    "First [citation:A](https://a.com/) then [B](https://b.com) then [A again](https://a.com) and [not a cite](https://x.com).";
  const numbering = buildCitationNumbering(content, registry);
  // citation-prefixed A => 1, registry-known B => 2, x.com is neither => skipped.
  assert.equal(numbering.entries.length, 2);
  assert.equal(numbering.byHref.get("https://a.com"), 1);
  assert.equal(numbering.byHref.get("https://b.com"), 2);
  assert.equal(numbering.entries[1].metadata?.title, "B");
});
