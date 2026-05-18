# -*- coding: utf-8 -*-
"""
无风扇温度箱 · Flask 实时仿真界面（双容模型）
===============================================
基于 no_fan_euler.py 的双容（加热丝 + 空气）热路模型与显式欧拉积分，
提供一个浏览器端的实时可视化界面：

    · 数值框      —— 实时显示加热丝温度 T_h、空气温度 T_a、时间、功率
    · 填充矩形    —— 两根温度计柱（T_h 红色尺度，T_a 蓝色尺度）
    · Plotly 曲线 —— 同图绘制 T_h、T_a、功率历史
    · 加热器按钮  —— "点动"控制：按住为开，松开为关

物理模型：
    C_h dT_h/dt = η·P − (T_h − T_a)/R_ha
    C_a dT_a/dt = (T_h − T_a)/R_ha − (T_a − T_e)/R_ae

依赖： pip install flask
运行： python flask_realtime.py
浏览器打开 http://127.0.0.1:5000
"""

import threading
import time
from flask import Flask, jsonify, request, render_template_string

# ===================================================================
# 1. 物理参数（与 no_fan_euler.py 完全一致）
# ===================================================================
c_h   = 200.0     # 加热丝热容          [J/K]
c_a   = 1500.0    # 空气+内胆等效热容    [J/K]
eta   = 0.95      # 加热器电热效率       [-]
r_ha  = 0.10      # 加热丝 → 空气热阻    [K/W]
r_ae  = 0.40      # 空气 → 环境热阻      [K/W]
t_env = 25.0      # 环境温度            [°C]

DT             = 1.0      # 仿真/控制周期 [s]，同时也是实时节拍
HEATER_POWER   = 200.0    # 加热器额定功率 [W]
MAX_HISTORY    = 600      # 曲线最多保留的采样点数

# ===================================================================
# 2. 单步推进函数（双容模型）
# ===================================================================
def step_euler(temp_h, temp_a, power, dt):
    """显式欧拉法把对象 (T_h, T_a) 推进一个采样周期 dt。"""
    q_ha = (temp_h - temp_a) / r_ha
    q_ae = (temp_a - t_env)  / r_ae
    d_temp_h = (eta * power - q_ha) / c_h
    d_temp_a = (q_ha        - q_ae) / c_a
    return temp_h + dt * d_temp_h, temp_a + dt * d_temp_a

# ===================================================================
# 3. 全局仿真状态（被后台线程与 Flask 路由共享，需要加锁）
# ===================================================================
state = {
    "t":                  0.0,
    "temperature_heater": t_env,
    "temperature_air":    t_env,
    "heat_power":         0.0,
    "heater_on":          False,
    "history":            [{"t": 0.0, "temperature_heater": t_env, "temperature_air": t_env, "heat_power": 0.0}],
}
state_lock = threading.Lock()

def simulation_loop():
    """后台仿真线程：每 DT 秒推进一次。"""
    next_tick = time.time()
    while True:
        next_tick += DT
        sleep_for = next_tick - time.time()
        if sleep_for > 0:
            time.sleep(sleep_for)
        else:
            next_tick = time.time()  # 落后了就重新对齐

        with state_lock:
            power = HEATER_POWER if state["heater_on"] else 0.0
            state["temperature_heater"], state["temperature_air"] = step_euler(
                state["temperature_heater"], state["temperature_air"], power, DT
            )
            state["t"]          += DT
            state["heat_power"]  = power
            state["history"].append({
                "t":                  round(state["t"], 2),
                "temperature_heater": round(state["temperature_heater"], 3),
                "temperature_air":    round(state["temperature_air"], 3),
                "heat_power":         power,
            })
            if len(state["history"]) > MAX_HISTORY:
                state["history"] = state["history"][-MAX_HISTORY:]

# ===================================================================
# 4. Flask 应用与 API
# ===================================================================
app = Flask(__name__)

@app.route("/")
def index():
    return render_template_string(PAGE)

@app.route("/api/state")
def api_state():
    with state_lock:
        return jsonify({
            "t":                  state["t"],
            "temperature_heater": state["temperature_heater"],
            "temperature_air":    state["temperature_air"],
            "heat_power":         state["heat_power"],
            "heater_on":          state["heater_on"],
            "history":            state["history"],
        })

