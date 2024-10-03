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
        python3 /path-to-scan/Scan.py -s "$apk_path" -D your-db
    
        echo ""
    done
else
    echo "Directory $dir_path does not exist."
fi
