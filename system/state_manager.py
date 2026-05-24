from dataclasses import dataclass
from typing import Optional


@dataclass
class SystemState:

    sensor_online: bool = False

    low_sensor_wet: bool = False
    high_sensor_wet: bool = False

    motor_on: bool = False

    current_mode: str = "idle"

    override_active: bool = False

    timer_end_timestamp: Optional[float] = None

    last_sensor_update: Optional[float] = None

    active_schedule_name: Optional[str] = None
    active_schedule_id: Optional[int] = None

    schedule_running: bool = False

    active_mode_display: str = "Idle"

    auto_mode_enabled: bool = False


state = SystemState()