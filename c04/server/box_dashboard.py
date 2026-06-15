# server/box_dashboard.py · part1 服务端看板：真值 vs 加噪
from __future__ import annotations

import logging
import socket as _socket
import threading
from collections import deque

from flask import Flask, jsonify, request

log = logging.getLogger(__name__)

MAXLEN = 600


class BoxDashboard:
    """收集每台箱的 true/noisy/u 历史，供 Flask 看板查询。"""

    def __init__(self, station_id: str = "my-station"):
        self.station_id = station_id
        self._tick: dict[str, int] = {}
        self._t: dict[str, deque] = {}
        self._true: dict[str, deque] = {}
        self._noisy: dict[str, deque] = {}
        self._u: dict[str, deque] = {}
        self._order: list[str] = []

    def record(self, box: str, true_v: float, noisy_v: float, u: float = 0.0) -> None:
        if box not in self._t:
            self._t[box] = deque(maxlen=MAXLEN)
            self._true[box] = deque(maxlen=MAXLEN)
            self._noisy[box] = deque(maxlen=MAXLEN)
            self._u[box] = deque(maxlen=MAXLEN)
            self._tick[box] = 0
            self._order.append(box)
        k = self._tick[box]
        self._tick[box] = k + 1
        self._t[box].append(k)
        self._true[box].append(round(float(true_v), 3))
        self._noisy[box].append(round(float(noisy_v), 3))
        self._u[box].append(round(float(u), 2))

    def boxes(self) -> list[str]:
        return list(self._order)

    def snapshot(self, box: str | None) -> dict:
        if box is None or box not in self._t:
            return {
                "boxes": self.boxes(), "box": box,
                "t": [], "true": [], "noisy": [], "u": [],
            }
        return {
            "boxes": self.boxes(),
            "box": box,
            "t": list(self._t[box]),
            "true": list(self._true[box]),
            "noisy": list(self._noisy[box]),
            "u": list(self._u[box]),
        }


_PAGE = """<!doctype html>
<html lang="zh"><head><meta charset="utf-8">
<title>服务端看板 · {sid} · 真值 vs 加噪</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
 html,body{{height:100%;margin:0}}
 body{{font-family:"Microsoft YaHei",sans-serif;color:#1f2328;
       display:flex;flex-direction:column;padding:12px 18px;box-sizing:border-box}}
 #bar{{flex:0 0 auto;display:flex;align-items:center;gap:20px;flex-wrap:wrap;margin-bottom:8px}}
 h2{{margin:0;font-size:18px}} h2 span{{color:#57606a;font-size:14px;font-weight:normal}}
 select{{font-size:15px;padding:3px 6px}}
 button{{font-size:14px;padding:4px 14px;cursor:pointer}}
 #now{{display:flex;gap:18px;font-size:15px}}
 #now b{{font-variant-numeric:tabular-nums}}
 .v-true{{color:#2ca02c}} .v-noisy{{color:#8a8a8a}}
 #plot{{flex:1 1 auto;min-height:0;width:100%}}
</style></head><body>
<div id="bar">
  <h2>服务端看板 · {sid} <span>真值 vs 加噪(part1)</span></h2>
  <div>选择温度箱:<select id="box" onchange="current=this.value;poll()"></select></div>
  <button id="pause" onclick="togglePause()">暂停</button>
  <div id="now">
    <span class="v-true">真值 true: <b id="vt">-</b> C</span>
    <span class="v-noisy">加噪 noisy: <b id="vn">-</b> C</span>
  </div>
</div>
<div id="plot"></div>
<script>
let current = "";
let paused = false;
function togglePause(){{
  paused = !paused;
  document.getElementById("pause").textContent = paused ? "继续" : "暂停";
}}
const last = a => (a && a.length) ? a[a.length - 1] : null;
const fmt  = v => (v == null ? "-" : v.toFixed(2));
async function poll(){{
  if (paused) return;
  let url = "/data" + (current ? ("?box="+encodeURIComponent(current)) : "");
  let d;
  try {{ d = await (await fetch(url)).json(); }} catch(e) {{ return; }}
  const sel = document.getElementById("box");
  if (sel.options.length !== d.boxes.length) {{
    sel.innerHTML = d.boxes.map(c=>'<option>'+c+'</option>').join("");
    if (!current && d.boxes.length) {{ current = d.boxes[0]; sel.value = current; }}
  }}
  document.getElementById("vt").textContent = fmt(last(d.true));
  document.getElementById("vn").textContent = fmt(last(d.noisy));
  const traces = [
    {{x:d.t, y:d.true,  name:"真值 true",  mode:"lines", line:{{color:"#2ca02c",width:2}}}},
    {{x:d.t, y:d.noisy, name:"加噪 noisy", mode:"lines", line:{{color:"#bbbbbb",width:1}}}},
  ];
  if (d.u && d.u.length) traces.push({{x:d.t, y:d.u, name:"功率 u", mode:"lines", yaxis:"y2",
                                       line:{{color:"#ff7f0e",width:1.5}}}});
  Plotly.react("plot", traces,
    {{autosize:true, uirevision:"keep", margin:{{t:10,r:54,b:40,l:52}},
      xaxis:{{title:"tick"}}, yaxis:{{title:"温度 / C"}},
      yaxis2:{{title:"功率 u / W", overlaying:"y", side:"right", showgrid:false, rangemode:"tozero"}},
      legend:{{orientation:"h"}}}},
    {{displayModeBar:true, responsive:true}});
}}
poll(); setInterval(poll, 1000);
</script></body></html>"""


def make_app(srv: BoxDashboard) -> Flask:
    """构造 Flask app：/ 返回页面，/data 返回选中箱的快照。"""
    app = Flask(__name__)
    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    @app.get("/")
    def index():
        return _PAGE.format(sid=srv.station_id)

    @app.get("/data")
    def data():
        box = request.args.get("box")
        if box is None:
            bs = srv.boxes()
            box = bs[0] if bs else None
        return jsonify(srv.snapshot(box))

    return app


def serve(srv: BoxDashboard, host: str = "127.0.0.1", port: int = 5400) -> Flask:
    """后台 daemon 线程里跑 Flask 看板，主进程退出时自动结束。"""
    app = make_app(srv)
    probe = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
    try:
        probe.bind((host, port))
    except OSError:
        probe.close()
        msg = (
            f"看板端口 {port} 已被占用；看板这次没有启动。"
            f"请先结束旧 server.main 进程，或改 dashboard_port。"
        )
        print("\n" + "!" * 12 + " [看板] " + msg + "\n")
        log.error(msg)
        return app
    probe.close()
    threading.Thread(
        target=lambda: app.run(host=host, port=port, threaded=True, use_reloader=False),
        daemon=True,
        name="box-dashboard",
    ).start()
    log.info("服务端看板:http://%s:%d/", host, port)
    return app
