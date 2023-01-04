import alarm


class CyclicBuffer:
    """
    Cyclic buffer with arbitrary datatype.

    The cyclic buffer consists of a block of memory starting at a certain offset position and holds a maximum
    capacity of bytes. Each value in the buffer can be of a size of one or more bytes. The head pointer is the "write to
    buffer index" and points to the next free element. The tail pointer is the "read from buffer index" and points to
    the oldest written element. Head and tail pointers are both in byte space, not value space.
    """
    addr_offset_capacity = 0  # in values
    addr_capacity_size = 2
    addr_value_size = 2  # bytes per value
    addr_value_size_size = 1
    addr_offset_head = 3  # in values
    addr_head_size = 2
    addr_offset_tail = 5
    addr_tail_size = 2
    header_size = 7


    def __init__(self, addr, capacity: int, bytes_per_value: int):
        assert capacity % bytes_per_value == 0
        self.addr = addr
        self.bytes_per_value = bytes_per_value

        # Read buffer size
        self.capacity = int.from_bytes(alarm.sleep_memory[0:2], 'big')
        if self.capacity == 0 or self.capacity != capacity:
            # Memory wasn't initialized
            assert 0 <= capacity <= 2 ** 16 - 1
            # Initialize empty buffer
            self.capacity = capacity
            self.value_capacity = self.capacity // self.bytes_per_value
            self.head = self.addr + self.header_size
            self.tail = self.addr + self.header_size
            self.current_size = 0
            self.update_header()
        else:
            # Read bytes per value
            self.bytes_per_value = int.from_bytes(
                alarm.sleep_memory[self.addr + self.addr_value_size:self.addr + self.addr_value_size +
                                                                    self.addr_value_size_size], 'big')
            self.value_capacity = self.capacity // self.bytes_per_value
            # Read buffer head and tail
            self.head = int.from_bytes(
                alarm.sleep_memory[
                self.addr + self.addr_offset_head:self.addr + self.addr_offset_head + self.addr_head_size],
                'big')
            self.tail = int.from_bytes(
                alarm.sleep_memory[
                self.addr + self.addr_offset_tail:self.addr + self.addr_offset_tail + self.addr_tail_size], 'big')
            self.current_size = int((self.head - self.tail) % self.capacity) // self.bytes_per_value
            if self.current_size == 0:
                # We cannot distinguish an empty from a full buffer -- thus assume the buffer is full if head == tail
                self.current_size = self.value_capacity


    def update_header(self, only_head_and_tail=False):
        if not only_head_and_tail:
            alarm.sleep_memory[self.addr + self.addr_offset_capacity:self.addr + self.addr_offset_capacity +
                                                                     self.addr_capacity_size] = \
                self.capacity.to_bytes(self.addr_capacity_size, 'big')
            alarm.sleep_memory[self.addr + self.addr_value_size:self.addr + self.addr_value_size +
                                                                self.addr_value_size_size] = \
                self.bytes_per_value.to_bytes(self.addr_value_size_size, 'big')
        alarm.sleep_memory[self.addr + self.addr_offset_head:self.addr + self.addr_offset_head +
                                                             self.addr_head_size] = \
            self.head.to_bytes(self.addr_head_size, 'big')
        alarm.sleep_memory[self.addr + self.addr_offset_tail:self.addr + self.addr_offset_tail +
                                                             self.addr_tail_size] = \
            self.tail.to_bytes(self.addr_tail_size, 'big')


    def increment_modulo_capacity(self, pointer):
        return self.addr + self.header_size + (
                (pointer + self.bytes_per_value - self.addr - self.header_size) % self.capacity)


    def add_value(self, val):
        # Encode value to byte array
        byte_array = self.encode(val)
        # Write bytes to head position
        alarm.sleep_memory[self.head:self.head + self.bytes_per_value] = byte_array
        # Increment head pointer
        self.head = self.increment_modulo_capacity(self.head)
        if self.current_size >= self.value_capacity:
            # Full capacity: Overwriting oldest data --> move tail
            self.tail = self.head
        else:
            self.current_size += 1
        self.update_header(only_head_and_tail=True)


    def read_all(self):
        val_list = []
        read_head = self.tail
        for _ in range(self.current_size):
            byte_block = alarm.sleep_memory[read_head:read_head + self.bytes_per_value]
            read_head = self.increment_modulo_capacity(read_head)
            val = self.decode(byte_block)
            val_list.append(val)
        return val_list


    def empty(self):
        self.tail = self.head
        self.current_size = 0
        self.update_header(only_head_and_tail=True)


    def encode(self, val) -> bytearray:
        # @abstractmethod
        pass


    def decode(self, byte_array: bytearray):
        # @abstractmethod
        pass


    def debug_print(self, max_addr=None):
        if max_addr is None:
            max_addr = self.header_size + self.capacity
        sizes = [self.addr_capacity_size, self.addr_value_size_size, self.addr_head_size, self.addr_tail_size]
        descs = ['capacity', 'bytes per value', 'head', 'tail']
        print('adr,int')
        addr = 0
        for startup_size, desc in zip(sizes, descs):
            b = alarm.sleep_memory[addr:addr + startup_size]
            print(f'{addr:>3} {int.from_bytes(b, "big")} \t {desc}')
            addr += startup_size
        while addr < max_addr:
            b = alarm.sleep_memory[addr:addr + 2]
            print(f'{addr:>3} {int.from_bytes(b, "big")}')
            addr += self.bytes_per_value

        print(f'capacity:{self.value_capacity} values ({self.capacity}B) @{self.bytes_per_value}B/value,', end='')
        print(f' {self.tail}->{self.head}, {self.current_size} values')


class Cyclic16BitTempBuffer(CyclicBuffer):
    """
    Cyclic buffer holding temperature values in 16 bit format.

    Temperatures between -40°C and 85°C must be representable with two decimals.
    85.00 - (-40.00) = 125.00

    In theory, the representable range is from -40.00°C to 615.35°C.
    """


    def __init__(self, addr, max_value_capacity):
        self.bytes_per_value = 2
        super().__init__(addr, max_value_capacity * self.bytes_per_value, self.bytes_per_value)


    def encode(self, temp: float) -> bytearray:
        int_val = round((temp + 40.0) * 100.0)
        return bytearray(int_val.to_bytes(self.bytes_per_value, 'big'))


    def decode(self, byte_array: bytearray) -> float:
        int_val = int.from_bytes(byte_array, 'big')
        return int_val / 100.0 - 40.0


class Cyclic16BitPercentageBuffer(CyclicBuffer):
    """
    Cyclic buffer holding percentage values in 16 bit format.

    Percentages between 0% and 400% must be representable with two decimals.
    400 - 0 = 400.00

    In theory, the representable range is from 0.00% to 655.35%.
    """


    def __init__(self, addr, max_value_capacity):
        self.bytes_per_value = 2
        super().__init__(addr, max_value_capacity * self.bytes_per_value, self.bytes_per_value)


    def encode(self, percentage: float) -> bytearray:
        int_val = round(percentage * 100.0)
        int_val = min(int_val, 65535)  #
        return bytearray(int_val.to_bytes(self.bytes_per_value, 'big'))


    def decode(self, byte_array: bytearray) -> float:
        int_val = int.from_bytes(byte_array, 'big')
        return int_val / 100.0
