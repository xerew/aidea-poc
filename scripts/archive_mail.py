#!/usr/bin/env python3
"""Archive an IMAP mailbox to a local .mbox file and delete the archived
messages from the server — to keep a small free-tier mailbox (e.g.
info@aidea-hub.eu, which collects DMARC reports and notifications) under quota.

Safe by design: a message is deleted from the server only after it has been
written to the mbox. Standard library only — no pip installs.

Configure via environment variables:

  MAIL_HOST         IMAP host, e.g. linux53.name-servers.gr   (required)
  MAIL_USER         mailbox login, e.g. info@aidea-hub.eu      (required)
  MAIL_PASSWORD     mailbox password                           (required)
  MAIL_PORT         IMAP-SSL port                              (default 993)
  MAIL_FOLDER       folder to archive                          (default INBOX)
  ARCHIVE_DIR       where to write the mbox files              (default ~/mail-archive)
  OLDER_THAN_DAYS   only archive messages older than N days    (default 0 = all)
  DRY_RUN           set to 1 to only count, archive nothing, delete nothing

Writes one file per month: <local-part>-YYYY-MM.mbox (re-runs append).

Usage:
  set -a; source ~/mail-archive/mail.env; set +a
  python3 archive_mail.py
"""
import email
import imaplib
import mailbox
import os
import sys
from datetime import datetime, timedelta, timezone


def _require(name):
    value = os.environ.get(name)
    if not value:
        sys.exit(f'Missing required env var: {name}')
    return value


def main():
    host = _require('MAIL_HOST')
    user = _require('MAIL_USER')
    password = _require('MAIL_PASSWORD')
    port = int(os.environ.get('MAIL_PORT', '993'))
    folder = os.environ.get('MAIL_FOLDER', 'INBOX')
    archive_dir = os.path.expanduser(os.environ.get('ARCHIVE_DIR', '~/mail-archive'))
    older_than = int(os.environ.get('OLDER_THAN_DAYS', '0'))
    dry_run = os.environ.get('DRY_RUN') == '1'

    os.makedirs(archive_dir, exist_ok=True)
    mbox_path = os.path.join(archive_dir, f'{user.split("@")[0]}-{datetime.now():%Y-%m}.mbox')

    imap = imaplib.IMAP4_SSL(host, port)
    imap.login(user, password)
    imap.select(f'"{folder}"')

    if older_than > 0:
        before = (datetime.now(timezone.utc) - timedelta(days=older_than)).strftime('%d-%b-%Y')
        typ, data = imap.search(None, 'BEFORE', before)
        scope = f'older than {older_than} day(s)'
    else:
        typ, data = imap.search(None, 'ALL')
        scope = 'all messages'
    if typ != 'OK':
        sys.exit(f'IMAP search failed: {typ}')

    ids = data[0].split()
    print(f'{folder}: {len(ids)} message(s) matched ({scope}).')
    if not ids or dry_run:
        if dry_run:
            print('DRY_RUN=1 — nothing archived or deleted.')
        imap.logout()
        return

    box = mailbox.mbox(mbox_path)
    box.lock()
    archived = []
    try:
        for num in ids:
            typ, msg_data = imap.fetch(num, '(RFC822)')
            if typ != 'OK' or not msg_data or msg_data[0] is None:
                print(f'  skip {num.decode()}: fetch failed')
                continue
            box.add(mailbox.mboxMessage(email.message_from_bytes(msg_data[0][1])))
            archived.append(num)
        box.flush()
    finally:
        box.unlock()
        box.close()

    # Delete only what we successfully archived.
    for num in archived:
        imap.store(num, '+FLAGS', '\\Deleted')
    imap.expunge()
    imap.close()
    imap.logout()
    print(f'Archived {len(archived)} message(s) to {mbox_path} and deleted them from the server.')


if __name__ == '__main__':
    main()
