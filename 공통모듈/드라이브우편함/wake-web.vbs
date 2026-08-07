' One-key wake for the web Claude (회신03 §1).
' Double-click me: if WAKE.md says WEB_NEEDED, this focuses the Claude window,
' pastes a wake message and presses Enter. Otherwise it silently does nothing.
'
' Optional hotkey: copy a shortcut of this file to the Desktop and set a
' shortcut key in its Properties (e.g. Ctrl+Alt+W). Hotkeys only work on
' Desktop / Start Menu shortcuts, so the user must place it there.
'
' ASCII-only comments on purpose (VBScript reads .vbs as ANSI).

Dim sh, fso, here
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
here = fso.GetParentFolderName(WScript.ScriptFullName)

sh.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & _
  here & "\scripts\wake-web.ps1""", 0, False
