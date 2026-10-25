# /// script
# requires-python = ">=3.10"
# dependencies = ["markdown>=3.5"]
# ///
"""把訪談官的 .md（規格書／工作單）轉成 Phase E 的 HTML 檢視版。

用法（uv 會自動準備 markdown 套件）：
  uv run ~/.claude/blacktea/md2html.py --kind requirements <in.md> <out.html> --project <專案名字>
  uv run ~/.claude/blacktea/md2html.py --kind workplan     <in.md> <out.html> --project <專案名字>
"""
import argparse
import html
import re

import markdown

KIND_DEFAULTS = {
    "requirements": ("規格書", ["分層技術棧表", "本版不做", "決策紀錄"]),
    "workplan": ("工作單", ["總表"]),
}

ap = argparse.ArgumentParser()
ap.add_argument("--kind", choices=KIND_DEFAULTS, required=True)
ap.add_argument("src")
ap.add_argument("out")
ap.add_argument("--project", required=True, help="專案名字（規格書「專案概述」的名稱，空白改底線）")
ap.add_argument("--highlight", action="append", help="額外要醒目標示的章節標題（可重複）")
args = ap.parse_args()

label, highlights = KIND_DEFAULTS[args.kind]
highlights = highlights + (args.highlight or [])
title = f"{args.project.replace('_', ' ')} {label}"
theme_key = f"{args.project}-report-theme"

text = open(args.src, encoding="utf-8").read()
lines = text.split("\n")
is_draft = any("DRAFT" in l for l in lines[:5] if l.startswith(">"))

chunks = []
cur = {"level": 0, "title": "", "lines": []}
in_code = False
for l in lines:
    if l.lstrip().startswith("```"):
        in_code = not in_code
    m = None if in_code else re.match(r"^(#{1,3}) (.+)$", l)
    if m:
        chunks.append(cur)
        cur = {"level": len(m.group(1)), "title": m.group(2).strip(), "lines": [l]}
    else:
        cur["lines"].append(l)
chunks.append(cur)

md = markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists"])
body = []
toc = []
n = 0
for c in chunks:
    if not "".join(c["lines"]).strip():
        continue
    # 文件以 2 格縮排寫巢狀清單；Python-Markdown 需要 4 格才認得
    src_lines = []
    fenced = False
    for ln in c["lines"]:
        if ln.lstrip().startswith("```"):
            fenced = not fenced
        if not fenced:
            ln = re.sub(r"^  (- |\d+\. )", r"    \1", ln)
        src_lines.append(ln)
    rendered = md.reset().convert("\n".join(src_lines))
    # 工作單的 `- [ ] **TXX …**` 呈現成票卡片
    rendered = re.sub(r"<li>(\s*<p>)?\[ \] <strong>", r'<li class="ticket">\1<span class="tbox">☐</span> <strong>', rendered)
    rendered = re.sub(r"<li>(\s*<p>)?\[x\] <strong>", r'<li class="ticket done">\1<span class="tbox">☑</span> <strong>', rendered)
    # 色碼前面加色塊
    rendered = re.sub(
        r"<code>(#[0-9a-fA-F]{6})</code>",
        r'<span class="sw" style="background:\1"></span><code>\1</code>',
        rendered,
    )
    if c["level"] in (2, 3):
        n += 1
        sid = f"s{n}"
        rendered = re.sub(r"^<h([23])>", rf'<h\1 id="{sid}">', rendered, count=1)
        toc.append((c["level"], sid, c["title"]))
    cls = "block"
    if any(h in c["title"] for h in highlights):
        cls += " highlight"
    if c["title"] == "缺口總覽":
        cls += " gap"
    body.append(f'<section class="{cls}">{rendered}</section>')

toc_html = "".join(
    f'<li class="lv{lv}"><a href="#{sid}">{html.escape(t.replace("`", ""))}</a></li>' for lv, sid, t in toc
)
banner = '<div class="draft">⚠️ 草稿——尚未定稿</div>' if is_draft else ""

