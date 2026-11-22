"""Copy the locked browser libraries into Django static assets."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
LIBRARIES = {
    'bootstrap': ('vendor/bootstrap', {
        'dist/css/bootstrap.min.css': 'bootstrap.min.css',
        'dist/js/bootstrap.bundle.min.js': 'bootstrap.bundle.min.js',
    }),
    'jquery': ('js/vendor', {'dist/jquery.min.js': 'jquery-3.8.0.min.js'}),
    'datatables.net': ('vendor/datatables', {'js/dataTables.min.js': 'dataTables.min.js'}),
    'datatables.net-bs5': ('vendor/datatables', {
        'js/dataTables.bootstrap5.min.js': 'dataTables.bootstrap5.min.js',
        'css/dataTables.bootstrap5.min.css': 'dataTables.bootstrap5.min.css',
    }),
    '@fortawesome/fontawesome-free': ('vendor/fontawesome', {
        'css/all.min.css': 'css/all.min.css',
        'css/v4-shims.min.css': 'css/v4-shims.min.css',
    }),
    'select2': ('vendor/select2', {
        'dist/js/select2.min.js': 'select2.min.js',
        'dist/css/select2.min.css': 'select2.min.css',
    }),
}


def main():
    versions = json.loads((ROOT / 'package.json').read_text())['dependencies']
    manifest = {}
    for package, (directory, files) in LIBRARIES.items():
        source = ROOT / 'node_modules' / package
        metadata = json.loads((source / 'package.json').read_text())
        if metadata['version'] != versions[package]:
            raise SystemExit(f'{package} version differs from package.json. Run npm ci.')
        destination = ROOT / 'static' / directory
        destination.mkdir(parents=True, exist_ok=True)
        for relative, name in files.items():
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / relative, target)
            manifest[target.relative_to(ROOT / 'static').as_posix()] = {
                'package': package, 'version': metadata['version'],
                'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
            }
            source_map = source / (relative + '.map')
            if source_map.is_file():
                shutil.copyfile(source_map, destination / (name + '.map'))
        if package == '@fortawesome/fontawesome-free':
            for font in (source / 'webfonts').iterdir():
                if font.is_file():
                    target = destination / 'webfonts' / font.name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(font, target)
                    manifest[target.relative_to(ROOT / 'static').as_posix()] = {
                        'package': package, 'version': metadata['version'],
                        'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                    }
        license_file = next((source / name for name in ('LICENSE', 'LICENSE.txt', 'License.txt', 'license.txt', 'LICENSE.md') if (source / name).is_file()), None)
        if license_file is None:
            raise SystemExit(f'Missing licence for {package}')
        shutil.copyfile(license_file, destination / (package.replace('.', '-').replace('/', '-').lstrip('@') + '-LICENSE.txt'))
    target = ROOT / 'static' / 'vendor' / 'manifest.json'
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(manifest, indent=2) + '\n')
    print('Vendored locked frontend libraries with licence notices and file hashes.')


if __name__ == '__main__':
    main()
