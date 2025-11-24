#!/bin/bash
# advanced_numa_test.sh - Comprehensive NUMA characterization for OS project

BENCHMARK="./numa_test_advanced"
RESULTS="numa_results_advanced"
mkdir -p $RESULTS

# Get available memory per node (in MB)
NODE0_MEM=$(numactl --hardware | grep "node 0 size" | awk '{print $4}')
NODE1_MEM=$(numactl --hardware | grep "node 1 size" | awk '{print $4}')

echo "=========================================="
echo "Advanced NUMA Policy Characterization"
echo "=========================================="
echo "Node 0 Memory: ${NODE0_MEM} MB"
echo "Node 1 Memory: ${NODE1_MEM} MB"
echo ""

# Compile benchmark
gcc -O2 numa_test_advanced.c -o numa_test_advanced -lnuma
if [ $? -ne 0 ]; then
    echo "Compilation failed! Install libnuma-dev"
    exit 1
fi

# ==================================================
# TEST CATEGORY 1: Memory Pressure & Fallback Behavior
# ==================================================
echo "=========================================="
echo "Category 1: Memory Pressure & Fallback"
echo "=========================================="

# Calculate memory sizes for testing
SMALL_MEM=$((NODE0_MEM / 4))      # 25% of node memory
MEDIUM_MEM=$((NODE0_MEM / 2))     # 50% of node memory
LARGE_MEM=$((NODE0_MEM * 3 / 4))  # 75% of node memory
OVERFLOW_MEM=$((NODE0_MEM * 5 / 4)) # 125% of node memory (triggers fallback)

for size in $SMALL_MEM $MEDIUM_MEM $LARGE_MEM $OVERFLOW_MEM; do
    echo ""
    echo "Testing with ${size}MB allocation..."
    
    # Test 1a: membind with small allocation (should succeed on single node)
    echo "  - Strict membind to node 0 (${size}MB)"
    numactl --membind=0 --cpunodebind=0 $BENCHMARK $size > ${RESULTS}/membind_node0_${size}MB.txt 2>&1
    numastat -p $! > ${RESULTS}/numastat_membind_node0_${size}MB.txt 2>/dev/null
    
    # Test 1b: preferred with overflow (should fallback gracefully)
    echo "  - Preferred node 0 (${size}MB) - may fallback"
    numactl --preferred=0 --cpunodebind=0 $BENCHMARK $size > ${RESULTS}/preferred_node0_${size}MB.txt 2>&1
    numastat -p $! > ${RESULTS}/numastat_preferred_node0_${size}MB.txt 2>/dev/null
    
    sleep 1
done

# ==================================================
# TEST CATEGORY 2: Cross-Node Access Patterns
# ==================================================
echo ""
echo "=========================================="
echo "Category 2: Cross-Node Memory Access"
echo "=========================================="

# Test 2a: Local vs Remote latency
echo "Testing local vs remote memory latency..."
numactl --membind=0 --cpunodebind=0 $BENCHMARK 1024 latency > ${RESULTS}/latency_local_node0.txt 2>&1
numactl --membind=1 --cpunodebind=0 $BENCHMARK 1024 latency > ${RESULTS}/latency_remote_node0to1.txt 2>&1
numactl --membind=0 --cpunodebind=1 $BENCHMARK 1024 latency > ${RESULTS}/latency_remote_node1to0.txt 2>&1

# Test 2b: Bandwidth comparison
echo "Testing local vs remote memory bandwidth..."
numactl --membind=0 --cpunodebind=0 $BENCHMARK 2048 bandwidth > ${RESULTS}/bandwidth_local_node0.txt 2>&1
numactl --membind=1 --cpunodebind=0 $BENCHMARK 2048 bandwidth > ${RESULTS}/bandwidth_remote_node0to1.txt 2>&1

# ==================================================
# TEST CATEGORY 3: Policy Comparison Under Load
# ==================================================
echo ""
echo "=========================================="
echo "Category 3: Policy Performance Under Load"
echo "=========================================="

TEST_SIZE=2048  # 2GB test

