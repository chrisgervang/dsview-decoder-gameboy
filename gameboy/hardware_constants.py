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

from typing import List, Dict
from dataclasses import dataclass, field, InitVar

@dataclass
class HardwareConstantData:
    ann: str
    data: int # i.e. SRamEnableData

@dataclass
class HardwareConstant:
    ann: str
    addr: int
    data_list: InitVar[List[HardwareConstantData]] = None

    data: Dict[int, HardwareConstantData] = field(default_factory=dict)

    def __post_init__(self, data_list):
        if data_list:
            self.data = {
                item.data: item
                for item in data_list
            }
        
# Graciously aped from:
# http://nocash.emubase.de/pandocs.htm
# http://gameboy.mongenel.com/dmg/asmmemmap.html

hardware_const_table = [
    HardwareConstant("MBC3SRamEnable", 0x0000, [
        HardwareConstantData("SRAM_ENABLE", 0x0a), 
        HardwareConstantData("SRAM_DISABLE", 0x00)]),
    HardwareConstant("MBC3RomBank", 0x2000),
    HardwareConstant("MBC3SRamBank", 0x4000),
    HardwareConstant("MBC3LatchClock", 0x6000, [
        HardwareConstantData("LATCH_CLOCK", 0x01), 
        HardwareConstantData("RESET_LATCH", 0x00)]),
    HardwareConstant("MBC3RTC", 0xa000)
]
