"""Year-specific nominal tax parameters for England, Wales and Northern Ireland."""
from dataclasses import dataclass
from datetime import date

ADDITIONAL_THRESHOLD = 125140.0

@dataclass(frozen=True)
class TaxParameters:
    allowance: float = 12570.0
    basic_band: float = 37700.0
    additional_threshold: float = ADDITIONAL_THRESHOLD
    taper_start: float = 100000.0
    cgt_exemption: float = 3000.0
    dividend_allowance: float = 500.0
    savings_allowances: tuple = (1000.0, 500.0, 0.0)
    starting_band: float = 5000.0
    other_rates: tuple = (.20, .40, .45)
    property_rates: tuple = (.22, .42, .47)
    savings_rates: tuple = (.22, .42, .47)
    dividend_rates: tuple = (.1075, .3575, .3935)


def period_tax_year(start, end):
    middle = start+(end-start)//2
    return middle.year if middle >= date(middle.year, 4, 6) else middle.year-1


def parameters_for_year(tax_year, inflation):
    # Freeze through 2030/31; annual CPI increases resume without catch-up.
    index = (1+inflation)**max(0, tax_year-2030)
    rates = (.22, .42, .47) if tax_year >= 2027 else (.20, .40, .45)
    return TaxParameters(allowance=12570*index, basic_band=37700*index,
                         property_rates=rates, savings_rates=rates)
