import argparse
import pathlib
import os
import io
import sys

from transposeTraces import transposeTraces
from RNR import RNR

parser = argparse.ArgumentParser(
    description='description to do later',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)

parser.add_argument(
    'trace_dirs', type=pathlib.Path, nargs='+',
    help="1 or more paths to directories with trace/plaintext/ciphertext files"
)

parser.add_argument(
    '-W', '--Window', type=int, default=-1,
    help="Window Size for Redundant Node Removal"
)

parser.add_argument(
    '-S', '--Sliding', type=int, default=-1,
    help="Number of nodes to slide after resolving a window for Redundant Node Removal"
)

parser.add_argument(
    '-t', '--falsePos', type=int, default=30,
    help="Exceding number of traces to avoid false-positives"
)

parser.add_argument(
    '--save-relations', action='store_true',
    help="Save redundant relations in a pickle file",
)

parser.add_argument(
    '--no-affine', action='store_true',
    help="Do not remove affine redundancies"
)

args = parser.parse_args()

for trace_dir in args.trace_dirs:
    print("Processing trace folder", trace_dir)
    transposeTraces(trace_dir)
    print()

    try:
        RNR(trace_dir, args.Window, args.Sliding, args.falsePos, save_relations=args.save_relations)
    except Exception as err:
        print("Error:", err)
        print("The file \"nodeVectors.bin\" is corrupted, most likely because the program has been")
        print("interrupted when creating it.")
        print("Removing it and recreating a new one...")
        #If transposeTraces is interrupted halfway through computation, an unfinished
        #nodeVectors.bin file can be created and won't work. This excpetion resolves
        #this problem.
        os.remove(trace_dir / "nodeVectors.bin")
        transposeTraces(trace_dir)
        RNR(trace_dir, args.Window, args.Sliding, args.falsePos, affine=not args.no_affine)
