from pathlib import Path

import pandas as pd

file_path = Path(__file__).with_name("f1-data.csv")
df = pd.read_csv(file_path)

# Create a DataFrame of race winners.
winners = df[df["Position"] == 1]
# Group by Driver and count wins.
g = winners.groupby("Driver")
print("Drivers by number of wins")
print(g["Driver"].count().sort_values(ascending=False))

# Group by Constructor and count wins.
g = winners.groupby("Constructor")
print()
print("Constructors by number of wins")
print(g["Constructor"].count().sort_values(ascending=False))

# Ensure the 'Fastest Lap' column is a datetime, and convert to ms.
df["Fastest Lap"] = pd.to_datetime(df["Fastest Lap"], format="%M:%S.%f")
df["Fastest Lap (ms)"] = (
    df["Fastest Lap"].dt.minute * 60000
    + df["Fastest Lap"].dt.second * 1000
    + df["Fastest Lap"].dt.microsecond / 1000
)
# Group Fastest Lap by Circuit and calculate mean.
g = df[df["Fastest Lap (ms)"].notna()].groupby("Circuit")
tdf = g["Fastest Lap (ms)"].mean().sort_values()


def to_time_str(time_ms):
    """Convert from ms to string in form MM:SS.[MS]"""
    mins, time_ms = divmod(time_ms, 60000)
    secs = time_ms / 1000
    return "{:02d}:{:6.3f}".format(int(mins), secs)


print()
print("Mean fastest lap times by circuit")
for circuit, time in tdf.items():
    print(to_time_str(time), circuit)
