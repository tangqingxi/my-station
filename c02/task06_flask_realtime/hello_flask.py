# -*- coding: utf-8 -*-
import threading
import time
from flask import Flask, jsonify, render_template_string, request

# ===== 物理参数(单节点)=====
c_heat       = 15.0      # 热容
eta          = 0.95      # 加热效率
r_th         = 0.40      # 对环境热阻
t_env        = 25.0      # 环境温度
DT           = 1.0       # 仿真步长 s
HEATER_POWER = 200.0     # 加热器额定 W

def step_euler(temp, power, dt):
    loss   = (temp - t_env) / r_th             # 向环境散热
    d_temp = (eta * power - loss) / c_heat     # 净功率 / 热容 = 升温率
    return temp + dt * d_temp

app   = Flask(__name__)
state = {
    "t":          0.0,
    "temp":       t_env,
    "heater_on":  False,           # ★ 新增
    "heat_power": 0.0,             # ★ 新增
}
state_lock = threading.Lock()

def simulation_loop():
    while True:
        with state_lock:
            power = HEATER_POWER if state["heater_on"] else 0.0   # ★ 按开关给功率
            state["temp"]       = step_euler(state["temp"], power, DT)
            state["heat_power"] = power               # ★ 存功率
            state["t"] += DT
        time.sleep(DT)

@app.route("/api/state")
def api_state():
    with state_lock:
        return jsonify(dict(state))

@app.route("/api/heater", methods=["POST"])   # ★ 新增 POST 路由
def api_heater():
    data = request.get_json() or {}
    with state_lock:
        state["heater_on"] = bool(data.get("on", False))
    return jsonify({"ok": True})

@app.route("/")
def index():
    return render_template_string('''<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>温控器</title></head>
<body>
<h1>温度 <span id="t">--</span> °C</h1>
<button id="heater-btn" style="padding:20px 30px;font-size:16px;">按住加热</button>
<script>
const btn = document.getElementById("heater-btn");
const post = on => fetch("/api/heater", {
    method:  "POST",
    headers: {"Content-Type": "application/json"},
    body:    JSON.stringify({on}),
});
btn.addEventListener("mousedown",  () => post(true));
btn.addEventListener("mouseup",    () => post(false));
btn.addEventListener("mouseleave", () => post(false));

setInterval(async () => {
  const d = await (await fetch("/api/state")).json();
  document.getElementById("t").textContent = d.temp.toFixed(1);
}, 500);
</script>
</body>
</html>''')

if __name__ == "__main__":
    threading.Thread(target=simulation_loop, daemon=True).start()
    app.run(host="127.0.0.1", port=5000, use_reloader=False)