"""Shared, auditable download and reporting helpers. No private data required."""
import hashlib
import html
import io
import json
from pathlib import Path
import urllib.request
import zipfile


def dataset(root, dataset_id, slug, filename):
    folder = Path(root) / 'data'
    folder.mkdir(exist_ok=True)
    archive = folder / 'source.zip'
    if not archive.exists():
        url = f'https://archive.ics.uci.edu/static/public/{dataset_id}/{slug}.zip'
        req = urllib.request.Request(url, headers={'User-Agent': 'MinwooPortfolio/1.0'})
        with urllib.request.urlopen(req, timeout=60) as response:
            payload = response.read(20_000_001)
        if len(payload) > 20_000_000:
            raise ValueError('Unexpected archive size')
        archive.write_bytes(payload)
    def find(payload):
        with zipfile.ZipFile(io.BytesIO(payload)) as z:
            for name in z.namelist():
                if name.split('/')[-1] == filename:
                    return z.read(name)
            for name in z.namelist():
                if name.endswith('.zip'):
                    result = find(z.read(name))
                    if result is not None:
                        return result
        return None
    raw = archive.read_bytes()
    content = find(raw)
    if content is None:
        raise ValueError('Dataset file not found: ' + filename)
    path = folder / filename
    path.write_bytes(content)
    return path, hashlib.sha256(raw).hexdigest()


def save_report(root, title, summary, sections, metrics):
    folder = Path(root) / 'reports'
    folder.mkdir(exist_ok=True)
    (folder / 'metrics.json').write_text(json.dumps(metrics, indent=2), encoding='utf-8')
    esc = html.escape
    blocks = ''.join(f'<section><h2>{esc(h)}</h2><p>{esc(p)}</p></section>' for h,p in sections)
    rows = ''.join(f'<tr><th>{esc(str(k))}</th><td>{esc(str(v))}</td></tr>' for k,v in metrics.items() if not isinstance(v,(dict,list)))
    page = f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>{esc(title)}</title>
    <style>body{{max-width:1000px;margin:42px auto;padding:0 24px;font:17px/1.6 system-ui;color:#182538}}
    h1{{font-size:36px;line-height:1.15}}h2{{font-size:23px;margin-top:30px}}table{{border-collapse:collapse;width:100%}}
    th,td{{padding:10px;border-bottom:1px solid #d7dfe8;text-align:left}}th{{width:55%}}small{{color:#536174}}</style>
    <small>Minwoo Jeong · Personal portfolio · Built with AI assistance</small><h1>{esc(title)}</h1>
    <p>{esc(summary)}</p><table>{rows}</table>{blocks}</html>'''
    (folder / 'executive_brief.html').write_text(page, encoding='utf-8')

