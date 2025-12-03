#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <numa.h>
#include <numaif.h>
#include <pthread.h>
#include <unistd.h>
#include <sys/time.h>

#define MB (1024 * 1024)
#define CACHE_LINE 64

typedef struct {
    long *array;
    size_t size;
    int thread_id;
    double result_time;
} thread_data_t;

// Measure time in microseconds
double get_time() {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return tv.tv_sec * 1000000.0 + tv.tv_usec;
}

// Get current node for a memory address
int get_memory_node(void *addr) {
    int status;
    void *pages[1] = {addr};
    int nodes[1];
    if (move_pages(0, 1, pages, NULL, nodes, 0) == 0) {
        return nodes[0];
    }
    return -1;
}

// Thread worker function
void *thread_worker(void *arg) {
    thread_data_t *data = (thread_data_t *)arg;
    volatile long sum = 0;
    
    double start = get_time();
    
    // Each thread works on its portion
    size_t chunk = data->size / 4;
    size_t start_idx = data->thread_id * chunk;
    size_t end_idx = start_idx + chunk;
    
    for (size_t i = start_idx; i < end_idx; i++) {
        sum += data->array[i];
    }
    
    double end = get_time();
    data->result_time = (end - start) / 1000000.0;
    
    printf("Thread %d: sum=%ld, time=%.3fs\n", data->thread_id, sum, data->result_time);
    return NULL;
}

// Multi-threaded test
void test_multithreaded(long *array, size_t size, int num_threads) {
    printf("=== Multi-threaded Test (%d threads) ===\n", num_threads);
    
    pthread_t threads[num_threads];
    thread_data_t thread_data[num_threads];
    
    double start = get_time();
    
    for (int i = 0; i < num_threads; i++) {
        thread_data[i].array = array;
        thread_data[i].size = size;
        thread_data[i].thread_id = i;
        pthread_create(&threads[i], NULL, thread_worker, &thread_data[i]);
    }
    
    for (int i = 0; i < num_threads; i++) {
        pthread_join(threads[i], NULL);
    }
    
    double end = get_time();
    printf("Total parallel time: %.3f seconds\n", (end - start) / 1000000.0);
}

// Force pages to a specific NUMA node using move_pages
void force_mbind_to_node(long *array, size_t size, int target_node) {
    printf("Forcing pages to Node %d (creating mismatch for migration test)...\n", target_node);

    // Use move_pages to manually migrate pages
    size_t num_pages = (size * sizeof(long) + 4095) / 4096;  // Round up to pages
    void **pages = malloc(num_pages * sizeof(void*));
    int *nodes = malloc(num_pages * sizeof(int));
    int *status = malloc(num_pages * sizeof(int));

    if (!pages || !nodes || !status) {
        printf("  WARNING: Cannot allocate arrays for migration\n");
        free(pages);
        free(nodes);
        free(status);
        return;
    }

    // Build page list
    for (size_t i = 0; i < num_pages; i++) {
        pages[i] = (void*)((char*)array + i * 4096);
        nodes[i] = target_node;
    }

    // Move pages
    // 0: current process
    // num_pages: the total number of 4KB pages in the memory region to be moved
    // pages: the array of virtual memory addresses, one for each page being targeted
    // nodes: the array where each element contains the target NUMA node for the corresponding page
    // status: the array where the kernel writes the final location (Node ID) for each page after the attempt
    // MPOL_MF_MOVE: the flag tells the kernel to force the physical migration of the pages to the target node, even if the pages are already allocated and in use
    long ret = move_pages(0, num_pages, pages, nodes, status, MPOL_MF_MOVE);

    int moved_count = 0;
    if (ret == 0) {
        for (size_t i = 0; i < num_pages; i++) {
            if (status[i] == target_node) moved_count++;
        }
        printf("✓ Successfully moved %d/%zu pages to Node %d\n", moved_count, num_pages, target_node);
    } else {
        printf("  WARNING: move_pages returned %ld (some pages may not have moved)\n", ret);
    }

    free(pages);
    free(nodes);
    free(status);

    sleep(1);  // Give kernel time to complete
}

