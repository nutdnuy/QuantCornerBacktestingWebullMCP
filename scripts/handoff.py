"""Record cross-skill pointers in a private project; never certify research validity."""
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def members():
    return json.loads((ROOT / 'suite.json').read_text())['skills']

def initialize(workspace):
    w = Path(workspace).expanduser().resolve()
    w.mkdir(parents=True, exist_ok=True)
    project = w / 'project.json'
    if not project.exists():
        old = (w / 'trials.jsonl').exists()
        nested = (w / 'runs/trials.jsonl').exists()
        if old and nested:
            raise ValueError('Two existing trial registries: resolve project lineage before setup; neither was modified')
        project.write_text(json.dumps({'schema_version': 1, 'research_directory': '.' if old else 'runs'}, indent=2)+'\n')
    load_project(w)
    path = w / 'CONTEXT.md'
    if not path.exists():
        path.write_text('# Research context\n\n## Intended learning\nUnresolved.\n\n## Confirmed decisions\nNone recorded yet. Read any existing plan and evidence before interviewing.\n\n## Open questions\nPopulate only unresolved assumptions.\n\n## Evidence and next step\nUse plan.json, data-audit.md, trials.jsonl in the configured research directory, and handoff.json.\n')
    handoff = w / 'handoff.json'
    if not handoff.exists():
        handoff.write_text(json.dumps({'schema_version': 1, 'skill': 'qc-webull-setup', 'status': 'ready', 'next_skill': 'qc-webull-design-strategy', 'artifacts': [], 'note': 'Local workspace initialized; Webull and research assumptions still require inspection.'}, indent=2)+'\n')
    return load_project(w)

def load_project(w):
    obj = json.loads((w / 'project.json').read_text())
    rel = obj.get('research_directory')
    if obj.get('schema_version') != 1 or rel not in ('.', 'runs'):
        raise ValueError('Unsupported project registry location')
    if not (w / rel).resolve().is_relative_to(w.resolve()):
        raise ValueError('Research directory escapes the project')
    return obj

def record(workspace, skill, status, next_skill, artifacts, note):
    w = Path(workspace).expanduser().resolve()
    project = load_project(w)
    names = members()
    if skill not in names or (next_skill is not None and next_skill not in names):
        raise ValueError('Unknown suite skill')
    if status not in ('ready', 'blocked', 'complete'):
        raise ValueError('Unknown handoff status')
    for relative in artifacts:
        path = Path(relative)
        if path.is_absolute() or not (w / path).resolve().is_relative_to(w) or not (w / path).is_file():
            raise ValueError('Artifact must be an existing file within the private workspace')
    event = {'schema_version': 1, 'time': datetime.now(timezone.utc).isoformat(),
             'skill': skill, 'status': status, 'next_skill': next_skill,
             'artifacts': artifacts, 'note': note, 'research_directory': project['research_directory']}
    lock = w / '.handoff.lock'
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    temp = w / '.handoff.tmp'
    try:
        temp.write_text(json.dumps(event, indent=2, ensure_ascii=False)+'\n')
        with (w / 'handoffs.jsonl').open('a') as stream:
            stream.write(json.dumps(event, ensure_ascii=False)+'\n')
            stream.flush(); os.fsync(stream.fileno())
        temp.replace(w / 'handoff.json')
    finally:
        if temp.exists():temp.unlink()
        lock.unlink()
    return event

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace', required=True)
    p.add_argument('--skill', required=True)
    p.add_argument('--status', choices=['ready', 'blocked', 'complete'], required=True)
    p.add_argument('--next-skill')
    p.add_argument('--artifact', action='append', default=[])
    p.add_argument('--note', required=True)
    a = p.parse_args()
    try:
        print(json.dumps(record(a.workspace, a.skill, a.status, a.next_skill, a.artifact, a.note), indent=2, ensure_ascii=False))
    except (OSError, ValueError, KeyError, TypeError) as e:
        p.exit(2, str(e)+'\n')
