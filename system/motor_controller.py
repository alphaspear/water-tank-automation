import asyncio
import yaml

from pywizlight import wizlight

# =====================================================
# LOAD CONFIG
# =====================================================

with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

PLUG_IP = config["motor"]["plug_ip"]

plug = wizlight(PLUG_IP)

# =====================================================
# MOTOR CONTROL
# =====================================================

async def turn_motor_on():

    try:

        await plug.turn_on()

        return True

    except Exception as e:

        print("Motor ON error:", e)

        return False

async def turn_motor_off():

    try:

        await plug.turn_off()

        return True

    except Exception as e:

        print("Motor OFF error:", e)

        return False

async def get_motor_state():

    try:

        state = await plug.updateState()

        return state.get_state()

    except Exception as e:

        print("State read error:", e)

        return False