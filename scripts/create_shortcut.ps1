param(
    [string]$Destination = [Environment]::GetFolderPath('Desktop'),
    [string]$ExecutablePath
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if ($ExecutablePath) {
    $targetPath = (Resolve-Path -LiteralPath $ExecutablePath -ErrorAction Stop).Path
    if (-not (Test-Path -LiteralPath $targetPath -PathType Leaf) -or
        [IO.Path]::GetExtension($targetPath) -ine '.exe') {
        throw 'ExecutablePath debe apuntar al archivo MemeCam.exe generado.'
    }
    $workingDirectory = Split-Path -Parent $targetPath
    $iconPath = $targetPath
    $arguments = ''
} else {
    $targetPath = Join-Path $projectRoot '.venv\Scripts\pythonw.exe'
    $workingDirectory = $projectRoot
    $iconPath = Join-Path $projectRoot 'assets\memecam.ico'
    $arguments = '-m memecam'
    if (-not (Test-Path -LiteralPath $targetPath -PathType Leaf)) {
        throw 'No se encontro el entorno de Python. Sigue la instalacion en README.md.'
    }
}
if (-not (Test-Path -LiteralPath $Destination -PathType Container)) {
    throw "No existe la carpeta de destino: $Destination"
}

$shortcutPath = Join-Path $Destination 'MemeCam.lnk'
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $targetPath
$shortcut.Arguments = $arguments
$shortcut.WorkingDirectory = $workingDirectory
$shortcut.IconLocation = "$iconPath,0"
$shortcut.Description = 'Abrir MemeCam'
$shortcut.Save()
Write-Output "Acceso directo creado: $shortcutPath"
