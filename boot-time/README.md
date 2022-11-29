# Experimenting with Micropython Boot time on ESP32

## Aim

To optimise the operation of micropython on ESP32 devices for operation as
battery operated sensor devices. In particular, to investigate and optimise:

1. Time (and power consumption) during boot from deepsleep
2. Power consumption to send espnow messages from sensors.

and to:

3. Compare power consumption for sending messages from ESPNow and wifi.

## Apparatus

### Software

These experiments are based on my micropython experiments branch at:
 - <https://github.com/glenn20/micropython/tree/espnow-g20-boot-tests>
   - based on micropython master branch revision: [v1.19.1-660-gc8913fdbf](https://github.com/micropython/micropython/tree/c8913fdbfadd43c879bba4d6d565be8b644f1feb)

### Hardware

- FeatherS3 device from UnexpectedMaker [feathers3.io](https://feathers3.io)
  - Selected for low power consumption and support for my sensors.
- [Power Profiler Kit
  II](https://www.nordicsemi.com/Products/Development-hardware/Power-Profiler-Kit-2)
  to measure power consumption of device during experiments.
  - Also supports visualisation of timing pulses from device pins.
- Cables, computer.

## Method and Results

### Measuring ESP32 boot times and power consumption

These measurements are made with the ESP32 device powered by USB (5V) and the
PPK2 operating in ammeter mode to measure the current on the USB 5V line. This
method does not fully reflect the power efficiency of the device when running
off a LiPoly battery, but is convenient for reprogramming and controlling the
device during the test. The average current draw for the FeatherS3 device while
in deepsleep is 1.73mA (at 5V USB).

See below for final power consumption measurements when the PPK2 is the power
source (simulating a LiPo battery power source).

#### Full boot to main.py

main.py:
```python
import time
import machine

pin = machine.Pin(18, machine.Pin.OUT)
pin.value(1)

# If we have just woken from a deep sleep go back to sleep
if machine.reset_cause() == machine.DEEPSLEEP_RESET:
    time.sleep_ms(10)
    pin.value(0)
    machine.deepsleep(1000)
```

Time to go back to sleep from main.py: 635ms

Power consumption: 41.3mC (11.5uWh) (microWh)

![PPK2 Full boot to main](./images/PPK2-full-boot-to-main.png)

_Interpreting the images:_
- The greyed numbers show values for current, time and charge within the
selected region.
- The voltage levels for Pin 18 (the boot timing signal pin) are shown in the
  trace lablled `0` at the bottom of the image. These are used to calculate
  timing between key boot events in micropython.

Time to start of micropython `app_main()`: 264ms (15.9mC)
![A](./images/ppk-20221117T050247.png)

From `app.main()` to end of boardctl_startup() (nvs_flash_init()): 7.8ms (0.57mC)

![A](./images/ppk-2-nvs_flash_init_time.png)

Time to execute gc_init() (with 16MB SPIRAM): 12.5ms (0.71mC)
![A](./images/ppk2-gc_init-time.png)

Time from call to load `_boot.py` to execution of deepsleep() in `main.py`:
350ms (23.6mC)

![A](./images/ppk-2-boot-to-main-py.png)

#### Optimisation opportunities:

**A: Reduce time to boot to `app_main()`:**
(commit [f2a3c66](https://github.com/glenn20/micropython/commit/f2a3c66ad30784cfc82269a491107befbd0bf8a6))

Add `CONFIG_BOOTLOADER_SKIP_VALIDATE_IN_DEEP_SLEEP=y` to
ports/esp32/boards/sdkconfig.base:
- **Reduces time to boot to `app_main()` from 264ms to 47.0ms** (15.9mC to 1.71mC)
- Disables validation of the micropython image when the device wakes from
  deepsleep (see [Espressif
  Docs](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/kconfig.html#config-bootloader-skip-validate-in-deep-sleep)))

![A](./images/ppk-2-fast-boot-to-app_main.png)

- Total boot time back to sleep: 418ms (26.5mC)

![A](./images/ppk-2-fast-boot-all.png)

**B: Execute app (deepsleep reboot) from frozen `_boot.py` module:**
(commit [8154c70](https://github.com/glenn20/micropython/commit/8154c70be59106cff7e0ad5c888479b62971852e))

Moving the code in `main.py` to `ports/esp32/modules/_boot.py` will eliminate
the need to mount and initialise the filesystem on the flash memory before
executing the app.

Time from `_boot.py` back to deepsleep reduced from 350ms (23.6mC) to 1.5ms
(0.09mC)

![A](./images/ppk-2-fast-boot_preboot_to_deepsleep.png)

Total time from boot back to deepsleep: 70.4ms (3.17mC)

![A](./images/ppk2-fast-boot_preboot.png)

**C: Skip `nvs_flash_init()` on boot if waking from deepsleep:**
(commit [9bfa464](https://github.com/glenn20/micropython/commit/9bfa4641cfe3f458c183ae88eae787a2cf2de3a7))

I _believe_ this is not necessary on every boot and can be safely skipped when
waking from deepsleep.

**UPDATE:** `nvs_flash_init()` must be called before initialising wifi (as RF
calibaration data is read from nvs).

Time for `nvs_flash_init()` reduced from 7.8ms (0.57mC) to 0ms (0mC).
(200microseconds is time to generate pulse on logic pin).

![](./images/ppk-2-fast-boot-no-nvs-init.png)

**D: Skip initialisation of SPIRAM on boot if waking from deepsleep:**
(commit [450b5a3](https://github.com/glenn20/micropython/commit/450b5a308df2e17eb2b740a49f65bb080c665612))

This reduces the work in gc_init() and is only of benefit on devices with
SPIRAM.

NOTE: For most battery operated devices it is unlikely that additional SPIRAM
would be required or be desirable, but I include it here as my testing device
was equipped with SPIRAM.

`gc_init()` time reduced from 12.5ms (0.71mC) to less than 0.1ms.
(200 microseconds is time to generate pulse on logic pin.)

![](./images/ppk-2-fast-boot-no-spiram.png)

**After all optimisations:**

Time from boot to back to deepsleep: 50.0ms (1.87mC) (reduced from 264ms
(15.9mC))

(Includes 6 * 0.2 = 1.2ms overhead for generating boot timing signals).

![](./images/ppk-2-fast-boot-final.png)

**Before Optimisation:**

(Energy (uWh) = 1000 * Charge (mC) * 5V / (60 * 60))
| Component | Time (ms) | Charge (mC) | Energy (microWh) |
|---|---:|---:|---:|
| Boot to `app_main()` without Validation | 47.0 |  1.7 | 2.4 |
| Validation of Image     | 217  | 14.2 | 19.7 |
| `nvs_flash_init()`      | 7.8  |  0.57 | 0.8 |
| Allocate SPIRAM to GC   | 12.5 |  0.71 | 1.0 |
| Micropython `app_main()` to `_boot.py` | 0.8 | 0.06 | 0.8 |
| `_boot.py` to deepsleep (`main.py`) | 350 | 23.6 | 32.8 |
|**Total:** | **635.1** | **41.92** | **58.3** |

**After Optimisation**
| Component | Time (ms) | Charge (mC) | Energy (microWh) |
|---|---:|---:|---:|
| Boot to `app_main()` without Validation | 47.0 |  1.7 | 2.4 |
| Micropython `app_main()` to `_boot.py` | 0.8 | 0.06 | 0.1 |
| `_boot.py` to deepsleep (`_preboot.py`) | 1.0 | 0.06 | 0.1 |
|**Total:** | **48.8** | **1.82** | **2.5** |

## Optimised code on ESP32 module:

Compared with the ESP32-S2 module above, the ESP32 boot from, and return to
deepsleep takes 70ms (3.32mC)

NOTE: This esp32 module board is not very power efficient (background current =
15.0mA), so charge values should not be compared directly.

![](./images/ppk-2-ESP32-fast-boot-1.png)

## Using ESP32 Wake stubs

(See [Espressif
Docs](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-guides/deep-sleep-stub.html)
and examples at <https://gist.github.com/igrr/54f7fbe0513ac14e1aea3fd7fbecfeab>)

Returns to sleep after 2.8ms (~0.044mC)!

Useful for silently counting input pulses or timer base sampling of a GPIO
input.

However, there are some severe limitations on what you can do in the wake_stub
function (see docs).

![](./images/ppk-2-ESP32-wake-stub.png)

### Wake Stubs on the ESP32S3 (UM_FEATHERS3)

Returns to deepsleep after 8.7ms (0.18mC) (4x longer than ESP32).
(vs 50.2ms/2.0mC)

![](./images/ppk-2-esp32s3-wake-stub.png)

Compared with fast boot from deep sleep.

![](./images/ppk-2-esp32s3-wake-stub-fast-boot.png)

### Send status via ESNow from _boot.py
(commit
[fc62686](https://github.com/micropython/micropython/commit/fc62686524245f9f1b492eb0c978e00375e44d90))

**NOTE:** This commit has `nvs_flash_init()` enabled at boot time as this is
required for `esp_wifi_init()` (additional 7ms of bootup time).

`_preboot.py`:
```python
import machine

def send_state(broker):
    import network
    from _espnow import ESPNow

    enow = ESPNow()
    enow.active(True)
    enow.add_peer(broker)
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    enow.send(broker, b"wake_up", True)
    enow.active(False)
    sta.active(False)

if machine.reset_cause() == machine.DEEPSLEEP_RESET:
    send_state(b"\xf4\x12\xfaA\xf7T")
    machine.deepsleep(1000)
```

**ESP32S3**

**ESP32**

- Time to boot and return to deepsleep is 118.8ms (7.68mC).
- A 1 byte message generates a current spike of ~550mA over 0.6ms.
  - A 250 byte messages generates a transmission spike of ~2.5ms and scales
    linearly with message length between these values.
- **NOTE:** The ESP32 board is inefficient and has a deepsleep current of 15mA.

![](./images/ppk-2-fast-boot_preboot-espnow-esp32.png)

If the peer is not found, the transmission is retried and more power is
consumed:

- 144.9ms (15.43mC) (twice the power consumption)
- Note: Retransmission does **NOT** occur if sending to the broadcast address.

![](./images/ppk-2-fast-boot_preboot-espnow-esp32-not-received.png)
![](./images/ppk-2-fast-boot_preboot-espnow-esp32-not-received-closeup.png)


### Send status over wifi from _boot.py
(commit
[44a1341](https://github.com/glenn20/micropython/commit/44a1341147513e7fbe0ccd9c2025869c09d27845))

`_preboot_wifi.py`:
```python
import machine

def send_state(broker):
    import network
    import urequests

    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    sta.connect("ssid", "password")
    while not sta.isconnected():
        pass
    try:
        r = urequests.post("http://XXX.XXX.XXX.XXX:5000/status", data="hello")
    except OSError:
        pass
    sta.disconnect()
    sta.active(False)

if machine.reset_cause() == machine.DEEPSLEEP_RESET:
    send_state()
    machine.deepsleep(1000)
```

**ESP32S3**

**ESP32**

- Time to boot and return to deepsleep is 2928ms (341.3mC).
- This showed considerable variability with many some tarnsmissions taking much
  longer (up to 4.9s (490mC)).
- You can see the power saving mode at work, where the wifi radio is turned off
  in PS_MIN_MODEM.

![](./images/ppk-2-fast-boot_preboot-wifi-esp32.png)

**Connect to Wifi only:**

- Time to connect to wifi and then deepsleep (ie. don't send message) is 1626ms (204.3mC).

![](./images/ppk-2-fast-boot_preboot-wifi-esp32-connect-only.png)

**Wifi connect - static IP:**

- Time to boot and return to deepsleep is 1157ms (165.6mC).
  - This may vary depending on your Access Point

![](./images/ppk-2-fast-boot_preboot-wifi-esp32-connect-only-static-ip.png)


