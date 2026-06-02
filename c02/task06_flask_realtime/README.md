# C2 M06 课堂练习:Flask 实时仿真

## 1. 最终目录结构
粘贴 dir(或 ls)的结果。

## 2. 成功运行命令
uv run python hello_flask.py

## 3. 浏览器看到什么(描述或截图)
- 数字:当前温度 T 实时刷新
- 按钮:按住爬温 · 松开降温

## 4. 我跑通到了哪一步(打勾)
- [ √ ] 步骤 1:最小 Flask
- [ √ ] 步骤 2:前端 fetch
- [ √ ] 步骤 3:后台线程
- [ √ ] 步骤 4:Lock 保护
- [ √ ] 步骤 5:step_euler 真物理
- [ √ ] 步骤 6:按钮控制

## 5. 我遇到的一个错误
错误命令或操作 / 报错信息 / 原因分析 / 修复方法

## 6. 自检回答
1. 为什么 simulation_loop 必须放在后台线程里?
- simulation_loop() 是无限循环，如果放在主线程里会阻塞 app.run()，导致 Flask 服务无法启动。
所以要放到后台线程中，让仿真计算和 Web 服务同时运行。
2. 为什么 with state_lock 块内不能放 time.sleep?
- state_lock 是互斥锁，只应该保护对共享变量 state 的短时间读写。time.sleep() 是耗时等待，如果放在锁内，会一直占着锁，导致其他线程无法读取或修改 state。
3. /api/state(GET)和 /api/heater(POST)有什么本质区别?
- /api/state 是 GET，用于读取当前温度、时间、加热状态；/api/heater 是 POST，用于接收按钮命令，修改加热器开关状态。
4. use_reloader=False 不加会怎么样?
- 如果不写 use_reloader=False，在 debug 或自动重载开启时，Flask 可能重复启动程序，从而导致 simulation_loop() 被重复启动。写上它可以避免后台线程重复运行。

