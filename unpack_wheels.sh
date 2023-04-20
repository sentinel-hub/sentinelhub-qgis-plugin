#!/bin/bash

external_dir="SentinelHub/external"

function extract_file() {
    local file=$1
    local extension=${file##*.}

    if [[ ! -f $external_dir/$file ]]; then
        echo "Extracting $file"
        case $extension in
            whl|zip)
                unzip -o "$file" -d "$external_dir"
                ;;
            tar|gz|bz2)
                tar -xvf "$file" -C "$external_dir"
                ;;
            *)
                echo "Unknown file type: $file"
                ;;
        esac
    else
        echo "$file already exists in $external_dir, skipping extraction"
    fi
}

while read line; do
    extract_file "$line"
done < wheels.txt

echo "Removing wheel files..."
while read line; do
    rm -f "$line"
done < wheels.txt
echo "All wheel files removed."
