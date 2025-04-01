#!/bin/bash

# Ensure the script stops on first error
set -e

# Default settings
SKIP_COMPILE=false

# Parse command line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --benchmark-only) SKIP_COMPILE=true ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Function to check if the last command was successful
check_status() {
    if [ $? -ne 0 ]; then
        echo "Error: $1"
        exit 1
    fi
}

if [ "$SKIP_COMPILE" = false ]; then
    echo "Cleaning previous builds..."
    aptos move clean
    check_status "Failed to clean previous builds"

    echo "Compiling Move module..."
    aptos move compile --named-addresses address_move=default
    check_status "Failed to compile module"

    echo "Publishing module..."
    aptos move publish --named-addresses address_move=default --assume-yes
    check_status "Failed to publish module"
else
    echo "Skipping compilation and publishing, running benchmarks only..."
fi

echo "Running benchmarks..."

# Define benchmarks with their arguments
# Format: "function_name|arg1_type:arg1_value|arg2_type:arg2_value|..."
# Use empty string for no arguments
declare -a BENCHMARK_CONFIGS=(
    "initialize"
    "benchmark_vector_ops"
    "benchmark_storage_ops"
    "benchmark_control_flow"
    "benchmark_arithmetic|u64:3|u64:4"
    "benchmark_conditional_logic|u64:10|u64:5|u8:255|u8:127|bool:true|bool:false"
    "benchmark_boolean_ops|bool:true|bool:false"
    "benchmark_bit_shift|u8:10|u8:3"
    "benchmark_casting|u8:10|u16:1000|u32:100000|u64:10000000|u128:10000000000|u256:1000000000000"
)

# Clear previous gas profiling results
rm -rf gas-profiling/*
mkdir -p gas-profiling

# Run each benchmark
for config in "${BENCHMARK_CONFIGS[@]}"; do
    # Split the config string by pipe symbol
    IFS='|' read -r -a config_parts <<< "$config"
    
    # Get the function name (first part)
    benchmark="${config_parts[0]}"
    
    echo "Running benchmark: $benchmark"
    
    # Start constructing the command
    cmd="aptos move run --function-id \"default::opcode_benchmark::$benchmark\""
    
    # Add arguments if they exist (from second part onwards)
    for ((i=1; i<${#config_parts[@]}; i++)); do
        cmd+=" --args '${config_parts[i]}'"
    done
    
    # Add profile-gas flag
    cmd+=" --profile-gas"
    
    # Execute the command
    echo "Executing: $cmd"
    eval $cmd
    check_status "Failed to run benchmark: $benchmark"
    
    # Wait a bit between benchmarks
    sleep 2
    
    # Verify that files were created
    latest_dir=$(ls -t gas-profiling | head -n1)
    if [ -z "$latest_dir" ]; then
        echo "Warning: No output directory created for benchmark $benchmark"
    else
        echo "Output directory created: gas-profiling/$latest_dir"
        
        # Check for required files
        if [ ! -f "gas-profiling/$latest_dir/result.json" ]; then
            echo "Warning: result.json not found for benchmark $benchmark"
        fi
        if [ ! -f "gas-profiling/$latest_dir/trace.json" ]; then
            echo "Warning: trace.json not found for benchmark $benchmark"
        fi
    fi
done

echo "All benchmarks completed. Results are in gas-profiling directory."
echo "Running Python analysis script..."
python3 analyze_benchmarks.py 