# Test 3a: interleave vs local allocation
echo "Comparing interleave vs local allocation..."
numactl --interleave=all --cpunodebind=0 $BENCHMARK $TEST_SIZE > ${RESULTS}/interleave_all.txt 2>&1
numactl --localalloc --cpunodebind=0 $BENCHMARK $TEST_SIZE > ${RESULTS}/localalloc_node0.txt 2>&1
numactl --membind=0 --cpunodebind=0 $BENCHMARK $TEST_SIZE > ${RESULTS}/membind_strict_node0.txt 2>&1

# Test 3b: Preferred with different preferred nodes
echo "Testing preferred policy with mismatched CPU/memory preference..."
numactl --preferred=0 --cpunodebind=1 $BENCHMARK $TEST_SIZE > ${RESULTS}/preferred_node0_cpu_node1.txt 2>&1
numactl --preferred=1 --cpunodebind=0 $BENCHMARK $TEST_SIZE > ${RESULTS}/preferred_node1_cpu_node0.txt 2>&1

# # ==================================================
# # TEST CATEGORY 4: Multi-threaded NUMA Behavior
# # ==================================================
# echo ""
# echo "=========================================="
# echo "Category 4: Multi-threaded Workloads"
# echo "=========================================="

# # Test 4a: Threads on same node
# echo "Testing multi-threaded on single node..."
# numactl --membind=0 --cpunodebind=0 $BENCHMARK 2048 threads 4 > ${RESULTS}/multithread_same_node.txt 2>&1

# # Test 4b: Threads spread across nodes
# echo "Testing multi-threaded across nodes..."
# numactl --membind=0,1 --cpunodebind=0,1 $BENCHMARK 2048 threads 4 > ${RESULTS}/multithread_cross_node.txt 2>&1

# # Test 4c: Interleave with multiple threads
# echo "Testing multi-threaded with interleave..."
# numactl --interleave=all $BENCHMARK 2048 threads 4 > ${RESULTS}/multithread_interleave.txt 2>&1

# # ==================================================
# # TEST CATEGORY 5: Page Migration and Auto-NUMA
# # ==================================================
# echo ""
# echo "=========================================="
# echo "Category 5: Dynamic Page Migration"
# echo "=========================================="

# # Check if auto-NUMA is enabled
# AUTO_NUMA=$(cat /proc/sys/kernel/numa_balancing 2>/dev/null)
# echo "Auto-NUMA status: $AUTO_NUMA"

# # Test 5a: Initial allocation on wrong node, let kernel migrate
# echo "Testing page migration (allocate on node 1, compute on node 0)..."
# numactl --membind=1 --cpunodebind=0 $BENCHMARK 2048 migrate > ${RESULTS}/page_migration_test.txt 2>&1

# # Monitor migration statistics
# grep -E "numa_hint|numa_pages_migrated|pgmigrate" /proc/vmstat > ${RESULTS}/vmstat_migration.txt

# # ==================================================
# # TEST CATEGORY 6: Mixed Access Patterns
# # ==================================================
# echo ""
# echo "=========================================="
# echo "Category 6: Mixed Access Patterns"
# echo "=========================================="

# # Test 6a: Sequential vs Random with different policies
# echo "Testing access patterns with different NUMA policies..."
# for policy in "membind=0" "interleave=all" "preferred=0"; do
#     policy_name=$(echo $policy | tr '=' '_')
#     numactl --$policy --cpunodebind=0 $BENCHMARK 1024 sequential > ${RESULTS}/sequential_${policy_name}.txt 2>&1
#     numactl --$policy --cpunodebind=0 $BENCHMARK 1024 random > ${RESULTS}/random_${policy_name}.txt 2>&1
#     numactl --$policy --cpunodebind=0 $BENCHMARK 1024 stride > ${RESULTS}/stride_${policy_name}.txt 2>&1
# done

echo ""
echo "=========================================="
echo "All tests complete!"
echo "Results in: $RESULTS/"
echo "=========================================="

# Generate analysis summary
./analyze_numa_results.sh $RESULTS