import asyncio
import time
import yaml

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
from fastapi import Form

from event_logger import (
    log_event,
    get_recent_events,
)

from mqtt_handler import mqtt_thread

from state_manager import state

from motor_controller import (
    turn_motor_on,
    turn_motor_off,
    get_motor_state,
)

from schedule_manager import (
    get_schedules,
    create_schedule,
    delete_schedule,
)

from scheduler_engine import (
    scheduler,
    load_schedules,
)

from database import initialize_database

# =====================================================
# LOAD CONFIG
# =====================================================

with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

# =====================================================
# FASTAPI
# =====================================================

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# =====================================================
# STARTUP
# =====================================================

@app.on_event("startup")
async def startup_event():

    initialize_database()

    mqtt_thread.start()

    scheduler.start()

    load_schedules()

    asyncio.create_task(sensor_health_monitor())
    asyncio.create_task(automation_loop())

    log_event(
        "SYSTEM_START",
        "Water tank automation system started"
    )

# =====================================================
# SENSOR HEALTH
# =====================================================

async def sensor_health_monitor():

    while True:

        if state.last_sensor_update:

            diff = (
                time.time()
                - state.last_sensor_update
            )

            if diff > config["system"]["sensor_timeout_seconds"]:

                state.sensor_online = False

        await asyncio.sleep(5)

# =====================================================
# AUTOMATION LOOP
# =====================================================

async def automation_loop():

    while True:
        # =============================================
        # FILL UNTIL FULL
        #=============================================
        if state.current_mode == "fill_until_full":

            # START MOTOR

            if not state.motor_on:

                print("FILL UNTIL FULL -> STARTING MOTOR")

                success = await turn_motor_on()

                if success:

                    state.motor_on = True

                    state.fill_start_time = time.time()

                    log_event(
                        "FILL_UNTIL_FULL_START",
                        "Motor started."
                    )

            # STOP WHEN FULL

            if (
                state.high_sensor_wet
                and state.motor_on
            ):

                print("FILL UNTIL FULL -> TANK FULL")

                await turn_motor_off()

                state.motor_on = False
                state.current_mode = "idle"
                state.active_mode_display = "Idle"

                log_event(
                    "FILL_UNTIL_FULL_COMPLETE",
                    "Tank reached full level."
                )
                

            # SENSOR OFFLINE

            elif (
                not state.sensor_online
                and state.motor_on
            ):

                print("FILL UNTIL FULL -> SENSOR OFFLINE")

                await turn_motor_off()

                state.motor_on = False
                state.current_mode = "idle"
                state.active_mode_display = "Idle"

                log_event(
                    "FILL_UNTIL_FULL_ABORTED",
                    "Sensor offline."
                )

            # FALLBACK TIMEOUT

            elif (
                state.motor_on
                and time.time() - state.fill_start_time >=
                config["system"]["sensor_fill_fallback_minutes"] * 60
            ):

                print("FILL UNTIL FULL -> TIMEOUT")

                await turn_motor_off()

                state.motor_on = False
                state.current_mode = "idle"
                state.active_mode_display = "Idle"

                log_event(
                    "FILL_UNTIL_FULL_TIMEOUT",
                    "Fallback timeout reached."
                )
                ####
        # =============================================
        # AUTO MODE
        # =============================================

        if state.auto_mode_enabled:

            # START MOTOR

            if (
                not state.low_sensor_wet
                and not state.motor_on
                and state.current_mode == "idle"
            ):

                print("AUTO MODE -> STARTING MOTOR")

                success = await turn_motor_on()

                if success:

                    state.current_mode = "auto_fill"

                    state.active_mode_display = (
                        "Automatic Fill"
                    )

                    state.motor_on = True

                    log_event(
                        "AUTO_START",
                        "Motor started automatically because low sensor became DRY"
                    )

            # STOP MOTOR

            if (
                state.high_sensor_wet
                and state.motor_on
                and state.current_mode == "auto_fill"
            ):

                print("AUTO MODE -> STOPPING MOTOR")

                await turn_motor_off()

                state.current_mode = "idle"

                state.active_mode_display = "Idle"

                state.motor_on = False

                log_event(
                    "AUTO_STOP",
                    "Motor stopped automatically because tank became FULL"
                )

        # # =============================================
        # # SENSOR OFFLINE SAFETY
        # # =============================================

        # if (
        #     not state.sensor_online
        #     and state.current_mode == "auto_fill"
        # ):
  
        #     print("Sensor offline -> emergency stop")

        #     await turn_motor_off()

        #     state.current_mode = "idle"

        #     state.active_mode_display = "Idle"

        #     state.motor_on = False

        #     log_event(
        #         "EMERGENCY_STOP",
        #         "Motor stopped because sensor telemetry went offline"
        #     )

        # =============================================
        # SENSOR OFFLINE SAFETY
        # =============================================

        if (
            not state.sensor_online
            and state.current_mode == "auto_fill"
        ):

            print("Sensor offline detected")

            motor_state = await get_motor_state()

            # -----------------------------------------
            # CASE 1 : Sensor offline, motor ON
            # -----------------------------------------
            if motor_state is True:
            
                print("Sensor OFFLINE, Motor ONLINE -> stopping motor")

                await turn_motor_off()

                state.current_mode = "idle"
                state.active_mode_display = "Idle"
                state.motor_on = False

                log_event(
                    "EMERGENCY_STOP",
                    "Sensor offline. Motor was running and has been stopped."
                )

            # -----------------------------------------
            # CASE 2 : Sensor offline, motor OFF
            # -----------------------------------------
            elif motor_state is False:
            
                print("Sensor OFFLINE, Motor already OFF")

                state.current_mode = "idle"
                state.active_mode_display = "Idle"
                state.motor_on = False

                log_event(
                    "EMERGENCY_STOP",
                    "Sensor offline. Motor was already OFF."
                )

            # -----------------------------------------
            # CASE 3 : Sensor offline, switch unreachable
            # -----------------------------------------
            else:
            
                print("Sensor OFFLINE, Switch OFFLINE")

                state.current_mode = "idle"
                state.active_mode_display = "Idle"
                state.motor_on = False

                log_event(
                    "EMERGENCY_STOP",
                    "Sensor offline and switch unreachable. Resetting automation."
                )

        await asyncio.sleep(2)

