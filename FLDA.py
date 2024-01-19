from sage.all import Matrix, GF, vector

import argparse
import pathlib
from time import time
import pickle
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

#Function to generate the file when keuboard interupted or if the attacks is finished
def printOutputFLDA(mostProbableKey, numOfNodes, ending, begining, nodesToGoThrough, nOfSkips, numberOfTimes, SUMtime, W, t, f, NRNonly, filtBy, record):
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
            fkey = args.trace_dir / ("Key_FLDA_bytesFound%d_W%d_t%d_f%d_NRN%d_b%d_e%d_filtBy%d.txt" % (bytesFound, W, t, f, NRNonly, begining, ending, filtBy))
            with open(fkey, "w") as file:
                file.write(output)
            print("\nA file \"Key_FLDA_bytesFound%d_W%d_t%d_f%d_NRN%d_b%d_e%d_filtBy%d.txt\" has been created in the traces folder." % (bytesFound, W, t, f, NRNonly, begining, ending, filtBy))
            print("It contains the above displayed information.")
    else:
        print("No key byte has been found, this scheme might be resistant to this attack,             ")
        print("or the window size has been chosen too small.")
        if ending-begining<0.75*numOfNodes:
            print("Perhaps the key bytes can be located elswhere as well.")
        if nOfSkips/(ending-begining)>.25:
            print("Number of skips: %d (%.2f%%).Use more traces or lower the window size to reduce this amount." % (nOfSkips, nOfSkips*100/(ending-begining)))


