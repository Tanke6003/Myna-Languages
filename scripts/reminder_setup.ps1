# Activa o desactiva el recordatorio diario de Myna (Tarea Programada de Windows, sin admin).
#   reminder_setup.ps1 -Action enable -Time 19:00
#   reminder_setup.ps1 -Action disable
param(
  [ValidateSet('enable', 'disable')] [string]$Action = 'enable',
  [string]$Time = '19:00'
)
$ErrorActionPreference = 'Stop'
$TaskName = 'MynaReminder'
$vbs = Join-Path $PSScriptRoot 'reminder.vbs'

# Quita la tarea anterior (idempotente) tanto al activar como al desactivar.
try { Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction Stop } catch { }

if ($Action -eq 'disable') { Write-Output 'disabled'; return }

if ($Time -notmatch '^[0-2]?\d:[0-5]\d$') { $Time = '19:00' }
$at = [datetime]::Today.Add([timespan]::Parse($Time))

# Nombres distintos de $Action (el parametro): PowerShell no distingue mayus/minus en variables.
$taskAction = New-ScheduledTaskAction -Execute 'wscript.exe' -Argument ('"' + $vbs + '"')
$trigger    = New-ScheduledTaskTrigger -Daily -At $at
# Que dispare aunque el PC estuviera apagado a esa hora y aunque vaya con bateria.
$settings   = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $TaskName -Action $taskAction -Trigger $trigger -Settings $settings `
  -Description 'Recordatorio diario de practica de Myna' -Force | Out-Null
Write-Output ("enabled " + $Time)
