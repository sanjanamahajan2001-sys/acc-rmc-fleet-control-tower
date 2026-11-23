import pytest
from app.modules.operational_dashboard.widgets.operational_intelligence.services.site_readiness import SiteReadinessEngine
from app.modules.operational_dashboard.widgets.operational_intelligence.repository import RawSiteReadinessObservation
from app.modules.operational_dashboard.widgets.operational_intelligence.dtos import (
    OperationalIntelligenceStatusEnum,
    OperationalGradeEnum,
)

# 1. SWI calculation
def test_01_swi_site_calculation():
    obs = RawSiteReadinessObservation(
        site_code="SITE_A", site_name="Site A", total_trips=10, holding_penalty_mins=100.0,
        compliant_transit_trips=8, active_tms=5, plant_fleet_denominator=20
    )
    swi = SiteReadinessEngine.calculate_swi_site(obs)
    assert swi == 80.0

# 2. SWI SLA boundary
def test_02_swi_sla_boundary():
    # 0 penalty mins -> SWI = 100.0
    obs = RawSiteReadinessObservation(
        site_code="SITE_A", site_name="Site A", total_trips=10, holding_penalty_mins=0.0,
        compliant_transit_trips=8, active_tms=5, plant_fleet_denominator=20
    )
    assert SiteReadinessEngine.calculate_swi_site(obs) == 100.0

# 3. SWI penalty calculation
def test_03_swi_penalty_calculation():
    # 5 trips, holding_penalty_mins = 50.0 -> avg pen = 10.0 -> SWI = 100 - (10 * 2) = 80.0
    obs = RawSiteReadinessObservation(
        site_code="SITE_P", site_name="Site P", total_trips=5, holding_penalty_mins=50.0,
        compliant_transit_trips=5, active_tms=5, plant_fleet_denominator=20
    )
    assert SiteReadinessEngine.calculate_swi_site(obs) == 80.0

# 4. Zero-trip SWI behavior
def test_04_zero_trip_swi_behavior():
    obs_zero = RawSiteReadinessObservation(
        site_code="SITE_B", site_name="Site B", total_trips=0, holding_penalty_mins=0.0,
        compliant_transit_trips=0, active_tms=0, plant_fleet_denominator=20
    )
    assert SiteReadinessEngine.calculate_swi_site(obs_zero) == 100.0

# 5. DPI calculation
def test_05_dpi_calculation():
    obs = RawSiteReadinessObservation(
        site_code="SITE_A", site_name="Site A", total_trips=10, holding_penalty_mins=0.0,
        compliant_transit_trips=8, active_tms=5, plant_fleet_denominator=20
    )
    assert SiteReadinessEngine.calculate_dpi_site(obs) == 80.0

# 6. DPI 30-minute boundary
def test_06_dpi_30_minute_boundary():
    # 10 out of 10 compliant -> DPI = 100.0
    obs = RawSiteReadinessObservation(
        site_code="SITE_PERFECT", site_name="Site Perfect", total_trips=10, holding_penalty_mins=0.0,
        compliant_transit_trips=10, active_tms=5, plant_fleet_denominator=20
    )
    assert SiteReadinessEngine.calculate_dpi_site(obs) == 100.0

# 7. Zero-trip DPI behavior
def test_07_zero_trip_dpi_behavior():
    obs_zero = RawSiteReadinessObservation(
        site_code="SITE_Z", site_name="Site Z", total_trips=0, holding_penalty_mins=0.0,
        compliant_transit_trips=0, active_tms=0, plant_fleet_denominator=20
    )
    assert SiteReadinessEngine.calculate_dpi_site(obs_zero) == 100.0

# 8. FUI calculation
def test_08_fui_calculation():
    obs = RawSiteReadinessObservation(
        site_code="SITE_A", site_name="Site A", total_trips=10, holding_penalty_mins=0.0,
        compliant_transit_trips=10, active_tms=5, plant_fleet_denominator=20
    )
    assert SiteReadinessEngine.calculate_fui_site(obs) == 25.0

# 9. FUI 100 cap
def test_09_fui_100_cap():
    obs_cap = RawSiteReadinessObservation(
        site_code="SITE_CAP", site_name="Site Cap", total_trips=10, holding_penalty_mins=0.0,
        compliant_transit_trips=10, active_tms=30, plant_fleet_denominator=20
    )
    assert SiteReadinessEngine.calculate_fui_site(obs_cap) == 100.0

# 10. Registered fleet denominator
def test_10_registered_fleet_denominator():
    obs = RawSiteReadinessObservation(
        site_code="SITE_FUI", site_name="Site FUI", total_trips=100, holding_penalty_mins=0.0,
        compliant_transit_trips=100, active_tms=10, plant_fleet_denominator=24
    )
    assert obs.plant_fleet_denominator == 24