# =====================================================
# HOME
# =====================================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):

    # KEEPING THIS FOR LIVE STATE TRACKING
    state.motor_on = await get_motor_state()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "state": state,
            "schedules": get_schedules(),
            "events": get_recent_events(),
        },
    )
# =====================================================
# HEALTH CHECK
# =====================================================

@app.get("/health")
async def health():

    return {
        "status": "healthy",
        "sensor_online": state.sensor_online,
        "motor_on": state.motor_on,
        "current_mode": state.current_mode,
        "auto_mode_enabled": state.auto_mode_enabled,
    }
    
# =====================================================
# AUTO MODE TOGGLE
# =====================================================

@app.post("/auto-mode/toggle")
async def toggle_auto_mode():

    state.auto_mode_enabled = (
        not state.auto_mode_enabled
    )

    if state.auto_mode_enabled:

        log_event(
            "AUTO_MODE_ENABLED",
            "Automatic mode enabled by user"
        )

    else:

        log_event(
            "AUTO_MODE_DISABLED",
            "Automatic mode disabled by user"
        )

    return {
        "success": True,
        "enabled": state.auto_mode_enabled
    }

# =====================================================
# MANUAL OVERRIDE
# =====================================================

@app.post("/motor/manual-on")
async def manual_on():

    if state.current_mode != "idle":

        return {
            "success": False,
            "message": "Another mode already active"
        }

    success = await turn_motor_on()

    if success:

        state.current_mode = "manual_indefinite"

        state.active_mode_display = (
            "Manual Override"
        )

        state.motor_on = True

        log_event(
            "MANUAL_START",
            "Motor started manually by user"
        )

    return {"success": success}

# =====================================================
# MANUAL TIMER
# =====================================================

