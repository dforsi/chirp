#!/usr/bin/python
#
# Copyright 2008 Dan Smith <dsmith@danplanet.com>
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

from chirp import chirp_common, icf, icx8x_ll, errors

def isUHF(pipe):
    md = icf.get_model_data(pipe)
    val = ord(md[20])
    uhf = val & 0x10

    print "Radio is a %s82" % (uhf and "U" or "V")

    return uhf

class ICx8xRadio(icf.IcomCloneModeRadio, chirp_common.IcomDstarSupport):
    VENDOR = "Icom"
    MODEL = "IC-V82/U82"

    _model = "\x28\x26\x00\x01"
    _memsize = 6464
    _endframe = "Icom Inc\x2eCD"

    _memories = []

    _ranges = [(0x0000, 0x1340, 32),
               (0x1340, 0x1360, 16),
               (0x1360, 0x136B,  8),

               (0x1370, 0x1440, 32),

               (0x1460, 0x15D0, 32),

               (0x15E0, 0x1930, 32),

               (0x1938, 0x1940,  8),
               ]

    MYCALL_LIMIT = (0, 6)
    URCALL_LIMIT = (0, 6)
    RPTCALL_LIMIT = (0, 6)

    def get_features(self):
        rf = chirp_common.RadioFeatures()
        rf.memory_bounds = (0, 199)
        rf.valid_modes = ["FM", "NFM", "DV"]
        rf.valid_tmodes = ["", "Tone", "TSQL", "DTCS"]
        rf.valid_duplexes = ["", "-", "+"]
        rf.valid_tuning_steps = [x for x in chirp_common.TUNING_STEPS
                                 if x != 6.25]
        rf.valid_bands = [(118.0, 176.0)]
        rf.valid_skips = ["", "S"]
        return rf

    def _get_type(self):
        flag = (isUHF(self.pipe) != 0)

        if self.isUHF is not None and (self.isUHF != flag):
            raise errors.RadioError("VHF/UHF model mismatch")

        self.isUHF = flag

        return flag

    def __init__(self, pipe):
        icf.IcomCloneModeRadio.__init__(self, pipe)

        # Until I find a better way, I'll stash a boolean to indicate
        # UHF-ness in an unused region of memory.  If we're opening a
        # file, look for the flag.  If we're syncing from serial, set
        # that flag.
        if isinstance(pipe, str):
            self.isUHF = (ord(self._mmap[0x1930]) != 0)
            print "Found %s image" % (self.isUHF and "UHF" or "VHF")
        else:
            self.isUHF = None

    def sync_in(self):
        self._get_type()
        icf.IcomCloneModeRadio.sync_in(self)
        self._mmap[0x1930] = self.isUHF and 1 or 0

    def sync_out(self):
        self._get_type()
        icf.IcomCloneModeRadio.sync_out(self)

    def get_special_locations(self):
        return sorted(icx8x_ll.ICx8x_SPECIAL.keys())

    def get_memory(self, number):
        if not self._mmap:
            self.sync_in()

        if self.isUHF:
            base = 400
        else:
            base = 0

        if isinstance(number, str):
            try:
                number = icx8x_ll.ICx8x_SPECIAL[number]
            except KeyError:
                raise errors.InvalidMemoryLocation("Unknown channel %s" % \
                                                       number)

        return icx8x_ll.get_memory(self._mmap, number, base)

    def set_memory(self, memory):
        if not self._mmap:
            self.sync_in()

        if self.isUHF:
            base = 400
        else:
            base = 0

        if memory.empty:
            self._mmap = icx8x_ll.erase_memory(self._mmap, memory.number)
        else:
            self._mmap = icx8x_ll.set_memory(self._mmap, memory, base)

    def get_raw_memory(self, number):
        return icx8x_ll.get_raw_memory(self._mmap, number)

    def get_banks(self):
        banks = []

        for i in range(0, 10):
            banks.append(chirp_common.ImmutableBank(icx8x_ll.bank_name(i)))

        return banks

    def set_banks(self, banks):
        raise errors.InvalidDataError("Bank naming not supported on this model")

    def get_urcall_list(self):
        calls = []

        for i in range(*self.URCALL_LIMIT):
            call = icx8x_ll.get_urcall(self._mmap, i)
            calls.append(call)

        return calls

    def get_repeater_call_list(self):
        calls = []

        for i in range(*self.RPTCALL_LIMIT):
            call = icx8x_ll.get_rptcall(self._mmap, i)
            calls.append(call)

        return calls

    def get_mycall_list(self):
        calls = []

        for i in range(*self.MYCALL_LIMIT):
            call = icx8x_ll.get_mycall(self._mmap, i)
            calls.append(call)

        return calls

    def set_urcall_list(self, calls):
        for i in range(*self.URCALL_LIMIT):
            try:
                call = calls[i]
            except IndexError:
                call = " " * 8

            icx8x_ll.set_urcall(self._mmap, i, call)

    def set_repeater_call_list(self, calls):
        for i in range(*self.RPTCALL_LIMIT):
            try:
                call = calls[i]
            except IndexError:
                call = " " * 8

            icx8x_ll.set_rptcall(self._mmap, i, call)

    def set_mycall_list(self, calls):
        for i in range(*self.MYCALL_LIMIT):
            try:
                call = calls[i]
            except IndexError:
                call = " " * 8

            icx8x_ll.set_mycall(self._mmap, i, call)
