from __future__ import annotations

from deerflow.community.academic_search.bibtex import (
    determine_entry_type,
    escape_latex,
    format_authors_bibtex,
    generate_bibtex,
    generate_bibtex_batch,
    generate_bibtex_key,
)


class TestEscapeLatex:
    def test_special_chars(self):
        assert escape_latex("10% & $5") == "10\\% \\& \\$5"

    def test_accented_chars(self):
        assert escape_latex("ä") == '{\\"a}'
        assert escape_latex("é") == "{\\'e}"
        assert escape_latex("ñ") == "{\\~n}"

    def test_empty_string(self):
        assert escape_latex("") == ""

    def test_plain_text(self):
        assert escape_latex("hello world") == "hello world"


class TestGenerateBibtexKey:
    def test_standard_paper(self):
        paper = {"authors": ["John Smith"], "year": 2024, "title": "Neural Networks for NLP"}
        assert generate_bibtex_key(paper) == "Smith2024Neural"

    def test_no_authors(self):
        paper = {"authors": [], "year": 2024, "title": "Some Title"}
        assert generate_bibtex_key(paper) == "Unknown2024Some"

    def test_skip_stop_words(self):
        paper = {"authors": ["Alice Bob"], "year": 2023, "title": "The Art of Programming"}
        assert generate_bibtex_key(paper) == "Bob2023Art"

    def test_comma_separated_author(self):
        paper = {"authors": ["Smith, John"], "year": 2024, "title": "Test Paper"}
        assert generate_bibtex_key(paper) == "Smith2024Test"

    def test_no_year(self):
        paper = {"authors": ["Smith"], "title": "Test"}
        assert generate_bibtex_key(paper) == "SmithTest"


class TestFormatAuthorsBibtex:
    def test_single_author(self):
        assert format_authors_bibtex(["John Smith"]) == "Smith, John"

    def test_multiple_authors(self):
        result = format_authors_bibtex(["John Smith", "Jane Doe"])
        assert result == "Smith, John and Doe, Jane"

    def test_already_formatted(self):
        result = format_authors_bibtex(["Smith, John"])
        assert result == "Smith, John"

    def test_empty(self):
        assert format_authors_bibtex([]) == ""

    def test_single_name(self):
        assert format_authors_bibtex(["Madonna"]) == "Madonna"


class TestDetermineEntryType:
    def test_conference_paper(self):
        assert determine_entry_type({"venue": "NeurIPS 2024"}) == "inproceedings"
        assert determine_entry_type({"venue": "Proceedings of ICML"}) == "inproceedings"

    def test_journal_article(self):
        assert determine_entry_type({"venue": "Nature"}) == "article"
        assert determine_entry_type({"venue": "IEEE Transactions on AI"}) == "article"

    def test_arxiv_preprint(self):
        assert determine_entry_type({"venue": "arXiv", "externalIds": {"ArXiv": "2401.12345"}}) == "misc"

    def test_with_volume_and_pages(self):
        assert determine_entry_type({"venue": "Some Venue", "volume": "42", "pages": "1--10"}) == "article"

    def test_default_misc(self):
        assert determine_entry_type({"venue": ""}) == "misc"
        assert determine_entry_type({}) == "misc"


class TestGenerateBibtex:
    def test_full_entry(self):
        paper = {
            "authors": ["John Smith", "Jane Doe"],
            "title": "A Great Paper",
            "venue": "NeurIPS 2024",
            "year": 2024,
            "externalIds": {"DOI": "10.1234/test"},
        }
        bib = generate_bibtex(paper)
        assert "@inproceedings{Smith2024Great," in bib
        assert "author = {Smith, John and Doe, Jane}" in bib
        assert "title = {A Great Paper}" in bib
        assert "booktitle = {NeurIPS 2024}" in bib
        assert "year = {2024}" in bib
        assert "doi = {10.1234/test}" in bib

    def test_custom_key(self):
        paper = {"authors": ["Smith"], "title": "Test", "year": 2024}
        bib = generate_bibtex(paper, custom_key="mykey2024")
        assert "@misc{mykey2024," in bib

    def test_journal_article(self):
        paper = {"authors": ["Smith"], "title": "Test", "venue": "Nature", "year": 2024}
        bib = generate_bibtex(paper)
        assert "journal = {Nature}" in bib

    def test_no_trailing_comma(self):
        paper = {"authors": ["Smith"], "title": "Test", "year": 2024}
        bib = generate_bibtex(paper)
        lines = bib.strip().split("\n")
        last_field_line = lines[-2]
        assert not last_field_line.rstrip().endswith(",")

    def test_url_prefers_canonical_citation_url(self):
        paper = {
            "authors": ["Smith"],
            "title": "Test",
            "year": 2024,
            "citationUrl": "https://doi.org/10.1234/test",
            "openAccessPdfUrl": "https://example.com/paper.pdf",
        }
        bib = generate_bibtex(paper)

        assert "url = {https://doi.org/10.1234/test}" in bib
        assert "https://example.com/paper.pdf" not in bib


class TestGenerateBibtexBatch:
    def test_batch_unique_keys(self):
        papers = [
            {"authors": ["Smith"], "title": "Paper One", "year": 2024},
            {"authors": ["Smith"], "title": "Paper One Again", "year": 2024},
        ]
        batch = generate_bibtex_batch(papers)
        entries = batch.split("\n\n")
        assert len(entries) == 2
        keys = []
        for entry in entries:
            key = entry.split("{")[1].split(",")[0]
            keys.append(key)
        assert len(set(keys)) == 2

    def test_empty_batch(self):
        assert generate_bibtex_batch([]) == ""
