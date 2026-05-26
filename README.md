# my-station

这是你这门课的个人项目仓库 · 整个学期就这一个 · 不要在 Gitee 上自己再开新的。

老师已经在 Gitee 把你加为成员 · 你登录自己的 Gitee 账号 · 在 **"我参与的仓库"** 列表里能直接看到。

## clone 到本地

1. 点进自己的仓库 → 右上角 **克隆/下载** → 复制链接
2. 本地随便建个目录(比如 `~/python-course/`) · 在里面执行:

```bash
git clone <你刚复制的 URL>
cd my-station-XXXX-yyy/
```

3. 第一次用 git 还要配一下身份(只配一次 · 全局):

```bash
git config --global user.name "你的名字"
git config --global user.email "你的邮箱"
```

## 目录结构

```
my-station-XXXX-yyy/
├── .gitignore
├── README.md               本文件
└── materials/              老师准备的代码 · 课中按需拷出来用
```

学期中老师可能往 `materials/` 里加新东西 · `git pull` 就能拿到。

## 基本 git 工作流

每完成一小段就提交一次。命令永远是这三行:

```bash
git add .
git commit -m "说明这次做了啥"
git push
```

## 几条注意

- **不要** clone 后又 `git init` — 会把模板 .git 覆盖掉
- **不要** `git push --force` 或 `git reset --hard`(改坏了找老师)
- **不要** 把 `.venv/` `__pycache__/` 之类 commit 进去(`.gitignore` 已经挡了)
- 默认分支是 **master**(不是 main)

## 隐私

仓库默认 **private** · 只你 + 老师能看。push 上去 = 已经交给老师。不用单独发 URL · 老师后台批量看 commit 记录。
