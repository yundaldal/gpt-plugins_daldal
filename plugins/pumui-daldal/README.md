# 품의 기안 도우미

한국 교육기관의 지출품의 초안과 계산 산출물을 준비하는 skills-only 플러그인입니다. A1~A4 수당, B1~B2 물품 구입, C1~C3 경비 흐름을 지원합니다. 외부 앱이나 계정 연결은 필요하지 않습니다.

포함된 단가표는 2026년 참고 프로필입니다. 기관·회계연도에 적용되는지 사용자가 확인하기 전에는 수당 계산을 진행하지 마세요. 생성 문서는 검토용 초안이며, 회계 분류·규정·결재 요건의 최종 판단을 대신하지 않습니다.

## 플러그인 설치와 입력 자료는 별개입니다

- **처음 설치할 때:** 품의 기안 도우미의 플러그인 전용 ZIP 하나를 설치합니다. ZIP 안에 `plugin.json`, 스킬 지침, 참고 JSON, 빈 HWPX·XLSX 양식, 스크립트가 함께 있습니다. 이 자료들을 하나씩 다시 첨부할 필요가 없습니다.
- **품의 작업을 할 때:** ChatGPT 대화형 작업에서는 그 건에 필요한 원본 자료만 해당 대화에 첨부하거나 요청된 내용을 입력합니다. 플러그인을 설치했다고 해서 ChatGPT가 PC의 임의 폴더를 자동으로 읽는 것은 아닙니다.
- **로컬 스크립트를 사용할 때:** 입력 자료와 `case.json`, 결과는 플러그인 폴더나 공개 GitHub 저장소에 넣지 말고 별도의 비공개 작업 폴더에 둡니다. 아래 로컬 실행 방법에서 입력 폴더 경로를 선택합니다.

플러그인 ZIP을 Custom GPT 편집기의 **지식(Knowledge)**에 올리는 것은 설치 방법이 아닙니다. 지식 파일 업로드는 참고자료를 GPT에 제공하는 기능이며, 플러그인 구성이나 ZIP 안의 스크립트 실행을 설정하지 않습니다.

## 플러그인 ZIP 개별 다운로드

