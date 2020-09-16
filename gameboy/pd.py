##
## Copyright (c) 2020 Chris Gervang

## Permission is hereby granted, free of charge, to any person obtaining a copy
## of this software and associated documentation files (the "Software"), to deal
## in the Software without restriction, including without limitation the rights
## to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
## copies of the Software, and to permit persons to whom the Software is
## furnished to do so, subject to the following conditions:

## The above copyright notice and this permission notice shall be included in all
## copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
## IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
## FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
## AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
## LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
## OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
## SOFTWARE.
##

import sigrokdecode as srd
from functools import reduce
from dataclasses import dataclass, field, InitVar
from .lookups import lookups, Lookups, Instruction
from typing import List
from .utils import AnnFilter
from .hardware_constants import HardwareConstant

class Mode:
    NONE = 0
    READ_ROM0, READ_ROMX = 1, 2
    READ_SRAM, WRITE_SRAM = 3, 4
    READ_WRAM0, READ_WRAMX = 5, 6
    SWITCH_ROM_BANK, SWITCH_WRAM_BANK = 7, 8

class Ann:
    ADDR, RD, WR, SYM, WR_FUNC, CODE, CONST, ROM_BANK, SRAM_BANK = 0, 1, 2, 3, 4, 5, 6, 7, 8

class Match:
    START_READ, START_WRITE = 0b01, 0b10

class Addr:
    '''
    $FFFF	Interrupt Enable Flag
    $FF80-$FFFE	Zero Page - 127 bytes
    $FF00-$FF7F	Hardware I/O Registers
    $FEA0-$FEFF	Unusable Memory
    $FE00-$FE9F	OAM - Object Attribute Memory
    $E000-$FDFF	Echo RAM - Reserved, Do Not Use

    $D000-$DFFF	Internal RAM - Bank 1-7 (switchable - CGB only)
    $C000-$CFFF	Internal RAM - Bank 0 (fixed)

    $A000-$BFFF	Cartridge RAM (If Available)
    $9C00-$9FFF	BG Map Data 2
    $9800-$9BFF	BG Map Data 1
    $8000-$97FF	Character RAM

    $4000-$7FFF	Cartridge ROM - Switchable Banks 1-xx
    $0150-$3FFF	Cartridge ROM - Bank 0 (fixed)
    $0100-$014F	Cartridge Header Area
    $0000-$00FF	Restart and Interrupt Vectors
    '''
    ROM0_START, ROM0_END = 0x0150, 0x3FFF
    ROMX_START, ROMX_END = 0x4000, 0x7FFF
    SRAM_START, SRAM_END = 0xA000, 0xBFFF

class Pin:
    CLK, RD, WR, CS = range(4)
    A0, A15 = 4, 19
    D0, D1, D2, D3, D4, D5, D6, D7 = range(20, 28)

def reduce_bus(bus):
    if 0xFF in bus:
        return None # unassigned bus channels
    else:
        return reduce(lambda a, b: (a << 1) | b, reversed(bus))


class ReadState:
    INIT, INCOMPLETE, COMPLETE = 0, 1, 2

class CycleType:
    UNKNOWN, DATA, OPCODE = 0, 1, 2

@dataclass
class Cycle:
    sample: int

    pins: InitVar[list]

    addr: int = field(init=False)
    data: int = field(init=False)
    cycle_type: int = CycleType.UNKNOWN # CycleType
    
    def __post_init__(self, pins):
        self.addr = reduce_bus(pins[Pin.A0:Pin.A15+1])
        self.data = reduce_bus(pins[Pin.D0:Pin.D7+1])

