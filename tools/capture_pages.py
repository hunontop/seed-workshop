# -*- coding: utf-8 -*-
"""화면 목록 → PNG 폴더. 낡은 스크린샷을 "다시 실행"으로 갱신하기 위한 도구.

핵심 생각
---------
찍은 그림을 보관하지 말고 **다시 찍을 수 있는 상태**를 보관한다.
그 상태 = 이 스크립트 + `shots.txt`(무엇을 찍나) + `shots.manifest.json`(언제 찍었나).

쓰는 법
-------
    python capture_pages.py                      # shots.txt 전부 찍는다
    python capture_pages.py --stale 180          # 180일 넘은 것만 알려준다 (안 찍는다)
    python capture_pages.py --only 로그인화면      # 이름에 그 말이 든 것만 다시 찍는다
    python capture_pages.py --width 1440         # 캡처 폭 (기본 1920)

shots.txt 형식 (한 줄에 하나, `#`은 주석)
    이름 = URL
    가입화면 = https://example.com/signup
    로컬덱  = file:///C:/work/deck/index.html

로그인이 필요한 화면은 이 스크립트로 못 찍는다 → `capture_login.py` 를 쓴다.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import urllib.parse
from datetime import date, datetime

# 한글 윈도우 콘솔(cp949)은 ✓·⚠ 같은 글자를 못 찍어 **프로그램이 죽는다**.
# 캡처가 끝난 뒤 출력 단계에서 죽으면 매니페스트도 안 남는다 — 그래서 맨 앞에서 손본다.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = pathlib.Path(__file__).parent
SHOTS_FILE = HERE / "shots.txt"
OUT_DIR = HERE / "shots"
MANIFEST = HERE / "shots.manifest.json"

CHROME_CANDIDATES = [
    os.environ.get("CHROME_EXE", ""),
    r"C:/Program Files/Google/Chrome/Application/chrome.exe",
    r"C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
]


def find_chrome() -> str:
    for c in CHROME_CANDIDATES:
        if c and pathlib.Path(c).exists():
            return c
    sys.exit("크롬을 못 찾았다. 환경변수 CHROME_EXE 에 경로를 넣어라.")


def read_shots(path: pathlib.Path) -> list[tuple[str, str]]:
    if not path.exists():
        sys.exit(f"{path.name} 이 없다. 아래처럼 한 줄에 하나씩 적어라.\n  가입화면 = https://example.com/signup")
    out = []
    # utf-8-sig: 메모장·PowerShell 로 저장하면 BOM 이 붙어 첫 줄 이름에 섞인다
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            print(f"  ! 건너뜀(= 없음): {line}")
            continue
        name, url = line.split("=", 1)
        out.append((name.strip(), url.strip()))
    return out


def to_url(raw: str) -> str:
    """로컬 경로면 file:// 로 바꾼다."""
    if raw.startswith(("http://", "https://", "file://")):
        return raw
    p = pathlib.Path(raw).resolve()
    return "file:///" + urllib.parse.quote(str(p).replace("\\", "/"), safe="/:")


def looks_blank(png: pathlib.Path) -> bool:
    """거의 한 색이면 '빈 화면'으로 본다.

    ⚠️ 이게 왜 필요한가 — **캡처는 조용히 실패한다.**
    JS 로 본문을 그리는 페이지는 렌더가 끝나기 전에 찍혀서 **로고만 있는 PNG** 가 남는다.
    파일은 멀쩡히 생겨서 눈으로 열어보기 전엔 모른다. 그래서 기계가 먼저 의심한다.
    """
    try:
        from PIL import Image
    except ImportError:
        return False
    with Image.open(png) as im:
        hist = im.convert("L").histogram()
        total = sum(hist)
        return total > 0 and max(hist) / total > 0.985


def trim(png: pathlib.Path) -> tuple[int, int] | None:
    """아래쪽 빈 여백을 잘라낸다. Pillow 가 없으면 건너뛴다(그래도 캡처는 된다)."""
    try:
        from PIL import Image, ImageChops
    except ImportError:
        return None
    with Image.open(png) as im:
        im = im.convert("RGB")
        bg = Image.new("RGB", im.size, im.getpixel((im.width - 1, im.height - 1)))
        bbox = ImageChops.difference(im, bg).getbbox()
        if bbox:
            # 좌우는 건드리지 않는다 — 폭은 의도한 값이다. 아래 여백만 자른다.
            im = im.crop((0, 0, im.width, max(bbox[3] + 1, 1)))
            im.save(png)
        return im.size


