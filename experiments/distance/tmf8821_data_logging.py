import re
import time

import pandas as pd
import serial


def main():
    port_name = 'COM4'
    baud_rate = 115200
    serial_connection = serial.Serial(port_name, baud_rate, timeout=4)

    csv_data = []
    start_time = None
    try:
        time.sleep(0.1)  # give some buffer time for retrieving data
        serial_connection.reset_input_buffer()

        while True:
            line = serial_connection.readline().decode("utf-8")

            beginning_match = re.findall(r'(\d)x(\d)', line)
            if beginning_match is None:
                print(f'Line doesn''t start with DxD:\n{line}')
                continue
            columns = line.split(' ')[1:-2]
            if len(columns) != 18:
                print('.'.join(columns))
                print(f'Line has not enough columns:\n{line}')
                continue
            start_time = start_time or pd.Timestamp.now()

            delta_time = pd.Timestamp.now() - start_time
            csv_data.append((delta_time, *columns))
            print(f'Recorded {len(csv_data)} rows in {delta_time}...\r', end='')
    except KeyboardInterrupt:
        serial_connection.close()
        df = pd.DataFrame(csv_data, columns=['timestamp', 'd0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7', 'd8',
                                             'c0', 'c1', 'c2', 'c3', 'c4', 'c5', 'c6', 'c7', 'c8'])
        print(f'\nSaving table with shape {df.shape} to "log_data.csv"...')
        df.to_csv('log_data.csv')


if __name__ == '__main__':
    main()
