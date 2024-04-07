##
## This file is part of the libsigrokdecode project.
##
## Copyright (C) 2011 Gareth McMullin <gareth@blacksphere.co.nz>
## Copyright (C) 2012-2014 Uwe Hermann <uwe@hermann-uwe.de>
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, see <http://www.gnu.org/licenses/>.
##

import sigrokdecode as srd

class SamplerateError(Exception):
    pass

cmd_map = {
    0x00: "CONSOLE PROBE",
    0xFF: "CONSOLE CALIB",
    0x41: "CONSOLE PROBE ORIGIN",
    0x42: "CONSOLE CALIB ORIGIN",
    0x40: "CONSOLE READ INPUT",
    0x54: "CONSOLE KEYBOARD READ",
}

class Decoder(srd.Decoder):
    api_version = 3
    id = 'gamecube'
    name = 'GameCube'
    longname = 'GameCube Controller Protocol'
    desc = 'GameCube Controller protocol'
    license = 'gplv2+'
    inputs = ['logic']
    outputs = []
    tags = ['Sensor']
    channels = (
        {'id': 'data', 'name': 'DATA', 'desc': 'Data'},
    )
    annotations = (
        ('bit', 'Bit'),
        ('byte', 'Byte'),
        ('stop', 'Stop Bit'),
        ('cmd', 'Commands'),
        ('buttons', 'Buttons'),
        ('a_stick', 'Analog Stick'),
        ('c_stick', 'C Stick'),
        ('l_trig', 'Left Trigger'),
        ('r_trig', 'Right Trigger'),
        ('origin1', 'Deadzone 1'),
        ('origin2', 'Deadzone 2'),
        ('warning', 'Warning'),
    )
    annotation_rows = (
        ('bits', 'Bits', (0,)),
        ('bytes', 'Bytes', (1,2)),
        ('cmds', 'Commands', tuple(range(3, 11))),
        ('warnings', 'Warnings', (11,)),
    )

    def __init__(self):
        self.reset()

    def reset(self):
        self.samplerate = None
        self.bits = []
        self.bytes = []
        self.fall = -1
        self.rise = -1

        self.edge_state = "FIND_FALL"
        self.cmd_state = "INITIAL"
        self.current_cmd = None
        self.cmd_read_buf = []
        self.cmd_read_size = -1

    def start(self):
        self.out_ann = self.register(srd.OUTPUT_ANN)

    def metadata(self, key, value):
       if key == srd.SRD_CONF_SAMPLERATE:
            self.samplerate = value

    def putm(self, data):
        self.put(0, 0, self.out_ann, data)

    def checks(self):
        # Check if samplerate is appropriate.
        if self.samplerate < 2000000:
            self.putm([11, ['Sampling rate is too low. Must be above ' +
                            '2MHz for proper overdrive mode decoding.']])
            raise SamplerateError('Sampling rate is too low. Must be above ' +
                            '2MHz for proper overdrive mode decoding.')
        elif self.samplerate < 5000000:
            self.putm([11, ['Sampling rate is suggested to be above 5MHz ' +
                            'for proper overdrive mode decoding.']])

    def display_cmd(self, cmd, start, end):
        cmd_str = f"UNK CMD {cmd:#04x}" if not cmd in cmd_map.keys() else cmd_map[cmd]
        self.put(start, end, self.out_ann, [3, [f"{cmd_str}"]])

    def display_inputs(self):
        self.put(self.bytes[0][1], self.bytes[1][2], self.out_ann, [4, [f"Buttons:{' A' if self.bytes[0][0] & 1 else ''}{' B' if self.bytes[0][0] & 2 else ''}{' X' if self.bytes[0][0] & 4 else ''}{' Y' if self.bytes[0][0] & 8 else ''}{' Start' if self.bytes[0][0] & 0x10 else ''}{' DL' if self.bytes[1][0] & 1 else ''}{' DR' if self.bytes[1][0] & 2 else ''}{' DD' if self.bytes[1][0] & 4 else ''}{' DU' if self.bytes[1][0] & 8 else ''}{' Z' if self.bytes[1][0] & 0x10 else ''}{' R' if self.bytes[1][0] & 0x20 else ''}{' L' if self.bytes[1][0] & 0x40 else ''}"]])
        self.put(self.bytes[2][1], self.bytes[3][2], self.out_ann, [5, [f"X:{self.bytes[2][0] - 128}; Y:{self.bytes[3][0] - 128}"]])
        self.put(self.bytes[4][1], self.bytes[5][2], self.out_ann, [6, [f"X:{self.bytes[4][0] - 128}; Y:{self.bytes[5][0] - 128}"]])
        self.put(self.bytes[6][1], self.bytes[6][2], self.out_ann, [7, [f"L:{self.bytes[6][0]}"]])
        self.put(self.bytes[7][1], self.bytes[7][2], self.out_ann, [8, [f"R:{self.bytes[7][0]}"]])
        if len(self.bytes) >= 10:
            self.put(self.bytes[8][1], self.bytes[8][2], self.out_ann, [9, [f"Deadzone1:{self.bytes[8][0]}"]])
            self.put(self.bytes[9][1], self.bytes[9][2], self.out_ann, [10, [f"Deadzone2:{self.bytes[9][0]}"]])

    def process_next_bit(self, bit, start, end):
        if self.cmd_state in ["WAIT_STOP_BIT", "WAIT_STOP_BIT_READ"]:
            if bit == 1:
                self.cmd_state = "WAIT_RESP_BYTE" if self.cmd_state == "WAIT_STOP_BIT" else "INITIAL"
                self.put(start, end, self.out_ann, [2, ["STOP"]])
                self.put(start, end, self.out_ann, [0, [f"{bit}"]])
                self.bits.clear()
                self.bytes.clear()
        else:
            self.bits.append((bit, start, end))
            self.put(start, end, self.out_ann, [0, [f"{bit}"]])
        if self.cmd_state == "WAIT_RESP_BYTE" and (self.samplenum - self.current_cmd[1]) / self.samplerate >= 0.001:
            self.cmd_state = "INITIAL"
            self.bytes.clear()
        while len(self.bits) >= 8:
            byte = 0
            idx = self.bits[0][1]
            end_idx = self.bits[0][2]
            for i in range(0, 8):
                byte <<= 1
                bit, _, end = self.bits.pop(0)
                byte |= bit
                end_idx = end
            self.bytes.append((byte, idx, end_idx))
            self.put(idx, end_idx, self.out_ann, [1, [f"{byte:#04x}", f"{byte:02x}"]])
        if self.cmd_state == "INITIAL":
            if len(self.bytes) > 0:
                self.current_cmd = self.bytes[0]
                if self.bytes[0][0] in [0x00, 0x41, 0x42, 0xFF]:
                    if len(self.bytes) >= 1:
                        self.cmd_state = "WAIT_STOP_BIT"
                        self.cmd_read_size = 3 if self.bytes[0][0] in [0x00, 0xFF] else 10
                        cmd, cmd_start, cmd_end = self.current_cmd
                        self.display_cmd(cmd, cmd_start, cmd_end)
                        self.bytes.clear()
                elif self.bytes[0][0] == 0x40:
                    if len(self.bytes) >= 3:
                        self.cmd_state = "WAIT_STOP_BIT"
                        self.cmd_read_size = 8
                        cmd, cmd_start, cmd_end = self.current_cmd
                        self.display_cmd(cmd, cmd_start, cmd_end)
                        self.put(self.bytes[2][1], self.bytes[2][2], self.out_ann, [3, [f"Rumble: {'ON' if self.bytes[2][0] & 1 else 'OFF'}"]])
                        self.bytes.clear()
                elif self.bytes[0][0] == 0x54:
                    if len(self.bytes) >= 3:
                        self.cmd_state = "WAIT_STOP_BIT"
                        self.cmd_read_size = 8
                        cmd, cmd_start, cmd_end = self.current_cmd
                        self.display_cmd(cmd, cmd_start, cmd_end)
                        self.bytes.clear()
                else:
                    self.bytes.clear()
        elif self.cmd_state == "WAIT_RESP_BYTE":
            if len(self.bytes) > 0:
                if len(self.bytes) >= self.cmd_read_size:
                    self.cmd_state = "WAIT_STOP_BIT_READ"
                    if self.current_cmd[0] in [0x00, 0xFF]:
                        self.put(self.bytes[0][1], self.bytes[-1][2], self.out_ann, [3, ["PROBE RESPONSE"]])
                    elif self.current_cmd[0] in [0x40, 0x41, 0x42]:
                        self.display_inputs()
                    self.cmd_read_size = -1

    def decode(self):
        if not self.samplerate:
            raise SamplerateError('Cannot decode without samplerate.')
        self.checks()
        while True:
            if self.edge_state == "FIND_FALL":
                self.wait([{0: 'f'}])
                self.fall = self.samplenum
                self.edge_state = "FIND_RISE"
                if self.samplenum - self.rise > 0.00001:
                    self.bits.clear()
            elif self.edge_state == "FIND_RISE":
                self.wait([{0: 'r'}])
                self.rise = self.samplenum
                self.edge_state = "CHECK_RATIO"
            elif self.edge_state == "CHECK_RATIO":
                val, = self.wait()
                if val == 0:
                    # We found the next falling edge
                    if self.samplenum - self.rise < self.rise - self.fall:
                        # Found a 0
                        self.process_next_bit(0, self.fall, self.samplenum)
                    else:
                        self.process_next_bit(1, self.fall, self.samplenum)
                    self.fall = self.samplenum
                    self.edge_state = "FIND_RISE"
                elif self.samplenum - self.rise >= (self.rise - self.fall) * 4:
                    # We waited long enough to know this is a 1
                    self.process_next_bit(1, self.fall, self.samplenum)
                    self.edge_state = "FIND_FALL"
