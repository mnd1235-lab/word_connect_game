<#
.SYNOPSIS
    .streamlit/secrets.toml 의 APP_PASSWORD 를 바꾼다.

.DESCRIPTION
    - OPENAI_API_KEY 를 비롯한 다른 값은 그대로 둔다.
    - APP_PASSWORD 가 여러 줄 들어가 있으면 모두 지우고 한 줄만 남긴다.
    - BOM 없는 UTF-8 로 저장한다. PowerShell 5.1 의 Set-Content -Encoding utf8 은
      BOM 을 붙이고, 그러면 TOML 파싱이 첫 줄부터 실패한다.
    - 저장 후 파싱까지 확인한다(python 이 있으면).

.EXAMPLE
    .\scripts\set_password.ps1
    비밀번호를 물어본다. 화면에 찍히지 않고 명령 기록에도 남지 않는다.

.EXAMPLE
    .\scripts\set_password.ps1 -Password 'hunter2'
    비대화식. 스크립트 자동화용. 명령 기록에 남으므로 평소엔 쓰지 말 것.
#>
[CmdletBinding()]
param(
    [string]$Password,
    [string]$SecretsPath
)

$ErrorActionPreference = 'Stop'

# 스크립트 위치 기준으로 저장소 루트를 잡는다 — 어디서 실행하든 동작한다.
if (-not $SecretsPath) {
    $root = Split-Path -Parent $PSScriptRoot
    $SecretsPath = Join-Path $root '.streamlit\secrets.toml'
}

if (-not (Test-Path $SecretsPath)) {
    throw "secrets 파일이 없습니다: $SecretsPath`n.streamlit\secrets.toml.example 을 복사해 만드세요."
}

# --- 비밀번호 입력 ---
if (-not $Password) {
    $secure = Read-Host -Prompt '새 비밀번호' -AsSecureString
    $confirm = Read-Host -Prompt '한 번 더' -AsSecureString
    $toPlain = {
        param($s)
        $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($s)
        try { [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
        finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
    }
    $Password = & $toPlain $secure
    if ($Password -ne (& $toPlain $confirm)) { throw '두 번 입력한 값이 다릅니다.' }
}

if ([string]::IsNullOrWhiteSpace($Password)) { throw '비밀번호가 비어 있습니다.' }

# TOML 기본 문자열 이스케이프 — 역슬래시를 먼저 처리해야 한다.
$escaped = $Password.Replace('\', '\\').Replace('"', '\"')

# --- 기존 내용 읽기 (BOM 제거) ---
$text = [IO.File]::ReadAllText($SecretsPath).TrimStart([char]0xFEFF)
$lines = $text -split "`r?`n"

# APP_PASSWORD 줄은 모두 걷어낸다. 중복이 남으면 TOML 이
# "Cannot overwrite a value" 로 죽는다.
$kept = @($lines | Where-Object { $_ -notmatch '^\s*APP_PASSWORD\s*=' })

# 끝의 빈 줄을 걷어낸다. $kept[0..($kept.Count-2)] 로 자르면 원소가 하나일 때
# 범위가 0..-1 이 되어 오히려 두 개로 늘어난다 — 인덱스로 자른다.
$end = $kept.Count - 1
while ($end -ge 0 -and [string]::IsNullOrWhiteSpace($kept[$end])) { $end-- }
$kept = if ($end -ge 0) { @($kept[0..$end]) } else { @() }

$out = @($kept) + "APP_PASSWORD = `"$escaped`""
$content = ($out -join "`n") + "`n"

# --- BOM 없는 UTF-8 로 저장 ---
$backup = "$SecretsPath.bak"
Copy-Item $SecretsPath $backup -Force
[IO.File]::WriteAllText($SecretsPath, $content, (New-Object Text.UTF8Encoding $false))

# --- 검증 ---
$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
    $keys = & python -c @"
import tomllib
with open(r'$SecretsPath','rb') as f:
    d = tomllib.load(f)
print(','.join(d))
"@ 2>&1
    if ($LASTEXITCODE -ne 0) {
        Copy-Item $backup $SecretsPath -Force
        throw "TOML 파싱에 실패해 원래 파일로 되돌렸습니다.`n$keys"
    }
    Write-Host "저장 완료. 키: $keys" -ForegroundColor Green
    if ($keys -notmatch 'OPENAI_API_KEY') {
        Write-Warning 'OPENAI_API_KEY 가 보이지 않습니다. 파일을 확인하세요.'
    }
} else {
    Write-Host "저장 완료. (python 이 없어 파싱 검증은 건너뜀)" -ForegroundColor Yellow
}

Remove-Item $backup -Force -ErrorAction SilentlyContinue
Write-Host '앱을 다시 실행하면 새 비밀번호가 적용됩니다.'
