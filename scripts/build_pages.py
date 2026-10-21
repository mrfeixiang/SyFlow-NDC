#!/usr/bin/env python3
"""Build the GitHub Pages site from README.md into ./site.

The page is a static rendering of the repository README, with figures copied
beside it. Run from anywhere:

    python scripts/build_pages.py
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import markdown

REPO_ROOT = Path(__file__).resolve().parent.parent
SITE_DIR = REPO_ROOT / "site"
REPO_WEB = "https://github.com/mrfeixiang/SyFlow-NDC"
PAGES_URL = "https://mrfeixiang.github.io/SyFlow-NDC/"
REPO_FILES = {
    "LICENSE",
    "CITATION.cff",
    "environment.yml",
    "pyproject.toml",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
}


def _source_ref() -> str:
    if os.environ.get("GITHUB_REF_NAME"):
        return os.environ["GITHUB_REF_NAME"]
    try:
        ref = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=REPO_ROOT,
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "main"
    if not ref or ref == "HEAD":
        return "main"
    return ref


def _render_readme(source_ref: str) -> str:
    text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    body = markdown.markdown(
        text,
        extensions=["tables", "fenced_code", "sane_lists", "toc"],
    )
    body = re.sub(
        r'<pre><code class="language-mermaid">(.*?)</code></pre>',
        r'<pre class="mermaid">\1</pre>',
        body,
        flags=re.S,
    )
    blob = f"{REPO_WEB}/blob/{source_ref}"
    for name in REPO_FILES:
        body = body.replace(f'href="{name}"', f'href="{blob}/{name}"')
    body = re.sub(r"^<h1[^>]*>.*?</h1>\s*", "", body, count=1, flags=re.S)
    return body


def _page(body: str, source_ref: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>SyFlow NDC Go/No-Go Platform</title>
  <meta name="description" content="Provenance-first Go/Hold/No-Go decisions for nanobody-drug conjugate dossiers."/>
  <link rel="canonical" href="{PAGES_URL}"/>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
  <link href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,500;6..72,650&family=Source+Sans+3:wght@400;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet"/>
  <style>
    :root {{
      --ink: #1c1915;
      --muted: #5c564c;
      --paper: #f6f1e7;
      --card: #fffdf8;
      --line: #e2d8c8;
      --teal: #0f3d3e;
      --teal-2: #1d6a62;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font-family: "Source Sans 3", "Segoe UI", sans-serif;
      font-size: 1.05rem;
      line-height: 1.6;
    }}
    header {{
      background: var(--teal);
      color: #f6f1e7;
      padding: 2.5rem 1.25rem 2rem;
    }}
    header .wrap, main {{
      max-width: 880px;
      margin: 0 auto;
    }}
    .kicker {{
      letter-spacing: 0.14em;
      text-transform: uppercase;
      font-size: 0.78rem;
      color: #c9e4df;
      margin: 0 0 0.6rem;
    }}
    h1 {{
      font-family: Newsreader, Georgia, serif;
      font-weight: 650;
      font-size: clamp(2rem, 4vw, 3.1rem);
      line-height: 1.15;
      margin: 0 0 0.75rem;
    }}
    .pitch {{ margin: 0; max-width: 40rem; color: #efe6d6; }}
    header a {{ color: #f3d7a1; }}
    main {{ padding: 1.5rem 1.25rem 3rem; }}
    article {{
      background: var(--card);
      border: 1px solid var(--line);
      padding: 0.5rem 1.4rem 2rem;
    }}
    h2 {{
      font-family: Newsreader, Georgia, serif;
      font-weight: 650;
      font-size: 1.7rem;
      margin-top: 2rem;
      padding-top: 0.4rem;
      border-top: 1px solid var(--line);
    }}
    h3 {{ font-family: Newsreader, Georgia, serif; }}
    a {{ color: var(--teal-2); }}
    code, pre {{ font-family: "IBM Plex Mono", ui-monospace, monospace; }}
    code {{
      background: #f3ecdf;
      padding: 0.1em 0.35em;
      border-radius: 4px;
      font-size: 0.88em;
    }}
    pre {{
      background: #14222e;
      color: #f6f1e7;
      padding: 1rem 1.1rem;
      overflow-x: auto;
      border-radius: 8px;
    }}
    pre code {{ background: transparent; color: inherit; padding: 0; }}
    pre.mermaid {{
      background: var(--card);
      color: var(--ink);
      border: 1px solid var(--line);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.95rem;
      display: block;
      overflow-x: auto;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      text-align: left;
      padding: 0.45rem 0.6rem;
      vertical-align: top;
    }}
    th {{ color: var(--teal); }}
    img {{ max-width: 100%; height: auto; border-radius: 8px; }}
    footer {{
      max-width: 880px;
      margin: 0 auto;
      padding: 0 1.25rem 2.5rem;
      color: var(--muted);
      font-size: 0.92rem;
    }}
  </style>
</head>
<body>
  <header>
    <div class="wrap">
      <p class="kicker">SyFlow · Nanobody-drug conjugates</p>
      <h1>SyFlow NDC Go/No-Go Platform</h1>
      <p class="pitch">Provenance-first Go/Hold/No-Go decisions for one nanobody-drug conjugate dossier at a time.</p>
    </div>
  </header>
  <main>
    <article class="markdown-body">
{body}
    </article>
  </main>
  <footer>
    <p>Built from <a href="{REPO_WEB}/blob/{source_ref}/README.md">README.md</a>
    on <code>{source_ref}</code>.
    Source: <a href="{REPO_WEB}">{REPO_WEB}</a>.</p>
  </footer>
  <script type="module">
    import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
    mermaid.initialize({{ startOnLoad: true, theme: "neutral", securityLevel: "loose" }});
  </script>
</body>
</html>
"""


def build() -> Path:
    source_ref = _source_ref()
    if SITE_DIR.exists():
        shutil.rmtree(SITE_DIR)
    SITE_DIR.mkdir(parents=True)
    figures = REPO_ROOT / "figures"
    if figures.is_dir():
        shutil.copytree(figures, SITE_DIR / "figures")
    (SITE_DIR / "index.html").write_text(_page(_render_readme(source_ref), source_ref), encoding="utf-8")
    (SITE_DIR / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Wrote {SITE_DIR / 'index.html'} from ref {source_ref}")
    return SITE_DIR


if __name__ == "__main__":
    build()
