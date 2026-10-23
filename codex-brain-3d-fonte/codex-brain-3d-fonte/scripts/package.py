#!/usr/bin/env python3
"""Package only the explicit plugin payload and source paths; no user vault data."""
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ('main.js', 'manifest.json', 'styles.css', 'README.md', 'VALIDACAO.md')

def package():
    output = ROOT / 'artifacts'
    output.mkdir(exist_ok=True)
    plugin = output / 'codex-brain-3d-plugin.zip'
    source = output / 'codex-brain-3d-fonte.zip'
    with zipfile.ZipFile(plugin, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in PAYLOAD:
            archive.write(ROOT / 'dist' / 'codex-brain-3d' / name, 'codex-brain-3d/' + name)
    sources = [ROOT / name for name in ('package.json', 'manifest.json', 'styles.css', 'README.md', 'VALIDACAO.md', '.gitignore')]
    for directory in ('src', 'scripts', 'tests', 'docs'):
        sources.extend(p for p in (ROOT / directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    with zipfile.ZipFile(source, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(sources):
            archive.write(path, 'codex-brain-3d-fonte/' + path.relative_to(ROOT).as_posix())
    for path in (plugin, source):
        with zipfile.ZipFile(path) as archive:
            bad = archive.testzip()
            if bad:
                raise RuntimeError('ZIP inválido: ' + bad)
        print(path)
    with zipfile.ZipFile(plugin) as archive:
        assert set(archive.namelist()) == {'codex-brain-3d/' + name for name in PAYLOAD}
        for name in PAYLOAD:
            assert archive.read('codex-brain-3d/' + name) == (ROOT / 'dist' / 'codex-brain-3d' / name).read_bytes()

if __name__ == '__main__':
    package()
