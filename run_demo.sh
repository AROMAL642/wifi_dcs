#!/bin/bash
# Distributed Computing System Demo Script
# This script helps you run all components in separate terminal windows

echo "======================================================================="
echo "Distributed Computing System - Multi-Terminal Demo"
echo "======================================================================="
echo ""
echo "This script will open multiple terminal windows."
echo "Press Ctrl+C in each terminal to stop that component."
echo ""

# Function to run command in new terminal
run_in_terminal() {
    local title=$1
    local command=$2
    
    if command -v gnome-terminal &> /dev/null; then
        gnome-terminal --title="$title" -- bash -c "$command; exec bash"
    elif command -v xterm &> /dev/null; then
        xterm -title "$title" -e "$command; bash" &
    elif command -v konsole &> /dev/null; then
        konsole --title "$title" -e bash -c "$command; exec bash" &
    else
        echo "No suitable terminal emulator found. Please run commands manually."
        echo "$title: $command"
        return 1
    fi
    
    sleep 1
}

cd "$(dirname "$0")"

echo "Starting simulated nodes..."
run_in_terminal "Node 1 - Worker1" "python3 simulated_node.py --name Worker1 --offset 0"
run_in_terminal "Node 2 - Worker2" "python3 simulated_node.py --name Worker2 --offset 1 --simulate-load"
run_in_terminal "Node 3 - Worker3" "python3 simulated_node.py --name Worker3 --offset 2"

echo "Waiting for nodes to initialize..."
sleep 3

echo "Starting discovery service..."
run_in_terminal "Discovery Service" "cd module1_discovery && python3 main.py"

echo "Waiting for discovery to start..."
sleep 3

echo "Starting distribution service..."
run_in_terminal "Distribution Service" "cd module2_distribution && python3 main.py --mode interactive"

echo ""
echo "======================================================================="
echo "All components started!"
echo "======================================================================="
echo ""
echo "Terminals opened:"
echo "  1. Worker1 (Simulated Node)"
echo "  2. Worker2 (Simulated Node with varying load)"
echo "  3. Worker3 (Simulated Node)"
echo "  4. Discovery Service (Finding nodes)"
echo "  5. Distribution Service (Interactive task management)"
echo ""
echo "In the Distribution Service terminal, try these commands:"
echo "  >> create 10 3     # Create 10 tasks"
echo "  >> distribute      # Distribute to nodes"
echo "  >> status          # Show system status"
echo "  >> nodes           # Show node details"
echo ""
