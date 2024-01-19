"""
This file is based on the script wboxkit/attacks/trace.py from the wboxkit package.
The modification consists in adding the Chosen-Plaintext Filtering functionality.
"""
import sys, os
import argparse
import random

from pathlib import Path

from wboxkit.fastcircuit import FastCircuit, chunks
from wboxkit.tracing import trace_split_batch
from wboxkit.attacks.reader import Reader

PATH_FORMAT_TRACE = "%04d.bin"
PATH_FORMAT_TMP = ".chunk%04d.bin"
PATH_FORMAT_PT = "%04d.pt"
PATH_FORMAT_CT = "%04d.ct"


def main():
    parser = argparse.ArgumentParser(
        description='''
Trace Boolean circuit serialized by wboxkit on random inputs,
with the Chosen-Plaintext Filtering selection.

This creates `T` traces with half bytes of the input fixed to a constant,
another `T` traces with the other half bytes fixed to (possibly) another constant,
and an extra `epsilon` fully random traces.
'''.strip(),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        'circuit', type=Path,
        help="File with serialized circuit"
    )
    parser.add_argument(
        'traces_dir', type=Path,
        help=(
            "path to directory with trace/plaintext/ciphertext files"
            " (subfolder with the circuit's file_name will be created)"
        )
    )

    parser.add_argument(
        '-H', '--traces-per-half', type=int, default=512,
        help="base number of CPF traces to record per each HALF (half-input fixed )"
    )
    parser.add_argument(
        '-B', '--traces-per-byte', type=int, default=64,
        help="extra number of random traces to record per each BYTE (one byte fixed)"
    )
    parser.add_argument(
        '-R', '--traces-random', type=int, default=0,
        help="extra number of random traces to record (nothing fixed)"
    )

    parser.add_argument(
        '--seed', type=int, default=0,
        help="seed to generate plaintexts"
    )


    args = parser.parse_args()

    NAME = args.circuit.name
    if NAME.endswith(".bin"):
        NAME = NAME[:-4]

    FC = FastCircuit(str(args.circuit))
    n_input_bytes = (FC.info.input_size + 7) // 8

    N_per_half = args.traces_per_half
    N_per_byte = args.traces_per_byte
    N_random = args.traces_random

    N = N_random + N_per_byte * n_input_bytes + N_per_half * 2

    TRACE_FOLDER = args.traces_dir
    PREFIX = TRACE_FOLDER / NAME
    assert "%" not in str(PREFIX)

    print("Tracing", args.circuit, "on", N, "traces")
    print("Saving to", PREFIX)

    PREFIX.mkdir(exist_ok=True)

    random.seed(args.seed)

    inds = list(range(n_input_bytes))
    random.shuffle(inds)
    half1, half2 = inds[:n_input_bytes//2], inds[n_input_bytes//2:]
    const1 = random.randrange(256)
    const2 = random.randrange(256)

    pts = []

    # I: random
    for i in range(N_random):
        pt = [random.getrandbits(8) for _ in range(n_input_bytes)]
        pts.append(bytes(pt))

    # II: byte fixed
    for ibyte in range(n_input_bytes):
        const = const1 if ibyte in half1 else const2
        for _ in range(N_per_byte):
            pt = [random.getrandbits(8) for _ in range(n_input_bytes)]
            pt[ibyte] = const
            pts.append(bytes(pt))

    # III: half fixed
    for i in range(N_per_half):
        pt = [random.getrandbits(8) for _ in range(n_input_bytes)]
        for ibyte in half1:
            pt[ibyte] = const1
        pts.append(bytes(pt))
    for i in range(N_per_half):
        pt = [random.getrandbits(8) for _ in range(n_input_bytes)]
        for ibyte in half2:
            pt[ibyte] = const2
        pts.append(bytes(pt))

    assert len(pts) == N

    # pad to 64 to avoid some bugs
    pts = list(map(bytes, pts))
    while len(pts) % 64:
        pts.append(pts[-1])

    cts = FC.compute_batches(
        inputs=pts,
        trace_filename_format=str(PREFIX / PATH_FORMAT_TMP)
    )
    for i in range((N+63)//64):
        print("splitting", i)
        filename = PREFIX / (PATH_FORMAT_TMP % i)
        trace_split_batch(
            filename=filename,
            make_output_filename=
                lambda j: PREFIX / (PATH_FORMAT_TRACE % (i * 64 + j)),
            ntraces=64,
            packed=True)
        os.unlink(filename)

    for i, (pt, ct) in enumerate(zip(pts, cts)):
        with open(PREFIX / (PATH_FORMAT_PT % i), "wb") as f:
            f.write(pt)
        with open(PREFIX / (PATH_FORMAT_CT % i), "wb") as f:
            f.write(ct)


if __name__ == '__main__':
    main()
