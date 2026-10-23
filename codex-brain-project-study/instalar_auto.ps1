$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$BrainScript = Join-Path $Root 'brain.py'
$SyncScript = Join-Path $Root 'sync_obsidian.py'
$AutoScript = Join-Path $Root 'auto_brain.py'
$Config = Join-Path $Root 'auto_brain.json'

foreach ($file in @($BrainScript, $SyncScript, $AutoScript, $Config)) {
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
        throw "Arquivo obrigatório não encontrado: $file. Extraia os arquivos desta integração diretamente na pasta do Codex Brain."
    }
}

$PythonCommand = Get-Command python -ErrorAction Stop
$PythonExe = (& $PythonCommand.Source -c "import sys; print(sys.executable)").Trim()
if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
    throw "Não consegui localizar o executável Python: $PythonExe"
}

Write-Host "Validando os scripts..." -ForegroundColor Cyan
& $PythonExe -m py_compile $AutoScript $SyncScript
if ($LASTEXITCODE -ne 0) { throw "A validação de sintaxe falhou." }

Write-Host "Executando uma verificação inicial (sem forçar nova análise)..." -ForegroundColor Cyan
& $PythonExe $AutoScript --once
if ($LASTEXITCODE -ne 0) {
    throw "A verificação inicial falhou. Consulte .brain\auto\auto.log antes de instalar a tarefa."
}

$taskName = 'Codex Brain - Atualização automática'
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$start = (Get-Date).AddMinutes(2).ToString("yyyy-MM-dd'T'HH:mm:ssK")
function XmlEscape([string]$Text) { return [System.Security.SecurityElement]::Escape($Text) }
$pyXml = XmlEscape $PythonExe
$rootXml = XmlEscape $Root
$scriptXml = XmlEscape $AutoScript
$userXml = XmlEscape $identity
$startXml = XmlEscape $start

# Repeats hourly within a daily trigger. InteractiveToken means it uses the current
# user's existing Codex login and does not run elevated or store a password.
$xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>Verifica alterações em projetos estudados, atualiza perfis do Codex Brain, mantém histórico e sincroniza notas gerenciadas no Obsidian.</Description><Author>$userXml</Author></RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <Enabled>true</Enabled><StartBoundary>$startXml</StartBoundary>
      <Repetition><Interval>PT1H</Interval><Duration>P1D</Duration><StopAtDurationEnd>false</StopAtDurationEnd></Repetition>
      <ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Principals><Principal id="Author"><UserId>$userXml</UserId><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries><StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate><StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings><StopOnIdleEnd>false</StopOnIdleEnd><RestartOnIdle>false</RestartOnIdle></IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand><Enabled>true</Enabled><Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle><WakeToRun>false</WakeToRun><ExecutionTimeLimit>PT2H</ExecutionTimeLimit><Priority>7</Priority>
  </Settings>
  <Actions Context="Author"><Exec><Command>$pyXml</Command><Arguments>"$scriptXml" --once</Arguments><WorkingDirectory>$rootXml</WorkingDirectory></Exec></Actions>
</Task>
"@

Register-ScheduledTask -TaskName $taskName -Xml $xml -Force | Out-Null
Write-Host "" 
Write-Host "Automação instalada: $taskName" -ForegroundColor Green
Write-Host "Frequência: a cada hora enquanto sua conta estiver conectada." 
Write-Host "Projetos: confira auto_brain.json" 
Write-Host "Logs: $Root\.brain\auto\auto.log" 
Write-Host "Para executar agora: & `"$PythonExe`" `"$AutoScript`" --once" 
Write-Host "A tarefa não roda elevada; usa o login Codex da sua sessão de usuário." 