@dataclass
class Write:
    # generic
    start_sample: int
    pins: InitVar[int]

    # write-specific
    sram_bank: InitVar[int]
    lookups: InitVar[Lookups]

    cycle: Cycle = field(init=False)
    mode: int = field(init=False) # Mode
    end_sample: int = field(init=False)

    symbol: str = None

    # write-specific
    hardware_const: HardwareConstant = None
    
    cycle_count: int = 0

    def __post_init__(self, pins, sram_bank: int, lookups: Lookups):
        self.cycle = Cycle(pins=pins, sample=self.start_sample)
        if Addr.SRAM_START <= self.cycle.addr <= Addr.SRAM_END:
            self.mode = Mode.WRITE_SRAM
            self.cycle.cycle_type = CycleType.DATA
            self.symbol = lookups.find_symbol(self.cycle, sram_bank)

        if self.cycle.addr in lookups.hardware_const:
            self.hardware_const = lookups.hardware_const[self.cycle.addr]


    def end(self, end_sample):
        self.end_sample = end_sample

    def get_ann_hardware_const_data(self):
        return self.hardware_const.data[self.cycle.data].ann

    def is_sram_bank_switch(self):
        if self.hardware_const and self.hardware_const.addr == 0x4000:
            return True
        return False

    def is_rom_bank_switch(self):
        if self.hardware_const and self.hardware_const.addr == 0x2000:
            return True
        return False

@dataclass
class Read:
    # generic
    start_sample: int
    pins: InitVar[int]

    # read-specific
    rom_bank: InitVar[int]
    lookups: InitVar[Lookups]

    cycles: List[Cycle] = field(default_factory=list)
    mode: int = field(init=False) # Mode
    end_sample: int = field(init=False)

    symbol: str = None

    # read-specific
    instruction: Instruction = None
    state: int = ReadState.INIT
    special_ann: str = None

    cycle_count: int = 0
    
    def __post_init__(self, pins, rom_bank: int, lookups: Lookups):
        cycle = Cycle(pins=pins, sample=self.start_sample)
        if Addr.ROM0_START <= cycle.addr <= Addr.ROM0_END:
            self.mode = Mode.READ_ROM0
            self.init_rom(cycle, lookups, 0x0)
        elif Addr.ROMX_START <= cycle.addr <= Addr.ROMX_END:
            self.mode = Mode.READ_ROMX
            # TODO: assign MCB mode. For now 03 has what I want.
            self.init_rom(cycle, lookups, rom_bank)
        else:
            cycle.cycle_type = CycleType.UNKNOWN
            self.state = ReadState.COMPLETE
  

        self.cycles.append(cycle)


    def init_rom(self, cycle: Cycle, lookups, rom_bank: int):
        self.symbol = lookups.find_symbol(cycle, rom_bank)

        # 
        self.state = ReadState.COMPLETE
        if cycle.data in lookups.instructions:
            self.instruction = lookups.instructions[cycle.data]
            cycle.cycle_type = CycleType.OPCODE
            if self.instruction.length != 1:
                self.state = ReadState.INCOMPLETE
        self.cycle_count = 1

    def next(self, pins, sample: int):
        cycle = Cycle(pins=pins, sample=sample)
        cycle.cycle_type = CycleType.DATA
        self.cycles.append(cycle)
        self.cycle_count += 1
        if self.cycle_count == self.instruction.length:
            self.state = ReadState.COMPLETE
    
    def end(self, end_sample, sram_bank=0x00):
        if self.instruction and self.instruction.opcode in [0x21, 0xc2, 0xc3, 0xca, 0xcd, 0xea]:
            # call nn or jp nn
            addr = (self.cycles[2].data << 0b1000) + self.cycles[1].data
            if addr in lookups.symbols:
                # only supports sram symbols for these parameter annotations right now.
                if sram_bank in lookups.symbols[addr]:
                    self.special_ann = f'{self.instruction.ann} ({lookups.symbols[addr][sram_bank]})'
        self.end_sample = end_sample

    def get_instruction_ann(self):
        return self.special_ann if self.special_ann is not None else self.instruction.ann

    def get_sub_end_sample(self, idx):
        return self.cycles[idx+1].sample if idx < len(self.cycles) - 1 else self.end_sample



