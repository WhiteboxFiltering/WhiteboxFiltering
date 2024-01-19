White-box filtering attacks breaking SEL masking
================================================

This repository contains implementations and logs for the paper 

> **White-box filtering attacks breaking SEL masking: from exponential to polynomial time**.

##### Requirements

Scripts require [SageMath](https://www.sagemath.org) of version at least 10.0, together with `wboxkit`, `tqdm` and `binteger` installed (based on [CHES 2022 WBC Tutorial](https://github.com/hellman/ches2022wbc)). Some scripts can be run with `pypy3` which is much faster (requires `wboxkit` installed as well).


Preparation of traces and Redundant node removal (RNR) 
------------------------------------------------------

All of our implementations use a new format of traces that enables attacks to be faster. The python program *prepareTraces.py* can be called using SageMath with the file location of the official [implementation of SEL](https://github.com/UzL-ITS/white-box-masking) or the official BU's one (from [CHES 2022 WBC Tutorial](https://github.com/hellman/ches2022wbc)), and will transform them into this new format into a single binary file *nodeVectors.bin*.

The *nodeVectors.bin* contains a header that indicates the number of traces and node vectors that it contains, and then all the data of the traces. Instead of storing this data trace after trace, *nodeVectors.bin* has it stored node vector by node vector, so that each node vector has its $T$ bit elements stored consecutively, where T is the number of traces, which enhances the reading speed of the file.

After this first step, *prepareTraces.py* will then apply the *RNR* preprocessing step to it, with, by default, a window size $W=\min(500, \text{maximum possible window})$. Applying RNR will create a file containing all the Non Redundant Nodes called *NRN_Wx.pkl*, where $x$ correspond to the window size used to generate it.

The created *NRN_Wx.pkl* file is a pickle file containing a python list of all indexes of the non-redundant vectors. Running the *RNR* algorithm does not really remove the traces from the file *nodeVectors.bin*.

If *nodeVectors.bin* already exists, calling *prepareTraces.py* will skip the first step to try the second one. Likewise, if *NRN_Wx.pkl* already exists for a window greater or equal to the one that has just been asked, it will skips the second step as well.

#### Parameters:

 * **path:** A **mandatory** path to a folder containing some traces from SEL, BU or ISW.
 * **-W:**   A window size to perform *RNR* with. By default, W=min(500, maximum possible window)
 * **-S:**   A sliding size corresponding to how many node to slid on after processing one window with *RNR*. By default, S=W/6.
 * **-f:**   The number of exceeding traces to perform *RNR* with, that corresponds to the t value of the paper. By default, f=30.
 * **--save-relations:** A path to store the kernel (linear relations) obtained by RNR. This is mainly needed for CPF attacks.

**Remark:** It is possible to call solely the format-changing algorithm by calling *transposeTraces.py* using Python or SageMath. Likewise, it is possible to call solely the *RNR* algorithm by calling *RNR.py* using SageMath.


Filtered LDA (FLDA)
-------------------

The SageMath program *FLDA.py* (Filtering Linear Decoding Analysis) is the code of the main algorithm of the paper. As shown in the paper, it allows to break ISW, BU, and most notably SEL masking scheme extremely fast. Our implementation runs onto the *nodeVectors.bin* and *NRN_Wx.pkl* that need to be prepared before-hand using the sage code *prepareTraces.py*.

Logs from our executions (commands are given in [./FLDA_commands.txt](./FLDA_commands.txt)) used in paper's results are given in [./logs_flda](./logs_flda).

#### Parameters:

 * **path:** A **mandatory** path to a folder containing the preprocessed traces from SEL, BU or ISW contained in *nodeVectors.bin* and *NRN_Wx.pkl*.
 * **-W:**   A window size to perform *FLDA* with. By default, W=50. *Remark:* there is no sliding size parameter as our code runs by filtering one node per window, while sliding one node at the time. By default, W=50, which is enough to break the official implementations of SEL and BU.
 * **-t:**   The number of supplementary traces to perform *FLDA*, allowing to ensure having 1-(1/2)^t chance of avoiding false positives per window. By default, t=30.
 * **-f:**   The number of supplementary traces to perform the filtering step before applying the LDA attack. If we cannot filter W+t traces out of the W+t+f available one for a given window, the FLDA algorithm simply skips this window. The number of skips is indicated throughout the processing of the traces, which, if this number is too high, indicates that f should be chosen larger. By default, f=min(W+t+50,maximum available traces), which was enough to break SEL and BU official implementations. *Remark:* The implementation will only open the total number of traces W+t+f required for the attack from the *nodeVectors.bon* file to reduce the RAM memory usage.
 * **-NRN:** While the attack chooses its window only on Non-Redundant Nodes to virtually increase its size, this parameter allows to run filter all the available nodes or not. If NRN=0, the algorithm will slide through all the nodes, whereas if NRN=1, if will filter only the nodes contained in the *NRN_Wx.pkl* file. The logs shows that choosing this option can make the attack miss some key parts, while making it twice faster, as explained in the paper; so by default, NRN=0.
 * **-filtBy:** This parameter set to one makes the attack filter the node vectors by one, whereas if its equal to zero it will make the attack filter by zero. Our in-practice results (log files) shown that it was enough to filter by zero to break the official implementation of SEL and BU, so its default value is zero. Although, the LDA attack remains performed by adding a the **1** vector, to break the potential bit flips, which is mandatory against the official SEL implementation, as they also forgot to register the output values of bit-flipping in their traces. By default, *filtBy* is set to zero.
 * **-b:**   This parameter allows to perform the attack from a given node index. Together with the parameter *-e*, it allows to attack a precise parts of the nodes. Additionally, this reduces the RAM costs of the attack as only the node vectors from *b* to *e* will be opened. By default, *b* is set to 0, which indicates that the attack will run through all the implementation.
 * **-e:**   This parameter has the same function as *-b*, but for the ending of the traces. Together they allow to perform the attack on a precise chunk of the traces, which is useful to parallelize the attack. *e* can be chosen negative to indicate the nodes to stop starting counting from the end. By default, *e* is set to 0, which indicates that the attack will run through all the implementation.
 * **-r:**   This boolean parameter allows to determine whether to record the output of the attack into a file or not. If it set to one, at the end of the attack or if it has been keyboard interrupted, if it found at least one key byte, it will create a file containing all the displayed information on the screen: key byte founds and where, timing of the attack etc. The name of the file is *Key_FLDA_bytesFoundS_WT_tU_fV_bW_eX_NRNY_filtByZ.txt*, with T,U,V,W,X,Y,Z the different corresponding parameters necessary to reproduce the same attack, and S the number of key byte found; which is stored in the corresponding trace folder. By default, r is set to one.
 * **-s:**   This boolean parameter, if set to one, allows to stop the attack right when it found the 16 byte of the key. By default, *s* is set to 0.
 * **--bytePos** This parameter indicates which part of the key to attack. For instance, choosing *bytePos*='0,1,5' indicates that the attack will try to recover only the first, second and sixth byte of the key. In this case, it would allow faster computations, as there is less selection vectors to verify. Reminder, the complexity of FLDA is in O(W^4 + |K|W), and here we reduce the |K| coefficient. By default, *bytePos* is set to 'all', which indicates that the attacks will try to recover all byte of the secret key.
 * **--masks** This parammeter indicates which linear masks to apply to the AES S-box, i.e., which linear combinations of output bits to consider. Most generally, it can be given as a comma separated list of integers, which will be treated as 8-bit vectors, for example, `--masks=128,64,32,16,8,4,2,1` corresponds to attacking all output bits of the S-box (in the order from most-significant to least-significant). Aliases exist such as `--masks=bits` (same as above), `--masks=random32` which chooses random 32 masks, and `--masks=all` which considers all (non-zero) masks.


Chosen-plaintext-filtered Attacks
---------------------------------

Chosen-plaintext-filtered attacks (CPF-LDA and CPF-FLDA) are sketched in [./Workflow_CPF_FLDA.sh](./Workflow_CPF_FLDA.sh). It runs a sequence of scripts to perform the CPF variant of the attacks. Some parameters are hardcorded in the script, such as:

```sh
STOP_ON_KEY_MATCH=0
BYTEPOSE_LIST=(0 7)
MASKS=all
WINDOW=100
```

The relevant scripts are:

- [./recordTracesCPF.py](./recordTracesCPF.py) calls `wboxkit` to trace a given circuit on specific groups of traces (fixed half of bytes, fixed single bytes, random).
- [./splitTracesCPF.py](./splitTracesCPF.py) splits the created traces (or random traces) into corresponding groups.
- [./transposeTraces.py](./transposeTraces.py) and [./RNR.py](./RNR.py) were described above.
- [./relationsExtract.py](./relationsExtract.py) applies RNR kernel to a set of traces (create the target reduced set of traces for CPF-LDA)
- [./Exact1.py](./Exact1.py) performs exact matching attack on the reduced tracs (for CPF-LDA)
- [./FRNR.py](./FRNR.py) performs filtered RNR, with various options, and records kernels of the filtered windows.
- [./FLDA-by-pos.py](./FLDA-by-pos.py) performs CPF-FLDA usign information from FRNR.

**Note**: it runs pypy3 if available for some scripts (transposing and recording traces), so it should have `wboxkit` installed. If pypy3 is not available, it uses SageMath (which must have `wboxkit` installed).

Logs from our executions used in paper's results are given in [./logs_cpf_flda](./logs_cpf_flda).


Making circuits
---------------
`wboxkit`-based circuits used for our attacks were generated using the [./make_circuits.py](./make_circuits.py) script, based on the [CHES 2022 WBC Tutorial](https://github.com/hellman/ches2022wbc):

```
AES2R(OptBooleanCircuit):
   |   128 inputs,  128 outputs,   5825 nodes
   | XOR:3380 (58.03%), AND:1248 (21.42%), NOT:1069 (18.35%), INPUT:128 (2.20%)
AES2R_ISW2(OptBooleanCircuit):
   |   128 inputs,  128 outputs,  38158 nodes
   | XOR:25875 (67.81%), AND:10974 (28.76%), NOT:1181 (3.10%), INPUT:128 (0.34%)
AES2R_ISW3(OptBooleanCircuit):
   |   128 inputs,  128 outputs,  65028 nodes
   | XOR:44485 (68.41%), AND:19236 (29.58%), NOT:1179 (1.81%), INPUT:128 (0.20%)
AES2R_ISW5(OptBooleanCircuit):
   |   128 inputs,  128 outputs, 140583 nodes
   | XOR:96669 (68.76%), AND:42600 (30.30%), NOT:1186 (0.84%), INPUT:128 (0.09%)
AES2R_MINQ(OptBooleanCircuit):
   |   128 inputs,  128 outputs, 151463 nodes
   | XOR:103010 (68.01%), AND:47124 (31.11%), NOT:1201 (0.79%), INPUT:128 (0.08%)
AES2R_QuadLin2(OptBooleanCircuit):
   |   128 inputs,  128 outputs, 198253 nodes
   | XOR:137186 (69.20%), AND:59738 (30.13%), NOT:1201 (0.61%), INPUT:128 (0.06%)
AES2R_QuadLin3(OptBooleanCircuit):
   |   128 inputs,  128 outputs, 272022 nodes
   | XOR:196045 (72.07%), AND:74648 (27.44%), NOT:1201 (0.44%), INPUT:128 (0.05%)
AES2R_QuadLin5(OptBooleanCircuit):
   |   128 inputs,  128 outputs, 497718 nodes
   | XOR:384522 (77.26%), AND:111867 (22.48%), NOT:1201 (0.24%), INPUT:128 (0.03%)
AES10R(OptBooleanCircuit):
   |   128 inputs,  128 outputs,  31273 nodes
   | XOR:19284 (61.66%), AND:6240 (19.95%), NOT:5621 (17.97%), INPUT:128 (0.41%)
AES10R_ISW2(OptBooleanCircuit):
   |   128 inputs,  128 outputs, 193726 nodes
   | XOR:133492 (68.91%), AND:54372 (28.07%), NOT:5734 (2.96%), INPUT:128 (0.07%)
AES10R_ISW3(OptBooleanCircuit):
   |   128 inputs,  128 outputs, 329366 nodes
   | XOR:227878 (69.19%), AND:95628 (29.03%), NOT:5732 (1.74%), INPUT:128 (0.04%)
AES10R_ISW5(OptBooleanCircuit):
   |   128 inputs,  128 outputs, 710148 nodes
   | XOR:491529 (69.22%), AND:212760 (29.96%), NOT:5731 (0.81%), INPUT:128 (0.02%)
AES10R_MINQ(OptBooleanCircuit):
   |   128 inputs,  128 outputs, 802764 nodes
   | XOR:547659 (68.22%), AND:249224 (31.05%), NOT:5753 (0.72%), INPUT:128 (0.02%)
AES10R_QuadLin2(OptBooleanCircuit):
   |   128 inputs,  128 outputs,1046257 nodes
   | XOR:726333 (69.42%), AND:314043 (30.02%), NOT:5753 (0.55%), INPUT:128 (0.01%)
AES10R_QuadLin3(OptBooleanCircuit):
   |   128 inputs,  128 outputs,1437285 nodes
   | XOR:1042622 (72.54%), AND:388782 (27.05%), NOT:5753 (0.40%), INPUT:128 (0.01%)
AES10R_QuadLin5(OptBooleanCircuit):
   |   128 inputs,  128 outputs,2636960 nodes
   | XOR:2056546 (77.99%), AND:574533 (21.79%), NOT:5753 (0.22%), INPUT:128 (0.00%)

________________________________________________________
Executed in   77,73 secs    fish           external
   usr time   74,96 secs    0,00 micros   74,96 secs
   sys time    2,69 secs  668,00 micros    2,69 secs
```