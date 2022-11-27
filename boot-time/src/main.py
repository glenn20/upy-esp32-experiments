import time
import machine

ldr_pin = machine.Pin(18, machine.Pin.OUT)
ldr_pin.value(1)

# If we have just woken from a deep sleep or running on battery...
if machine.reset_cause() in (machine.DEEPSLEEP_RESET, ):
    time.sleep_ms(1)
    ldr_pin.value(0)
    machine.deepsleep(1000)
