#!/usr/bin/env python3
"""Render the static Art Space Rodeo listings site (public/index.html) from data/*.json.

No Node, no Astro: stdlib only. Run `python3 build.py` after the scrapers refresh
data/, then deploy the public/ directory to GitHub Pages.
"""
import json
import os
import re
from datetime import date, datetime
from html import escape

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "public")

DATE_PREFIX_RE = re.compile(
    r"^(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d"
)


def fmt_date(iso):
    if not iso:
        return ""
    d = datetime.strptime(iso, "%Y-%m-%d").date()
    return d.strftime("%b ") + str(d.day) + ", " + str(d.year)


def date_display(start, end):
    if start or end:
        return f"{fmt_date(start) or '?'} - {fmt_date(end) or '?'}"
    return "Dates TBD"


def render_card(ex, school):
    title = escape(ex["title"])
    img = escape(ex.get("image_url") or "/placeholder.svg")
    url = escape(ex["url"])
    state = escape(school["state"])
    gallery = escape(school["gallery_name"])
    name = escape(school["name"])
    show_school = school["name"] != school["gallery_name"]
    school_label = name if show_school else gallery

    desc = ex.get("description")
    if desc and DATE_PREFIX_RE.match(desc):
        desc = None

    parts = [
        f'<a class="exhibition-card" href="{url}" target="_blank" rel="noopener noreferrer">',
        '  <div class="card-image">',
        f'    <img src="{img}" alt="{title}" loading="lazy" />',
        "  </div>",
        '  <div class="card-body">',
        f'    <h3 class="card-title">{title}</h3>',
        '    <div class="card-meta">',
        f'      <span class="card-school">{school_label}'
        f' <span class="state-badge" data-state="{state}">{state}</span></span>',
    ]
    if show_school:
        parts.append(
            f'      <span style="color: var(--muted); font-size: 0.75rem;">{gallery}</span>'
        )
    parts.append(f'      <span class="card-dates">{date_display(ex.get("start_date"), ex.get("end_date"))}</span>')
    if desc:
        clamped = escape(desc[:150]) + ("..." if len(desc) > 150 else "")
        parts.append(
            f'      <p style="margin-top: 0.5rem; font-size: 0.8125rem; color: var(--muted);">{clamped}</p>'
        )
    parts += ["    </div>", "  </div>", "</a>"]
    return "\n".join("            " + p for p in parts)


def render_section(exhibitions, school_map, *, section_id, title, title_cls, label):
    states = sorted({school_map[ex["school_id"]]["state"]
                     for ex in exhibitions if school_map.get(ex["school_id"])})
    sources = len({ex["school_id"] for ex in exhibitions})

    if not exhibitions:
        return f"""  <section id="{section_id}-section">
    <h2 class="section-title {title_cls}">{title}</h2>
    <p class="empty-state">No {label} exhibitions currently listed.</p>
  </section>"""

    filters = [f'      <button class="filter-btn active" data-filter="all">All</button>']
    filters += [f'      <button class="filter-btn" data-filter="{s}">{s}</button>' for s in states]

    cards = []
    for ex in exhibitions:
        school = school_map.get(ex["school_id"])
        if not school:
            continue
        cards.append(
            f'          <div class="grid-item" data-state="{escape(school["state"])}"'
            f' data-school="{escape(school["id"])}">\n{render_card(ex, school)}\n          </div>'
        )

    return f"""  <section id="{section_id}-section">
    <h2 class="section-title {title_cls}">{title}</h2>
    <div class="filters" id="{section_id}-filters">
{chr(10).join(filters)}
    </div>
    <p class="stats" id="{section_id}-stats">
      {len(exhibitions)} exhibitions across {sources} {label}s
    </p>
    <div class="exhibition-grid" id="{section_id}-grid">
{chr(10).join(cards)}
    </div>
    <div class="empty-state" id="{section_id}-empty" style="display: none;">
      No {label} exhibitions found for this filter.
    </div>
  </section>"""


FILTER_SCRIPT = """  <script>
    function setupFilters(filtersId, gridId, statsId, emptyId, label) {
      const buttons = document.querySelectorAll(`#${filtersId} .filter-btn`);
      const grid = document.getElementById(gridId);
      const stats = document.getElementById(statsId);
      const empty = document.getElementById(emptyId);
      if (!grid || !stats || !empty) return;

      const cards = grid.querySelectorAll(":scope > div");

      buttons.forEach((btn) => {
        btn.addEventListener("click", () => {
          const filter = btn.dataset.filter;

          buttons.forEach((b) => b.classList.remove("active"));
          btn.classList.add("active");

          let visible = 0;
          cards.forEach((card) => {
            const show = filter === "all" || card.dataset.state === filter;
            card.style.display = show ? "" : "none";
            if (show) visible++;
          });

          const sourceCount = new Set(
            Array.from(cards)
              .filter((c) => filter === "all" || c.dataset.state === filter)
              .map((c) => c.dataset.school)
          ).size;

          stats.textContent = `${visible} exhibition${visible !== 1 ? "s" : ""} across ${sourceCount} ${label}${sourceCount !== 1 ? "s" : ""}`;
          empty.style.display = visible === 0 ? "" : "none";
          grid.style.display = visible === 0 ? "none" : "";
        });
      });
    }

    setupFilters("museum-filters", "museum-grid", "museum-stats", "museum-empty", "museum");
    setupFilters("college-filters", "college-grid", "college-stats", "college-empty", "gallery");
  </script>"""


def main():
    exhibitions = json.load(open(os.path.join(DATA, "exhibitions.json"), encoding="utf-8"))
    schools = json.load(open(os.path.join(DATA, "schools.json"), encoding="utf-8"))
    school_map = {s["id"]: s for s in schools}

    def sort_key(ex):
        # dated exhibitions first (by end date asc), undated last
        return (ex["end_date"] is None, ex["end_date"] or "")

    ordered = sorted(exhibitions, key=sort_key)
    museums = [e for e in ordered if school_map.get(e["school_id"], {}).get("type") == "museum"]
    colleges = [e for e in ordered if school_map.get(e["school_id"], {}).get("type") == "college"]

    body = "\n\n".join([
        render_section(museums, school_map, section_id="museum",
                       title="Museum Exhibitions", title_cls="", label="museum"),
        '  <hr class="section-divider" />',
        render_section(colleges, school_map, section_id="college",
                       title="College &amp; University Galleries",
                       title_cls="section-title-secondary", label="gallery"),
    ])

    updated = date.today().strftime("%B ") + str(date.today().day) + ", " + str(date.today().year)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="description" content="Art Space Rodeo &mdash; current exhibitions at museums and college galleries across New England" />
  <title>Art Space Rodeo</title>
  <link rel="stylesheet" href="/style.css" />
</head>
<body>
  <div class="container">
    <header>
      <h1>Art Space Rodeo</h1>
      <p>Museums and college galleries across New England</p>
      <nav class="site-nav">
        <a href="/" aria-current="page">Exhibitions</a>
        <a href="https://janetknott.com" target="_blank" rel="noopener noreferrer">Photo Essays by Janet Knott &#8599;</a>
      </nav>
    </header>
    <main>
{body}
    </main>
    <footer>
      <p>Data last updated: {updated}</p>
    </footer>
  </div>
{FILTER_SCRIPT}
</body>
</html>
"""

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote {os.path.join(OUT, 'index.html')} "
          f"({len(museums)} museum + {len(colleges)} college exhibitions)")


if __name__ == "__main__":
    main()
