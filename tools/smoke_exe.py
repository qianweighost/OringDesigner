# -*- coding: utf-8 -*-
"""对打包好的 exe 做启动存活冒烟测试。

背景：PyInstaller 的 onefile 模式会把 QtSvg 之外的插件裁掉，
打包「成功」并不等于「能起来」——缺 DLL / 缺插件时 exe 会静默退出或弹错误框。
所以每次出包都要真启动一次，确认进程能活过冷启动阶段。

用法：
    python tools/smoke_exe.py                     # 用默认 dist/ 产物
    python tools/smoke_exe.py path/to/x.exe       # 指定产物
    python tools/smoke_exe.py --keep 5            # 存活判定时间（秒，默认 4）

退出码：0 = 通过，1 = 失败。
"""
from __future__ import annotations

import os
import subprocess
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
DEFAULT_EXE = os.path.join(_ROOT, "dist", "O型密封圈设计计算器.exe")

# onefile 每次启动都要解压到临时目录，冷启动偏慢，判定时间给宽一点
DEFAULT_KEEP = 4.0


def smoke(exe: str, keep: float = DEFAULT_KEEP) -> bool:
    print("产物: %s" % exe)
    if not os.path.isfile(exe):
        print("  ✗ 文件不存在")
        return False
    size = os.path.getsize(exe)
    with open(exe, "rb") as f:
        head = f.read(2)
    print("  大小: %.1f MB   头部魔术: %r" % (size / 1048576.0, head))
    if head != b"MZ":
        print("  ✗ 不是有效的 Windows 可执行文件")
        return False

    t0 = time.time()
    proc = subprocess.Popen([exe], cwd=_ROOT)
    print("  已启动 pid=%s，存活判定 %.1fs ..." % (proc.pid, keep))
    time.sleep(keep)
    rc = proc.poll()
    alive = rc is None
    print("  冷启动耗时: %.1fs" % (time.time() - t0))

    if alive:
        print("  ✓ 进程存活（未在冷启动阶段退出）")
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("  已关闭。")
        return True

    print("  ✗ 进程已退出，退出码 = %s（说明启动失败）" % rc)
    return False


def main(argv) -> int:
    keep = DEFAULT_KEEP
    exe = None
    rest = list(argv[1:])
    while rest:
        a = rest.pop(0)
        if a == "--keep" and rest:
            keep = float(rest.pop(0))
        elif a.startswith("--"):
            continue
        else:
            exe = a
    exe = os.path.abspath(exe or DEFAULT_EXE)
    ok = smoke(exe, keep)
    print()
    print("冒烟测试：%s" % ("通过 ✓" if ok else "失败 ✗"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
