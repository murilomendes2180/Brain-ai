$ErrorActionPreference = 'Stop'
$taskName = 'Codex Brain - Atualização automática'
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($task) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "Tarefa removida: $taskName" -ForegroundColor Green
} else {
    Write-Host "A tarefa '$taskName' não está instalada."
}
Write-Host "Os scripts, logs, perfis e notas do Obsidian não foram apagados."
