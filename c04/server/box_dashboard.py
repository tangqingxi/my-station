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

    def __init__(self, station_id: str = "my-station", collector=None):
        self.station_id = station_id
        self._collector = collector
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
        boxes = self.boxes()
        if self._collector is not None and box in set(self._collector.boxes()):
            s = self._collector.plot_snapshot(box)
            s["boxes"] = boxes
        elif box is None or box not in self._t:
            s = {
                "boxes": self.boxes(), "box": box,
                "t": [], "true": [], "noisy": [], "u": [],
            }
        else:
            s = {
                "boxes": boxes,
                "box": box,
                "t": list(self._t[box]),
                "true": list(self._true[box]),
                "noisy": list(self._noisy[box]),
                "u": list(self._u[box]),
            }
        if self._collector is not None:
            s["scoreboard"] = self._collector.scoreboard()
        return s


_PAGE = """<!doctype html>
<html lang="zh"><head><meta charset="utf-8">
<title>服务端看板 · {sid} · 真值 vs 加噪</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
 html,body{{height:100%;margin:0}}
 body{{font-family:"Microsoft YaHei",sans-serif;color:#1f2328;
       display:flex;flex-direction:row;gap:14px;padding:12px 18px;box-sizing:border-box}}
 #main{{flex:1 1 auto;display:flex;flex-direction:column;min-width:0}}
 #bar{{flex:0 0 auto;display:flex;align-items:center;gap:20px;flex-wrap:wrap;margin-bottom:8px}}
 h2{{margin:0;font-size:18px}} h2 span{{color:#57606a;font-size:14px;font-weight:normal}}
 select{{font-size:15px;padding:3px 6px}}
 button{{font-size:14px;padding:4px 14px;cursor:pointer}}
 #now{{display:flex;gap:18px;font-size:15px}}
 #now b{{font-variant-numeric:tabular-nums}}
 .v-true{{color:#2ca02c}} .v-noisy{{color:#8a8a8a}} .v-filt{{color:#1f77b4}}
 #kpi{{display:flex;gap:10px;flex-wrap:wrap}}
 .card{{background:#f6f8fa;border:1px solid #d0d7de;border-radius:8px;padding:4px 12px;min-width:78px;font-size:13px}}
 .card b{{display:block;font-size:17px;font-variant-numeric:tabular-nums}} .card span{{color:#57606a}}
 #plot:fullscreen{{background:#fff;padding:6px;box-sizing:border-box}}
 #plot{{flex:1 1 auto;min-height:0;width:100%}}
 #side{{flex:0 0 200px;display:flex;flex-direction:column;border-left:1px solid #e1e4e8;padding-left:12px;overflow-y:auto}}
 #side h3{{margin:2px 0 8px;font-size:15px}}
 table.board{{border-collapse:collapse;width:100%;font-size:13px}}
 .board th,.board td{{border-bottom:1px solid #eee;padding:4px 6px;text-align:left}}
 .board th{{color:#57606a}}  .board td.sc{{font-variant-numeric:tabular-nums;font-weight:600;text-align:right}}
 .board tr.cur{{background:#eaf2ff}}  .board td.dim{{color:#9aa0a6}}
</style></head><body>
<div id="main">
<div id="bar">
  <h2>服务端看板 · {sid} <span>真值 / 加噪 / 去噪 + 打分</span></h2>
  <div>选择温度箱:<select id="box" onchange="current=this.value;poll()"></select></div>
  <button id="pause" onclick="togglePause()">暂停</button>
  <div id="now">
    <span class="v-true">真值 <b id="vt">—</b></span>
    <span class="v-noisy">加噪 <b id="vn">—</b></span>
    <span class="v-filt" id="nfilt" style="display:none">去噪 <b id="vf">—</b></span>
  </div>
  <div id="kpi"></div>
</div>
<div id="plot"></div>
</div>
<div id="side">
  <h3>实时评分</h3>
  <table class="board"><thead><tr><th>device</th><th>综合分</th><th>dB</th></tr></thead><tbody id="board"></tbody></table>
</div>
<script>
let current = "";
let paused = false;
function togglePause(){{
  paused = !paused;
  document.getElementById("pause").textContent = paused ? "继续" : "暂停";
}}
const last = a => (a && a.length) ? a[a.length - 1] : null;
const fmt  = v => (v == null ? "—" : v.toFixed(2));
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
  let umax = 0;
  if (d.u && d.u.length) {{
    d.u.forEach(function(v){{ if (v > umax) umax = v; }});
    traces.push({{x:d.t, y:d.u, name:"功率 u", mode:"lines", yaxis:"y2",
                  line:{{color:"#ff7f0e",width:1.5}}}});
  }}
  const hasFilt = d.filtered && d.filtered.length;
  document.getElementById("nfilt").style.display = hasFilt ? "" : "none";
  if (hasFilt) {{
    traces.push({{x:d.t_filt, y:d.filtered, name:"去噪 filtered", mode:"lines",
                  line:{{color:"#1f77b4",width:2}}}});
    document.getElementById("vf").textContent = fmt(last(d.filtered));
  }}
  const k = d.kpi;
  let cards = "";
  if (k) {{
    cards = card("MSE", k.mse, "") + card("SNR", k.snr_db, " dB") + card("SNR改善", k.snr_improve_db, " dB");
    if (k.final) cards += card("★最终分", k.final.final_pct, " 分") + card("累计改善", k.final.final_improve_db, " dB");
  }}
  document.getElementById("kpi").innerHTML = cards;
  const sb = d.scoreboard;
  if (sb) document.getElementById("board").innerHTML = sb.map(r =>
    '<tr class="'+(r.box===current?'cur':'')+'"><td>'+r.device_id+'</td>'+
    '<td class="sc'+(r.final_pct==null?' dim':'')+'">'+(r.final_pct==null?'预热':r.final_pct)+'</td>'+
    '<td class="'+(r.final_db==null?'dim':'')+'">'+(r.final_db==null?'—':r.final_db.toFixed(1))+'</td></tr>'
  ).join("");
  Plotly.react("plot", traces,
    {{autosize:true, uirevision:"keep", margin:{{t:10,r:54,b:40,l:52}},
      xaxis:{{title:"tick"}}, yaxis:{{title:"温度 / C"}},
      yaxis2:{{title:"功率 u / W", overlaying:"y", side:"right", showgrid:false,
               range:[0, (umax>0?umax:1)*2.2]}},
      legend:{{orientation:"h"}}}},
    {{displayModeBar:true, responsive:true, modeBarButtonsToAdd:[fsBtn]}});
}}
function card(label, val, unit){{
  return '<div class="card"><span>'+label+'</span><b>'+
         (val==null?'—':(typeof val==='number'?val.toFixed(2):val))+(unit||'')+'</b></div>';
}}
const fsBtn = {{ name:"全屏", title:"全屏显示曲线(再按 Esc 退出)",
  icon:{{width:1000,height:1000,path:"M0 0H420V120H120V420H0ZM580 0H1000V420H880V120H580ZM0 580H120V880H420V1000H0ZM880 580H1000V1000H580V880H880Z"}},
  click:function(gd){{ if(!document.fullscreenElement){{ gd.requestFullscreen(); }} else {{ document.exitFullscreen(); }} }} }};
document.addEventListener("fullscreenchange", function(){{ const p=document.getElementById("plot"); if(p) Plotly.Plots.resize(p); }});
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
