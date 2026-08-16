' Cria o atalho "IRIS" na Area de Trabalho do usuario atual, apontando pra
' iniciar_iris_oculto.vbs NESTA MESMA PASTA - onde quer que o projeto tenha sido
' clonado (usa WshShell.SpecialFolders("Desktop"), que ja resolve certo mesmo com a
' Area de Trabalho redirecionada pro OneDrive). Roda uma vez so, depois de clonar o
' repositorio - da pra rodar de novo sem problema (so sobrescreve o atalho).

Set oWshShell = CreateObject("WScript.Shell")
Set oFso = CreateObject("Scripting.FileSystemObject")

strPastaAtual = oFso.GetParentFolderName(WScript.ScriptFullName)
strDesktop = oWshShell.SpecialFolders("Desktop")

Set oAtalho = oWshShell.CreateShortcut(strDesktop & "\IRIS.lnk")
oAtalho.TargetPath = strPastaAtual & "\iniciar_iris_oculto.vbs"
oAtalho.WorkingDirectory = strPastaAtual
oAtalho.Description = "Iniciar IRIS (launcher radial)"

strIcone = strPastaAtual & "\assets\iris.ico"
If oFso.FileExists(strIcone) Then
    oAtalho.IconLocation = strIcone
End If

oAtalho.Save

MsgBox "Atalho ""IRIS"" criado na sua Area de Trabalho!", vbInformation, "IRIS"
