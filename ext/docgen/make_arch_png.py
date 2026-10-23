#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用 Pillow 绘制 s2 方案架构图（PNG），替代 Word/PDF 里易跑版的 ASCII 架构图。
无需额外依赖（仅 Pillow）。CJK 使用系统 WenQuanYi 字体。

用法：python3 make_arch_png.py <输出.png>
"""
import sys
from PIL import Image, ImageDraw, ImageFont

FONT_PATH = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"

# 高分辨率绘制再缩放，获得更锐利的线条与文字
SCALE = 2
W, H = 1600, 920

# 配色
C_BG = (255, 255, 255)
C_OVERSEAS = (0xEF, 0xF4, 0xFB)   # 浅蓝
C_OVERSEAS_B = (0x2E, 0x6F, 0xB5)
C_CN = (0xED, 0xF7, 0xF0)         # 浅绿
C_CN_B = (0x2E, 0x8B, 0x57)
C_EXEC = (0xFB, 0xF3, 0xE6)       # 浅橙
C_EXEC_B = (0xC8, 0x7A, 0x1E)
C_REPO = (0xFF, 0xFF, 0xFF)
C_TEXT = (0x22, 0x22, 0x22)
C_SUB = (0x66, 0x66, 0x66)
C_ARROW = (0x44, 0x44, 0x44)


def font(sz, bold=False):
    # wqy-zenhei.ttc 第 0 个 face 即正黑
    return ImageFont.truetype(FONT_PATH, sz * SCALE, index=0)


def s(v):
    return v * SCALE


def rrect(d, box, radius, fill, outline, width=2):
    d.rounded_rectangle([s(box[0]), s(box[1]), s(box[2]), s(box[3])],
                        radius=s(radius), fill=fill, outline=outline, width=s(width))


def text(d, xy, txt, fnt, fill=C_TEXT, anchor="la"):
    d.text((s(xy[0]), s(xy[1])), txt, font=fnt, fill=fill, anchor=anchor)


def center_text(d, box, txt, fnt, fill=C_TEXT):
    cx = (box[0] + box[2]) / 2
    cy = (box[1] + box[3]) / 2
    d.text((s(cx), s(cy)), txt, font=fnt, fill=fill, anchor="mm")


def arrow(d, p1, p2, color=C_ARROW, width=3, label=None, lfont=None, loffset=(0, -18)):
    x1, y1 = s(p1[0]), s(p1[1])
    x2, y2 = s(p2[0]), s(p2[1])
    d.line([x1, y1, x2, y2], fill=color, width=s(width))
    # 箭头头部
    import math
    ang = math.atan2(y2 - y1, x2 - x1)
    L = s(12)
    for da in (math.radians(22), -math.radians(22)):
        hx = x2 - L * math.cos(ang - da)
        hy = y2 - L * math.sin(ang - da)
        d.line([x2, y2, hx, hy], fill=color, width=s(width))
    if label and lfont:
        mx, my = (p1[0] + p2[0]) / 2 + loffset[0], (p1[1] + p2[1]) / 2 + loffset[1]
        text(d, (mx, my), label, lfont, fill=C_SUB, anchor="mm")


def build(out_path):
    img = Image.new("RGB", (s(W), s(H)), C_BG)
    d = ImageDraw.Draw(img)

    f_title = font(26, True)
    f_box = font(19, True)
    f_item = font(16)
    f_small = font(14)
    f_arrow = font(15)

    # 标题
    text(d, (W / 2, 30), "海外 repo 镜像同步到 AWS 中国区 ECR — 架构图", f_title,
         fill=C_CN_B, anchor="ma")

    # ---- 左：海外源 registry ----
    overseas = (60, 110, 520, 360)
    rrect(d, overseas, 14, C_OVERSEAS, C_OVERSEAS_B, 2)
    text(d, (overseas[0] + 20, overseas[1] + 16), "海外源 registry", f_box, fill=C_OVERSEAS_B)
    for i, line in enumerate(["- Docker Hub", "- gcr.io（Google）", "- ghcr.io", "- 海外 global ECR"]):
        text(d, (overseas[0] + 28, overseas[1] + 58 + i * 38), line, f_item)
    text(d, (overseas[0] + 20, overseas[3] - 34),
         "源清单：images.yaml（--src yaml）", f_small, fill=C_SUB)

    # ---- 右：中国区 ECR ----
    cn = (1040, 110, 1540, 470)
    rrect(d, cn, 14, C_CN, C_CN_B, 2)
    text(d, (cn[0] + 20, cn[1] + 16), "AWS 中国区（aws-cn）ECR", f_box, fill=C_CN_B)
    text(d, (cn[0] + 20, cn[1] + 52),
         "<acct>.dkr.ecr.cn-northwest-1", f_small, fill=C_SUB)
    text(d, (cn[0] + 20, cn[1] + 74), ".amazonaws.com.cn", f_small, fill=C_SUB)
    repos = ["mirror/pause", "mirror/busybox", "mirror/static-debian12", "mirror/python ..."]
    for i, r in enumerate(repos):
        rb = (cn[0] + 24, cn[1] + 110 + i * 54, cn[2] - 24, cn[1] + 150 + i * 54)
        rrect(d, rb, 8, C_REPO, C_CN_B, 1)
        center_text(d, rb, r, f_item, fill=C_TEXT)

    # ---- 下：同步执行者 ----
    ex = (60, 560, 520, 860)
    rrect(d, ex, 14, C_EXEC, C_EXEC_B, 2)
    text(d, (ex[0] + 20, ex[1] + 16), "同步执行者（三选一）", f_box, fill=C_EXEC_B)
    for i, line in enumerate([
        "A. 中国区 EC2 + systemd timer（推荐）",
        "B. Bitbucket Pipelines（Scheduled）",
        "C. 本地 / CI 手动 / crontab",
    ]):
        text(d, (ex[0] + 28, ex[1] + 64 + i * 46), line, f_item)
    text(d, (ex[0] + 20, ex[3] - 70), "运行 sync_ecr.sh：", f_small, fill=C_SUB)
    text(d, (ex[0] + 20, ex[3] - 48),
         "dry-run 算目标 → 自动建仓 → skopeo sync", f_small, fill=C_SUB)

    # ---- 右下：中国区使用方 ----
    user = (1040, 620, 1540, 820)
    rrect(d, user, 14, C_CN, C_CN_B, 2)
    text(d, (user[0] + 20, user[1] + 16), "中国区使用方", f_box, fill=C_CN_B)
    for i, line in enumerate(["- ECS / EKS 拉取镜像", "- EC2 / CodeBuild", "- 区内流量，快且稳"]):
        text(d, (user[0] + 28, user[1] + 58 + i * 40), line, f_item)

    # ---- 箭头 ----
    # 执行者 读取 源清单 -> 海外源（向上）
    arrow(d, (290, 560), (290, 362), label="读取 images.yaml", lfont=f_arrow, loffset=(90, 0))
    # 海外源 --跨境 skopeo sync--> 中国区 ECR（主链路）
    arrow(d, (522, 235), (1038, 235), label="skopeo sync / copy（跨境 + 重试）",
          lfont=f_arrow, loffset=(0, -22))
    # 执行者 push -> 中国区 ECR（落在 ECR 框左下边缘，避开 repo 小框）
    arrow(d, (522, 640), (1038, 430), label="push（建仓 + 写入）",
          lfont=f_arrow, loffset=(20, -22))
    # 中国区 ECR -> 使用方
    arrow(d, (1290, 472), (1290, 618), label="pull", lfont=f_arrow, loffset=(40, 0))

    # 说明脚注
    text(d, (60, 884),
         "关键链路：仅「执行者拉取海外源」一跳跨境；执行者放在中国区 EC2 时，push 为区内流量，最稳定。",
         f_small, fill=C_SUB)

    img = img.resize((W, H), Image.LANCZOS)
    img.save(out_path, "PNG")
    print("saved:", out_path)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "arch.png"
    build(out)
