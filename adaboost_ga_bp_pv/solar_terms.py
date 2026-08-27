"""
24 Solar Terms Astronomical Partitioner & Similarity Analyzer
Calculates solar ecliptic longitude lambda(t) and partitions datetime data into
the 24 traditional solar terms (each 15 degrees of solar longitude).
Computes Standardized Euclidean Distance (SED) and Spearman Correlation.
"""

import math
from datetime import datetime, date
import numpy as np

# Acronyms and names matching Paper Table 1 & Table 3
SOLAR_TERMS = [
    {"index": 0,  "acronym": "SE",  "name": "Spring Equinox",       "chinese": "春分", "deg": 0},
    {"index": 1,  "acronym": "PB",  "name": "Pure Brightness",      "chinese": "清明", "deg": 15},
    {"index": 2,  "acronym": "GR",  "name": "Grain Rain",           "chinese": "谷雨", "deg": 30},
    {"index": 3,  "acronym": "BSU", "name": "Beginning of Summer",  "chinese": "立夏", "deg": 45},
    {"index": 4,  "acronym": "GB",  "name": "Grain Buds",           "chinese": "小满", "deg": 60},
    {"index": 5,  "acronym": "GE",  "name": "Grain in Ear",         "chinese": "芒种", "deg": 75},
    {"index": 6,  "acronym": "SS",  "name": "Summer Solstice",      "chinese": "夏至", "deg": 90},
    {"index": 7,  "acronym": "MIH", "name": "Minor Heat",           "chinese": "小暑", "deg": 105},
    {"index": 8,  "acronym": "MAH", "name": "Major Heat",           "chinese": "大暑", "deg": 120},
    {"index": 9,  "acronym": "BA",  "name": "Beginning of Autumn",  "chinese": "立秋", "deg": 135},
    {"index": 10, "acronym": "EH",  "name": "End of Heat",          "chinese": "处暑", "deg": 150},
    {"index": 11, "acronym": "WD",  "name": "White Dew",            "chinese": "白露", "deg": 165},
    {"index": 12, "acronym": "AE",  "name": "Autumn Equinox",       "chinese": "秋分", "deg": 180},
    {"index": 13, "acronym": "CD",  "name": "Cold Dew",             "chinese": "寒露", "deg": 195},
    {"index": 14, "acronym": "FD",  "name": "Frost's Descent",       "chinese": "霜降", "deg": 210},
    {"index": 15, "acronym": "BW",  "name": "Beginning of Winter",  "chinese": "立冬", "deg": 225},
    {"index": 16, "acronym": "MIS", "name": "Minor Snow",           "chinese": "小雪", "deg": 240},
    {"index": 17, "acronym": "MAS", "name": "Major Snow",           "chinese": "大雪", "deg": 255},
    {"index": 18, "acronym": "WS",  "name": "Winter Solstice",      "chinese": "冬至", "deg": 270},
    {"index": 19, "acronym": "MIC", "name": "Minor Cold",           "chinese": "小寒", "deg": 285},
    {"index": 20, "acronym": "MAC", "name": "Major Cold",           "chinese": "大寒", "deg": 300},
    {"index": 21, "acronym": "BSP", "name": "Beginning of Spring",  "chinese": "立春", "deg": 315},
    {"index": 22, "acronym": "RW",  "name": "Rain Water",           "chinese": "雨水", "deg": 330},
    {"index": 23, "acronym": "AI",  "name": "Awakening of Insects", "chinese": "惊蛰", "deg": 345},
]


def calculate_solar_longitude(dt: datetime) -> float:
    """
    Calculate solar ecliptic longitude lambda in degrees [0, 360) for a given datetime.
    Uses high-precision Keplerian solar position approximation.
    """
    # Julian Date calculation
    year, month, day = dt.year, dt.month, dt.day
    hour = dt.hour + dt.minute / 60.0 + dt.second / 3600.0

    if month <= 2:
        year -= 1
        month += 12

    A = math.floor(year / 100.0)
    B = 2 - A + math.floor(A / 4.0)

    jd = math.floor(365.25 * (year + 4716)) + math.floor(30.6001 * (month + 1)) + day + B - 1524.5 + hour / 24.0
    d = jd - 2451545.0  # Days since J2000.0

    # Mean anomaly of the Sun (degrees)
    g = math.radians((357.529 + 0.98560028 * d) % 360.0)

    # Mean ecliptic longitude of the Sun (degrees)
    q = (280.459 + 0.98564736 * d) % 360.0

    # True ecliptic longitude lambda (degrees)
    lambda_deg = q + 1.915 * math.sin(g) + 0.020 * math.sin(2 * g)
    return lambda_deg % 360.0


def get_solar_term_index(dt: datetime) -> int:
    """Returns solar term index (0..23) for a given datetime."""
    sol_long = calculate_solar_longitude(dt)
    term_idx = int(sol_long // 15.0) % 24
    return term_idx


class SolarTermPartitioner:
    """Partitions PV dataset into 24 Solar Terms or Gregorian half-months."""

    def __init__(self):
        self.terms = SOLAR_TERMS

    def partition_by_solar_terms(self, dataset: list) -> dict:
        """
        Groups dataset items by solar term.
        Each item in dataset must be a dict or tuple containing a 'datetime' key/field.
        """
        partitions = {term["acronym"]: [] for term in self.terms}
        for row in dataset:
            dt = row["datetime"]
            idx = get_solar_term_index(dt)
            acronym = self.terms[idx]["acronym"]
            partitions[acronym].append(row)
        return partitions

    def partition_by_gregorian_half_months(self, dataset: list) -> dict:
        """
        Groups dataset items into 24 Gregorian half-month bins (1st-15th, 16th-end of month).
        Used for benchmark comparisons as done in paper Section 4.3.
        """
        partitions = {}
        for row in dataset:
            dt = row["datetime"]
            half = 1 if dt.day <= 15 else 2
            key = f"M{dt.month:02d}_H{half}"
            if key not in partitions:
                partitions[key] = []
            partitions[key].append(row)
        return partitions

    @staticmethod
    def calc_standardized_euclidean_distance(x: np.ndarray, y: np.ndarray) -> float:
        """
        Calculates Standardized Euclidean Distance (SED) between feature vectors x and y:
        d(x, y) = sqrt( sum( (x_i - y_i)^2 / s_i ) )
        where s_i is variance of feature i across samples.
        """
        var = np.var(np.vstack([x, y]), axis=0)
        var = np.where(var == 0, 1e-8, var)  # avoid division by zero
        sed = np.sqrt(np.sum(((x - y) ** 2) / var))
        return float(sed)

    @staticmethod
    def calc_spearman_correlation(x: np.ndarray, y: np.ndarray) -> float:
        """
        Calculates Spearman rank correlation coefficient between two 1D arrays x and y.
        """
        rank_x = np.argsort(np.argsort(x))
        rank_y = np.argsort(np.argsort(y))
        n = len(x)
        if n <= 1:
            return 1.0
        d = rank_x - rank_y
        d_sq = np.sum(d ** 2)
        rho = 1.0 - (6.0 * d_sq) / (n * (n ** 2 - 1))
        return float(rho)
