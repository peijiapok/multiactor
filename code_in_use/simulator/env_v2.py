"""
Enhanced EV Charging Environment (v2) for the journal paper.

Wraps the existing EVEnvironment from ev-charging-rl/RL_5.py with:
  - Non-unity charging efficiency (eta=0.90 L2, eta=0.85 DCFC)
  - Linear battery degradation cost
  - Real KEPCO 3-tier TOU pricing
  - Configurable forecast horizon (for E6 ablation)
"""

import sys
import os
import numpy as np
import numpy.typing as npt
from dataclasses import dataclass

from data_grounding import get_scenario_preset

sys.path.insert(0, os.path.expanduser("~/ev-charging-rl"))


@dataclass
class EnvV2Config:
    n_cars: int = 1000
    episode_hours: int = 168
    eta_l2: float = 0.90
    eta_dcfc: float = 0.85
    bcap_kwh: float = 64.0
    soc_min: float = 0.20
    soc_max: float = 0.95
    degradation_cost_per_kwh: float = 0.15       # KRW/kWh throughput
    off_peak_price_krw_per_kwh: float = 57.6
    solar_off_price_krw_per_kwh: float = 65.0
    mid_peak_price_krw_per_kwh: float = 109.0
    on_peak_price_krw_per_kwh: float = 232.5
    p_fail: float = 100_000.0
    p_cancel: float = 2_000.0
    p_anxiety: float = 500.0
    shadow_price_failure: float = 50_000.0        # for RAC metric
    forecast_horizon: int = 168                    # hours (168 = perfect)
    forecast_noise_std: float = 0.0
    trip_uncertainty_std: float = 0.0
    trip_scale: float = 1.0
    init_soc_low: float = 0.30
    init_soc_high: float = 0.90
    seed: int = 42
    scenario_name: str = "synthetic_base"
    data_grounded: bool = False
    home_access_prob: float = 1.0
    work_access_prob: float = 1.0
    public_access_prob: float = 1.0
    public_fallback_prob: float = 0.0
    residential_slot_ratio: float = 2.0
    work_slot_ratio: float = 2.0
    public_slot_ratio: float = 2.0
    public_price_markup: float = 1.0
    public_session_overhead_krw: float = 0.0
    scenario_preset_materialized: bool = False


KEPCO_TOU = {
    "off_peak":  {"hours": list(range(23, 24)) + list(range(0, 6)), "rate": 57.6},
    "mid_peak":  {"hours": list(range(6, 11)) + list(range(15, 17)), "rate": 109.0},
    "on_peak":   {"hours": list(range(17, 23)), "rate": 232.5},
    "solar_off": {"hours": list(range(11, 15)), "rate": 65.0},
}

SOLAR_OFF_HOURS = set(range(11, 15))
OFF_PEAK_HOURS = {23, 0, 1, 2, 3, 4, 5}
MID_PEAK_HOURS = set(range(6, 11)) | {15, 16}
ON_PEAK_HOURS = set(range(17, 23))


def get_kepco_price(hour_of_day: int) -> float:
    h = hour_of_day % 24
    if h in SOLAR_OFF_HOURS:
        return 65.0
    if h in OFF_PEAK_HOURS:
        return 57.6
    if h in MID_PEAK_HOURS:
        return 109.0
    if h in ON_PEAK_HOURS:
        return 232.5
    return 109.0


def get_kepco_price_schedule(n_hours: int = 168) -> npt.NDArray[np.float64]:
    return np.array([get_kepco_price(h) for h in range(n_hours)])


