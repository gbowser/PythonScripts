import numpy as np

# Read in the data from stroop.txt, identifying missing values and
# replacing them with NaN
data = np.genfromtxt(
    "stroop.txt",
    skip_header=1,
    dtype=[("student", "u8"), ("gender", "S1"), ("black", "f8"), ("colour", "f8")],
    delimiter=",",
    missing_values="X",
)
nwords = 25

# Remove invalid rows from data set
filtered_data = data[np.isfinite(data["black"]) & np.isfinite(data["colour"])]

# Extract rows by gender (M/F) and word colour (black/colour) and normalize
# to time taken per word.
fb = filtered_data["black"][filtered_data["gender"] == b"F"] / nwords
mb = filtered_data["black"][filtered_data["gender"] == b"M"] / nwords
fc = filtered_data["colour"][filtered_data["gender"] == b"F"] / nwords
mc = filtered_data["colour"][filtered_data["gender"] == b"M"] / nwords

# Produce statistics: mean and standard deviation by gender and word colour.
mu_fb, sig_fb = np.mean(fb), np.std(fb)
mu_fc, sig_fc = np.mean(fc), np.std(fc)
mu_mb, sig_mb = np.mean(mb), np.std(mb)
mu_mc, sig_mc = np.mean(mc), np.std(mc)

print("Mean and (standard deviation) times per word (sec)")
print("gender |    black      |    colour     | difference")
print(f"   F   | {mu_fb:4.3f} ({sig_fb:4.3f}) | {mu_fc:4.3f} ({sig_fc:4.3f}) |   {mu_fc - mu_fb:4.3f}")
print(f"   M   | {mu_mb:4.3f} ({sig_mb:4.3f}) | {mu_mc:4.3f} ({sig_mc:4.3f}) |   {mu_mc - mu_mb:4.3f}")
