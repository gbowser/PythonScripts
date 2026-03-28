import math


EARTH_RADIUS_KM = 6378.1


def load_airports(filename):
    """
    Load airport data from a tab-delimited file.

    Expected fields:
    IATA code, airport name, airport location, latitude, longitude
    """
    airports = {}

    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            # Skip blank lines
            if not line:
                continue

            parts = line.split("\t")

            # Skip malformed lines
            if len(parts) != 5:
                continue

            code, name, location, lat, lon = parts

            try:
                airports[code.upper()] = {
                    "name": name,
                    "location": location,
                    "lat": float(lat),
                    "lon": float(lon),
                }
            except ValueError:
                # Skip header or bad numeric rows
                continue

    return airports


def haversine(lat1, lon1, lat2, lon2):
    """
    Compute great-circle distance between two points on Earth in km.
    Inputs are in degrees.
    """
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.asin(math.sqrt(a))
    return EARTH_RADIUS_KM * c


def main():
    filename = "busiest_airports.txt"
    airports = load_airports(filename)

    code1 = input("Enter first IATA code: ").strip().upper()
    code2 = input("Enter second IATA code: ").strip().upper()

    if code1 not in airports:
        print(f"Error: airport code {code1} not found.")
        return

    if code2 not in airports:
        print(f"Error: airport code {code2} not found.")
        return

    a1 = airports[code1]
    a2 = airports[code2]

    distance = haversine(a1["lat"], a1["lon"], a2["lat"], a2["lon"])

    print()
    print(f"{code1}: {a1['name']} ({a1['location']})")
    print(f"{code2}: {a2['name']} ({a2['location']})")
    print(f"Distance = {distance:.2f} km")


if __name__ == "__main__":
    main()