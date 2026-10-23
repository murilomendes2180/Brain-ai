from __future__ import annotations

import argparse
import hashlib
import re
import sys
from datetime import datetime
from pathlib import Path

from brain_io import atomic_write_text, exclusive_file_lock

# This helper is designed to sit beside brain.py in codex-brain-project-study.
ROOT = Path(__file__).resolve().parent
PROJECTS_DIR = ROOT / ".brain" / "projects"


def canonical_project(value: str) -> Path:
    return Path(value).expanduser().resolve()


def project_key(project: Path) -> str:
    normalized = str(project).casefold()
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:10]
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", project.name).strip("-")[:40] or "project"
    return f"{slug}-{digest}"


def safe_folder(value: str) -> str:
    # Keep this argument to one folder name; avoid path traversal.
    result = re.sub(r'[<>:"/\\|?*]+', "-", value).strip(" .-")
    if not result or result in {".", ".."}:
        raise ValueError("--folder precisa ser um nome de pasta válido.")
    return result[:80]


def yaml_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'


def managed_index_content(existing: str, entries: list[str]) -> str:
    start = "<!-- CODEX-BRAIN:START -->"
    end = "<!-- CODEX-BRAIN:END -->"
    listing = "\n".join(entries) if entries else "_Nenhum perfil sincronizado ainda._"
    block = f"{start}\n\n{listing}\n\n{end}"
    if start in existing and end in existing:
        before, rest = existing.split(start, 1)
        _old, after = rest.split(end, 1)
        return before.rstrip() + "\n\n" + block + after
    if existing.strip():
        return existing.rstrip() + "\n\n" + block + "\n"
    return "# Perfis do Codex Brain\n\nEsta página lista os perfis espelhados pelo script `sync_obsidian.py`. A lista é atualizada a cada sincronização.\n\n" + block + "\n"


def yaml_value(text: str, key: str) -> str:
    match = re.search(rf'(?m)^{re.escape(key)}:\s*"(.*)"\s*$', text)
    if not match:
        return ""
    return match.group(1).replace('\\"', '"').replace('\\\\', '\\')


def ensure_owned_note(path: Path, project: Path) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    frontmatter = parts[1] if len(parts) == 3 and parts[0] == "" else ""
    if not re.search(r"(?m)^gerenciado_por: sync_obsidian\.py\s*$", frontmatter) or yaml_value(frontmatter, "caminho_origem") != str(project):
        raise FileExistsError(f"Nota existente não pertence a este projeto/integração: {path}. Escolha outra pasta em 'folder' ou mova sua nota manual.")


def render_profile_note(project: Path, content: str, synced_at: str) -> str:
    return (
        "---\n"
        "tipo: perfil-gerado\n"
        f"projeto: {yaml_quote(project.name)}\n"
        f"caminho_origem: {yaml_quote(str(project))}\n"
        f"sincronizado_em: {yaml_quote(synced_at)}\n"
        "gerenciado_por: sync_obsidian.py\n"
        "---\n\n"
        "> [!info] Perfil espelhado automaticamente\n"
        "> Esta nota é atualizada a partir do perfil do Codex Brain. Para preservar anotações manuais, escreva-as em outras notas do cofre e crie links para esta página.\n\n"
        "**Notas relacionadas:** [[Visão geral]] · [[Arquitetura]] · [[Fluxos principais]] · [[Persistência e modelo de dados]] · [[Testes e qualidade]] · [[Riscos e perguntas abertas]]\n\n"
        f"{content.rstrip()}\n"
    )


def profile_note_is_current(project: Path, vault: Path, folder: str, content: str) -> bool:
    path = vault / "Projetos" / safe_folder(folder) / "Perfil do Codex Brain.md"
    if not path.is_file():
        return False
    existing = path.read_text(encoding="utf-8")
    timestamp = yaml_value(existing, "sincronizado_em")
    return bool(timestamp) and existing == render_profile_note(project, content, timestamp)


