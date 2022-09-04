import board
import simpleio
import time

short_pulses = (2000, [65, 65, 65, 65, 65, 65, 65, 7 * 65])
buzzer_pin = board.A5


def sound_alarm(alarm_pattern, pin, max_duration=2):
    assert len(alarm_pattern[1]) % 2 == 0
    total_duration = 0
    pattern_index = 0
    while total_duration <= max_duration:
        duration_ms = alarm_pattern[1][pattern_index]
        # print(pattern_index)
        if pattern_index % 2 == 0:
            # Every even time is sound time
            # print(f'ON: {alarm_pattern[0]}Hz, {duration_ms}ms')
            simpleio.tone(pin, alarm_pattern[0], duration=duration_ms / 1000)
        else:
            time.sleep(duration_ms / 1000)
            # print(f'OFF: {duration_ms}ms')
        total_duration += duration_ms / 1000
        pattern_index = (pattern_index + 1) % len(alarm_pattern[1])

# sound_alarm(short_pulses, buzzer_pin, 8)
