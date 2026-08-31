; Inno Setup script – builds VintedAutoListingTool-Setup.exe
; Requires Inno Setup 6 (https://jrsoftware.org/isdl.php) and a finished
; PyInstaller build in packaging\dist\VintedAutoListingTool\.

#define AppName "Vinted Auto Listing Tool"
#define AppVersion "2.0.0"
#define AppExeName "VintedAutoListingTool.exe"
#define AppPublisher "Vinted Auto Listing Tool"

[Setup]
AppId={{8C2F4E51-9F4B-4B4E-9F0A-4C3E7B2D51A2}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\VintedAutoListingTool
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..\installer_output
OutputBaseFilename=VintedAutoListingTool-Setup
SetupIconFile=..\src\vinted_tool\assets\app.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\{#AppExeName}

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\packaging\dist\VintedAutoListingTool\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\.env.example"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Anwendungsdaten (Datenbank, Bilder, Logs) bleiben bewusst erhalten und liegen
; unter %APPDATA%\VintedAutoListingTool. Sie können dort manuell gelöscht werden.
Type: filesandordirs; Name: "{app}\_internal\__pycache__"
