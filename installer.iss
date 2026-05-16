; ============================================================
;  싹싹번역 - Inno Setup 설치 마법사 스크립트
;
;  사용법:
;    1) https://jrsoftware.org/isinfo.php 에서 Inno Setup 설치
;    2) 먼저 build_exe.bat 을 실행해 dist\SsakSsak\ 가 만들어진 상태여야 함
;    3) 이 파일(installer.iss)을 Inno Setup Compiler로 열고 [Compile] 클릭
;    4) Output\SsakSsak-Setup-x.x.x.exe 가 생성됨 → GitHub Release에 업로드
; ============================================================

; UI 표시명: 한글 "싹싹번역"
; 내부 패키지/exe 식별자: ASCII "SsakSsak"
#define MyAppName "싹싹번역"
#define MyAppPackageName "SsakSsak"
; CI에서 ISCC /DMyAppVersion=1.2.3 으로 덮어쓸 수 있도록 ifndef 로 가드
#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif
#define MyAppPublisher "seoyeon59"
#define MyAppURL "https://github.com/seoyeon59/SsakSsak"
#define MyAppExeName "SsakSsak.exe"

[Setup]
; ── 식별자 (배포 후엔 절대 바꾸지 마세요. 업그레이드 인식에 사용됨) ──
AppId={{A8F1E3D7-5B9C-4F2A-9D6E-7C1B3A8E2F4D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases

; ── 기본 설치 경로: 사용자별 (관리자 권한 불필요)
;    경로는 ASCII(SsakSsak)로 두어 비유니코드 도구와의 호환성을 확보
DefaultDirName={localappdata}\Programs\{#MyAppPackageName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; ── 출력 ──
OutputDir=Output
OutputBaseFilename=싹싹번역-Setup-{#MyAppVersion}
SetupIconFile=icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

; ── UI 언어 ──
ShowLanguageDialog=auto

; ── 라이선스/정보 페이지 ──
; LicenseFile=LICENSE.txt   ; LICENSE.txt 추가 시 주석 해제
; InfoBeforeFile=README_KR.txt

; ── 최소 OS ──
MinVersion=10.0   ; Windows 10+

; ── 압축 해제 후 사이즈 ──
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} {#MyAppVersion}

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1

[Files]
; ── PyInstaller --onedir 결과물 전체를 설치 폴더로 복사 ──
Source: "dist\{#MyAppPackageName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
; ── 설치 직후 바로 실행할지 묻기 ──
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; ── 사용자 데이터(글로사리, 캐시 등)는 보존하지 않고 같이 삭제할 항목 ──
; user_glossary.json은 사용자가 만든 데이터라 일부러 남깁니다.
; 필요 시 아래 주석 해제:
; Type: files; Name: "{app}\user_glossary.json"
