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

from .symbols import sym
from typing import Dict, List
from dataclasses import dataclass, field, InitVar
from .hardware_constants import HardwareConstant, hardware_const_table

@dataclass
class Instruction:
    opcode: int
    length: int # cycles / 4
    ann: str

tables = [
    # 8 bit loads
    Instruction(opcode=0x3e, length=2, ann='ld a, #'),
    Instruction(opcode=0x7e, length=2, ann='ld a, [hl]'),
    # 16 bit loads
    Instruction(opcode=0x21, length=3, ann='ld hl, nn'),
    # LD n,A. Put value A into n.
    Instruction(opcode=0xea, length=4, ann='ld [nn], a'),

    # Compare a with n, where n = a, b, c, d, e, h, k, hl, #
    # Instruction(opcode=0xbf, length=1, ann='cp a'),
    # Instruction(opcode=0xb8, length=1, ann='cp b'),
    # Instruction(opcode=0xb9, length=1, ann='cp c'),
    # Instruction(opcode=0xba, length=1, ann='cp d'),
    # Instruction(opcode=0xbb, length=1, ann='cp e'),
    # Instruction(opcode=0xbc, length=1, ann='cp h'),
    # Instruction(opcode=0xbd, length=1, ann='cp l'),
    # Instruction(opcode=0xbe, length=2, ann='cp [hl]'),
    Instruction(opcode=0xfe, length=2, ann='cp #'),
    # # Power down CPU until an interrupt occurs. Use this when ever possible to reduce energy consumption.
    # Instruction(opcode=0x76, length=1, ann='halt'),
    # # This instruction disables interrupts but not immediately. Interrupts are disabled after instruction after DI is executed.
    # Instruction(opcode=0xf3, length=1, ann='di'),
    # # Enable interrupts. This intruction enables interrupts but not immediately. Interrupts are enabled after instruction after EI is executed.
    # Instruction(opcode=0xfb, length=1, ann='ei'),
    # Jump to address nn. nn = two byte immediate value. (LS byte first.)
    Instruction(opcode=0xc3, length=3, ann='jp nn'),
    # Jump to address n if following condition is true: 
    # NZ, Jump if Z flag is reset.
    Instruction(opcode=0xc2, length=3, ann='jp NZ, nn'),
    # Z, Jump if Z flag is set.
    Instruction(opcode=0xca, length=3, ann='jp Z, nn'),
    # 0xd2
    # 0xda
    ##
    # 0xe9
    # Add n to current address and jump to it.
    Instruction(opcode=0x18, length=2, ann='jp n'),
    # 0x20
    # 0x28
    # 0x30
    # 0x38
    # Push address of next instruction onto stack and then jump to address nn
    Instruction(opcode=0xcd, length=3, ann='call nn'),
    # 0xc4
    # 0xcc
    # 0xd4
    # 0xdc
    # Push present address onto stack. Jump to address $0000 + n
    Instruction(opcode=0xc7, length=8, ann='rst 0x00'),



]

@dataclass
class Lookups:
    symbols: Dict[int, Dict[int, str]] = field(init=False)
    instructions: Dict[int, Instruction] = field(init=False)
    hardware_const: Dict[int, HardwareConstant] = field(init=False)

    inst_table: InitVar[List[Instruction]]
    raw_symbols: InitVar[str]
    hardware_const_table: InitVar[List[HardwareConstant]]

    def __post_init__(self, inst_table, raw_symbols, hardware_const_table):
        self.instructions = {
            inst.opcode: inst
            for inst in inst_table
        }

        self.symbols = Lookups.process_raw_symbols(raw_symbols)

        self.hardware_const = {
            const.addr: const
            for const in hardware_const_table
        }

    def find_symbol(self, cycle, bank):
        '''
        bank could be SRAM, ROM or any other bank type. They're all in the same symbol table.
        '''
        if cycle.addr in self.symbols:
            if bank in self.symbols[cycle.addr]:
                return self.symbols[cycle.addr][bank]
        return None

    @staticmethod
    def process_raw_symbols(raw_symbols: str) -> dict:
        symbols_raw = sym.split('\n')
        symbols = {}
        for symbol_line in symbols_raw:
            if symbol_line == '':
                continue
            p1 = symbol_line.split(":")
            if len(p1) != 2:
                # error
                print(symbol_line)
                print(p1)
            bank = int(p1[0], 16)
            p2 = p1[1].split(" ")
            addr = int(p2[0], 16)
            symbol = p2[1]
            if addr not in symbols:
                symbols[addr] = {}
            symbols[addr][bank] = symbol
        return symbols

lookups = Lookups(
    inst_table=tables, 
    raw_symbols=sym, 
    hardware_const_table=hardware_const_table
)
print(len(lookups.symbols))
print(len(lookups.instructions))
print(len(lookups.hardware_const))
