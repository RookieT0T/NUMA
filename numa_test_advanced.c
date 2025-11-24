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

// Latency test - measure random access latency
void test_latency(long *array, size_t size) {
    printf("=== Latency Test ===\n");
    volatile long sum = 0;
    size_t iterations = 10000000;
    
    // Warm up
    for (size_t i = 0; i < 1000; i++) {
        sum += array[rand() % size];
    }
    
    double start = get_time();
    for (size_t i = 0; i < iterations; i++) {
        size_t idx = rand() % size;
        sum += array[idx];
    }
    double end = get_time();
    
    double latency_ns = ((end - start) * 1000.0) / iterations;
    printf("Average latency: %.2f ns per access\n", latency_ns);
    printf("Total time: %.3f seconds\n", (end - start) / 1000000.0);
    printf("Sum (prevent optimization): %ld\n", sum);
}

// Bandwidth test - measure sequential throughput
void test_bandwidth(long *array, size_t size) {
    printf("=== Bandwidth Test ===\n");
    volatile long sum = 0;
    
    double start = get_time();
    for (size_t i = 0; i < size; i++) {
        sum += array[i];
    }
    double end = get_time();
    
    double time_sec = (end - start) / 1000000.0;
    double bytes = size * sizeof(long);
    double bandwidth_mbps = (bytes / (1024 * 1024)) / time_sec;
    
    printf("Bandwidth: %.2f MB/s\n", bandwidth_mbps);
    printf("Time: %.3f seconds\n", time_sec);
    printf("Sum: %ld\n", sum);
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

// Migration test - allocate, use, check migration
void test_migration(long *array, size_t size) {
    printf("=== Page Migration Test ===\n");
    
    // Check initial page distribution
    int initial_node = get_memory_node(&array[0]);
    printf("Initial memory node: %d\n", initial_node);
    
    // Intensive computation to trigger auto-NUMA
    volatile long sum = 0;
    double start = get_time();
    
    for (int iter = 0; iter < 5; iter++) {
        for (size_t i = 0; i < size; i++) {
            sum += array[i];
            array[i] = sum % 100;
        }
        usleep(100000); // 100ms pause
    }
    
    double end = get_time();
    
    // Check final page distribution
    int final_node = get_memory_node(&array[0]);
    printf("Final memory node: %d\n", final_node);
    printf("Migration occurred: %s\n", (initial_node != final_node) ? "YES" : "NO");
    printf("Time: %.3f seconds\n", (end - start) / 1000000.0);
}

// Sequential access
void test_sequential(long *array, size_t size) {
    printf("=== Sequential Access ===\n");
    volatile long sum = 0;
    
    double start = get_time();
    for (size_t i = 0; i < size; i++) {
        sum += array[i];
    }
    double end = get_time();
    
    printf("Time: %.3f seconds\n", (end - start) / 1000000.0);
    printf("Sum: %ld\n", sum);
}

// Random access
void test_random(long *array, size_t size) {
    printf("=== Random Access ===\n");
    volatile long sum = 0;
    size_t iterations = size / 10; // 10% of array size
    
    double start = get_time();
    for (size_t i = 0; i < iterations; i++) {
        size_t idx = rand() % size;
        sum += array[idx];
    }
    double end = get_time();
    
    printf("Time: %.3f seconds (%zu iterations)\n", (end - start) / 1000000.0, iterations);
    printf("Sum: %ld\n", sum);
}

// Stride access
void test_stride(long *array, size_t size) {
    printf("=== Stride Access (stride=64) ===\n");
    volatile long sum = 0;
    int stride = 64;
    
    double start = get_time();
    for (size_t i = 0; i < size; i += stride) {
        sum += array[i];
    }
    double end = get_time();
    
    printf("Time: %.3f seconds\n", (end - start) / 1000000.0);
    printf("Sum: %ld\n", sum);
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <size_mb> [test_type] [threads]\n", argv[0]);
        fprintf(stderr, "Test types: latency, bandwidth, threads, migrate, sequential, random, stride\n");
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
    
    // Run specified test
    srand(12345); // Fixed seed
    
    if (strcmp(test_type, "latency") == 0) {
        test_latency(array, size);
    } else if (strcmp(test_type, "bandwidth") == 0) {
        test_bandwidth(array, size);
    } else if (strcmp(test_type, "threads") == 0) {
        test_multithreaded(array, size, num_threads);
    } else if (strcmp(test_type, "migrate") == 0) {
        test_migration(array, size);
    } else if (strcmp(test_type, "sequential") == 0) {
        test_sequential(array, size);
    } else if (strcmp(test_type, "random") == 0) {
        test_random(array, size);
    } else if (strcmp(test_type, "stride") == 0) {
        test_stride(array, size);
    } else {
        test_sequential(array, size);
    }
    
    free(array);
    printf("\nTest completed successfully\n");
    return 0;
}