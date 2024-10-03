#!/bin/bash

if [ $# -eq 0 ]; then
    echo "Usage: $0 <directory_with_apks>"
    exit 1
fi

dir_path="$1"

if [ -d "$dir_path" ]; then

    for apk_path in "$dir_path"/*.apk; do

        apk_name=$(basename "$apk_path")
        echo "Analyzing $apk_name ..."

        # use this to save all results
        python3 /home/elis/Desktop/uni/assegno/llm_x_apr/llm-evaluation-master/SPECK_mod/SPECK/Scan.py -s "$apk_path" -D mongodb+srv://elisbreb:nfT3uIn7vrnFgLOU@cluster0.nbeceqe.mongodb.net/trial_2
    
        
        # use this to try it out:
        # python3 /your-path-to/SPECK-mod/SPECK/Scan.py -s "$apk_path" -D mongodb+srv://elisbreb:nfT3uIn7vrnFgLOU@cluster0.nbeceqe.mongodb.net/trial
 
        echo ""
    done
else
    echo "Directory $dir_path does not exist."
fi
