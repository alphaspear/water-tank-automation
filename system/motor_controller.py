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
# INTERNAL ASYNC FUNCTIONS
# =====================================================

async def _async_turn_on():

    plug = wizlight(PLUG_IP)

    await plug.turn_on()

async def _async_turn_off():

    plug = wizlight(PLUG_IP)

    await plug.turn_off()

async def _async_get_state():

    plug = wizlight(PLUG_IP)

    state = await plug.updateState()

    return state.get_state()

# =====================================================
# SAFE LOOP RUNNER
# =====================================================

def run_async(coro):

    loop = asyncio.new_event_loop()

    asyncio.set_event_loop(loop)

    try:

        result = loop.run_until_complete(coro)

        return result

    finally:

        loop.close()

# =====================================================
# PUBLIC FUNCTIONS
# =====================================================

async def turn_motor_on():

    try:

        run_async(_async_turn_on())

        return True

    except Exception as e:

        print("Motor ON error:", e)

        return False

# =====================================================

async def turn_motor_off():

    try:

        run_async(_async_turn_off())

        return True

    except Exception as e:

        print("Motor OFF error:", e)

        return False

# =====================================================

async def get_motor_state():

    try:

        return run_async(_async_get_state())

    except Exception as e:

        print("State read error:", e)

        return False