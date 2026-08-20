"""Area calculation in square meters from feddan/qirat/sahm."""

FEDDAN_M2 = 4200.833
QIRAT_M2 = FEDDAN_M2 / 24  # 175.0347...
SAHM_M2 = QIRAT_M2 / 24  # 7.2931...


def calculate_m2(feddan: float, qirat: float, sahm: float) -> float:
    """Returns area in m², rounded to 2 decimal places."""
    total = feddan * FEDDAN_M2 + qirat * QIRAT_M2 + sahm * SAHM_M2
    return round(total, 2)
