---
name: PDF Table Extractor
description: Extract tables from PDF files into structured rows and export as CSV.
---

# PDF Table Extractor

Use this skill to turn tables trapped in a PDF into clean, structured rows.

## Steps

1. **Classify the PDF**: is the text selectable (digital) or is it a scan (image)?
   `pdftotext -layout file.pdf -` quickly shows whether text is extractable.
2. **Digital PDFs**: use a table-aware extractor (e.g. `camelot`/`tabula` for ruled
   tables, `pdfplumber` for finer control). Prefer "lattice" mode when the table has
   visible gridlines, "stream" mode when it's whitespace-separated.
3. **Scanned PDFs**: rasterize pages and OCR them (e.g. Tesseract) before table
   detection; expect to clean up misread digits and merged cells.
4. **Normalize**: strip header/footer rows, fix merged/spanning cells, coerce numeric
   columns, and ensure a consistent column count per row.
5. **Export**: write UTF-8 CSV with a header row; quote fields containing commas or
   newlines.

## Tips

- Validate row/column counts against a sample page before bulk-processing.
- Keep the page number as a column so extracted rows stay traceable to the source.
