import pandas as pd
from pathlib import Path


file_path = Path(__file__).with_name("ionization-energies.csv")

# Read columns 0-4 from the CSV: Element, IE1, IE2, IE3, IE4.
# The first loaded column (Element) is then used as the DataFrame index,
# so the visible data columns become IE1 to IE4 and labels like Li become row names.
df = pd.read_csv( file_path, skiprows=1, index_col=0, usecols=range(5), nrows=11)
# Strip spaces from the column names so labels like IE2 can be accessed cleanly.
df.columns = df.columns.str.strip()
print(f"Second ionization energy of Li: {df.loc['Li'].IE2} eV")
