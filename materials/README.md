# materials/ · 老师准备的代码模板

> 这个目录是**老师准备好的起点代码** · 整个 C2-C8 不动 · 学生按段拷出来用 · 跟课进度走。

---

## 这里是什么

| 文件 | C2 哪里拷 | 用途 |
|---|---|---|
| `no_fan_euler.py` | 段 3 P3 | 双容温度仿真 · `step_euler(t_h, t_a, power, dt)` 核心函数 + main 块画 PNG |
| `flask_realtime.py` | 段 6 P27 | Flask + Plotly + threading 实时温控浏览器 demo · 段 7 综合练习改的就是它 |

---

## 怎么用(按段拷)

### 段 3 P3(课中第 75-95 min 左右 · 跟做)

```bash
# 在 my-station 项目根目录(已 cd 进来)
cp materials/no_fan_euler.py .
git add no_fan_euler.py
git commit -m "feat: 加入双容仿真代码"

# 然后跟段 3 PPT 走:
# 1. 写 simple_demo.py 同目录 import
# 2. 改成 physics/ package
# 3. __init__.py 暴露 step_euler
```

### 段 6 P27(课中第 150-160 min 左右 · 跟做)

```bash
# 在 my-station 项目根目录
cp materials/flask_realtime.py .
git add flask_realtime.py
git commit -m "feat: 加入 Flask 实时温控 demo"

# 跑起来
uv run python flask_realtime.py
# 浏览器 http://127.0.0.1:5000/ · 按住"按住加热"看温度爬
```

### 段 7 综合练习(40 min 高密度)

段 7 是改 flask_realtime.py 加 6 个改动 + 双 feature 分支 + 解冲突 + push Gitee。
**不再从 materials/ 拷文件** · 在段 6 已经拷过来的 flask_realtime.py 上改即可。

---

## ❓ 为什么不直接把这些文件放项目根?

3 个原因:

1. **跟课节奏一致**:课程设计成"段 3 才加物理代码 / 段 6 才加 Flask demo" · 拷文件本身是学生 git 实操的一部分(`cp + git add + git commit -m "feat: ..."`)
2. **保留老师"标准版"**:学生改坏了项目根的 `no_fan_euler.py` / `flask_realtime.py` 时 · 还能从 `materials/` 拷一份回去 · 不用查 Gitee 历史
3. **教 git 工作流**:`materials/` 的文件不要改 · 也不要 `git rm` · 学期内保留作为"老师原始代码标尺"

---

## ⚠ 不要做的事

- ❌ 不要直接在 `materials/` 里改文件(改了就再难恢复 · 而且不符合"教材代码"角色)
- ❌ 不要 `git rm -r materials/`(保留对照用)
- ❌ 不要重命名(段 3 / 段 6 PPT 命令依赖这个路径)

## ✓ 推荐做的事

- ✓ 段 3 / 段 6 按 PPT 指引 `cp materials/xxx .` 到项目根
- ✓ 改坏项目根的版本 → `cp materials/xxx .` 重新拷一份覆盖 · 重新 commit
- ✓ C5 / C6 想看老师"基础版" 长啥样 → 直接 `cat materials/flask_realtime.py`

---

## 老师补充材料的位置(不在本仓库)

- **plotkit 通用画图包**:课程仓库 `lecture/_共享代码包/plotkit/`(课后选装)
- **C2 ~ C8 各次课材料**:课程仓库 `lecture/C{N}_第0{N}次课/`(PPT / 速查卡 / 跟做清单 / 操作指导书)
- **完整 thermal_station 真品** :课程仓库 `thermal_station/` · C3 起对照看

---

*r1 · 2026-05-18 · 跟 C2 段 3 / 段 6 PPT 拷文件命令对齐*