def load_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {}


def report_stale(days: int) -> None:
    man = load_manifest()
    if not man:
        sys.exit("아직 찍은 게 없다. 먼저 한 번 돌려라.")
    today = date.today()
    stale, fresh = [], 0
    for name, rec in sorted(man.items()):
        captured = datetime.strptime(rec["captured"], "%Y-%m-%d").date()
        age = (today - captured).days
        if age >= days:
            stale.append((age, name, rec["captured"]))
        else:
            fresh += 1
    print(f"\n기준 {days}일 · 오늘 {today}\n")
    if not stale:
        print(f"  낡은 것 없음 ({fresh}장 전부 최신)")
        return
    for age, name, captured in sorted(stale, reverse=True):
        print(f"  {age:>5}일   {name}   (마지막 촬영 {captured})")
    print(f"\n  낡음 {len(stale)}장 · 최신 {fresh}장")
    print(f"  다시 찍기:  python {pathlib.Path(__file__).name} --only <이름>")
    print(f"  전부 다시:  python {pathlib.Path(__file__).name}\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stale", type=int, metavar="일수", help="이 일수를 넘긴 샷만 보고한다(촬영 안 함)")
    ap.add_argument("--only", metavar="말", help="이름에 이 말이 든 샷만 찍는다")
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--tall", type=int, default=6000, help="넉넉히 잡고 아래 여백을 잘라낸다")
    ap.add_argument("--wait", type=int, default=6000, help="렌더 대기 ms")
    ap.add_argument("--timeout", type=int, default=60,
                    help="한 장에 이 초를 넘기면 포기하고 다음으로 (기본 60)")
    args = ap.parse_args()

    if args.stale is not None:
        report_stale(args.stale)
        return

    chrome = find_chrome()
    shots = read_shots(SHOTS_FILE)
    if args.only:
        shots = [s for s in shots if args.only in s[0]]
        if not shots:
            sys.exit(f"'{args.only}' 에 맞는 샷이 없다.")

    OUT_DIR.mkdir(exist_ok=True)
    man = load_manifest()
    today = date.today().isoformat()
    suspects: list[str] = []

    for name, raw in shots:
        png = OUT_DIR / f"{name}.png"
        before = png.stat().st_mtime if png.exists() else 0
        try:
            subprocess.run(
                [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                 "--force-device-scale-factor=1",
                 f"--window-size={args.width},{args.tall}",
                 f"--virtual-time-budget={args.wait}",
                 f"--screenshot={png}", to_url(raw)],
                capture_output=True, timeout=args.timeout,
            )
        except subprocess.TimeoutExpired:
            # ⚠️ 애니메이션·폴링이 안 끝나는 페이지는 크롬이 스스로 안 죽는다.
            #    실측: 마케팅 페이지 하나가 무한 대기했다. 그래서 시간을 끊는다.
            print(f"  ⏱ {name} — {args.timeout}초 초과. 건너뛴다 (--timeout 으로 늘릴 수 있다)")
            continue
        if not png.exists() or png.stat().st_mtime == before:
            print(f"  ✗ {name} — 캡처 실패. 로그인이 필요한 화면이면 capture_login.py 를 써라.")
            continue
        size = trim(png)
        blank = looks_blank(png)
        man[name] = {"url": raw, "captured": today, "width": args.width}
        if blank:
            man[name]["suspect"] = "거의 빈 화면 — 확인 필요"
            suspects.append(name)
            print(f"  ⚠ {name}  {size or ''}  ← 거의 빈 화면이다. 열어서 확인해라")
        else:
            print(f"  ✓ {name}  {size or ''}")

    MANIFEST.write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{OUT_DIR}  ·  기록 {MANIFEST.name}")
    if suspects:
        print(
            "\n⚠ 빈 화면으로 의심되는 것: " + ", ".join(suspects) + "\n"
            "   JS 로 본문을 그리는 페이지는 헤드리스 크롬이 렌더 전에 찍는다.\n"
            "   → --wait 을 늘려보고, 그래도 비면 capture_login.py 를 써라.\n"
            "     (로그인이 없어도 된다 — 그쪽은 네트워크가 잠잠해질 때까지 기다린다)"
        )


if __name__ == "__main__":
    main()