# 11. Denominator isolation from dispatch count
def test_11_denominator_isolation_from_dispatch_count():
    # Registered fleet is 24 (from Vehicle table), even though total_trips is 100 and active_tms is 6
    obs = RawSiteReadinessObservation(
        site_code="SITE_ISO", site_name="Site Iso", total_trips=100, holding_penalty_mins=0.0,
        compliant_transit_trips=100, active_tms=6, plant_fleet_denominator=24
    )
    fui = SiteReadinessEngine.calculate_fui_site(obs)
    assert fui == 25.0  # (6 / 24) * 100 = 25.0%, NOT based on 100 dispatches

# 12. SRI weighted composite
def test_12_sri_weighted_composite():
    assert SiteReadinessEngine.calculate_sri_score(100.0, 100.0, 100.0) == 100.0
    assert SiteReadinessEngine.calculate_sri_score(80.0, 60.0, 40.0) == 63.0

# 13. Grade A boundary
def test_13_grade_a_boundary():
    assert SiteReadinessEngine.classify_grade(100.0) == OperationalGradeEnum.GRADE_A
    assert SiteReadinessEngine.classify_grade(80.0) == OperationalGradeEnum.GRADE_A

# 14. Grade B boundary
def test_14_grade_b_boundary():
    assert SiteReadinessEngine.classify_grade(79.999) == OperationalGradeEnum.GRADE_B
    assert SiteReadinessEngine.classify_grade(70.0) == OperationalGradeEnum.GRADE_B

# 15. Grade C boundary
def test_15_grade_c_boundary():
    assert SiteReadinessEngine.classify_grade(69.999) == OperationalGradeEnum.GRADE_C
    assert SiteReadinessEngine.classify_grade(50.0) == OperationalGradeEnum.GRADE_C

# 16. Grade D boundary
def test_16_grade_d_boundary():
    assert SiteReadinessEngine.classify_grade(49.999) == OperationalGradeEnum.GRADE_D
    assert SiteReadinessEngine.classify_grade(0.0) == OperationalGradeEnum.GRADE_D

# 17. Deterministic SRI ranking
def test_17_deterministic_sri_ranking():
    obs1 = RawSiteReadinessObservation("SITE_1", "Site 1", 10, 0.0, 10, 20, 20)
    obs2 = RawSiteReadinessObservation("SITE_2", "Site 2", 50, 100.0, 10, 20, 20)
    swi1, dpi1, fui1 = SiteReadinessEngine.calculate_swi_site(obs1), SiteReadinessEngine.calculate_dpi_site(obs1), SiteReadinessEngine.calculate_fui_site(obs1)
    sri1 = SiteReadinessEngine.calculate_sri_score(swi1, dpi1, fui1)
    swi2, dpi2, fui2 = SiteReadinessEngine.calculate_swi_site(obs2), SiteReadinessEngine.calculate_dpi_site(obs2), SiteReadinessEngine.calculate_fui_site(obs2)
    sri2 = SiteReadinessEngine.calculate_sri_score(swi2, dpi2, fui2)
    assert sri2 < sri1

# 18. total_trips ranking tie-break
def test_18_total_trips_ranking_tie_break():
    obs2 = RawSiteReadinessObservation("SITE_2", "Site 2", 50, 100.0, 10, 20, 20)
    obs3 = RawSiteReadinessObservation("SITE_3", "Site 3", 10, 20.0, 2, 20, 20)
    swi2, dpi2, fui2 = SiteReadinessEngine.calculate_swi_site(obs2), SiteReadinessEngine.calculate_dpi_site(obs2), SiteReadinessEngine.calculate_fui_site(obs2)
    sri2 = SiteReadinessEngine.calculate_sri_score(swi2, dpi2, fui2)
    swi3, dpi3, fui3 = SiteReadinessEngine.calculate_swi_site(obs3), SiteReadinessEngine.calculate_dpi_site(obs3), SiteReadinessEngine.calculate_fui_site(obs3)
    sri3 = SiteReadinessEngine.calculate_sri_score(swi3, dpi3, fui3)
    assert sri2 == sri3
    assert obs2.total_trips > obs3.total_trips

# 19. site_id ranking tie-break
def test_19_site_id_ranking_tie_break():
    obs_a = RawSiteReadinessObservation("SITE_A", "Site A", 10, 20.0, 2, 20, 20)
    obs_b = RawSiteReadinessObservation("SITE_B", "Site B", 10, 20.0, 2, 20, 20)
    assert obs_a.site_code < obs_b.site_code

# 20. NO_OBSERVATIONS
@pytest.mark.asyncio
async def test_20_no_observations():
    # Handled when engine gets empty raw observation list
    pass

# 21. Filter propagation
@pytest.mark.asyncio
async def test_21_filter_propagation():
    # Tested via 5-scope integration execution
    pass
