"""
Compare bubble sort and merge sort timing across different data sizes.

The script generates random integer datasets from 10 to 1000 entries, times
both algorithms on identical data, and plots elapsed time against dataset size.
"""

from __future__ import annotations

import random
import time
from typing import Callable

try:
    import matplotlib.pyplot as plt
except ModuleNotFoundError as error:
    raise SystemExit(
        "This script needs matplotlib to draw the graph.\n"
        "Install it with: uv add matplotlib\n"
        "Or run this script with the Python environment that already has matplotlib."
    ) from error


Sorter = Callable[[list[int]], list[int]]


def bubble_sort(values: list[int]) -> list[int]:
    """Return a sorted copy of values using bubble sort."""
    sorted_values = values.copy()
    n = len(sorted_values)

    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            if sorted_values[j] > sorted_values[j + 1]:
                sorted_values[j], sorted_values[j + 1] = (
                    sorted_values[j + 1],
                    sorted_values[j],
                )
                swapped = True

        if not swapped:
            break

    return sorted_values


def merge_sort(values: list[int]) -> list[int]:
    """Return a sorted copy of values using merge sort."""
    if len(values) <= 1:
        return values.copy()

    midpoint = len(values) // 2
    left = merge_sort(values[:midpoint])
    right = merge_sort(values[midpoint:])

    return merge(left, right)


def merge(left: list[int], right: list[int]) -> list[int]:
    merged = []
    left_index = 0
    right_index = 0

    while left_index < len(left) and right_index < len(right):
        if left[left_index] <= right[right_index]:
            merged.append(left[left_index])
            left_index += 1
        else:
            merged.append(right[right_index])
            right_index += 1

    merged.extend(left[left_index:])
    merged.extend(right[right_index:])
    return merged


def time_sort(sort_function: Sorter, dataset: list[int], trials: int) -> float:
    """Return average elapsed seconds for sorting the dataset."""
    total_time = 0.0

    for _ in range(trials):
        data_copy = dataset.copy()
        start_time = time.perf_counter()
        sorted_data = sort_function(data_copy)
        total_time += time.perf_counter() - start_time

        if sorted_data != sorted(dataset):
            raise ValueError(f"{sort_function.__name__} returned incorrect results")

    return total_time / trials


def run_simulation(
    min_size: int = 10,
    max_size: int = 1000,
    step: int = 10,
    trials: int = 5,
) -> tuple[list[int], list[float], list[float]]:
    sizes = list(range(min_size, max_size + 1, step))
    bubble_times = []
    merge_times = []

    for size in sizes:
        dataset = [random.randint(0, 10_000) for _ in range(size)]
        bubble_time = time_sort(bubble_sort, dataset, trials)
        merge_time = time_sort(merge_sort, dataset, trials)

        bubble_times.append(bubble_time)
        merge_times.append(merge_time)

        print(
            f"Size {size:4d}: "
            f"bubble sort = {bubble_time:.6f}s, "
            f"merge sort = {merge_time:.6f}s"
        )

    return sizes, bubble_times, merge_times


def plot_results(
    sizes: list[int],
    bubble_times: list[float],
    merge_times: list[float],
) -> None:
    plt.figure(figsize=(10, 6))
    plt.plot(sizes, bubble_times, marker="o", markersize=3, label="Bubble sort")
    plt.plot(sizes, merge_times, marker="s", markersize=3, label="Merge sort")
    plt.xlabel("Dataset size")
    plt.ylabel("Average time (seconds)")
    plt.title("Bubble Sort vs Merge Sort Efficiency")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


def main() -> None:
    random.seed(42)
    sizes, bubble_times, merge_times = run_simulation()
    plot_results(sizes, bubble_times, merge_times)


if __name__ == "__main__":
    main()
