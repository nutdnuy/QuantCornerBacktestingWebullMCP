"""Install the QuantCorner suite; optional upgrades retain complete local backups."""
import argparse
import json
import re
import shutil
import tempfile
import uuid
from pathlib import Path

CORE = 'quantcorner-backtesting-webull-mcp'

def sources(source):
    result = {CORE: source}
    manifest = source / 'suite.json'
    if not manifest.exists():
        return result  # Compatibility with the original single-skill distribution.
    data = json.loads(manifest.read_text())
    names = data.get('skills')
    if data.get('schema_version') != 1 or data.get('shared_skill') != CORE or not isinstance(names, list) or not names:
        raise ValueError('Invalid suite manifest')
    if any(not isinstance(n, str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', n) or n == CORE for n in names) or len(set(names)) != len(names):
        raise ValueError('Invalid or duplicate suite skill names')
    for name in names:
        bundled = source / 'skills' / name
        folder = bundled if bundled.exists() else source.parent / name
        if folder.is_symlink() or not (folder / 'SKILL.md').is_file() or (folder / 'SKILL.md').is_symlink():
            raise ValueError('Missing or linked suite source: ' + name)
        if not declared_name(folder, name):
            raise ValueError('Suite source name mismatch: ' + name)
        result[name] = folder
    return result

def declared_name(folder, name):
    try:
        text = (folder / 'SKILL.md').read_text()
        front = text.split('---', 2)[1] if text.startswith('---\n') else ''
        return re.search(r'^name:\s*[\"\']?' + re.escape(name) + r'[\"\']?\s*$', front, re.M) is not None
    except (OSError, UnicodeError, IndexError):
        return False

def copy_public(source, target, core=False):
    target.mkdir()
    files = ['SKILL.md']
    groups = {'agents': {'.yaml'}}
    if core:
        files += ['README.md', 'LICENSE', 'ASSETS_LICENSE.md', 'TESTING.md', 'suite.json',
                  'examples/report.html']
        groups.update({'scripts': {'.py'}, 'tests': {'.py'}, 'references': {'.md'},
                       'assets': {'.svg', '.woff2', '.txt'}})
    for name in files:
        path = source / name
        if path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(source.resolve()):
            dest = target / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
    for folder, suffixes in groups.items():
        for path in (source / folder).rglob('*'):
            if (path.is_file() and not path.is_symlink() and path.suffix in suffixes
                    and '__pycache__' not in path.parts
                    and path.resolve().is_relative_to(source.resolve())):
                dest = target / path.relative_to(source)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dest)

def install(destination, upgrade=False):
    source = Path(__file__).resolve().parents[1]
    members = sources(source)
    parent = Path(destination).expanduser().resolve()
    # Preflight every destination before copying any skill.
    existing = []
    for name in members:
        target = parent / name
        if target.is_symlink():
            raise ValueError('Canonical/linked installation: update its source, not its symlink: ' + name)
        if target.exists():
            if not upgrade:
                raise ValueError('Destination exists. Use --upgrade for a backed-up replacement, or choose another destination.')
            if not target.is_dir() or not declared_name(target, name):
                raise ValueError('Unrecognized destination; preserved: ' + name)
            existing.append(name)
    parent.mkdir(parents=True, exist_ok=True)
    backup = parent / '.quantcorner-backups' / uuid.uuid4().hex
    moved, published = [], []
    with tempfile.TemporaryDirectory(prefix='.quantcorner-stage-', dir=parent) as temp:
        stage = Path(temp)
        for name, folder in members.items():
            copy_public(folder, stage / name, core=name == CORE)
        try:
            if existing:
                backup.mkdir(parents=True)
            for name in existing:
                (parent / name).rename(backup / name)
                moved.append(name)
            for name in members:
                # Never overwrite a concurrent install after preflight.
                if (parent / name).exists() or (parent / name).is_symlink():
                    raise ValueError('Destination changed during installation: ' + name)
                (stage / name).rename(parent / name)
                published.append(name)
        except Exception:
            for name in reversed(published):
                (parent / name).rename(stage / name)
            for name in reversed(moved):
                (backup / name).rename(parent / name)
            raise
    return parent / CORE

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--target', choices=['codex', 'claude'])
    g.add_argument('--destination')
    p.add_argument('--upgrade', action='store_true', help='Back up recognized existing skill folders before replacing; symlinks are never replaced')
    a = p.parse_args()
    try:
        dest = Path.home() / ('.codex' if a.target == 'codex' else '.claude') / 'skills' if a.target else Path(a.destination)
        print(install(dest, a.upgrade))
        if a.upgrade:
            print('Previous folders, when present, are retained under .quantcorner-backups in the destination.')
    except (OSError, ValueError) as e:
        p.exit(2, str(e) + '\n')