#Main implementation of FLDA, see the ReadMe file for more details about the inputs
def FLDA(pathToTraces, W, t=30, f=-1, NRNonly=1, filtBy=0, begining=0, ending=0, record=1, stoping=1, bytePositions="all", masks='bits'):

    #RECOVERING THE HEADER OF THE NODE VECTORS FILE
    (numOfNodes, T)=getHeader(pathToTraces)

    if not W%2:
        W+=1
    halfW=W//2

    if f==-1:
        f=min((W+t)+50,T-W-t)

    #GETTING THE LIST OF NON REDUNDANT NODE INDICES
    NonRedundantNodes = getNRN(pathToTraces)

    ##GETTING THE NODE VECTORS
    if NRNonly:
        (NODEVECTORS, nodesToGoThrough, begining, ending) = getNodeVectors(pathToTraces, W+t+f, begining=begining, ending=ending, NonRedundantNodes=NonRedundantNodes, silent=0)
    else:
        (NODEVECTORS, nodesToGoThrough, begining, ending) = getNodeVectors(pathToTraces, W+t+f, begining=begining, ending=ending, NonRedundantNodes=None, silent=0)
    numOfNodesVectors=len(nodesToGoThrough)

    #GETTING THE PLAINTEXTS
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
    print(f"window parameters: W={W} t={t} f={f} (total traces={W+t+f})")
    SELECTIONVECTORS, INFO = getSelectionVectors(PLAINTEXTS, W+t+f, mode='fulmat', bytePositions=bytePositions, masks=masks)
    SELECTIONVECTORStr = SELECTIONVECTORS.transpose()


    #ACTUAL FLDA
    print("\rFiltered Linear Decoding Analysis with the sliding window...\n\n\n")

    mostProbableKey = [[-1,-1] for i in range(16)]

    SUMtime=0
    numberOfTimes=0
    nOfSkips=0

    ONES = vector(GF(2), [1]*len(NODEVECTORS[0]))
    ONESmat = Matrix(GF(2), [[1]*len(NODEVECTORS[0])])
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
                inds = list(range(max(0,filtPos-halfW), min(numOfNodesVectors-1,filtPos+halfW)))
                if filtPos in inds:
                    inds.remove(filtPos)
                matrixArray=NODEVECTORS[inds].stack(ONESmat)
                Window=Matrix(GF(2), matrixArray).transpose()
            else:
                while filtPosInNRNlist < len(NonRedundantNodes) and NonRedundantNodes[filtPosInNRNlist]<filtPos+begining:
                    filtPosInNRNlist+=1
                if filtPosInNRNlist >= len(NonRedundantNodes):
                    break
                #Get the window
                inds=[]
                for posInNRNlist in NonRedundantNodes[max(0,filtPosInNRNlist-halfW) : min(len(NonRedundantNodes)-1,filtPosInNRNlist+halfW)]:
                    inds.append(min(numOfNodesVectors-1,max(0,(posInNRNlist-begining))))
                if filtPos in inds:
                    inds.remove(filtPos)
                matrixArray=NODEVECTORS[inds].stack(ONESmat)
                Window=Matrix(GF(2), matrixArray).transpose()

            #Flitering
            filtVector=NODEVECTORS[filtPos,:W+t+f][0]
            if filtBy == 1:
                filtColIdx=filtVector.support()[:W+t]
            else:
                filtColIdx=(ONES-filtVector).support()[:W+t]

            if len(filtColIdx) >= W+t:
                #Get only non redundant nodes vector and filtered traces of the window:
                WindowFilt = Window[filtColIdx]

                #LDA
                PCM=left_kernel_matrix(WindowFilt)

                selVectors = PCM * SELECTIONVECTORStr[filtColIdx]
                for guess, selParity in enumerate(selVectors.transpose()):
                    if selParity.is_zero():
                        print('\033[1A', end='\x1b[2K')
                        print('\033[1A', end='\x1b[2K')
                        print('\033[1A', end='\x1b[2K')
                        print(" "*100, end='\r')
                        reportKeyMatch(INFO[guess], filtPpos=nodesToGoThrough[filtPos-1], PCMrows=PCM.nrows())
                        print("\n\n")

                        # print("\n")
                        # print("Pos", filtPos)
                        # print("Matrix:", WindowFilt.nrows(), WindowFilt.ncols())
                        #print("sol", WindowFilt.solve_right(SELECTIONVECTORS[guess,filtColIdx][0]))

                        #print("selvec", SELECTIONVECTORS[guess])
                        #print("selvec", SELECTIONVECTORS[guess,filtColIdx][0])
                        #print("par", PCM*SELECTIONVECTORS[guess,filtColIdx][0])

                        bytePosition, keyByteGuess, *_ = INFO[guess]
                        if mostProbableKey[bytePosition][0] == -1:
                            mostProbableKey[bytePosition]=[keyByteGuess,nodesToGoThrough[filtPos]]
                        if stoping:
                            keyFound=1
                            for byte in bytePositions:
                                if mostProbableKey[byte][0]==-1:
                                    keyFound=0
                            if keyFound:
                                printOutputFLDA(mostProbableKey, numOfNodes, nodesToGoThrough[filtPos-1], begining, nodesToGoThrough, nOfSkips, numberOfTimes, SUMtime, W, t, f, NRNonly, filtBy, record)
                                exit()
            else:
                nOfSkips+=1

            t2=time()
            SUMtime+=t2-t1
            numberOfTimes+=1

            print('\033[1A', end='\x1b[2K')
            print('\033[1A', end='\x1b[2K')
            print('\033[1A', end='\x1b[2K')
            print("node %d/%d (%.2f%%), solution: " % (nodesToGoThrough[filtPos], numOfNodes, 100*(filtPos)/(numOfNodesVectors)))
            print(mostProbableKey[0:8])
            print(mostProbableKey[8:16])
            timeRemaining=SUMtime/numberOfTimes*(numOfNodesVectors-filtPos)
            print("Skips:%d (%.2f%%), estimated remaining time: %dh%dm%.2fs                         " % (nOfSkips, 100*nOfSkips/(filtPos+1), timeRemaining//3600, (timeRemaining//60)%60, timeRemaining%60), end = "\r")
            filtPos+=1
        print("                                                                                         ", end="\r")
    except KeyboardInterrupt:
        printOutputFLDA(mostProbableKey, numOfNodes, nodesToGoThrough[filtPos-1], begining, nodesToGoThrough, nOfSkips, numberOfTimes, SUMtime, W, t, f, NRNonly, filtBy, record)
        exit()
    printOutputFLDA(mostProbableKey, numOfNodes, nodesToGoThrough[filtPos-1], begining, nodesToGoThrough, nOfSkips, numberOfTimes, SUMtime, W, t, f, NRNonly, filtBy, record)

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

    FLDA(args.trace_dir, args.window_size, args.supplementary_traces_for_false_positives, args.traces_for_filtering, args.Non_Redundant_Nodes_Only, args.filtering_mode, args.node_to_begin, args.node_to_end, args.record, args.stop_when_key_found, args.bytePos, args.masks)
