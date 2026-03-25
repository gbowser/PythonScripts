import numpy as np


def dms_to_decimal(coordinate):
    degrees_text, remainder = coordinate.split("d")
    minutes_text, remainder = remainder.split("m")
    seconds_text, direction = remainder.split("s")

    decimal = int(degrees_text) + int(minutes_text) / 60 + int(seconds_text) / 3600

    if direction == "S" or direction == "W":
        return -decimal
    return decimal


def parse_date(date_text):
    if date_text == "" or date_text == "-":
        return np.datetime64("NaT")
    day_text, month_text, year_text = date_text.split("/")
    iso_date = f"{int(year_text):04d}-{int(month_text):02d}-{int(day_text):02d}"
    return np.datetime64(iso_date)


raw_data = np.genfromtxt(
    "ex6-2-b-mountain-data.txt",
    delimiter=[14, 8, 12, 13, 11, 10],
    dtype=[
        ("mountain", "U14"),
        ("height", "i4"),
        ("first_ascent", "U10"),
        ("first_winter", "U10"),
        ("latitude", "U12"),
        ("longitude", "U12"),
    ],
    skip_header=12,
    skip_footer=1,
    autostrip=True,
)

data = np.empty(
    raw_data.shape,
    dtype=[
        ("mountain", "U14"),
        ("height", "i4"),
        ("first_ascent", "datetime64[D]"),
        ("first_winter", "datetime64[D]"),
        ("latitude", "f8"),
        ("longitude", "f8"),
    ],
)

data["mountain"] = raw_data["mountain"]
data["height"] = raw_data["height"]
data["first_ascent"] = np.array([parse_date(date) for date in raw_data["first_ascent"]])
data["first_winter"] = np.array([parse_date(date) for date in raw_data["first_winter"]])
data["latitude"] = np.array([dms_to_decimal(latitude) for latitude in raw_data["latitude"]])
data["longitude"] = np.array([dms_to_decimal(longitude) for longitude in raw_data["longitude"]])

print(f"{data}")

print(f"The lowest mountain is {data['mountain'][data['height'].argmin()]} at {data['height'].min()} m")

valid_winter_dates = ~np.isnat(data["first_winter"])
valid_winter_indices = np.where(valid_winter_dates)[0]

print(f"The most northerly mountain is {data['mountain'][data['latitude'].argmax()]}")
print(f"Its latitude in decimal degrees is {data['latitude'][data['latitude'].argmax()]:.4f}")
print(f"The most easterly mountain is {data['mountain'][data['longitude'].argmax()]}")
print(f"Its longitude in decimal degrees is {data['longitude'][data['longitude'].argmax()]:.4f}")
print(f"The most recent first winter ascent was of {data['mountain'][valid_winter_indices[data['first_winter'][valid_winter_dates].argmax()]]} in {data['first_winter'][valid_winter_indices[data['first_winter'][valid_winter_dates].argmax()]]}")
print(f"The most recent first ascent was of {data['mountain'][data['first_ascent'].argmax()]} in {data['first_ascent'][data['first_ascent'].argmax()]}")
