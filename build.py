#!/usr/bin/env python3
"""src.html + saga.mp3 -> index.html (오디오 base64 내장)"""
import base64, pathlib

root = pathlib.Path(__file__).parent
b64 = base64.b64encode((root / 'saga.mp3').read_bytes()).decode()
logo_b64 = base64.b64encode((root / 'logo.png').read_bytes()).decode()
html = (root / 'src.html').read_text(encoding='utf-8')
assert '__SAGA_SRC__' in html, 'src.html에 __SAGA_SRC__ 플레이스홀더가 없습니다'
assert '__LOGO_SRC__' in html, 'src.html에 __LOGO_SRC__ 플레이스홀더가 없습니다'
html = html.replace('__SAGA_SRC__', 'data:audio/mpeg;base64,' + b64)
html = html.replace('__LOGO_SRC__', 'data:image/png;base64,' + logo_b64)
(root / 'index.html').write_text(html, encoding='utf-8')
print(f'index.html 생성 완료 ({(root / "index.html").stat().st_size / 1048576:.2f} MB)')
