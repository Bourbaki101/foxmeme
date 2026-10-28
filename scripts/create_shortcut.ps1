param(
    [string]$Destination = [Environment]::GetFolderPath('Desktop')
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\pythonw.exe'
$iconPath = Join-Path $projectRoot 'assets\memecam.ico'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'No se encontro el entorno de Python. Sigue la instalacion en README.md.'
}
if (-not (Test-Path -LiteralPath $Destination -PathType Container)) {
    throw "No existe la carpeta de destino: $Destination"
}

$shortcutPath = Join-Path $Destination 'MemeCam.lnk'
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $pythonPath
$shortcut.Arguments = '-m memecam'
$shortcut.WorkingDirectory = $projectRoot
$shortcut.IconLocation = "$iconPath,0"
$shortcut.Description = 'Abrir MemeCam'
$shortcut.Save()
Write-Output "Acceso directo creado: $shortcutPath"
