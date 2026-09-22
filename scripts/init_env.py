"""Create .env without overwriting existing configuration."""
import secrets
from pathlib import Path
root = Path(__file__).resolve().parent.parent
target = root / '.env'
if target.exists():
    print('.env already exists; unchanged.')
else:
    content = (root / '.env.example').read_text(encoding='utf-8')
    content = content.replace('replace-with-a-random-secret-at-least-50-characters-long', secrets.token_urlsafe(64))
    content = content.replace('replace-with-a-random-url-safe-password', secrets.token_urlsafe(32))
    content = content.replace('replace-with-a-unique-strong-password', secrets.token_urlsafe(30))
    target.write_text(content, encoding='utf-8')
    print('.env created with generated secrets.')
