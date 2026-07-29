from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path

import pandas as pd


def _resolve_data_path(filename: str) -> Path:
    for root in (Path("/home/jia"), Path("/Users/peijia/Downloads")):
        p = root / filename
        if p.exists():
            return p
    return Path("/home/jia") / filename


APARTMENT_PATH = _resolve_data_path("korea apartment.xlsx")
STATION_PATH = _resolve_data_path("location of ev stations.xlsx")
CHARGING_PATH = _resolve_data_path("charging amount.xlsx")


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@dataclass(frozen=True)
class GroundingStats:
    apartment_rows: int = 0
    apartment_mean_households: float = 579.0
    apartment_share_with_any_charger: float = 0.838
    apartment_share_ev_gt_chargers: float = 0.405
    apartment_mean_chargers_per_100_households: float = 2.48
    seoul_share_with_any_charger: float = 0.786
    seoul_share_ev_gt_chargers: float = 0.410
    station_rows: int = 4635
    station_share_24h: float = 0.935
    charging_rows: int = 10
    charging_mean_kwh: float = 39.8
    charging_median_kwh: float = 38.1
    charging_mean_hours: float = 2.76
    charging_fast_mean_kwh: float = 43.2
    charging_slow_mean_kwh: float = 34.6


@dataclass(frozen=True)
class ScenarioPreset:
    scenario_name: str
    data_grounded: bool
    home_access_prob: float
    work_access_prob: float
    public_access_prob: float
    public_fallback_prob: float
    residential_slot_ratio: float
    work_slot_ratio: float
    public_slot_ratio: float
    public_price_markup: float
    public_session_overhead_krw: float
    trip_scale: float
    init_soc_low: float
    init_soc_high: float
    forecast_horizon: int
    forecast_noise_std: float
    trip_uncertainty_std: float
    p_fail: float

    def to_config_dict(self) -> dict[str, float | str | bool]:
        return asdict(self)


