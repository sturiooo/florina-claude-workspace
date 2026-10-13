# install.ps1: instalacja srodowiska Claude Code dla sklepu Florina (Windows 10/11)
#
# Uruchom w folderze projektu (tam, gdzie jest ten plik), w zwyklym PowerShell (nie trzeba administratora):
#   powershell -ExecutionPolicy Bypass -File .\install.ps1
#
# Skrypt mozna uruchamiac wiele razy: pomija to, co juz jest zainstalowane.
# Opcje:
#   -BezGitHubCli     nie instaluj GitHub CLI (gh)
#   -BezRozszerzenia  nie instaluj rozszerzenia Claude Code w VS Code

param(
  [switch]$BezGitHubCli,
  [switch]$BezRozszerzenia
)

$ErrorActionPreference = "Continue"
$Projekt = $PSScriptRoot
Set-Location $Projekt
$Problemy = New-Object System.Collections.ArrayList

function Krok($t)  { Write-Host "`n=== $t ===" -ForegroundColor Cyan }
function Ok($t)    { Write-Host "[OK]  $t" -ForegroundColor Green }
function Info($t)  { Write-Host "[..]  $t" }
function Uwaga($t) { Write-Host "[!!]  $t" -ForegroundColor Yellow; [void]$Problemy.Add($t) }

function Odswiez-Path {
  $m = [Environment]::GetEnvironmentVariable("Path", "Machine")
  $u = [Environment]::GetEnvironmentVariable("Path", "User")
  $env:Path = "$m;$u;$env:USERPROFILE\.local\bin;$env:APPDATA\npm"
}

function Jest($cmd) {
  $c = Get-Command $cmd -ErrorAction SilentlyContinue
  if ($null -eq $c) { return $false }
  # alias Microsoft Store dla pythona to nie jest prawdziwy Python
  if ($c.Source -like "*\WindowsApps\*") { return $false }
  return $true
}

function Winget-Zainstaluj($id, $nazwa) {
  $lista = winget list --id $id -e --accept-source-agreements 2>$null | Out-String
  if ($lista -match [regex]::Escape($id)) { Ok "$nazwa juz jest"; return }
  Info "Instaluje $nazwa (moze pojawic sie okno zgody Windows)..."
  winget install --id $id -e --silent --accept-package-agreements --accept-source-agreements
  if ($LASTEXITCODE -ne 0) { Uwaga "Instalacja $nazwa zwrocila kod $LASTEXITCODE. Sprobuj recznie: winget install --id $id -e" }
  else { Ok "$nazwa zainstalowany" }
}

Write-Host "Instalacja srodowiska Claude Code: sklep Florina" -ForegroundColor White
Write-Host "Folder projektu: $Projekt"

# ---------------------------------------------------------------------------
Krok "1/8 Sprawdzam winget (instalator programow Windows)"
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
  Write-Host "Brak winget. Zainstaluj 'Instalator aplikacji' (App Installer) ze sklepu Microsoft Store i uruchom skrypt ponownie." -ForegroundColor Red
  exit 1
}
Ok "winget jest"

# ---------------------------------------------------------------------------
Krok "2/8 Programy bazowe: Git, Node.js LTS, Python 3"
Winget-Zainstaluj "Git.Git" "Git"
Winget-Zainstaluj "OpenJS.NodeJS.LTS" "Node.js LTS"
Odswiez-Path
if (Jest "python") { Ok "Python juz jest ($(python --version 2>&1))" }
else { Winget-Zainstaluj "Python.Python.3.12" "Python 3.12" }
if (-not $BezGitHubCli) { Winget-Zainstaluj "GitHub.cli" "GitHub CLI" }
Odswiez-Path

if (-not (Jest "python")) {
  Uwaga "Komenda 'python' nie dziala. Zamknij to okno, otworz nowe PowerShell i uruchom skrypt ponownie. Jesli nadal: Ustawienia > Aplikacje > Aliasy wykonywania aplikacji > wylacz python.exe i python3.exe."
}
if (-not (Jest "node")) { Uwaga "Komenda 'node' nie dziala. Otworz nowe okno PowerShell i uruchom skrypt ponownie." }

# ---------------------------------------------------------------------------
Krok "3/8 Shopify CLI"
if (Jest "shopify") { Ok "Shopify CLI juz jest ($(shopify version 2>$null))" }
elseif (Jest "npm") {
  Info "Instaluje Shopify CLI (npm install -g @shopify/cli)..."
  npm install -g @shopify/cli@latest
  Odswiez-Path
  if (Jest "shopify") { Ok "Shopify CLI zainstalowany ($(shopify version 2>$null))" } else { Uwaga "Shopify CLI nie odpowiada po instalacji. Otworz nowe okno i sprawdz: shopify version" }
}
else { Uwaga "Brak npm (Node.js). Shopify CLI nie zostal zainstalowany." }

