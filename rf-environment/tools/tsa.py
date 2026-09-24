"""Minimal tinySA shell driver (COM17 only; COM3 is an unrelated device)."""
import sys, time, serial

PORT = "COM17"
PROMPT = b"ch> "


class TinySA:
    def __init__(self, port=PORT):
        if port.upper() == "COM3":
            raise SystemExit("refusing COM3")
        self.s = serial.Serial(port, 115200, timeout=0.5)
        self.s.reset_input_buffer()
        self.s.write(b"\r")
        self._read_until_prompt(5)

    def _read_until_prompt(self, timeout):
        buf = b""
        end = time.time() + timeout
        while time.time() < end:
            chunk = self.s.read(self.s.in_waiting or 1)
            if chunk:
                buf += chunk
                if buf.endswith(PROMPT):
                    return buf
        raise TimeoutError(f"no prompt; got {buf[-200:]!r}")

    def cmd(self, line, timeout=10):
        self.s.reset_input_buffer()
        self.s.write(line.encode() + b"\r")
        raw = self._read_until_prompt(timeout)
        text = raw.decode(errors="replace").replace("\r", "")
        lines = text.split("\n")
        # drop echoed command and trailing prompt
        if lines and lines[0].strip() == line.strip():
            lines = lines[1:]
        if lines and lines[-1].startswith("ch>"):
            lines = lines[:-1]
        return "\n".join(lines)

    def scan(self, start, stop, points=290, timeout=600):
        """Return list of (freq_hz, dbm)."""
        out = self.cmd(f"scan {int(start)} {int(stop)} {points} 3", timeout=timeout)
        res = []
        for ln in out.split("\n"):
            p = ln.split()
            if len(p) >= 2:
                try:
                    res.append((float(p[0]), float(p[1])))
                except ValueError:
                    pass
        return res

    def close(self):
        self.s.close()


if __name__ == "__main__":
    t = TinySA()
    for c in sys.argv[1:]:
        print(f"--- {c}")
        print(t.cmd(c))
    t.close()