@lru_cache(maxsize=1)
def load_grounding_stats() -> GroundingStats:
    stats = GroundingStats()

    try:
        apt = pd.read_excel(APARTMENT_PATH, engine="openpyxl", header=1)
        for col in [
            "세대수",
            "차량보유대수(전기차)",
            "전기차 충전시설 설치대수(지상)",
            "전기차 충전시설 설치대수(지하)",
        ]:
            apt[col] = pd.to_numeric(apt[col], errors="coerce").fillna(0)
        apt["total_chargers"] = apt["전기차 충전시설 설치대수(지상)"] + apt["전기차 충전시설 설치대수(지하)"]
        valid_households = apt[apt["세대수"] > 0]
        valid_ev = apt[apt["차량보유대수(전기차)"] > 0]
        seoul = apt[apt["시도"] == "서울특별시"] if "시도" in apt.columns else apt.iloc[0:0]
        seoul_ev = seoul[seoul["차량보유대수(전기차)"] > 0] if len(seoul) else seoul
        stats = GroundingStats(
            apartment_rows=int(len(apt)),
            apartment_mean_households=float(valid_households["세대수"].mean()) if len(valid_households) else stats.apartment_mean_households,
            apartment_share_with_any_charger=float((apt["total_chargers"] > 0).mean()) if len(apt) else stats.apartment_share_with_any_charger,
            apartment_share_ev_gt_chargers=float((valid_ev["차량보유대수(전기차)"] > valid_ev["total_chargers"]).mean()) if len(valid_ev) else stats.apartment_share_ev_gt_chargers,
            apartment_mean_chargers_per_100_households=float((valid_households["total_chargers"] / valid_households["세대수"] * 100.0).mean()) if len(valid_households) else stats.apartment_mean_chargers_per_100_households,
            seoul_share_with_any_charger=float((seoul["total_chargers"] > 0).mean()) if len(seoul) else stats.seoul_share_with_any_charger,
            seoul_share_ev_gt_chargers=float((seoul_ev["차량보유대수(전기차)"] > seoul_ev["total_chargers"]).mean()) if len(seoul_ev) else stats.seoul_share_ev_gt_chargers,
            station_rows=stats.station_rows,
            station_share_24h=stats.station_share_24h,
            charging_rows=stats.charging_rows,
            charging_mean_kwh=stats.charging_mean_kwh,
            charging_median_kwh=stats.charging_median_kwh,
            charging_mean_hours=stats.charging_mean_hours,
            charging_fast_mean_kwh=stats.charging_fast_mean_kwh,
            charging_slow_mean_kwh=stats.charging_slow_mean_kwh,
        )
    except Exception:
        pass

    try:
        station = pd.read_excel(STATION_PATH, engine="openpyxl")
        share_24h = float(station["이용가능시간"].astype(str).str.contains("24").mean()) if len(station) else stats.station_share_24h
        stats = GroundingStats(**{**asdict(stats), "station_rows": int(len(station)), "station_share_24h": share_24h})
    except Exception:
        pass

    try:
        charge = pd.read_excel(CHARGING_PATH, engine="openpyxl")
        charge["충전량"] = pd.to_numeric(charge["충전량"], errors="coerce")
        charge["충전시간(시)"] = pd.to_numeric(charge["충전시간(시)"], errors="coerce").fillna(0)
        charge["충전시간(분)"] = pd.to_numeric(charge["충전시간(분)"], errors="coerce").fillna(0)
        charge["hours_total"] = charge["충전시간(시)"] + charge["충전시간(분)"] / 60.0
        by_type = charge.groupby("충전구분")["충전량"].agg(["mean"]).to_dict().get("mean", {})
        stats = GroundingStats(
            **{
                **asdict(stats),
                "charging_rows": int(len(charge)),
                "charging_mean_kwh": float(charge["충전량"].mean()) if len(charge) else stats.charging_mean_kwh,
                "charging_median_kwh": float(charge["충전량"].median()) if len(charge) else stats.charging_median_kwh,
                "charging_mean_hours": float(charge["hours_total"].mean()) if len(charge) else stats.charging_mean_hours,
                "charging_fast_mean_kwh": float(by_type.get("급속", stats.charging_fast_mean_kwh)),
                "charging_slow_mean_kwh": float(by_type.get("완속", stats.charging_slow_mean_kwh)),
            }
        )
    except Exception:
        pass

    return stats


