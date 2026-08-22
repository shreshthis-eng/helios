"""
helios/p3_solar_economics.py
Person 3: Solar and Economics Engineer

Answers: "How much solar capacity could fit here, how much electricity might it generate, and what could it cost?"
Responsibility:
- Convert usable roof area (m²) into installable PV capacity (kWp).
- Estimate annual yield (kWh/yr) using Kharghar solar resource assumptions & shading losses.
- Compute installation CapEx (INR), roof lease rent (INR/mo), and payback (years).
- Provide solar and economics confidence metrics.
"""

from typing import List
from helios.contracts.models import SpatialFeaturesP2, SolarEconomicsP3

class Person3SolarEconomicEngineer:
    def __init__(
        self,
        area_per_kwp: float = 6.0,          # 6 m2 usable per kWp capacity
        specific_yield: float = 1450.0,     # kWh/kWp/year in Kharghar
        system_loss_factor: float = 0.85,    # 15% combined system & temperature losses
        capex_per_kwp_inr: float = 48000.0, # ₹48,000 / kWp installed
        electricity_tariff_inr: float = 8.0,# ₹8.0 / kWh commercial tariff in Kharghar
        rent_per_m2_month_inr: float = 30.0 # ₹30 / m2 / month roof rent
    ):
        self.area_per_kwp = area_per_kwp
        self.specific_yield = specific_yield
        self.system_loss_factor = system_loss_factor
        self.capex_per_kwp_inr = capex_per_kwp_inr
        self.electricity_tariff_inr = electricity_tariff_inr
        self.rent_per_m2_month_inr = rent_per_m2_month_inr

    def process_candidate(self, spatial: SpatialFeaturesP2) -> SolarEconomicsP3:
        usable_area = spatial.usable_area_m2
        
        # 1. Capacity in kWp
        capacity_kwp = round(usable_area / self.area_per_kwp, 1)
        
        # 2. Annual Generation in kWh
        yield_kwh = round(capacity_kwp * self.specific_yield * spatial.shading_factor * self.system_loss_factor, 0)
        
        # 3. Installation CapEx in INR
        capex_inr = round(capacity_kwp * self.capex_per_kwp_inr, 0)
        
        # 4. Estimated monthly roof rent
        rent_month_inr = round(usable_area * self.rent_per_m2_month_inr, 0)
        
        # 5. Indicative Payback Period
        annual_energy_value = yield_kwh * self.electricity_tariff_inr
        annual_rent_cost = rent_month_inr * 12.0
        net_annual_benefit = max(1.0, annual_energy_value - annual_rent_cost)
        
        payback_years = round(capex_inr / net_annual_benefit, 1)
        
        # 6. Confidence scores
        solar_conf = round(spatial.spatial_confidence * 0.95, 2)
        econ_conf = round(0.80 if spatial.usable_area_m2 > 100 else 0.65, 2)

        return SolarEconomicsP3(
            candidate_id=spatial.candidate_id,
            estimated_capacity_kwp=capacity_kwp,
            annual_yield_kwh=yield_kwh,
            estimated_capex_inr=capex_inr,
            estimated_rent_inr_month=rent_month_inr,
            indicative_payback_years=payback_years,
            solar_confidence=solar_conf,
            economics_confidence=econ_conf
        )

    def process_batch(self, spatials: List[SpatialFeaturesP2]) -> List[SolarEconomicsP3]:
        return [self.process_candidate(s) for s in spatials]
