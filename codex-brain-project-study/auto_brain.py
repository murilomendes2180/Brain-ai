from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from brain_io import acquire_file_lock, release_file_lock, atomic_write_text
from sync_obsidian import sync_is_current

ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = ROOT / "auto_brain.json"
AUTO_DIR = ROOT / ".brain" / "auto"
STATE_PATH = AUTO_DIR / "state.json"
LOG_PATH = AUTO_DIR / "auto.log"
DB_PATH = ROOT / ".brain" / "brain.db"

DEFAULT_IGNORE_DIRS = {
    ".git", ".hg", ".svn", ".brain", ".venv", "venv", "env", "node_modules",
    "dist", "build", "target", "out", "coverage", ".next", ".nuxt", ".cache",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "vendor-bin",
    "Pods", "DerivedData", "TestResults", "packages-cache",
}
SECRET_NAMES = {
    "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519", "credentials.json",
    "service-account.json", "secrets.json", "secrets.yaml", "secrets.yml",
}
SECRET_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".keystore", ".jks"}
START_MARKER = "<!-- CODEX-BRAIN-AUTO:START -->"
END_MARKER = "<!-- CODEX-BRAIN-AUTO:END -->"
DRY_RUN = False


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def local_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def python_environment() -> dict[str, str]:
    # Keep child Python output compatible with the parent's UTF-8 decoder on Windows.
    return {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}


def write_log(message: str) -> None:
    line = f"[{local_now()}] {message}\n"
    if not DRY_RUN:
        AUTO_DIR.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line)
    print(line.rstrip())


def load_json(path: Path, fallback: Any) -> Any:
    if not path.is_file():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Não foi possível ler JSON {path}: {exc}") from exc


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2))


def project_key(project: Path) -> str:
    normalized = str(project).casefold()
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:10]
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", project.name).strip("-")[:40] or "project"
    return f"{slug}-{digest}"


def profile_path(project: Path) -> Path:
    return ROOT / ".brain" / "projects" / project_key(project) / "profile.md"


def profile_hash(content: str | None) -> str:
    if content is None:
        return ""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def is_secret_file(path: Path) -> bool:
    name = path.name.casefold()
    if name in SECRET_NAMES:
        return True
    if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
        return True
    if path.suffix.casefold() in SECRET_SUFFIXES:
        return True
    # Common private key naming. Deliberately avoid broad 'secret' matches so
    # source files such as secure_store.rs remain part of the analysis snapshot.
    if name.endswith(".privatekey") or name.endswith("_private_key"):
        return True
    return False


def scan_project(project: Path, old_manifest: dict[str, Any], config: dict[str, Any]) -> tuple[str, dict[str, Any], int]:
    ignore = set(DEFAULT_IGNORE_DIRS)
    ignore.update(str(x) for x in config.get("ignore_dirs", []))
    ignore_folded = {x.casefold() for x in ignore}
    try:
        max_size = max(1, int(config.get("max_file_size_mb", 2))) * 1024 * 1024
    except (TypeError, ValueError):
        max_size = 2 * 1024 * 1024

    manifest: dict[str, Any] = {}
    skipped_secrets = 0
    for current, dirs, files in os.walk(project, topdown=True, followlinks=False):
        current_path = Path(current)
        dirs[:] = sorted(d for d in dirs if d.casefold() not in ignore_folded and not (current_path / d).is_symlink())
        for filename in sorted(files):
            path = current_path / filename
            if is_secret_file(path):
                skipped_secrets += 1
                continue
            try:
                stat = path.stat(follow_symlinks=False)
                if not path.is_file() or path.is_symlink():
                    continue
                rel = path.relative_to(project).as_posix()
                old = old_manifest.get(rel, {})
                meta = {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns}
                if old.get("size") == stat.st_size and old.get("mtime_ns") == stat.st_mtime_ns and old.get("digest"):
                    digest = old["digest"]
                elif stat.st_size > max_size:
                    digest = f"large-file:{stat.st_size}:{stat.st_mtime_ns}"
                else:
                    h = hashlib.sha256()
                    with path.open("rb") as f:
                        for chunk in iter(lambda: f.read(1024 * 1024), b""):
                            h.update(chunk)
                    digest = h.hexdigest()
                meta["digest"] = digest
                manifest[rel] = meta
            except (OSError, PermissionError):
                # A transiently locked file should not crash the whole scan.
                continue

    overall = hashlib.sha256()
    for rel in sorted(manifest):
        item = manifest[rel]
        overall.update(rel.encode("utf-8", errors="replace"))
        overall.update(b"\0")
        overall.update(str(item.get("digest", "")).encode("ascii", errors="replace"))
        overall.update(b"\n")
    return overall.hexdigest(), manifest, skipped_secrets


