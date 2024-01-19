from sage.all import Matrix, GF, vector

import argparse
import pathlib
from time import time
import pickle
import gzip
from random import sample

from transposeTraces import transposeTraces, getHeader, getNodeVectors
from SelectionVectors import getSelectionVectors, getPlaintexts, reportKeyMatch
from RNR import RNR, getNRN, reduceVectors

try:
    Matrix(GF(2), 5, 5).left_kernel_matrix
    left_kernel_matrix = lambda mat: mat.left_kernel_matrix()
except AttributeError:
    # old sage
    left_kernel_matrix = lambda mat: mat.left_kernel().matrix()
    print("Warning: old SAGE detected, using slower kernel method")


def FRNR(pathToTraces, W, t=30, f=-1, NRNonly=1, filtBy=0, save_relations=False, save_independent=False, baseNRNpath=None, skip_relations=None, output_friendly=False):
    if skip_relations:
        with gzip.open(skip_relations, "rb") as fsr:
            skip_relations = pickle.load(fsr)[::-1]
    else:
        skip_relations = ()

    #RECOVERING THE HEADER OF THE NODE VECTORS FILE
    (numOfNodes, T)=getHeader(pathToTraces)

    if not W%2:
        W+=1
    halfW=W//2

    if f==-1:
        f=min((W+t)+50,T-W-t)

    print("\rFiltered Redundant Node Removal with the sliding window... W=%d t=%d f=%d\n\n\n" % (W, t, f))

    #GETTING THE LIST OF NON REDUNDANT NODE INDICES
    if baseNRNpath is None:
        NonRedundantNodes = getNRN(pathToTraces)
    else:
        NonRedundantNodes = getNRN(baseNRNpath)

    ##GETTING THE NODE VECTORS
    if NRNonly:
        (NODEVECTORS, nodesToGoThrough, begining, ending) = getNodeVectors(pathToTraces, W+t+f, NonRedundantNodes=NonRedundantNodes, silent=0)
    else:
        (NODEVECTORS, nodesToGoThrough, begining, ending) = getNodeVectors(pathToTraces, W+t+f, NonRedundantNodes=None, silent=0)
    numOfNodesVectors=len(nodesToGoThrough)


    SUMtime=0
    numberOfTimes=0
    nOfSkips=0

    redundant_relations = []
    independent_pairs = []

    nPositionsWithRedundant = 0
    nRedundant = 0
    nIndependent = 0

    ONES = vector(GF(2), [1]*len(NODEVECTORS[0]))
    ONESmat = Matrix(GF(2), [[1]*len(NODEVECTORS[0])])

    if not NRNonly:
        filtPosInNRNlist=0
        while NonRedundantNodes[filtPosInNRNlist]<begining:
            filtPosInNRNlist+=1
    filtPos=0
    while filtPos<numOfNodesVectors:
        t1=time()

        if NRNonly:
            #Get the window
            inds = list(range(max(0,filtPos-halfW), min(numOfNodesVectors-1,filtPos+halfW)))
        else:
            while filtPosInNRNlist < len(NonRedundantNodes) and NonRedundantNodes[filtPosInNRNlist]<filtPos+begining:
                filtPosInNRNlist+=1
            if filtPosInNRNlist >= len(NonRedundantNodes):
                break
            #Get the window
            inds=[]
            for posInNRNlist in NonRedundantNodes[max(0,filtPosInNRNlist-halfW) : min(len(NonRedundantNodes)-1,filtPosInNRNlist+halfW)]:
                inds.append(min(numOfNodesVectors-1,max(0,(posInNRNlist-begining))))

        if skip_relations and skip_relations[-1][0] == filtPos:
            sr_filtPos, sr_filtBy, sr_inds, sr_linIndRows, sr_ker = skip_relations[-1]
            assert sr_filtBy == filtBy, "need to use the same filtBy in relations!"
            # orig = len(inds)
            # print(len(inds), "red", sr_ker.nrows(), " xxxxxxxxxxxxxxxxxxxx")
            inds = sorted(set(inds) & {sr_inds[i] for i in sr_linIndRows})
            # print(len(inds), "\n\n\n")
            # assert len(inds) == l0 - sr_ker.nrows()
            skip_relations.pop()



        if filtPos in inds:
            inds.remove(filtPos)

        matrixArray=NODEVECTORS[inds]
        Window=Matrix(GF(2), matrixArray).transpose()

        #Flitering
        filtVector=NODEVECTORS[filtPos,:W+t+f][0]
        if filtBy == 1:
            filtColIdx=filtVector.support()[:W+t]
        else:
            filtColIdx=(ONES-filtVector).support()[:W+t]

        if len(filtColIdx) >= W+t:
            #Get only non redundant nodes vector and filtered traces of the window:
            WindowFilt = Window[filtColIdx].transpose()
            WindowFilt -= WindowFilt.column(0).outer_product(ONES[:WindowFilt.ncols()])

            linIndRows, ker = reduceVectors(WindowFilt, with_kernel=True)

            nPositionsWithRedundant += int(bool(ker))
            nRedundant += ker.nrows()
            nIndependent += Window.nrows() - ker.nrows()
            if save_relations and ker:
                redundant_relations.append((filtPos, filtBy, inds, linIndRows, ker))
            if save_independent and linIndRows:
                independent_pairs.append((filtPos, linIndRows))
        else:
            nOfSkips+=1

        t2=time()
        SUMtime+=t2-t1
        numberOfTimes+=1

        if not output_friendly:
            print('\033[1A', end='\x1b[2K')
            print("node %d/%d (%.2f%%), filter positions with redundants %d (total redundant %d, independent %d)" % (nodesToGoThrough[filtPos], numOfNodes, 100*(filtPos)/(numOfNodesVectors), nPositionsWithRedundant, nRedundant, nIndependent))
            timeRemaining=SUMtime/numberOfTimes*(numOfNodesVectors-filtPos)
            print("Skips:%d (%.2f%%), estimated remaining time: %dh%dm%.2fs                         " % (nOfSkips, 100*nOfSkips/(filtPos+1), timeRemaining//3600, (timeRemaining//60)%60, timeRemaining%60), end = "\r")
            # print("filtPos", filtPos, "inds", inds, "\n\n\n")
        filtPos+=1
    print("                                                                                         ", end="\r")

    print("Finished!")

    if save_relations:
        frel = pathToTraces / ("FRNrel_W%04d.pkl.gz" % W)
        print("Saving FRNR relations to", frel)
        with gzip.open(frel, "wb", compresslevel=1) as file:
            pickle.dump(redundant_relations, file)

    if save_independent:
        frel = pathToTraces / ("FNRN_W%04d.pkl.gz" % W)
        print("Saving FRNR independent to", frel)
        with gzip.open(frel, "wb", compresslevel=1) as file:
            pickle.dump(independent_pairs, file)


if __name__ == '__main__' and '__file__' in globals():
    parser = argparse.ArgumentParser(
        description='description to do later',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        '--output-friendly', action='store_true',
        help="Do not print cursor-up sequences"
    )

    parser.add_argument(
        'trace_dir', type=pathlib.Path,
        help="path to directory with trace/plaintext/ciphertext files"
    )

    parser.add_argument(
        '-W', '--window-size', type=int, default=50,
        help="Window size"
    )

    parser.add_argument(
        '-t', '--supplementary-traces-for-false-positives', type=int, default=30,
        help="Exceeding number of traces to avoid false-positives"
    )

    parser.add_argument(
        '-f', '--traces-for-filtering', type=int, default=-1,
        help="Supplementary traces to allow filter W+t traces"
    )

    parser.add_argument(
        '-NRN', '--Non-Redundant-Nodes-Only', type=int, default=0,
        help="if NRN==1: the attack will filter only the non redundant nodes, otherwise it will filter every nodes."
    )

    parser.add_argument(
        '-filtBy', '--filtering_mode', type=int, default=0,
        help="filtBy==0: filter only by zeroes, filtBy==1 only by ones"
    )

    parser.add_argument(
        '--save-relations', action='store_true',
        help="Save redundant relations in a pickle file",
    )

    parser.add_argument(
        '--skip-relations', type=pathlib.Path, default=None,
        help="Skip redundant relations from a pickle file",
    )

    parser.add_argument(
        '--save-independent', action='store_true',
        help="Save independent node vector positions in a pickle file",
    )

    parser.add_argument(
        '--baseNRNpath', type=pathlib.Path, default=None,
        help="Base trace folder to pick NRN file",
    )


    args = parser.parse_args()

    FRNR(args.trace_dir, args.window_size, args.supplementary_traces_for_false_positives, args.traces_for_filtering, args.Non_Redundant_Nodes_Only, args.filtering_mode, save_relations=args.save_relations, save_independent=args.save_independent, skip_relations=args.skip_relations, baseNRNpath=args.baseNRNpath, output_friendly=args.output_friendly)
