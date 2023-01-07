import os
import sdcardio
import storage
import busio
import board

filename = 'data_000.csv'
DEBUG = True

temp_buffer = [24, 35, 99, 14]
growth_buffer = [110, 120, 140, 222, 144, 150, 130]

try:
    with busio.SPI(board.SCK, board.MOSI, board.MISO) as spi:
        sd_cd = board.D5
        sd = sdcardio.SDCard(spi, sd_cd)
        vfs = storage.VfsFat(sd)
        storage.mount(vfs, '/sd')

        files = os.listdir('/sd')
        data_files = [f for f in files if f.startswith('data_') and f.endswith('.csv')]
        if data_files:
            next_number = int(sorted(data_files, reverse=True)[0][5:8]) + 1
        else:
            next_number = 0

        with open(f'/sd/data_{next_number:03d}.csv', 'w') as file:
            file.write('growth,temp\n')
            max_rows = max(len(temp_buffer), len(growth_buffer))
            for i in range(max_rows):
                i_growth = i - (max_rows - len(growth_buffer))
                i_temp = i - (max_rows - len(temp_buffer))
                if i_growth >= 0:
                    file.write(f'{growth_buffer[i_growth]:.2f},')
                else:
                    file.write(',')
                if i_temp >= 0:
                    file.write(f'{temp_buffer[i_temp]:.2f}')
                file.write('\n')

        sd.sync()
        storage.umount(vfs)
except Exception as e:
    if DEBUG:
        print(f'Couldn\'t write to SD card: {e}')