// Migration test - allocate, use, check migration
void test_migration(long *array, size_t size) {
    printf("=== Page Migration Test ===\n");

    // Get current CPU and its node
    int current_cpu = sched_getcpu();
    int cpu_node = numa_node_of_cpu(current_cpu);
    int remote_node = (cpu_node == 0) ? 1 : 0;

    printf("Running on CPU %d (Node %d)\n", current_cpu, cpu_node);
    printf("Will force pages to Node %d (remote) first\n\n", remote_node);

    // STEP 1: Force all pages to remote node to create mismatch
    force_mbind_to_node(array, size, remote_node);

    // Sample pages to get distribution
    int samples = (int)(size * 0.001);
    if (samples < 100) samples = 100;
    if (samples > 10000) samples = 10000;

    // Counter per node
    int initial_dist[2] = {0, 0};
    int final_dist[2] = {0, 0};

    printf("Sampling %d pages (0.1%% of array) for distribution check\n", samples);

    // Check initial distribution
    for (int i = 0; i < samples; i++) {
        size_t idx = (size / samples) * i;
        int node = get_memory_node(&array[idx]);
        if (node >= 0 && node < 2) initial_dist[node]++;
    }

    printf("Initial distribution: Node0=%d%%, Node1=%d%%\n",
           (initial_dist[0] * 100) / samples,
           (initial_dist[1] * 100) / samples);

    // STEP 2: Intensive access from local CPU to trigger Auto-NUMA migration
    printf("\n--- Starting intensive access to trigger Auto-NUMA ---\n");

    volatile long sum = 0;

    // Pre-generate random indices to avoid caching and rand() overhead
    // DO THIS BEFORE starting timer
    // size_t *random_indices = malloc(num_accesses * sizeof(size_t));
    // if (!random_indices) {
    //     printf("ERROR: Cannot allocate random indices array\n");
    //     return;
    // }

    // for (size_t i = 0; i < num_accesses; i++) {
    //     random_indices[i] = rand() % size;
    // }

    // Track per-iteration time to show migration benefit
    printf("Iteration, IterTime(s), Node0%%, Node1%%, Status\n");  // CSV header

    double cumulative_access_time = 0.0;
    double test_start = get_time();  // Wall-clock start for progress tracking

    // Sample every iteration for detailed timeline
    int total_iterations = 400;
    size_t num_accesses = 400000;
    for (int iter = 0; iter < total_iterations; iter++) {
        // TIME ONLY THE MEMORY ACCESS (pure performance measurement)
        double iter_start = get_time();

        for (size_t i = 0; i < num_accesses; i++) {
            size_t idx = rand() % size;
            sum += array[idx];
            array[idx] = sum % 100;
        }

        double iter_end = get_time();
        double iter_time = (iter_end - iter_start) / 1000000.0;  // Convert to seconds
        cumulative_access_time += iter_time;

        // Small pause to let Auto-NUMA scan and make decisions (NOT timed)
        usleep(50000); // 50ms pause

        // Sample distribution EVERY iteration (NOT timed)
        int mid_dist[2] = {0, 0};
        for (int j = 0; j < samples; j++) {
            size_t idx = (size / samples) * j;
            int node = get_memory_node(&array[idx]);
            if (node >= 0 && node < 2) mid_dist[node]++;
        }

        int node0_pct = (mid_dist[0] * 100) / samples;
        int node1_pct = (mid_dist[1] * 100) / samples;

        // Show status indicator
        const char* status;
        if (node0_pct == 0) {
            status = "All_Remote";
        } else if (node0_pct == 100) {
            status = "All_Local";
        } else {
            status = "Migrating";
        }

        // Output: iteration number, THIS iteration's time, distribution, status
        printf("%d, %.3f, %d, %d, %s\n", iter, iter_time,
               node0_pct, node1_pct, status);
    }

    // free(random_indices);

    double test_end = get_time();
    double total_wall_time = (test_end - test_start) / 1000000.0;

    // Check final distribution
    for (int i = 0; i < samples; i++) {
        size_t idx = (size / samples) * i;
        int node = get_memory_node(&array[idx]);
        if (node >= 0 && node < 2) final_dist[node]++;
    }

    printf("Final distribution: Node0=%d%%, Node1=%d%%\n",
           (final_dist[0] * 100) / samples,
           (final_dist[1] * 100) / samples);

    int migration_occurred = (initial_dist[0] != final_dist[0]) ||
                            (initial_dist[1] != final_dist[1]);
    printf("Migration occurred: %s\n", migration_occurred ? "YES" : "NO");
    printf("\n=== Performance Summary ===\n");
    printf("Pure access time: %.3f seconds\n", cumulative_access_time);
    printf("Total wall time (includes pauses): %.3f seconds\n", total_wall_time);
    printf("Overhead (sampling + sleeping): %.3f seconds\n",
           total_wall_time - cumulative_access_time);
    printf("Sum (prevent optimization): %ld\n", sum);
}

// Sequential access
void test_sequential(long *array, size_t size) {
    printf("=== Sequential Access Pattern ===\n");
    volatile long sum = 0;

    // Warmup with random accesses to avoid caching
    for (size_t i = 0; i < 10000; i++) {
        size_t idx = rand() % size;
        sum += array[idx];
    }

    // Single measurement loop for both throughput and latency
    size_t num_iterations = (size < 1000000) ? size : 1000000;
    double start = get_time();
    for (size_t i = 0; i < num_iterations; i++) {
        sum += array[i];
    }
    double end = get_time();

    double time_sec = (end - start) / 1000000.0;
    double bytes = num_iterations * sizeof(long);
    double throughput_mbps = (bytes / (1024 * 1024)) / time_sec;
    double avg_latency_ns = (time_sec * 1000000000.0) / num_iterations;

    printf("Throughput: %.2f MB/s\n", throughput_mbps);
    printf("Average latency: %.2f ns per access\n", avg_latency_ns);
    printf("Time: %.3f seconds\n", time_sec);
    printf("Sum (prevent optimization): %ld\n", sum);
}

