planets = {
    "Mercury": "\u263F",
    "Venus": "\u2640",
    "Earth": "\u2641",
    "Mars": "\u2642",
    "Jupiter": "\u2643",
    "Saturn": "\u2644",
    "Uranus": "\u2645",
    "Neptune": "\u2646",
    "Pluto": "\u2647"
}

for name, symbol in planets.items():
    print(f"{name:8} {symbol}  U+{ord(symbol):04X}")