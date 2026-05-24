import asyncio
import time

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
from fastapi import Form

from mqtt_handler import mqtt_thread

from state_manager import state

from motor_controller import (
    turn_motor_on,
    turn_motor_off,
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
# APP
# =====================================================

app = FastAPI()

APP_START_TIME = time.time()

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

# =====================================================
# SENSOR HEALTH
# =====================================================

async def sensor_health_monitor():

    while True:

        if state.last_sensor_update:

            diff = time.time() - state.last_sensor_update

            if diff > 15:

                state.sensor_online = False

        await asyncio.sleep(5)

# =====================================================
# AUTOMATION LOOP
# =====================================================

async def automation_loop():

    while True:

        # =================================================
        # AUTO MODE START
        # =================================================

        if state.auto_mode_enabled:

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

        # =================================================
        # AUTO STOP
        # =================================================

        if (
            state.high_sensor_wet
            and state.motor_on
            and state.current_mode in [
                "auto_fill",
                "fill_until_full",
                "scheduled_sensor"
            ]
        ):

            print("HIGH SENSOR WET -> STOPPING")

            await turn_motor_off()

            state.current_mode = "idle"

            state.active_mode_display = "Idle"

            state.motor_on = False

            state.schedule_running = False

            state.active_schedule_name = None

            state.active_schedule_id = None

        # =================================================
        # SENSOR OFFLINE SAFETY
        # =================================================

        if (
            not state.sensor_online
            and state.motor_on
            and state.current_mode in [
                "auto_fill",
                "fill_until_full",
                "scheduled_sensor"
            ]
        ):

            print("SENSOR OFFLINE -> EMERGENCY STOP")

            await turn_motor_off()

            state.current_mode = "idle"

            state.active_mode_display = "Idle"

            state.motor_on = False

            state.schedule_running = False

            state.active_schedule_name = None

            state.active_schedule_id = None

        await asyncio.sleep(2)

# =====================================================
# HOME
# =====================================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "state": state,
            "schedules": get_schedules(),
        },
    )

# =====================================================
# AUTO MODE TOGGLE
# =====================================================

@app.post("/auto-mode/toggle")
async def toggle_auto_mode():

    state.auto_mode_enabled = (
        not state.auto_mode_enabled
    )

    return {
        "success": True,
        "enabled": state.auto_mode_enabled
    }

# =====================================================
# MANUAL ON
# =====================================================

@app.post("/motor/manual-on")
async def manual_on():

    success = await turn_motor_on()

    if success:

        state.current_mode = "manual_indefinite"

        state.active_mode_display = (
            "Manual Override"
        )

        state.motor_on = True

    return {"success": success}

# =====================================================
# FILL UNTIL FULL
# =====================================================

@app.post("/motor/fill-until-full")
async def fill_until_full():

    success = await turn_motor_on()

    if success:

        state.current_mode = "fill_until_full"

        state.active_mode_display = (
            "Fill Until Full"
        )

        state.motor_on = True

    return {"success": success}

# =====================================================
# MANUAL TIMER
# =====================================================

@app.post("/motor/manual-timer")
async def manual_timer(
    duration_minutes: int = Form(...)
):

    duration_seconds = duration_minutes * 60

    success = await turn_motor_on()

    if success:

        state.current_mode = "manual_timer"

        state.active_mode_display = (
            f"Timed Override ({duration_minutes} min)"
        )

        state.motor_on = True

        async def timer_stop():

            await asyncio.sleep(duration_seconds)

            await turn_motor_off()

            state.current_mode = "idle"

            state.active_mode_display = "Idle"

            state.motor_on = False

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

    return {"success": True}

# =====================================================
# DELETE SCHEDULE
# =====================================================

@app.post("/schedule/delete/{schedule_id}")
async def delete_schedule_route(schedule_id: int):

    delete_schedule(schedule_id)

    load_schedules()

    return {"success": True}

# =====================================================
# HEALTH
# =====================================================

@app.get("/health")
async def health():

    uptime_seconds = int(
        time.time() - APP_START_TIME
    )

    return {

        "status": "ok",

        "sensor_online": state.sensor_online,

        "low_sensor_wet": state.low_sensor_wet,

        "high_sensor_wet": state.high_sensor_wet,

        "motor_on": state.motor_on,

        "current_mode": state.current_mode,

        "active_mode_display": (
            state.active_mode_display
        ),

        "auto_mode_enabled": (
            state.auto_mode_enabled
        ),

        "schedule_running": (
            state.schedule_running
        ),

        "active_schedule_name": (
            state.active_schedule_name
        ),

        "last_sensor_update": (
            state.last_sensor_update
        ),

        "server_timestamp": time.time(),

        "uptime_seconds": uptime_seconds
    }