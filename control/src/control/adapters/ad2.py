"""Digilent Analog Discovery 2 capture adapter.

The AD2 is used as a lightweight dashboard instrument:

* Scope CH1: ChipSHOUTER voltage monitor, rendered as the UI CH3 pulse trace.
* DIO0: ledger trigger/reference marker.
* DIO1: ledger-generated clock.
* DIO2/DIO3: optional target status/UART markers.

The adapter talks directly to Digilent's WaveForms runtime through ``ctypes`` so
Control does not need a Python package beyond the vendor ``libdwf`` runtime.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import threading
import time
from typing import Any, Dict, List, Optional

from control.adapters.base import BaseAdapter


class AD2Adapter(BaseAdapter):
    name = "ad2"

    def __init__(self) -> None:
        self._dwf: Any = None
        self._hdwf = ctypes.c_int(0)
        self._lock = threading.RLock()
        self._last_error: Optional[str] = None
        self._sample_rate_hz = 2_000_000.0
        self._digital_sample_rate_hz = 2_000_000.0
        self._samples = 1200
        self._analog_range_v = 5.0
        self._available = False
        self._load_runtime()

    @property
    def available(self) -> bool:
        return self._available

    @property
    def connected(self) -> bool:
        return bool(self._hdwf.value)

    def connect(self, port: Optional[str] = None) -> None:
        del port
        with self._lock:
            if not self._available or self._dwf is None:
                raise RuntimeError(self._last_error or "Digilent WaveForms runtime is not available")
            if self.connected:
                return
            hdwf = ctypes.c_int(0)
            ok = self._dwf.FDwfDeviceOpen(ctypes.c_int(-1), ctypes.byref(hdwf))
            if not ok or not hdwf.value:
                self._last_error = self._error_message()
                raise RuntimeError(f"AD2 open failed: {self._last_error}")
            self._hdwf = hdwf
            self._last_error = None
            self._configure_instruments()

    def disconnect(self) -> None:
        with self._lock:
            if self._dwf is not None and self.connected:
                self._dwf.FDwfDeviceClose(self._hdwf)
            self._hdwf = ctypes.c_int(0)

    def configure(
        self,
        *,
        sample_rate_hz: Optional[float] = None,
        samples: Optional[int] = None,
        analog_range_v: Optional[float] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            if sample_rate_hz is not None:
                if sample_rate_hz <= 0:
                    raise ValueError("sample_rate_hz must be positive")
                self._sample_rate_hz = float(sample_rate_hz)
            if samples is not None:
                if samples < 64 or samples > 8192:
                    raise ValueError("samples must be between 64 and 8192")
                self._samples = int(samples)
            if analog_range_v is not None:
                if analog_range_v <= 0:
                    raise ValueError("analog_range_v must be positive")
                self._analog_range_v = float(analog_range_v)
            if self.connected:
                self._configure_instruments()
            return self.status()

    def capture(self) -> Dict[str, Any]:
        with self._lock:
            if not self.connected:
                self.connect()

            assert self._dwf is not None
            count = int(self._samples)
            sample_rate = float(self._sample_rate_hz)
            started_at = time.time()

            analog = (ctypes.c_double * count)()
            digital = (ctypes.c_uint16 * count)()

            self._dwf.FDwfAnalogInConfigure(self._hdwf, ctypes.c_bool(False), ctypes.c_bool(True))
            self._dwf.FDwfDigitalInConfigure(self._hdwf, ctypes.c_bool(False), ctypes.c_bool(True))

            analog_status = ctypes.c_byte(0)
            digital_status = ctypes.c_byte(0)
            deadline = time.monotonic() + 1.5
            while time.monotonic() < deadline:
                self._dwf.FDwfAnalogInStatus(self._hdwf, ctypes.c_bool(True), ctypes.byref(analog_status))
                self._dwf.FDwfDigitalInStatus(self._hdwf, ctypes.c_bool(True), ctypes.byref(digital_status))
                if analog_status.value == 2 and digital_status.value == 2:
                    break
                time.sleep(0.002)

            self._dwf.FDwfAnalogInStatusData(self._hdwf, ctypes.c_int(0), analog, ctypes.c_int(count))
            self._dwf.FDwfDigitalInStatusData(
                self._hdwf,
                ctypes.cast(digital, ctypes.c_void_p),
                ctypes.c_int(count * ctypes.sizeof(ctypes.c_uint16)),
            )

            volts = [round(float(analog[i]), 5) for i in range(count)]
            words = [int(digital[i]) for i in range(count)]
            channels = {
                "pulse": {
                    "source": "ad2_scope_ch1",
                    "label": "ChipSHOUTER voltage monitor",
                    "unit": "V",
                    "values": volts,
                },
                "trigger": {
                    "source": "ad2_dio0",
                    "label": "Ledger trigger/ref",
                    "values": self._bit_values(words, 0),
                },
                "clock": {
                    "source": "ad2_dio1",
                    "label": "Ledger clock",
                    "values": self._bit_values(words, 1),
                },
                "status0": {
                    "source": "ad2_dio2",
                    "label": "Optional DIO2 marker",
                    "values": self._bit_values(words, 2),
                },
                "status1": {
                    "source": "ad2_dio3",
                    "label": "Optional DIO3 marker",
                    "values": self._bit_values(words, 3),
                },
            }
            return {
                "name": self.name,
                "available": self.available,
                "connected": self.connected,
                "timestamp": started_at,
                "sample_rate_hz": sample_rate,
                "digital_sample_rate_hz": self._digital_sample_rate_hz,
                "samples": count,
                "duration_s": count / sample_rate,
                "analog_range_v": self._analog_range_v,
                "mapping": {
                    "ui_ch3_pulse": "ad2_scope_ch1",
                    "ui_ch2_trigger": "ad2_dio0",
                    "ui_ch1_clock": "ad2_dio1",
                    "optional_status": ["ad2_dio2", "ad2_dio3"],
                },
                "channels": channels,
            }

    def status(self) -> Dict[str, Any]:
        status = super().status()
        status.update(
            {
                "available": self.available,
                "sample_rate_hz": self._sample_rate_hz,
                "digital_sample_rate_hz": self._digital_sample_rate_hz,
                "samples": self._samples,
                "analog_range_v": self._analog_range_v,
                "mapping": {
                    "scope_ch1": "ChipSHOUTER voltage monitor",
                    "dio0": "ledger trigger/ref",
                    "dio1": "ledger clock",
                    "dio2": "optional marker/UART",
                    "dio3": "optional marker/UART",
                },
            }
        )
        return status

    def _load_runtime(self) -> None:
        path = ctypes.util.find_library("dwf")
        candidates = [path, "libdwf.so", "/usr/lib/libdwf.so", "/usr/lib/x86_64-linux-gnu/libdwf.so"]
        for candidate in candidates:
            if not candidate:
                continue
            try:
                self._dwf = ctypes.cdll.LoadLibrary(candidate)
                self._set_prototypes()
                self._available = True
                self._last_error = None
                return
            except OSError as exc:
                self._last_error = str(exc)
        self._available = False
        if not self._last_error:
            self._last_error = "Digilent WaveForms runtime libdwf.so not found"

    def _set_prototypes(self) -> None:
        assert self._dwf is not None
        self._dwf.FDwfDeviceOpen.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
        self._dwf.FDwfDeviceOpen.restype = ctypes.c_int
        self._dwf.FDwfDeviceClose.argtypes = [ctypes.c_int]
        self._dwf.FDwfDeviceClose.restype = None
        self._dwf.FDwfGetLastErrorMsg.argtypes = [ctypes.c_char_p]
        self._dwf.FDwfGetLastErrorMsg.restype = None
        self._dwf.FDwfAnalogInChannelEnableSet.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_bool]
        self._dwf.FDwfAnalogInChannelRangeSet.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_double]
        self._dwf.FDwfAnalogInFrequencySet.argtypes = [ctypes.c_int, ctypes.c_double]
        self._dwf.FDwfAnalogInBufferSizeSet.argtypes = [ctypes.c_int, ctypes.c_int]
        self._dwf.FDwfAnalogInConfigure.argtypes = [ctypes.c_int, ctypes.c_bool, ctypes.c_bool]
        self._dwf.FDwfAnalogInStatus.argtypes = [ctypes.c_int, ctypes.c_bool, ctypes.POINTER(ctypes.c_byte)]
        self._dwf.FDwfAnalogInStatusData.argtypes = [
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_double),
            ctypes.c_int,
        ]
        self._dwf.FDwfDigitalInInternalClockInfo.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_double)]
        self._dwf.FDwfDigitalInDividerSet.argtypes = [ctypes.c_int, ctypes.c_uint]
        self._dwf.FDwfDigitalInBufferSizeSet.argtypes = [ctypes.c_int, ctypes.c_int]
        self._dwf.FDwfDigitalInSampleFormatSet.argtypes = [ctypes.c_int, ctypes.c_int]
        self._dwf.FDwfDigitalInConfigure.argtypes = [ctypes.c_int, ctypes.c_bool, ctypes.c_bool]
        self._dwf.FDwfDigitalInStatus.argtypes = [ctypes.c_int, ctypes.c_bool, ctypes.POINTER(ctypes.c_byte)]
        self._dwf.FDwfDigitalInStatusData.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_int]

    def _configure_instruments(self) -> None:
        assert self._dwf is not None
        self._dwf.FDwfAnalogInChannelEnableSet(self._hdwf, ctypes.c_int(0), ctypes.c_bool(True))
        self._dwf.FDwfAnalogInChannelRangeSet(self._hdwf, ctypes.c_int(0), ctypes.c_double(self._analog_range_v))
        self._dwf.FDwfAnalogInFrequencySet(self._hdwf, ctypes.c_double(self._sample_rate_hz))
        self._dwf.FDwfAnalogInBufferSizeSet(self._hdwf, ctypes.c_int(self._samples))
        digital_clock_hz = ctypes.c_double(100_000_000.0)
        self._dwf.FDwfDigitalInInternalClockInfo(self._hdwf, ctypes.byref(digital_clock_hz))
        divider = max(1, int(round(digital_clock_hz.value / self._sample_rate_hz)))
        self._digital_sample_rate_hz = digital_clock_hz.value / divider
        self._dwf.FDwfDigitalInDividerSet(self._hdwf, ctypes.c_uint(divider))
        self._dwf.FDwfDigitalInBufferSizeSet(self._hdwf, ctypes.c_int(self._samples))
        self._dwf.FDwfDigitalInSampleFormatSet(self._hdwf, ctypes.c_int(16))

    def _error_message(self) -> str:
        if self._dwf is None:
            return self._last_error or "libdwf.so not loaded"
        buf = ctypes.create_string_buffer(512)
        self._dwf.FDwfGetLastErrorMsg(buf)
        return buf.value.decode(errors="replace") or "unknown WaveForms error"

    @staticmethod
    def _bit_values(words: List[int], bit: int) -> List[int]:
        mask = 1 << bit
        return [1 if (word & mask) else 0 for word in words]
