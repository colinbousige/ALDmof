#!/usr/bin/env python3

import pyhid_usb_relay

relayboard = pyhid_usb_relay.find()

for i in range(8):
    relayboard[i+1] = True


