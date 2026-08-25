# seed-workshop — 가져가는 도구

「노하우 시드화」 강의에서 **참가자가 가져가서 쓸 도구**만 모은 공개 페이지다.

> **담는 기준** — 참가자가 강의가 끝난 뒤 **가져가서 쓸 것만** 담는다.
> 그렇지 않은 것은 안 들어간다. 그게 전부다.

- 공개 주소: `https://hunontop.github.io/seed-workshop/`
- 강의안(비공개): `C:\dev\lecture\projects\노하우-시드화-50분\강의안.md`

## 담는 것 / 안 담는 것

| | |
|---|---|
| **담는다** | 프롬프트 원문 · 스킬 패키지 · 빈 템플릿 · 실습 샘플 |
| **안 담는다** | 강의안 · 원본 시드 라이브러리 · **계정명·기관명 등 현장 한정 정보** · 저작권 있는 원천 · 참가자 산출물 |

⚠️ **강의 레포(`C:\dev\lecture`)는 공개하지 않는다.** 기관명·미공개 기획·자료 경로가 들어 있다.
이 레포만 공개한다. 두 곳을 섞지 말 것.

⚠️ **계정명을 페이지에 적지 않는다.** 인스타 계정은 **현장 화면에서만** 보여준다.
강의장에서 말하는 것과 인터넷에 영구히 남는 문서는 결이 다르다.

## 담은 것 — **우선순위가 있다**

강의장에서 쓴 프롬프트는 슬라이드에도 있었다. **이 페이지의 값어치는 집에 가서 쓸 둘이다.**

| 순위 | 무엇 | 어디 |
|:--:|---|---|
| **①** | **책에서 그림과 텍스트를 어떻게 처리하나** | `guides/01-책-그림과-텍스트.md` |
| **②** | **화면이 낡았을 때 자동으로 다시 찍기** ★ | `guides/02-화면-자동-갱신.md` + `tools/` |
| **③** | **시드를 어떻게 정리하나 — 제텔카스텐 · PARA** | `guides/03-시드-정리법.md` |
| 덤 | 쓰기(조립·깎기·빈칸) · 쌓는 층 · SNS · 세션 시드화 스킬 | `index.html` · `skill/` |
| 실습 | 슬라이드 7장 · 결과 샘플 · **카드 8장(비번 zip)** | `practice/` · `downloads/실습카드-8장.zip` |

**①과 ②는 한 줄로 이어진다** — 책 그림 대부분이 **서비스 화면**이라 낡을 운명이라,
애초에 갖지 않고 `figures_todo`(찍을 목록)만 남긴다. **그 "찍기"를 자동화하는 것이 ②다.**

## 구조

```
index.html                 페이지 본체 (자기완결 — 외부 의존 0)
guides/                    ①·②·③ 전체 가이드
tools/capture_pages.py     화면 목록 → PNG + 언제 찍었는지 기록 + --stale 보고
tools/capture_live.py      외부 사이트 (Playwright + 실크롬 헤디드) · --login 은 필요할 때만
tools/shots.txt            찍을 목록 예시
templates/시드-템플릿.md     빈 시드 뼈대
practice/                  실습 슬라이드 7장 + ①의 결과 샘플
samples/                   막힌 사람이 중간부터 합류할 입력물 + 직접 쓴 카드 3장
skill/seed-from-session/   스킬 소스 (SSOT)
downloads/                 스킬 배포본 · 전체 도구모음 zip(USB 배포용) · 실습카드 8장(비번 zip)
.nojekyll                  GitHub Pages 의 Jekyll 처리를 끈다
```

⚠️ `.gitignore` 에 **`tools/pw_profile/`** 이 들어 있다 — 로그인 세션이다. **절대 커밋하지 말 것.**
캡처 산출물(`tools/shots/`·매니페스트)도 제외한다 — **재생성물을 보관하지 않는 게 이 저장소의 요지**다.

## 도구 재빌드

```powershell
# 오프라인 배포용 도구모음 zip (현장 와이파이 대비 USB 백업)
# ⚠️ 반드시 tools/pw_profile · tools/shots 가 없는 상태에서 돌릴 것 (아래 경고)
Compress-Archive -Path guides,tools,templates,samples,practice,downloads\seed-from-session.skill `
  -DestinationPath downloads\seed-workshop-도구모음.zip -Force
```

🔴 **`.gitignore` 는 zip 을 못 막는다 — 실제로 한 번 새어 나갔다(2026-08-24).**
`Copy-Item -Recurse` 나 `Compress-Archive` 는 `.gitignore` 를 보지 않는다.
`capture_live.py` 를 한 번이라도 돌리면 `tools/pw_profile/`(브라우저 프로필 · 쿠키)이 생기고,
그대로 압축하면 **공개 페이지에서 내려받는 zip 에 들어간다.**

**빌드 전에 지운다:**
```powershell
Remove-Item tools\pw_profile,tools\shots -Recurse -Force -ErrorAction SilentlyContinue
```

**빌드 후에 확인한다** — **17개 항목**이어야 하고 `pw_profile` 이 없어야 한다(2026-08-25 기준):
```powershell
Add-Type -AssemblyName System.IO.Compression.FileSystem
$z=[IO.Compression.ZipFile]::OpenRead("$PWD\downloads\seed-workshop-도구모음.zip")
$z.Entries.FullName; $z.Dispose()
```

## 스킬 재패키징

`skill/seed-from-session/` 이 정본이다. **거기를 고치고 다시 묶는다** — `downloads/` 에서 직접 고치지 말 것.

```powershell
Compress-Archive -Path skill\seed-from-session\* -DestinationPath downloads\seed-from-session.zip -Force
Move-Item downloads\seed-from-session.zip downloads\seed-from-session.skill -Force
```

## 배포

GitHub Pages: Settings → Pages → Source `main` / 루트(`/`).
`.nojekyll` 이 있어야 한글 파일명·`_` 로 시작하는 경로가 정상 서빙된다.

## 🔒 실습 카드 8장 — 비밀번호 zip

`downloads/실습카드-8장.zip` 은 **비밀번호를 걸어 둔다.** 카드의 원천이 남의 게시물이라
그냥 열어 두면 공개 배포가 되기 때문이다. **파일은 올리되 열리지는 않는 상태**로 둔다.

- 비밀번호는 **강의 중에 구두로** 전한다. **저장소·페이지·이 문서 어디에도 적지 않는다.**
- 강한 보안이 아니라 **우연한 공개 열람 차단**이 목적이다. 그 선에서 충분하다.
- 🔴 **정답지(`_강사용-정답지.md`)를 절대 같이 넣지 않는다.** 참가자에게 주지 않는 문서다.
- 🔴 **도구모음 zip에는 카드를 넣지 않는다.** 그쪽은 비밀번호가 없다.

## 갱신

- 도구가 낡으면 **버리지 말고 기준일을 갱신**한다. 페이지 하단의 기준일도 같이 고친다.
- 강의에서 즉석으로 쓴 자잘한 프롬프트는 **강의 후 강의 순서대로 추가**한다.
  이 페이지는 완성물이 아니라 자라는 것이다.
- 샘플(`samples/`)은 재구성한 예시다. **강사 본인의 실제 세션으로 바꾸면 더 좋다** —
  강의 준비물(강사가 미리 ②③을 돌려보기)과 같은 작업이라 한 번에 끝난다.
