#!/bin/bash -ex

CIRCUIT=$1
NAME=$(basename "$CIRCUIT")
NAME="${NAME%%.*}"
FRNR_FLAGS=--output-friendly
# FRNR_FLAGS=

TIME="/usr/bin/time -v"

DO_LDA=1
DO_FLDA=1
STOP_ON_KEY_MATCH=0
BYTEPOSE_LIST=(0 7)
MASKS=all  # random32 all bits

TRACES_BASE=traces-cpf/
TRACES_RAND=traces-rand/

echo CIRCUIT $CIRCUIT
echo NAME $NAME

test $NAME || exit 1
test $CIRCUIT || exit 1

PYPY3=$(which pypy3 || echo sage)

mkdir "$TRACES_BASE" || true
mkdir "$TRACES_RAND" || true

WINDOW=100
WINDOW_RNR=$((WINDOW*2+50))
T_NEED=$((WINDOW*2+112))  # (WINDOW+30)*2+50
T_PERGROUP=64
T_RAND=$((T_NEED + 64 - T_NEED%64))  # pad to multiple of 64 to avoid some bugs


$TIME "$PYPY3" recordTracesCPF.py "$CIRCUIT" "$TRACES_BASE" -H $((T_NEED-T_PERGROUP)) -B $((T_PERGROUP))
$TIME "$PYPY3" splitTracesCPF.py "$TRACES_BASE/$NAME/"
$TIME "$PYPY3" -m wboxkit.attacks.trace -t "$T_RAND" --seed 0 "$CIRCUIT" "$TRACES_RAND"

# CPF-LDA/CPF-FLDA Step 0: preprocessing: RNR random trace
#$TIME sage prepareTraces.py "$TRACES_RAND/$NAME/"
$TIME "$PYPY3" transposeTraces.py "$TRACES_RAND/$NAME/"
$TIME sage RNR.py "$TRACES_RAND/$NAME" -W "$WINDOW_RNR"

pattern="$TRACES_RAND/$NAME"/NRN_W*.pkl
bigNRN=( $pattern )
echo "bigRNR: $bigNRN"

for BYTEPOS in "${BYTEPOSE_LIST[@]}"; do
	SUB=$(printf "byte%02x" "$BYTEPOS")

	# FIXED BYTE TRACE:
	# create nodeVectors.bin
	$TIME "$PYPY3" transposeTraces.py "$TRACES_BASE/$NAME.$SUB/"

	# CPF-FLDA Step 0: preprocessing: RNR fixed-byte trace
	# CPF-LDA Step 1: RNR fixed-byte trace
	$TIME sage RNR.py -NRN "${bigNRN[-1]}" --save-relations "$TRACES_BASE/$NAME.$SUB/" -W "$WINDOW_RNR"
done

if [[ "$DO_LDA" == "1" ]]; then
	for BYTEPOS in "${BYTEPOSE_LIST[@]}"; do
		SUB=$(printf "byte%02x" "$BYTEPOS")
		# CPF-LDA Step 2: RNR extract random trace
		time sage relationsExtract.py "$TRACES_RAND/$NAME/" "$TRACES_RAND/$NAME.cpf.$SUB/" "$TRACES_BASE/$NAME.$SUB"/RNrel_W*.pkl "$bigNRN"

		set +x
		cp "$TRACES_RAND/$NAME/"*.pt "$TRACES_RAND/$NAME.cpf.$SUB/"
		set -x

		# CPF-LDA Step 3: attack extracted trace of redundancies
		#sage LDA.py "$TRACES_RAND/$NAME.cpf.$SUB/" --bytePos=0 --masks=random32 -W 5
		sage Exact1.py "$TRACES_RAND/$NAME.cpf.$SUB/" --bytePos=$BYTEPOS --masks="$MASKS" --window=1 
	done
fi

if [[ "$DO_FLDA" == "1" ]]; then
	# CPF-FLDA Step 1: record redundant relations on random traces (to exclude later)
	$TIME sage FRNR.py $FRNR_FLAGS "$TRACES_RAND/$NAME/" --save-relations -W "$WINDOW"
	
	for BYTEPOS in "${BYTEPOSE_LIST[@]}"; do
		SUB=$(printf "byte%02x" "$BYTEPOS")
		
		# CPF-FLDA Step 2: record redundant relations on fixed traces (to use later)
		pattern="$TRACES_RAND/$NAME/"FRNrel_W*.pkl.gz 
		randFRNR=( $pattern )
		$TIME sage FRNR.py $FRNR_FLAGS "$TRACES_BASE/$NAME.$SUB/" --save-relations --baseNRNpath="$TRACES_RAND/$NAME/" --skip-relations="${randFRNR[-1]}" -W "$WINDOW"
		
		# CPF-FLDA Step 3: use redundant relations from fixed traces on random traces
		pattern="$TRACES_BASE/$NAME.$SUB/"FRNrel_W*.pkl.gz
		fixedFRNR=( $pattern )
		$TIME sage FLDA-by-pos.py $FRNR_FLAGS "$TRACES_RAND/$NAME/" --frnr="${fixedFRNR[-1]}" --byte="$BYTEPOS" --masks="$MASKS" -s="$STOP_ON_KEY_MATCH" -W "$WINDOW"
	done
fi