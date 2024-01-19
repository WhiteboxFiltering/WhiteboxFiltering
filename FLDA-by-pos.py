from sage.all import Matrix, GF, vector

import argparse
import pathlib
from time import time
import pickle
import gzip
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


def printOutputFLDA(mostProbableKey, numOfNodes, ending, begining, nodesToGoThrough, nOfSkips, numberOfTimes, SUMtime, W, t, f, record):
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
        output+=("Total time taken to perform the attack: %dh%dm%.2fs (%ds)\n" % ((SUMtime)//(3600), ((SUMtime)//60)%60, (SUMtime)%60, SUMtime))
        print(output)
        if record:
            fkey = args.trace_dir / ("Key_FLDA_bytesFound%d_W%d_t%d_f%d_NRNX_b%d_e%d_filtByX.txt" % (bytesFound, W, t, f, begining, ending))
            with open(fkey, "w") as file:
                file.write(output)
            print(f"\nA file \"{fkey}\" has been created in the traces folder.")
            print("It contains the above displayed information.")
    else:
        print("No key byte has been found, this scheme might be resistant to this attack,             ")
        print("or the window size has been chosen too small.")
        if ending-begining<0.75*numOfNodes:
            print("Perhaps the key bytes can be located elswhere as well.")
        if nOfSkips/(ending-begining)>.25:
            print("Number of skips: %d (%.2f%%).Use more traces or lower the window size to reduce this amount." % (nOfSkips, nOfSkips*100/(ending-begining)))


def FLDA(pathToTraces, pathToFRNR, W, t=30, f=-1, begining=0, ending=0, record=1, stoping=1, bytePositions="all", masks='bits', output_friendly=False):

    #RECOVERING THE HEADER OF THE NODE VECTORS FILE
    (numOfNodes, T)=getHeader(pathToTraces)

    if not W%2:
        W+=1
    halfW=W//2

    if f==-1:
        f=min((W+t)+50,T-W-t)

    ##GETTING THE NODE VECTORS
    (NODEVECTORS, nodesToGoThrough, begining, ending) = getNodeVectors(pathToTraces, W+t+f, begining=begining, ending=ending, NonRedundantNodes=None, silent=0)
    numOfNodesVectors=len(nodesToGoThrough)

    #GETTING THE PLAINTEXTS
    PLAINTEXTS = getPlaintexts(pathToTraces)

    print("Reading FRNR relations from", pathToFRNR)
    with gzip.open(pathToFRNR, "rb") as file:
        redundant_relations = pickle.load(file)

    print("Read redundant filter positions:", len(redundant_relations))
    print([red[0] for red in redundant_relations][100:150])

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
    SELECTIONVECTORS, INFO = getSelectionVectors(PLAINTEXTS, W+t+f, mode='fulmat', bytePositions=bytePositions, masks=masks)
    SELECTIONVECTORStr = SELECTIONVECTORS.transpose()

    SELECTIONVECTORS_TABLE = {}
    for guess, row in enumerate(SELECTIONVECTORS):
        row.set_immutable()
        SELECTIONVECTORS_TABLE[row] = guess

    print("\rFiltered Linear Decoding Analysis with the sliding window...\n\n\n")

    mostProbableKey = [[-1,-1] for i in range(16)]

    SUMtime=0
    numberOfTimes=0
    nOfSkips=0

    ONES = vector(GF(2), [1]*len(NODEVECTORS[0]))
    ONESmat = Matrix(GF(2), [[1]*len(NODEVECTORS[0])])
    ONESmatT = ONESmat.transpose()
    try:
        # start from the end, to aim for the S-box output
        for filt_i, sr_rel in enumerate(redundant_relations[::-1]):
            filtPos, sr_filtBy, sr_inds, sr_linIndRows, sr_ker = sr_rel
            # print("filtpos", filtPos, "nvecs", sr_ker.nrows(), "            ")
            # print("sr_inds", sr_inds)
            # print(sr_ker.str())
            # print()
            # print()
            t1=time()
            matrixArray=NODEVECTORS[sr_inds]#.stack(ONESmat)
            Window=Matrix(GF(2), matrixArray).transpose()

            #Flitering
            filtVector=NODEVECTORS[filtPos,:W+t+f][0]
            if sr_filtBy == 1:
                filtColIdx=filtVector.support()[:W+t]
            else:
                filtColIdx=(ONES-filtVector).support()[:W+t]

            if len(filtColIdx) >= W+t:
                #Get only non redundant nodes vector and filtered traces of the window:
                WindowFilt = Window[filtColIdx]
                Sub = WindowFilt * sr_ker.transpose()

                if Sub.ncols() == 1:
                    vec = Sub.transpose()
                    vec.set_immutable()
                    guess = SELECTIONVECTORS_TABLE.get(vec)
                    if guess is not None:
                        if not output_friendly:
                            print('\033[1A', end='\x1b[2K')
                            print('\033[1A', end='\x1b[2K')
                            print('\033[1A', end='\x1b[2K')
                            print(" "*100, end='\r')
                        reportKeyMatch(INFO[guess], filtPpos=nodesToGoThrough[filtPos-1], PCMrows=PCM.nrows())
                        print("\n\n")

                        bytePosition, keyByteGuess, *_ = INFO[guess]
                        if mostProbableKey[bytePosition][0] == -1:
                            mostProbableKey[bytePosition]=[keyByteGuess,nodesToGoThrough[filtPos]]
                        if stoping:
                            keyFound=1
                            for byte in bytePositions:
                                if mostProbableKey[byte][0]==-1:
                                    keyFound=0
                            if keyFound:
                                printOutputFLDA(mostProbableKey, numOfNodes, nodesToGoThrough[filtPos-1], begining, nodesToGoThrough, nOfSkips, numberOfTimes, SUMtime, W, t, f, record)
                                return
                else:
                    Sub = Sub.augment(ONESmatT[:Sub.nrows()])

                    #LDA
                    PCM=left_kernel_matrix(Sub)[:t]
                    # print("PCM", PCM.nrows(), "FILT", len(filtColIdx))
                    # print()
                    # print()
                    # print()

                    selVectors = PCM * SELECTIONVECTORStr[filtColIdx]
                    for guess, selParity in enumerate(selVectors.transpose()):
                        if selParity.is_zero():
                            if not output_friendly:
                                print('\033[1A', end='\x1b[2K')
                                print('\033[1A', end='\x1b[2K')
                                print('\033[1A', end='\x1b[2K')
                                print(" "*100, end='\r')
                            reportKeyMatch(INFO[guess], filtPpos=nodesToGoThrough[filtPos-1], PCMrows=PCM.nrows())
                            print("\n\n")

                            bytePosition, keyByteGuess, *_ = INFO[guess]
                            if mostProbableKey[bytePosition][0] == -1:
                                mostProbableKey[bytePosition]=[keyByteGuess,nodesToGoThrough[filtPos]]
                            if stoping:
                                keyFound=1
                                for byte in bytePositions:
                                    if mostProbableKey[byte][0]==-1:
                                        keyFound=0
                                if keyFound:
                                    printOutputFLDA(mostProbableKey, numOfNodes, nodesToGoThrough[filtPos-1], begining, nodesToGoThrough, nOfSkips, numberOfTimes, SUMtime, W, t, f, record)
                                    return
            else:
                nOfSkips+=1

            t2=time()
            SUMtime+=t2-t1
            numberOfTimes+=1

            if not output_friendly:
                print('\033[1A', end='\x1b[2K')
                print('\033[1A', end='\x1b[2K')
                print('\033[1A', end='\x1b[2K')
                # print("node %d/%d (%.2f%%), solution: " % (nodesToGoThrough[filtPos], numOfNodes, 100*(filtPos)/(numOfNodesVectors)))
                print("filter position %d/%d (filter node %d/%d) (%.2f%%)"
                    % (filt_i, len(redundant_relations), filtPos, numOfNodes, 100*(filt_i)/(len(redundant_relations))))
                print(mostProbableKey[0:8])
                print(mostProbableKey[8:16])
                timeRemaining=SUMtime/numberOfTimes*(len(redundant_relations)-filt_i)
                print("Skips:%d (%.2f%%), estimated remaining time: %dh%dm%.2fs                         " % (nOfSkips, 100*nOfSkips/(filtPos+1), timeRemaining//3600, (timeRemaining//60)%60, timeRemaining%60), end = "\r")
        print("                                                                                         ", end="\r")
    except IOError:
        printOutputFLDA(mostProbableKey, numOfNodes, nodesToGoThrough[filtPos-1], begining, nodesToGoThrough, nOfSkips, numberOfTimes, SUMtime, W, t, f, record)
        return
    printOutputFLDA(mostProbableKey, numOfNodes, nodesToGoThrough[filtPos-1], begining, nodesToGoThrough, nOfSkips, numberOfTimes, SUMtime, W, t, f, record)

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
        '--output-friendly', action='store_true',
        help="Do not print cursor-up sequences"
    )

    parser.add_argument(
        '--frnr', type=pathlib.Path,
        help="path to directory with FRNR files"
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
        '-s', '--stop-when-key-found', type=int, default=1,
        help="Stop when all the 16 bytes of the key has been found"
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

    FLDA(args.trace_dir, args.frnr, args.window_size, args.supplementary_traces_for_false_positives, args.traces_for_filtering, args.node_to_begin, args.node_to_end, args.record, args.stop_when_key_found, args.bytePos, args.masks, args.output_friendly)
