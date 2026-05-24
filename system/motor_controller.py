import asyncio
import json
import socket
import yaml

# =====================================================
# LOAD CONFIG
# =====================================================

with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

PLUG_IP = config["motor"]["plug_ip"]

WIZ_PORT = 38899

# =====================================================
# SEND UDP COMMAND
# =====================================================

async def send_wiz_command(payload):

    loop = asyncio.get_running_loop()

    def _send():

        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM
        )

        sock.settimeout(2)

        try:

            sock.sendto(
                json.dumps(payload).encode(),
                (PLUG_IP, WIZ_PORT)
            )

            data, _ = sock.recvfrom(4096)

            return json.loads(
                data.decode()
            )

        finally:

            sock.close()

    return await loop.run_in_executor(
        None,
        _send
    )

# =====================================================
# MOTOR ON
# =====================================================

async def turn_motor_on():

    try:

        await send_wiz_command({
            "id": 1,
            "method": "setState",
            "params": {
                "state": True
            }
        })

        return True

    except Exception as e:

        print("Motor ON error:", e)

        return False

# =====================================================
# MOTOR OFF
# =====================================================

async def turn_motor_off():

    try:

        await send_wiz_command({
            "id": 1,
            "method": "setState",
            "params": {
                "state": False
            }
        })

        return True

    except Exception as e:

        print("Motor OFF error:", e)

        return False

# =====================================================
# GET MOTOR STATE
# =====================================================

async def get_motor_state():

    try:

        response = await send_wiz_command({
            "id": 1,
            "method": "getPilot",
            "params": {}
        })

        result = response.get(
            "result",
            {}
        )

        return result.get(
            "state",
            False
        )

    except Exception as e:

        print("State read error:", e)

        return False