class Decoder(srd.Decoder):
    api_version = 3
    id       = 'gbc'
    name     = 'Gameboy'
    longname = 'Nintendo Gameboy Color'
    desc     = 'Nintendo Gameboy microprocessor disassembly.'
    license  = 'mit'
    inputs   = ['logic']
    outputs  = []
    tags     = ['Retro computing', 'Gaming']
    channels = (
        {'id': 'clk', 'name': '/CLK', 'desc': 'Clock'},
        {'id': 'rd', 'name': '/RD', 'desc': 'Bus read'},
        {'id': 'wr', 'name': '/WR', 'desc': 'Bus write'},
        {'id': 'cs', 'name': '/CS', 'desc': 'Chip select'}
    ) + tuple({
        'id': 'a%d' % i,
        'name': 'A%d' % i,
        'desc': 'Address bus line %d' % i
        } for i in range(16)
    ) + tuple(
        {
        'id': 'd%d' % i,
        'name': 'D%d' % i,
        'desc': 'Data bus line %d' % i
        } for i in range(8)
    )

    annotations = (
        ('addr',  'Address'),
        ('sym',  'Symbol'),
        ('wr_func', 'Write Function'),
        ('rd',  'Byte read'),
        ('wr',  'Byte written'),
        ('code', 'Code'),
        ('const', 'Constant'),
        ('rom_bank', 'ROM Bank'),
        ('sram_bank', 'SRAM Bank')
    )
    annotation_rows = (
        ('addrbus', 'Address bus', (Ann.ADDR,)),
        ('symbol', 'Symbol', (Ann.SYM, Ann.WR_FUNC)),
        ('databus', 'Data bus', (Ann.RD, Ann.WR)),
        ('code', 'Code', (Ann.CODE, Ann.CONST)),
        ('rom_bank', 'ROM Bank', (Ann.ROM_BANK,)),
        ('sram_bank', 'SRAM Bank', (Ann.SRAM_BANK,)),
    )

    def __init__(self):
        self.reset()

    def reset(self):
        self.prev_read  = None
    
    def start(self):
        self.out_ann    = self.register(srd.OUTPUT_ANN)        
        self.samplenum  = None

        # self.pend_addr  = None
        # self.pend_data  = None

        self.prev_read  = None
        self.prev_write  = None
        self.prev_rom_bank = None
        self.prev_sram_bank = None

        self.print_player_step = AnnFilter(
            start_symbol="UpdatePlayerCoords",
            end_symbol="_HandlePlayerStep.finish",
            func=self.print_read
        )

    def print_read(self, read):
        for idx, cycle in enumerate(read.cycles):
            end_sample = read.get_sub_end_sample(idx)
            self.put(cycle.sample, end_sample, self.out_ann, [Ann.ADDR, ['{:04X}'.format(cycle.addr)]])
            self.put(cycle.sample, end_sample, self.out_ann, [Ann.RD, ['{:02X}'.format(cycle.data)]])
        if read.symbol:
            self.put(read.start_sample, read.end_sample, self.out_ann, [Ann.SYM, [read.symbol]])
        # else:
        #     self.put(read.start_sample, read.end_sample, self.out_ann, [Ann.SYM, ['']])

        if read.instruction:
            ann = read.get_instruction_ann()
            self.put(read.start_sample, read.end_sample, self.out_ann, [Ann.CODE, [ann]])
        # else: 
        #     self.put(read.start_sample, read.end_sample, self.out_ann, [Ann.CODE, ['']])

    def read(self, pins):
        rom_bank = self.prev_rom_bank['bank'] if self.prev_rom_bank else 0x00
        if self.prev_read is None:
            self.prev_read = Read(pins=pins, start_sample=self.samplenum, rom_bank=rom_bank, lookups=lookups)
        elif self.prev_read.state == ReadState.INCOMPLETE:
            self.prev_read.next(pins=pins, sample=self.samplenum)
        elif self.prev_read.state == ReadState.COMPLETE:
            self.end_read()
            self.prev_read = Read(pins=pins, start_sample=self.samplenum, rom_bank=rom_bank, lookups=lookups)

    def end_read(self):
        sram_bank = self.prev_sram_bank['bank'] if self.prev_sram_bank else 0x00
        if self.prev_read:
            self.prev_read.end(self.samplenum, sram_bank)
            self.print_player_step.check(self.prev_read)
            self.prev_read = None

    def switch_sram(self, write):
        if self.prev_sram_bank:
            self.put(self.prev_sram_bank['start_sample'], self.samplenum, self.out_ann, [Ann.SRAM_BANK, [self.prev_sram_bank['ann']]])

        self.prev_sram_bank = {
            'start_sample': self.samplenum,
            'end_sample': None,
            'bank': write.cycle.data,
            'ann': 'SRAM Bank: {:02X}'.format(write.cycle.data)
        }

    def switch_rom(self, write):
        if self.prev_rom_bank:
            self.put(self.prev_rom_bank['start_sample'], self.samplenum, self.out_ann, [Ann.ROM_BANK, [self.prev_rom_bank['ann']]])

        self.prev_rom_bank = {
            'start_sample': self.samplenum,
            'end_sample': None,
            'bank': write.cycle.data,
            'ann': 'ROM Bank: {:02X}'.format(write.cycle.data)
        }

    def write(self, pins):
        if self.prev_write:
            self.end_write()
        sram_bank = self.prev_sram_bank['bank'] if self.prev_sram_bank else 0x00
        self.prev_write = Write(pins=pins, start_sample=self.samplenum, sram_bank=sram_bank, lookups=lookups)
        if self.prev_write.is_rom_bank_switch():
            self.switch_rom(self.prev_write)
        elif self.prev_write.is_sram_bank_switch():
            self.switch_sram(self.prev_write)   

    def end_write(self):
        write = self.prev_write

        if write:
            write.end(self.samplenum)
            if self.print_player_step.putting:
                self.put(
                    write.start_sample, 
                    write.end_sample, 
                    self.out_ann, [Ann.ADDR, ['{:04X}'.format(write.cycle.addr)]]
                )
                self.put(
                    write.start_sample, 
                    write.end_sample, 
                    self.out_ann, [Ann.WR, ['{:02X}'.format(write.cycle.data)]]
                )

                if write.symbol:
                    self.put(write.start_sample, write.end_sample, self.out_ann, [Ann.SYM, [write.symbol]])
                elif write.hardware_const:
                    self.put(
                        write.start_sample, 
                        write.end_sample, 
                        self.out_ann, [Ann.WR_FUNC, [write.hardware_const.ann]]
                    )

                    if write.cycle.data in write.hardware_const.data:
                        ann = write.get_ann_hardware_const_data()
                        self.put(write.start_sample, write.end_sample, self.out_ann, [Ann.CONST, [ann]])
                    # else:
                    #     self.put(write.start_sample, write.end_sample, self.out_ann, [Ann.CONST, ['']])

                # else:
                #     self.put(write.start_sample, write.end_sample, self.out_ann, [Ann.WR_FUNC, ['']])
                #     self.put(write.start_sample, write.end_sample, self.out_ann, [Ann.CONST, ['']])

            self.prev_write = None

    def decode(self):
        while True:
            (clk, rd, wr, cs, a0, a1, a2, a3, a4, a5, a6, a7, a8, a9, a10, a11, a12, a13, a14, a15, d0, d1, d2, d3, d4, d5, d6, d7) = self.wait([
                {Pin.CLK: 'f', Pin.RD: 'l', Pin.WR: 'h'}, # READ INIT
                {Pin.CLK: 'f', Pin.RD: 'h', Pin.WR: 'f'} # WRITE INIT
            ])
            
            pins = (clk, rd, wr, cs, a0, a1, a2, a3, a4, a5, a6, a7, a8, a9, a10, a11, a12, a13, a14, a15, d0, d1, d2, d3, d4, d5, d6, d7)

            if self.matched == Match.START_READ:
                self.end_write()
                self.read(pins)
            elif self.matched == Match.START_WRITE:
                self.end_read()
                self.write(pins)
