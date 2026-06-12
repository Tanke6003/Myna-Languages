# Muestra el recordatorio de Myna como notificacion (toast) de Windows.
# Al hacer clic, abre Myna (via el protocolo myna:). Lo dispara la Tarea Programada
# (ver reminder_setup.ps1). Es idempotente: registra lo que haga falta en cada ejecucion.
param([string]$Message = "")
$ErrorActionPreference = 'SilentlyContinue'

$root  = Split-Path $PSScriptRoot -Parent
$vbs   = Join-Path $root 'Myna.vbs'
$ico   = Join-Path $root 'myna.ico'
$AUMID = 'Myna.Tutor'

if (-not $Message) {
  $Message = @(
    "Unos minutos hoy y suenas mas nativo. Vamos con una conversacion.",
    "Hora de practicar ingles. Tu racha te esta esperando.",
    "Un ejercicio rapido cuenta: abre Myna y practica.",
    "Manten tu ingles afilado: dedicale 5 minutos ahora."
  ) | Get-Random
}
# Escapa lo minimo para el XML del toast.
$Message = $Message -replace '&', '&amp;' -replace '<', '&lt;' -replace '>', '&gt;'

# 1) Identidad de la app para el toast (nombre + icono) -> sale como "Myna", no "PowerShell".
$key = "HKCU:\Software\Classes\AppUserModelId\$AUMID"
New-Item -Path $key -Force | Out-Null
Set-ItemProperty -Path $key -Name 'DisplayName' -Value 'Myna'
if (Test-Path $ico) { Set-ItemProperty -Path $key -Name 'IconUri' -Value $ico }

# 2) Protocolo myna: -> abre la app al hacer clic (HKCU, sin admin).
if (Test-Path $vbs) {
  $proto = 'HKCU:\Software\Classes\myna'
  New-Item -Path "$proto\shell\open\command" -Force | Out-Null
  Set-ItemProperty -Path $proto -Name '(default)' -Value 'URL:Myna'
  Set-ItemProperty -Path $proto -Name 'URL Protocol' -Value ''
  Set-ItemProperty -Path "$proto\shell\open\command" -Name '(default)' -Value ('wscript.exe "' + $vbs + '"')
}

# 3) Mostrar el toast.
try {
  $null = [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]
  $null = [Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications, ContentType = WindowsRuntime]
  $null = [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, ContentType = WindowsRuntime]
  $template = @"
<toast activationType="protocol" launch="myna:">
  <visual><binding template="ToastGeneric">
    <text>Practica ingles con Myna</text>
    <text>$Message</text>
  </binding></visual>
  <actions>
    <action content="Abrir Myna" activationType="protocol" arguments="myna:" />
    <action content="Mas tarde" activationType="system" arguments="dismiss" />
  </actions>
</toast>
"@
  $doc = [Windows.Data.Xml.Dom.XmlDocument]::new()
  $doc.LoadXml($template)
  $toast = [Windows.UI.Notifications.ToastNotification]::new($doc)
  [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($AUMID).Show($toast)
} catch { }