class EVEnvironmentV2:
    """
    Enhanced wrapper around EVEnvironment with journal-paper features.

    Can run standalone (simplified physics) or wrap the original RL_5.py env.
    """

    def __init__(self, config: EnvV2Config | None = None, base_env=None):
        self.config = config or EnvV2Config()
        self._apply_scenario_defaults()
        self.rng = np.random.default_rng(self.config.seed)
        self.price_schedule = self._build_price_schedule(self.config.episode_hours)

        self.base_env = base_env
        self.n_cars = self.config.n_cars
        self.t = 0

        self.soc = np.zeros(self.n_cars)
        self.locations = np.zeros(self.n_cars, dtype=int)
        self.location_schedule = None
        self.trip_schedule = None
        self.mandatory_trip_schedule = None
        self.realized_trip_schedule = None
        self.realized_mandatory_trip_schedule = None
        self.anxiety_thresholds = np.zeros(self.n_cars)
        self.anxiety_baseline = np.zeros(self.n_cars)
        self.cumulative_throughput = np.zeros(self.n_cars)
        self.cumulative_charge_kwh = np.zeros(self.n_cars)
        self.failure_count = 0
        self.cancel_count = 0
        self.has_home_access = np.ones(self.n_cars, dtype=bool)
        self.has_work_access = np.ones(self.n_cars, dtype=bool)
        self.has_public_access = np.ones(self.n_cars, dtype=bool)
        self.public_fallback = np.zeros(self.n_cars, dtype=bool)
        self.archetypes = np.array(["commuter"] * self.n_cars, dtype=object)
        self._current_charge_modes = np.array(["none"] * self.n_cars, dtype=object)
        self._last_raw_actions = np.zeros(self.n_cars, dtype=int)
        self._last_effective_actions = np.zeros(self.n_cars, dtype=int)
        self._last_invalid_charge_mask = np.zeros(self.n_cars, dtype=bool)
        self._last_charge_stored_actual_kwh = np.zeros(self.n_cars)

    def _build_price_schedule(self, n_hours: int) -> npt.NDArray[np.float64]:
        prices = np.zeros(n_hours, dtype=float)
        for h in range(n_hours):
            hod = h % 24
            if hod in SOLAR_OFF_HOURS:
                prices[h] = self.config.solar_off_price_krw_per_kwh
            elif hod in OFF_PEAK_HOURS:
                prices[h] = self.config.off_peak_price_krw_per_kwh
            elif hod in MID_PEAK_HOURS:
                prices[h] = self.config.mid_peak_price_krw_per_kwh
            elif hod in ON_PEAK_HOURS:
                prices[h] = self.config.on_peak_price_krw_per_kwh
            else:
                prices[h] = self.config.mid_peak_price_krw_per_kwh
        return prices

    def _apply_scenario_defaults(self):
        if self.config.scenario_name == "synthetic_base":
            return
        preset = get_scenario_preset(self.config.scenario_name)
        if not self.config.scenario_preset_materialized:
            defaults = preset.to_config_dict()
            for key, value in defaults.items():
                if key == "scenario_name":
                    continue
                current = getattr(self.config, key, None)
                baseline = getattr(EnvV2Config, key, None)
                if current == baseline:
                    setattr(self.config, key, value)
        # Scenario-specific tariff overrides (tariff sensitivity study)
        if self.config.scenario_name == "metro_korea_flat":
            # Flat tariff: single price equal to KEPCO mean (roughly 114 KRW/kWh)
            flat = 114.0
            self.config.off_peak_price_krw_per_kwh = flat
            self.config.mid_peak_price_krw_per_kwh = flat
            self.config.on_peak_price_krw_per_kwh = flat
            self.config.solar_off_price_krw_per_kwh = flat
        elif self.config.scenario_name == "metro_korea_2tier":
            # US-style 2-tier: off-peak 57.6, on-peak 172.8 (ratio 3x), merging mid into on
            self.config.off_peak_price_krw_per_kwh = 57.6
            self.config.mid_peak_price_krw_per_kwh = 172.8
            self.config.on_peak_price_krw_per_kwh = 172.8
            self.config.solar_off_price_krw_per_kwh = 57.6
        elif self.config.scenario_name == "metro_caltech_sce":
            # SCE TOU-EV-9 (2024 CA rates) converted at 1 USD ≈ 1400 KRW:
            # Super-off-peak (overnight): ≈0.07 USD/kWh → 98 KRW
            # Mid-peak (daytime): ≈0.17 USD/kWh → 238 KRW
            # On-peak (4-9pm weekdays): ≈0.42 USD/kWh → 588 KRW
            self.config.off_peak_price_krw_per_kwh = 98.0
            self.config.mid_peak_price_krw_per_kwh = 238.0
            self.config.on_peak_price_krw_per_kwh = 588.0
            self.config.solar_off_price_krw_per_kwh = 238.0

    def reset(self) -> dict[str, object]:
        self.t = 0
        self.soc = self.rng.uniform(self.config.init_soc_low, self.config.init_soc_high, size=self.n_cars)
        self.locations = np.zeros(self.n_cars, dtype=int)
        self.location_schedule = np.zeros((self.n_cars, self.config.episode_hours), dtype=int)
        self.cumulative_throughput = np.zeros(self.n_cars)
        self.cumulative_charge_kwh = np.zeros(self.n_cars)
        self.failure_count = 0
        self.cancel_count = 0
        self.anxiety_baseline = self.rng.uniform(0.15, 0.25, size=self.n_cars)
        self._sample_access_profiles()

        planned_schedule, planned_mandatory, location_schedule = self._generate_trip_schedule()
        self.trip_schedule = planned_schedule
        self.mandatory_trip_schedule = planned_mandatory
        self.location_schedule = location_schedule
        self.locations = self.location_schedule[:, 0].copy()
        if self.config.trip_uncertainty_std > 0:
            noise = self.rng.normal(0.0, self.config.trip_uncertainty_std, size=planned_schedule.shape)
            realized = planned_schedule * np.clip(1.0 + noise, 0.1, None)
            realized_mandatory = planned_mandatory * np.clip(1.0 + noise, 0.1, None)
            self.realized_trip_schedule = realized
            self.realized_mandatory_trip_schedule = realized_mandatory
        else:
            self.realized_trip_schedule = planned_schedule.copy()
            self.realized_mandatory_trip_schedule = planned_mandatory.copy()
        self.anxiety_thresholds = self._compute_anxiety_thresholds()

        return self._get_obs()

    def _charge_location_type_for_agent(self, agent_idx: int) -> str | None:
        loc = int(self.locations[agent_idx])
        if loc == 1 and bool(self.has_work_access[agent_idx]):
            return "work"
        if loc == 0 and bool(self.has_home_access[agent_idx]):
            return "home"
        if bool(self.has_public_access[agent_idx]) and bool(self.public_fallback[agent_idx]):
            return "public"
        return None

    def charge_available_mask(self) -> npt.NDArray[np.bool_]:
        return np.array(
            [self._charge_location_type_for_agent(i) is not None for i in range(self.n_cars)],
            dtype=bool,
        )

    def _mask_invalid_charge_actions(self, actions: npt.NDArray[np.int_]) -> tuple[npt.NDArray[np.int_], npt.NDArray[np.bool_]]:
        effective = np.asarray(actions, dtype=int).copy()
        charge_requested = effective <= 5
        available = self.charge_available_mask()
        invalid = charge_requested & ~available
        effective[invalid] = 6
        return effective, invalid

    def step(self, actions: npt.NDArray[np.int_]):
        """
        Execute one timestep for all agents.

        Args:
            actions: shape (n_cars,), each in {0..7}

        Returns:
            (obs, rewards, done, info)
        """
        rewards = np.zeros(self.n_cars)
        failures = np.zeros(self.n_cars, dtype=bool)
        price = self.price_schedule[self.t % len(self.price_schedule)]
        if self.location_schedule is not None and self.t < self.location_schedule.shape[1]:
            self.locations = self.location_schedule[:, self.t].copy()
        raw_actions = np.asarray(actions, dtype=int).copy()
        actions, invalid_charge_mask = self._mask_invalid_charge_actions(raw_actions)
        self._last_raw_actions = raw_actions
        self._last_effective_actions = actions.copy()
        self._last_invalid_charge_mask = invalid_charge_mask.copy()
        granted_modes = self._allocate_charge_modes(actions)
        self._current_charge_modes = granted_modes.copy()
        self._last_charge_stored_actual_kwh = np.zeros(self.n_cars)

        for i in range(self.n_cars):
            a = int(actions[i])
            trip_energy = self._get_trip_energy(i, self.t)
            step_throughput_kwh = 0.0

            if a <= 5 and granted_modes[i] != "none":
                eta = self._get_efficiency(granted_modes[i])
                p_charge = self._get_charge_power(granted_modes[i])
                old_soc = float(self.soc[i])
                delta_soc = (eta * p_charge * 1.0) / self.config.bcap_kwh
                charge_cost = price * self._price_multiplier(granted_modes[i]) * p_charge * 1.0 + self._session_overhead(granted_modes[i])

                self.soc[i] = min(self.config.soc_max, self.soc[i] + delta_soc)
                # Battery-side usable charge service, after the soc_max clamp.
                # The simulator timestep is one hour; eta is the same one-way
                # charging efficiency used in the SoC update above.
                self._last_charge_stored_actual_kwh[i] = max(0.0, float(self.soc[i]) - old_soc) * self.config.bcap_kwh
                charged_kwh = abs(delta_soc) * self.config.bcap_kwh
                self.cumulative_throughput[i] += charged_kwh
                self.cumulative_charge_kwh[i] += charged_kwh
                step_throughput_kwh += charged_kwh
                rewards[i] -= charge_cost

            elif a == 7:
                if self._is_discretionary_trip(i, self.t):
                    rewards[i] -= self.config.p_cancel
                    self.cancel_count += 1
                    trip_energy = 0.0

            if trip_energy > 0:
                energy_needed_soc = trip_energy / self.config.bcap_kwh
                if self.soc[i] >= energy_needed_soc:
                    self.soc[i] -= energy_needed_soc
                    self.cumulative_throughput[i] += trip_energy
                    step_throughput_kwh += trip_energy
                else:
                    failures[i] = True
                    self.failure_count += 1
                    rewards[i] -= self.config.p_fail

            deg_cost = self.config.degradation_cost_per_kwh * step_throughput_kwh
            rewards[i] -= deg_cost

            if self.soc[i] < self.anxiety_thresholds[i]:
                rewards[i] -= self.config.p_anxiety

        self.t += 1
        done = self.t >= self.config.episode_hours
        if not done and self.location_schedule is not None and self.t < self.location_schedule.shape[1]:
            self.locations = self.location_schedule[:, self.t].copy()
        self.anxiety_thresholds = self._compute_anxiety_thresholds()

        # Aggregate charging demand this step (sum of granted charge powers)
        agg_kw = 0.0
        for i in range(self.n_cars):
            a = int(actions[i])
            if a <= 5 and granted_modes[i] != "none":
                agg_kw += self._get_charge_power(granted_modes[i])
        info = {
            "failures": failures,
            "failure_count": self.failure_count,
            "cancel_count": self.cancel_count,
            "price": price,
            "mean_soc": self.soc.mean(),
            "agg_demand_kw": float(agg_kw),
            "raw_actions": raw_actions.copy(),
            "effective_actions": actions.copy(),
            "invalid_charge_request_mask": invalid_charge_mask.copy(),
            "invalid_charge_request_count": int(invalid_charge_mask.sum()),
        }

        return self._get_obs(), rewards, done, info

    def _get_obs(self) -> dict[str, object]:
        forecast_h = min(self.config.forecast_horizon, self.config.episode_hours - self.t)
        if forecast_h <= 0:
            future_demand = np.zeros(168)
        else:
            future_demand = np.zeros(168)
            for h in range(min(forecast_h, 168)):
                t_future = self.t + h
                if t_future < self.config.episode_hours and self.trip_schedule is not None:
                    future_demand[h] = self.trip_schedule[:, t_future % self.trip_schedule.shape[1]].mean()
                    if self.config.forecast_noise_std > 0:
                        noise = self.rng.normal(0.0, self.config.forecast_noise_std)
                        future_demand[h] = max(0.0, future_demand[h] * (1.0 + noise))

        return {
            "soc": self.soc.copy(),
            "locations": self.locations.copy(),
            "price": self.price_schedule[self.t % len(self.price_schedule)],
            "time_of_week": self.t,
            "anxiety_thresholds": self.anxiety_thresholds.copy(),
            "future_demand": future_demand,
            "solar_index": self._solar_index(),
            "charge_available": self.charge_available_mask(),
        }

    def _sample_access_profiles(self):
        self.has_home_access = self.rng.random(self.n_cars) < self.config.home_access_prob
        self.has_work_access = self.rng.random(self.n_cars) < self.config.work_access_prob
        self.has_public_access = self.rng.random(self.n_cars) < self.config.public_access_prob
        self.public_fallback = self.rng.random(self.n_cars) < self.config.public_fallback_prob

    def _allocate_charge_modes(self, actions: npt.NDArray[np.int_]) -> npt.NDArray[np.ndarray]:
        modes = np.array(["none"] * self.n_cars, dtype=object)
        requested = np.asarray(actions) <= 5
        home_idx: list[int] = []
        work_idx: list[int] = []
        public_idx: list[int] = []

        for i in np.where(requested)[0]:
            loc = int(self.locations[i])
            if loc == 1 and self.has_work_access[i]:
                work_idx.append(int(i))
            elif loc == 0 and self.has_home_access[i]:
                home_idx.append(int(i))
            elif self.has_public_access[i] and self.public_fallback[i]:
                public_idx.append(int(i))

        allocations = {
            "home": self._apply_slot_limit(home_idx, self._slot_limit(self.config.residential_slot_ratio)),
            "work": self._apply_slot_limit(work_idx, self._slot_limit(self.config.work_slot_ratio)),
            "public": self._apply_slot_limit(public_idx, self._slot_limit(self.config.public_slot_ratio)),
        }
        for mode, idxs in allocations.items():
            for idx in idxs:
                modes[idx] = mode
        return modes

    def _slot_limit(self, ratio: float) -> int:
        if ratio >= 1.5:
            return self.n_cars
        return max(1, int(np.ceil(self.n_cars * ratio)))

    def _apply_slot_limit(self, indices: list[int], limit: int) -> npt.NDArray[np.int_]:
        if len(indices) <= limit:
            return np.asarray(indices, dtype=int)
        chosen = self.rng.choice(np.asarray(indices, dtype=int), size=limit, replace=False)
        return np.sort(chosen)

    def _get_efficiency(self, charge_mode: str) -> float:
        if charge_mode == "public":
            return self.config.eta_dcfc
        return self.config.eta_l2

    def _get_charge_power(self, charge_mode: str) -> float:
        if charge_mode == "public":
            return 50.0
        return 7.0

    def _price_multiplier(self, charge_mode: str) -> float:
        if charge_mode == "public":
            return self.config.public_price_markup
        return 1.0

    def _session_overhead(self, charge_mode: str) -> float:
        if charge_mode == "public":
            return self.config.public_session_overhead_krw
        return 0.0

    def _solar_index(self) -> float:
        h = self.t % 24
        if 6 <= h <= 18:
            return max(0.0, np.sin(np.pi * (h - 6) / 12))
        return 0.0

    def _generate_trip_schedule(self) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64], npt.NDArray[np.int_]]:
        if self.config.scenario_name == "thrifty_death_timing_trap":
            return self._generate_timing_trap_schedule()
        if self.config.scenario_name in ("metro_caltech", "metro_caltech_uncertain", "metro_caltech_sce",
                                          "nl_office", "nl_office_uncertain",
                                          "uk_home", "uk_home_uncertain"):
            return self._generate_caltech_schedule()
        schedule = np.zeros((self.n_cars, self.config.episode_hours))
        mandatory = np.zeros((self.n_cars, self.config.episode_hours))
        location_schedule = np.zeros((self.n_cars, self.config.episode_hours), dtype=int)
        for i in range(self.n_cars):
            archetype = self.rng.choice(["commuter", "part_time", "unemployed"],
                                        p=[0.6, 0.1, 0.3])
            self.archetypes[i] = archetype
            if archetype == "commuter":
                for day in range(7):
                    if day < 5:
                        base = day * 24
                        to_work = self.rng.uniform(10, 20)
                        from_work = self.rng.uniform(10, 20)
                        schedule[i, base + 8] = to_work
                        schedule[i, base + 18] = from_work
                        mandatory[i, base + 8] = to_work
                        mandatory[i, base + 18] = from_work
                        location_schedule[i, base + 9: base + 18] = 1
                        if self.rng.random() < 0.4:
                            morning_errand = self.rng.uniform(5, 10)
                            afternoon_errand = self.rng.uniform(5, 10)
                            schedule[i, base + 7] = morning_errand
                            schedule[i, base + 15] = afternoon_errand
                            mandatory[i, base + 7] = morning_errand
                            mandatory[i, base + 15] = afternoon_errand
                            location_schedule[i, base + 7] = 13
                            location_schedule[i, base + 15] = 13
            elif archetype == "part_time":
                work_days = self.rng.choice(5, size=3, replace=False)
                for day in work_days:
                    base = day * 24
                    to_work = self.rng.uniform(8, 15)
                    from_work = self.rng.uniform(8, 15)
                    schedule[i, base + 9] = to_work
                    schedule[i, base + 17] = from_work
                    mandatory[i, base + 9] = to_work
                    mandatory[i, base + 17] = from_work
                    location_schedule[i, base + 10: base + 17] = 1

            n_discretionary = self.rng.poisson(3)
            for _ in range(n_discretionary):
                hour = self.rng.integers(0, self.config.episode_hours)
                schedule[i, hour] += self.rng.uniform(2, 8)
                location_schedule[i, hour] = 13

            if self.rng.random() < 0.25:
                weekend_start = 5 * 24 + self.rng.integers(0, 48)
                if weekend_start < self.config.episode_hours:
                    schedule[i, weekend_start] = self.rng.uniform(60, 300)
                    location_schedule[i, weekend_start:min(self.config.episode_hours, weekend_start + 4)] = 13

        scaled_schedule = self.config.trip_scale * schedule
        scaled_mandatory = self.config.trip_scale * mandatory
        return scaled_schedule, scaled_mandatory, location_schedule

    def _generate_caltech_schedule(self) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64], npt.NDArray[np.int_]]:
        """
        Caltech workplace-commuter scenario.

        Two calibration sources, in priority order:
          1) caltech_multisite_summary.json (preferred) — combined ACN-Data
             across Caltech main + JPL + Office001, proportionally weighted by
             session count (Office001 filtered to its valid 2019-03-25 to
             2019-10-31 range; charger power kept at L2 default).
          2) Hardcoded Caltech-only fallback (single-site, n=11,448 sessions).
        """
        schedule = np.zeros((self.n_cars, self.config.episode_hours))
        mandatory = np.zeros((self.n_cars, self.config.episode_hours))
        location_schedule = np.zeros((self.n_cars, self.config.episode_hours), dtype=int)

        import json as _json, os as _os
        _summary_map = {
            "nl_office": "nl_office_summary.json", "nl_office_uncertain": "nl_office_summary.json",
            "uk_home": "uk_home_summary.json", "uk_home_uncertain": "uk_home_summary.json",
        }
        _summary_file = _summary_map.get(self.config.scenario_name, "caltech_multisite_summary.json")
        _summary_path = _os.path.join(_os.path.dirname(__file__), _summary_file)
        if _os.path.exists(_summary_path):
            _s = _json.loads(open(_summary_path).read())
            plugin_hist = np.asarray(_s["hour_of_day_connection_hist"], dtype=float)
            dow_hist    = np.asarray(_s["dow_connection_hist"], dtype=float)
            kwh_mu, kwh_sigma = float(_s["kwh_lognormal_mu"]), float(_s["kwh_lognormal_sigma"])
            dur_mu, dur_sigma = float(_s["duration_lognormal_mu"]), float(_s["duration_lognormal_sigma"])
        else:
            plugin_hist = np.array([27, 8, 9, 3, 6, 39, 253, 527, 2226, 2094, 1366, 662,
                                    792, 746, 413, 326, 380, 364, 434, 291, 203, 162, 78, 39],
                                   dtype=float)
            dow_hist = np.array([1898, 2108, 2211, 2007, 1873, 727, 624], dtype=float)
            kwh_mu, kwh_sigma = 1.80, 0.85
            dur_mu, dur_sigma = 1.65, 0.60

        plugin_probs = plugin_hist / plugin_hist.sum()
        dow_probs = dow_hist / dow_hist.sum()

        n_days = int(np.ceil(self.config.episode_hours / 24))
        for i in range(self.n_cars):
            self.archetypes[i] = "caltech_commuter"
            for day in range(n_days):
                base = day * 24
                if base >= self.config.episode_hours:
                    break
                dow = day % 7
                if self.rng.random() > dow_probs[dow] * 7:
                    continue
                arrive_h = int(self.rng.choice(24, p=plugin_probs))
                duration_h = max(1, int(round(self.rng.lognormal(mean=dur_mu, sigma=dur_sigma))))
                duration_h = min(duration_h, 14)
                daily_kwh = float(np.clip(self.rng.lognormal(mean=kwh_mu, sigma=kwh_sigma), 1.0, 40.0))
                daily_km = daily_kwh / 0.18

                arrive_t = base + arrive_h
                raw_depart_t = arrive_t + duration_h
                dwell_end_t = min(raw_depart_t, self.config.episode_hours)
                if arrive_t < self.config.episode_hours:
                    schedule[i, arrive_t] = daily_km * 0.4
                    mandatory[i, arrive_t] = daily_km * 0.4
                    location_schedule[i, arrive_t:dwell_end_t] = 1
                if raw_depart_t < self.config.episode_hours:
                    schedule[i, raw_depart_t] = daily_km * 0.6
                    mandatory[i, raw_depart_t] = daily_km * 0.6

        scaled_schedule = self.config.trip_scale * schedule
        scaled_mandatory = self.config.trip_scale * mandatory
        return scaled_schedule, scaled_mandatory, location_schedule

    def _generate_timing_trap_schedule(self) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64], npt.NDArray[np.int_]]:
        schedule = np.zeros((self.n_cars, self.config.episode_hours))
        mandatory = np.zeros((self.n_cars, self.config.episode_hours))
        location_schedule = np.zeros((self.n_cars, self.config.episode_hours), dtype=int)

        for i in range(self.n_cars):
            self.archetypes[i] = "timing_trap_commuter"
            for day in range(7):
                base = day * 24
                if base + 20 >= self.config.episode_hours:
                    break
                if day < 5:
                    morning_depart_km = self.rng.uniform(95, 115)
                    evening_return_km = self.rng.uniform(120, 145)
                    schedule[i, base + 8] = morning_depart_km
                    schedule[i, base + 20] = evening_return_km
                    mandatory[i, base + 8] = morning_depart_km
                    mandatory[i, base + 20] = evening_return_km
                    location_schedule[i, base + 9: base + 20] = 1
                else:
                    if self.rng.random() < 0.35 and base + 14 < self.config.episode_hours:
                        errand_km = self.rng.uniform(10, 18)
                        schedule[i, base + 14] = errand_km
                        location_schedule[i, base + 14] = 13

        return schedule, mandatory, location_schedule

    def count_mandatory_trip_events(self, realized: bool = True) -> int:
        target = self.realized_mandatory_trip_schedule if realized else self.mandatory_trip_schedule
        if target is None:
            return 0
        return int((target > 0).sum())

    def _get_trip_energy(self, agent_idx: int, t: int) -> float:
        if self.realized_trip_schedule is None:
            return 0.0
        if t >= self.realized_trip_schedule.shape[1]:
            return 0.0
        km = self.realized_trip_schedule[agent_idx, t]
        return km * 0.18  # ~0.18 kWh/km

    def _is_discretionary_trip(self, agent_idx: int, t: int) -> bool:
        h = t % 24
        day = t // 24
        if day < 5 and h in [7, 8, 15, 18]:
            return False
        return True

    def _compute_anxiety_thresholds(self) -> npt.NDArray[np.float64]:
        base = self.anxiety_baseline
        lookahead_stress = np.zeros(self.n_cars)

        if self.trip_schedule is not None:
            end_h = min(self.t + 72, self.trip_schedule.shape[1])
            if end_h > self.t:
                upcoming_km = self.trip_schedule[:, self.t:end_h].sum(axis=1)
                lookahead_stress = 0.15 * (upcoming_km > 100).astype(float)

        return np.clip(base + lookahead_stress, 0.15, 0.50)

    def get_metrics(self) -> dict[str, float | int]:
        mandatory_trip_events = max(1, self.count_mandatory_trip_events(realized=True))
        return {
            "reliability_pct": 100.0 * (1.0 - self.failure_count / mandatory_trip_events),
            "avg_cost_krw": 0.0,  # computed externally from reward accumulation
            "failure_count": self.failure_count,
            "cancel_count": self.cancel_count,
            "mean_final_soc": self.soc.mean(),
            "herding_index": 0.0,  # computed from demand profile
        }
