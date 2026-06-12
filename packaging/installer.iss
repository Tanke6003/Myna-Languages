; Asistente de instalación (.exe) para Myna — Inno Setup.
; Compilar:  ISCC.exe packaging\installer.iss   ->   dist_installer\Myna-Setup.exe
; Las rutas son relativas a la RAIZ del proyecto (SourceDir=..).

#define AppName "Myna"

[Setup]
AppName={#AppName}
AppVersion=1.0
AppPublisher=Local
DefaultDirName={localappdata}\Myna
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
SourceDir=..
OutputDir=dist_installer
OutputBaseFilename=Myna-Setup
SetupIconFile=myna.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "dist_package\Myna\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{userprograms}\{#AppName}"; Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\run.ps1"""; \
  WorkingDir: "{app}"; IconFilename: "{app}\myna.ico"
Name: "{userdesktop}\{#AppName}"; Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\run.ps1"""; \
  WorkingDir: "{app}"; IconFilename: "{app}\myna.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[Run]
Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\run.ps1"""; \
  WorkingDir: "{app}"; \
  Description: "Abrir Myna ahora (instalara lo necesario la primera vez)"; \
  Flags: postinstall nowait skipifsilent