def parse_time(value: str | None) -> float:
    if not value:
        return 0.0
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError, OSError):
        return 0.0


def db_profile_record(project: Path) -> dict[str, Any] | None:
    if not DB_PATH.exists():
        return None
    try:
        with sqlite3.connect(DB_PATH) as con:
            con.row_factory = sqlite3.Row
            row = con.execute(
                "SELECT project_path, project_name, profile, profile_path, studied_at, last_exit_code FROM project_profiles WHERE project_path=?",
                (str(project),),
            ).fetchone()
            return dict(row) if row else None
    except sqlite3.Error:
        return None


def run_brain_study(project: Path, timeout: int) -> tuple[int, str]:
    brain_script = ROOT / "brain.py"
    if not brain_script.is_file():
        return 2, f"Não encontrei brain.py em {ROOT}"
    command = [sys.executable, str(brain_script), "study", "--project", str(project), "--refresh", "--timeout", str(timeout)]
    write_log(f"Iniciando estudo somente leitura: {project}")
    try:
        proc = subprocess.run(
            command, cwd=ROOT, env=python_environment(), text=True, encoding="utf-8", errors="replace",
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout + 60, check=False,
        )
        output = proc.stdout or ""
        for line in output.splitlines()[-28:]:
            # The CLI output is logged locally; avoid copying arbitrary output into shared notes.
            write_log("Codex: " + line[:1000])
        return proc.returncode, output
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "")
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        return 124, f"Tempo limite do processo excedido.\n{output}"
    except OSError as exc:
        return 2, f"Falha ao iniciar brain.py: {exc}"


def sync_project(project: Path, vault: Path, folder: str) -> tuple[int, str]:
    sync_script = ROOT / "sync_obsidian.py"
    if not sync_script.is_file():
        return 2, f"Não encontrei sync_obsidian.py em {ROOT}"
    command = [sys.executable, str(sync_script), "--project", str(project), "--vault", str(vault), "--folder", folder]
    try:
        proc = subprocess.run(command, cwd=ROOT, env=python_environment(), text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120, check=False)
        return proc.returncode, proc.stdout or ""
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 2, f"Falha na sincronização do Obsidian: {exc}"


def safe_note_folder(value: str) -> str:
    result = re.sub(r'[<>:"/\\|?*]+', "-", value).strip(" .-")
    return (result or "Projeto")[:80]


def create_history(vault: Path, folder: str, project_name: str, old_profile: str, new_profile: str, reason: str) -> list[str]:
    if not old_profile or old_profile == new_profile:
        return []
    stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S-%f")
    history_dir = vault / "Projetos" / safe_note_folder(folder) / "Histórico Codex Brain"
    history_dir.mkdir(parents=True, exist_ok=True)
    previous_path = history_dir / f"Perfil anterior - {stamp}.md"
    counter = 2
    while previous_path.exists():
        previous_path = history_dir / f"Perfil anterior - {stamp} ({counter}).md"
        counter += 1
    atomic_write_text(previous_path,
        f"---\ntipo: snapshot-perfil\nprojeto: {json.dumps(project_name, ensure_ascii=False)}\ndata: {local_now()}\n---\n\n"
        "> Cópia do perfil anterior à atualização. O backup local foi preservado antes da substituição.\n\n" + old_profile.rstrip() + "\n",
    )

    diff_lines = list(difflib.unified_diff(
        old_profile.splitlines(), new_profile.splitlines(),
        fromfile="perfil-anterior.md", tofile="perfil-atual.md", lineterm="",
    ))
    diff_text = "\n".join(diff_lines)
    truncated = len(diff_text) > 30000
    if truncated:
        diff_text = diff_text[:30000] + "\n\n[Diff truncado para manter a nota manejável.]"
    diff_path = history_dir / f"Mudanças no conhecimento - {stamp}.md"
    atomic_write_text(diff_path,
        f"---\ntipo: diff-perfil\nprojeto: {json.dumps(project_name, ensure_ascii=False)}\ndata: {local_now()}\n---\n\n"
        f"# Mudanças no conhecimento: {project_name}\n\n"
        f"- Motivo: {reason}\n- Snapshot anterior: [[{previous_path.with_suffix('').relative_to(vault).as_posix()}]]\n\n"
        "> A diferença textual mostra o que mudou no perfil, não prova que cada afirmação nova foi validada.\n\n"
        "````diff\n" + (diff_text or "(sem diferenças textuais)") + "\n````\n",
    )
    return [str(previous_path.relative_to(vault).as_posix()), str(diff_path.relative_to(vault).as_posix())]


