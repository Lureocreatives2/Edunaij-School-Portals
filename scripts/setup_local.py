"""Create development configuration without overwriting existing settings."""
from pathlib import Path
import secrets
ROOT = Path(__file__).resolve().parents[1]
def main():
    target = ROOT / 'envs' / '.env'
    target.parent.mkdir(exist_ok=True)
    content = (ROOT / '.env.example').read_text(encoding='utf-8')
    content = content.replace('GENERATE_WITH_SETUP_LOCAL', secrets.token_urlsafe(64))
    try:
        with target.open('x', encoding='utf-8') as output:
            output.write(content)
    except FileExistsError:
        print('Existing envs/.env preserved.')
    else:
        print('Created local settings with a unique secret. Do not commit envs/.env.')
if __name__ == '__main__':
    main()
