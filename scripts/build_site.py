import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from build_dashboard import build_dashboard_body
OUT = ROOT / '_site'; OUT.mkdir(exist_ok=True)
DOCTYPE = chr(60) + chr(33) + 'doctype html' + chr(62)
PAGE = DOCTYPE + '<html><head><meta charset="utf-8"><title>Claude Tools</title></head><body>' + build_dashboard_body() + '</body></html>'
(OUT / 'dashboard.html').write_text(PAGE, encoding='utf-8')
print('wrote dashboard')
