; Nexus - instalador Windows (Inno Setup 6).
;
; COMO USAR:
;   1. Gere a pasta da release:  installer\build_release.bat
;      (PyInstaller -> release\Nexus\ com Nexus.exe, nexus_browser.exe,
;      assets\, logo_nexus\, games\, streaming_images\ gerados)
;   2. Compile aqui:  iscc installer\nexus.iss
;      (saida em dist\Nexus-5.7.0-setup.exe)
;
; COMPATIVEL COM O AUTO-UPDATE: o app baixa Nexus-vX.X.X-windows.zip e
; expande por cima do install_dir, entao o .exe continua no mesmo lugar
; e os atalhos abaixo seguem validos. Instalacao por usuario (sem admin).
; settings.json/nexus.db sao criados no 1o uso: NAO vao no instalador.

#define MyAppName "Nexus"
#define MyAppVersion "5.7.0"
#define MyAppPublisher "Nexus"
#define MyAppURL "https://github.com/ryanvidallima2/nexus-big-picture"
#define MyAppExeName "Nexus.exe"

[Setup]
AppId={{C7A4E2B1-5F3D-4A8C-9E1F-2B6D0A4C8E10}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\{#MyAppName}
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename={#MyAppName}-{#MyAppVersion}-setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\release\Nexus\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
