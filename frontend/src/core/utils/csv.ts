/**
 * Minimal zero-dependency RFC 4180 CSV parser.
 *
 * Handles:
 * - Quoted fields containing commas: "a, b"
 * - Escaped double quotes inside quoted fields: "she said ""hi"""
 * - Line endings: \n, \r\n, \r
 * - UTF-8 BOM at the start of the file
 * - Files without a trailing newline
 * - Empty input (returns [])
 *
 * Returns a 2D array of strings. Does NOT infer types — every cell is a string.
 */
export function parseCsv(input: string): string[][] {
  if (!input) return [];

  // Strip UTF-8 BOM if present.
  let text = input;
  if (text.charCodeAt(0) === 0xfeff) {
    text = text.slice(1);
  }

  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let inQuotes = false;

  for (let i = 0; i < text.length; i++) {
    const c = text[i];

    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') {
          // Escaped double quote.
          field += '"';
          i++;
        } else {
          inQuotes = false;
        }
      } else {
        field += c;
      }
      continue;
    }

    if (c === '"') {
      inQuotes = true;
    } else if (c === ",") {
      row.push(field);
      field = "";
    } else if (c === "\n" || c === "\r") {
      // Consume \r\n as a single line break.
      if (c === "\r" && text[i + 1] === "\n") i++;
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
    } else {
      field += c;
    }
  }

  // Flush the final field/row if the file doesn't end with a newline.
  if (field.length > 0 || row.length > 0) {
    row.push(field);
    rows.push(row);
  }

  return rows;
}
