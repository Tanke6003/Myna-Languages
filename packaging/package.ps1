# Crea un paquete distribuible (ZIP) para copiar a otra PC.
# Incluye el frontend ya compilado; NO incluye venv ni node_modules.
# Se ejecuta desde packaging/ pero opera sobre la raíz del proyecto.
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

$out = ".\dist_package"
$stage = "$out\Myna"
Remove-Item $out -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $stage | Out-Null

Write-Host "Compilando el frontend..."
Push-Location frontend
npm install
npm run build
Pop-Location

Write-Host "Copiando archivos..."
$items = @('backend', 'services', 'config.py', 'requirements.txt',
           'install.ps1', 'run.ps1', 'Instalar.bat', 'Abrir Myna.bat',
           'install.sh', 'run.sh', 'README.md', 'myna.ico')
foreach ($i in $items) { Copy-Item $i -Destination $stage -Recurse -Force }
New-Item -ItemType Directory -Force "$stage\frontend" | Out-Null
Copy-Item 'frontend\dist' -Destination "$stage\frontend\dist" -Recurse -Force

# Limpia cachés de Python del paquete
Get-ChildItem $stage -Recurse -Directory -Filter '__pycache__' | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Compress-Archive -Path "$stage\*" -DestinationPath "$out\Myna.zip" -Force
Write-Host ""
Write-Host "Paquete listo: $out\Myna.zip" -ForegroundColor Green
Write-Host "En la otra PC: descomprime y ejecuta Instalar.bat" -ForegroundColor Green
