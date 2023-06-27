import time, network, espnow

sta = network.WLAN(0)
e = espnow.ESPNow()
sta.active(1)
e.active(1)
pm_values = ((75, 200), (75, 300), (50, 500), (10, 500), (1000, 500))
while True:
    for p in pm_values:
        e.config(pm=p)
        time.sleep(2)
