import os
from pathlib import Path
from dotenv import load_dotenv
from firecrawl import FirecrawlApp

load_dotenv()

OUTPUT_DIR = Path("knowledge/raw")

SEED = [
    # gapinc.com — quarterly earnings press releases
    {"slug": "gapinc-q1-2024-earnings",      "url": "https://www.gapinc.com/en-us/articles/2024/05/gap-inc-reports-first-quarter-fiscal-2024-results"},
    {"slug": "gapinc-q2-2024-earnings",      "url": "https://www.gapinc.com/en-us/articles/2024/08/gap-inc-reports-second-quarter-fiscal-2024-results"},
    {"slug": "gapinc-q3-2024-earnings",      "url": "https://www.gapinc.com/en-us/articles/2024/11/gap-inc-reports-third-quarter-fiscal-2024-results"},
    {"slug": "gapinc-q4-2024-earnings",      "url": "https://www.gapinc.com/en-us/articles/2025/03/gap-inc-reports-fourth-quarter-and-fiscal-2024-res"},
    # gapinc.com — media & marketing
    {"slug": "gapinc-media-marketing-2024",  "url": "https://www.gapinc.com/en-us/articles/2024/05/evolving-media-marketing-at-gap-inc"},
    # gapinc.com — annual report (PDF — Firecrawl handles PDFs)
    {"slug": "gapinc-fy2024-annual-report",  "url": "https://s204.q4cdn.com/320226404/files/doc_financials/2024/ar/FY-2024-ARS-Revised-4-4-25.pdf"},
    # Retail Dive
    {"slug": "retaildive-q2-turnaround",     "url": "https://www.retaildive.com/news/gap-inc-second-quarter-turnaround-momentum-troye-sivan-loose-fit-denim/725653/"},
    {"slug": "retaildive-q4-comeback",       "url": "https://www.retaildive.com/news/old-navy-gap-lead-comeback-athleta-sales-down-q4/741856/"},
    {"slug": "retaildive-recovery-dickson",  "url": "https://www.retaildive.com/news/gap-old-navy-earnings-sales-progress-recovery-richard-dickson/709698/"},
    # Wikipedia — brand pages
    {"slug": "wiki-gap-inc",                 "url": "https://en.wikipedia.org/wiki/Gap_Inc."},
    {"slug": "wiki-old-navy",                "url": "https://en.wikipedia.org/wiki/Old_Navy"},
    {"slug": "wiki-banana-republic",         "url": "https://en.wikipedia.org/wiki/Banana_Republic_(clothing_retailer)"},
    {"slug": "wiki-athleta",                 "url": "https://en.wikipedia.org/wiki/Athleta_(clothing)"},
    # Placer.ai — foot traffic / brand analysis
    {"slug": "placerai-gap-2025-recap",      "url": "https://www.placer.ai/anchor/articles/gap-inc-in-2025-recapping-2024-and-uncovering-banana-republics-athleisure-opportunity"},
    # Sheng Lu Fashion — sourcing analysis
    {"slug": "shenglufashion-sourcing-2024", "url": "https://shenglufashion.com/2025/03/06/gap-inc-s-evolving-apparel-sourcing-base-2021-2024/"},
]


def main(seed: list[dict] | None = None, output_dir: Path | None = None) -> None:
    if seed is None:
        seed = SEED
    if output_dir is None:
        output_dir = OUTPUT_DIR

    app = FirecrawlApp(api_key=os.environ["FIRECRAWL_API_KEY"])
    output_dir.mkdir(parents=True, exist_ok=True)

    for item in seed:
        slug, url = item["slug"], item["url"]
        if url == "TODO":
            print(f"[SKIP] {slug} — URL not set")
            continue
        try:
            result = app.scrape_url(url, params={"formats": ["markdown"]})
            content = result.get("markdown", "")
            (output_dir / f"{slug}.md").write_text(content, encoding="utf-8")
            print(f"[OK]   {slug}")
        except Exception as exc:
            print(f"[WARN] {slug} failed: {exc}")


if __name__ == "__main__":
    main()
