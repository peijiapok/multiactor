"""
E12: Constrained-infrastructure env with FIFO queue dynamics per location-type.

Subclass of EVEnvironmentV2 that replaces the existing random-cull slot limit
with persistent FIFO queues (one per {home, work, public}).  Queue state carries
across timesteps; after joining, agents are released only when they are admitted,
physically leave that location type, or reach the fixed maximum queue wait.

Design rules (from E12 spec):
  - 3 type-keyed FIFO queues: {"home", "work", "public"}
  - Per-location-type capacity n_slots (count of chargers of that type)
  - No queue penalty in reward; failures cascade through existing SoC->trip-fail path
  - Queue release on admission, physical location change, or max_queue_wait_steps
  - Default max_queue_wait_steps = 24 one-hour steps
  - Optional target-SoC feasibility mask prevents non-reserve charging above
    target SoC; disabled by default for backwards compatibility

Observation is augmented with 2 per-agent dims (queue_length_norm, occupancy_rate)
for the agent's current location-type; use `flatten_agent_obs_queue` from
`obs_adapter.py` (STATE_DIM_QUEUE = 191).
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import numpy.typing as npt

from env_v2 import EVEnvironmentV2, EnvV2Config


DEFAULT_SLOTS = {"home": 9999, "work": 9999, "public": 9999}


@dataclass
class QueueEnvConfig(EnvV2Config):
    """EnvV2Config + per-type charger capacity and queue timeout.

    max_queue_wait_steps defaults to 24 one-hour steps. A queued vehicle that is
    not admitted after this many waiting steps abandons the queue via timeout.
    """
    n_slots_home: int = 9999
    n_slots_work: int = 9999
    n_slots_public: int = 9999
    max_queue_wait_steps: int = 24
    prevent_nonreserve_charging_above_target: bool = False
    target_soc: float = 0.90
    reserve_margin: float = 0.12
    queue_discipline: str = "fifo"


def _loc_type_of(loc: int, has_home: bool, has_work: bool, has_public: bool,
                 public_fallback: bool) -> Optional[str]:
    """Map raw location index to which queue the agent belongs at, if any.
    Matches the routing rules in EVEnvironmentV2._allocate_charge_modes."""
    if loc == 1 and has_work:
        return "work"
    if loc == 0 and has_home:
        return "home"
    if has_public and public_fallback:
        return "public"
    return None


class EVEnvironmentV2Queue(EVEnvironmentV2):
    """EV env with FIFO queues per location-type.

    State added on top of EVEnvironmentV2:
      self.charger_occupied[t]    : int per type
      self.charger_queues[t]      : deque[int] per type (agent ids, FIFO)
      self.agent_wait_time        : (N,) cumulative wait steps
      self.agent_queue_wait_age   : (N,) consecutive wait steps in current queue
      self.agent_queue_events     : (N,) count of distinct queue-joining events
      self.agent_queuing          : (N,) bool
      self.agent_queuing_at       : (N,) str or None
      self.max_queue_length_seen  : {type: int} monitoring
      self.util_sum, self.util_n  : running sums for mean charger_utilization
    """

    def __init__(self, config: Optional[QueueEnvConfig] = None, base_env=None):
        super().__init__(config or QueueEnvConfig(), base_env=base_env)
        self.n_slots = {
            "home": int(self.config.n_slots_home),
            "work": int(self.config.n_slots_work),
            "public": int(self.config.n_slots_public),
        }
        self.max_queue_wait_steps = max(1, int(self.config.max_queue_wait_steps))
        self.queue_discipline = str(getattr(self.config, "queue_discipline", "fifo"))
        if self.queue_discipline not in {"fifo", "least_laxity"}:
            raise ValueError(f"Unknown queue discipline: {self.queue_discipline}")
        self._init_queue_state()

    def _init_queue_state(self):
        self.charger_occupied = {t: 0 for t in ("home", "work", "public")}
        self.charger_queues = {t: deque() for t in ("home", "work", "public")}
        self.agent_wait_time = np.zeros(self.n_cars, dtype=np.int64)
        self.agent_queue_wait_age = np.zeros(self.n_cars, dtype=np.int64)
        self.agent_queue_events = np.zeros(self.n_cars, dtype=np.int64)
        self.agent_queuing = np.zeros(self.n_cars, dtype=bool)
        self.agent_queuing_at = np.full(self.n_cars, None, dtype=object)
        self.max_queue_length_seen = {t: 0 for t in ("home", "work", "public")}
        self.util_sum = {t: 0.0 for t in ("home", "work", "public")}
        self.util_n = 0
        # Per-timestep queue-length and admission-count history (Phase 1.1 logging)
        self.queue_length_history = {t: [] for t in ("home", "work", "public")}
        self.admitted_history = {t: [] for t in ("home", "work", "public")}
        self.attempts_history = []
        self.invalid_attempt_history = []
        self.joins_history = {t: [] for t in ("home", "work", "public")}
        # Proof-4 per-vehicle event counters
        self.charge_attempts = np.zeros(self.n_cars, dtype=np.int64)        # action <= 5 picked any step
        self.charge_successes = np.zeros(self.n_cars, dtype=np.int64)       # admitted to charger this step
        self.queue_abandonments_loc = np.zeros(self.n_cars, dtype=np.int64) # released by location change
        self.queue_abandonments_timeout = np.zeros(self.n_cars, dtype=np.int64) # released by max wait
        self.queue_abandonments_idle = np.zeros(self.n_cars, dtype=np.int64) # legacy compat; idle no longer releases
        self.denied_no_queue = np.zeros(self.n_cars, dtype=np.int64)         # charge at non-chargeable location

    def reset(self) -> dict[str, object]:
        obs = super().reset()
        self._init_queue_state()
        # Inject queue obs for t=0 (all zeros since nothing has happened yet)
        obs["queue_length_norm"] = np.zeros(self.n_cars, dtype=np.float32)
        obs["occupancy_rate"] = np.zeros(self.n_cars, dtype=np.float32)
        return obs

    def _charging_need_mask(self) -> npt.NDArray[np.bool_]:
        """Return whether each vehicle still has a defensible reason to charge.

        If the repair flag is off, every vehicle is treated as needing charge so
        legacy behavior is unchanged. With the flag on, a vehicle may request
        service only when below the target SoC or inside the reserve margin used
        by transparent baselines.
        """
        if not bool(self.config.prevent_nonreserve_charging_above_target):
            return np.ones(self.n_cars, dtype=bool)
        target_need = np.asarray(self.soc, dtype=float) < float(self.config.target_soc)
        reserve_need = np.asarray(self.soc, dtype=float) < (
            np.asarray(self.anxiety_thresholds, dtype=float) + float(self.config.reserve_margin)
        )
        return target_need | reserve_need

    def charge_available_mask(self) -> npt.NDArray[np.bool_]:
        return super().charge_available_mask() & self._charging_need_mask()

    def step(self, actions: npt.NDArray[np.int_]):
        """Execute one step with persistent service intent for queued vehicles.

        Joining the queue is controlled by the vehicle's charge action. After a
        vehicle has joined, FIFO service no longer depends on later idle/cancel
        actions while it remains at the same queued location type; admission
        therefore produces actual charging energy under the base environment.
        """
        raw_actions = np.asarray(actions)
        effective_actions = raw_actions.copy()
        raw_policy_actions_for_counts = raw_actions.copy()
        available = self.charge_available_mask()
        invalid_raw = (raw_policy_actions_for_counts <= 5) & ~available
        raw_policy_actions_for_counts[invalid_raw] = 6
        self.denied_no_queue += invalid_raw.astype(np.int64)
        self.invalid_attempt_history.append(int(invalid_raw.sum()))
        self._raw_policy_actions_for_queue = raw_policy_actions_for_counts.copy()
        for i in np.where(self.agent_queuing)[0]:
            t_q = self.agent_queuing_at[i]
            if t_q is None:
                continue
            t_now = _loc_type_of(int(self.locations[i]),
                                 bool(self.has_home_access[i]),
                                 bool(self.has_work_access[i]),
                                 bool(self.has_public_access[i]),
                                 bool(self.public_fallback[i]))
            if t_now == t_q and bool(available[i]):
                effective_actions[i] = 0
        obs, rewards, done, info = super().step(effective_actions)
        info["effective_actions"] = effective_actions.copy()
        info["raw_policy_actions"] = raw_actions.copy()
        return obs, rewards, done, info

    def _release_from_queue(self, agent_id: int):
        """Remove agent from its current queue (no-op if not queuing)."""
        t = self.agent_queuing_at[agent_id]
        if t is None:
            return
        q = self.charger_queues[t]
        try:
            q.remove(agent_id)
        except ValueError:
            pass
        self.agent_queuing[agent_id] = False
        self.agent_queuing_at[agent_id] = None
        self.agent_queue_wait_age[agent_id] = 0

    def _allocate_charge_modes(self, actions: npt.NDArray[np.int_]) -> npt.NDArray[np.ndarray]:
        """FIFO queue replacement for EVEnvironmentV2._allocate_charge_modes.

        Protocol per step:
          (1) release anyone whose location changed from their queue's location
          (2) for each requester (action <= 5) at a chargeable location:
                if not queuing here, append to this location's queue
                (duplicates are prevented by the queuing flag)
          (3) for each location-type: admit up to (capacity - currently_occupied)
              from the front of the queue, mark them as granted this step
          (4) increment wait_time for everyone still queuing this step
          (5) release queued agents whose current wait age reaches max_queue_wait_steps
          (6) clear admitted agents from queues; chargers are free for next step

        Already-queued vehicles stay in FIFO order even if their controller
        chooses idle on later steps. EVEnvironmentV2Queue.step converts those
        later queued actions into persistent charge requests while the vehicle
        remains at the same location type, so FIFO admission produces actual
        delivered charging energy.
        """
        modes = np.array(["none"] * self.n_cars, dtype=object)
        actions = np.asarray(actions)
        requested = actions <= 5
        raw_actions = getattr(self, "_raw_policy_actions_for_queue", actions)
        raw_requested = np.asarray(raw_actions) <= 5
        # Proof-4: count policy charge intent, not forced FIFO persistence.
        self.charge_attempts[raw_requested] += 1
        self.attempts_history.append(int(raw_requested.sum()))

        current_available = self.charge_available_mask()

        # (1) location-change releases (counts as queue abandonment)
        for i in range(self.n_cars):
            t_q = self.agent_queuing_at[i]
            if t_q is None:
                continue
            t_now = _loc_type_of(int(self.locations[i]),
                                 bool(self.has_home_access[i]),
                                 bool(self.has_work_access[i]),
                                 bool(self.has_public_access[i]),
                                 bool(self.public_fallback[i]))
            if t_now != t_q:
                self.queue_abandonments_loc[i] += 1
                self._release_from_queue(i)

        # (1b) optional target-SoC release. A vehicle that no longer needs
        # charge should not stay in FIFO only because it queued earlier.
        if bool(self.config.prevent_nonreserve_charging_above_target):
            for i in np.where(self.agent_queuing & ~current_available)[0]:
                self._release_from_queue(int(i))

        # (2) join queues (or denial if non-chargeable location)
        joins_this_step = {t: 0 for t in ("home", "work", "public")}
        for i in np.where(requested)[0]:
            t = _loc_type_of(int(self.locations[i]),
                             bool(self.has_home_access[i]),
                             bool(self.has_work_access[i]),
                             bool(self.has_public_access[i]),
                             bool(self.public_fallback[i]))
            if t is None:
                raise AssertionError("invalid charge request should be masked before queue allocation")
            if not self.agent_queuing[i]:
                self.charger_queues[t].append(int(i))
                self.agent_queuing[i] = True
                self.agent_queuing_at[i] = t
                self.agent_queue_events[i] += 1
                joins_this_step[t] += 1

        # Optional priority admission over a persistent intent set. Vehicles
        # remain in the expressed queue and accrue waiting time; only the
        # admission order changes from FIFO to least-laxity-first.
        if self.queue_discipline == "least_laxity":
            for t in ("home", "work", "public"):
                self.charger_queues[t] = deque(
                    sorted(self.charger_queues[t], key=self._least_laxity_key)
                )

        # (3) admit up to capacity. Admission is per-step: admitted agents get
        # a slot for this step and are popped from the queue at end of step.
        # Agents still in the queue after admission accrue one step of wait.
        self.charger_occupied = {t: 0 for t in ("home", "work", "public")}
        admitted_mask = np.zeros(self.n_cars, dtype=bool)
        for t in ("home", "work", "public"):
            capacity = int(self.n_slots[t])
            q = self.charger_queues[t]
            n_admit = min(capacity, len(q))
            for idx_in_q in range(n_admit):
                a_id = q[idx_in_q]
                modes[a_id] = t
                admitted_mask[a_id] = True
                self.charge_successes[a_id] += 1  # Proof-4: admitted = success
            self.charger_occupied[t] = n_admit
            self.util_sum[t] += n_admit / max(capacity, 1)
            self.max_queue_length_seen[t] = max(self.max_queue_length_seen[t], len(q))
            self.queue_length_history[t].append(int(len(q)))
            self.admitted_history[t].append(int(n_admit))
            self.joins_history[t].append(int(joins_this_step[t]))
        self.util_n += 1

        # (4) wait_time: queuing at end-of-step *without* admission counts as 1 waited step.
        still_waiting = self.agent_queuing & ~admitted_mask
        self.agent_wait_time[still_waiting] += 1
        self.agent_queue_wait_age[still_waiting] += 1

        # (5) timeout releases: counted separately from physical location exits.
        timed_out = np.where(still_waiting & (self.agent_queue_wait_age >= self.max_queue_wait_steps))[0]
        for i in timed_out:
            self.queue_abandonments_timeout[i] += 1
            self._release_from_queue(int(i))

        # (6) pop admitted agents from their queue so next step they re-queue at the back
        for t in ("home", "work", "public"):
            q = self.charger_queues[t]
            n_admit = self.charger_occupied[t]
            for _ in range(n_admit):
                a_id = q.popleft()
                self.agent_queuing[a_id] = False
                self.agent_queuing_at[a_id] = None
                self.agent_queue_wait_age[a_id] = 0

        return modes

    def _least_laxity_key(self, agent_id: int) -> tuple[float, int]:
        """Priority key for least-laxity-first admission among queued vehicles.

        Lower laxity is higher priority. The second tuple element keeps ordering
        deterministic when two vehicles have equal scores.
        """
        i = int(agent_id)
        planned = getattr(self, "mandatory_trip_schedule", None)
        if planned is None or self.t >= int(self.config.episode_hours):
            return (0.0, i)

        future = np.asarray(planned[i, self.t:int(self.config.episode_hours)], dtype=float)
        nz = np.flatnonzero(future > 0.0)
        if nz.size == 0:
            return (1.0e6 + max(0.0, float(self.config.target_soc) - float(self.soc[i])), i)

        hours_to_deadline = float(nz[0])
        trip_kwh = float(future[nz[0]]) * 0.18
        usable_kwh = max(0.0, float(self.soc[i]) - float(self.config.soc_min)) * float(self.config.bcap_kwh)
        deficit_kwh = max(0.0, trip_kwh - usable_kwh)
        loc_type = _loc_type_of(
            int(self.locations[i]),
            bool(self.has_home_access[i]),
            bool(self.has_work_access[i]),
            bool(self.has_public_access[i]),
            bool(self.public_fallback[i]),
        )
        if loc_type is None:
            return (np.inf, i)
        stored_kwh_per_hour = max(
            float(self._get_charge_power(loc_type)) * float(self._get_efficiency(loc_type)),
            1.0e-9,
        )
        charge_hours_needed = deficit_kwh / stored_kwh_per_hour
        return (hours_to_deadline - charge_hours_needed, i)

    # obs extension: append queue_length_norm and occupancy_rate per agent
    def _get_obs(self) -> dict[str, object]:
        obs = super()._get_obs()
        ql = np.zeros(self.n_cars, dtype=np.float32)
        occ = np.zeros(self.n_cars, dtype=np.float32)
        q_len = {t: len(self.charger_queues[t]) for t in ("home", "work", "public")}
        for i in range(self.n_cars):
            t = _loc_type_of(int(self.locations[i]),
                             bool(self.has_home_access[i]),
                             bool(self.has_work_access[i]),
                             bool(self.has_public_access[i]),
                             bool(self.public_fallback[i]))
            if t is None:
                continue
            cap = max(int(self.n_slots[t]), 1)
            ql[i] = q_len[t] / cap
            occ[i] = self.charger_occupied[t] / cap
        obs["queue_length_norm"] = ql
        obs["occupancy_rate"] = occ
        return obs

    def mean_charger_utilization(self) -> dict[str, float]:
        n = max(self.util_n, 1)
        return {t: float(self.util_sum[t] / n) for t in ("home", "work", "public")}