# ---------------------------------------------------------------------------
Krok "4/8 Claude Code (instalator natywny Anthropic)"
if (Jest "claude") { Ok "Claude Code juz jest ($(claude --version 2>$null))" }
else {
  Info "Instaluje Claude Code (irm https://claude.ai/install.ps1 | iex)..."
  try { Invoke-RestMethod https://claude.ai/install.ps1 | Invoke-Expression } catch { Uwaga "Instalator Claude Code zglosil blad: $($_.Exception.Message)" }
  Odswiez-Path
  if (-not (Jest "claude")) {
    Info "Zapasowo: winget install Anthropic.ClaudeCode"
    Winget-Zainstaluj "Anthropic.ClaudeCode" "Claude Code"
    Odswiez-Path
  }
  if (Jest "claude") { Ok "Claude Code zainstalowany ($(claude --version 2>$null))" } else { Uwaga "Claude Code nie odpowiada. Otworz nowe okno i sprawdz: claude --version" }
}
# katalog instalatora natywnego na stale w PATH uzytkownika
$lokalnyBin = "$env:USERPROFILE\.local\bin"
$pathUz = [Environment]::GetEnvironmentVariable("Path", "User")
if ((Test-Path $lokalnyBin) -and ($pathUz -notlike "*$lokalnyBin*")) {
  [Environment]::SetEnvironmentVariable("Path", "$pathUz;$lokalnyBin", "User")
  Ok "Dodano $lokalnyBin do PATH uzytkownika"
}

# ---------------------------------------------------------------------------
Krok "5/8 Rozszerzenie Claude Code w VS Code"
if ($BezRozszerzenia) { Info "Pominiete (-BezRozszerzenia)" }
else {
  $code = (Get-Command code -ErrorAction SilentlyContinue).Source
  if (-not $code) {
    foreach ($k in @("$env:LOCALAPPDATA\Programs\Microsoft VS Code\bin\code.cmd", "$env:ProgramFiles\Microsoft VS Code\bin\code.cmd")) {
      if (Test-Path $k) { $code = $k; break }
    }
  }
  if (-not $code) { Uwaga "Nie znaleziono VS Code. Zainstaluj VS Code i uruchom skrypt ponownie (albo zainstaluj rozszerzenie 'Claude Code' recznie)." }
  else {
    $rozszerzenia = & $code --list-extensions 2>$null | Out-String
    if ($rozszerzenia -match "anthropic.claude-code") { Ok "Rozszerzenie Claude Code juz jest" }
    else {
      & $code --install-extension anthropic.claude-code --force | Out-Null
      Ok "Rozszerzenie Claude Code zainstalowane"
    }
  }
}

# ---------------------------------------------------------------------------
Krok "6/8 Pliki projektu (.env i katalogi robocze)"
if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  Ok "Utworzono .env z .env.example (uzupelnij BASELINKER_TOKEN, patrz INSTALACJA.md krok 7)"
} else { Ok ".env juz jest (nie nadpisuje)" }
foreach ($k in @("backup", "raporty", "robocze", "robocze\media", "robocze\opisy", "robocze\faq", "dziennik", "docs")) {
  if (-not (Test-Path $k)) { New-Item -ItemType Directory -Path $k | Out-Null }
}
Ok "Katalogi: backup, raporty, robocze, dziennik, docs"

# ---------------------------------------------------------------------------
Krok "7/8 Test zabezpieczen (straznik zmian)"
if (Jest "python") {
  python ".claude\hooks\test_straznik.py" | Select-Object -Last 1
  if ($LASTEXITCODE -eq 0) { Ok "Straznik dziala poprawnie" } else { Uwaga "Testy straznika nie przeszly. NIE uzywaj projektu, zadzwon do Igora." }
} else { Uwaga "Bez Pythona straznik nie dziala, a Claude Code zablokuje komendy. Najpierw napraw Pythona." }

# ---------------------------------------------------------------------------
Krok "8/8 Wersje"
foreach ($c in @("git --version", "node --version", "npm --version", "python --version", "shopify version", "claude --version", "gh --version")) {
  $nazwa = $c.Split(" ")[0]
  if (Jest $nazwa) {
    $w = (Invoke-Expression "$c 2>&1" | Select-Object -First 1)
    Write-Host ("  {0,-8} {1}" -f $nazwa, $w)
  } else { Write-Host ("  {0,-8} BRAK" -f $nazwa) -ForegroundColor Yellow }
}

if ($Problemy.Count -gt 0) {
  Write-Host "`nDo sprawdzenia:" -ForegroundColor Yellow
  $Problemy | ForEach-Object { Write-Host "  - $_" -ForegroundColor Yellow }
}

Write-Host @"

==================== DALSZE KROKI ====================
1. Zamknij to okno. Otworz VS Code: Plik > Otworz folder > $Projekt
2. Kliknij ikone Claude (iskierka) na pasku bocznym albo Ctrl+Esc i zaloguj sie kontem Claude
   (Pro / Max / Team). W terminalu VS Code mozna tez wpisac: claude
3. Logowanie do sklepu (JEDEN RAZ, w terminalu VS Code, wklej w calosci):
   shopify store auth --store florina-pl.myshopify.com --scopes read_products,write_products,read_files,write_files,read_metaobjects,write_metaobjects,read_metaobject_definitions,read_inventory,read_orders,read_translations,write_translations,read_locales
   Otworzy sie przegladarka: zaloguj sie WLASNYM kontem pracownika sklepu i zatwierdz.
4. Klucz BaseLinkera: otworz plik .env w VS Code i wklej token po BASELINKER_TOKEN=  (zapisz Ctrl+S).
5. W okienku Claude napisz: "Uruchom rozpoznanie struktury sklepu" (zrobi docs/struktura-sklepu.md).
Szczegoly: INSTALACJA.md
"@ -ForegroundColor White
