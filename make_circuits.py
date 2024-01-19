# pip install binteger wboxkit pycryptodome

from binteger import Bin
from wboxkit.ciphers.aes import BitAES
from circkit.boolean import OptBooleanCircuit as BooleanCircuit

from Crypto.Cipher import AES


def make_AES_circuit(key=b"abcdefghABCDEFGH", rounds=10):
    key_bits = Bin(key).tuple

    C = BooleanCircuit(name=f"AES{rounds}R")
    pt = C.add_inputs(128)
    ct, k10 = BitAES(pt, key_bits, rounds=rounds)
    C.add_output(ct)

    C.in_place_remove_unused_nodes()
    C.print_stats()

    if rounds == 10:
        plaintext = b"0123456789abcdef"
        ciphertext_bits = C.evaluate(Bin(plaintext).tuple)
        ct1 =  Bin(ciphertext_bits).bytes
        ct2 = AES.new(key, mode=AES.MODE_ECB).encrypt(plaintext)
        assert ct1 == ct2

    return C


from wboxkit.prng import NFSR, Pool
from wboxkit.serialize import RawSerializer

nfsr = NFSR(
    taps=[[], [11], [50], [3, 107]],
    clocks_initial=32,
    clocks_per_step=1,
)


from wboxkit.masking import ISW
from wboxkit.masking import MINQ
from wboxkit.masking import QuadLin

for rounds in (2, 5, 10):
    C = make_AES_circuit(rounds=rounds)
    RawSerializer(bytes_addr=2).serialize_to_file(C, f"circuits/{C.name}.bin".lower())

    # ISW03 from wboxkit
    for l in (2, 3, 5):
        prng = Pool(prng=nfsr, n=100)
        C_ISW = ISW(prng=prng, order=l).transform(C)
        C_ISW.name += str(l)
        C_ISW.in_place_remove_unused_nodes()
        C_ISW.print_stats()

        RawSerializer(bytes_addr=2).serialize_to_file(C_ISW, f"circuits/{C_ISW.name}.bin".lower())

    # BU18 from wboxkit
    prng = Pool(prng=nfsr, n=100)
    C_MINQ = MINQ(prng=prng).transform(C)
    C_MINQ.in_place_remove_unused_nodes()
    C_MINQ.print_stats()

    RawSerializer(bytes_addr=2).serialize_to_file(C_MINQ, f"circuits/{C_MINQ.name}.bin".lower())


    for l in (2, 3, 5):
        # SEL(d=2) from wboxkit
        prng = Pool(prng=nfsr, n=100)
        C_QL = QuadLin(prng=prng, n_linear=l).transform(C)
        C_QL.name += str(l)
        C_QL.in_place_remove_unused_nodes()
        C_QL.print_stats()

        RawSerializer(bytes_addr=2).serialize_to_file(C_QL, f"circuits/{C_QL.name}.bin".lower())

'''
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
'''
