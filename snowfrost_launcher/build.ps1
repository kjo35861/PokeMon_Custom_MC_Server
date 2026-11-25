param([switch]$IconPreviewBuild, [ValidatePattern('^[A-Za-z0-9_-]+\.exe$')][string]$OutputName)
$ErrorActionPreference = 'Stop'
$launcherRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$launcherCompiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
$launcherFramework = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319'
$launcherWpf = Join-Path $launcherFramework 'WPF'
$launcherFilename = if ($OutputName) { $OutputName } elseif ($IconPreviewBuild) { 'PocketmateLauncher-NewIcon.exe' } else { 'PocketmateLauncher.exe' }
$launcherOutput = Join-Path $launcherRoot ('dist\' + $launcherFilename)
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $launcherOutput) | Out-Null
$launcherArguments = @(
    '/nologo', '/target:winexe', '/platform:x64', '/optimize+', '/codepage:65001',
    ('/win32manifest:' + (Join-Path $launcherRoot 'src\app.manifest')),
    ('/resource:' + (Join-Path $launcherRoot 'assets\launcher.ico') + ',Snowfrost.LauncherIcon.ico'),
    ('/win32icon:' + (Join-Path $launcherRoot 'assets\launcher.ico')),
    ('/out:' + $launcherOutput),
    ('/reference:' + (Join-Path $launcherWpf 'PresentationFramework.dll')),
    ('/reference:' + (Join-Path $launcherWpf 'PresentationCore.dll')),
    ('/reference:' + (Join-Path $launcherWpf 'WindowsBase.dll')),
    ('/reference:' + (Join-Path $launcherFramework 'System.Xaml.dll')),
    ('/reference:' + (Join-Path $launcherFramework 'System.Web.Extensions.dll')),
    ('/reference:' + (Join-Path $launcherFramework 'System.Web.dll')),
    ('/reference:' + (Join-Path $launcherFramework 'System.Net.Http.dll')),
    ('/reference:' + (Join-Path $launcherFramework 'System.Security.dll')),
    ('/reference:' + (Join-Path $launcherFramework 'System.Management.dll')),
    ('/reference:' + (Join-Path $launcherFramework 'System.IO.Compression.dll')),
    ('/reference:' + (Join-Path $launcherFramework 'System.IO.Compression.FileSystem.dll')),
    ('/resource:' + (Join-Path $launcherRoot 'src\MainWindow.xaml') + ',Snowfrost.MainWindow.xaml'),
    ('/resource:' + (Join-Path $launcherRoot 'assets\mountain-lake.png') + ',Snowfrost.Background.png'),
    (Join-Path $launcherRoot 'src\Launcher.cs'),
    (Join-Path $launcherRoot 'src\Services.cs'),
    (Join-Path $launcherRoot 'src\Authentication.cs'),
    (Join-Path $launcherRoot 'src\GameInstaller.cs'),
    (Join-Path $launcherRoot 'src\PrismBridge.cs'),
    (Join-Path $launcherRoot 'src\BackendTests.cs')
)
& $launcherCompiler @launcherArguments
if ($LASTEXITCODE -ne 0) { throw 'Launcher compilation failed.' }
# Keep the previously delivered download path working with the updated brand.
if (-not $IconPreviewBuild -and -not $OutputName) { Copy-Item -LiteralPath $launcherOutput -Destination (Join-Path $launcherRoot 'dist\SnowfrostLauncher.exe') -Force }
if (-not (Test-Path -LiteralPath (Join-Path $launcherRoot 'dist\launcher-config.json'))) { Copy-Item -LiteralPath (Join-Path $launcherRoot 'launcher-config.json') -Destination (Join-Path $launcherRoot 'dist\launcher-config.json') }
Copy-Item -LiteralPath (Join-Path $launcherRoot '로그인 연결 안내.txt') -Destination (Join-Path $launcherRoot 'dist\로그인 연결 안내.txt') -Force
Get-Item -LiteralPath $launcherOutput | Select-Object FullName,Length,LastWriteTime

if (-not (Test-Path (Join-Path $launcherRoot 'dist\notices.json'))) { Copy-Item (Join-Path $launcherRoot 'notices.json') (Join-Path $launcherRoot 'dist\notices.json') }
