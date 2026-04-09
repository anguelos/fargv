#!/bin/bash

COLS=80
ROWS=24
SCENE_PAUSE=1.2
LARGE_PAUSE=2.5
CMD_PAUSE=0.5
CHAR_PAUSE=0.07
PROMPT="$ "

printf "\e[8;${ROWS};${COLS}t"
sleep 0.3

# type_cmd() {
#     echo -n "$PROMPT"
#     echo "$1"
#     sleep $CMD_PAUSE
# }

type_cmd() {
    echo -n "$PROMPT"
    local cmd="$1"
    for ((i=0; i<${#cmd}; i++)); do
        echo -n "${cmd:$i:1}"
        sleep $CHAR_PAUSE
    done
    echo
    sleep $CMD_PAUSE
}

# Uncomment to record:
# asciinema rec demo.cast --overwrite
# sleep 0.5

# Scene 1: show word_count.py
clear
#type_cmd "bat --style=plain --paging=never word_count.py"
type_cmd "cat word_count.py"
batcat --style=plain --paging=never word_count.py
echo -n $PROMPT
sleep $SCENE_PAUSE

# Scene 2: run word_count.py
clear
type_cmd "python word_count.py"
python word_count.py
echo -n $PROMPT
sleep $SCENE_PAUSE


# Scene 3: delta diff
clear
type_cmd "delta word_count.py word_count_fargv.py"
diff -U 999 word_count.py word_count_fargv.py | delta --width=$COLS | tail -n +8
echo -n $PROMPT
#sleep $SCENE_PAUSE
sleep $LARGE_PAUSE


# Scene 4: run word_count_fargv.py --help
clear
type_cmd "python word_count_fargv.py -h"
python word_count_fargv.py -h
echo -n $PROMPT
sleep $LARGE_PAUSE

# # Scene 5: run word_count_fargv.py
clear
type_cmd "python word_count_fargv.py"
python word_count_fargv.py
echo -n $PROMPT
sleep $SCENE_PAUSE

# Scene 6: run with -v
clear
type_cmd "python word_count_fargv.py -v"
python word_count_fargv.py -v
echo -n $PROMPT
sleep $SCENE_PAUSE

# # Scene 7: run with -vv
# clear
# type_cmd "python word_count_fargv.py -vv"
# python word_count_fargv.py -vv
# echo -n $PROMPT
# sleep $SCENE_PAUSE

# Uncomment to stop recording:
# exit