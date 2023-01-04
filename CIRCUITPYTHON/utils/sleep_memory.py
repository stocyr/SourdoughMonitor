import alarm


class CyclicBuffer:
    """
    Cyclic buffer with arbitrary datatype.

    The cyclic buffer consists of a block of memory starting at a certain offset position and holds a maximum
    capacity of bytes. Each value in the buffer can be of a size of one or more bytes. The head pointer is the "write to
    buffer index" and points to the next free element. The tail pointer is the "read from buffer index" and points to
    the oldest written element. Head and tail pointers are both in byte space, not value space. The situation where the
    head and the tail pointer both point to the same memory can be interpreted as either a full or an empty buffer.
    Thus, a flag for "empty" is reserved.
    """
    addr_offset_capacity = 0  # in values
    addr_capacity_size = 2
    addr_offset_bytes_per_value = 2  # bytes per value
    addr_bytes_per_value_size = 1
    addr_offset_head = 3  # in values
    addr_head_size = 2
    addr_offset_tail = 5
    addr_tail_size = 2
    addr_offset_empty = 7
    header_size = 8


    def __init__(self, addr, capacity: int, bytes_per_value: int):
        assert capacity % bytes_per_value == 0
        self.addr = addr

        # Read bytes per value
        self.bytes_per_value = int.from_bytes(
            alarm.sleep_memory[self.addr + self.addr_offset_bytes_per_value:
                               self.addr + self.addr_offset_bytes_per_value + self.addr_bytes_per_value_size], 'big')

        # Read buffer size
        self.capacity = int.from_bytes(
            alarm.sleep_memory[self.addr + self.addr_offset_capacity:
                               self.addr + self.addr_offset_capacity + self.addr_capacity_size], 'big')
        if self.capacity == 0 or self.capacity != capacity or self.bytes_per_value == 0:
            # Memory wasn't initialized
            assert 0 <= capacity <= 2 ** 16 - 1
            # Initialize empty buffer
            self.capacity = capacity
            self.bytes_per_value = bytes_per_value
            self.value_capacity = self.capacity // self.bytes_per_value
            self.head = self.addr + self.header_size
            self.tail = self.addr + self.header_size
            self.empty = 1
            self.current_size = 0
            self.update_header()
        else:
            self.value_capacity = self.capacity // self.bytes_per_value
            # Read buffer head and tail
            self.head = int.from_bytes(
                alarm.sleep_memory[
                self.addr + self.addr_offset_head:self.addr + self.addr_offset_head + self.addr_head_size], 'big')
            self.tail = int.from_bytes(
                alarm.sleep_memory[
                self.addr + self.addr_offset_tail:self.addr + self.addr_offset_tail + self.addr_tail_size], 'big')
            self.empty = alarm.sleep_memory[self.addr + self.addr_offset_empty]
            if self.empty:
                self.current_size = 0
            else:
                self.current_size = int((self.head - self.tail) % self.capacity) // self.bytes_per_value


    def update_header(self, only_head_and_tail=False):
        if not only_head_and_tail:
            alarm.sleep_memory[self.addr + self.addr_offset_capacity:self.addr + self.addr_offset_capacity +
                                                                     self.addr_capacity_size] = \
                self.capacity.to_bytes(self.addr_capacity_size, 'big')
            alarm.sleep_memory[
            self.addr + self.addr_offset_bytes_per_value:self.addr + self.addr_offset_bytes_per_value +
                                                         self.addr_bytes_per_value_size] = \
                self.bytes_per_value.to_bytes(self.addr_bytes_per_value_size, 'big')
        alarm.sleep_memory[self.addr + self.addr_offset_head:self.addr + self.addr_offset_head +
                                                             self.addr_head_size] = \
            self.head.to_bytes(self.addr_head_size, 'big')
        alarm.sleep_memory[self.addr + self.addr_offset_tail:self.addr + self.addr_offset_tail +
                                                             self.addr_tail_size] = \
            self.tail.to_bytes(self.addr_tail_size, 'big')
        alarm.sleep_memory[self.addr + self.addr_offset_empty] = self.empty


    def increment_modulo_capacity(self, pointer):
        return self.addr + self.header_size + (
                (pointer + self.bytes_per_value - self.addr - self.header_size) % self.capacity)


    def add_value(self, val):
        self.empty = 0
        # Encode value to byte array
        byte_array = self.encode(val)
        # Write bytes to head position
        alarm.sleep_memory[self.head:self.head + self.bytes_per_value] = byte_array
        # Increment head pointer
        self.head = self.increment_modulo_capacity(self.head)
        if self.current_size >= self.value_capacity:
            # Full capacity: Overwriting oldest data --> move tail along with head
            self.tail = self.head
        else:
            self.current_size += 1
        self.update_header(only_head_and_tail=True)


    def read_array(self, amount=None):
        val_list = []
        if amount is None:
            amount = self.current_size
            read_head = self.tail
        else:
            amount = min(self.current_size, amount)
            read_head = self.addr + self.header_size + (
                    self.head - self.addr - self.header_size - amount * self.bytes_per_value) % self.capacity
        for _ in range(amount):
            byte_block = alarm.sleep_memory[read_head:read_head + self.bytes_per_value]
            read_head = self.increment_modulo_capacity(read_head)
            val = self.decode(byte_block)
            val_list.append(val)
        return val_list


    def empty(self):
        self.tail = self.head
        self.current_size = 0
        self.empty = 1
        self.update_header(only_head_and_tail=True)


    def encode(self, val) -> bytearray:
        # @abstractmethod
        pass


    def decode(self, byte_array: bytearray):
        # @abstractmethod
        pass


    def debug_print(self, max_addr=None):
        if max_addr is None:
            max_addr = self.addr + self.header_size + self.capacity
        sizes = [self.addr_capacity_size, self.addr_bytes_per_value_size, self.addr_head_size, self.addr_tail_size, 1]
        descs = ['capacity', 'bytes per value', 'head', 'tail', 'empty']
        print('adr, val')
        addr = self.addr
        for startup_size, desc in zip(sizes, descs):
            b = alarm.sleep_memory[addr:addr + startup_size]
            print(f'{addr:>3}: {int.from_bytes(b, "big"):<6} {desc}')
            addr += startup_size
        while addr < max_addr:
            b = alarm.sleep_memory[addr:addr + self.bytes_per_value]
            print(f'{addr:>3}: {int.from_bytes(b, "big")}')
            addr += self.bytes_per_value

        print(f'capacity:{self.value_capacity} values ({self.capacity}B) @{self.bytes_per_value}B/value,', end='')
        print(f' {self.tail}->{self.head}, {self.current_size} values')


    def get_last_address(self):
        return self.addr + self.header_size + self.capacity


