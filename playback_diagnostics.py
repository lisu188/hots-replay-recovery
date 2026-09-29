from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from pathlib import Path, PureWindowsPath

MAX_INPUT = 64 * 1024 * 1024


def digest(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bounded_bytes(path: Path) -> bytes:
    if not 0 < Path(path).stat().st_size <= MAX_INPUT:
        raise ValueError('Diagnostic input exceeds the supported size bounds')
    raw = Path(path).read_bytes()
    if len(raw) > MAX_INPUT:
        raise ValueError('Diagnostic input changed beyond the supported size bounds')
    return raw


def read_text(path: Path) -> str:
    raw = bounded_bytes(path)
    encoding = 'utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'
    return raw.decode(encoding, errors='strict')


def minidump_exception(raw: bytes) -> dict:
    def unpack(fmt: str, offset: int, limit: int | None = None):
        size = struct.calcsize(fmt)
        if offset < 0 or offset + size > (len(raw) if limit is None else limit):
            raise ValueError('Truncated or out-of-bounds minidump structure')
        return struct.unpack_from(fmt, raw, offset)

    if len(raw) < 32 or raw[:4] != b'MDMP':
        raise ValueError('Not a Windows minidump')
    count, directory = unpack('<II', 8)
    if not 1 <= count <= 1024 or directory + count * 12 > len(raw):
        raise ValueError('Invalid minidump stream directory')
    streams = {}
    for index in range(count):
        kind, size, offset = unpack('<III', directory + index * 12)
        if offset + size > len(raw):
            raise ValueError('Minidump stream is outside the file')
        if kind in (6, 7):
            if kind in streams:
                raise ValueError('Duplicate minidump diagnostic stream')
            streams[kind] = (offset, size)
    if 6 not in streams or streams[6][1] < 168:
        raise ValueError('Minidump has no complete exception stream')
    offset, _ = streams[6]
    thread, = unpack('<I', offset)
    code, = unpack('<I', offset + 8)
    address, = unpack('<Q', offset + 24)
    parameters, = unpack('<I', offset + 32)
    if parameters > 15:
        raise ValueError('Invalid exception parameter count')
    information = unpack(f'<{parameters}Q', offset + 40) if parameters else ()
    size, context = unpack('<II', offset + 160)
    if context + size > len(raw):
        raise ValueError('Minidump context is outside the file')
    result = {'exception_code': f'0x{code:08x}', 'instruction_address': hex(address),
              'thread_id': thread, 'architecture': None, 'access_operation': None,
              'access_address': None, 'rcx': None, 'rip': None}
    if code == 0xC0000005 and parameters >= 2:
        result['access_operation'] = {0: 'read', 1: 'write', 8: 'execute'}.get(information[0], 'unknown')
        result['access_address'] = hex(information[1])
    if 7 in streams:
        system, length = streams[7]
        if length < 2:
            raise ValueError('Truncated minidump system information')
        architecture, = unpack('<H', system)
        result['architecture'] = architecture
        if architecture == 9:
            if size < 256:
                raise ValueError('Truncated AMD64 exception context')
            flags, = unpack('<I', context + 48, context + size)
            if flags & 0x100000 != 0x100000 or flags & 3 != 3:
                raise ValueError('AMD64 integer/control registers are unavailable')
            result['rcx'] = hex(unpack('<Q', context + 128, context + size)[0])
            result['rip'] = hex(unpack('<Q', context + 248, context + size)[0])
    return result


def field(text: str, name: str) -> str | None:
    match = re.search(r'^' + re.escape(name) + r'[ \t]+([^\r\n]+)', text, re.MULTILINE)
    return match.group(1).strip() if match else None


def executable_build(value: str | None) -> int | None:
    match = re.search(r'[\\/]Base(\d+)[\\/]HeroesOfTheStorm_x64\.exe', value or '', re.IGNORECASE)
    return int(match.group(1)) if match else None


def active_installation(text: str) -> dict | None:
    lines = text.strip().splitlines()
    if not lines:
        return None
    keys = [key.split('!', 1)[0] for key in lines[0].split('|')]
    active = []
    for line in lines[1:]:
        values = line.split('|')
        if len(values) != len(keys):
            raise ValueError('Malformed build-info row')
        row = dict(zip(keys, values))
        if row.get('Active') == '1':
            version = row.get('Version', '')
            if not re.fullmatch(r'\d+\.\d+\.\d+\.\d+', version):
                raise ValueError('Invalid active installation version')
            active.append({'version': version, 'build': int(version.rsplit('.', 1)[1]),
                           'build_key': row.get('Build Key', '').lower(),
                           'cdn_key': row.get('CDN Key', '').lower()})
    if len(active) > 1:
        raise ValueError('Multiple active installation rows require explicit selection')
    return active[0] if active else None


def analyze_crash(log: str, dump: bytes | None = None, variables: str | None = None,
                  build_info: str | None = None) -> dict:
    executing = executable_build(field(log, 'Executable'))
    launcher = executable_build(field(log, 'Grandparent Executable'))
    summary = field(log, '<BlizzardError.Summary>') or ''
    failure = re.search(r'ACCESS_VIOLATION\s+(reading|writing|executing)\s+(?:from|to|at)\s+(0x[0-9a-f]+)', summary, re.I)
    ip = re.search(r'DBG-ADDR<([0-9A-Fa-f]+)>', summary)
    rcx = re.search(r'^\s*RCX:([0-9A-Fa-f]+)', log, re.M)
    instruction = None
    if ip:
        row = re.search(r'DBG-CODEBYTES<\s*' + ip.group(1) + r':\s*([0-9A-Fa-f\s]+)>', log, re.I)
        if row:
            instruction = bytes.fromhex(row.group(1))[:4].hex(' ')
    access = {'reading': 'read', 'writing': 'write', 'executing': 'execute'}
    exception = {'code': '0xc0000005' if failure else None,
                 'operation': access[failure.group(1).lower()] if failure else None,
                 'address': hex(int(failure.group(2), 16)) if failure else None,
                 'instruction_address': hex(int(ip.group(1), 16)) if ip else None,
                 'rcx': hex(int(rcx.group(1), 16)) if rcx else None,
                 'instruction_bytes': instruction}
    version = field(log, '<Version>')
    if version and not re.fullmatch(r'\d+\.\d+\.\d+\.\d+', version):
        raise ValueError('Invalid crashing executable version')
    if executing is None or failure is None:
        raise ValueError('Log lacks the supported executable/access-violation evidence')
    if version and int(version.rsplit('.', 1)[1]) != executing:
        raise ValueError('Crash version and executable path disagree')
    confirmed = exception['operation'] == 'read' and exception['address'] == '0x78' and exception['rcx'] == '0x0' and instruction == '48 8b 41 78'
    result = {'format': 'hots-playback-diagnostic-v1', 'outcome': 'client-crashed',
              'executing_build': executing, 'executing_version': version,
              'launcher_build': launcher, 'version_switch_observed': launcher is not None and launcher != executing,
              'exception': exception, 'null_member_read_confirmed': confirmed,
              'root_cause_established': False, 'client_playback_validated': False,
              'symbolized_fault_function': None,
              'instruction': 'mov rax, qword ptr [rcx+0x78]' if confirmed else None}
    if variables is not None:
        value = re.search(r'^lastReplayFilePath=(.+)$', variables, re.M)
        result['last_replay_basename'] = PureWindowsPath(value.group(1).strip()).name if value else None
    if build_info is not None:
        result['installation'] = active_installation(build_info)
        installed = result['installation']
        result['installation_matches_launcher'] = installed['build'] == launcher if installed and launcher else None
    if dump is not None:
        result['minidump'] = minidump_exception(dump)
        pairs = [('code', 'exception_code'), ('address', 'access_address'), ('operation', 'access_operation'),
                 ('instruction_address', 'instruction_address'), ('rcx', 'rcx')]
        for left, right in pairs:
            if exception[left] is not None and result['minidump'][right] is not None and exception[left] != result['minidump'][right]:
                raise ValueError(f'Text log and minidump disagree on {left}')
        result['minidump_confirms_text_exception'] = result['minidump']['exception_code'] == exception['code'] and result['minidump']['access_address'] == exception['address']
    result['limitations'] = ['The immediate invalid memory access does not identify the missing object or upstream cause.',
                             'A version-switch observation does not prove a failed download or corrupt installation.',
                             'A build-info version is not a substitute for exact replay schema and compatibility metadata.']
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--crash-log', type=Path, required=True)
    parser.add_argument('--dump', type=Path)
    parser.add_argument('--variables', type=Path)
    parser.add_argument('--build-info', type=Path)
    parser.add_argument('--replay', type=Path)
    parser.add_argument('--expected-replay-sha256')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    result = analyze_crash(read_text(args.crash_log), bounded_bytes(args.dump) if args.dump else None,
                           read_text(args.variables) if args.variables else None,
                           read_text(args.build_info) if args.build_info else None)
    result['input_sha256'] = {key: digest(path) for key, path in
                             [('crash_log', args.crash_log), ('minidump', args.dump),
                              ('variables', args.variables), ('build_info', args.build_info)] if path}
    if args.replay:
        actual = hashlib.sha256(bounded_bytes(args.replay)).hexdigest()
        if args.expected_replay_sha256 and actual != args.expected_replay_sha256.lower():
            raise ValueError('Replay hash differs from the expected candidate')
        result['replay_sha256'] = actual
        result['replay_basename_matches_variables'] = args.replay.name == result.get('last_replay_basename')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write('\n')
    print(json.dumps({'outcome': result['outcome'], 'executing_build': result['executing_build'],
                      'launcher_build': result['launcher_build'], 'root_cause_established': False}))


if __name__ == '__main__':
    main()
