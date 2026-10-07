"""Run the real grant source against mocked database/mail boundaries.
Run from a Visual Studio developer shell: python tests/mantech/test_portable_utility_grants.py
This is a logic regression test, not an in-game mail test.
"""
from pathlib import Path
import subprocess
import tempfile
here = Path(__file__).resolve().parent
root = here.parents[1]
source = (root / 'src/game/Mails/ManTechPortableUtilityGrant.cpp').read_text()
source = '\n'.join(line for line in source.splitlines() if not line.startswith('#include'))
with tempfile.TemporaryDirectory(prefix='mantech-utility-test-') as folder:
    folder = Path(folder)
    test = (here / 'portable_utility_grant_test_prefix.h').read_text() + source + (here / 'portable_utility_grant_test_suffix.cpp').read_text()
    (folder / 'test.cpp').write_text(test)
    subprocess.run(['cl.exe', '/nologo', '/EHsc', '/std:c++17', 'test.cpp', '/Fe:test.exe'], cwd=folder, check=True)
    subprocess.run([str(folder / 'test.exe')], check=True)
