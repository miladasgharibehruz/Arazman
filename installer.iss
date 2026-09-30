#ifndef AppVersion
#define AppVersion "1.1"
#endif
[Setup]
AppId={{A39A4D47-CA4A-40FA-B1CF-0E36EA4529AF}
AppName=Arazman
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\Arazman
DefaultGroupName=Arazman
PrivilegesRequired=lowest
OutputDir=output
OutputBaseFilename=Arazman-Setup
SetupIconFile=icons\arazman-app.ico
UninstallDisplayIcon={app}\Arazman.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UsePreviousAppDir=yes
CloseApplications=no
RestartApplications=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
[Files]
Source: "dist\Arazman\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\Arazman"; Filename: "{app}\Arazman.exe"
Name: "{autodesktop}\Arazman"; Filename: "{app}\Arazman.exe"
[Run]
Filename: "{app}\Arazman.exe"; Description: "Launch Arazman"; Flags: nowait postinstall skipifsilent
