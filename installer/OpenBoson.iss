; OpenBoson Windows installer (Inno Setup 6)
; Per-user install under %LocalAppData%\Programs\OpenBoson
; Preserves %USERPROFILE%\.openboson across upgrades.

#define MyAppName "OpenBoson"
#ifndef MyAppVersion
  #define MyAppVersion "0.4.1"
#endif
#define MyAppPublisher "OpenBoson contributors"
#define MyAppURL "https://github.com/Elshayib/OpenBoson"
#define MyAppExeName "OpenBoson.exe"

[Setup]
AppId={{A7C3E9F1-2B4D-4E8A-9C1F-6D5B0A8E3F21}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist\installer
OutputBaseFilename=OpenBoson-Setup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=yes
CloseApplicationsFilter=OpenBoson.exe
RestartApplications=no
ArchitecturesInstallIn64BitMode=x64compatible
InfoBeforeFile=..\SUPPORT.md
LicenseFile=..\LICENSE

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Application files from PyInstaller onedir build. Never touch user data under ~/.openboson.
Source: "..\dist\OpenBoson\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;
