; Hikvision Time-Lapse Client Windows 安装程序

#define MyAppName "Hikvision Time-Lapse Client"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Hikvision Time-Lapse Client"
#define MyAppExeName "HikvisionTimeLapse.exe"

[Setup]
AppId={{A2AC26F8-70D8-4A7C-9F4B-5F4E4F47C1A1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\Hikvision Time-Lapse Client
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist\installer
OutputBaseFilename=HikvisionTimeLapse-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加快捷方式:"; Flags: unchecked
Name: "startup"; Description: "登录 Windows 后自动启动"; GroupDescription: "运行选项:"; Flags: unchecked

[Files]
Source: "..\dist\HikvisionTimeLapse\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\dist\VideoMaker_Test\*"; DestDir: "{app}\VideoMaker_Test"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "HikvisionTimeLapse"; ValueData: """{app}\{#MyAppExeName}"""; Tasks: startup; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent
