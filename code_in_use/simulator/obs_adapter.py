from __future__ import annotations

import numpy as np


LOCATION_DIM = 14
TIME_DIM = 2
FORECAST_DIM = 168
CHARGE_AVAILABLE_INDEX = 3 + LOCATION_DIM + TIME_DIM + FORECAST_DIM
SOLAR_INDEX = CHARGE_AVAILABLE_INDEX + 1
STATE_DIM = 1 + 1 + 1 + LOCATION_DIM + TIME_DIM + FORECAST_DIM + 1 + 1


def _normalize_price(price: float) -> float:
    return float(price) / 500.0


def _time_encoding(time_of_week: int) -> tuple[float, float]:
    angle = 2.0 * np.pi * (time_of_week % 168) / 168.0
    return float(np.sin(angle)), float(np.cos(angle))


def flatten_agent_obs(obs: dict[str, object], agent_idx: int) -> np.ndarray:
    vec = np.zeros(STATE_DIM, dtype=np.float32)
    vec[0] = float(np.asarray(obs["soc"])[agent_idx])
    vec[1] = _normalize_price(float(obs["price"]))
    vec[2] = float(np.asarray(obs["anxiety_thresholds"])[agent_idx])

    loc = int(np.asarray(obs["locations"])[agent_idx])
    if 0 <= loc < LOCATION_DIM:
        vec[3 + loc] = 1.0

    sin_t, cos_t = _time_encoding(int(obs["time_of_week"]))
    vec[3 + LOCATION_DIM] = sin_t
    vec[3 + LOCATION_DIM + 1] = cos_t

    future = np.asarray(obs["future_demand"], dtype=np.float32)
    if future.shape[0] < FORECAST_DIM:
        padded = np.zeros(FORECAST_DIM, dtype=np.float32)
        padded[: future.shape[0]] = future
        future = padded
    else:
        future = future[:FORECAST_DIM]
    vec[3 + LOCATION_DIM + TIME_DIM:3 + LOCATION_DIM + TIME_DIM + FORECAST_DIM] = future / 300.0

    if "charge_available" in obs:
        vec[CHARGE_AVAILABLE_INDEX] = float(np.asarray(obs["charge_available"], dtype=np.float32)[agent_idx])
    else:
        vec[CHARGE_AVAILABLE_INDEX] = 1.0
    vec[SOLAR_INDEX] = float(obs["solar_index"])
    return vec


def batch_flatten_obs(obs: dict[str, object], n_agents: int) -> np.ndarray:
    return np.stack([flatten_agent_obs(obs, i) for i in range(n_agents)], axis=0)


# ---- E12: queue-aware obs ----
STATE_DIM_QUEUE = STATE_DIM + 2


def flatten_agent_obs_queue(obs: dict[str, object], agent_idx: int) -> np.ndarray:
    base = flatten_agent_obs(obs, agent_idx)
    ql = float(np.asarray(obs.get("queue_length_norm", np.zeros(1)))[agent_idx]) if "queue_length_norm" in obs else 0.0
    oc = float(np.asarray(obs.get("occupancy_rate",     np.zeros(1)))[agent_idx]) if "occupancy_rate"     in obs else 0.0
    return np.concatenate([base, np.asarray([ql, oc], dtype=np.float32)]).astype(np.float32)


def batch_flatten_obs_queue(obs: dict[str, object], n_agents: int) -> np.ndarray:
    base = batch_flatten_obs(obs, n_agents)  # (N, STATE_DIM)
    ql = np.asarray(obs.get("queue_length_norm", np.zeros(n_agents)), dtype=np.float32).reshape(n_agents, 1)
    oc = np.asarray(obs.get("occupancy_rate",     np.zeros(n_agents)), dtype=np.float32).reshape(n_agents, 1)
    return np.concatenate([base, ql, oc], axis=1).astype(np.float32)
