"""Build wearable_fusion_auth_paper.pdf from PAPER.md (markdown -> HTML -> PDF).

Resolves {{artifact:...}} image markers to the local figures/ PNGs by matching the
image alt-text, so it does not depend on exact artifact IDs. Run from paper/:
    python build_pdf.py
"""
import re
from pathlib import Path
from weasyprint import HTML, CSS

ALT_TO_FILE = {
    "within vs cross eer": "fig1_collapse.png",
    "per-signal degradation": "fig3_per_signal.png",
    "security bar": "fig2_security_bar.png",
}


def main() -> None:
    md = Path("PAPER.md").read_text()
    md = re.sub(r"^> .*$", "", md, flags=re.M)  # drop the top note blockquote

    def repl(m):
        alt = m.group(1).strip().lower()
        fn = ALT_TO_FILE.get(alt)
        return f"![{m.group(1)}]({fn})" if fn else m.group(0)

    md = re.sub(r"!\[([^\]]*)\]\(\{\{artifact:[^}]+\}\}\)", repl, md)

    import markdown
    body = markdown.markdown(md, extensions=["tables", "fenced_code", "toc"])
    assert "{{artifact" not in body, "unresolved artifact marker in HTML"
    css = (
        "@page{size:A4;margin:2cm;@bottom-center{content:counter(page);font-size:9px;color:#888}}"
        "body{font-family:'DejaVu Serif',Georgia,serif;font-size:10.5pt;line-height:1.45;color:#1a1a1a}"
        "h1{font-size:17pt;margin:0 0 2pt}h3{color:#444;font-weight:normal;font-size:12pt;margin-top:0}"
        "h2{font-size:13pt;border-bottom:1px solid #ccc;padding-bottom:2px;margin-top:16pt}"
        "h4{font-size:11pt;margin-bottom:2pt}table{border-collapse:collapse;width:100%;font-size:9pt;margin:8pt 0}"
        "th,td{border:1px solid #bbb;padding:3px 6px;text-align:left}th{background:#f0f0f0}"
        "img{max-width:100%;display:block;margin:8pt auto}code{background:#f4f4f4;padding:0 2px;font-size:9pt}"
        "a{color:#2166ac;text-decoration:none}"
    )
    html = f"<html><head><meta charset='utf-8'></head><body>{body}</body></html>"
    HTML(string=html, base_url=".").write_pdf(
        "wearable_fusion_auth_paper.pdf", stylesheets=[CSS(string=css)])
    n_imgs = body.count("<img")
    import os
    print(f"wrote wearable_fusion_auth_paper.pdf ({os.path.getsize('wearable_fusion_auth_paper.pdf')} bytes, {n_imgs} images)")


if __name__ == "__main__":
    main()