// Random access
void test_random(long *array, size_t size) {
    printf("=== Random Access Pattern ===\n");
    volatile long sum = 0;

    // Warmup with random accesses (use rand() directly to avoid caching)
    for (size_t i = 0; i < 10000; i++) {
        size_t idx = rand() % size;
        sum += array[idx];
    }

    // Pre-compute random indices to avoid rand() overhead during measurement
    size_t num_iterations = 1000000;
    size_t *indices = malloc(num_iterations * sizeof(size_t));
    if (indices == NULL) {
        fprintf(stderr, "Failed to allocate index array\n");
        return;
    }

    for (size_t i = 0; i < num_iterations; i++) {
        indices[i] = rand() % size;
    }

    // Single measurement loop for both throughput and latency
    double start = get_time();
    for (size_t i = 0; i < num_iterations; i++) {
        sum += array[indices[i]];
    }
    double end = get_time();

    double time_sec = (end - start) / 1000000.0;
    double bytes_accessed = num_iterations * sizeof(long);
    double throughput_mbps = (bytes_accessed / (1024 * 1024)) / time_sec;
    double avg_latency_ns = (time_sec * 1000000000.0) / num_iterations;

    printf("Throughput: %.2f MB/s (%zu random accesses)\n", throughput_mbps, num_iterations);
    printf("Average latency: %.2f ns per access\n", avg_latency_ns);
    printf("Time: %.3f seconds\n", time_sec);
    printf("Sum (prevent optimization): %ld\n", sum);

    free(indices);
}

// Stride access
void test_stride(long *array, size_t size) {
    printf("=== Stride Access Pattern (stride=64) ===\n");
    volatile long sum = 0;
    int stride = 64;

    // Warmup with random accesses (use rand() directly to avoid caching)
    for (size_t i = 0; i < 10000; i++) {
        size_t idx = rand() % size;
        sum += array[idx];
    }

    // Pre-compute stride indices to avoid arithmetic overhead during measurement
    size_t num_iterations = 1000000;
    size_t *indices = malloc(num_iterations * sizeof(size_t));
    if (indices == NULL) {
        fprintf(stderr, "Failed to allocate index array\n");
        return;
    }

    for (size_t i = 0; i < num_iterations; i++) {
        indices[i] = (i * stride) % size;
    }

    // Single measurement loop for both throughput and latency
    double start = get_time();
    for (size_t i = 0; i < num_iterations; i++) {
        sum += array[indices[i]];
    }
    double end = get_time();

    double time_sec = (end - start) / 1000000.0;
    double bytes_accessed = num_iterations * sizeof(long);
    double throughput_mbps = (bytes_accessed / (1024 * 1024)) / time_sec;
    double avg_latency_ns = (time_sec * 1000000000.0) / num_iterations;

    printf("Throughput: %.2f MB/s (%zu strided accesses)\n", throughput_mbps, num_iterations);
    printf("Average latency: %.2f ns per access\n", avg_latency_ns);
    printf("Time: %.3f seconds\n", time_sec);
    printf("Sum (prevent optimization): %ld\n", sum);

    free(indices);
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <size_mb> [test_type] [threads]\n", argv[0]);
        fprintf(stderr, "Test types: sequential, random, stride, threads, migrate\n");
        fprintf(stderr, "Note: sequential/random/stride tests measure both latency and throughput\n");
        return 1;
    }

    if (numa_available() < 0) {
        fprintf(stderr, "NUMA not available\n");
        return 1;
    }

    size_t size_mb = atol(argv[1]);
    size_t size = (size_mb * MB) / sizeof(long);
    char *test_type = (argc > 2) ? argv[2] : "sequential";
    int num_threads = (argc > 3) ? atoi(argv[3]) : 4;

    printf("Allocating %zu MB (%zu elements)...\n", size_mb, size);
    long *array = malloc(size * sizeof(long));

    if (array == NULL) {
        fprintf(stderr, "Memory allocation failed!\n");
        return 1;
    }

    // Initialize array (triggers actual allocation)
    printf("Initializing array...\n");
    for (size_t i = 0; i < size; i++) {
        array[i] = i % 100;
    }
    printf("Initialization complete.\n\n");

    // Run specified test (each access pattern measures both throughput and latency)
    srand(12345); // Fixed seed

    if (strcmp(test_type, "sequential") == 0) {
        test_sequential(array, size);
    } else if (strcmp(test_type, "random") == 0) {
        test_random(array, size);
    } else if (strcmp(test_type, "stride") == 0) {
        test_stride(array, size);
    } else if (strcmp(test_type, "threads") == 0) {
        test_multithreaded(array, size, num_threads);
    } else if (strcmp(test_type, "migrate") == 0) {
        test_migration(array, size);
    } else {
        // Default to sequential
        test_sequential(array, size);
    }

    free(array);
    printf("\nTest completed successfully\n");
    return 0;
}