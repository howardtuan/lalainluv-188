"""Check the Git index before publishing. Never prints discovered secret values.

Run after `git add` so the scan inspects exactly the staged/tracked content,
not just the working tree. Uses only the standard library in CI. If a local
.env exists, python-dotenv is used to detect accidental copies of its secrets.
This is a guardrail, not a replacement for a dedicated secret scanner/review.
"""
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent
BLOCKED_DIRS = {
    '.venv', 'venv', 'env', 'media', 'staticfiles', 'artifacts', 'backups',
    'uploads', '__pycache__', 'node_modules', '.codex', '.agents', '.claude',
    '.idea', '.vscode', '.pytest_cache', '.tests', 'test-results', 'playwright-report',
}
BLOCKED_SUFFIXES = {'.sqlite3', '.db', '.dump', '.sql', '.backup', '.bak', '.log',
                    '.pyc', '.pyo', '.pem', '.key', '.p12', '.pfx'}
PATTERNS = {
    'private key': rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----',
    'GitHub token': rb'(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})',
    'AWS access key': rb'(?:AKIA|ASIA)[A-Z0-9]{16}',
    'Google API key': rb'AIza[0-9A-Za-z_-]{35}',
    'Google client secret': rb'GOCSPX-[0-9A-Za-z_-]{20,}',
    'Slack token': rb'xox[baprs]-[0-9A-Za-z-]{20,}',
    'Stripe live secret': rb'sk_live_[0-9A-Za-z]{20,}',
}


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, stderr=subprocess.PIPE)


def forbidden_path(name):
    path = PurePosixPath(name)
    filename = path.name.lower()
    return (
        any(part.lower() in BLOCKED_DIRS for part in path.parts)
        or filename == '.env' or (filename.startswith('.env.') and filename != '.env.example')
        or filename == '.envrc' or path.suffix.lower() in BLOCKED_SUFFIXES
        or '.sqlite3-' in filename or filename == 'credentials.json'
        or (filename.endswith('.json') and filename.startswith(('client_secret', 'service_account')))
    )


def main():
    try:
        names = [name.decode('utf-8') for name in git('ls-files', '-z').split(b'\0') if name]
    except subprocess.CalledProcessError:
        print('FAIL: initialize Git and stage the intended source files before scanning.')
        return 1
    if not names:
        print('FAIL: no files in the Git index; stage source files first.')
        return 1
    secrets = {}
    if (ROOT / '.env').exists():
        try:
            from dotenv import dotenv_values
        except ImportError:
            print('FAIL: install requirements.txt to compare staged content with local .env secrets.')
            return 1
        for key, value in dotenv_values(ROOT / '.env').items():
            sensitive = any(word in key.upper() for word in ('SECRET', 'PASSWORD', 'TOKEN', 'PRIVATE_KEY', 'DATABASE_URL'))
            if sensitive and value and len(value) >= 8 and not value.startswith('replace-with-'):
                secrets[key] = value.encode('utf-8')
    issues = []
    for name in names:
        if forbidden_path(name):
            issues.append((name, 'private/generated file must not be tracked'))
            continue
        try:
            content = git('show', ':' + name)
        except subprocess.CalledProcessError:
            issues.append((name, 'cannot read staged content (resolve merge conflicts first)'))
            continue
        for label, pattern in PATTERNS.items():
            if re.search(pattern, content):
                issues.append((name, label + ' pattern detected'))
        for key, value in secrets.items():
            # Short passwords may also be common identifiers/usernames. For
            # these, match credential assignments or URL password positions,
            # rather than substrings of unrelated words (e.g. a URL scheme).
            if len(value) < 16:
                escaped = re.escape(value)
                key_pattern = re.escape(key.encode('utf-8'))
                assignment = rb'(?i)(?:' + key_pattern + rb'|password)[\"\x27]?\s*[:=]\s*[\"\x27]?' + escaped + rb'(?=[\"\x27\s,}]|$)'
                url_password = rb'://[^\s/:]+:' + escaped + rb'@'
                found = re.search(assignment, content) or re.search(url_password, content)
            else:
                found = value in content
            if found:
                issues.append((name, 'contains local .env value for ' + key))
    for name, reason in issues:
        print(f'FAIL: {name}: {reason}')
    if issues:
        print('Do not push. Remove private content from the index and re-run this check.')
        return 1
    print(f'PASS: {len(names)} staged/tracked files; no blocked paths or detected secrets.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
