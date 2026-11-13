"""Build a curated source archive; never package local runtime data."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = ('config', 'context_processors', 'django_school_management', 'permission_handlers', 'utilities', 'templates', 'static', 'tests', 'scripts', '.github', 'requirements', 'docs/public')
FILES = ('README.md', 'CONTRIBUTING.md', 'SECURITY.md', 'THIRD_PARTY_NOTICES.md', 'CHANGELOG.md', 'CODE_OF_CONDUCT.md', '.env.example', '.gitignore', '.dockerignore', 'manage.py', 'requirements.txt', 'requirements_minimal.txt', 'setup.cfg', '.coveragerc', 'LICENSE', 'LICENSE.md', 'LICENSE.txt', 'django_school_management/institute/fixtures/bd_cities.json')
EXTENSIONS = {'.py', '.html', '.css', '.js', '.map', '.json', '.txt', '.md', '.rst', '.svg', '.png', '.jpg', '.jpeg', '.webp', '.gif', '.ico', '.woff', '.woff2', '.ttf', '.eot', '.otf', '.yml', '.yaml', '.cfg', '.scss', '.less'}
def allowed(path):
    rel = path.relative_to(ROOT)
    parts = rel.parts
    lower = rel.as_posix().lower()
    if path.is_symlink() or not path.is_file():
        return False
    if any(part in {'__pycache__', 'fixtures', 'node_modules', '.git'} for part in parts):
        return False
    if lower.startswith(('static/ckeditor/', 'static/js/jquery-file-upload/server/')):
        return False
    if path.suffix.lower() == '.json' and not lower.startswith('static/'):
        return False
    if path.name.startswith('.env') and rel.as_posix() != '.env.example':
        return False
    return path.suffix.lower() in EXTENSIONS or path.name.upper().startswith(('LICENSE', 'COPYING', 'NOTICE'))

def main():
    selected = {ROOT / name for name in FILES if (ROOT / name).is_file()}
    for name in DIRECTORIES:
        directory = ROOT / name
        if directory.exists():
            selected.update(p for p in directory.rglob('*') if allowed(p))
    selected = sorted(selected, key=lambda p: p.relative_to(ROOT).as_posix())
    output = ROOT / 'dist'
    output.mkdir(exist_ok=True)
    archive = output / 'edunaij-source-draft.zip'
    manifest = {}
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for path in selected:
            name = path.relative_to(ROOT).as_posix()
            data = path.read_bytes()
            manifest[name] = hashlib.sha256(data).hexdigest()
            bundle.writestr('edunaij/' + name, data)
        bundle.writestr('edunaij/SOURCE_MANIFEST.json', json.dumps(manifest, indent=2) + '\n')
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output / (archive.name + '.sha256')).write_text(checksum + '  ' + archive.name + '\n')
    (output / 'SOURCE_MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Created {archive.name}: {len(manifest)} files. All rights reserved; see LICENSE.')

if __name__ == '__main__':
    main()
