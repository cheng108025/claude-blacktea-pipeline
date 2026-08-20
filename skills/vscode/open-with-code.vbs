' Open with VS Code; \\wsl.localhost\ and \\wsl$\ paths connect to WSL directly.
Option Explicit
Dim sh, code, arg, re, m, distro, rest
Set sh = CreateObject("WScript.Shell")
code = """C:\Users\peter\AppData\Local\Programs\Microsoft VS Code\Code.exe"""
If WScript.Arguments.Count = 0 Then
  sh.Run code, 1, False
  WScript.Quit 0
End If
arg = WScript.Arguments(0)
Set re = New RegExp
re.Pattern = "^\\\\wsl(\.localhost|\$)\\([^\\]+)(\\.*)?$"
re.IgnoreCase = True
If re.Test(arg) Then
  Set m = re.Execute(arg)(0)
  distro = m.SubMatches(1)
  rest = m.SubMatches(2)
  If rest = "" Then rest = "\"
  rest = Replace(rest, "\", "/")
  sh.Run code & " --remote wsl+" & distro & " """ & rest & """", 1, False
Else
  sh.Run code & " """ & arg & """", 1, False
End If
