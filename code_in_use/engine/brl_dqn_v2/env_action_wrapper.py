from __future__ import annotations

import sys
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import numpy.typing as npt


SOURCE_ROOT = Path("/home/jia/thirftydeath")
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from e12_queue_env import EVEnvironmentV2Queue, QueueEnvConfig, _loc_type_of  # noqa: E402


PRIMITIVE_IDLE = 0
PRIMITIVE_FLEXIBLE_REQUEST = 1
PRIMITIVE_NORMAL_REQUEST = 2
PRIMITIVE_URGENT_REQUEST = 3
N_PRIMITIVE_ACTIONS = 4

# Historical aliases retained for old imports. Current semantics are service
# priority requests, not delay locks.
PRIMITIVE_CHARGE_NOW = PRIMITIVE_NORMAL_REQUEST
PRIMITIVE_DEFER_1H = PRIMITIVE_FLEXIBLE_REQUEST
PRIMITIVE_DEFER_2H = PRIMITIVE_URGENT_REQUEST

REQUEST_PRIORITIES = {
    PRIMITIVE_IDLE: 0,
    PRIMITIVE_FLEXIBLE_REQUEST: 1,
    PRIMITIVE_NORMAL_REQUEST: 2,
    PRIMITIVE_URGENT_REQUEST: 3,
}


@dataclass
class PrimitiveActionInfo:
    invalid_request_count: int
    invalid_urgent_count: int
    request_count: int


