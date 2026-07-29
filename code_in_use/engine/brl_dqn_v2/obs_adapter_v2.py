from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


SOURCE_ROOT = Path("/home/jia/thirftydeath")
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from obs_adapter import STATE_DIM_QUEUE, flatten_agent_obs_queue  # noqa: E402


EXTRA_FEATURES = [
    "global_occupancy_rate",
    "local_wait_estimate_norm",
    "soc_margin_to_anxiety",
    "next_mandatory_trip_kwh_norm",
    "time_to_next_mandatory_norm",
    "energy_shortfall_norm",
    "target_energy_deficit_norm",
    "deadline_energy_deficit_norm",
    "required_charge_hours_norm",
    "deadline_laxity_hours_norm",
    "charge_power_available_norm",
    "service_request_priority_norm",
]
STATE_DIM_V2 = STATE_DIM_QUEUE + len(EXTRA_FEATURES)


def flatten_agent_obs_v2(obs: dict[str, object], agent_idx: int) -> np.ndarray:
    base = flatten_agent_obs_queue(obs, agent_idx)
    extras = []
    for name in EXTRA_FEATURES:
        default = np.zeros(len(np.asarray(obs["soc"])), dtype=np.float32)
        values = np.asarray(obs.get(name, default), dtype=np.float32)
        extras.append(float(values[agent_idx]))
    return np.concatenate([base, np.asarray(extras, dtype=np.float32)]).astype(np.float32)


def batch_flatten_obs_v2(obs: dict[str, object], n_agents: int) -> np.ndarray:
    return np.stack([flatten_agent_obs_v2(obs, i) for i in range(n_agents)], axis=0)


def batch_action_mask(obs: dict[str, object], n_agents: int) -> np.ndarray:
    mask = np.asarray(obs.get("primitive_action_mask"), dtype=bool)
    if mask.shape != (n_agents, 4):
        return np.ones((n_agents, 4), dtype=bool)
    return mask
