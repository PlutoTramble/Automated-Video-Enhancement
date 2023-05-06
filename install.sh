#!/usr/bin/env bash

echo "This script will download the needed binaries and install 
them into the AIs directory."
echo ""

## Check if user has ffmpeg
if ! ffmpeg -h &> /dev/null; then
    echo "Please install ffmpeg in your system before running this script."
    exit 1
fi

echo "Make sure to check out nihui's repositories."
echo "Without them, this project wouldn't be possible. :"
echo "https://github.com/nihui/rife-ncnn-vulkan"
echo "https://github.com/nihui/srmd-ncnn-vulkan"
echo "https://github.com/nihui/ifrnet-ncnn-vulkan"
echo ""

echo "The installation will start in 5 seconds"
sleep 5

## Check if user has AIs directory and is on the working directory
if [ -d "AIs/" -a -f "src/main.py" ]; then
    cd AIs
    OS=ubuntu
    if [[ $OSTYPE == 'darwin'* ]]; then #If mac os
        echo "Installing SRMD"
        OS=macos
    fi
    echo "Installing SRMD"
    curl -L https://github.com/nihui/srmd-ncnn-vulkan/releases/download/20220728/srmd-ncnn-vulkan-20220728-$OS.zip --output srmd.zip
    unzip srmd.zip
    mv srmd-ncnn-vulkan-20220728-$OS/models-srmd ../AIs/
    mv srmd-ncnn-vulkan-20220728-$OS/srmd-ncnn-vulkan ../AIs/
    rm -r srmd-ncnn-vulkan-20220728-$OS/
    rm srmd.zip

    echo "Installing RIFE"
    curl -L https://github.com/nihui/rife-ncnn-vulkan/releases/download/20220728/rife-ncnn-vulkan-20220728-$OS.zip --output rife.zip
    unzip rife.zip
    mv rife-ncnn-vulkan-20220728-$OS/rife-v2.3 ../AIs/
    mv rife-ncnn-vulkan-20220728-$OS/rife-ncnn-vulkan ../AIs/
    rm -r rife-ncnn-vulkan-20220728-$OS/
    rm rife.zip

    echo "Installing IFRNet"
    curl -L https://github.com/nihui/ifrnet-ncnn-vulkan/releases/download/20220720/ifrnet-ncnn-vulkan-20220720-$OS.zip --output ifrnet.zip
    unzip ifrnet.zip
    mv ifrnet-ncnn-vulkan-20220720-$OS/IFRNet_L_Vimeo90K ../AIs/
    mv ifrnet-ncnn-vulkan-20220720-$OS/ifrnet-ncnn-vulkan ../AIs/
    rm -r ifrnet-ncnn-vulkan-20220720-$OS/
    rm ifrnet.zip
else
    echo "File and directory not found. Please run this in the working directory"
    exit 2
fi

echo "Finished installing files in AIs directory."