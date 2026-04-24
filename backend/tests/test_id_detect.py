from __future__ import annotations

import pytest

from deerflow.community.academic_search.id_detect import detect_paper_id_source


class TestDetectPaperIdSource:
    def test_doi_with_prefix(self):
        assert detect_paper_id_source("10.1038/nature12373") == "doi"

    def test_doi_with_url(self):
        assert detect_paper_id_source("https://doi.org/10.1145/1234567") == "doi"

    def test_arxiv_new_format(self):
        assert detect_paper_id_source("2401.12345") == "arxiv"

    def test_arxiv_new_format_with_version(self):
        assert detect_paper_id_source("2401.12345v2") == "arxiv"

    def test_arxiv_old_format(self):
        assert detect_paper_id_source("hep-th/9901001") == "arxiv"

    def test_arxiv_with_prefix(self):
        assert detect_paper_id_source("arxiv:2401.12345") == "arxiv"

    def test_s2_hex_id(self):
        assert detect_paper_id_source("a" * 40) == "s2"

    def test_openalex_id(self):
        assert detect_paper_id_source("W2741809807") == "openalex"

    def test_unknown_defaults(self):
        assert detect_paper_id_source("some-random-string") == "unknown"

    def test_whitespace_stripped(self):
        assert detect_paper_id_source("  10.1038/nature12373  ") == "doi"
