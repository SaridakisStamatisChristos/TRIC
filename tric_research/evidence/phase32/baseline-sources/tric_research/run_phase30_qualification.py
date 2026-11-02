"""Run the frozen Phase XXX campaign sequentially on one pinned CPU."""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def run(build):
    source = Path(__file__).resolve().parent
    build = Path(build).resolve()
    root = source / 'evidence/phase30'
    protocol = json.loads((root / 'qualification_protocol.json').read_text())
    for spec in protocol['runs']:
        output = root / spec['tag'] / 'qualification-final'
        command = [sys.executable, str(source / 'benchmark_native_changes.py'),
                   '--fixtures', str(source / spec['fixtures']),
                   '--output', str(output), '--trials', str(spec['trials']),
                   '--horizons', *map(str, spec['horizons']),
                   '--cap', str(protocol['cap_bytes']), '--cpu', str(protocol['cpu'])]
        for arm in spec['arms']:
            command += ['--arm', arm, str(build / ('previous' if arm == 'previous' else 'candidate')),
                        'auto' if arm in ('previous', 'candidate') else arm]
        print('Starting ' + spec['tag'], flush=True)
        with (build / (spec['tag'] + '.log')).open('w') as log:
            subprocess.run(command, check=True, stdout=log)
        subprocess.run([sys.executable, str(source / 'summarize_native_changes.py'),
                        str(output.parent), '--fixtures', str(source / spec['fixtures'])], check=True)
        print('Completed ' + spec['tag'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', required=True)
    run(parser.parse_args().build)
