# 설치 및 사용 안내

이 저장소는 다운로드 가능한 플러그인 패키지를 제공합니다. ZIP 파일을 내려받는 것과 ChatGPT에 설치하는 것은 별도 단계입니다.

## 요금제별 이용 조건

- **무료 계정:** Plugins 디렉터리를 확인하고 플러그인 카드에 `Install plugin`이 표시될 때 설치할 수 있습니다. 디렉터리가 보이더라도 개별 플러그인 설치·사용은 요금제, 지역, 계정과 워크스페이스 설정에 따라 달라집니다. 개인 Skills 기능은 일반적으로 Business·Enterprise·Healthcare·Edu에서 제공되므로, 무료 개인 계정에서 Skills 전용 ZIP이 설치된다고 보장할 수 없습니다.
- **유료 개인 계정:** 같은 방식으로 Plugins 디렉터리에서 설치 가능 여부를 확인합니다. Plus·Pro 등 유료 요금제라는 사실만으로 ZIP 업로드 권한이 생기지는 않습니다. 메뉴가 보이지 않으면 해당 계정의 기능 제공 범위를 확인하세요.
- **Business·Enterprise·Edu 등 워크스페이스:** 워크스페이스 관리자는 플러그인을 사용할 수 있게 설정하고, ZIP 업로드 권한을 부여하거나 GitHub 마켓플레이스를 가져올 수 있습니다. 사용자는 관리자 설정에 따라 설치합니다.

## 개별 ZIP 업로드

1. [저장소의 `downloads/`](downloads/)에서 설치할 플러그인의 ZIP을 내려받습니다.
2. ChatGPT 웹에서 대상 워크스페이스의 **Admin console → Plugins → Add → Upload plugin**을 엽니다.
3. ZIP을 업로드합니다. 이 메뉴는 업로드 권한이 있거나 자격이 되는 워크스페이스 소유자·관리자에게만 제공될 수 있습니다.
4. 업로드는 플러그인을 워크스페이스에 등록하는 단계이며, 사용자별 설치와는 별개입니다. 관리자는 워크스페이스의 플러그인 설정에서 설치 정책을 정합니다.
5. 정책이 **사용 가능(Available)**이면 각 사용자가 ChatGPT의 **플러그인 디렉터리(Plugins)**에서 해당 플러그인을 열고 **플러그인 설치(Install plugin)**를 눌러 별도로 설치합니다. 관리자가 **설치됨(Installed)** 정책을 설정한 경우에는 자격이 있는 사용자에게 자동 설치되므로 설치 목록에서 상태를 확인합니다.

이 플러그인 6종은 Skills 전용이라 외부 계정 연결이나 API 키가 필요하지 않습니다. ZIP 업로드 메뉴가 없으면 관리자에게 권한을 확인하거나 Plugins 디렉터리의 제공 여부를 확인하세요.

## GitHub 마켓플레이스 가져오기

이 방법은 **워크스페이스 관리자**가 사용합니다.

1. ChatGPT **Admin console → 대상 워크스페이스 → Plugins → Add → Import marketplace**로 이동합니다.
2. **Source**에 `https://github.com/yundaldal/gpt-plugins_daldal`를 입력합니다.
3. 마켓플레이스 파일이 저장소 루트의 `.agents/plugins/marketplace.json`에 있으므로 **Path는 비워 둡니다**. 기본 브랜치는 `main`입니다.
4. GitHub 접근을 승인한 뒤 가져오기 결과를 확인하고, 각 플러그인의 워크스페이스 설치 정책을 설정합니다.

GitHub 가져오기는 워크스페이스 구성원에게 자동으로 앱 접근 권한을 주지 않습니다. 이 저장소의 6개 새 플러그인은 외부 앱을 포함하지 않지만, 사용 가능 여부는 워크스페이스 설정을 따릅니다.

## 사용 방법

플러그인을 설치한 뒤 요청에 맞을 때 자동으로 선택될 수 있습니다. 직접 선택하려면 ChatGPT에서 `@`로 플러그인을 부르거나, `+` 메뉴에서 이름을 입력하거나, 작성창의 **플러그인(Plugins)**을 선택하세요. ZIP을 올리기만 한 상태라면 먼저 위의 별도 설치 단계를 마칩니다. 각 플러그인 안내의 예시 문장을 복사해 시작할 수 있습니다.

## ChatGPT 공식 문서

- [Plugins in ChatGPT](https://help.openai.com/en/articles/20001256-plugins-in-chatgpt)
- [GitHub 마켓플레이스 가져오기와 동기화](https://help.openai.com/en/articles/20001504-importing-and-syncing-plugin-marketplaces-from-github)

설치 메뉴와 권한은 ChatGPT 계정·워크스페이스에 따라 다를 수 있으므로, 최신 메뉴는 위 공식 안내에서 확인하세요.