def sync_is_current(project: Path, vault: Path, folder: str, content: str) -> bool:
    if not profile_note_is_current(project, vault, folder, content):
        return False
    index = vault / "Sistemas" / "Índice dos perfis do Codex Brain.md"
    if not index.is_file():
        return False
    existing = index.read_text(encoding="utf-8")
    return existing == managed_index_content(existing, collect_profile_entries(vault))


def collect_profile_entries(vault: Path) -> list[str]:
    projects_root = vault / "Projetos"
    entries: list[str] = []
    if not projects_root.is_dir():
        return entries
    for note_path in sorted(projects_root.glob("*/Perfil do Codex Brain.md")):
        try:
            note_text = note_path.read_text(encoding="utf-8")
        except OSError:
            continue
        project_name = yaml_value(note_text, "projeto") or note_path.parent.name
        source_path = yaml_value(note_text, "caminho_origem")
        synced_at = yaml_value(note_text, "sincronizado_em")
        note_rel = note_path.relative_to(vault).with_suffix("").as_posix()
        line = f"- [[{note_rel}|{project_name}]]"
        if synced_at:
            line += f" · Sincronizado: `{synced_at}`"
        if source_path:
            line += f" · origem: `{source_path}`"
        entries.append(line)
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Exporta o perfil persistente de um projeto para um cofre Obsidian sem tocar nas notas manuais."
    )
    parser.add_argument("--project", required=True, help="Caminho exato do projeto estudado pelo brain.py")
    parser.add_argument("--vault", required=True, help="Caminho da raiz do cofre Obsidian")
    parser.add_argument("--folder", default=None, help="Nome da pasta dentro de Projetos (padrão: nome do repositório)")
    args = parser.parse_args()

    project = canonical_project(args.project)
    vault = Path(args.vault).expanduser().resolve()
    folder = safe_folder(args.folder or project.name)

    source_profile = PROJECTS_DIR / project_key(project) / "profile.md"
    if not source_profile.is_file():
        print(f"Erro: não encontrei o perfil salvo em:\n{source_profile}\nExecute primeiro `python brain.py study --project \"{project}\"`.", file=sys.stderr)
        return 2
    if not vault.exists() or not vault.is_dir():
        print(f"Erro: a pasta do cofre não existe ou não é uma pasta:\n{vault}", file=sys.stderr)
        print("Abra o Obsidian, clique com o botão direito no nome do cofre e use 'Mostrar na pasta' para localizar a raiz.", file=sys.stderr)
        return 2

    # Only these script-managed files are written; hand-authored vault notes are not modified.
    target_dir = vault / "Projetos" / folder
    target_dir.mkdir(parents=True, exist_ok=True)
    target_note = target_dir / "Perfil do Codex Brain.md"
    synced_at = datetime.now().astimezone().isoformat(timespec="seconds")
    content = source_profile.read_text(encoding="utf-8")
    if not content.strip():
        print("Erro: perfil de origem vazio; nada foi sincronizado.", file=sys.stderr)
        return 2
    index_path = vault / "Sistemas" / "Índice dos perfis do Codex Brain.md"
    lock_key = hashlib.sha256(str(vault).casefold().encode("utf-8")).hexdigest()[:20]
    with exclusive_file_lock(ROOT / ".brain" / "locks" / f"vault-{lock_key}.lock"):
        ensure_owned_note(target_note, project)
        if not profile_note_is_current(project, vault, folder, content):
            atomic_write_text(target_note, render_profile_note(project, content, synced_at))
        existing = index_path.read_text(encoding="utf-8") if index_path.exists() else ""
        updated = managed_index_content(existing, collect_profile_entries(vault))
        if updated != existing:
            atomic_write_text(index_path, updated)

    print("Sincronização concluída.")
    print(f"Projeto: {project}")
    print(f"Perfil de origem: {source_profile}")
    print(f"Nota Obsidian: {target_note}")
    print(f"Índice: {index_path}")
    print("Notas manuais existentes não foram modificadas. A nota 'Perfil do Codex Brain.md' é gerenciada pelo script e será atualizada em futuras sincronizações.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Erro de sincronização: {exc}", file=sys.stderr)
        raise SystemExit(2)
