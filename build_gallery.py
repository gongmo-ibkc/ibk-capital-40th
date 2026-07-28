# -*- coding: utf-8 -*-
"""사진/ 원본 → photos/g###.jpg 썸네일 + src.html의 GALLERY 매니페스트 갱신
실행: python -X utf8 build_gallery.py  (이후 python3 build.py 로 index.html 재생성)

- EXIF 회전 보정, 같은 연월 내 시각적 근접 중복 제거(해상도 낮은 쪽 폐기)
- 높이 340px 리사이즈, JPEG q77 (EXIF 등 메타데이터 제거됨)
- 캡션: 실명 괄호("(김재원 외)" 등) 제거 — 공개 사이트라 이름 노출 금지,
  "사회공헌_" 프리픽스/봉사·헌혈·나눔 키워드 → 나눔(금색 태그) 플래그
- src.html 안의 `const GALLERY=[...];` 한 줄을 새 매니페스트로 교체
"""
import glob, os, re, json
from PIL import Image, ImageOps

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "사진")
OUT = os.path.join(ROOT, "photos")
HTML = os.path.join(ROOT, "src.html")
os.makedirs(OUT, exist_ok=True)

files = sorted(glob.glob(os.path.join(SRC, "*")))
print("원본:", len(files))

items = []
for f in files:
    try:
        im = ImageOps.exif_transpose(Image.open(f)).convert("RGB")
    except Exception as e:
        print("SKIP", f, e); continue
    fp = list(im.resize((16, 16)).convert("L").getdata())
    stem = os.path.splitext(os.path.basename(f))[0]
    m = re.match(r"^(\d{4})(\d{2})_(.+)$", stem)
    if not m:
        print("이름형식 불일치 SKIP:", stem); continue
    items.append({"f": f, "im": im, "fp": fp, "y": m.group(1), "m": m.group(2),
                  "desc": m.group(3), "px": im.size[0] * im.size[1]})

def mae(a, b):
    return sum(abs(x - y) for x, y in zip(a, b)) / 256.0

drop = set()
for i in range(len(items)):
    for j in range(i + 1, len(items)):
        a, b = items[i], items[j]
        if a["y"] + a["m"] != b["y"] + b["m"] or i in drop or j in drop:
            continue
        if mae(a["fp"], b["fp"]) < 9:
            drop.add(i if a["px"] < b["px"] else j)
            print("중복 제거:", os.path.basename(items[i if a['px'] < b['px'] else j]["f"]))
items = [it for k, it in enumerate(items) if k not in drop]

def clean_caption(desc):
    s = desc.replace("&amp;", "&").replace("박랍회", "박람회")
    nanum = s.startswith("사회공헌_")
    if nanum:
        s = s[len("사회공헌_"):]
    if re.search(r"봉사|헌혈|불우이웃|연탄|나눔", s):
        nanum = True
    s = re.sub(r"\s*\([^)]{2,12}외\)", "", s)   # 실명 목록 괄호 제거
    s = re.sub(r"\s*\(\d+\)$", "", s)            # 파일 중복 표기 (2) 제거
    # "해외박람회(X)" → X만 (박람회명 자체로 충분) + 표기 정규화
    m = re.match(r"^해외박람회\((.+)\)$", s)
    if m:
        x = m.group(1).strip()
        x = re.sub(r"^(\d{4})\s*(CES|MWC|IFA)$", r"\2 \1", x)   # 2018MWC → MWC 2018
        x = re.sub(r"^(CES|MWC|IFA)\s*(\d{4})$", r"\1 \2", x)   # CES2018 → CES 2018
        x = x.replace("로스엔젤레스", "LA").replace("의약품 제약전시회", "제약전시회")
        x = x.replace("국제 플라스틱 및 고무", "플라스틱·고무")
        s = x
    # 남은 괄호 정리: 차수(1차,) 제거, 쉼표 나열 → 가운뎃점
    def tidy(mm):
        inner = re.sub(r"^\d차,\s*", "", mm.group(1))
        return "(" + re.sub(r"\s*,\s*", "·", inner) + ")"
    s = re.sub(r"\((.+)\)$", tidy, s)
    return re.sub(r"\s+", " ", s).strip(), nanum

# 기존 썸네일/확대본 비우고 새로 저장 (번호 밀림 방지)
for old in glob.glob(os.path.join(OUT, "g*.jpg")) + glob.glob(os.path.join(OUT, "f*.jpg")):
    os.remove(old)

manifest = []
for idx, it in enumerate(items, 1):
    src_im = it["im"]
    w, h = src_im.size
    # 라이트박스 확대본 (높이 최대 800px, 업스케일 없음)
    full = src_im.resize((round(w * 800 / h), 800), Image.LANCZOS) if h > 800 else src_im
    full.save(os.path.join(OUT, f"f{idx:03d}.jpg"), "JPEG", quality=80, optimize=True, progressive=True)
    # 마퀴 썸네일 (높이 340px)
    im = src_im.resize((round(w * 340 / h), 340), Image.LANCZOS) if h > 340 else src_im
    im.save(os.path.join(OUT, f"g{idx:03d}.jpg"), "JPEG", quality=77, optimize=True, progressive=True)
    cap, nanum = clean_caption(it["desc"])
    # [파일, 캡션, 연월, 나눔, 썸네일 w, h] — w/h는 카드 비율 유지(얼굴 잘림 방지)용
    manifest.append([f"g{idx:03d}.jpg", cap, f"{it['y']}.{it['m']}", 1 if nanum else 0, im.size[0], im.size[1]])

total = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT))
print(f"썸네일 {len(manifest)}장, 총 {total/1024/1024:.1f}MB, 나눔 {sum(m[3] for m in manifest)}장")

js = "const GALLERY=" + json.dumps(manifest, ensure_ascii=False, separators=(",", ":")) + ";"
src = open(HTML, encoding="utf-8").read()
new = re.sub(r"const GALLERY=\[.*?\];", lambda _: js, src, count=1)
assert new != src or js in src, "src.html에서 GALLERY 마커를 찾지 못했습니다"
open(HTML, "w", encoding="utf-8", newline="").write(new)
print("src.html GALLERY 갱신 완료 — build.py 실행으로 index.html 재생성 필요")
