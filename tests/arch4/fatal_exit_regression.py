"""Exercise the production release assertion and Windows crash writer in child processes."""
from pathlib import Path
import json
import shutil
import struct
import subprocess
import sys
import tempfile

probe = Path(sys.argv[1]).resolve()
base = probe.parent / 'fatal-regression'
base.mkdir(exist_ok=True)
assert not base.is_symlink()
results = []
for mode in ('normal', 'assert', 'terminate', 'exception', 'abort', 'seh'):
    with tempfile.TemporaryDirectory(prefix='mantech-fatal-', dir=base) as folder:
        assert Path(folder).resolve().parent == base.resolve()
        destination = Path(folder) / probe.name
        shutil.copy2(probe, destination)
        if probe.with_suffix('.pdb').exists():
            shutil.copy2(probe.with_suffix('.pdb'), destination.with_suffix('.pdb'))
        process = subprocess.run([str(destination), mode], capture_output=True, timeout=30)
        crash = destination.parent / 'Crashes'
        files = list(crash.glob('*'))
        if mode == 'normal':
            assert process.returncode == 0 and not files
        else:
            assert process.returncode != 0, mode
            dumps = list(crash.glob('*.dmp'))
            reports = [p for p in crash.glob('*.txt') if not p.name.startswith('FatalError-')]
            assert dumps and reports, (mode, process.stderr, [p.name for p in files])
            data = dumps[0].read_bytes()
            header = struct.unpack_from('<IIIIIIQ', data)
            assert header[0] == 0x504d444d
            streams = [struct.unpack_from('<III', data, header[3] + i * 12) for i in range(header[2])]
            exception = next(at for kind, size, at in streams if kind == 6)
            code = struct.unpack_from('<I', data, exception + 8)[0]
            if mode in ('assert', 'terminate', 'abort'):
                assert code == 0xC0000420, (mode, hex(code))
                comment = next(data[at:at + size] for kind, size, at in streams if kind == 10)
                expected = {'assert': b'Assertion failed: false', 'terminate': b'std::terminate', 'abort': b'abort / SIGABRT'}[mode]
                assert expected in comment, (mode, comment)
                receipts = list(crash.glob('FatalError-*.txt'))
                assert len(receipts) == 1 and expected in receipts[0].read_bytes()
                if mode == 'assert':
                    assert b'fatal_exit_probe.cpp:' in comment and b'Function: main' in comment
            if mode == 'seh':
                assert code == 0xC0000005
            if mode == 'exception':
                assert code in (0xE06D7363, 0xC0000420)
                assert b'fatal probe exception' in b'\n'.join(p.read_bytes() for p in crash.glob('*.txt'))
                assert b'resource deadlock' not in b'\n'.join(p.read_bytes() for p in crash.glob('*.txt'))
        results.append({'mode': mode, 'exit_code': process.returncode, 'crash_files': len(files)})
print(json.dumps(results, indent=2))