page = f"""<!doctype html>
<html lang="zh-Hant" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script>
try {{ var t = localStorage.getItem({theme_key!r}); if (t === "dark" || t === "light") document.documentElement.setAttribute("data-theme", t); }} catch (e) {{}}
</script>
<title>{html.escape(title)}</title>
<style>
:root, [data-theme="light"] {{
  --bg:#ffffff; --surface:#f7f7f5; --border:#e3e3e0; --text:#37352f; --muted:#6b6a66;
  --link:#2563eb; --accent:#2563eb; --hl-bg:#eff6ff; --hl-border:#93c5fd;
  --gap-bg:#fffbeb; --gap-border:#f59e0b; --draft-bg:#fef3c7; --draft-fg:#92400e; --code-bg:#f1f1ef;
}}
[data-theme="dark"] {{
  --bg:#191919; --surface:#202020; --border:#333; --text:#e6e6e5; --muted:#9b9a97;
  --link:#60a5fa; --accent:#3b82f6; --hl-bg:#172036; --hl-border:#1e40af;
  --gap-bg:#2b230c; --gap-border:#b45309; --draft-bg:#3a2e0b; --draft-fg:#fcd34d; --code-bg:#262626;
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--text); font:15px/1.7 system-ui,-apple-system,"Segoe UI","Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif; }}
a {{ color:var(--link); }}
.wrap {{ max-width:1080px; margin:0 auto; padding:24px 16px 80px; }}
.toggle {{ position:fixed; top:12px; right:12px; z-index:10; background:var(--surface); color:var(--text); border:1px solid var(--border); border-radius:999px; padding:6px 14px; cursor:pointer; font:inherit; }}
.draft {{ background:var(--draft-bg); color:var(--draft-fg); border:1px solid var(--gap-border); padding:10px 16px; border-radius:8px; font-weight:700; margin:8px 0 16px; }}
nav.toc {{ background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:12px 20px; margin:16px 0 24px; }}
nav.toc ul {{ margin:0; padding-left:18px; columns:2; }}
nav.toc li.lv3 {{ margin-left:16px; font-size:13px; }}
section.highlight {{ background:var(--hl-bg); border:1px solid var(--hl-border); border-left:5px solid var(--accent); border-radius:8px; padding:4px 18px 12px; margin:12px 0; }}
section.gap {{ background:var(--gap-bg); border:1px solid var(--gap-border); border-left:5px solid var(--gap-border); border-radius:8px; padding:4px 18px 12px; margin:12px 0; }}
h1 {{ font-size:28px; margin:8px 0; }}
h2 {{ font-size:22px; margin:36px 0 10px; padding-bottom:6px; border-bottom:1px solid var(--border); }}
h3 {{ font-size:18px; margin:24px 0 8px; }}
table {{ border-collapse:collapse; width:100%; margin:10px 0; font-size:14px; display:block; overflow-x:auto; }}
th, td {{ border:1px solid var(--border); padding:6px 10px; text-align:left; vertical-align:top; }}
th {{ background:var(--surface); }}
code {{ background:var(--code-bg); padding:1px 5px; border-radius:4px; font-size:13px; word-break:break-word; }}
pre {{ background:var(--code-bg); padding:12px; border-radius:8px; overflow-x:auto; }}
pre code {{ padding:0; }}
blockquote {{ margin:8px 0; padding:4px 14px; border-left:4px solid var(--border); color:var(--muted); }}
ul:has(> li.ticket) {{ list-style:none; padding-left:0; }}
li.ticket {{ background:var(--surface); border:1px solid var(--border); border-left:4px solid var(--accent); border-radius:8px; padding:10px 16px; margin:12px 0; }}
li.ticket.done {{ border-left-color:#16a34a; }}
li.ticket > strong, li.ticket > p > strong {{ font-size:16px; }}
li.ticket .tbox {{ color:var(--muted); }}
li.ticket ul {{ margin:6px 0 0; padding-left:18px; font-size:14px; }}
.sw {{ display:inline-block; width:14px; height:14px; border-radius:3px; border:1px solid var(--border); vertical-align:-2px; margin-right:4px; }}
@media (max-width:700px) {{ nav.toc ul {{ columns:1; }} }}
</style>
</head>
<body>
<button class="toggle" id="themeBtn" type="button"></button>
<div class="wrap">
{banner}
<nav class="toc"><strong>目錄</strong><ul>{toc_html}</ul></nav>
{''.join(body)}
</div>
<script>
(function() {{
  var btn = document.getElementById("themeBtn"), root = document.documentElement, key = {theme_key!r};
  function label() {{ btn.textContent = root.getAttribute("data-theme") === "dark" ? "☀️ 白天" : "🌙 夜晚"; }}
  btn.addEventListener("click", function() {{
    var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    try {{ localStorage.setItem(key, next); }} catch (e) {{}}
    label();
  }});
  label();
}})();
</script>
</body>
</html>
"""
open(args.out, "w", encoding="utf-8").write(page)
tickets = len(re.findall(r'class="ticket', page))
print(f"wrote {args.out}  sections={n}  tickets={tickets}  draft={is_draft}")
