# Security

## Reporting a vulnerability

Do not post credentials, customer/order data, or an exploit containing private data in public issues. Use this repository's **Security → Report a vulnerability** when private reporting is enabled; otherwise contact the repository owner privately. Do not test against a live store without permission.

## Before publishing or deploying

- Commit `.env.example` only. Never commit `.env`, OAuth/SMTP secrets, private keys, database dumps, customer uploads, screenshots of private orders, or production logs.
- Run `python scripts/check_public_repo.py` after staging changes. It checks tracked paths, common credential patterns, and accidental copies of local `.env` secrets without printing their values. This is a safety check, not a comprehensive security audit.
- If a secret was ever committed or exposed, revoke/rotate it immediately. Removing the file in a later commit is not enough; also clean affected history and coordinate with other clones.
- Use a unique administrator username/email/password; `sync_admin` saves a password hash. Restrict access to `.env` on the host. Keep backups encrypted and access-controlled.
- Enable HTTPS, correct trusted hosts/origins, secure cookies and a shared rate-limit cache or reverse-proxy rate limiter in production. Never publicly expose `runserver` or the PostgreSQL port.
- Complete real OAuth callback testing before opening customer registrations; do not loosen the binding requirement as a workaround for missing credentials.
- Configure SMTP before relying on email verification, password recovery or order notifications. Do not publish application logs containing order data or authentication links.
- Test accounts in automated tests and `scripts/preview_test_store.py` are disposable fixtures, never production credentials. The preview script creates an isolated temporary database and only listens on loopback.
- GitHub Actions uses a disposable PostgreSQL service and test-only values. It must not receive production secrets or access the production database. The workflow does not deploy the website.
- Check dependencies regularly and apply supported security updates. Review third-party image/trademark rights before commercial use or redistribution.

## GitHub settings

After creating the public repository, enable available secret scanning, push protection, private vulnerability reporting, and branch protection. Avoid posting `.env` values in issues, pull requests or Actions logs. A public repository is not itself a public deployment of the store.
