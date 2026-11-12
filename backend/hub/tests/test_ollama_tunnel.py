"""The ollama-tunnel container's entrypoint: tries each NTUA address in turn and
records the one it is using. Runs the real script with a fake `ssh` on PATH."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

ENTRYPOINT = Path(settings.BASE_DIR).parent / 'docker' / 'ollama-tunnel' / 'entrypoint.sh'
SH = shutil.which('sh')

# Every "connection" fails at once; the third call stops the loop (kills the script).
FAKE_SSH = """#!/bin/sh
host=""
for a in "$@"; do host="$a"; done
n=$(( $(cat "$FAKE_DIR/count" 2>/dev/null || echo 0) + 1 ))
echo "$n" > "$FAKE_DIR/count"
echo "$host|$(cat "$STATUS_FILE")|$*" >> "$FAKE_DIR/calls"
if [ "$n" -ge 3 ]; then kill "$PPID"; fi
exit 255
"""


@unittest.skipUnless(SH, 'needs a POSIX sh')
class TunnelEntrypointTests(SimpleTestCase):
    def run_entrypoint(self, **env):
        work = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, work, ignore_errors=True)
        fake = work / 'ssh'
        fake.write_text(FAKE_SSH, newline='\n')
        fake.chmod(0o755)
        status = work / 'status' / 'ollama-tunnel.json'
        full_env = {
            **os.environ,
            'PATH': f'{work}{os.pathsep}{os.environ["PATH"]}',
            'FAKE_DIR': work.as_posix(),
            'STATUS_FILE': status.as_posix(),
            'RETRY_PAUSE': '0',
            'SSH_REMOTE_USER': 'ngrammatikos',
            **env,
        }
        subprocess.run([SH, ENTRYPOINT.as_posix()], env=full_env, timeout=30, capture_output=True)
        lines = (work / 'calls').read_text().splitlines()
        return [line.split('|', 2) for line in lines]

    def test_tries_each_address_in_turn_and_starts_over(self):
        calls = self.run_entrypoint(SSH_REMOTE_HOSTS='10.0.0.1 10.0.0.2')
        self.assertEqual([c[0] for c in calls],
                         ['ngrammatikos@10.0.0.1', 'ngrammatikos@10.0.0.2', 'ngrammatikos@10.0.0.1'])

    def test_status_file_names_the_address_in_use(self):
        calls = self.run_entrypoint(SSH_REMOTE_HOSTS='10.0.0.1 10.0.0.2')
        self.assertIn('"host": "10.0.0.1"', calls[0][1])
        self.assertIn('"host": "10.0.0.2"', calls[1][1])
        self.assertRegex(calls[0][1], r'"since": "\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ"')

    def test_defaults_to_both_ntua_addresses_and_forwards_ollama(self):
        calls = self.run_entrypoint()
        self.assertEqual([c[0] for c in calls[:2]],
                         ['ngrammatikos@147.102.17.66', 'ngrammatikos@147.102.23.222'])
        self.assertIn('-L 0.0.0.0:11434:127.0.0.1:11434', calls[0][2])
        self.assertIn('ConnectTimeout=', calls[0][2])