class Cyclic16BitTempBuffer(CyclicBuffer):
    """
    Cyclic buffer holding temperature values in 16 bit format.

    Temperatures between -40°C and 85°C must be representable with two decimals.
    85.00 - (-40.00) = 125.00

    In theory, the representable range is from -40.00°C to 655.35°C.
    """


    def __init__(self, addr, max_value_capacity):
        self.bytes_per_value = 2
        super().__init__(addr, capacity=max_value_capacity * self.bytes_per_value, bytes_per_value=self.bytes_per_value)


    def encode(self, temp: float) -> bytearray:
        int_val = round((temp + 40.0) * 100.0)
        int_val = max(0, min(int_val, 65535))  # clip to 0..2^16-1
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
        super().__init__(addr, capacity=max_value_capacity * self.bytes_per_value, bytes_per_value=self.bytes_per_value)


    def encode(self, percentage: float) -> bytearray:
        int_val = round(percentage * 100)
        int_val = max(0, min(int_val, 65535))  # clip to 0..2^16-1
        return bytearray(int_val.to_bytes(self.bytes_per_value, 'big'))


    def decode(self, byte_array: bytearray) -> float:
        int_val = int.from_bytes(byte_array, 'big')
        return int_val / 100.0


class SingleIntMemory:

    def __init__(self, addr: int, default_value: int, invalid_value: int = 0, size=2):
        self.addr = addr
        self.invalid_value = invalid_value
        self.size = size
        self.default_value = default_value

        # First read existing value
        self.value = int.from_bytes(alarm.sleep_memory[self.addr:self.addr + self.size], 'big')
        if self.value == self.invalid_value:
            # Assume value has not been written yet
            self.value = self.default_value
            self._write(self.value)


    def _write(self, val: int):
        alarm.sleep_memory[self.addr:self.addr + self.size] = val.to_bytes(self.size, 'big')


    def _read(self):
        value = int.from_bytes(alarm.sleep_memory[self.addr:self.addr + self.size], 'big')
        return value if value != self.invalid_value else None


    def __call__(self, new_value: int = None):
        if new_value is None:
            self.value = self._read()
            return self.value
        else:
            self.value = new_value
            self._write(self.value)
            return self.value


    def get_last_address(self):
        return self.addr + self.size
