# core/codec.py · float32 ↔ 2 个 Modbus 寄存器 · big-endian（工业默认）
import struct


def f32_to_regs(v: float) -> list[int]:
    # 给好的范例：float32 → 2 个 16-bit 无符号寄存器（big-endian）
    b = struct.pack(">f", float(v))                  # 4 字节
    return [int.from_bytes(b[0:2], "big"), int.from_bytes(b[2:4], "big")]


def regs_to_f32(regs) -> float:
    # 2 个寄存器 → 4 字节 → float32，顺序必须和 f32_to_regs 完全相反。
    if len(regs) < 2:
        raise ValueError(f"需要 2 个寄存器，实际 {len(regs)}")
    b = int(regs[0]).to_bytes(2, "big") + int(regs[1]).to_bytes(2, "big")
    return struct.unpack(">f", b)[0]
