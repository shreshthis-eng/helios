"""
PV Dataset Generator modeled after the Hebei PVOD dataset (Paper Section 2 & 5).
Generates realistic 15-minute resolution meteorological & photovoltaic power data.
"""

from datetime import datetime, timedelta
import numpy as np
from .solar_terms import calculate_solar_longitude


class PVDataGenerator:
    """Generates synthetic high-resolution 15-min PV data matching paper station parameters."""

    def __init__(self, capacity_mw: float = 20.0, seed: int = 42):
        self.capacity_mw = capacity_mw
        np.random.seed(seed)

    def generate_dataset(self, start_date: datetime = datetime(2018, 7, 1), days: int = 347) -> list:
        """
        Generates dataset for specified number of days with 15-minute sampling (96 steps per day).
        Returns list of feature dictionaries.
        """
        dataset = []
        cur_dt = start_date

        for d in range(days):
            # Calculate seasonal factor based on day of year / solar position
            day_of_year = cur_dt.timetuple().tm_yday
            season_rad = (day_of_year - 80) * (2 * np.pi / 365.25)

            # Max daily solar irradiance varies seasonally
            max_ghi = 800 + 350 * np.sin(season_rad) + np.random.uniform(-50, 50)
            ambient_temp_mean = 15 + 18 * np.sin(season_rad - 0.4)

            for step in range(96):
                dt = cur_dt + timedelta(minutes=15 * step)
                hour = dt.hour + dt.minute / 60.0

                # Solar elevation factor (0 at night, peak at solar noon ~12:30)
                if 6.0 <= hour <= 19.0:
                    solar_elevation = np.sin((hour - 6.0) / 13.0 * np.pi)
                else:
                    solar_elevation = 0.0

                # Cloud fluctuation factor
                cloud_noise = np.clip(np.random.normal(1.0, 0.15), 0.3, 1.1)

                ghi = float(np.clip(max_ghi * (solar_elevation ** 1.2) * cloud_noise, 0.0, 1300.0))
                dhi = float(np.clip(ghi * (0.2 + 0.3 * (1.0 - solar_elevation)), 0.0, ghi))

                temp = float(ambient_temp_mean + 6.0 * np.sin((hour - 8.0) / 24.0 * 2 * np.pi) + np.random.normal(0, 0.5))
                wind_speed = float(np.clip(np.random.lognormal(mean=0.8, sigma=0.4), 0.2, 12.0))

                # Physical PV power output calculation with temperature loss coefficient
                temp_loss = 1.0 - 0.004 * (temp - 25.0)
                efficiency = 0.18 * temp_loss
                power_mw = float(np.clip((ghi / 1000.0) * self.capacity_mw * efficiency * cloud_noise, 0.0, self.capacity_mw))

                dataset.append({
                    "datetime": dt,
                    "ghi": ghi,
                    "dhi": dhi,
                    "temp": temp,
                    "wind_speed": wind_speed,
                    "power_mw": power_mw,
                    "solar_longitude": calculate_solar_longitude(dt)
                })

            cur_dt += timedelta(days=1)

        return dataset
