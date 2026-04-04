from pathlib import Path

import pandas as pd

file_path = Path(__file__).with_name("bond-lengths.xlsx")


df = pd.read_excel(
    file_path,
    index_col=0,  # the first column contains the index labels
    skipfooter=2,  # ignore the last two lines of the sheet
    header=1,  # take the column names from the second row
    usecols="A:E",  # use Excel columns labeled A-E
    sheet_name="Diatomics",  # take data from this sheet
)

print(df)
