#!/usr/bin/env python3
"""Build the GitHub Pages site from the READMEs into ./site.

Writes index.html (English), ko/index.html, and zh/index.html. Figures stay
in site/figures/ and are referenced relatively from each page.

    python scripts/build_pages.py
"""
from __future__ import annotations

import html
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
_SWITCHER_RE = re.compile(
    r"^(?:\[English\]\([^)]+\)|English)"
    r" \| (?:\[한국어\]\([^)]+\)|한국어)"
    r" \| (?:\[简体中文\]\([^)]+\)|简体中文)\s*\n+",
)

LOCALES = (
    {
        "id": "en",
        "lang": "en",
        "label": "English",
        "readme": "README.md",
        "dir": "",
        "pitch": (
            "Provenance-first Go/Hold/No-Go decisions for one "
            "nanobody-drug conjugate dossier at a time."
        ),
        "description": "Provenance-first Go/Hold/No-Go decisions for nanobody-drug conjugate dossiers.",
        "kicker": "SyFlow · Nanobody-drug conjugates",
        "switch_label": "Language",
        "footer": "Built from",
    },
    {
        "id": "ko",
        "lang": "ko",
        "label": "한국어",
        "readme": "README.ko.md",
        "dir": "ko",
        "pitch": "나노바디-약물 접합체 도씨에 한 건씩, 출처를 남기는 Go/Hold/No-Go 결정을 내립니다.",
        "description": "나노바디-약물 접합체 도씨에를 위한 출처 우선 Go/Hold/No-Go 결정.",
        "kicker": "SyFlow · 나노바디-약물 접합체",
        "switch_label": "언어",
        "footer": "다음 파일에서 생성",
    },
    {
        "id": "zh",
        "lang": "zh-CN",
        "label": "简体中文",
        "readme": "README.zh-CN.md",
        "dir": "zh",
        "pitch": "一次只对一份纳米抗体-药物偶联物档案做出可追溯的 Go/Hold/No-Go 决定。",
        "description": "面向纳米抗体-药物偶联物档案的可追溯 Go/Hold/No-Go 决定。",
        "kicker": "SyFlow · 纳米抗体-药物偶联物",
        "switch_label": "语言",
        "footer": "生成自",
    },
)


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


def _href(current_id: str, target_id: str) -> str:
    """Relative link from one locale page to another."""
    target = next(item for item in LOCALES if item["id"] == target_id)
    if current_id == "en":
        return "./" if target_id == "en" else f"{target['dir']}/"
    if target_id == "en":
        return "../"
    return f"../{target['dir']}/"


def _absolute(locale_id: str) -> str:
    locale = next(item for item in LOCALES if item["id"] == locale_id)
    if not locale["dir"]:
        return PAGES_URL
    return f"{PAGES_URL}{locale['dir']}/"


def _switcher(current_id: str) -> str:
    locale = next(item for item in LOCALES if item["id"] == current_id)
    parts = []
    for item in LOCALES:
        label = html.escape(item["label"])
        if item["id"] == current_id:
            parts.append(
                f'<span aria-current="page" lang="{item["lang"]}">{label}</span>'
            )
            continue
        href = html.escape(_href(current_id, item["id"]))
        parts.append(
            f'<a href="{href}" hreflang="{item["lang"]}" lang="{item["lang"]}">{label}</a>'
        )
    label = html.escape(locale["switch_label"])
    return f'<nav class="langs" aria-label="{label}">{" | ".join(parts)}</nav>'


def _hreflang_links() -> str:
    lines = []
    for item in LOCALES:
        lines.append(
            f'  <link rel="alternate" hreflang="{item["lang"]}" href="{_absolute(item["id"])}"/>'
        )
    lines.append(f'  <link rel="alternate" hreflang="x-default" href="{PAGES_URL}"/>')
    return "\n".join(lines)


def _render_readme(locale: dict, source_ref: str) -> str:
    text = (REPO_ROOT / locale["readme"]).read_text(encoding="utf-8")
    text = _SWITCHER_RE.sub("", text, count=1)
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
    pitch = re.escape(locale["pitch"])
    body = re.sub(rf"^<p>{pitch}</p>\s*", "", body, count=1)
    if locale["dir"]:
        body = body.replace('src="figures/', 'src="../figures/')
    return body


def _page(locale: dict, body: str, source_ref: str) -> str:
    readme_href = f"{REPO_WEB}/blob/{source_ref}/{locale['readme']}"
    return f"""<!DOCTYPE html>
<html lang="{locale["lang"]}">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>SyFlow NDC Go/No-Go Platform</title>
  <meta name="description" content="{html.escape(locale["description"])}"/>
  <link rel="canonical" href="{_absolute(locale["id"])}"/>
{_hreflang_links()}
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Newsreader:opsz,wght@6..72,500;6..72,650&family=Noto+Sans+KR:wght@400;600&family=Noto+Sans+SC:wght@400;600&family=Source+Sans+3:wght@400;600&display=swap" rel="stylesheet"/>
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
      font-family: "Source Sans 3", "Noto Sans KR", "Noto Sans SC", "Segoe UI", sans-serif;
      font-size: 1.05rem;
      line-height: 1.6;
    }}
    header {{
      background: var(--teal);
      color: #f6f1e7;
      padding: 1.4rem 1.25rem 2rem;
    }}
    header .wrap, main {{
      max-width: 880px;
      margin: 0 auto;
    }}
    .langs {{
      margin: 0 0 1.1rem;
      font-size: 0.95rem;
    }}
    .langs a {{ color: #f3d7a1; }}
    .langs [aria-current="page"] {{
      color: #fff;
      font-weight: 600;
      text-decoration: underline;
      text-underline-offset: 0.2em;
    }}
    .kicker {{
      letter-spacing: 0.14em;
      text-transform: uppercase;
      font-size: 0.78rem;
      color: #c9e4df;
      margin: 0 0 0.6rem;
    }}
    h1 {{
      font-family: Newsreader, "Noto Sans KR", "Noto Sans SC", Georgia, serif;
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
    h2, h3 {{
      font-family: Newsreader, "Noto Sans KR", "Noto Sans SC", Georgia, serif;
    }}
    h2 {{
      font-weight: 650;
      font-size: 1.7rem;
      margin-top: 2rem;
      padding-top: 0.4rem;
      border-top: 1px solid var(--line);
    }}
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
      {_switcher(locale["id"])}
      <p class="kicker">{html.escape(locale["kicker"])}</p>
      <h1>SyFlow NDC Go/No-Go Platform</h1>
      <p class="pitch">{html.escape(locale["pitch"])}</p>
    </div>
  </header>
  <main>
    <article>
{body}
    </article>
  </main>
  <footer>
    <p>{html.escape(locale["footer"])} <a href="{readme_href}">{html.escape(locale["readme"])}</a>
    · <code>{html.escape(source_ref)}</code>.
    <a href="{REPO_WEB}">{REPO_WEB}</a>.</p>
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
    (SITE_DIR / ".nojekyll").write_text("", encoding="utf-8")
    for locale in LOCALES:
        out_dir = SITE_DIR / locale["dir"] if locale["dir"] else SITE_DIR
        out_dir.mkdir(parents=True, exist_ok=True)
        page = _page(locale, _render_readme(locale, source_ref), source_ref)
        out = out_dir / "index.html"
        out.write_text(page, encoding="utf-8")
        print(f"Wrote {out} from {locale['readme']} ({source_ref})")
    return SITE_DIR


if __name__ == "__main__":
    build()
