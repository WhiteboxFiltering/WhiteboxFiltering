import sys, os
import argparse
import random

from collections import Counter
from pathlib import Path

PATH_FORMAT_TRACE = "%04d.bin"
PATH_FORMAT_TMP = ".chunk%04d.bin"
PATH_FORMAT_PT = "%04d.pt"
PATH_FORMAT_CT = "%04d.ct"


def symlink(src, dst):
    src = src.resolve()
    if dst.is_symlink() or dst.exists():
        dst.unlink()
    os.symlink(src, dst)


def split_plaintexts_by_most_frequent_byte(plaintexts: list[bytes], verbose=False) -> list[list[int]]:
    """Return list of (16) groups, one per each byte position,
    each group is a list of indexes of plaintexts/traces with the most frequent byte value at the position
    """
    groups = []
    for ibyte in range(len(plaintexts[0])):
        stat = Counter(pt[ibyte] for pt in plaintexts)
        value, cnt = stat.most_common()[0]
        if verbose:
            print(
                f"Creating trace set for byte position {ibyte:2d}:",
                f"most common char {bytes([value])!r}",
                f"({cnt}/{len(plaintexts)} = {cnt/len(plaintexts)*100:.1f}%)",
            )
        inds = [i for i, pt in enumerate(plaintexts) if pt[ibyte] == value]
        groups.append(inds)
    return groups


def main():
    parser = argparse.ArgumentParser(
        description='''
Split a set of traces into groups by the most frequent byte values,
one set per byte position.
'''.strip(),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        'traces_dir', type=Path,
        help=(
            "path to directory with trace/plaintext/ciphertext files"
        )
    )
    args = parser.parse_args()

    DIR = args.traces_dir

    pts = []
    for i in range(2**100):
        fname_pt = DIR / (PATH_FORMAT_PT % i)
        if not fname_pt.exists():
            break
        with open(fname_pt, "rb") as f:
            pt = f.read()
        pts.append(pt)

    if not pts:
        print("No traces found\n")
        return

    for ibyte, group in enumerate(split_plaintexts_by_most_frequent_byte(pts, verbose=True)):
        subdir = DIR.parent / (DIR.name + ".byte%02d" % ibyte)
        subdir.mkdir(exist_ok=True)
        for newi, i in enumerate(group):
            symlink(DIR / (PATH_FORMAT_PT % i), subdir / (PATH_FORMAT_PT % newi))
            symlink(DIR / (PATH_FORMAT_CT % i), subdir / (PATH_FORMAT_CT % newi))
            symlink(DIR / (PATH_FORMAT_TRACE % i), subdir / (PATH_FORMAT_TRACE % newi))


if __name__ == '__main__':
    main()
