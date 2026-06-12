' Lanza Myna SIN mostrar ninguna ventana de terminal.
' (En el primer arranque, run.ps1 abre por su cuenta una ventana visible para la instalacion.)
Dim sh, dir
Set sh = CreateObject("WScript.Shell")
dir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
sh.CurrentDirectory = dir
' 0 = ventana oculta ; False = no esperar
sh.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & dir & "run.ps1""", 0, False
