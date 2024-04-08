##
## This file is part of the libsigrokdecode project.
##
## Copyright (C) 2012 Uwe Hermann <uwe@hermann-uwe.de>
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

'''
This decoder decodes the Nintendo Gamecube controller protocol.

Details:
https://www.int03.co.uk/crema/hardware/gamecube/gc-control.html
https://simplecontrollers.com/blogs/resources/gamecube-protocol
https://github.com/extremscorner/gba-as-controller/blob/gc/controller/source/main.iwram.c#L264
'''

from .pd import Decoder