class BRLDQNPrimitiveEnv(EVEnvironmentV2Queue):
    """Queue env with a real 4-action policy interface.

    The wrapped source environment still receives its native action codes:
    service request is `0`, idle is `6`. This class exposes:

    - 0: idle/no request
    - 1: flexible low-priority service request
    - 2: normal service request
    - 3: urgent high-priority service request

    Priority affects queue ordering only. Under no contention, all non-idle
    requests admit identically and can receive charging in the same timestep.
    """

    def __init__(self, config: QueueEnvConfig | None = None, base_env=None):
        super().__init__(config=config, base_env=base_env)
        self.last_primitive_actions = np.zeros(self.n_cars, dtype=np.int64)
        self.last_action_mask = np.ones((self.n_cars, N_PRIMITIVE_ACTIONS), dtype=bool)
        self.last_request_priority = np.zeros(self.n_cars, dtype=np.int64)

    def _init_queue_state(self):
        super()._init_queue_state()
        self.agent_queue_priority = np.zeros(self.n_cars, dtype=np.int64)

    def reset(self) -> dict[str, object]:
        obs = super().reset()
        self.last_primitive_actions = np.zeros(self.n_cars, dtype=np.int64)
        self.last_action_mask = self.action_mask()
        self.last_request_priority = np.zeros(self.n_cars, dtype=np.int64)
        self.agent_queue_priority = np.zeros(self.n_cars, dtype=np.int64)
        return self._augment_obs(obs)

    def _augment_obs(self, obs: dict[str, object]) -> dict[str, object]:
        obs = dict(obs)
        current = self._current_queue_features()
        urgency = self._urgency_features()
        obs.update(current)
        obs.update(urgency)
        obs["service_request_priority_norm"] = (self.agent_queue_priority / 3.0).astype(np.float32)
        obs["defer_remaining_norm"] = obs["service_request_priority_norm"]
        obs["primitive_action_mask"] = self.action_mask()
        return obs

    def _current_queue_features(self) -> dict[str, object]:
        local_wait = np.zeros(self.n_cars, dtype=np.float32)
        global_capacity = max(1, sum(int(v) for v in self.n_slots.values()))
        global_occupied = sum(int(v) for v in self.charger_occupied.values())
        global_occ = np.full(self.n_cars, global_occupied / global_capacity, dtype=np.float32)
        for i in range(self.n_cars):
            loc_type = _loc_type_of(
                int(self.locations[i]),
                bool(self.has_home_access[i]),
                bool(self.has_work_access[i]),
                bool(self.has_public_access[i]),
                bool(self.public_fallback[i]),
            )
            if loc_type is None:
                continue
            cap = max(1, int(self.n_slots[loc_type]))
            local_wait[i] = min(1.0, len(self.charger_queues[loc_type]) / cap / max(1, self.max_queue_wait_steps))
        return {
            "global_occupancy_rate": global_occ,
            "local_wait_estimate_norm": local_wait,
        }

    def _next_mandatory(self, agent_idx: int) -> tuple[int, float]:
        if self.mandatory_trip_schedule is None:
            return self.config.episode_hours + 1, 0.0
        horizon = self.mandatory_trip_schedule.shape[1]
        start = min(max(self.t, 0), horizon)
        row = np.asarray(self.mandatory_trip_schedule[agent_idx, start:horizon], dtype=float)
        hits = np.flatnonzero(row > 0.0)
        if hits.size == 0:
            return self.config.episode_hours + 1, 0.0
        delta = int(hits[0])
        km = float(row[delta])
        return delta, km * 0.18

    def _agent_charge_power_kw(self, agent_idx: int) -> float:
        loc_type = _loc_type_of(
            int(self.locations[agent_idx]),
            bool(self.has_home_access[agent_idx]),
            bool(self.has_work_access[agent_idx]),
            bool(self.has_public_access[agent_idx]),
            bool(self.public_fallback[agent_idx]),
        )
        if loc_type is not None:
            return float(self._get_charge_power(loc_type))
        candidates: list[str] = []
        if bool(self.has_home_access[agent_idx]):
            candidates.append("home")
        if bool(self.has_work_access[agent_idx]):
            candidates.append("work")
        if bool(self.has_public_access[agent_idx]):
            candidates.append("public")
        if not candidates:
            candidates = ["home", "work", "public"]
        return max(float(self._get_charge_power(t)) for t in candidates)

    def _urgency_features(self) -> dict[str, object]:
        soc_margin = np.asarray(self.soc - self.anxiety_thresholds, dtype=np.float32)
        next_kwh = np.zeros(self.n_cars, dtype=np.float32)
        next_time = np.ones(self.n_cars, dtype=np.float32)
        shortfall = np.zeros(self.n_cars, dtype=np.float32)
        target_deficit = np.maximum(0.0, float(self.config.target_soc) - np.asarray(self.soc, dtype=float)).astype(np.float32)
        deadline_deficit = np.zeros(self.n_cars, dtype=np.float32)
        required_hours = np.zeros(self.n_cars, dtype=np.float32)
        laxity_hours = np.ones(self.n_cars, dtype=np.float32)
        charge_power_norm = np.zeros(self.n_cars, dtype=np.float32)
        max_power = max(float(self._get_charge_power(t)) for t in ("home", "work", "public"))
        for i in range(self.n_cars):
            delta_h, kwh = self._next_mandatory(i)
            next_kwh[i] = min(1.0, kwh / max(1.0, self.config.bcap_kwh))
            next_time[i] = min(1.0, delta_h / 168.0)
            needed_soc = kwh / max(1.0, self.config.bcap_kwh)
            shortfall[i] = max(0.0, needed_soc - float(self.soc[i]))
            deadline_deficit_kwh = max(0.0, kwh - float(self.soc[i]) * float(self.config.bcap_kwh))
            deadline_deficit[i] = min(1.0, deadline_deficit_kwh / max(1.0, self.config.bcap_kwh))
            power_kw = max(1.0e-9, self._agent_charge_power_kw(i))
            required_h = deadline_deficit_kwh / power_kw
            required_hours[i] = min(1.0, required_h / 24.0)
            laxity_hours[i] = float(np.clip((delta_h - required_h) / 24.0, -1.0, 1.0))
            charge_power_norm[i] = min(1.0, power_kw / max(max_power, 1.0e-9))
        return {
            "soc_margin_to_anxiety": soc_margin,
            "next_mandatory_trip_kwh_norm": next_kwh,
            "time_to_next_mandatory_norm": next_time,
            "energy_shortfall_norm": shortfall.astype(np.float32),
            "target_energy_deficit_norm": target_deficit.astype(np.float32),
            "deadline_energy_deficit_norm": deadline_deficit.astype(np.float32),
            "required_charge_hours_norm": required_hours.astype(np.float32),
            "deadline_laxity_hours_norm": laxity_hours.astype(np.float32),
            "charge_power_available_norm": charge_power_norm.astype(np.float32),
        }

    def _urgent_request_mask(self) -> npt.NDArray[np.bool_]:
        urgent = np.asarray(self.soc <= (self.anxiety_thresholds + 0.05), dtype=bool)
        for i in range(self.n_cars):
            delta_h, kwh = self._next_mandatory(i)
            needed_soc = kwh / max(1.0, self.config.bcap_kwh)
            shortfall = needed_soc > float(self.soc[i])
            near_trip = delta_h <= 24
            urgent[i] = urgent[i] or shortfall or near_trip
        return urgent

    def action_mask(self) -> npt.NDArray[np.bool_]:
        mask = np.ones((self.n_cars, N_PRIMITIVE_ACTIONS), dtype=bool)
        charge_available = self.charge_available_mask()
        urgent = self._urgent_request_mask()
        mask[:, PRIMITIVE_FLEXIBLE_REQUEST] = charge_available
        mask[:, PRIMITIVE_NORMAL_REQUEST] = charge_available
        mask[:, PRIMITIVE_URGENT_REQUEST] = charge_available & urgent
        return mask

    def primitive_to_env_actions(self, primitive_actions: npt.ArrayLike) -> tuple[npt.NDArray[np.int_], PrimitiveActionInfo]:
        primitive = np.asarray(primitive_actions, dtype=int).copy()
        if primitive.shape != (self.n_cars,):
            raise ValueError(f"expected primitive action shape {(self.n_cars,)}, got {primitive.shape}")
        primitive = np.clip(primitive, 0, N_PRIMITIVE_ACTIONS - 1)
        mask = self.action_mask()
        invalid_request = (primitive != PRIMITIVE_IDLE) & ~mask[np.arange(self.n_cars), primitive]
        invalid_urgent = (primitive == PRIMITIVE_URGENT_REQUEST) & ~mask[:, PRIMITIVE_URGENT_REQUEST]
        primitive[invalid_request] = PRIMITIVE_IDLE

        request_mask = primitive != PRIMITIVE_IDLE
        env_actions = np.full(self.n_cars, 6, dtype=int)
        env_actions[request_mask] = 0
        priority = np.asarray([REQUEST_PRIORITIES[int(a)] for a in primitive], dtype=np.int64)
        info = PrimitiveActionInfo(
            invalid_request_count=int(invalid_request.sum()),
            invalid_urgent_count=int(invalid_urgent.sum()),
            request_count=int(request_mask.sum()),
        )
        self.last_primitive_actions = primitive.copy()
        self.last_action_mask = mask.copy()
        self.last_request_priority = priority.copy()
        return env_actions, info

    def _sort_queue_by_priority(self, loc_type: str) -> None:
        q = list(self.charger_queues[loc_type])
        q.sort(key=lambda agent_id: -int(self.agent_queue_priority[int(agent_id)]))
        self.charger_queues[loc_type] = deque(q)

    def _allocate_charge_modes(self, actions: npt.NDArray[np.int_]) -> npt.NDArray[np.ndarray]:
        modes = np.array(["none"] * self.n_cars, dtype=object)
        actions = np.asarray(actions)
        requested = actions <= 5
        raw_actions = getattr(self, "_raw_policy_actions_for_queue", actions)
        raw_requested = np.asarray(raw_actions) <= 5
        self.charge_attempts[raw_requested] += 1
        self.attempts_history.append(int(raw_requested.sum()))

        current_available = self.charge_available_mask()

        for i in range(self.n_cars):
            t_q = self.agent_queuing_at[i]
            if t_q is None:
                continue
            t_now = _loc_type_of(
                int(self.locations[i]),
                bool(self.has_home_access[i]),
                bool(self.has_work_access[i]),
                bool(self.has_public_access[i]),
                bool(self.public_fallback[i]),
            )
            if t_now != t_q:
                self.queue_abandonments_loc[i] += 1
                self.agent_queue_priority[i] = 0
                self._release_from_queue(i)

        if bool(self.config.prevent_nonreserve_charging_above_target):
            for i in np.where(self.agent_queuing & ~current_available)[0]:
                self.agent_queue_priority[int(i)] = 0
                self._release_from_queue(int(i))

        joins_this_step = {t: 0 for t in ("home", "work", "public")}
        for i in np.where(requested)[0]:
            t = _loc_type_of(
                int(self.locations[i]),
                bool(self.has_home_access[i]),
                bool(self.has_work_access[i]),
                bool(self.has_public_access[i]),
                bool(self.public_fallback[i]),
            )
            if t is None:
                raise AssertionError("invalid charge request should be masked before queue allocation")
            req_priority = int(self.last_request_priority[i])
            if not self.agent_queuing[i]:
                self.charger_queues[t].append(int(i))
                self.agent_queuing[i] = True
                self.agent_queuing_at[i] = t
                self.agent_queue_priority[i] = req_priority
                self.agent_queue_events[i] += 1
                joins_this_step[t] += 1
            else:
                self.agent_queue_priority[i] = max(int(self.agent_queue_priority[i]), req_priority)

        self.charger_occupied = {t: 0 for t in ("home", "work", "public")}
        admitted_mask = np.zeros(self.n_cars, dtype=bool)
        for t in ("home", "work", "public"):
            self._sort_queue_by_priority(t)
            capacity = int(self.n_slots[t])
            q = self.charger_queues[t]
            n_admit = min(capacity, len(q))
            for idx_in_q in range(n_admit):
                a_id = q[idx_in_q]
                modes[a_id] = t
                admitted_mask[a_id] = True
                self.charge_successes[a_id] += 1
            self.charger_occupied[t] = n_admit
            self.util_sum[t] += n_admit / max(capacity, 1)
            self.max_queue_length_seen[t] = max(self.max_queue_length_seen[t], len(q))
            self.queue_length_history[t].append(int(len(q)))
            self.admitted_history[t].append(int(n_admit))
            self.joins_history[t].append(int(joins_this_step[t]))
        self.util_n += 1

        still_waiting = self.agent_queuing & ~admitted_mask
        self.agent_wait_time[still_waiting] += 1
        self.agent_queue_wait_age[still_waiting] += 1

        timed_out = np.where(still_waiting & (self.agent_queue_wait_age >= self.max_queue_wait_steps))[0]
        for i in timed_out:
            self.queue_abandonments_timeout[i] += 1
            self.agent_queue_priority[int(i)] = 0
            self._release_from_queue(int(i))

        for t in ("home", "work", "public"):
            q = self.charger_queues[t]
            n_admit = self.charger_occupied[t]
            for _ in range(n_admit):
                a_id = q.popleft()
                self.agent_queuing[a_id] = False
                self.agent_queuing_at[a_id] = None
                self.agent_queue_wait_age[a_id] = 0
                self.agent_queue_priority[a_id] = 0

        return modes

    def step(self, primitive_actions: npt.ArrayLike):
        pre_t = int(self.t)
        pre_step_soc = self.soc.copy()
        pre_step_urgency = self._urgency_features()
        if self.realized_mandatory_trip_schedule is not None and pre_t < self.realized_mandatory_trip_schedule.shape[1]:
            pre_step_trip_event = np.asarray(self.realized_mandatory_trip_schedule[:, pre_t] > 0.0, dtype=bool)
        else:
            pre_step_trip_event = np.zeros(self.n_cars, dtype=bool)
        env_actions, primitive_info = self.primitive_to_env_actions(primitive_actions)
        obs, rewards, done, info = super().step(env_actions)
        info = dict(info)
        info["pre_step_soc"] = pre_step_soc
        info["pre_step_energy_shortfall_norm"] = np.asarray(
            pre_step_urgency.get("energy_shortfall_norm", np.zeros(self.n_cars)),
            dtype=np.float32,
        )
        info["pre_step_target_energy_deficit_norm"] = np.asarray(
            pre_step_urgency.get("target_energy_deficit_norm", np.zeros(self.n_cars)),
            dtype=np.float32,
        )
        info["pre_step_deadline_energy_deficit_norm"] = np.asarray(
            pre_step_urgency.get("deadline_energy_deficit_norm", np.zeros(self.n_cars)),
            dtype=np.float32,
        )
        info["pre_step_required_charge_hours_norm"] = np.asarray(
            pre_step_urgency.get("required_charge_hours_norm", np.zeros(self.n_cars)),
            dtype=np.float32,
        )
        info["pre_step_deadline_laxity_hours_norm"] = np.asarray(
            pre_step_urgency.get("deadline_laxity_hours_norm", np.ones(self.n_cars)),
            dtype=np.float32,
        )
        info["pre_step_mandatory_trip_event"] = pre_step_trip_event
        info["primitive_actions"] = self.last_primitive_actions.copy()
        info["primitive_action_mask"] = self.last_action_mask.copy()
        info["primitive_request_priority"] = self.last_request_priority.copy()
        info["primitive_invalid_request_count"] = primitive_info.invalid_request_count
        info["primitive_invalid_urgent_count"] = primitive_info.invalid_urgent_count
        info["primitive_request_count"] = primitive_info.request_count
        info["primitive_invalid_charge_count"] = primitive_info.invalid_request_count
        info["primitive_invalid_defer_count"] = primitive_info.invalid_urgent_count
        info["primitive_forced_defer_idle_count"] = 0
        return self._augment_obs(obs), rewards, done, info
