; Inno Setup installer for Plant Automation.
; The application remains portable internally, while this installer provides
; a normal one-click Windows installation and Start Menu/Desktop shortcuts.
#define AppName "Plant Automation"
#define AppVersion "0.1.0"
#define AppPublisher "Plant Automation"
#define AppExeName "Plant Automation.exe"
#define AppSourceDir "..\dist\Plant Automation"
#define AppOutputDir "..\release"

[Setup]
AppId={{A5B1B9B7-9F89-4C68-8D01-1A2B3C4D5E6F}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir={#AppOutputDir}
OutputBaseFilename=Plant-Automation-Windows-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#AppExeName}
; Add a version marker for support diagnostics.
VersionInfoDescription={#AppName} installer
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}

[Files]
Source: "{#AppSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\docs\HUONG_DAN_SU_DUNG.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\docs\GHI_CHU_PHAT_HANH.md"; DestDir: "{app}\docs"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Mở {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
