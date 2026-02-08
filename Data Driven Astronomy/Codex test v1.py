# Bubble vs Merge sort runtime distribution (boxplot)
import random
import time
import statistics
import matplotlib.pyplot as plt

def bubble_sort(arr):
    a = arr[:]  # copy
    n = len(a)
    for i in range(n - 1):
        swapped = False
        for j in range(0, n - 1 - i):
            if a[j] > a[j + 1]:
                a[j], a[j + 1] = a[j + 1], a[j]
                swapped = True
        if not swapped:
            break
    return a

def merge_sort(arr):
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return merge(left, right)

def merge(left, right):
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result

def time_sort(fn, data, trials=30):
    times = []
    for _ in range(trials):
        start = time.perf_counter()
        fn(data)
        end = time.perf_counter()
        times.append(end - start)
    return times

def main():
    random.seed(42)
    n = 2000
    trials = 30

    base = [random.randint(0, 10_000_000) for _ in range(n)]

    bubble_times = time_sort(bubble_sort, base, trials=trials)
    merge_times = time_sort(merge_sort, base, trials=trials)

    print(f"Bubble sort mean: {statistics.mean(bubble_times):.6f}s")
    print(f"Merge sort  mean: {statistics.mean(merge_times):.6f}s")

    plt.figure(figsize=(8, 5))
    plt.boxplot([bubble_times, merge_times], labels=["Bubble", "Merge"], showmeans=True)
    plt.ylabel("Seconds")
    plt.title(f"Runtime Distribution (n={n}, trials={trials})")
    plt.grid(axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()
