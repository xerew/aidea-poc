"""Completing .h5p files that lack their H5P libraries — typical of downloads
from H5P.org — with the official H5P Hub's content-type packages
(https://api.h5p.org/v1/content-types/<machineName>, no registration).

The Hub serves only the latest version of each library. When a file needs an
older minor version of a library, h5p.json is pointed at the newer one (H5P
keeps minor versions compatible) and the change is reported."""
import io
import json
import re
import urllib.request
import zipfile

HUB_URL = 'https://api.h5p.org/v1/content-types/{}'
_VERSIONED = re.compile(r'([A-Za-z0-9._]+)-(\d+)\.(\d+)')


def fetch_from_hub(machine_name, timeout=60):
    with urllib.request.urlopen(HUB_URL.format(machine_name), timeout=timeout) as response:
        return response.read()


def _library_folders(names):
    """({machineName: {(major, minor)}}, {unversioned folder names})."""
    versioned, plain = {}, set()
    for name in names:
        if '/' not in name:
            continue
        top = name.split('/', 1)[0]
        match = _VERSIONED.fullmatch(top)
        if match:
            versioned.setdefault(match[1], set()).add((int(match[2]), int(match[3])))
        elif top != 'content':
            plain.add(top)
    return versioned, plain


def complete_from_hub(archive_bytes, fetch=None):
    """Return (new archive bytes, report). The report lists library folders
    added, dependencies moved to a newer minor version, and anything the Hub
    could not provide. A file that already has its libraries is returned as is."""
    fetch = fetch or fetch_from_hub
    source = zipfile.ZipFile(io.BytesIO(archive_bytes))
    meta = json.loads(source.read('h5p.json').decode('utf-8-sig'))
    deps = [d for d in meta.get('preloadedDependencies') or [] if isinstance(d, dict)]
    for dep in deps:  # H5P.org writes versions as text ("1"); compare as numbers
        dep['majorVersion'], dep['minorVersion'] = int(dep['majorVersion']), int(dep['minorVersion'])
    have, plain = _library_folders(source.namelist())
    report = {'added': [], 'upgraded': [], 'missing': []}

    def present(name, version=None):
        if name in plain:
            return True
        return version in have.get(name, set()) if version else name in have

    if present(meta['mainLibrary']) and all(
        present(d['machineName'], (d['majorVersion'], d['minorVersion'])) for d in deps
    ):
        return archive_bytes, report

    hub = zipfile.ZipFile(io.BytesIO(fetch(meta['mainLibrary'])))
    hub_have, _ = _library_folders(hub.namelist())
    for dep in deps:
        wanted = (dep['majorVersion'], dep['minorVersion'])
        if present(dep['machineName'], wanted) or wanted in hub_have.get(dep['machineName'], set()):
            continue
        newer = sorted(v for v in hub_have.get(dep['machineName'], set()) if v[0] == wanted[0] and v[1] > wanted[1])
        if newer:
            report['upgraded'].append(f"{dep['machineName']} {wanted[0]}.{wanted[1]} → {newer[-1][0]}.{newer[-1][1]}")
            dep['minorVersion'] = newer[-1][1]
        else:
            report['missing'].append(f"{dep['machineName']}-{wanted[0]}.{wanted[1]}")

    report['added'] = sorted(
        f'{name}-{major}.{minor}'
        for name, versions in hub_have.items() for major, minor in versions
        if (major, minor) not in have.get(name, set()) and name not in plain
    )
    added = set(report['added'])
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as target:
        for info in source.infolist():
            if info.is_dir():
                continue
            data = json.dumps(meta, ensure_ascii=False, indent=2) if info.filename == 'h5p.json' else source.read(info)
            target.writestr(info.filename, data)
        for info in hub.infolist():
            if not info.is_dir() and info.filename.split('/', 1)[0] in added:
                target.writestr(info.filename, hub.read(info))
    return out.getvalue(), report
