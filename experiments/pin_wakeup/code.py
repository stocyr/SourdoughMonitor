import time

t_start = time.monotonic()

import alarm
import board

from utils.oled import full_width_display

full_width_display()

print(f'Startup time: {t_start}s')
wake = alarm.wake_alarm
if wake is None:
    print('Wakeup: Reset')
elif isinstance(wake, alarm.time.TimeAlarm):
    print(f'Wakeup: timeout')
elif isinstance(wake, alarm.pin.PinAlarm):
    print(f'Wakeup: Pin {wake.pin} = {wake.value}')

for _ in range(4):
    print('.', end='')
    time.sleep(1)

left_alarm = alarm.pin.PinAlarm(pin=board.D11, value=False, pull=True)
middle_alarm = alarm.pin.PinAlarm(pin=board.D12, value=False, pull=True)

timeout_alarm = alarm.time.TimeAlarm(monotonic_time=t_start + 10)
# This does not return -- it sleeps 20 seconds and then restarts from top
alarm.exit_and_deep_sleep_until_alarms(timeout_alarm, left_alarm, middle_alarm)
# We will never get *here*
