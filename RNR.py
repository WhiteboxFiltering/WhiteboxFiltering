import os
import argparse
import pathlib
import pickle
import fnmatch
from time import time

from sage.all import Matrix, GF, floor, vector

from transposeTraces import  getHeader, getNodeVectors

#@TODO
def reduceVectors(vectors, with_kernel=True):
    if not with_kernel:
        return Matrix(GF(2), vectors).pivot_rows(), None

    mat = Matrix(GF(2), vectors)
    return mat.pivot_rows(), mat.left_kernel_matrix()

    '''
    sage: version()
    'SageMath version 10.0, Release Date: 2023-05-20'

    sage: %timeit matrix(GF(2), vecs).left_kernel().matrix()
    1.03 s ± 5.17 ms per loop (mean ± std. dev. of 7 runs, 1 loop each)
    sage: %timeit matrix(GF(2), vecs).left_kernel_matrix()
    99.3 ms ± 957 µs per loop (mean ± std. dev. of 7 runs, 10 loops each)
    sage: %timeit matrix(GF(2), vecs).pivot_rows()
    99.8 ms ± 414 µs per loop (mean ± std. dev. of 7 runs, 10 loops each)

    But when cached...

    sage: %timeit mat.left_kernel().matrix()
    215 ns ± 0.222 ns per loop (mean ± std. dev. of 7 runs, 1,000,000 loops each)
    sage: %timeit mat.left_kernel_matrix()
    1.27 ms ± 1.75 µs per loop (mean ± std. dev. of 7 runs, 1,000 loops each)
    '''

    # failed attempt to optimize by hand:
    ker = Matrix(GF(2), vectors).left_kernel().matrix()

    pivots = []
    x = 0
    for y in range(ker.nrows()):
        while not ker[y,x]:
            x += 1
        pivots.append(x)
    return pivots, ker


#bestNRNfile allows to find the best pickle file containing the indexes of the
#non-redundant nodes, using their names. It returns the window size that has
#been used to create this file with RNR.
def bestNRNfile(pathToTraces):
    correspondingFiles = []
    #Getting all the files called NRN_W
    for root, dirs, files in os.walk(pathToTraces):
        for name in files:
            if fnmatch.fnmatch(name, 'NRN_W*.pkl'):
                correspondingFiles.append(os.path.join(root, name))
    maxValue=0
    if len(correspondingFiles)>1:
        #Getting the biggest value for W
        for file in correspondingFiles:
            value=int(file[-8:-4])
            if value>maxValue:
                maxValue=value
    elif len(correspondingFiles)==1:
        maxValue=int(correspondingFiles[0][-8:-4])
    return maxValue


#Given the path of a folder containing the NRN file, getNRN will load into a
#list all the indexes of the non redundant nodes.
def getNRN(pathToTraces):
    (numOfNodes, T)=getHeader(pathToTraces)
    maxValue=bestNRNfile(pathToTraces)
    if maxValue==0:
        #If no NRN file exists, returns all the list of all the node indexes
        return list(range(numOfNodes))
    else:
        #Else, we open the pickle file and load it in the list
        fNRN = pathToTraces / ("NRN_W%04d.pkl" % maxValue)
        with open(fNRN, "rb") as file:
            return pickle.load(file)


#@TODO
def bestRNrelFile(pathToTraces):
    correspondingFiles = []
    for root, dirs, files in os.walk(pathToTraces):
        for name in files:
            if fnmatch.fnmatch(name, 'RNrel_W*.pkl'):
                correspondingFiles.append(os.path.join(root, name))
    if not correspondingFiles:
        raise IOError("RNrel file not found")
    maxValue=0
    if len(correspondingFiles)>1:
        for file in correspondingFiles:
            value=int(file[-8:-4])
            if value>maxValue:
                maxValue=value
    elif len(correspondingFiles)==1:
        maxValue=int(correspondingFiles[0][-8:-4])
    return maxValue


