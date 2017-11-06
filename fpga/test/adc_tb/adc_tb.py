########################################################################
# Copyright (c) 2017 David Caruso <carusodvd@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
########################################################################
# Description
# 
# Testbench for adc with COCOTB!
########################################################################
# Author: David Caruso <carusodvd@gmail.com>
########################################################################

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer, RisingEdge, FallingEdge, Edge, Event
from cocotb.result import TestFailure, TestError, ReturnValue, SimFailure
from cocotb.binary import BinaryValue
import sys
import random
import Image
import pylab as plt
import numpy as np

class ADC:
    def __init__(self, dut):
        self.dut = dut
        self.dut.ch_num_i = 7
        self.dut.dout_i = 1
        self.dut.rst_i = 1
        self.dut.auto_inc_i = 0
        self.dut.start_i = 0
        self.ch_val = np.random.randint(1<<12, size=(1, 8))
        # self.ch_val = [[4094,4094,4094,4094,4094,4094,4094,4094]]

    @cocotb.coroutine
    def reset(self):
        self.dut.rst_i = 1
        for i in range(10):
            yield RisingEdge(self.dut.clk_i)
        self.dut.rst_i = 0
        yield RisingEdge(self.dut.clk_i)

    def read_channel(self, channel):
        self.xd = np.random.randint(14)
        self.yd = np.random.randint(14)
        self.xp = self.xp + self.xd
        self.yp = self.yp + self.yd

    @cocotb.coroutine
    def conversion_monitor(self, e):
        while True:
            self.dut._log.info("* Start")
            yield RisingEdge(self.dut.valid_o)
            e.set()
            self.dut._log.info("* Detect end")

    @cocotb.coroutine
    def start_convertion(self, channel):
        self.dut.ch_num_i = channel
        yield RisingEdge(self.dut.clk_i)
        self.dut.start_i = 1
        yield RisingEdge(self.dut.clk_i)
        self.dut.start_i = 0

    @cocotb.coroutine
    def spi_slave(self):
        while True:
            data_out = 0
            channel = 0
            self.dut.dout_i = 1
            yield FallingEdge(self.dut.ncs_o)
            self.dut.dout_i = 0
            for i in range(16):
                bit = 15-i
                yield FallingEdge(self.dut.sclk_o)
                channel = channel*2 + self.dut.din_o.value.integer
                if (i==4):
                    self.dut._log.info("> Channel to read: {}, value: {}".format(channel, self.ch_val[0][channel]))
                    data_out = self.ch_val[0][channel]
                self.dut.dout_i = (data_out&(1<<bit))/(1<<bit)
            yield RisingEdge(self.dut.ncs_o)

@cocotb.test()
def test(dut):
    dut._log.info("> Starting Test")
    cocotb.fork(Clock(dut.clk_i, 20, units='ns').start())
    adc_dev = ADC(dut)
    cocotb.fork(adc_dev.spi_slave())
    conversion_end = Event("conversion_monitor")
    cocotb.fork(adc_dev.conversion_monitor(conversion_end))
    yield adc_dev.reset()
    for i in range(10):
        ch_list = list(range(8))
        random.shuffle(ch_list)
        for ch in ch_list:
            dut._log.info("> (Test ADC) Random Channel reading: {}".format(ch))
            yield adc_dev.start_convertion(ch)
            yield conversion_end.wait()
            if (adc_dev.ch_val[0][ch] != dut.data_an_o.value.integer):
                dut._log.error("> (Test ADC) ADC reference: {}, receiver: {}".format(adc_dev.ch_val[0][ch], dut.data_an_o.value.integer))
                raise TestFailure("> (Test ADC) Error!")
            yield RisingEdge(dut.clk_i)
            yield RisingEdge(dut.clk_i)
            yield RisingEdge(dut.clk_i)
            yield RisingEdge(dut.clk_i)

        dut._log.info("> Ok")
    dut._log.info("> End of test!")