def update_learning_log(vault: Path, events: list[dict[str, str]]) -> None:
    systems = vault / "Sistemas"
    systems.mkdir(parents=True, exist_ok=True)
    path = systems / "Diário de aprendizagem do Codex Brain.md"
    existing = path.read_text(encoding="utf-8") if path.exists() else "# Diário de aprendizagem do Codex Brain\n\nEste diário é gerenciado automaticamente entre os marcadores. Notas fora do bloco são preservadas.\n"
    lines = [START_MARKER, "", "## Eventos recentes", ""]
    for event in reversed(events[-100:]):
        lines.append(f"- **{event.get('at', '?')}** · **{event.get('status', 'evento')}** · {event.get('project', 'projeto')}: {event.get('message', '').replace(chr(10), ' ')[:500]}")
    lines.extend(["", END_MARKER])
    block = "\n".join(lines)
    if START_MARKER in existing and END_MARKER in existing:
        before, rest = existing.split(START_MARKER, 1)
        _old, after = rest.split(END_MARKER, 1)
        output = before.rstrip() + "\n\n" + block + after
    else:
        output = existing.rstrip() + "\n\n" + block + "\n"
    if output != existing:
        atomic_write_text(path, output)


def update_proposals_note(vault: Path) -> None:
    """Mirror pending/reviewed brain proposals to a clearly generated note."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "brain.py"), "proposals"], cwd=ROOT,
        env=python_environment(), text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, timeout=60, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Consulta de propostas falhou (código {result.returncode}).")
    systems = vault / "Sistemas"
    systems.mkdir(parents=True, exist_ok=True)
    path = systems / "Propostas de melhoria do Codex Brain (geradas).md"
    atomic_write_text(path,
        "---\ntipo: propostas-geradas\ngerenciado_por: auto_brain.py\n---\n\n"
        "# Propostas de melhoria do Codex Brain\n\n"
        "> Propostas são hipóteses para revisão. Não são aplicadas automaticamente ao código, às regras ou às permissões.\n\n"
        "```text\n" + (result.stdout or "Nenhuma saída.").rstrip() + "\n```\n",
    )


def acquire_lock() -> int | None:
    return acquire_file_lock(AUTO_DIR / "running.lock")


def release_lock(fd: int | None) -> None:
    release_file_lock(fd)


def process_project(entry: dict[str, Any], config: dict[str, Any], state: dict[str, Any], force: bool, dry_run: bool) -> bool:
    project = Path(str(entry.get("path", ""))).expanduser().resolve()
    folder = str(entry.get("folder") or project.name)
    vault = Path(str(config.get("vault", ""))).expanduser().resolve()
    pkey = str(project)
    prev = state.setdefault("projects", {}).get(pkey, {})
    if not project.is_dir():
        msg = f"Pasta de projeto não encontrada: {project}"
        write_log("ERRO: " + msg)
        add_event(state, "falha", project.name, msg)
        return False
    if not vault.is_dir():
        msg = f"Pasta do cofre Obsidian não encontrada: {vault}"
        write_log("ERRO: " + msg)
        add_event(state, "falha", project.name, msg)
        return False

    old_manifest = prev.get("manifest", {}) if isinstance(prev.get("manifest", {}), dict) else {}
    fingerprint, manifest, skipped_secrets = scan_project(project, old_manifest, config)
    current_profile_path = profile_path(project)
    current_profile = current_profile_path.read_text(encoding="utf-8", errors="replace") if current_profile_path.is_file() else None
    existing_db = db_profile_record(project)
    last_refresh = parse_time((existing_db or {}).get("studied_at"))
    if not last_refresh:
        last_refresh = float(prev.get("last_refresh_epoch", 0) or 0)
    refresh_days = max(1, int(config.get("refresh_every_days", 7)))

    reason: str | None = None
    if force:
        reason = "forçado pelo usuário"
    elif not current_profile or not current_profile.strip():
        reason = "perfil ainda não existe ou está vazio"
    elif existing_db and existing_db.get("last_exit_code") != 0:
        reason = "perfil anterior veio de uma execução com erro"
    elif prev and prev.get("fingerprint") and fingerprint != prev.get("fingerprint"):
        reason = "arquivos do projeto mudaram"
    elif last_refresh and time.time() - last_refresh >= refresh_days * 86400:
        reason = f"revisão periódica ({refresh_days} dias)"
    elif not last_refresh:
        # A database profile may have been restored/copied but has no studied_at.
        reason = "data da última análise desconhecida"

    if skipped_secrets:
        write_log(f"Aviso: {skipped_secrets} arquivo(s) potencialmente sensível(is) foram excluídos da impressão digital; conteúdos não foram lidos.")

    if dry_run:
        action = f"estudar ({reason})" if reason else "sem estudo; apenas verificar sincronização"
        write_log(f"SIMULAÇÃO: {project} -> {action}")
        return True

    old_hash = profile_hash(current_profile)
    proposals_updated = False
    succeeded = True
    if reason:
        original_profile = current_profile
        code, output = run_brain_study(project, int(config.get("timeout_seconds", 1800)))
        after_path = profile_path(project)
        new_profile = after_path.read_text(encoding="utf-8", errors="replace") if after_path.is_file() else None
        if code != 0 or not new_profile:
            # brain.py accepts only successful final answers and saves its own history.
            # Do not blindly restore: another manual study may have completed meanwhile.
            message = f"Estudo falhou (código {code}); nenhuma sincronização foi feita. Veja .brain/auto/auto.log e o histórico local."
            write_log("ERRO: " + message)
            add_event(state, "falha", project.name, message)
            # Keep prior fingerprint so that the next scheduled run retries.
            return False
        changed = old_hash != profile_hash(new_profile)
        history_paths: list[str] = []
        if changed and original_profile is not None:
            history_paths = create_history(vault, folder, project.name, original_profile, new_profile, reason)
        updated_db = db_profile_record(project)
        fresh_time = parse_time((updated_db or {}).get("studied_at")) or time.time()
        prev.update({
            "fingerprint": fingerprint,
            "manifest": manifest,
            "last_refresh_epoch": fresh_time,
            "profile_hash": profile_hash(new_profile),
            "synced_profile_hash": prev.get("synced_profile_hash", ""),
            "last_study_reason": reason,
        })
        state["projects"][pkey] = prev
        status = "conhecimento atualizado" if changed else "estudo concluído; perfil textual sem mudanças"
        message = f"{status}; motivo: {reason}."
        if history_paths:
            message += " Histórico: " + ", ".join(f"[[{Path(x).with_suffix('').as_posix()}]]" for x in history_paths)
        add_event(state, "estudo concluído", project.name, message)
        write_log(f"Estudo concluído com sucesso para {project}. Perfil mudou: {changed}.")
        # Run existing safe learning analysis; it creates proposals but does not edit rules/code.
        try:
            learned = subprocess.run([sys.executable, str(ROOT / "brain.py"), "learn"], cwd=ROOT, env=python_environment(), text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60, check=False)
            if learned.returncode != 0:
                raise RuntimeError(f"Análise de propostas falhou (código {learned.returncode}).")
            update_proposals_note(vault)
            proposals_updated = True
        except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
            succeeded = False
            write_log(f"Aviso: não foi possível atualizar propostas de melhoria nesta execução: {exc}")

    # Persist the baseline on every non-failing pass. This is essential on the very
    # first run: without a saved fingerprint, later repository changes would not be detected.
    current_profile_path = profile_path(project)
    current_profile = current_profile_path.read_text(encoding="utf-8", errors="replace") if current_profile_path.is_file() else None
    if current_profile is None:
        return False
    current_hash = profile_hash(current_profile)
    if not reason:
        prev.update({
            "fingerprint": fingerprint,
            "manifest": manifest,
            "last_refresh_epoch": last_refresh or current_profile_path.stat().st_mtime,
            "profile_hash": current_hash,
            "synced_profile_hash": prev.get("synced_profile_hash", ""),
        })

    # Sync if the profile hash changed or hasn't been synced yet. This also repairs a
    # previous sync failure on the next hourly pass without restudying the repo.
    synced_hash = prev.get("synced_profile_hash", "")
    if current_hash != synced_hash or not sync_is_current(project, vault, folder, current_profile):
        code, output = sync_project(project, vault, folder)
        if code == 0:
            prev["synced_profile_hash"] = current_hash
            prev["profile_hash"] = current_hash
            write_log(f"Obsidian sincronizado: {project}")
            add_event(state, "sincronização concluída", project.name, "Perfil e índice do Obsidian sincronizados automaticamente.")
            for line in output.splitlines():
                write_log("Sync: " + line[:800])
            if not proposals_updated:
                try:
                    update_proposals_note(vault)
                except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
                    succeeded = False
                    write_log(f"Aviso: não foi possível exportar propostas: {exc}")
        else:
            succeeded = False
            message = f"Sincronização do Obsidian falhou (código {code}); será tentada novamente na próxima execução."
            write_log("ERRO: " + message + " " + output[-1000:].replace("\n", " "))
            add_event(state, "falha de sincronização", project.name, message)
    state["projects"][pkey] = prev
    return succeeded


def add_event(state: dict[str, Any], status: str, project: str, message: str) -> None:
    events = state.setdefault("events", [])
    event = {"at": local_now(), "status": status, "project": project, "message": message[:1200]}
    # Avoid hourly duplicates for the same repeated error.
    if events:
        last = events[-1]
        if last.get("status") == status and last.get("project") == project and last.get("message") == event["message"]:
            return
    events.append(event)
    state["events"] = events[-100:]


def main() -> int:
    global DRY_RUN
    parser = argparse.ArgumentParser(description="Atualização automática de conhecimento e sincronização do Codex Brain com Obsidian.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Arquivo auto_brain.json")
    parser.add_argument("--once", action="store_true", help="Executar uma verificação e sair (padrão)")
    parser.add_argument("--force", action="store_true", help="Forçar novo estudo de todos os projetos configurados")
    parser.add_argument("--dry-run", action="store_true", help="Mostrar o que seria feito sem estudar nem salvar estado")
    args = parser.parse_args()
    DRY_RUN = args.dry_run

    if not (ROOT / "brain.py").is_file() or not (ROOT / "sync_obsidian.py").is_file():
        print("Erro: coloque auto_brain.py na mesma pasta de brain.py e sync_obsidian.py.", file=sys.stderr)
        return 2
    try:
        config = load_json(Path(args.config).expanduser().resolve(), {})
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if not isinstance(config, dict) or not isinstance(config.get("projects"), list) or not config["projects"]:
        print("Erro: auto_brain.json precisa conter uma lista não vazia em 'projects'.", file=sys.stderr)
        return 2
    if not config.get("vault"):
        print("Erro: informe o caminho do cofre em auto_brain.json.", file=sys.stderr)
        return 2

    lock_fd = None if args.dry_run else acquire_lock()
    if not args.dry_run and lock_fd is None:
        write_log("Outra execução automática já está em andamento; esta verificação foi ignorada.")
        return 3
    try:
        state = load_json(STATE_PATH, {"version": 1, "projects": {}, "events": []})
        if not isinstance(state, dict) or not isinstance(state.get("projects", {}), dict) or not isinstance(state.get("events", []), list):
            raise RuntimeError("Estado inválido; state.json foi preservado para diagnóstico.")
        state.setdefault("version", 1)
        state.setdefault("projects", {})
        state.setdefault("events", [])
        succeeded = True
        for entry in config["projects"]:
            try:
                if not isinstance(entry, dict) or not entry.get("path"):
                    write_log("Aviso: entrada de projeto ignorada por não conter 'path'.")
                    succeeded = False
                    continue
                if not process_project(entry, config, state, args.force, args.dry_run):
                    succeeded = False
            except Exception as exc:
                succeeded = False
                project_name = str(entry.get("path", "projeto desconhecido")) if isinstance(entry, dict) else "entrada inválida"
                write_log(f"ERRO inesperado em {project_name}: {type(exc).__name__}: {exc}")
                add_event(state, "falha", project_name, f"{type(exc).__name__}: {exc}")
            if not args.dry_run:
                try:
                    vault = Path(str(config["vault"])).expanduser().resolve()
                    if vault.is_dir():
                        update_learning_log(vault, state["events"])
                except OSError as exc:
                    succeeded = False
                    write_log(f"Aviso: não foi possível atualizar o diário do Obsidian: {exc}")
                atomic_write_json(STATE_PATH, state)
        if args.dry_run:
            return 0 if succeeded else 1
        atomic_write_json(STATE_PATH, state)
        write_log("Verificação automática concluída." if succeeded else "Verificação automática terminou com falhas; consulte os eventos acima.")
        return 0 if succeeded else 1
    except (OSError, RuntimeError) as exc:
        print(f"Erro na automação: {exc}", file=sys.stderr)
        return 1
    finally:
        release_lock(lock_fd)


if __name__ == "__main__":
    raise SystemExit(main())
