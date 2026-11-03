#!/usr/bin/env bash
# 국가별 화면 비교 캡쳐 도구 실행 스크립트 (폐쇄망 반입용)
#
# 인터넷 되는 PC에서:
#   tools/site_compare/run.sh download                   # 이 PC와 같은 OS·Python용 패키지 받기
#   tools/site_compare/run.sh download linux             # 폐쇄망이 리눅스 x86_64일 때
#   -> 저장소 폴더 전체(tools/site_compare/wheels 포함)를 폐쇄망으로 옮김
#
# 폐쇄망 PC에서:
#   tools/site_compare/run.sh install                    # wheels/로 오프라인 설치 (.venv 생성)
#   tools/site_compare/run.sh check                      # Chrome 실행·samsung.com 접속 확인
#   tools/site_compare/run.sh capture tv_s95h            # 캡쳐 + 리포트 (그 밖의 인자는 그대로 전달)
#   tools/site_compare/run.sh capture tv_s95h --only uk,us --headed
#   tools/site_compare/run.sh build tv_s95h              # 캡쳐 없이 리포트만 재생성
#   tools/site_compare/run.sh all                        # 모든 상품을 차례로 캡쳐
#
# 환경변수: PYTHON(사용할 파이썬, 기본은 3.10 이상 자동 탐색), PYVER(download linux 대상 버전, 기본 3.12)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HERE="$ROOT/tools/site_compare"
WHEELS="$HERE/wheels"
VENV="$ROOT/.venv"
VPY="$VENV/bin/python"
cd "$ROOT"

find_python() {
  local c
  for c in ${PYTHON:-} python3.12 python3.13 python3.11 python3.10 python3; do
    if command -v "$c" >/dev/null 2>&1 &&
       "$c" -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>/dev/null; then
      echo "$c"; return
    fi
  done
  echo "Python 3.10 이상이 필요합니다 (PYTHON=경로 로 지정 가능)" >&2
  exit 1
}

need_venv() {
  [ -x "$VPY" ] || { echo ".venv가 없습니다. 먼저: $0 install" >&2; exit 1; }
}

cmd="${1:-help}"
case "$cmd" in
  download)
    py="$(find_python)"
    mkdir -p "$WHEELS"
    if [ "${2:-}" = "linux" ]; then
      "$py" -m pip download -r requirements.txt -d "$WHEELS" --only-binary=:all: \
        --platform manylinux2014_x86_64 --python-version "${PYVER:-3.12}"
    else
      "$py" -m pip download -r requirements.txt -d "$WHEELS"
    fi
    echo "받은 패키지: $WHEELS ($(ls "$WHEELS" | wc -l | tr -d ' ')개). 저장소 폴더째 폐쇄망으로 옮기세요."
    ;;
  install)
    py="$(find_python)"
    [ -x "$VPY" ] || "$py" -m venv "$VENV"
    if [ -d "$WHEELS" ] && [ -n "$(ls -A "$WHEELS")" ]; then
      "$VPY" -m pip install --no-index --find-links="$WHEELS" -r requirements.txt
    else
      echo "wheels/가 비어 있어 인터넷에서 설치합니다." >&2
      "$VPY" -m pip install -r requirements.txt
    fi
    echo "설치 완료. 다음: $0 check"
    ;;
  check)
    need_venv
    "$VPY" - <<'EOF'
from playwright.sync_api import sync_playwright

# 실제 캡쳐와 같은 Chrome으로 열어 봅니다 (사내 SSL 검사 환경에서도 시스템 인증서를 따름)
with sync_playwright() as p:
    try:
        b = p.chromium.launch(channel="chrome", headless=True)
    except Exception as e:
        raise SystemExit(f"[실패] Chrome 실행: {e}\n  -> Google Chrome을 설치하세요.")
    print(f"[OK] Chrome {b.version}")
    page = b.new_page()
    for url in ["https://www.samsung.com/uk/", "https://www.samsung.com/ca/", "https://www.samsung.com/us/"]:
        try:
            r = page.goto(url, timeout=30000, wait_until="domcontentloaded")
            print(f"[OK] {url} ({r.status if r else '?'})")
        except Exception as e:
            print(f"[실패] {url}: {str(e).splitlines()[0]}")
            print("  -> 접속이 막혀 있으면 capture는 안 됩니다 (프록시가 있으면 HTTPS_PROXY 설정).")
    b.close()
EOF
    ;;
  all)
    need_venv
    shift
    for f in "$HERE"/products/*.yaml; do
      p="$(basename "$f" .yaml)"
      echo "=== $p ==="
      "$VPY" -m tools.site_compare capture "$p" "$@" || echo "[실패] $p — 이어서 진행합니다." >&2
    done
    ;;
  capture|build|snapshot)
    need_venv
    exec "$VPY" -m tools.site_compare "$@"
    ;;
  *)
    sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'
    echo "상품: $(ls "$HERE"/products/*.yaml | xargs -n1 basename | sed 's/\.yaml$//' | tr '\n' ' ')"
    ;;
esac
