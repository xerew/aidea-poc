"""Checking and unpacking uploaded .h5p files (zip archives) — see
docs/superpowers/specs/2026-10-08-h5p-activities-design.md.

An upload must be a real H5P package (h5p.json + content/content.json) that
bundles the libraries it needs, hold only file types H5P itself allows, stay
inside its folder, and stay within the size limits. Nothing is left on disk
when a check fails."""
import json
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

MAX_FILE_BYTES = 100 * 1024 * 1024
MAX_UNPACKED_BYTES = 300 * 1024 * 1024
MAX_ENTRIES = 10000

# H5P core's default whitelist, minus swf.
ALLOWED_EXTENSIONS = frozenset(
    'json png jpg jpeg gif bmp tif tiff svg eot ttf woff woff2 otf webm mp4 ogg mp3 m4a '
    'wav txt pdf rtf doc docx xls xlsx ppt pptx odt ods odp xml csv diff patch md textile '
    'vtt webvtt gltf glb js css'.split()
)

# Content types that never report "finished": learners mark them done themselves.
SELF_COMPLETE_LIBRARIES = frozenset({
    'H5P.Accordion', 'H5P.Agamotto', 'H5P.Chart', 'H5P.Collage', 'H5P.Dialogcards',
    'H5P.IFrameEmbed', 'H5P.ImageHotspots', 'H5P.ImageJuxtaposition', 'H5P.ImageSlider',
    'H5P.Link', 'H5P.Table', 'H5P.Timeline',
})


class H5PError(Exception):
    def __init__(self, code, detail):
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass
class PackageInfo:
    title: str
    main_library: str
    unpacked_bytes: int


def default_self_complete(main_library):
    return main_library in SELF_COMPLETE_LIBRARIES


def _ignored(name):
    return name.startswith('__MACOSX/') or PurePosixPath(name).name.startswith('.')


def _check_entries(members):
    if len(members) > MAX_ENTRIES:
        raise H5PError('too_many_files', 'The package contains too many files.')
    total = sum(info.file_size for info in members)
    if total > MAX_UNPACKED_BYTES:
        raise H5PError('too_large_unpacked', 'The package is too large once unpacked.')
    for info in members:
        name = info.filename
        path = PurePosixPath(name)
        if name.startswith('/') or '\\' in name or ':' in name or '..' in path.parts:
            raise H5PError('unsafe_path', f'Unsafe file path in package: {name}')
        if path.suffix.lower().lstrip('.') not in ALLOWED_EXTENSIONS:
            raise H5PError('bad_extension', f'File type not allowed in an H5P package: {path.name}')
    return total


def _read_meta(archive, names):
    if 'h5p.json' not in names:
        raise H5PError('no_h5p_json', 'h5p.json is missing — this is not an H5P package.')
    if 'content/content.json' not in names:
        raise H5PError('no_content', 'content/content.json is missing.')
    try:
        meta = json.loads(archive.read('h5p.json').decode('utf-8-sig'))
    except (ValueError, UnicodeDecodeError) as exc:
        raise H5PError('no_h5p_json', 'h5p.json cannot be read.') from exc
    if not isinstance(meta, dict) or not isinstance(meta.get('mainLibrary'), str) or not meta['mainLibrary']:
        raise H5PError('no_h5p_json', 'h5p.json does not name a main library.')
    return meta


def _has_library(names, machine_name, version=''):
    """A library folder is 'Name-1.2/' (current exports) or 'Name/' (exports
    from 2014–2015, which the player also understands)."""
    prefixes = (f'{machine_name}-{version}/' if version else f'{machine_name}-', f'{machine_name}/')
    return any(n.startswith(prefixes) for n in names)


def _check_libraries(meta, names):
    deps = [d for d in meta.get('preloadedDependencies') or [] if isinstance(d, dict)]
    missing = [
        f"{d.get('machineName')}-{d.get('majorVersion')}.{d.get('minorVersion')}" for d in deps
        if not _has_library(names, d.get('machineName'), f"{d.get('majorVersion')}.{d.get('minorVersion')}")
    ]
    if not _has_library(names, meta['mainLibrary']) and meta['mainLibrary'] not in ' '.join(missing):
        missing.insert(0, meta['mainLibrary'])
    if missing:
        raise H5PError(
            'missing_libraries',
            "This file doesn't include its H5P libraries — export it again with libraries "
            f"included. Missing: {', '.join(missing)}",
        )


def extract_package(fileobj, dest):
    """Check an .h5p archive and unpack it into `dest` (created here)."""
    dest = Path(dest)
    try:
        archive = zipfile.ZipFile(fileobj)
    except (zipfile.BadZipFile, OSError, ValueError) as exc:
        raise H5PError('not_zip', 'This is not a valid .h5p file.') from exc
    with archive:
        members = [i for i in archive.infolist() if not i.is_dir() and not _ignored(i.filename)]
        total = _check_entries(members)
        names = {i.filename for i in members}
        meta = _read_meta(archive, names)
        _check_libraries(meta, names)
        try:
            dest.mkdir(parents=True)
            root = dest.resolve()
            for info in members:
                target = (dest / info.filename).resolve()
                if root not in target.parents:
                    raise H5PError('unsafe_path', f'Unsafe file path in package: {info.filename}')
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as src, open(target, 'wb') as out:
                    shutil.copyfileobj(src, out)
        except zipfile.BadZipFile as exc:
            shutil.rmtree(dest, ignore_errors=True)
            raise H5PError('not_zip', 'This is not a valid .h5p file.') from exc
        except BaseException:
            shutil.rmtree(dest, ignore_errors=True)
            raise
    title = meta.get('title') if isinstance(meta.get('title'), str) else ''
    return PackageInfo(title=title[:255], main_library=meta['mainLibrary'][:100], unpacked_bytes=total)


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if value != value or value in (float('inf'), float('-inf')):
        return None
    return value


def clean_result(raw):
    """The learner's first finished attempt as sent by the page, reduced to
    known fields: raw/max score, success, duration, language and package.
    Returns None when `raw` is not a dict."""
    from hub.translation import LANGUAGE_NAMES
    if not isinstance(raw, dict):
        return None
    out = {}
    score_max, score_raw = _number(raw.get('max')), _number(raw.get('raw'))
    if score_max is not None and score_max > 0 and score_raw is not None:
        out['max'] = score_max
        out['raw'] = min(max(score_raw, 0), score_max)
    if isinstance(raw.get('success'), bool):
        out['success'] = raw['success']
    duration = _number(raw.get('duration_s'))
    if duration is not None and duration >= 0:
        out['duration_s'] = round(min(duration, 86400), 1)
    language = raw.get('language')
    if isinstance(language, str) and (language == '' or language in LANGUAGE_NAMES):
        out['language'] = language
    for key in ('package_id', 'package_version'):
        value = raw.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and value > 0:
            out[key] = value
    return out
