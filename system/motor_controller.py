import asyncio
import yaml

from pywizlight import wizlight

# =====================================================
# LOAD CONFIG
# =====================================================

with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

PLUG_IP = config["motor"]["plug_ip"]

# =====================================================
# INTERNAL ASYNC
# =====================================================

async def _turn_on():

    plug = wizlight(PLUG_IP)

    await plug.turn_on()

async def _turn_off():

    plug = wizlight(PLUG_IP)

    await plug.turn_off()

async def _get_state():

    plug = wizlight(PLUG_IP)

    state = await plug.updateState()

    return state.get_state()

# =====================================================
# THREAD SAFE EXECUTION
# =====================================================

def run_async_blocking(coro):

    return asyncio.run(coro)

# =====================================================
# PUBLIC FUNCTIONS
# =====================================================

async def turn_motor_on():

    try:

        await asyncio.to_thread(
            run_async_blocking,
            _turn_on()
        )

        return True

    except Exception as e:

        print("Motor ON error:", e)

        return False

# =====================================================

async def turn_motor_off():

    try:

        await asyncio.to_thread(
            run_async_blocking,
            _turn_off()
        )

        return True

    except Exception as e:

        print("Motor OFF error:", e)

        return False

# =====================================================

async def get_motor_state():

    try:

        return await asyncio.to_thread(
            run_async_blocking,
            _get_state()
        )

    except Exception as e:

        print("State read error:", e)

        return False