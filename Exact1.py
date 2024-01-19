from sage.all import Matrix, GF, vector

import argparse
import pathlib
import pickle
from time import time
from tqdm import tqdm
from random import sample

from transposeTraces import transposeTraces, getHeader, getNodeVectors
from SelectionVectors import getSelectionVectors, getPlaintexts, reportKeyMatch
from RNR import RNR, getNRN

try:
    Matrix(GF(2), 5, 5).left_kernel_matrix
    left_kernel_matrix = lambda mat: mat.left_kernel_matrix()
except AttributeError:
    # old sage
    left_kernel_matrix = lambda mat: mat.left_kernel().matrix()
    print("Warning: old SAGE detected, using slower kernel method")


def printOutputFLDA(mostProbableKey, numOfNodes, ending, begining, nodesToGoThrough, nOfSkips, numberOfTimes, SUMtime, E, f, t, NRNonly, filtBy, record):
    print('\033[1A', end='\x1b[2K')
    print('\033[1A', end='\x1b[2K')
    print('\033[1A', end='\x1b[2K')
    keyFound=1
    bytesFound=0
    key=[]
    winPos=[]
    for byte in mostProbableKey:
        if byte[0]==-1:
            keyFound=0
        else:
            bytesFound+=1
        key.append(byte[0])
        winPos.append(byte[1])
    if keyFound:
        keyString=""
        for byte in mostProbableKey:
            keyString += hex(byte[0])[2:]
    if keyFound or bytesFound:
        output=""
        if keyFound:
            output+="The key has been successfully recovered: "+keyString+"\n"
        else:
            output+=("The key has been partially recovered, %d bytes missing.\n" % (16-bytesFound))
        output+="key = "+str(key)+"\n"
        output+="These key bytes has been found at the respective nodes:\n"
        output+="filtPos = "+str(winPos)+"\n"
        output+=("Number of skips: %d (%.2f%%).\n" % (nOfSkips, nOfSkips*100/(ending-begining)))
        if nOfSkips/(ending-begining)>.25:
            output+= "Use more traces or lower the window size to reduce this amount\n"
        output+=("Total time taken to perform the attack: %dh%dm%.2fs (%ds), pace:%.4fs/node\n" % ((SUMtime)//(3600), ((SUMtime)//60)%60, (SUMtime)%60, SUMtime, SUMtime/numberOfTimes))
        print(output)
        if record:
            fkey = args.trace_dir / ("Key_FLDA_bytesFound%d_E%d_f%d_t%d_b%d_e%d_NRN%d_filtBy%d.txt" % (bytesFound, E, f, t, NRNonly, begining, ending, filtBy))
            with open(fkey, "w") as file:
                file.write(output)
            print("\nA file \"Key_FLDA_bytesFound%d_E%d_f%d_t%d_NRN%d_b%d_e%d_filtBy%d.txt\" has been created in the traces folder." % (bytesFound, E, f, t, NRNonly, begining, ending, filtBy))
            print("It contains the above displayed information.")
    else:
        print("No key byte has been found, this scheme might be resistant to this attack,             ")
        print("or the window size has been chosen too small.")
        if ending-begining<0.75*numOfNodes:
            print("Perhaps the key bytes can be located elswhere as well.")
        if nOfSkips/(ending-begining)>.25:
            print("Number of skips: %d (%.2f%%).Use more traces or lower the window size to reduce this amount." % (nOfSkips, nOfSkips*100/(ending-begining)))


def ExactMatching1(pathToTraces, t=-1, window=1, begining=0, ending=0, record=1, bytePositions="all", masks='bits'):
    #RECOVERING THE HEADER OF THE NODE VECTORS FILE
    (numOfNodes, T)=getHeader(pathToTraces)

    if t == -1:
        t = T
    else:
        t = min(T, max(128, t))

    NODEVECTORS, *_ = getNodeVectors(pathToTraces, t, begining=begining, ending=ending, NonRedundantNodes=None, silent=0, mode='mat')
    PLAINTEXTS = getPlaintexts(pathToTraces)

    #DEDUCING THE SELECTION VECTORS
    if bytePositions == "all":
        bytePositions = list(range(16))
    else:
        bytePositions = list(map(int, bytePositions.split(",")))
    if masks == 'all':
        masks = list(range(1, 256))
    elif masks == 'bits':
        masks = [2**i for i in range(8)]
    elif masks == "random32":
        masks = [2**i for i in range(8)]
        all_masks = [i for i in range(1, 256) if i not in masks]
        masks += list(sample(all_masks, 24))
    else:
        masks = list(map(int, masks.split(",")))
    print("using bytes:", bytePositions)
    print("using masks:", masks)

    SELECTIONVECTORS, INFO = getSelectionVectors(PLAINTEXTS, t, mode='mat', bytePositions=bytePositions, masks=masks)
    print("selection vectors:", len(SELECTIONVECTORS))
    print("     node vectors:", len(NODEVECTORS))
    print("           traces:", NODEVECTORS[0].nrows())

    for selVec in SELECTIONVECTORS:
        selVec.set_immutable()
    lookup = dict(zip(SELECTIONVECTORS, INFO))

    print("start loop")
    assert window == 1
    #if window == 1:
    for pos, nodeVec in tqdm(enumerate(NODEVECTORS)):
        nodeVec.set_immutable()
        info = lookup.get(nodeVec)
        if info:
            print()
            reportKeyMatch(info, pos=pos)
    # else:
    #     combs = [NODEVECTORS[0] * 0] * (2**window)
    #     # comb[0b10011] = node[i+4] + node[i+1] + node[i+0]
    #     # combs[::2] : 0b10010 >>= 1: 0b1001
    #     for pos, nodeVec in enumerate(tqdm(NODEVECTORS)):
    #         combs = combs[::2]
    #         new = [acc + nodeVec for acc in combs]
    #         for slideMask, accVec in enumerate(new):
    #             accVec.set_immutable()
    #             info = lookup.get(accVec)
    #             if info:
    #                 print()
    #                 reportKeyMatch(info, pos=pos, slideMask=bin(2**window+slideMask)[2:].zfill(window))
    #         combs += new



if __name__ == '__main__' and '__file__' in globals():
    parser = argparse.ArgumentParser(
        description='description to do later',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        'trace_dir', type=pathlib.Path,
        help="path to directory with trace/plaintext/ciphertext files"
    )

    parser.add_argument(
        '-t', '--traces', type=int, default=-1,
        help="number of traces to study"
    )
    parser.add_argument(
        '-w', '--window', type=int, default=5,
        help="sliding window of XORs to consider"
    )

    parser.add_argument(
        '-b', '--node-to-begin', type=int, default=0,
        help="The number of the node where to begin the attack"
    )

    parser.add_argument(
        '-e', '--node-to-end', type=int, default=0,
        help="The number of the node where to end the attack"
    )

    parser.add_argument(
        '-r', '--record', type=int, default=1,
        help="r=1: a file will be created at the end of the attack if at least one byte of the key has been found"
    )

    parser.add_argument(
        '--bytePos', type=str, default="all",
        help="Byte positions ('all' or comma-separated ints, e.g. '0,1,5')"
    )
    parser.add_argument(
        '--masks', type=str, default="bits",
        help="Byte masks ('all', 'bits', 'random32')"
    )

    args = parser.parse_args()

    ExactMatching1(
        args.trace_dir,
        args.traces,
        args.window,
        args.node_to_begin, args.node_to_end, args.record, args.bytePos, args.masks,
    )
