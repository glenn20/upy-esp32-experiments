# My Experiments and Measurments with Micropython on ESP32* devices

Here are some of my experiments and measurements on running micropython on
ESP32* devices, including:

- [Optimising Micropython Boot Time](./OptimisingMicropythonBootTime/README.md):
  Optimising the time to boot Micropython from deepsleep mode and returning to
  deepsleep.
- [ESP32 Wake Stubs](./ESP32WakeStubs/README.md): Measuring power consumption
  and time to boot using the ESP32 Wake Stubs.
- [ESPNow vs Wifi Energy Consumption](./ESPNowvsWifiEnergyUsage/README.md):
  Measuring the energy consumed to boot Micropython from deepsleep and send a
  status message to a peer vie ESPNow and Wifi.