def get_scenario_preset(name: str) -> ScenarioPreset:
    stats = load_grounding_stats()
    home_access_base = _clamp(1.0 - stats.apartment_share_ev_gt_chargers, 0.45, 0.80)
    public_access_base = _clamp(stats.station_share_24h, 0.75, 0.98)
    residential_slot_base = _clamp(stats.apartment_mean_chargers_per_100_households / 3.0, 0.45, 1.10)

    presets = {
        "synthetic_base": ScenarioPreset(
            scenario_name="synthetic_base",
            data_grounded=False,
            home_access_prob=1.0,
            work_access_prob=1.0,
            public_access_prob=1.0,
            public_fallback_prob=0.0,
            residential_slot_ratio=2.0,
            work_slot_ratio=2.0,
            public_slot_ratio=2.0,
            public_price_markup=1.0,
            public_session_overhead_krw=0.0,
            trip_scale=1.0,
            init_soc_low=0.30,
            init_soc_high=0.90,
            forecast_horizon=168,
            forecast_noise_std=0.0,
            trip_uncertainty_std=0.0,
            p_fail=2000.0,
        ),
        "metro_main": ScenarioPreset(
            scenario_name="metro_main",
            data_grounded=True,
            home_access_prob=home_access_base,
            work_access_prob=0.22,
            public_access_prob=public_access_base,
            public_fallback_prob=0.70,
            residential_slot_ratio=residential_slot_base,
            work_slot_ratio=0.22,
            public_slot_ratio=0.12,
            public_price_markup=1.08,
            public_session_overhead_krw=350.0,
            trip_scale=1.08,
            init_soc_low=0.25,
            init_soc_high=0.88,
            forecast_horizon=24,
            forecast_noise_std=0.10,
            trip_uncertainty_std=0.10,
            p_fail=2000.0,
        ),
        "metro_korea": ScenarioPreset(
            scenario_name="metro_korea",
            data_grounded=True,
            home_access_prob=home_access_base,
            work_access_prob=0.22,
            public_access_prob=public_access_base,
            public_fallback_prob=0.70,
            residential_slot_ratio=residential_slot_base,
            work_slot_ratio=0.22,
            public_slot_ratio=0.12,
            public_price_markup=1.08,
            public_session_overhead_krw=350.0,
            trip_scale=1.08,
            init_soc_low=0.25,
            init_soc_high=0.88,
            forecast_horizon=24,
            forecast_noise_std=0.10,
            trip_uncertainty_std=0.10,
            p_fail=2000.0,
        ),
        "metro_caltech": ScenarioPreset(
            scenario_name="metro_caltech",
            data_grounded=True,
            home_access_prob=0.25,
            work_access_prob=0.90,
            public_access_prob=0.40,
            public_fallback_prob=0.35,
            residential_slot_ratio=0.30,
            work_slot_ratio=0.85,
            public_slot_ratio=0.20,
            public_price_markup=1.20,
            public_session_overhead_krw=500.0,
            trip_scale=1.0,
            init_soc_low=0.35,
            init_soc_high=0.80,
            forecast_horizon=24,
            forecast_noise_std=0.10,
            trip_uncertainty_std=0.10,
            p_fail=2000.0,
        ),
        # --- International external-validity scenarios (session distributions data-grounded via
        #     {nl_office,uk_home}_summary.json; infra access calibrated to documented regional context) ---
        "nl_office": ScenarioPreset(
            scenario_name="nl_office", data_grounded=True,
            home_access_prob=0.45, work_access_prob=0.85, public_access_prob=0.65,
            public_fallback_prob=0.45, residential_slot_ratio=0.45, work_slot_ratio=0.80,
            public_slot_ratio=0.35, public_price_markup=1.15, public_session_overhead_krw=400.0,
            trip_scale=1.0, init_soc_low=0.30, init_soc_high=0.82, forecast_horizon=24,
            forecast_noise_std=0.10, trip_uncertainty_std=0.10, p_fail=2000.0,
        ),
        "nl_office_uncertain": ScenarioPreset(
            scenario_name="nl_office_uncertain", data_grounded=True,
            home_access_prob=0.45, work_access_prob=0.85, public_access_prob=0.65,
            public_fallback_prob=0.45, residential_slot_ratio=0.45, work_slot_ratio=0.80,
            public_slot_ratio=0.35, public_price_markup=1.15, public_session_overhead_krw=400.0,
            trip_scale=1.15, init_soc_low=0.20, init_soc_high=0.70, forecast_horizon=12,
            forecast_noise_std=0.30, trip_uncertainty_std=0.30, p_fail=2000.0,
        ),
        "uk_home": ScenarioPreset(
            scenario_name="uk_home", data_grounded=True,
            home_access_prob=0.85, work_access_prob=0.20, public_access_prob=0.45,
            public_fallback_prob=0.40, residential_slot_ratio=0.85, work_slot_ratio=0.20,
            public_slot_ratio=0.20, public_price_markup=1.20, public_session_overhead_krw=450.0,
            trip_scale=1.0, init_soc_low=0.30, init_soc_high=0.85, forecast_horizon=24,
            forecast_noise_std=0.10, trip_uncertainty_std=0.10, p_fail=2000.0,
        ),
        "uk_home_uncertain": ScenarioPreset(
            scenario_name="uk_home_uncertain", data_grounded=True,
            home_access_prob=0.85, work_access_prob=0.20, public_access_prob=0.45,
            public_fallback_prob=0.40, residential_slot_ratio=0.85, work_slot_ratio=0.20,
            public_slot_ratio=0.20, public_price_markup=1.20, public_session_overhead_krw=450.0,
            trip_scale=1.15, init_soc_low=0.20, init_soc_high=0.70, forecast_horizon=12,
            forecast_noise_std=0.30, trip_uncertainty_std=0.30, p_fail=2000.0,
        ),
        "metro_korea_uncertain": ScenarioPreset(
            scenario_name="metro_korea_uncertain",
            data_grounded=True,
            home_access_prob=home_access_base,
            work_access_prob=0.22,
            public_access_prob=public_access_base,
            public_fallback_prob=0.70,
            residential_slot_ratio=residential_slot_base,
            work_slot_ratio=0.22,
            public_slot_ratio=0.12,
            public_price_markup=1.08,
            public_session_overhead_krw=350.0,
            trip_scale=1.15,
            init_soc_low=0.15,
            init_soc_high=0.70,
            forecast_horizon=12,
            forecast_noise_std=0.30,
            trip_uncertainty_std=0.30,
            p_fail=2000.0,
        ),
        "metro_korea_flat": ScenarioPreset(  # flat tariff sensitivity check
            scenario_name="metro_korea_flat",
            data_grounded=True,
            home_access_prob=home_access_base,
            work_access_prob=0.22,
            public_access_prob=public_access_base,
            public_fallback_prob=0.70,
            residential_slot_ratio=residential_slot_base,
            work_slot_ratio=0.22,
            public_slot_ratio=0.12,
            public_price_markup=1.08,
            public_session_overhead_krw=350.0,
            trip_scale=1.08,
            init_soc_low=0.25,
            init_soc_high=0.88,
            forecast_horizon=24,
            forecast_noise_std=0.10,
            trip_uncertainty_std=0.10,
            p_fail=2000.0,
        ),
        "metro_korea_2tier": ScenarioPreset(  # US-style 2-tier tariff
            scenario_name="metro_korea_2tier",
            data_grounded=True,
            home_access_prob=home_access_base,
            work_access_prob=0.22,
            public_access_prob=public_access_base,
            public_fallback_prob=0.70,
            residential_slot_ratio=residential_slot_base,
            work_slot_ratio=0.22,
            public_slot_ratio=0.12,
            public_price_markup=1.08,
            public_session_overhead_krw=350.0,
            trip_scale=1.08,
            init_soc_low=0.25,
            init_soc_high=0.88,
            forecast_horizon=24,
            forecast_noise_std=0.10,
            trip_uncertainty_std=0.10,
            p_fail=2000.0,
        ),
        "metro_caltech_sce": ScenarioPreset(  # Caltech arrivals under SCE TOU-EV rates
            scenario_name="metro_caltech_sce",
            data_grounded=True,
            home_access_prob=0.25,
            work_access_prob=0.90,
            public_access_prob=0.40,
            public_fallback_prob=0.35,
            residential_slot_ratio=0.30,
            work_slot_ratio=0.85,
            public_slot_ratio=0.20,
            public_price_markup=1.20,
            public_session_overhead_krw=500.0,
            trip_scale=1.0,
            init_soc_low=0.35,
            init_soc_high=0.80,
            forecast_horizon=24,
            forecast_noise_std=0.10,
            trip_uncertainty_std=0.10,
            p_fail=2000.0,
        ),
        "metro_caltech_uncertain": ScenarioPreset(
            scenario_name="metro_caltech_uncertain",
            data_grounded=True,
            home_access_prob=0.25,
            work_access_prob=0.90,
            public_access_prob=0.40,
            public_fallback_prob=0.35,
            residential_slot_ratio=0.30,
            work_slot_ratio=0.85,
            public_slot_ratio=0.20,
            public_price_markup=1.20,
            public_session_overhead_krw=500.0,
            trip_scale=1.15,
            init_soc_low=0.20,
            init_soc_high=0.70,
            forecast_horizon=12,
            forecast_noise_std=0.30,
            trip_uncertainty_std=0.30,
            p_fail=2000.0,
        ),
        "metro_stress": ScenarioPreset(
            scenario_name="metro_stress",
            data_grounded=True,
            home_access_prob=_clamp(home_access_base - 0.15, 0.35, 0.70),
            work_access_prob=0.12,
            public_access_prob=_clamp(public_access_base - 0.12, 0.65, 0.95),
            public_fallback_prob=0.55,
            residential_slot_ratio=_clamp(residential_slot_base * 0.72, 0.30, 0.95),
            work_slot_ratio=0.12,
            public_slot_ratio=0.08,
            public_price_markup=1.12,
            public_session_overhead_krw=500.0,
            trip_scale=1.20,
            init_soc_low=0.20,
            init_soc_high=0.82,
            forecast_horizon=24,
            forecast_noise_std=0.20,
            trip_uncertainty_std=0.20,
            p_fail=2000.0,
        ),
        "metro_moderate": ScenarioPreset(
            scenario_name="metro_moderate",
            data_grounded=True,
            home_access_prob=_clamp(home_access_base + 0.10, 0.55, 0.90),
            work_access_prob=0.30,
            public_access_prob=public_access_base,
            public_fallback_prob=0.80,
            residential_slot_ratio=_clamp(residential_slot_base * 1.15, 0.55, 1.20),
            work_slot_ratio=0.30,
            public_slot_ratio=0.15,
            public_price_markup=1.05,
            public_session_overhead_krw=250.0,
            trip_scale=1.0,
            init_soc_low=0.28,
            init_soc_high=0.90,
            forecast_horizon=24,
            forecast_noise_std=0.08,
            trip_uncertainty_std=0.08,
            p_fail=2000.0,
        ),
        "thrifty_death_stress": ScenarioPreset(
            scenario_name="thrifty_death_stress",
            data_grounded=True,
            home_access_prob=_clamp(home_access_base - 0.25, 0.20, 0.55),
            work_access_prob=0.07,
            public_access_prob=_clamp(public_access_base - 0.22, 0.50, 0.85),
            public_fallback_prob=0.45,
            residential_slot_ratio=_clamp(residential_slot_base * 0.50, 0.20, 0.70),
            work_slot_ratio=0.07,
            public_slot_ratio=0.05,
            public_price_markup=1.15,
            public_session_overhead_krw=650.0,
            trip_scale=1.38,
            init_soc_low=0.15,
            init_soc_high=0.70,
            forecast_horizon=6,
            forecast_noise_std=0.30,
            trip_uncertainty_std=0.30,
            p_fail=2000.0,
        ),
        "thrifty_death_timing_trap": ScenarioPreset(
            scenario_name="thrifty_death_timing_trap",
            data_grounded=True,
            home_access_prob=1.0,
            work_access_prob=0.0,
            public_access_prob=0.0,
            public_fallback_prob=0.0,
            residential_slot_ratio=0.55,
            work_slot_ratio=0.0,
            public_slot_ratio=0.0,
            public_price_markup=1.0,
            public_session_overhead_krw=0.0,
            trip_scale=1.0,
            init_soc_low=0.18,
            init_soc_high=0.32,
            forecast_horizon=6,
            forecast_noise_std=0.10,
            trip_uncertainty_std=0.10,
            p_fail=2000.0,
        ),
        "thrifty_death_timing_trap_price": ScenarioPreset(
            scenario_name="thrifty_death_timing_trap_price",
            data_grounded=True,
            home_access_prob=1.0,
            work_access_prob=0.0,
            public_access_prob=0.0,
            public_fallback_prob=0.0,
            residential_slot_ratio=0.55,
            work_slot_ratio=0.0,
            public_slot_ratio=0.0,
            public_price_markup=1.0,
            public_session_overhead_krw=0.0,
            trip_scale=1.0,
            init_soc_low=0.18,
            init_soc_high=0.32,
            forecast_horizon=6,
            forecast_noise_std=0.10,
            trip_uncertainty_std=0.10,
            p_fail=2000.0,
        ),
    }
    if name not in presets:
        raise ValueError(f"Unknown scenario preset: {name}")
    return presets[name]
