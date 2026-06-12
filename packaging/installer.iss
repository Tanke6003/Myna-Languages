; Asistente de instalación (.exe) para Myna — Inno Setup.
; Compilar:  ISCC.exe packaging\installer.iss   ->   dist_installer\Myna-Setup.exe
; Las rutas son relativas a la RAIZ del proyecto (SourceDir=..).

#define AppName "Myna"
; Version: fuente UNICA de verdad en el fichero VERSION de la raiz del proyecto.
; Asi instalador, backend y UI muestran siempre el mismo numero (se cambia en un solo sitio).
#define AppVersion Trim(FileRead(FileOpen(SourcePath + "..\VERSION")))

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Local
DefaultDirName={localappdata}\Myna
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
SourceDir=..
OutputDir=dist_installer
; El .exe lleva nombre + version, p. ej. Myna-Setup-1.3.0.exe
OutputBaseFilename={#AppName}-Setup-{#AppVersion}
SetupIconFile=myna.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "dist_package\Myna\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{userprograms}\{#AppName}"; Filename: "wscript.exe"; \
  Parameters: """{app}\Myna.vbs"""; \
  WorkingDir: "{app}"; IconFilename: "{app}\myna.ico"
Name: "{userdesktop}\{#AppName}"; Filename: "wscript.exe"; \
  Parameters: """{app}\Myna.vbs"""; \
  WorkingDir: "{app}"; IconFilename: "{app}\myna.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[Run]
Filename: "wscript.exe"; \
  Parameters: """{app}\Myna.vbs"""; \
  WorkingDir: "{app}"; \
  Description: "Abrir Myna ahora (instalara lo necesario la primera vez)"; \
  Flags: postinstall nowait skipifsilent

[UninstallRun]
; Al desinstalar, quita la Tarea Programada del recordatorio (si existe).
Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\scripts\reminder_setup.ps1"" -Action disable"; \
  Flags: runhidden; RunOnceId: "MynaReminderOff"
