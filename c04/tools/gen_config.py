# tools/gen_config.py · 生成 50 箱 config.toml · t_env = 20 + device_id · T_ss = 96 + device_id
N = 50
HEADER = '''# config.toml · v3 多箱版(50 箱) · 由 tools/gen_config.py 生成
[server]
bind = "0.0.0.0"
port = 5020

[loop]
dt_s = 0.1
'''

def box_block(did: int) -> str:
    t_env = float(20 + did)
    def line(key, typ, body):
        typetok = f'"{typ}",'
        return f'{key:<17} = {{ type = {typetok:<29} params = {{ {body} }} }}'
    return "\n".join([
        "[[box]]", f'name = "box-{did}"', f"device_id = {did}",
        line("plant", "thermal", f"temp = 25.0, c_heat = 15.0, eta = 0.95, r_th = 0.40, t_env = {t_env:.1f}"),
        line("sensor", "SimulatedTemperatureSensor", f'name = "t{did}"'),
        line("actuator", "SimulatedHeaterActuator", f'name = "h{did}", channel = "heat_power", max_power = 200.0'),
        line("sensor_endpoint", "ModbusSensorEndpoint", f'name = "tep{did}", register_address = 0'),
        line("actuator_endpoint", "ModbusActuatorEndpoint", f'name = "aep{did}", coil_address = 0'),
    ])

def main():
    parts = [HEADER] + [box_block(d) for d in range(1, N + 1)]
    open("config.toml", "w", encoding="utf-8").write("\n".join(parts) + "\n")
    print(f"已生成 config.toml · {N} 台箱 · box-1=21C ... box-{N}={20+N}C")

if __name__ == "__main__":
    main()
