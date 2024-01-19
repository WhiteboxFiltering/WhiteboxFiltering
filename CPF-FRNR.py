from sage.all import Matrix, GF, vector

import sys
import argparse
import pathlib
from time import time
import pickle

from transposeTraces import transposeTraces, getHeader, getNodeVectors
from SelectionVectors import getSelectionVectors, getPlaintexts
from RNR import RNR, getNRN, reduceVectors


def CPF_RNR(pathToTraces, pathToFullFRNR, E, f=30, t=-1, NRNonly=1, filtBy=0, begining=0, ending=0, record=1):
    with open(pathToFullFRNR, "rb") as fullF:
        FullFRNR = pickle.load(fullF)[::-1]

    #RECOVERING THE HEADER OF THE NODE VECTORS FILE
    (numOfNodes, T)=getHeader(pathToTraces)
    W=E+1

    if t==-1:
        t=T-W-f

    requiredT = W + f + t
    print(f"{E=}  {W=} {t=} {f=}, {T=}, {requiredT=}")
    # quit()

    #GETTING THE LIST OF NON REDUNDANT NODE INDICES
    NonRedundantNodes = getNRN(pathToTraces)

    ##GETTING THE NODE VECTORS
    if NRNonly:
        (NODEVECTORS, nodesToGoThrough, begining, ending) = getNodeVectors(pathToTraces, requiredT, begining=begining, ending=ending, NonRedundantNodes=NonRedundantNodes, silent=0)
    else:
        (NODEVECTORS, nodesToGoThrough, begining, ending) = getNodeVectors(pathToTraces, requiredT, begining=begining, ending=ending, NonRedundantNodes=None, silent=0)
    numOfNodesVectors=len(nodesToGoThrough)


    print("\rChosen-Plaintext-Filtered Redundant Node Detection with the sliding window...\n\n\n")

    SUMtime=0
    numberOfTimes=0
    nOfSkips=0
    ONES = vector(GF(2), [1]*len(NODEVECTORS[0]))

    redundants = []
    try:
        if not NRNonly:
            filtPosInNRNlist=0
            while NonRedundantNodes[filtPosInNRNlist]<begining:
                filtPosInNRNlist+=1
        filtPos=0
        while filtPos<numOfNodesVectors:
            t1=time()

            if NRNonly:
                #Get the window
                inds = list(range(max(0,filtPos-E), min(numOfNodesVectors-1,filtPos+E)))
                if filtPos in inds:
                    inds.remove(filtPos)
                matrixArray=NODEVECTORS[inds]
                Window=Matrix(GF(2), matrixArray).transpose()
            else:
                while NonRedundantNodes[filtPosInNRNlist]<filtPos+begining:
                    filtPosInNRNlist+=1
                #Get the window
                inds=[]
                for posInNRNlist in NonRedundantNodes[max(0,filtPosInNRNlist-E) : min(len(NonRedundantNodes)-1,filtPosInNRNlist+E)]:
                    inds.append(min(numOfNodesVectors-1,max(0,(posInNRNlist-begining))))
                if filtPos in inds:
                    inds.remove(filtPos)
                matrixArray=NODEVECTORS[inds]
                Window=Matrix(GF(2), matrixArray).transpose()


            #Flitering
            filtVector=NODEVECTORS[filtPos,:2*W+f+t][0]
            if filtBy == 1:
                filtColIdx=filtVector.support()[:2*W+f]
            else:
                filtColIdx=(ONES-filtVector).support()[:2*W+f]

            if FullFRNR and FullFRNR[-1][0] == filtPos:
                _, FullRedundant = FullFRNR.pop()
                orig_len = len(filtColIdx)
                filtColIdx = sorted(set(filtColIdx) - set(FullRedundant))
                print(f"Skipping full-F-redundant nodes: {orig_len} -> {len(filtColIdx)} ({len(FullRedundant)})")

            if len(filtColIdx) >= 2*W+f:
                #Get only non redundant nodes vector and filtered traces of the window:
                WindowFilt = Window[filtColIdx].transpose()

                linIndRows, _ = reduceVectors(WindowFilt, with_kernel=False)
                if len(linIndRows) < WindowFilt.nrows():
                    off = 0
                    redIndexes = []
                    for i in range(WindowFilt.nrows()):
                        if off < len(linIndRows) and i == linIndRows[off]:
                            off += 1
                            continue
                        if off < len(linIndRows) and i >= linIndRows[off]:
                            assert 0
                        redIndexes.append(i)
                    assert not (set(redIndexes) & set(linIndRows))

                    print("filtPos", filtPos, ":", Window.nrows(), Window.ncols(), "->", WindowFilt.nrows(), WindowFilt.ncols(), "rank", Window.rank(), "->", WindowFilt.rank(), ":", len(redIndexes), "relations")
                    redundants.append([filtPos, redIndexes])
                    print("redundant:", filtPos, ":", redIndexes)
            else:
                nOfSkips+=1

            t2=time()
            SUMtime+=t2-t1
            numberOfTimes+=1

            # print('\033[1A', end='\x1b[2K')
            # print('\033[1A', end='\x1b[2K')
            # print('\033[1A', end='\x1b[2K')
            # print(
            #     "node %d/%d (%.2f%%), solution: " % (nodesToGoThrough[filtPos], numOfNodes, 100*(filtPos)/(numOfNodesVectors)),
            #     "redundant:", len(redundants))
            pace=SUMtime/numberOfTimes
            timeRemaining=pace*(numOfNodesVectors-filtPos)
            # print(
            #     "Pace: %fs/node, skips:%d (%.2f%%), estimated remaining time: %dh%dm%.2fs                         " % (pace, nOfSkips, 100*nOfSkips/(filtPos+1), timeRemaining//3600, (timeRemaining//60)%60, timeRemaining%60),
            #     # end = "\r"
            # )
            filtPos+=1
        # print("                                                                                         ", end="\r")
    except KeyboardInterrupt:
        # printOutputFLDA(mostProbableKey, numOfNodes, nodesToGoThrough[filtPos-1], begining, nodesToGoThrough, nOfSkips, numberOfTimes, SUMtime, E, f, t, NRNonly, filtBy, record)
        sys.exit()
    finally:
        frel = pathToTraces / ("FRNR_E%04d.pkl" % E)
        with open(frel, "wb") as file:
            pickle.dump(redundants, file)
    # printOutputFLDA(mostProbableKey, numOfNodes, nodesToGoThrough[filtPos-1], begining, nodesToGoThrough, nOfSkips, numberOfTimes, SUMtime, E, f, t, NRNonly, filtBy, record)


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
        'full_FRNR', nargs="?", type=pathlib.Path, default="",
        help="path to the base FRNR result to exclude",
    )

    parser.add_argument(
        '-E', '--effective-window-size', type=int, default=100,
        help="size of the effective window size"
    )

    parser.add_argument(
        '-f', '--falsePos', type=int, default=30,
        help="Exceding number of traces to avoid false-positives"
    )

    parser.add_argument(
        '-t', '--traces-for-filtering', type=int, default=-1,
        help="number of traces to study"
    )

    parser.add_argument(
        '-NRN', '--Non-Redundant-Nodes-Only', type=int, default=1,
        help="if NRN==1: the attack will filter only the non redundant nodes, otherwise it will filter every nodes."
    )

    parser.add_argument(
        '-filtBy', '--filtering_mode', type=int, default=0,
        help="filtBy==0: filter only by zeroes, filtBy==1 only by ones"
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

    args = parser.parse_args()

    CPF_RNR(args.trace_dir, args.full_FRNR, args.effective_window_size, args.falsePos, args.traces_for_filtering, args.Non_Redundant_Nodes_Only, args.filtering_mode, args.node_to_begin, args.node_to_end, args.record)
