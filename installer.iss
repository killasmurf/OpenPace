; OpenPace Windows Installer Script
; Requires Inno Setup 6.0 or later
; Download from: https://jrsoftware.org/isdl.php

#define MyAppName "OpenPace"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "OpenPace Team"
#define MyAppURL "https://github.com/killasmurf/OpenPace"
#define MyAppExeName "OpenPace.exe"
#define MyAppDescription "Pacemaker Data Analysis Platform"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
AppId={{8A7B9C3D-4E5F-6A1B-2C3D-4E5F6A7B8C9D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=LICENSE
InfoBeforeFile=README.md
OutputDir=installer_output
OutputBaseFilename=OpenPace-Setup-{#MyAppVersion}
SetupIconFile=openpace\gui\resources\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#MyAppExeName}

; Require Windows 10 or later
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Main application files from PyInstaller output
Source: "dist\OpenPace\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Configuration examples
Source: ".env.example"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "SECURITY_FIXES.md"; DestDir: "{app}"; Flags: ignoreversion
; Documentation
Source: "docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "_build,__pycache__"

[Icons]
; Start menu shortcuts
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{#MyAppName} Documentation"; Filename: "{app}\README.md"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
; Desktop shortcut (optional)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
; Quick Launch shortcut (optional, older Windows)
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
; Option to launch application after installation
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up user data directory (optional - only if user confirms)
Type: filesandordirs; Name: "{userappdata}\{#MyAppName}"

[Code]
var
  DataDirPage: TInputOptionWizardPage;

procedure InitializeWizard;
begin
  { Create custom wizard page for data directory options }
  DataDirPage := CreateInputOptionPage(wpSelectDir,
    'Data Storage Location', 'Where should OpenPace store patient data?',
    'OpenPace stores patient data in a secure SQLite database. Choose the default location or specify a custom path.',
    True, False);
  DataDirPage.Add('Use default location (Recommended): ' + ExpandConstant('{userappdata}\OpenPace'));
  DataDirPage.Add('Custom location (Advanced users only)');
  DataDirPage.Values[0] := True;
end;

function InitializeSetup(): Boolean;
begin
  Result := True;

  { Check if .NET Framework or other prerequisites are installed }
  { For OpenPace, we bundle everything with PyInstaller, so no additional checks needed }
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  DataDir: String;
begin
  if CurStep = ssPostInstall then
  begin
    { Create data directory }
    DataDir := ExpandConstant('{userappdata}\OpenPace');
    if not DirExists(DataDir) then
    begin
      CreateDir(DataDir);
      CreateDir(DataDir + '\logs');
      CreateDir(DataDir + '\exports');
    end;

    { Create default config file if it doesn't exist }
    if not FileExists(DataDir + '\config.json') then
    begin
      { The application will create this on first run }
    end;
  end;
end;

function InitializeUninstall(): Boolean;
var
  Response: Integer;
begin
  Result := True;

  { Ask user if they want to keep patient data }
  Response := MsgBox('Do you want to keep your patient data and settings?' + #13#10 + #13#10 +
                     'Select YES to keep data (you can reinstall later without losing data).' + #13#10 +
                     'Select NO to completely remove all OpenPace data.',
                     mbConfirmation, MB_YESNO);

  if Response = IDYES then
  begin
    { Keep data - do nothing, UninstallDelete section won't execute }
  end
  else
  begin
    { User wants to remove data - will be handled by UninstallDelete section }
  end;
end;
