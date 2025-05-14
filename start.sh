#!/bin/bash

# Check if ffmpeg is already installed
if ! command -v ffmpeg &> /dev/null; then
    echo "ffmpeg is not installed. Installing ffmpeg..."
    sudo apt update && sudo apt install -y ffmpeg
else
    echo "ffmpeg is already installed. Skipping installation."
fi

# Install Python dependencies from requirements.txt
echo "Installing Python dependencies from requirements.txt..."
pip install --break-system-packages -r requirements.txt

# Install additional specific versions of pymongo and motor
echo "Installing pymongo==4.3.3..."
pip install --break-system-packages "pymongo==4.3.3"

echo "Installing motor==3.1.1..."
pip install --break-system-packages --upgrade "motor==3.1.1"

# Run the Python bot
echo "Starting the Python bot..."
python3 -m bot
