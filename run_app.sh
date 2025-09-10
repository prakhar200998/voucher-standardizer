#!/bin/bash

# Set up environment variables for WeasyPrint
export PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig:/opt/homebrew/share/pkgconfig:$PKG_CONFIG_PATH"
export DYLD_LIBRARY_PATH="/opt/homebrew/lib:$DYLD_LIBRARY_PATH"

# Activate virtual environment
source venv/bin/activate

# Run Streamlit app
streamlit run app.py