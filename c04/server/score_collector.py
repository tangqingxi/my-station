# server/score_collector.py · 打分收集器 · 骑在 server.main 现有箱子上
#
# 评分机制：服务端每个 emit 拍记录最新 true/noisy；客户端每回传一个
# filtered，就与“此刻最新真值”计算即时偏差平方。这样不需要序号、不需要对齐。

from __future__ import annotations

import logging
import math
import statistics as st
from collections import deque

log = logging.getLogger(__name__)

WINDOW = 480  # 滑动窗口采样数：emit_dt=0.5 时约 240 秒


class ScoreCollector:
    def __init__(
        self, station: str = "my-station",
        broker_host: str = "127.0.0.1", broker_port: int = 1883,
        dt: float = 0.5, warmup_s: float = 30.0,
    ) -> None:
        self.station = station
        self._broker = (broker_host, int(broker_port))
        self.dt = float(dt)
        self._warmup = int(warmup_s / self.dt)
        self._tick: dict[str, int] = {}
        self._true: dict[str, deque] = {}
        self._noisy: dict[str, deque] = {}
        self._filt: dict[str, deque] = {}
        self._ferr: dict[str, deque] = {}
        self._nerr: dict[str, deque] = {}
        self._drive: dict[str, deque] = {}
        self._latest_true: dict[str, float | None] = {}
        self._cf: dict[str, float] = {}
        self._cfn: dict[str, int] = {}
        self._cn: dict[str, float] = {}
        self._cnn: dict[str, int] = {}
        self._order: list[str] = []
        self._client = None

    def _ensure(self, box: str) -> None:
        if box in self._true:
            return
        for d in (self._true, self._noisy, self._filt, self._ferr, self._nerr, self._drive):
            d[box] = deque(maxlen=WINDOW)
        self._tick[box] = 0
        self._latest_true[box] = None
        self._cf[box] = 0.0
        self._cn[box] = 0.0
        self._cfn[box] = 0
        self._cnn[box] = 0
        self._order.append(box)

    def feed(self, box: str, true_v: float, noisy_v: float, drive: float | None = None) -> None:
        """每个 emit 拍喂入真值、加噪值，可顺带记录激励功率。"""
        self._ensure(box)
        k = self._tick[box]
        self._tick[box] = k + 1
        tv, nv = float(true_v), float(noisy_v)
        self._latest_true[box] = tv
        self._true[box].append((k, round(tv, 3)))
        self._noisy[box].append((k, round(nv, 3)))
        ne = (nv - tv) ** 2
        self._nerr[box].append(ne)
        if drive is not None:
            self._drive[box].append(round(float(drive), 3))
        if k >= self._warmup:
            self._cn[box] += ne
            self._cnn[box] += 1

    def record_filtered(self, box: str, v: float) -> None:
        """收到客户端回传的去噪值后，立刻与最新真值算偏差平方。"""
        self._ensure(box)
        lt = self._latest_true.get(box)
        if lt is None:
            return
        k = self._tick[box]
        fv = float(v)
        self._filt[box].append((k, round(fv, 3)))
        fe = (fv - lt) ** 2
        self._ferr[box].append(fe)
        if k >= self._warmup:
            self._cf[box] += fe
            self._cfn[box] += 1

    def boxes(self) -> list[str]:
        return [b for b in self._order if self._ferr.get(b)]

    def final_score(self, box: str) -> dict | None:
        """预热后累计的 SNR 改善，百分制只作展示。"""
        if self._cfn.get(box, 0) < 1 or self._cnn.get(box, 0) < 1 or self._cf[box] <= 0:
            return None
        mean_f = self._cf[box] / self._cfn[box]
        mean_n = self._cn[box] / self._cnn[box]
        if mean_f <= 0 or mean_n <= 0:
            return None
        improve = 10 * math.log10(mean_n / mean_f)
        return {
            "final_improve_db": round(improve, 2),
            "final_pct": max(0, min(100, round(10 * improve))),
            "n": self._cfn[box],
        }

    def scoreboard(self) -> list[dict]:
        """所有已收到回传的箱子排行，阶段 4 看板会直接消费。"""
        rows = []
        for box in self.boxes():
            fin = self.final_score(box)
            did = box.rsplit("-", 1)[-1]
            rows.append({
                "device_id": did,
                "box": box,
                "final_pct": fin["final_pct"] if fin else None,
                "final_db": fin["final_improve_db"] if fin else None,
            })
        rows.sort(key=lambda r: (r["final_pct"] is None, -(r["final_pct"] or 0)))
        return rows

    def kpi(self, box: str) -> dict | None:
        if not self._ferr.get(box):
            return None
        fmse = st.fmean(self._ferr[box])
        nmse = st.fmean(self._nerr[box]) if self._nerr[box] else None
        tv = [v for _, v in self._true[box]]
        var_t = st.pvariance(tv) if len(tv) > 1 else 0.0
        snr = 10 * math.log10(var_t / fmse) if var_t > 0 and fmse > 0 else None
        improve = 10 * math.log10(nmse / fmse) if nmse and fmse > 0 else None
        out = {
            "n": len(self._ferr[box]),
            "mse": round(fmse, 3),
            "snr_db": round(snr, 2) if snr is not None else None,
            "snr_improve_db": round(improve, 2) if improve is not None else None,
        }
        out["final"] = self.final_score(box)
        return out

    def plot_snapshot(self, box: str) -> dict:
        """给阶段 4 看板准备三条线和 KPI。"""
        tt = list(self._true.get(box, []))
        nn = list(self._noisy.get(box, []))
        ff = list(self._filt.get(box, []))
        return {
            "box": box,
            "t": [k for k, _ in tt],
            "true": [v for _, v in tt],
            "noisy": [v for _, v in nn],
            "t_filt": [k for k, _ in ff],
            "filtered": [v for _, v in ff],
            "u": list(self._drive.get(box, [])),
            "kpi": self.kpi(box),
        }

    def start(self) -> None:
        return

    def stop(self) -> None:
        return
