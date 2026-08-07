' Launches watcher.mjs in the background with no console window.
' Called by the Startup-folder shortcut at logon, and can be double-clicked anytime.
'
' Duplicate-run guard: reads the PID from WATCHER_HEARTBEAT.md and checks whether
' that process is actually alive. A timestamp check is not enough -- a freshly
' killed watcher leaves a recent heartbeat behind and the relaunch gets skipped.
'
' To stop: end node.exe in Task Manager.
'
' NOTE: comments are English on purpose. This file must stay pure ASCII --
' VBScript reads .vbs as ANSI, so UTF-8 Korean comments corrupt the parser.
' Korean explanation lives in CLAUDE.md instead.

Option Explicit

Const NODE_EXE = "C:\Program Files\nodejs\node.exe"

Dim sh, fso, here, hb, alive, pid, line, ts, wmi, procs

Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

here = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = here

hb = here & "\WATCHER_HEARTBEAT.md"
alive = False
pid = 0

' Parse "PID: 12345" from the heartbeat file
If fso.FileExists(hb) Then
  Dim f, txt
  Set f = fso.OpenTextFile(hb, 1)
  Do While Not f.AtEndOfStream
    line = f.ReadLine
    If Left(line, 4) = "PID:" Then
      pid = CLng(Trim(Mid(line, 5)))
    End If
  Loop
  f.Close
End If

' Is that PID a living node.exe?
If pid > 0 Then
  On Error Resume Next
  Set wmi = GetObject("winmgmts:\\.\root\cimv2")
  Set procs = wmi.ExecQuery("SELECT Name FROM Win32_Process WHERE ProcessId = " & pid)
  If Err.Number = 0 Then
    Dim p
    For Each p In procs
      If LCase(p.Name) = "node.exe" Then alive = True
    Next
  End If
  On Error GoTo 0
End If

If Not alive Then
  ' 0 = hidden window, False = do not wait for it to finish
  sh.Run """" & NODE_EXE & """ """ & here & "\watcher.mjs""", 0, False
End If
