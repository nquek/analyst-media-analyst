from pathlib import Path
from unittest.mock import MagicMock, patch
import ingestion.scrape_to_knowledge as scraper_module

TEST_SEED = [
    {"slug": "test-article", "url": "https://example.com/article"},
]


def test_scrape_writes_md_file(tmp_path, monkeypatch):
    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")
    mock_app = MagicMock()
    mock_app.scrape_url.return_value = {"markdown": "# Test\nSome content."}

    with patch("ingestion.scrape_to_knowledge.FirecrawlApp", return_value=mock_app):
        scraper_module.main(seed=TEST_SEED, output_dir=tmp_path)

    out = tmp_path / "test-article.md"
    assert out.exists()
    assert "Test" in out.read_text()


def test_scrape_skips_todo_urls(tmp_path, monkeypatch):
    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")
    seed = [{"slug": "pending", "url": "TODO"}]
    mock_app = MagicMock()

    with patch("ingestion.scrape_to_knowledge.FirecrawlApp", return_value=mock_app):
        scraper_module.main(seed=seed, output_dir=tmp_path)

    mock_app.scrape_url.assert_not_called()
    assert not (tmp_path / "pending.md").exists()


def test_scrape_skips_failed_url_without_raising(tmp_path, monkeypatch):
    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")
    seed = [{"slug": "bad", "url": "https://example.com/bad"}]
    mock_app = MagicMock()
    mock_app.scrape_url.side_effect = Exception("Firecrawl error")

    with patch("ingestion.scrape_to_knowledge.FirecrawlApp", return_value=mock_app):
        scraper_module.main(seed=seed, output_dir=tmp_path)  # must not raise

    assert not (tmp_path / "bad.md").exists()


def test_scrape_creates_output_dir_if_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")
    new_dir = tmp_path / "nested" / "dir"
    seed = [{"slug": "article", "url": "https://example.com/article"}]
    mock_app = MagicMock()
    mock_app.scrape_url.return_value = {"markdown": "content"}

    with patch("ingestion.scrape_to_knowledge.FirecrawlApp", return_value=mock_app):
        scraper_module.main(seed=seed, output_dir=new_dir)

    assert (new_dir / "article.md").exists()
