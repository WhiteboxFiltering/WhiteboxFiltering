import os
import argparse
import pathlib
import pickle
import fnmatch
from time import time
from tqdm import tqdm

from sage.all import Matrix, GF, floor

from transposeTraces import  getHeader, getNodeVectors, writeNodeVectors


def extract_relations(pathToTraces, dstTraces, relFile, NRNfile):
    #RECOVERING THE HEADER OF THE NODE VECTORS FILE
    (numOfNodes, T) = getHeader(pathToTraces)

    dstTraces.mkdir(exist_ok=True)

    with open(relFile, "rb") as file:
        relations=pickle.load(file)

    with open(NRNfile, "rb") as file:
        NonRedundantNodes=pickle.load(file)

    #NODEVECTORS = getNodeVectors(pathToTraces, T)[0]
    NODEVECTORS = getNodeVectors(pathToTraces, T, NonRedundantNodes=NonRedundantNodes)[0]
    NODEVECTORS = dict(zip(NonRedundantNodes, NODEVECTORS))

    OUTPUT = []
    for rel in tqdm(relations):
        res = sum(NODEVECTORS[idx] for idx in rel)
        OUTPUT.append(res)

    print("Writing...")
    writeNodeVectors(OUTPUT, dstTraces / "nodeVectors.bin")






if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='description to do later',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        'src_trace_dir', type=pathlib.Path,
        help="1 or more paths to directories with trace/plaintext/ciphertext files"
    )
    parser.add_argument(
        'dst_trace_dir', type=pathlib.Path,
        help="1 or more paths to directories with trace/plaintext/ciphertext files"
    )
    parser.add_argument(
        'rel_file', type=pathlib.Path,
        help="1 or more paths to directories with trace/plaintext/ciphertext files"
    )
    parser.add_argument(
        'NRN_file', type=pathlib.Path,
        help="1 or more paths to directories with trace/plaintext/ciphertext files"
    )

    args = parser.parse_args()
    extract_relations(args.src_trace_dir, args.dst_trace_dir, args.rel_file, args.NRN_file)
