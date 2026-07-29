"""OpenIOS — fully-local Cisco IOS-like CLI emulator for OpenBoson NetSim.

This is *not* real Cisco IOS. It is an original command-line state machine
that mimics IOS modes, prompts, abbreviations, show output, and common
error messages so labs feel like configuring real gear — without bundling
any Cisco images or copyrighted software.
"""

from openboson.netsim.ios.device import DeviceRuntime, InterfaceState
from openboson.netsim.ios.shell import OpenIOSShell
from openboson.netsim.ios.world import LabWorld

__all__ = ["DeviceRuntime", "InterfaceState", "OpenIOSShell", "LabWorld"]
