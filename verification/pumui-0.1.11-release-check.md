# 품의 플러그인 0.1.11 검증 기록

검증일: 2026-10-20

## 범위

- Claude Code 사진은 실제 질문의 진행 방식과 판단 항목을 파악하는 참고로 사용했습니다. 모든 품의에 같은 문구나 순서를 강제하지 않습니다.
- 필요한 질문은 맥락별로 골라 한 번에 하나씩 제시하고, 객관식 목록 안에 `직접 입력`을 둡니다. 사람·회차·원본별로 다른 값은 별도 질문 ID와 출처 revision에 묶습니다.
- 답변 상태가 없거나 필요한 답이 남아 있으면 생성 경로를 차단합니다. 선택값, 사용자 수정값, 확인된 출처 값을 case와 대조합니다.
- HWPX·TXT는 내장 읽기 경로를 사용합니다. 레거시 HWP·PDF 분석은 이미 설치된 kordoc 호환 실행 파일이 있을 때만 선택적으로 시도합니다. 플러그인은 엔진을 설치하거나 내려받지 않습니다.
- HWPX 생성은 기존 품의 바탕 양식과 생성기를 유지합니다. 범용 문서 변환기로 품의 양식을 대체하지 않습니다.

## 자동 검증

- Python `unittest discover -s verification`: 41개 테스트 통과. 질문 상태·직접 입력·case 바인딩·문서 어댑터·패키징 재현성을 확인합니다.
- `npm run check:content`: 통과. 웹사이트 카탈로그의 다운로드 이름과 렌더 결과를 확인합니다.
- `node --test tests/content.spec.mjs`: 8개 콘텐츠 계약 테스트 통과.
- `python verification/package_release.py --check`: 소스 파일과 다운로드 ZIP의 바이트 일치, 단일 플러그인 루트, 안전한 경로, SHA-256 sidecar를 확인합니다.
- 배포 ZIP은 28개 파일을 포함합니다. SHA-256: `fa3752c3d335f0962ccfa4968d1cee08554db2b5da070da6f5e8782feb1622d3`.

## 실제 런타임 한계

- 실제 HWP/HWPX 업무 문서, 스캔 PDF, kordoc 설치본, Windows 한글 COM, 실제 ChatGPT 플러그인 화면은 이 검증에 사용하지 않았습니다. 자동 테스트 입력은 합성 자료입니다.
- 내장 HWPX 추출은 section 텍스트 순서를 읽고 표 셀 배치·병합은 보존하지 않습니다. 표 구조가 필요한 분석은 이미 설치·연결된 엔진을 사용해야 합니다.
- 이 저장소의 Python 스크립트가 ChatGPT의 모든 플러그인 화면에서 자동 실행되거나 선택지가 실제 버튼으로 렌더되는 것은 아닙니다. 실행 도구와 파일 접근 여부를 확인하고 텍스트 선택지를 보여 주도록 지침과 로컬 검증 경로를 제공합니다.
- k-skill의 MIT 안내 및 kordoc 연결 방식만 참고했습니다. hwpx-skill·hwp-mcp 코드는 복사하지 않았고 필수 설치로 만들지 않았습니다.

합성 대화 시나리오와 대응 테스트는 [`dialogues/README.md`](dialogues/README.md)에 기록했습니다. ZIP 생성·검증 명령은 저장소 루트에서 `python verification/package_release.py` 및 `python verification/package_release.py --check`입니다.