@app.post("/motor/manual-timer")
async def manual_timer(
    duration_minutes: int = Form(...)
):

    if state.current_mode != "idle":

        return {
            "success": False,
            "message": "Another mode already active"
        }

    duration_seconds = duration_minutes * 60

    success = await turn_motor_on()

    if success:

        state.current_mode = "manual_timer"

        state.active_mode_display = (
            f"Timed Override ({duration_minutes} min)"
        )

        state.motor_on = True

        log_event(
            "MANUAL_TIMER_START",
            f"Timed override started for {duration_minutes} minutes"
        )

        async def timer_stop():

            await asyncio.sleep(duration_seconds)

            await turn_motor_off()

            state.current_mode = "idle"

            state.active_mode_display = "Idle"

            state.motor_on = False

            log_event(
                "MANUAL_TIMER_STOP",
                "Timed override completed"
            )

        asyncio.create_task(timer_stop())

    return {"success": True}

# =====================================================
# STOP MOTOR
# =====================================================

@app.post("/motor/off")
async def motor_off():

    await turn_motor_off()

    state.current_mode = "idle"

    state.active_mode_display = "Idle"

    state.motor_on = False

    state.override_active = False

    state.schedule_running = False

    state.active_schedule_name = None
    state.active_schedule_id = None

    log_event(
        "MANUAL_STOP",
        "Motor manually stopped by user"
    )

    return {"success": True}

# =====================================================
# CREATE SCHEDULE
# =====================================================

@app.post("/schedule/create")
async def create_schedule_route(

    name: str = Form(...),

    schedule_type: str = Form(...),

    start_time: str = Form(...),

    duration_minutes: int = Form(None),
):

    duration_seconds = None

    if duration_minutes:
        duration_seconds = duration_minutes * 60

    create_schedule(
        name=name,
        schedule_type=schedule_type,
        start_time=start_time,
        duration_seconds=duration_seconds,
    )

    load_schedules()

    log_event(
        "SCHEDULE_CREATED",
        f"Schedule created: {name}"
    )

    return {"success": True}

# =====================================================
# DELETE SCHEDULE
# =====================================================

@app.post("/schedule/delete/{schedule_id}")
async def delete_schedule_route(schedule_id: int):

    delete_schedule(schedule_id)

    load_schedules()

    log_event(
        "SCHEDULE_DELETED",
        f"Schedule deleted with ID {schedule_id}"
    )

    return {"success": True}

# =====================================================
# FILL UNTIL FULL
# =====================================================


@app.post("/motor/fill-until-full")
async def fill_until_full():

    if state.current_mode != "idle":
        return {
            "success": False,
            "message": "Another mode already active"
        }

    state.current_mode = "fill_until_full"

    state.active_mode_display = "Fill Until Full"

    log_event(
        "FILL_UNTIL_FULL_REQUESTED",
        "Fill Until Full requested"
    )

    return {"success": True}

# @app.post("/motor/fill-until-full")
# async def fill_until_full():

#     if state.current_mode != "idle":

#         return {
#             "success": False,
#             "message": "Another mode already active"
#         }

#     success = await turn_motor_on()

#     if not success:

#         return {
#             "success": False
#         }

#     state.current_mode = "fill_until_full"

#     state.active_mode_display = (
#         "Fill Until Full"
#     )

#     state.motor_on = True

#     log_event(
#         "FILL_UNTIL_FULL_START",
#         "Fill until full started manually"
#     )

#     async def monitor_fill():

#         start_time = time.time()

#         fallback_timeout = (
#             60
#             * config["system"][
#                 "sensor_fill_fallback_minutes"
#             ]
#         )

#         while True:

#             if state.high_sensor_wet:

#                 print("Tank full reached")

#                 break

#             if not state.sensor_online:

#                 print("Sensor offline stop")

#                 break

#             elapsed = (
#                 time.time() - start_time
#             )

#             if elapsed >= fallback_timeout:

#                 print("Fallback timeout")

#                 break

#             await asyncio.sleep(2)

#         await turn_motor_off()

#         state.current_mode = "idle"

#         state.active_mode_display = "Idle"

#         state.motor_on = False

#         log_event(
#             "FILL_UNTIL_FULL_STOP",
#             "Fill until full completed"
#         )

#     asyncio.create_task(
#         monitor_fill()
#     )

#     return {"success": True}