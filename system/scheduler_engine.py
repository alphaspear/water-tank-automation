import asyncio
import time

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from schedule_manager import get_schedules

from motor_controller import (
    turn_motor_on,
    turn_motor_off
)

from state_manager import state

from event_logger import log_event

scheduler = AsyncIOScheduler()

# =====================================================
# LOAD SCHEDULES
# =====================================================

def load_schedules():

    scheduler.remove_all_jobs()

    schedules = get_schedules()

    for sched in schedules:

        start_time = str(sched["start_time"])

        hour, minute = start_time.split(":")[:2]

        scheduler.add_job(
            execute_schedule,
            CronTrigger(
                hour=int(hour),
                minute=int(minute)
            ),
            args=[sched],
            id=str(sched["id"])
        )

        print(f"Loaded schedule: {sched['name']}")

# =====================================================
# EXECUTE SCHEDULE
# =====================================================

async def execute_schedule(schedule):

    if state.current_mode != "idle":

        print("Another mode already active")

        return

    state.schedule_running = True
    state.active_schedule_name = schedule["name"]
    state.active_schedule_id = schedule["id"]

    log_event(
        "SCHEDULE_START",
        f"Schedule started: {schedule['name']}"
    )

    # =================================================
    # TIMER MODE
    # =================================================

    if schedule["schedule_type"] == "timer":

        state.current_mode = "scheduled_timer"
        state.active_mode_display = "Scheduled Timer Fill"

        success = await turn_motor_on()

        if not success:
            return

        state.motor_on = True

        duration = schedule["duration_seconds"]

        await asyncio.sleep(duration)

        await turn_motor_off()

        state.motor_on = False

    # =================================================
    # SENSOR MODE
    # =================================================

    elif schedule["schedule_type"] == "sensor":

        state.current_mode = "scheduled_sensor"
        state.active_mode_display = "Scheduled Sensor Fill"

        success = await turn_motor_on()

        if not success:
            return

        state.motor_on = True

        start_time = time.time()

        fallback_timeout = (
            schedule["duration_seconds"] or 900
        )

        while True:

            if state.high_sensor_wet:

                print("Tank full reached")

                break

            if not state.sensor_online:

                print("Sensor offline fallback stop")

                break

            elapsed = time.time() - start_time

            if elapsed >= fallback_timeout:

                print("Fallback timeout reached")

                break

            await asyncio.sleep(2)

        await turn_motor_off()

        state.motor_on = False

    # =================================================
    # RESET
    # =================================================

    state.current_mode = "idle"
    state.active_mode_display = "Idle"

    state.schedule_running = False
    state.active_schedule_name = None
    state.active_schedule_id = None

    log_event(
        "SCHEDULE_STOP",
        f"Schedule completed: {schedule['name']}"
    )