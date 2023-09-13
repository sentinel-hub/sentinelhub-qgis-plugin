#!/bin/bash

external_dir="SentinelHub/external"
tar_file_to_copy="utm.tar"

function copy_tar_file() {
    local source_file=$1
    local destination_dir=$2

    if [[ ! -f $destination_dir/source.tar ]]; then
        echo "Copying source.tar to $destination_dir"
        cp "$source_file" "$destination_dir/source.tar"
    else
        echo "source.tar already exists in $destination_dir, skipping copy"
    fi
}

# Copy the specific tar file to the external directory
copy_tar_file "$tar_file_to_copy" "$external_dir"

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

for file in "$external_dir"/*.{whl,zip,tar,gz,bz2}; do
    extract_file "$file"
done

echo "Removing wheel files..."
rm -f "$external_dir"/*.{whl,zip,tar}
echo "All wheel files removed."