#@TODO
def getNRrel(pathToTraces):
    maxValue=bestNRNfile(pathToTraces)
    fNRN = pathToTraces / ("RNrel_W%04d.pkl" % maxValue)
    with open(fNRN, "rb") as file:
        return pickle.load(file)

#Main implementation of RNR, see the ReadMe file for more details about the inputs
def RNR(pathToTraces, W=-1, S=-1, t=30, save_relations=False, ignoreExisting=False, extraNRN=None, affine=False):

    #RECOVERING THE HEADER OF THE NODE VECTORS FILE: number of traces and nodes
    (numOfNodes, T) = getHeader(pathToTraces)
    totalNumOfNodes = numOfNodes

    #VERIFYING INPUT PARAMETER
    W=min(W, numOfNodes)
    maxWValue=floor(T-t)
    if W>maxWValue:
        print("/!\\ Not enough traces to perform RNR with window size W=%d /!\\" % W)
        print("With the available T=%d traces, you can choose W%d at maximum." % (T,maxWValue))
        print("Performing RNR with W=%d would require T=%d traces." % (W, W+t))
        return
    if S>W:
        S=W
    if W==0:
        W=maxWValue
    if W==-1:
        W=min(maxWValue,500)
    if S==-1:
        S=max(1,W//6)

    if ignoreExisting:
        maxValue = 0
    else:
        maxValue = bestNRNfile(pathToTraces)

    if maxValue>=W:
        print("A better file containing indices for non redundant nodes (NRN) already exists for W=%d" % maxValue)
        return

    #OPENNING AN EXISTING NRN FILE IF IT EXISTS TO RUN RNR ONTO IT
    if maxValue==0:
        NonRedundantNodes=list(range(numOfNodes))
    else:
        fNRN = pathToTraces / ("NRN_W%04d.pkl" % maxValue)
        with open(fNRN, "rb") as file:
            NonRedundantNodes=pickle.load(file)
        numOfNodes=len(NonRedundantNodes)

    #@TODO
    if extraNRN:
        with open(extraNRN, "rb") as file:
            extraNRN=pickle.load(file)
            orig = len(NonRedundantNodes)
            NonRedundantNodes=sorted(set(NonRedundantNodes) & set(extraNRN))
            print("reduced NRN using extra file:", orig, "->", len(NonRedundantNodes))
    reverseQueue = list(reversed(NonRedundantNodes))

    NonRedundantNodes = []
    T=W+t
    SUMtime=0
    numberOfTimes=0

    #GETTING THE NODE VECTORS
    NODEVECTORS = getNodeVectors(pathToTraces, T)[0]

    if save_relations:
        redundant_relations = []

    slidingWindowPosition=0
    removedNodes=0

    ONES = vector(GF(2), [1]*len(NODEVECTORS[0]))

    #PREPARING FIRST WINDOW
    XORnodesRemoved=True
    while XORnodesRemoved:
        XORnodesRemoved=False

        indexes=revQueuePopN(reverseQueue, W-S)
        windowMatrix=NODEVECTORS[indexes]
        if affine:
            # reduce node vectors (rows) by the all-constant vector
            windowMatrix -= windowMatrix.column(0).outer_product(ONES)
        linIndRows, ker = reduceVectors(windowMatrix, with_kernel=save_relations)

        if len(linIndRows)<len(indexes):
            XORnodesRemoved=True

        # return back independent indexes
        for index in reversed(linIndRows):
            globalIndex = indexes[index]
            reverseQueue.append(globalIndex)
        for index in linIndRows:
            globalIndex = indexes[index]
            if (not NonRedundantNodes) or globalIndex > NonRedundantNodes[-1]:
                NonRedundantNodes.append(globalIndex)
        removedNodes += len(indexes) - len(linIndRows)

        if save_relations:
            for row in ker:
                relation = [index for index, take in zip(indexes, row) if take]
                redundant_relations.append(relation)

    #ACTUAL REDUNDANT NODES REMOVAL
    print("Removing redundant nodes for window size W=%d t=%d  on T=%d traces                   " % (W, t, T))

    t0 = time()
    SUMtime=0
    numberOfTimes=0


    while reverseQueue:
        t1=time()

        indexes=revQueuePopN(reverseQueue, W)
        slidingWindowPosition = indexes[0]
        windowMatrix=NODEVECTORS[indexes]
        if affine:
            # reduce node vectors (rows) by the all-constant vector
            windowMatrix -= windowMatrix.column(0).outer_product(ONES)
        linIndRows, ker = reduceVectors(windowMatrix, with_kernel=save_relations)

        wasEmptied = not reverseQueue

        # return back independent indexes
        for index in reversed(linIndRows):
            globalIndex = indexes[index]
            reverseQueue.append(globalIndex)
        for index in linIndRows:
            globalIndex = indexes[index]
            if (not NonRedundantNodes) or globalIndex > NonRedundantNodes[-1]:
                NonRedundantNodes.append(globalIndex)
        removedNodes += len(indexes) - len(linIndRows)

        if save_relations:
            for row in ker:
                relation = [index for index, take in zip(indexes, row) if take]
                redundant_relations.append(relation)

        # slide W//6 vectors
        revQueuePopN(reverseQueue, S)

        if wasEmptied:
            reverseQueue.clear()

        t2=time()
        SUMtime+=t2-t1
        numberOfTimes+=1
        percentDone=max(slidingWindowPosition,1)/numOfNodes
        remainingTime=((1-percentDone)/percentDone)*SUMtime

        if numberOfTimes%32==0:
            print("[.] node %d/%d (%.2f%%), number of removed XOR nodes so far: %d (%.2f%%), estimated remaining time: %dh%02dm%fs" % (slidingWindowPosition, numOfNodes, percentDone*100, removedNodes, 100*removedNodes/(slidingWindowPosition), remainingTime//3600, (remainingTime//60)%60, remainingTime%60), end="\r")

    TOTALtime = time() - t0
    print("                                                                                           ")
    print('\033[1A', end='\x1b[2K')
    print("[✓] removed XOR nodes: %d (%.2f%%), remaining: %d, time elapsed: %dh%02dm%fs                                   " % (numOfNodes-len(NonRedundantNodes), 100*(numOfNodes-len(NonRedundantNodes))/numOfNodes, len(NonRedundantNodes), TOTALtime//3600, (TOTALtime//60)%60, TOTALtime%60))
    print(" "*101)
    print(" "*101)
    print('\033[1A', end='\x1b[2K')
    print('\033[1A', end='\x1b[2K')

    ftrace = pathToTraces / ("NRN_W%04d.pkl" % W)
    with open(ftrace, "wb") as file:
        pickle.dump(NonRedundantNodes, file)

    if save_relations:
        frel = pathToTraces / ("RNrel_W%04d.pkl" % W)
        with open(frel, "wb") as file:
            pickle.dump(redundant_relations, file)

    if maxValue>0:
        #os.remove(args.trace_dir / ("NRN_W%04d.pkl" % maxValue))
        print("The pickle file \"NRN_W%04d.pkl\" containig the list of all non redudant nodes has been created" % W)
        print("Total number of removed node from the original file: %d (%.2f%%)" % (totalNumOfNodes-len(NonRedundantNodes), 100*(totalNumOfNodes-len(NonRedundantNodes))/totalNumOfNodes))


def revQueuePopN(d, N):
    assert N >= 0
    ret = list(reversed(d[-N:]))
    del d[-N:]
    return ret


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='description to do later',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        'trace_dirs', type=pathlib.Path, nargs='+',
        help="1 or more paths to directories with trace/plaintext/ciphertext files"
    )

    parser.add_argument(
        '-NRN', type=pathlib.Path, default=None,
        help="Extra list for non-redundant nodes",
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

        RNR(trace_dir, extraNRN=args.NRN, W=args.Window, S=args.Sliding, t=args.falsePos, save_relations=args.save_relations, affine=not args.no_affine, ignoreExisting=True)
