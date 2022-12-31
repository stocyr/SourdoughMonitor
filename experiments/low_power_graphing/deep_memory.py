import alarm


class CyclicBuffer:
    addr_offset_maxsize = 0  # in values
    addr_maxsize_size = 2
    addr_value_size = 2  # bytes per value
    addr_value_size_size = 1
    addr_offset_head = 3  # in values
    addr_head_size = 2
    addr_offset_tail = 5
    addr_tail_size = 2
    addr_offset_buffer_start = 7


    def __init__(self, addr, default_max_size: int, default_value_size: int):
        self.addr = addr

        # Read buffer size
        self.max_size = int.from_bytes(alarm.sleep_memory[0:2], 'big')
        if self.max_size == 0:
            # Memory wasn't initialized
            assert 0 <= default_max_size <= 2 ** 16 - 1
            # Initialize empty buffer
            self.max_size = default_max_size
            self.bytes_per_value = default_value_size
            self.head = self.addr + self.addr_offset_buffer_start
            self.tail = self.addr + self.addr_offset_buffer_start
            self.write_header()
        else:
            # Read bytes per value
            self.bytes_per_value = int.from_bytes(
                alarm.sleep_memory[self.addr + self.addr_value_size:self.addr + self.addr_value_size +
                                                                    self.addr_value_size_size], 'big')
            # Read buffer head and tail
            self.head = int.from_bytes(
                alarm.sleep_memory[
                self.addr + self.addr_offset_head:self.addr + self.addr_offset_head + self.addr_head_size],
                'big')
            self.tail = int.from_bytes(
                alarm.sleep_memory[
                self.addr + self.addr_offset_tail:self.addr + self.addr_offset_tail + self.addr_tail_size], 'big')
        self.current_size = (self.head - self.tail) % self.max_size


    def write_header(self):
        alarm.sleep_memory[self.addr + self.addr_offset_maxsize:self.addr + self.addr_offset_maxsize +
                                                                self.addr_maxsize_size] = \
            self.max_size.to_bytes(self.addr_maxsize_size, 'big')
        alarm.sleep_memory[self.addr + self.addr_value_size:self.addr + self.addr_value_size +
                                                            self.addr_value_size_size] = \
            self.bytes_per_value.to_bytes(self.addr_value_size_size, 'big')
        alarm.sleep_memory[self.addr + self.addr_offset_head:self.addr + self.addr_offset_head +
                                                             self.addr_head_size] = \
            self.head.to_bytes(self.addr_head_size, 'big')
        alarm.sleep_memory[self.addr + self.addr_offset_tail:self.addr + self.addr_offset_tail +
                                                             self.addr_tail_size] = \
            self.tail.to_bytes(self.addr_tail_size, 'big')


    def add_value(self):
        pass