[품의 기안 도우미 ZIP 0.1.1 다운로드](https://github.com/yundaldal/gpt-plugins_daldal/raw/refs/heads/main/downloads/pumui-daldal-0.1.1.zip)

ZIP 내부 최상위에는 `pumui-daldal/` 폴더가 있습니다. 전체 원본과 테스트 자료는 [저장소의 플러그인 소스](https://github.com/yundaldal/gpt-plugins_daldal/tree/main/plugins/pumui-daldal)에서 확인할 수 있습니다.

## ChatGPT 웹에서 ZIP 업로드

공식 안내에서 ZIP 업로드는 업로드 권한이 있는 사용자나 자격을 갖춘 워크스페이스 소유자·관리자에게 제공됩니다. 메뉴가 보이지 않으면 개인용 Free·Plus 계정에서 사용할 수 있다고 가정하지 마세요.

1. 위의 **품의 기안 도우미 ZIP** 하나를 내려받습니다.
2. ChatGPT 웹에서 **관리자 콘솔(Admin console)**을 열고 대상 워크스페이스를 선택합니다.
3. **플러그인(Plugins) → 추가(Add) → 플러그인 업로드(Upload plugin)**를 선택하고 품의 플러그인 ZIP을 올립니다.
4. 관리자에게 플러그인을 워크스페이스에서 사용할 수 있도록 설정해 달라고 요청합니다. 설정에 따라 사용자가 **설치(Install plugin)**를 눌러야 할 수 있습니다.
5. ChatGPT 대화에서 `@품의 기안 도우미`를 입력해 선택하거나, 메시지 입력창의 `+` / **플러그인(Plugins)** 메뉴에서 설치된 플러그인을 선택합니다. 자동 선택이 제공되는 화면에서는 요청 내용에 따라 플러그인이 선택될 수도 있습니다.

워크스페이스의 **플러그인 업로드(Upload plugins)** 권한은 요금제만으로 결정되지 않습니다. 특히 Enterprise 워크스페이스에서는 관리자가 이 권한을 꺼둘 수 있습니다. ChatGPT 플러그인 디렉터리 자체는 여러 요금제에서 제공되지만, 개별 플러그인을 설치하거나 사용하는 조건은 계정·요금제·지역·워크스페이스 역할에 따라 다릅니다. 이 GitHub 저장소는 공개 플러그인 디렉터리에 등록된 저장소가 아닙니다.

## ChatGPT Desktop에서 로컬 마켓플레이스 사용

지원되는 ChatGPT Desktop의 Work 또는 Codex 환경에서는 GitHub 저장소의 마켓플레이스를 등록해 설치할 수 있습니다. 이 방법은 플러그인 리소스 파일을 따로 첨부하는 절차가 아닙니다. 마켓플레이스가 플러그인 폴더를 가리킵니다.

### GitHub 저장소를 바로 등록

Codex CLI가 설치된 환경의 터미널에서 다음을 실행합니다.

```powershell
codex plugin marketplace add yundaldal/gpt-plugins_daldal
```

ChatGPT Desktop을 완전히 종료하고 다시 시작한 뒤, **플러그인 디렉터리(Plugins Directory)**에서 `달달 품의 플러그인` 마켓플레이스를 열고 **품의 기안 도우미**를 설치합니다. 이 저장소 마켓플레이스에는 관련 공문 정보 추출기도 함께 표시됩니다.

### 저장소 ZIP을 내려받아 등록

1. 저장소 첫 화면에서 **Code → Download ZIP**을 눌러 저장소 전체를 내려받고 압축을 풉니다. 이 단계에서는 개별 플러그인 ZIP이 아니라 저장소 전체 ZIP을 사용합니다.
2. 압축을 푼 폴더의 루트에 `.agents/plugins/marketplace.json`이 있고, `plugins/pumui-daldal/` 폴더가 있는지 확인합니다.
3. PowerShell에서 저장소 루트로 이동해 등록합니다.

   ```powershell
   Set-Location "<압축을 푼 저장소 폴더>"
   codex plugin marketplace add .
   ```

4. ChatGPT Desktop을 완전히 종료하고 다시 시작합니다.
5. **플러그인 디렉터리(Plugins Directory)**에서 `달달 품의 플러그인` 마켓플레이스를 선택한 뒤 **품의 기안 도우미**를 설치합니다.

이 저장소 마켓플레이스의 경로는 `./plugins/pumui-daldal`입니다. 플러그인 폴더만 다른 곳으로 옮기면 마켓플레이스가 찾지 못하므로, 폴더를 옮긴 경우 마켓플레이스 경로도 함께 수정해야 합니다. 로컬 마켓플레이스 메뉴는 앱 버전·계정·실행 화면에 따라 달라질 수 있습니다.

## ChatGPT 워크스페이스에서 GitHub 마켓플레이스 가져오기

워크스페이스 관리자라면 저장소 ZIP을 내려받지 않고 GitHub에서 마켓플레이스를 가져올 수 있습니다.

1. ChatGPT 웹의 **관리자 콘솔(Admin console) → 워크스페이스 선택 → 플러그인(Plugins) → 추가(Add) → 마켓플레이스 가져오기(Import marketplace)**를 선택합니다.
2. **Source**에는 저장소 주소 `https://github.com/yundaldal/gpt-plugins_daldal`를 입력합니다. 저장소 URL만 입력하고 브랜치나 하위 폴더는 붙이지 않습니다.
3. **Path**는 비워 둡니다. 마켓플레이스 파일이 저장소 루트의 `.agents/plugins/marketplace.json`에 있습니다. **Branch**에는 `main`을 입력합니다.
4. GitHub 접근을 승인하고 가져오기 결과를 확인합니다. 이 마켓플레이스에는 두 플러그인이 등록되어 있습니다.

이 방법은 워크스페이스 관리자용입니다. 새 마켓플레이스에는 일일 자동 동기화가 설정될 수 있으며, 동기화는 플러그인 파일을 업데이트하지만 사용자의 외부 앱 계정이나 PC 폴더를 연결하지 않습니다. 개별 플러그인의 설치 정책과 사용 권한은 워크스페이스에서 따로 설정합니다.

## 자료를 올려서 품의 초안 만들기

플러그인을 설치한 뒤 새 대화에서 **품의 기안 도우미**를 선택하고 요청합니다. 예:

> 첨부한 자료로 품의 초안을 준비해 주세요. 유형을 먼저 확인하고, 기관과 회계연도에 단가표가 적용되는지 확인한 뒤, 빠진 항목을 질문하고 계산과 결과를 교차 점검해 주세요.

ChatGPT 웹에서 작업한다면 **그 건의 원본 파일만 대화에 첨부**합니다. 플러그인의 빈 양식·참고 JSON·코드는 ZIP에 들어 있으므로 매번 올릴 필요가 없습니다. PC 폴더를 연결하지 않아도 대화 첨부로 작업할 수 있지만, ChatGPT는 첨부하지 않은 로컬 파일을 볼 수 없습니다. 화면의 파일 첨부 가능 형식과 한도는 계정·워크스페이스 설정에 따릅니다.

이 플러그인은 지침과 리소스를 포함한 skills-only 패키지이며 외부 앱/MCP 연결은 없습니다. ChatGPT 화면이 플러그인에 포함된 로컬 Python 스크립트를 실행할 수 있다고 가정하지 마세요. HWPX·XLSX 산출물을 스크립트로 생성하려면 아래처럼 PC에서 로컬 실행합니다.

## 로컬 실행 및 의존성

Python 3.10 이상과 `requirements.txt`의 패키지가 필요합니다. 저장소를 내려받은 경우 PowerShell에서 플러그인 폴더로 이동한 뒤 실행합니다.

```powershell
Set-Location "<저장소 폴더>\plugins\pumui-daldal"
python -m pip install -r requirements.txt
python .\skills\pumui\scripts\run_case.py "<비공개 작업 폴더>\case.json" "<비공개 작업 폴더>\results" "<비공개 작업 폴더>\input"
```

마지막 `input` 폴더 인자는 선택 사항입니다. 실제 자료와 산출물은 비공개 폴더에 둡니다. 실행기는 입력 `case.json`을 결과 폴더에 복사하지 않지만, 지정한 원본 파일은 별도로 남습니다. 생성 결과는 유형에 따라 HWPX 기안문, 텍스트 미리보기, 수당 또는 물품 엑셀, 예산연결 업로드 엑셀, 준비점검표, 자동 점검 보고서입니다.

`requirements.txt`는 `openpyxl`과 `lxml`을 사용합니다. 자동 점검에서 실패가 나오면 보고서의 항목을 확인하고, 실패가 남은 결과를 완성본으로 사용하지 마세요.

## 검증과 개인정보

전체 GitHub 소스 트리의 `verification/` 폴더에 합성 입력 테스트가 있습니다. 플러그인 전용 ZIP에는 이 테스트 폴더가 들어 있지 않습니다. 저장소 소스를 내려받아 저장소 루트에서 실행합니다.

```powershell
python -X utf8 -m unittest discover -s verification -v
```

검증은 모든 유형을 합성 입력으로 실행하고, 세금 경계값·시간별 수당·원고료 한도와 재활용 구간·누락 및 잘못된 입력의 생성 차단을 확인합니다. 합성 입력은 실제 인명, 기관명, 계좌, 과거 문서를 포함하지 않습니다.

테스트 결과는 ChatGPT 웹 또는 데스크톱에서 플러그인 설치, 스크립트 실행, 파일 전달까지 확인한 결과가 아닙니다. 해당 환경에서 실행 기능을 사용할 수 없다면 위 로컬 실행 방법을 이용하세요. 실제 자료·`case.json`·결과 엑셀은 공개 저장소에 올리지 마세요.

## 공식 안내

- [ChatGPT 플러그인 설치·사용·ZIP 업로드](https://help.openai.com/en/articles/20001256-plugins-in-chatgpt)
- [GitHub 마켓플레이스 가져오기 및 동기화](https://help.openai.com/en/articles/20001504-importing-and-syncing-plugin-marketplaces-from-github)
- [플러그인 패키지와 데스크톱 로컬 마켓플레이스](https://developers.openai.com/plugins/build/plugins)
- [Custom GPT 지식 파일 업로드](https://help.openai.com/en/articles/8554397-creating-and-editing-gpts)

플러그인 원본 및 릴리스 자료: <https://github.com/yundaldal/gpt-plugins_daldal>
