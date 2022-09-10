class TMF882X_Configuration:
    _TMF8821_DEFAULT_CONFIGS = [
        33,  # PERIOD_MS_LSB (at address 0x24)
        0,  # PERIOD_MS_MSB (at address 0x25)
        25,  # KILO_ITERATIONS_LSB (at address 0x26)
        2,  # KILO_ITERATIONS_MSB (at address 0x27)
        0,  # INT_THRESHOLD_LOW_LSB (at address 0x28)
        0,  # INT_THRESHOLD_LOW_MSB (at address 0x29)
        0,  # INT_THRESHOLD_HIGH_LSB (at address 0x2A)
        0,  # INT_THRESHOLD_HIGH_MSB (at address 0x2B)
        0,  # INT_ZONE_MASK_0 (at address 0x2C)
        0,  # INT_ZONE_MASK_1 (at address 0x2D)
        0,  # INT_ZONE_MASK_2 (at address 0x2E)
        0,  # INT_PERSISTENCE (at address 0x2F)
        6,  # CONFIDENCE_THRESHOLD (at address 0x30)
        0,  # GPIO_0 (at address 0x31)
        0,  # GPIO_1 (at address 0x32)
        0,  # POWER_CFG (at address 0x33)
        1,  # SPAD_MAP_ID (at address 0x34)
        4,  # ALG_SETTING_0 (at address 0x35)
        0,  # HIST_DUMP (at address 0x39)
        82,  # I2C_SLAVE_ADDRESS (at address 0x3B) --> 0x41 << 1
        0,  # OSC_TRIM_VALUE_LSB (at address 0x3C)
        0,  # OSC_TRIM_VALUE_MSB (at address 0x3D)
        0,  # I2C_ADDR_CHANGE (at address 0x3E)
    ]

    spad_map_str2val = {
        '3x3_normal_mode': 1,
        '3x3_macro_mode_upper': 2,
        '3x3_macro_mode_lower': 3,
        '3x3_wide_mode': 6,
        '3x3_checkerboard_mode': 11,
        '3x3_inverted_checkerboard_mode': 12,
        '4x4_normal_mode': 7,
        '4x4_macro_mode_upper': 4,
        '4x4_macro_mode_lower': 5,
        '4x4_narrow_mode': 13,
        '3x6_mode': 10,
    }

    spad_map_val2str = dict(zip(spad_map_str2val.values(), spad_map_str2val.keys()))


    def __init__(self):
        self.config = self._TMF8821_DEFAULT_CONFIGS


    @property
    def period_ms(self):
        return self.config[0] + (self.config[1] << 8)


    @period_ms.setter
    def period_ms(self, value):
        self.config[0] = value % 0xFF  # LSB
        self.config[1] = value >> 8  # MSB


    @property
    def iterations(self):
        return (self.config[2] + (self.config[3] << 8)) * 1024


    @iterations.setter
    def iterations(self, value):
        self.config[2] = int(value // 1024) % 0xFF  # LSB
        self.config[3] = int(value // 1024) >> 8  # MSB


    @property
    def confidence_threshold(self):
        return self.config[12]


    @confidence_threshold.setter
    def confidence_threshold(self, value):
        self.config[12] = value


    @property
    def spad_map(self):
        return self.spad_map_val2str[self.config[16]]


    @spad_map.setter
    def spad_map(self, description):
        self.config[16] = self.spad_map_str2val[description]


    @property
    def confidence_ecoding(self):
        return int(bool(self.config[17] & (1 << 7)))


    @confidence_ecoding.setter
    def confidence_ecoding(self, value):
        if value == 'logarithmic':
            self.config[17] |= 1 << 7
        elif value == 'linear':
            self.config[17] &= 1 << 7
        else:
            raise ValueError()


    def pack_to_data(self):
        if not all([0 <= v <= 255 for v in self.config]):
            raise ValueError(f'Some values are outside the byte range!\n{self.config}')
        return bytes(self.config)
