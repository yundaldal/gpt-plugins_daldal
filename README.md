# 달달샘 GPT 플러그인 모음

교육·업무용 플러그인을 모아 공유하는 저장소입니다.

| 플러그인 | 설명 | 개별 ZIP 다운로드 | 사용 안내·원본 |
|---|---|---|---|
| 관련 공문 정보 추출기_달달샘 | 공문 목록 이미지에서 문서번호·날짜·제목 추출 | [플러그인 ZIP 다운로드](https://github.com/yundaldal/gpt-plugins_daldal/raw/refs/heads/main/downloads/related-document-extractor.zip) | [사용 안내·원본](plugins/related-document-extractor/) |
| 품의 기안 도우미_달달샘 | 수당·물품·경비 품의 초안, 계산 산출물 및 교차 점검 | [플러그인 ZIP 다운로드 (0.1.1)](https://github.com/yundaldal/gpt-plugins_daldal/raw/refs/heads/main/downloads/pumui-daldal-0.1.1.zip) | [설치·사용 안내·원본](plugins/pumui-daldal/) |

## 플러그인 하나씩 다운로드하기

1. 표에서 필요한 플러그인의 **플러그인 ZIP 다운로드**를 누릅니다.
2. 해당 플러그인 ZIP 하나만 내려받습니다. 품의 기안 도우미 ZIP에는 플러그인 설명, 스킬, 참고 자료, 빈 서식, 스크립트가 함께 들어 있습니다.
3. 저장소 화면의 **Code → Download ZIP**은 플러그인 하나가 아니라 저장소 전체를 받습니다. 데스크톱에서 로컬 마켓플레이스를 설치할 때는 전체 저장소가 필요할 수 있습니다.

직접 링크가 열리지 않으면 [downloads 폴더](downloads/)에서 원하는 플러그인 ZIP 파일을 열고 **Download raw file**을 선택하세요.

## 설치 경로 선택

- **ChatGPT 웹에서 ZIP 업로드:** 업로드 권한이 있는 워크스페이스 관리자 등이 사용할 수 있습니다. **관리자 콘솔 → 워크스페이스 선택 → 플러그인 → 추가 → 플러그인 업로드**로 들어가 해당 플러그인의 ZIP을 올립니다. 메뉴가 보이지 않으면 계정·워크스페이스 역할의 업로드 권한을 확인하세요.
- **ChatGPT Desktop 로컬 마켓플레이스:** 지원되는 데스크톱 환경에서는 Codex CLI에서 `codex plugin marketplace add yundaldal/gpt-plugins_daldal`을 실행하고 앱을 다시 시작한 뒤, **플러그인 디렉터리**에서 `달달 품의 플러그인`을 선택해 설치할 수 있습니다. 저장소 전체를 압축 해제해 사용하는 경우 저장소 루트에서 `codex plugin marketplace add .`을 실행합니다.
- **개인용 Free·Plus 계정:** 플러그인 디렉터리는 여러 요금제에서 제공되지만, 개별 플러그인의 설치와 ZIP 업로드는 계정·화면·지역·워크스페이스 권한에 따라 달라집니다. 이 저장소에 GitHub로 공개했다고 해서 공개 플러그인 디렉터리에 등록된 것은 아닙니다. 개인 계정에 ZIP 업로드 메뉴가 없다면 지원되는 데스크톱 로컬 마켓플레이스 또는 업로드 권한이 있는 워크스페이스를 이용하세요.

품의 플러그인의 구체적인 설치 단계와 자료 준비 방법은 [품의 기안 도우미 안내](plugins/pumui-daldal/README.md)를 참고하세요. 플러그인 ZIP을 Custom GPT의 **지식(Knowledge)** 파일로 올리는 것은 플러그인 설치와 다릅니다.

## 개인정보와 정확성

공개 플러그인의 예시와 검증 자료는 가상 정보입니다. 실제 공문 이미지, 품의 입력·출력 자료, 성명·계좌, 대화 기록, 인증 정보는 포함하지 않습니다. 문서와 계산 결과는 검토용 초안이며, 원본 자료·단가 적용 여부·회계 요건을 담당자가 확인한 뒤 사용하세요. 플러그인별 지원 범위와 설치 조건은 각 사용 안내를 참고하세요.

## 공식 안내

- [ChatGPT 플러그인 설치 및 ZIP 업로드](https://help.openai.com/en/articles/20001256-plugins-in-chatgpt)
- [GitHub 마켓플레이스 가져오기 및 동기화](https://help.openai.com/en/articles/20001504-importing-and-syncing-plugin-marketplaces-from-github)
- [플러그인 패키지 및 로컬 마켓플레이스](https://developers.openai.com/plugins/build/plugins)
