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
    0x00: "PROBE",
    0x14: "READ GBA",
    0x15: "WRITE GBA",
    0x40: "STATUS",
    0x41: "ORIGIN",
    0x42: "CALIBRATE",
    0x43: "STATUS LONG",
    0x54: "KEYBOARD READ",
    0xFF: "RESET",
}

motor_modes = {
    0: "OFF",
    1: "ON",
    2: "BREAK",
    3: "UNK"
}

controller_types = {
    0: "N64",
    1: "GC",
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
        ('resp', 'Responses'),
        ('warning', 'Warning'),
    )
    annotation_rows = (
        ('bits', 'Bits', (0,)),
        ('bytes', 'Bytes', (1,2)),
        ('cmds', 'Commands', (3,4)),
        ('warnings', 'Warnings', (5,)),
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
        self.poll_mode = 0

    def start(self):
        self.out_ann = self.register(srd.OUTPUT_ANN)

    def metadata(self, key, value):
       if key == srd.SRD_CONF_SAMPLERATE:
            self.samplerate = value

    def putm(self, data):
        self.put(0, self.samplenum, self.out_ann, data)

    def checks(self):
        # Check if samplerate is appropriate.
        if self.samplerate < 2000000:
            self.putm([5, ['Sampling rate is too low. Must be above ' +
                            '2MHz for proper overdrive mode decoding.']])
            raise SamplerateError('Sampling rate is too low. Must be above ' +
                            '2MHz for proper overdrive mode decoding.')
        elif self.samplerate < 5000000:
            self.putm([5, ['Sampling rate is suggested to be above 5MHz ' +
                            'for proper overdrive mode decoding.']])

    def display_cmd(self, cmd, start, end):
        cmd_str = f"UNK CMD {cmd:#04x}" if not cmd in cmd_map.keys() else cmd_map[cmd]
        self.put(start, end, self.out_ann, [3, [f"{cmd_str}"]])

    def display_inputs(self):
        b_A = 'A' if self.bytes[0][0] & 1 else ''
        b_B = 'B' if self.bytes[0][0] & 2 else ''
        b_X = 'X' if self.bytes[0][0] & 4 else ''
        b_Y = 'Y' if self.bytes[0][0] & 8 else ''
        b_Start = 'S' if self.bytes[0][0] & 0x10 else ''
        b_DL = 'L' if self.bytes[1][0] & 1 else ''
        b_DR = 'R' if self.bytes[1][0] & 2 else ''
        b_DD = 'D' if self.bytes[1][0] & 4 else ''
        b_DU = 'U' if self.bytes[1][0] & 8 else ''
        b_Z = 'Z' if self.bytes[1][0] & 0x10 else ''
        b_R = 'Rt' if self.bytes[1][0] & 0x20 else ''
        b_L = 'Lt' if self.bytes[1][0] & 0x40 else ''
        self.put(self.bytes[0][1], self.bytes[1][2], self.out_ann, [4, [f"Buttons: {b_A}{b_B}{b_X}{b_Y}{b_Start}{b_DL}{b_DR}{b_DD}{b_DU}{b_Z}{b_R}{b_L}", f"{b_A}{b_B}{b_X}{b_Y}{b_Start}{b_DL}{b_DR}{b_DD}{b_DU}{b_Z}{b_R}{b_L}"]])
        self.put(self.bytes[2][1], self.bytes[2][2], self.out_ann, [4, [f"Analog X: {self.bytes[2][0] - 128}", f"A-X:{self.bytes[2][0] - 128}", f"{self.bytes[2][0] - 128}"]])
        self.put(self.bytes[3][1], self.bytes[3][2], self.out_ann, [4, [f"Analog Y: {self.bytes[3][0] - 128}", f"A-Y:{self.bytes[3][0] - 128}", f"{self.bytes[3][0] - 128}"]])
        self.put(self.bytes[4][1], self.bytes[4][2], self.out_ann, [4, [f"C-Stick X: {self.bytes[4][0] - 128}", f"C-X:{self.bytes[4][0] - 128}", f"{self.bytes[4][0] - 128}"]])
        self.put(self.bytes[5][1], self.bytes[5][2], self.out_ann, [4, [f"C-Stick Y: {self.bytes[5][0] - 128}", f"C-Y:{self.bytes[5][0] - 128}", f"{self.bytes[5][0] - 128}"]])
        self.put(self.bytes[6][1], self.bytes[6][2], self.out_ann, [4, [f"L:{self.bytes[6][0]}", f"{self.bytes[6][0]}"]])
        self.put(self.bytes[7][1], self.bytes[7][2], self.out_ann, [4, [f"R:{self.bytes[7][0]}", f"{self.bytes[7][0]}"]])
        if len(self.bytes) >= 10:
            self.put(self.bytes[8][1], self.bytes[8][2], self.out_ann, [4, [f"Origin X: {self.bytes[8][0]}", f"X:{self.bytes[8][0]}", f"{self.bytes[8][0]}"]])
            self.put(self.bytes[9][1], self.bytes[9][2], self.out_ann, [4, [f"Origin Y: {self.bytes[9][0]}", f"Y:{self.bytes[9][0]}", f"{self.bytes[9][0]}"]])

    def display_probe_resp(self):
        [byte0, byte1, byte2] = [b[0] for b in self.bytes]
        wireless_state = "Fixed " if byte0 & 0x02 else "Variable "
        wireless_rx = 'Bidirectional ' if byte0 & 0x40 else '' # Supports Wireless reception of data to the controller
        wireless = f'Wireless {wireless_state}{wireless_rx}' if byte0 & 0x80 else 'Wired '
        motor = ' with Rumble' if not byte0 & 0x20 else ''
        controller_type_id = (byte0 >> 3) & 3
        standard = f'{"Non-" if not byte0 & 1 else ""}Standard '
        controller_type = f'Unknown ({controller_type_id:#04x})' if not controller_type_id in controller_types.keys() else controller_types[controller_type_id] + ' '
        self.put(self.bytes[0][1], self.bytes[1][2], self.out_ann, [4, [f"{standard}{wireless}{controller_type}Controller{motor}", f"{standard}{controller_type}{motor}", f"{controller_type}{motor}", f"{controller_type}"]])
        if controller_type_id == 1:
            err = byte2 & 0x80
            err_latch = byte2 & 0x40
            origin_not_sent = byte2 & 0x20
            rumble_mode = (byte2 & 0x18) >> 3
            poll_mode = (byte2 & 0x07)
            self.poll_mode = poll_mode
            self.put(self.bytes[2][1], self.bytes[2][2], self.out_ann, [4, [f"{'Had ERR;' if err else ''}{'ERR;' if err_latch else ''}{'Origin Missing;' if origin_not_sent else ''}Rumble mode:{motor_modes[rumble_mode]};Poll mode:{poll_mode}", f"Rumble:{rumble_mode};Poll:{poll_mode}", f"R:{rumble_mode};P:{poll_mode}"]])

    def process_next_bit(self, bit, start, end):
        if self.cmd_state in ["WAIT_STOP_BIT", "WAIT_STOP_BIT_READ"]:
            if bit == 1:
                self.cmd_state = "WAIT_RESP_BYTE" if self.cmd_state == "WAIT_STOP_BIT" else "INITIAL"
                self.put(start, end, self.out_ann, [0, [f"{bit}"]])
                self.put(start, end, self.out_ann, [2, ["STOP Bit", "STOP"]])
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
                if self.bytes[0][0] in [0x00, 0x41, 0x42, 0x43, 0xFF]:
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
                        self.put(self.bytes[1][1], self.bytes[1][2], self.out_ann, [3, [f"Mode: {self.bytes[1][0] & 0b111:#04x}"]])
                        self.put(self.bytes[2][1], self.bytes[2][2], self.out_ann, [3, [f"Rumble: {motor_modes[self.bytes[2][0] & 3]}", f"{motor_modes[self.bytes[2][0] & 3]}"]])
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
                        self.display_probe_resp()
                    elif self.current_cmd[0] in [0x40, 0x41, 0x42, 0x43]:
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
                        # Found a 1
                        self.process_next_bit(1, self.fall, self.samplenum)
                    self.fall = self.samplenum
                    self.edge_state = "FIND_RISE"
                elif self.samplenum - self.rise >= (self.rise - self.fall) * 4:
                    # We waited long enough to know this is a 1
                    self.process_next_bit(1, self.fall, self.samplenum)
                    self.edge_state = "FIND_FALL"
