#!/bin/bash
# Launch script for Three-Phase Motor Capacitor Simulator

echo "=========================================="
echo "Three-Phase Motor Capacitor Simulator"
echo "=========================================="
echo ""

# Check if required packages are installed
echo "Checking dependencies..."
python3 -c "import numpy, matplotlib, scipy" 2>/dev/null

if [ $? -ne 0 ]; then
    echo "Missing dependencies. Installing..."
    pip install -r requirements_motor_simulator.txt
fi

echo "Starting simulator..."
python3 three_phase_motor_capacitor_simulator.py
