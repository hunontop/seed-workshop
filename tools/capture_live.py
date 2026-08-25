# -*- coding: utf-8 -*-
"""외부 서비스 화면 캡처 — **이게 기본 경로다.** Playwright + 진짜 크롬(헤디드).

왜 헤드리스가 아닌가
------------------
**헤드리스는 봇 차단에 막힌다. 로그인이 필요 없는 페이지라도 그렇다.**
Cloudflare 뒤에 있는 사이트를 `chrome --headless --screenshot` 으로 뜨면
**봇 검증 페이지나 빈 화면**이 찍힌다 — 파일은 멀쩡히 생겨서 열어보기 전엔 모른다.

실측
  · claude.ai 공유 링크  → 헤드리스로 봇 검증 페이지만 찍힘  (2026-08-03)
  · openai.com 요금제    → 헤드리스로 로고만 있는 빈 PNG      (2026-08-24)
  · anthropic.com · notebooklm.google → 헤드리스도 됨 (CF 게이트 없음)

⇒ **외부 사이트는 이 스크립트로 시작해라.** 헤드리스(`capture_pages.py`)는
   내 로컬 파일·자체 서버에만 쓴다 — 거기선 더 빠르고 확실하다.

세 가지를 바꾼다
  ⓐ 진짜 크롬(channel="chrome")  ⓑ 화면 있는 채로(headless=False)  ⓒ 자동화 표식 끄기

준비
----
    pip install playwright

쓰는 법
-------
    python capture_live.py                    # shots.live.txt 를 전부 찍는다
    python capture_live.py --only 요금제        # 이름에 그 말이 든 것만
    python capture_live.py --stale 180        # 낡은 것 보고
    python capture_live.py --login            # 로그인이 필요할 때만. 1회.

shots.live.txt 형식 (capture_pages.py 와 같다)
    ChatGPT요금제 = https://openai.com/chatgpt/pricing/

`--login` 으로 로그인하면 프로필이 `./pw_profile` 에 남아 다음부터 재사용된다.
**그 폴더를 공개 저장소에 올리지 마라 — 로그인 세션이 들어 있다.**
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from datetime import date, datetime

# 한글 윈도우 콘솔(cp949)은 ✓·⚠ 같은 글자를 못 찍어 **프로그램이 죽는다**.
# 캡처가 끝난 뒤 출력 단계에서 죽으면 매니페스트도 안 남는다 — 그래서 맨 앞에서 손본다.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = pathlib.Path(__file__).parent
PROFILE = HERE / "pw_profile"
SHOTS_FILE = HERE / "shots.live.txt"
OUT_DIR = HERE / "shots"
MANIFEST = HERE / "shots.live.manifest.json"

# 자동화 표식을 끄는 인자 — 이게 없으면 봇 차단에 걸린다
STEALTH_ARGS = ["--disable-blink-features=AutomationControlled"]
IGNORE_DEFAULTS = ["--enable-automation"]


def read_shots() -> list[tuple[str, str]]:
    if not SHOTS_FILE.exists():
        sys.exit(f"{SHOTS_FILE.name} 이 없다.\n  ChatGPT요금제 = https://openai.com/chatgpt/pricing/")
    out = []
    # utf-8-sig: 메모장·PowerShell 로 저장하면 BOM 이 붙어 첫 줄 이름에 섞인다
    for line in SHOTS_FILE.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, url = line.split("=", 1)
        out.append((name.strip(), url.strip()))
    return out


def launch(p, headless: bool):
    """실크롬 + 영속 프로필. channel='chrome' 이 핵심 — 번들 크로미움은 더 잘 걸린다."""
    kwargs = dict(
        user_data_dir=str(PROFILE),
        headless=headless,
        args=STEALTH_ARGS,
        ignore_default_args=IGNORE_DEFAULTS,
        viewport={"width": 1920, "height": 1080},
    )
    try:
        return p.chromium.launch_persistent_context(channel="chrome", **kwargs)
    except Exception:
        print("  ! 실크롬을 못 찾아 번들 크로미움으로 간다 — 봇 차단에 걸릴 수 있다.")
        return p.chromium.launch_persistent_context(**kwargs)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--login", action="store_true", help="로그인이 필요할 때만. 창을 띄워 손으로 로그인한다(1회)")
    ap.add_argument("--only", metavar="말")
    ap.add_argument("--stale", type=int, metavar="일수")
    args = ap.parse_args()

    if args.stale is not None:
        if not MANIFEST.exists():
            sys.exit("아직 찍은 게 없다.")
        man = json.loads(MANIFEST.read_text(encoding="utf-8"))
        today = date.today()
        rows = []
        for name, rec in man.items():
            age = (today - datetime.strptime(rec["captured"], "%Y-%m-%d").date()).days
            if age >= args.stale:
                rows.append((age, name, rec["captured"]))
        print(f"\n기준 {args.stale}일 · 오늘 {today}\n")
        for age, name, captured in sorted(rows, reverse=True):
            print(f"  {age:>5}일   {name}   (마지막 촬영 {captured})")
        print(f"\n  낡음 {len(rows)}장\n" if rows else "  낡은 것 없음\n")
        return

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("pip install playwright 먼저.")

    PROFILE.mkdir(exist_ok=True)

    if args.login:
        with sync_playwright() as p:
            ctx = launch(p, headless=False)
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto("about:blank")
            print("\n창이 떴다. 서비스에 **손으로 로그인**한 뒤 이 창을 닫아라.")
            print("(닫으면 프로필이 저장되고, 다음부터는 로그인 없이 찍는다)\n")
            try:
                page.wait_for_event("close", timeout=0)
            except Exception:
                pass
            ctx.close()
        print(f"프로필 저장됨: {PROFILE}")
        return

    shots = read_shots()
    if args.only:
        shots = [s for s in shots if args.only in s[0]]
    OUT_DIR.mkdir(exist_ok=True)
    man = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    today = date.today().isoformat()

    with sync_playwright() as p:
        # ⚠️ headless=False 다. 로그인 여부와 무관하게 헤드리스는 봇 차단에 걸린다(파일 머리말 실측).
        ctx = launch(p, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        for name, url in shots:
            try:
                page.goto(url, wait_until="networkidle", timeout=60000)
                page.wait_for_timeout(1500)
                png = OUT_DIR / f"{name}.png"
                page.screenshot(path=str(png), full_page=True)
                man[name] = {"url": url, "captured": today, "engine": "playwright-chrome"}
                print(f"  ✓ {name}")
            except Exception as e:
                print(f"  ✗ {name} — {type(e).__name__}: {e}")
                print("     로그인이 풀렸으면 --login 으로 다시 로그인해라.")
        ctx.close()

    MANIFEST.write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{OUT_DIR}  ·  기록 {MANIFEST.name}")


if __name__ == "__main__":
    main()
