' Lanza el recordatorio de Myna SIN mostrar ninguna ventana (lo invoca la Tarea Programada).
Dim sh, dir
Set sh = CreateObject("WScript.Shell")
dir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
sh.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & dir & "reminder.ps1""", 0, False