@app.route("/api/heater", methods=["POST"])
def api_heater():
    data = request.get_json(silent=True) or {}
    with state_lock:
        if "on" in data:
            state["heater_on"] = bool(data["on"])
        else:
            state["heater_on"] = not state["heater_on"]
        return jsonify({"heater_on": state["heater_on"]})

@app.route("/api/reset", methods=["POST"])
def api_reset():
    with state_lock:
        state["t"]                  = 0.0
        state["temperature_heater"] = t_env
        state["temperature_air"]    = t_env
        state["heat_power"]         = 0.0
        state["heater_on"]          = False
        state["history"]            = [{"t": 0.0, "temperature_heater": t_env, "temperature_air": t_env, "heat_power": 0.0}]
    return jsonify({"ok": True})

# ===================================================================
# 5. 前端页面（单文件 HTML + JS）
# ===================================================================
PAGE = r"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>无风扇温度箱 · 实时仿真（双容模型）</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  * { box-sizing: border-box; }
  body { font-family: "Segoe UI", "Microsoft YaHei", Tahoma, sans-serif;
         background:#f4f6f8; margin:0; padding:20px; color:#1f2937; }
  h1   { margin:0 0 16px 0; font-size:22px; }
  h1 small { color:#6b7280; font-size:14px; font-weight:400; margin-left:8px;}
  .container { max-width:1240px; margin:auto; }
  .panel { display:flex; gap:16px; flex-wrap:wrap; align-items:stretch; }
  .card  { background:#fff; border-radius:10px;
           box-shadow:0 2px 8px rgba(0,0,0,.06); padding:16px; }
  .label { color:#6b7280; font-size:13px; }

  /* 数值显示 + 控制 (合并到同一张卡) */
  .display      { flex:0 0 260px; display:flex; flex-direction:column; }
  .num-row      { display:flex; justify-content:space-between; align-items:baseline;
                  border-bottom:1px dashed #e5e7eb; padding:6px 0; }
  .num-row:last-of-type { border-bottom:none; }
  .num-name     { font-size:14px; color:#374151; }
  .num-value    { font-size:30px; font-weight:700;
                  font-variant-numeric: tabular-nums; line-height:1.1; }
  .num-value.h  { color:#dc2626; }   /* 加热丝 红 */
  .num-value.a  { color:#2563eb; }   /* 空气   蓝 */
  .num-value.s  { color:#374151; font-size:18px; }
  .num-unit     { font-size:13px; color:#6b7280; margin-left:2px; }
  .ctrl-block   { margin-top:14px; padding-top:14px; border-top:1px solid #e5e7eb; }
  .heater-btn   { width:100%; padding:20px 16px; font-size:18px;
                  font-weight:700; border:none; border-radius:10px;
                  background:#374151; color:#fff; cursor:pointer;
                  user-select:none; transition: background .12s, transform .05s; }
  .heater-btn.on { background:#dc2626; box-shadow: inset 0 0 0 4px #fca5a5; }
  .heater-btn:active { transform: translateY(1px); }
  .status   { margin-top:10px; font-size:13px; color:#374151; }
  .led      { display:inline-block; width:10px; height:10px;
              border-radius:50%; background:#9ca3af; margin-right:6px;
              vertical-align:middle; }
  .led.on   { background:#22c55e; box-shadow:0 0 8px #22c55e; }
  .reset-btn{ margin-top:10px; padding:8px 16px; border:none;
              border-radius:6px; background:#3b82f6; color:#fff;
              cursor:pointer; font-size:14px; }
  .reset-btn:hover { background:#2563eb; }

  /* 柱状温度计（双柱） */
  .bar-card  { flex:0 0 180px; display:flex; flex-direction:column; align-items:center; }
  .bars      { display:flex; gap:18px; margin-top:8px; }
  .bar-col   { display:flex; flex-direction:column; align-items:center; }
  .bar-frame { width:46px; height:280px; border:2px solid #374151;
               border-radius:6px; position:relative; background:#e5e7eb;
               overflow:hidden; }
  .bar-fill  { position:absolute; left:0; right:0; bottom:0;
               transition: height .35s ease, background-color .35s ease; }
  .bar-cap   { font-size:12px; margin-top:6px; }
  .bar-cap.h { color:#dc2626; }
  .bar-cap.a { color:#2563eb; }

  /* 曲线 (现在放到右侧那张卡) */
  .chart-card { flex:1; min-width:380px; display:flex; flex-direction:column; }
  #chart      { flex:1; min-height:380px; }
  .footer     { margin-top:14px; color:#9ca3af; font-size:12px; line-height:1.6; }
  .footer code{ background:#f3f4f6; padding:1px 6px; border-radius:4px; color:#374151; }
</style>
</head>
<body>
<div class="container">
  <h1>无风扇温度箱 · 实时数字孪生
    <small>双容模型（加热丝 T<sub>h</sub> + 空气 T<sub>a</sub>） · 显式欧拉</small>
  </h1>

  <div class="panel">
    <!-- 数值 + 控制（合并到一张卡）-->
    <div class="card display">
      <div class="num-row">
        <span class="num-name">加热丝温度 T<sub>h</sub></span>
        <span><span class="num-value h" id="num-h">25.00</span><span class="num-unit">°C</span></span>
      </div>
      <div class="num-row">
        <span class="num-name">空气温度 T<sub>a</sub></span>
        <span><span class="num-value a" id="num-a">25.00</span><span class="num-unit">°C</span></span>
      </div>
      <div class="num-row">
        <span class="num-name">仿真时间 t</span>
        <span><span class="num-value s" id="num-t">0</span><span class="num-unit">s</span></span>
      </div>
      <div class="num-row">
        <span class="num-name">加热功率 P</span>
        <span><span class="num-value s" id="num-p">0</span><span class="num-unit">W</span></span>
      </div>

      <div class="ctrl-block">
        <div class="label">加热器（点动 · 按住为开，松开为关）</div>
        <button id="heater-btn" class="heater-btn">按住加热</button>
        <div class="status">
          <span class="led" id="led"></span>
          <span id="state-text">加热器关闭</span>
        </div>
        <button id="reset-btn" class="reset-btn">重置仿真</button>
      </div>
    </div>

    <!-- 柱状条 -->
    <div class="card bar-card">
      <div class="label">温度直观显示</div>
      <div class="bars">
        <div class="bar-col">
          <div class="bar-frame">
            <div class="bar-fill" id="bar-h" style="height:17%; background:#3b82f6;"></div>
          </div>
          <div class="bar-cap h">T<sub>h</sub> 0~150°C</div>
        </div>
        <div class="bar-col">
          <div class="bar-frame">
            <div class="bar-fill" id="bar-a" style="height:25%; background:#3b82f6;"></div>
          </div>
          <div class="bar-cap a">T<sub>a</sub> 0~100°C</div>
        </div>
      </div>
    </div>

    <!-- 实时曲线（搬到右侧原来按钮所在的位置） -->
    <div class="card chart-card">
      <div id="chart"></div>
    </div>
  </div>

  <div class="footer">
    参数：C<sub>h</sub>=200 J/°C，C<sub>a</sub>=1500 J/°C，η=0.95，
    R<sub>ha</sub>=0.10 °C/W，R<sub>ae</sub>=0.40 °C/W，T<sub>env</sub>=25°C，
    P=200 W，dt=1 s。
    <br>
    模型：<code>C_h·dT_h/dt = η·P − (T_h−T_a)/R_ha</code> ；
    <code>C_a·dT_a/dt = (T_h−T_a)/R_ha − (T_a−T_env)/R_ae</code>。
    稳态：T<sub>a</sub>≈101 °C，T<sub>h</sub>≈120 °C；时间常数 τ<sub>fast</sub>≈18 s，τ<sub>slow</sub>≈690 s。
  </div>
</div>

<script>
// ---- DOM 引用 ----
const $numH    = document.getElementById('num-h');
const $numA    = document.getElementById('num-a');
const $numT    = document.getElementById('num-t');
const $numP    = document.getElementById('num-p');
const $barH    = document.getElementById('bar-h');
const $barA    = document.getElementById('bar-a');
const $heater  = document.getElementById('heater-btn');
const $led     = document.getElementById('led');
const $stateTx = document.getElementById('state-text');
const $reset   = document.getElementById('reset-btn');

// ---- Plotly 初始化 ----
const layout = {
  margin: {l:60, r:60, t:30, b:45},
  xaxis:  {title:'时间 t / s'},
  yaxis:  {title:{text:'温度 / °C'}, },
  yaxis2: {title:{text:'功率 / W', font:{color:'#374151'}},
           tickfont:{color:'#374151'}, overlaying:'y', side:'right'},
  legend: {orientation:'h', y:1.15, x:0.5, xanchor:'center'},
  showlegend: true,
};
Plotly.newPlot('chart', [
  {x:[], y:[], mode:'lines', name:'T_h 加热丝 / °C',
   line:{color:'#dc2626', width:2}, yaxis:'y1'},
  {x:[], y:[], mode:'lines', name:'T_a 空气 / °C',
   line:{color:'#2563eb', width:2}, yaxis:'y1'},
  {x:[], y:[], mode:'lines', name:'功率 / W',
   line:{color:'#374151', dash:'dash'}, yaxis:'y2'}
], layout, {responsive:true, displayModeBar:false});

// ---- 颜色映射：低温 → 蓝，高温 → 红 ----
function tempToColor(t, lo, hi) {
  const r = Math.max(0, Math.min(1, (t - lo)/(hi - lo)));
  const R = Math.round( 59 + r*(220 -  59));
  const G = Math.round(130*(1-r) + 38*r);
  const B = Math.round(246*(1-r) + 38*r);
  return `rgb(${R},${G},${B})`;
}

// ---- 与后端通信 ----
function setHeater(on) {
  fetch('/api/heater', {
    method: 'POST',
    headers:{'Content-Type':'application/json'},
    body:   JSON.stringify({on})
  });
}

// 点动（鼠标 + 触摸屏）
$heater.addEventListener('mousedown',  e => { e.preventDefault(); setHeater(true);  });
$heater.addEventListener('mouseup',    e => { e.preventDefault(); setHeater(false); });
$heater.addEventListener('mouseleave', e => { setHeater(false); });
$heater.addEventListener('touchstart', e => { e.preventDefault(); setHeater(true);  }, {passive:false});
$heater.addEventListener('touchend',   e => { e.preventDefault(); setHeater(false); }, {passive:false});
$heater.addEventListener('touchcancel',e => { setHeater(false); });

$reset.addEventListener('click', () => fetch('/api/reset', {method:'POST'}));

// ---- 周期性拉取状态并刷新 UI ----
async function poll() {
  try {
    const r = await fetch('/api/state');
    const s = await r.json();

    $numH.textContent = s.temperature_heater.toFixed(2);
    $numA.textContent = s.temperature_air.toFixed(2);
    $numT.textContent = s.t.toFixed(0);
    $numP.textContent = s.heat_power.toFixed(0);

    // 柱状条：T_h 量程 0~150°C，T_a 量程 0~100°C
    const pctH = Math.max(0, Math.min(100, s.temperature_heater / 150 * 100));
    const pctA = Math.max(0, Math.min(100, s.temperature_air / 100 * 100));
    $barH.style.height          = pctH + '%';
    $barA.style.height          = pctA + '%';
    $barH.style.backgroundColor = tempToColor(s.temperature_heater, 25, 130);
    $barA.style.backgroundColor = tempToColor(s.temperature_air, 25, 100);

    // 加热器外观
    if (s.heater_on) {
      $heater.classList.add('on');
      $heater.textContent = '加热中…';
      $led.classList.add('on');
      $stateTx.textContent = '加热器开启 (P = 200 W)';
    } else {
      $heater.classList.remove('on');
      $heater.textContent = '按住加热';
      $led.classList.remove('on');
      $stateTx.textContent = '加热器关闭 (P = 0 W)';
    }

    // 更新曲线
    const xs    = s.history.map(p => p.t);
    const tH    = s.history.map(p => p.temperature_heater);
    const tA    = s.history.map(p => p.temperature_air);
    const pwrs  = s.history.map(p => p.heat_power);
    Plotly.react('chart', [
      {x:xs, y:tH,   mode:'lines', name:'T_h 加热丝 / °C',
       line:{color:'#dc2626', width:2}, yaxis:'y1'},
      {x:xs, y:tA,   mode:'lines', name:'T_a 空气 / °C',
       line:{color:'#2563eb', width:2}, yaxis:'y1'},
      {x:xs, y:pwrs, mode:'lines', name:'功率 / W',
       line:{color:'#374151', dash:'dash'}, yaxis:'y2'}
    ], layout, {responsive:true, displayModeBar:false});
  } catch (err) {
    console.error('poll error:', err);
  }
}
setInterval(poll, 500);
poll();
</script>
</body>
</html>
"""

# ===================================================================
# 6. 入口
# ===================================================================
if __name__ == "__main__":
    sim_thread = threading.Thread(target=simulation_loop, daemon=True)
    sim_thread.start()
    # use_reloader=False 防止 Flask 重启时多开仿真线程
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
