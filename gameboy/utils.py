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

from typing import List, Callable
from dataclasses import dataclass, field


@dataclass
class AnnFilter:
    start_symbol: str
    end_symbol: str
    func: Callable
    putting: bool = False

    def check(self, read):
        if read.symbol == self.start_symbol:
            self.putting = True

        if self.putting:
            self.func(read)

        if read.symbol == self.end_symbol:
            self.putting = False

@dataclass
class FilterRegistry:
    registered: List[AnnFilter] = field(default_factory=list)

    def register(self, ann_filter: AnnFilter):
        self.registered.push(ann_filter)

    def check(self, read):
        for ann_filter in self.registered:
            ann_filter.check(read)