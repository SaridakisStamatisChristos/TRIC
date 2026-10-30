"""Recreate the exact 37 construction inputs in a new, empty directory."""
import argparse
from pathlib import Path
from verify_phase33_evidence import fixtures, sha, E, read


def materialize(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    assert not any(output.iterdir()),'output directory must be empty'
    for name,(raw,_) in fixtures().items():
        (output/name).write_bytes(raw)
        assert sha((output/name).read_bytes())==read(E/'qualification_v2_protocol.json')['fixtures'][name]
    return len(fixtures())


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output');a=p.parse_args()
    print('Materialized',materialize(a.output),'frozen fixtures')
