def get_resistor_value(bands):
    """
    Translate four resistor color abbreviations into
    (resistance_in_ohms, tolerance_percent).

    Example:
        get_resistor_value(['vi', 'yl', 'rd', 'gr']) -> (7400, 0.5)
    """

    if len(bands) != 4:
        raise ValueError("Exactly 4 color abbreviations are required.")

    resistor_bands = {
        'bk': {'value': 0},
        'br': {'value': 1, 'tolerance': 1},
        'rd': {'value': 2, 'tolerance': 2},
        'or': {'value': 3},
        'yl': {'value': 4},
        'gr': {'value': 5, 'tolerance': 0.5},
        'bl': {'value': 6, 'tolerance': 0.25},
        'vi': {'value': 7, 'tolerance': 0.1},
        'gy': {'value': 8, 'tolerance': 0.05},
        'wh': {'value': 9},
        'au': {'power': -1, 'tolerance': 5},
        'ag': {'power': -2, 'tolerance': 10},
        '--': {'tolerance': 20}
    }

    b1, b2, b3, b4 = bands

    if b1 not in resistor_bands or 'value' not in resistor_bands[b1]:
        raise ValueError(f"Invalid first band: {b1}")
    if b2 not in resistor_bands or 'value' not in resistor_bands[b2]:
        raise ValueError(f"Invalid second band: {b2}")
    if b3 not in resistor_bands or (
        'value' not in resistor_bands[b3] and 'power' not in resistor_bands[b3]
    ):
        raise ValueError(f"Invalid multiplier band: {b3}")
    if b4 not in resistor_bands or 'tolerance' not in resistor_bands[b4]:
        raise ValueError(f"Invalid tolerance band: {b4}")

    multiplier_power = resistor_bands[b3].get('power', resistor_bands[b3]['value'])
    multiplier = 10 ** multiplier_power
    resistance = (
        10 * resistor_bands[b1]['value'] + resistor_bands[b2]['value']
    ) * multiplier
    tolerance = resistor_bands[b4]['tolerance']

    return resistance, tolerance


def format_engineering(value):
    prefixes = [
        (10**9, 'G'),
        (10**6, 'M'),
        (10**3, 'k'),
        (1, ''),
        (10**-3, 'm')
    ]

    for scale, prefix in prefixes:
        if value >= scale:
            formatted = value / scale
            return f"{formatted:g} {prefix}Ω".strip()

    return f"{value:g} Ω"


# Example from the question
resistance, tolerance = get_resistor_value(['vi', 'yl', 'rd', 'gr'])
print(f"{format_engineering(resistance)}, {tolerance:g}%")
