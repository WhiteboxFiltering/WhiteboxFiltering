import argparse
import pathlib
import os
import io
import sys
from time import time

TRACE_HEADER = b"WboxTrac"
TRACE_FOOTER = b"TraceEnd"


def to_bytes(n, length=1, byteorder='big', signed=False):
    if byteorder == 'little':
        order = range(length)
    elif byteorder == 'big':
        order = reversed(range(length))
    else:
        raise ValueError("byteorder must be either 'little' or 'big'")

    return bytes((n >> i*8) & 0xff for i in order)

def transposeTraces(pathToTraces):
    try:
        open(pathToTraces / "nodeVectors.bin", "rb")
        print("The traces are already transposed and contained in the file \"nodeVectors.bin\".")
    except IOError:
        #OPENING TRACE FILE(S) FROM EITHER BU OR SEL  OFFICIAL IMPLEMENTATIONS
        SELorBU=0 #SEL traces = 1, BU traces = 2, not found = 0
        try:
            f = open(pathToTraces / "trace.txt", "rt").readlines()
            SELorBU=1
        except IOError:
            pass
        try:
            numOfBytes = os.path.getsize(pathToTraces / "0000.bin")
            if SELorBU==1:
                print("/!\\ Traces of SEL masking scheme and BU masking scheme are located in the same folder /!\\")
                print("Please separate \"traces.txt\" into a different one and relaunch the program.")
                sys.exit()
            else:
                SELorBU=2
        except IOError:
            pass
        if not SELorBU:
            print("/!\\ The given path to the traces directory does not contain the file \"0000.bin\" or \"traces.txt\" /!\\")
            print("  Either the path is not correct, or the traces are not in the correct format")
            sys.exit()

        #READING TRACE FILE(S), TRANSPOSING THEM AND WRITING THEM INTO nodeVectors.bin
        try:
            #Processing SEL traces
            if SELorBU==1:
                print()
                print()
                with open(pathToTraces / "nodeVectors.bin", "wb") as outputfile:
                    numOfNodes=len(f[0])-1
                    T=len(f)

                    #WRITING HEADER
                    outputfile.write(TRACE_HEADER)
                    outputfile.write(to_bytes(numOfNodes, 4, 'big'))
                    outputfile.write(to_bytes(T, 4, 'big'))

                    #WRITING NODE VECTORS
                    for node in range(numOfNodes):
                        nodeByte=0
                        for traceNumber in range(T):
                            try:
                                nodeByte^=int(f[traceNumber][node]) << (7-traceNumber%8)
                                if traceNumber%8==7:
                                    outputfile.write(to_bytes(nodeByte, 1, 'big'))
                                    nodeByte=0
                            except IndexError:
                                print('\033[1A', end='\x1b[2K')
                                print("/!\\ The trace %d does not have the size as the first one /!\\" % traceNumber)
                                print("Exiting the program.")
                                print("The file \"nodeVectors.txt\" has still been created for the first %d nodes (%.2f%%)" % (node,100*node/numOfNodes))
                                sys.exit()
                        if T % 8:
                            try:
                                outputfile.write(to_bytes(nodeByte, 1, 'big'))
                            except IndexError:
                                print('\033[1A', end='\x1b[2K')
                                print("/!\\ The trace %d does not have the size as the first one /!\\" % traceNumber)
                                print("Exiting the program.")
                                print("The file \"nodeVectors.txt\" has still been created for the first %d nodes (%.2f%%)" % (node,100*node/numOfNodes))
                                sys.exit()
                        if node % 128==0:
                            print('\033[1A', end='\x1b[2K')
                            print("%d/%d (%.2f%%)" % (node, numOfNodes, 100*node/numOfNodes))
                    outputfile.write(TRACE_FOOTER)
                print('\033[1A', end='\x1b[2K')
                print('\033[1A', end='\x1b[2K')
                print("The file \"nodeVectors.bin\" containing all the node vectors has been created.")
            else:
                #Processing BU traces
                numOfNodes = numOfBytes*8
                TRACES=[]
                T = 0
                while True:
                    ftrace = pathToTraces / ("%04d.bin" % T)
                    try:
                        with open(ftrace, "rb") as file:
                            try:
                                TRACES.append(file.read(numOfBytes))
                            except IOError as err:
                                print("/!\\ The trace %04d.bin does not have the size as the trace 0000.bin /!\\" % len(TRACES))
                                print("Exiting the program.")
                                sys.exit()
                            if len(TRACES[-1]) != numOfBytes:
                                print("/!\\ The trace %04d.bin does not have the size as the trace 0000.bin /!\\" % len(TRACES))
                                print("Exiting the program.")
                                sys.exit()
                        T+=1
                        file.close()
                    except IOError as err:
                        break
                #TRANSPOSITION OF TRACES AND WRITING THE NODE VECTORS
                print("Transposing traces...")
                with open(pathToTraces / "nodeVectors.bin", "wb") as outputfile:

                    #WRITING HEADER
                    outputfile.write(TRACE_HEADER)
                    outputfile.write(to_bytes(numOfNodes, 4, 'big'))
                    outputfile.write(to_bytes(T, 4, 'big'))

                    #WRITING NODE VECTORS
                    SUMtime=0
                    numberOfTimes=0
                    for node in range(numOfNodes):
                        t1=time()
                        nodeByte=0
                        for traceNumber in range(T):
                            try:
                                nodeByte ^= ((TRACES[traceNumber][node//8] >> (7-node%8)) & 1) << (7-traceNumber%8)
                                if traceNumber%8==7:
                                    outputfile.write(to_bytes(nodeByte, 1, 'big'))
                                    nodeByte=0
                            except IndexError:
                                print('\033[1A', end='\x1b[2K')
                                print("/!\\ The trace %04d.bin does not have the size as the the trace 0000.bin /!\\" % traceNumber)
                                print("Exiting the program.")
                                print("The file \"nodeVectors.txt\" has still been created for the first %d nodes (%.2f%%)" % (node,100*node/numOfNodes))
                                sys.exit()
                        if T % 8:
                            try:
                                outputfile.write(to_bytes(nodeByte, 1, 'big'))
                            except IndexError:
                                print('\033[1A', end='\x1b[2K')
                                print("/!\\ The trace %04d.bin does not have the size as the the trace 0000.bin /!\\" % traceNumber)
                                print("Exiting the program.")
                                print("The file \"nodeVectors.txt\" has still been created for the first %d nodes (%.2f%%)" % (node,100*node/numOfNodes))
                                sys.exit()
                        t2=time()
                        SUMtime+=t2-t1
                        if node % 128==0:
                            print("node %d/%d (%.2f%%)," % (node, numOfNodes, 100*node/numOfNodes), end="")
                            timeRemaining=SUMtime/(node+1)*(numOfNodes-node)
                            print(" Estimated remaining time: %dh%dm%.2fs                         " % (timeRemaining//3600, (timeRemaining//60)%60, timeRemaining%60), end = "\r")
                    outputfile.write(TRACE_FOOTER)
        except Exception as err:
            if os.path.exists(pathToTraces / "nodeVectors.bin"):
                os.remove(pathToTraces / "nodeVectors.bin")
            print(err)
            sys.exit()
        print()
        print("                                                                          ", end="\r")
        print('\033[1A', end='\x1b[2K')
        print("                                                                          ", end="\r")
        print('\033[1A', end='\x1b[2K')
        print("The file \"nodeVectors.bin\" containing all the node vectors has been created.")


def getHeader(pathToTraces):
    #OPENING THE FILE
    try:
        with open(pathToTraces / "nodeVectors.bin", "rb") as ftrace:
            header=ftrace.read(16)
        assert header[:8] == TRACE_HEADER
        ftrace.close()
    except IOError as err:
        print("Impossible to open the file \"NodeVectors.bin\"")
        print("Please execute first \"sage prepareTraces.sage ./yourPath/toTraces/\"")
        print(err)
        print("Exiting the program.")
        sys.exit()

    #READING THE HEADER
    numOfNodes=int.from_bytes(header[8:12], byteorder='big')
    T=int.from_bytes(header[12:16], byteorder='big')

    return(numOfNodes, T)


#Function openning nodeVectors.bin and returning a list of selction vectors
def getNodeVectors(pathToTraces, requiredT, begining=0, ending=0, NonRedundantNodes=None, silent=0, mode='vect'):
    from sage.all import Matrix, GF, vector
    (numOfNodes, T)=getHeader(pathToTraces)

    #Opens only from the begining index to the ending one
    if ending<=0:
        ending=numOfNodes-ending
    else:
        ending=min(ending, numOfNodes)

    if begining>numOfNodes:
        print("the parameter cannot be chose greater then the number of available nodes (here:%d)" % numOfNodes)
        print("Exiting the program.")
        sys.exit()

    if begining>=ending:
        print("We have b=%d and e=%d:" % (begining,ending))
        print("The parameter \"b\" cannot be chosen greater than the parameter \"e\"")
        print("Exiting the program.")
        sys.exit()

    if requiredT>T:
        print("Only %d traces available, cannot get T=%d traces" % (T, requiredT))
        print("Exiting the program.")
        sys.exit()

    Tbytes=(T+7)//8
    requiredTbytes=(requiredT)//8
    assert requiredT <= T
    assert requiredTbytes <= Tbytes

    #OPENING THE FILE
    try:
        with open(pathToTraces / "nodeVectors.bin", "rb") as ftrace:
            assert ftrace.read(16).startswith(TRACE_HEADER)
            fileBytes=ftrace.read()
        assert fileBytes.endswith(TRACE_FOOTER)
        fileBytes = fileBytes[:-8]
        assert len(fileBytes) == numOfNodes * Tbytes
        ftrace.close()
    except IOError as err:
        print("Impossible to open the file \"NodeVectors.bin\"")
        print("Please execute first \"sage prepareTraces.sage ./yourPath/toTraces/\"")
        print(err)
        print("Exiting the program.")
        sys.exit()

    #If an NRN list is given, it opens only non redudant vectors
    nodesToGoThrough=[]
    if NonRedundantNodes is not None:
        newBegining=0
        while NonRedundantNodes[newBegining]<begining:
            newBegining+=1
        newBegining=max(newBegining-1,0)
        newEnding=newBegining
        while newEnding<len(NonRedundantNodes) and NonRedundantNodes[newEnding]<ending :
            newEnding+=1
        nodesToGoThrough=NonRedundantNodes[newBegining:newEnding]
    else:
        nodesToGoThrough=range(begining,ending)
        newBegining=begining
        newEnding=ending

    #RECOVERING THE NODE VECTORS
    if not silent:
        print("Opening NodeVectors.bin")
        SUMtime=0

    t0 = time()
    NODEVECTORS=[]
    for nodePos in range(len(nodesToGoThrough)):
        node=nodesToGoThrough[nodePos]
        if not silent:
            t1=time()
        nodeVector=[]
        for nodeVecByte in fileBytes[node*Tbytes:node*Tbytes+requiredTbytes]:
            for i in range(8):
                nodeVector.append((nodeVecByte >> (7-i)) & 1)
        if requiredT%8:
            for i in range(requiredT%8):
                nodeVector.append((fileBytes[node*Tbytes+requiredTbytes] >> (7-i)) & 1)
        if mode=='vect':
            # NODEVECTORS.append(vector(GF(2),nodeVector))
            # NODEVECTORS.append(Matrix(GF(2), 1, requiredT, nodeVector))
            NODEVECTORS.append(nodeVector)
        elif mode=='mat':
            NODEVECTORS.append(Matrix(GF(2), 1, requiredT, nodeVector))
        if not silent:
            t2=time()
            SUMtime+=t2-t1
            if node%128==0:
                print("[.] node %d/%d (%.2f%%)," % (nodePos, len(nodesToGoThrough), 100*nodePos/len(nodesToGoThrough)), end="")
                timeRemaining=SUMtime/(nodePos+1)*(len(nodesToGoThrough)-nodePos)
                print(" Estimated remaining time: %dh%02dm%.2fs                         " % (timeRemaining//3600, (timeRemaining//60)%60, timeRemaining%60), end = "\r")

    if not silent:
        print("                                                                                           ", end="")
        print('\033[1A', end='\x1b[2K')

        TOTALtime = time() - t0
        print(
            f"\r[✓] Opened {len(nodesToGoThrough):d} nodes in"
            f" {int(TOTALtime)//3600:d}h{(int(TOTALtime)//60)%60:02d}m{TOTALtime%60:.2f}s"
        )
        print("[.] Converting the node vectors into a matrix")
        t1=time()

    if mode=='fulmat':
        output=(Matrix(GF(2),NODEVECTORS).transpose(), nodesToGoThrough, newBegining, newEnding)

    if mode=='mat':
        output=(NODEVECTORS, nodesToGoThrough, newBegining, newEnding)

    else:
        output=(Matrix(GF(2),NODEVECTORS), nodesToGoThrough, newBegining, newEnding)

    if not silent:
        TOTALtime = time() - t0
        print('\033[1A', end='\x1b[2K')
        print(
            f"\r[✓] Converted the node vectors into a matrix in"
            f" {int(TOTALtime)//3600:d}h{(int(TOTALtime)//60)%60:02d}m{TOTALtime%60:.2f}s"
        )

    return(output)


#@TODO
def writeNodeVectors(vecs, file):
    with open(file, "wb") as f:
        f.write(TRACE_HEADER)
        f.write(to_bytes(len(vecs), 4, 'big'))
        f.write(to_bytes(len(vecs[0]), 4, 'big'))
        T = len(vecs[0])

        for vec in vecs:
            assert len(vec) == T

            nodeByte=0
            for i in range(T):
                nodeByte ^= int(vec[i]) << (7-i%8)
                if i%8==7:
                    f.write(to_bytes(nodeByte, 1, 'big'))
                    nodeByte = 0
            if T % 8:
                f.write(to_bytes(nodeByte, 1, 'big'))
                nodeByte = 0

        f.write(TRACE_FOOTER)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description='description to do later',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        'trace_dir', type=pathlib.Path,
        help="path to directory with trace/plaintext/ciphertext files"
    )

    args = parser.parse_args()

    transposeTraces(args.trace_dir)
