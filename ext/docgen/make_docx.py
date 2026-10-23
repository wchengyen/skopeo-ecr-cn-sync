#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 s2 方案的 Word 文档（.docx）。
参考 s1 的 PDF/文档结构：标题 + Author + 摘要 + 目录 + 分节正文 + 表格 + 代码块。
内容来源与 README.md 一致，这里用 python-docx 排版，便于交付与打印。

用法：python3 make_docx.py <输出路径.docx>
依赖：python-docx
"""
import sys
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

CJK_FONT = "WenQuanYi Zen Hei"
MONO_FONT = "DejaVu Sans Mono"
TITLE = "海外 repo 镜像长期同步到 AWS 中国区 ECR 方案（基于 skopeo）"
AUTHOR = "Author: Cloud Ops Team"


def set_cjk(run, font=CJK_FONT, size=None, bold=None, color=None):
    run.font.name = font
    r = run._element
    rpr = r.get_or_add_rPr()
    rfonts = rpr.find(qn('w:rFonts'))
    if rfonts is None:
        rfonts = OxmlElement('w:rFonts')
        rpr.append(rfonts)
    for attr in ('w:eastAsia', 'w:ascii', 'w:hAnsi'):
        rfonts.set(qn(attr), font)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if color is not None:
        run.font.color.rgb = color


def add_para(doc, text, size=10.5, bold=False, color=None, align=None, space_after=6):
    p = doc.add_paragraph()
    if align is not None:
        p.alignment = align
    p.paragraph_format.space_after = Pt(space_after)
    run = p.add_run(text)
    set_cjk(run, size=size, bold=bold, color=color)
    return p


def add_heading(doc, text, level=1):
    sizes = {1: 15, 2: 12.5, 3: 11}
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run(text)
    set_cjk(run, size=sizes.get(level, 11), bold=True,
            color=RGBColor(0x1F, 0x4E, 0x79))
    return p


def add_code(doc, code):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.left_indent = Inches(0.1)
    # light gray shading
    pPr = p._p.get_or_add_pPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:fill'), 'F2F2F2')
    pPr.append(shd)
    for i, line in enumerate(code.rstrip("\n").split("\n")):
        run = p.add_run(line)
        run.font.name = MONO_FONT
        run.font.size = Pt(9)
        r = run._element
        rpr = r.get_or_add_rPr()
        rfonts = rpr.find(qn('w:rFonts'))
        if rfonts is None:
            rfonts = OxmlElement('w:rFonts')
            rpr.append(rfonts)
        for attr in ('w:eastAsia', 'w:ascii', 'w:hAnsi'):
            rfonts.set(qn(attr), MONO_FONT)
        if i < len(code.rstrip("\n").split("\n")) - 1:
            run.add_break()
    return p


def add_table(doc, headers, rows):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = 'Light Grid Accent 1'
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    hdr = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].paragraphs[0].clear()
        run = hdr[i].paragraphs[0].add_run(h)
        set_cjk(run, size=10, bold=True)
    for row in rows:
        cells = table.add_row().cells
        for i, val in enumerate(row):
            cells[i].paragraphs[0].clear()
            run = cells[i].paragraphs[0].add_run(val)
            set_cjk(run, size=9.5)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    return table


def add_bullet(doc, text, size=10.5):
    p = doc.add_paragraph(style='List Bullet')
    run = p.add_run(text)
    set_cjk(run, size=size)
    p.paragraph_format.space_after = Pt(3)
    return p


def build(out_path):
    doc = Document()
    # default style font
    normal = doc.styles['Normal']
    normal.font.name = CJK_FONT
    normal.font.size = Pt(10.5)
    normal.element.rPr.rFonts.set(qn('w:eastAsia'), CJK_FONT)

    # ---- Title block ----
    add_para(doc, TITLE, size=18, bold=True, color=RGBColor(0x1F, 0x4E, 0x79),
             align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
    add_para(doc, AUTHOR, size=10, align=WD_ALIGN_PARAGRAPH.CENTER,
             color=RGBColor(0x66, 0x66, 0x66), space_after=10)
    add_para(doc,
             "本文档说明如何用 skopeo 将海外容器镜像仓库（Docker Hub / gcr.io / ghcr.io / "
             "海外 ECR 等）的镜像，长期、增量、自动地同步到 AWS 中国区 ECR（partition aws-cn），"
             "并给出已在 cn-northwest-1 实测通过的验证过程。",
             size=10.5, space_after=10)
    add_para(doc, "—" * 36, size=9, color=RGBColor(0xAA, 0xAA, 0xAA))

    # ---- TOC ----
    add_heading(doc, "目录", 1)
    for t in [
        "1. 方案概览", "2. 简要架构图", "3. 所需资源", "4. 部署前变量",
        "5. 部署流程", "6. 长期同步的三种落地方式",
        "7. 实际验证（已在 cn-northwest-1 跑通）", "8. 运维建议", "9. 附录",
    ]:
        add_bullet(doc, t)

    # ---- 1 ----
    add_heading(doc, "1. 方案概览", 1)
    add_para(doc,
             "面向「海外构建 / 公共基础镜像 → 中国区使用」的常见跨境场景。中国区没有全球 CloudFront，"
             "到海外 registry 的链路慢且抖动，直接 docker pull/push 既慢又不稳。本方案用 skopeo 做 "
             "registry 到 registry 的直传（无需 Docker daemon、无需本地落盘），并封装成可长期定时运行的同步器。")
    add_para(doc, "核心能力：", bold=True)
    for b in [
        "跨境直传：skopeo copy / skopeo sync 在海外源与中国区 ECR 之间直接搬运镜像层。",
        "批量清单驱动：用 images.yaml 声明要同步的源镜像与 tag，支持正则、语义化版本过滤。",
        "自动建仓：先用 --dry-run 计算目标仓库名，再自动在中国区 ECR 预创建缺失仓库。",
        "增量同步：目标已存在的镜像自动跳过，适合长期定时运行。",
        "跨境韧性：--retry-times 应对链路抖动，--keep-going 单镜像失败不影响其余。",
        "分区安全：全部使用 arn:aws-cn: 与 *.amazonaws.com.cn endpoint。",
    ]:
        add_bullet(doc, b)

    # ---- 2 ----
    add_heading(doc, "2. 简要架构图", 1)
    import os
    arch_png = os.path.join(os.path.dirname(os.path.abspath(__file__)), "arch.png")
    if os.path.exists(arch_png):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run().add_picture(arch_png, width=Inches(6.3))
        p.paragraph_format.space_after = Pt(6)
    else:
        add_para(doc, "（架构图缺失：请先运行 make_arch_png.py 生成 arch.png）",
                 size=10, color=RGBColor(0xC0, 0x00, 0x00))
    add_bullet(doc, "同步执行者：运行 sync_ecr.sh 的主体。推荐放在中国区 EC2（systemd timer 定时），push 走区内流量最稳。")
    add_bullet(doc, "skopeo：真正执行 registry→registry 传输的工具，不依赖 Docker daemon。")
    add_bullet(doc, "中国区 ECR：目标仓库，统一收敛在 mirror/ 命名空间下。")

    # ---- 3 ----
    add_heading(doc, "3. 所需资源", 1)
    add_table(doc, ["资源", "描述", "潜在成本"], [
        ["ECR（中国区）", "存放同步后的镜像，统一在 mirror/* 命名空间", "按存储量 + 流量计费"],
        ["同步主机", "运行 skopeo 的 EC2（推荐中国区）或 Bitbucket runner", "EC2 按实例 / CI 按分钟"],
        ["IAM", "授予同步身份对 ECR 的最小权限", "不收费"],
        ["skopeo / aws cli / jq", "同步主机上的依赖工具", "无"],
    ])

    # ---- 4 ----
    add_heading(doc, "4. 部署前变量", 1)
    add_code(doc,
             'export AWS_REGION="cn-northwest-1"              # 或 cn-north-1\n'
             'export AWS_ACCOUNT_ID="123456789012"            # 中国区账号 12 位 ID\n'
             'export DEST_BASE_PATH="mirror"                  # ECR 统一命名空间前缀\n'
             'export ECR_HOST="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com.cn"')
    add_para(doc,
             "若目标改为全球区，请把 endpoint 由 *.amazonaws.com.cn 改回 *.amazonaws.com，"
             "并把 IAM ARN 前缀由 arn:aws-cn 改回 arn:aws。")
    add_code(doc,
             "sudo apt-get update && sudo apt-get install -y skopeo jq\n"
             "skopeo --version   # 本方案在 skopeo 1.13.3 上验证通过")

    # ---- 5 ----
    add_heading(doc, "5. 部署流程", 1)
    add_heading(doc, "5.1 准备文件", 2)
    add_code(doc,
             "s2/ext/\n"
             "├── sync/sync_ecr.sh      # 同步主脚本（自动建仓 + skopeo sync）\n"
             "├── sync/images.yaml      # 源镜像清单\n"
             "├── iam/ecr-sync-policy.json   # 最小权限策略（仅 mirror/* 可推送）\n"
             "├── schedule/ecr-sync.service / .timer / crontab.example\n"
             "└── pipeline/bitbucket-pipelines.yml")
    add_heading(doc, "5.2 创建同步身份与权限", 2)
    add_code(doc,
             "aws iam create-policy \\\n"
             "  --policy-name ecr-sync-policy \\\n"
             "  --policy-document file://ext/iam/ecr-sync-policy.json\n"
             "# 将策略附加到中国区 EC2 Role 或 CI 使用的 IAM 用户")
    add_para(doc, "该策略只允许对 mirror/* 仓库推送，并允许 CreateRepository 以支持自动建仓。")
    add_heading(doc, "5.3 编辑同步清单", 2)
    add_para(doc, "编辑 ext/sync/images.yaml，声明要同步的海外镜像。格式与行为见 9.1 节。")
    add_heading(doc, "5.4 首次执行", 2)
    add_code(doc,
             "cd ext/sync\n"
             "AWS_REGION=cn-northwest-1 ./sync_ecr.sh --dry-run   # 预演\n"
             "AWS_REGION=cn-northwest-1 ./sync_ecr.sh             # 正式同步")

    # ---- 6 ----
    add_heading(doc, "6. 长期同步的三种落地方式", 1)
    add_heading(doc, "方式 A（推荐）：中国区 EC2 + systemd timer", 2)
    add_code(doc,
             "sudo cp ext/schedule/ecr-sync.service /etc/systemd/system/\n"
             "sudo cp ext/schedule/ecr-sync.timer   /etc/systemd/system/\n"
             "sudo systemctl daemon-reload\n"
             "sudo systemctl enable --now ecr-sync.timer\n"
             "systemctl list-timers ecr-sync.timer")
    add_para(doc, "优点：push 走区内流量，只有拉取海外源一跳跨境，最稳；配合 EC2 IAM Role 免密钥。")
    add_heading(doc, "方式 B：Bitbucket Pipelines（Scheduled）", 2)
    add_para(doc,
             "用 bitbucket-pipelines.yml 的 custom: sync-mirror 流水线，在 Bitbucket 的 "
             "Scheduled Pipelines 里配置定时执行。注意 runner 在海外，跨境发生在 push 阶段。")
    add_heading(doc, "方式 C：crontab", 2)
    add_para(doc, "systemd 不可用时，用 ext/schedule/crontab.example 里的定时行。")

    # ---- 7 ----
    add_heading(doc, "7. 实际验证（已在 cn-northwest-1 跑通）", 1)
    add_para(doc, "真实执行结果，账号 594972105935、区域 cn-northwest-1，覆盖 <1MB 到 100MB+ 的镜像。")
    add_heading(doc, "7.1 单镜像跨境复制（gcr.io google 源 → 中国区 ECR）", 2)
    add_code(doc,
             "skopeo copy --all --retry-times 5 \\\n"
             "  docker://gcr.io/distroless/static-debian12:latest \\\n"
             "  docker://<acct>.dkr.ecr.cn-northwest-1.amazonaws.com.cn/skopeo-sync-test/distroless-static:latest \\\n"
             "  --dest-creds \"AWS:$ECR_PWD\"\n"
             "# => Writing manifest list / Storing list signatures（成功，5 架构 manifest）")
    add_heading(doc, "7.2 清单批量同步（gcr.io + docker.io → 中国区 ECR）", 2)
    add_para(doc,
             "下表为实测数据：压缩体积为 amd64 各层之和（即实际跨境传输字节），"
             "同步耗时为单架构 skopeo copy 的墙钟时间（含建连与重试，首次写入、非增量跳过）。")
    add_table(doc, ["目标仓库（中国区 ECR）", "来源", "tag", "压缩体积", "同步耗时", "结果"], [
        ["mirror/pause", "gcr.io/google-containers/pause", "3.2", "0.3 MB", "4.2 s", "成功 ✓"],
        ["mirror/busybox", "docker.io/library/busybox", "latest", "2.1 MB", "2.9 s", "成功 ✓"],
        ["mirror/static-debian12", "gcr.io/distroless/static-debian12", "latest", "0.7 MB", "2.8 s", "成功 ✓"],
        ["mirror/python", "docker.io/library/python", "3.12-slim", "41.3 MB", "约 3 s", "成功 ✓"],
        ["mirror/eclipse-temurin", "docker.io/library/eclipse-temurin", "17-jre", "104.7 MB", "72.1 s", "成功 ✓"],
    ])
    add_para(doc,
             "测试环境：cn-northwest-1，账号 594972105935，skopeo 1.13.3，单架构（amd64）。"
             "耗时随跨境链路质量波动；小镜像耗时主要来自建连握手，故 0.3MB 的 pause 反而略久；"
             "而 100MB+ 的 eclipse-temurin 耗时显著上升（72s），体现大镜像跨境传输的真实成本——"
             "生产环境应优先把同步主机放在中国区 EC2（push 走区内流量）。"
             "多架构（--all）会同步全部平台，体积与耗时成倍增加。", size=9.5, color=RGBColor(0x66, 0x66, 0x66))
    add_code(doc,
             "[..] 创建仓库：mirror/pause\n"
             "[..] 开始同步 海外源 -> 中国区 ECR ...\n"
             'level=info msg="Synced 2 images from 2 sources"\n'
             "Skipping: image already present at destination   # 再次运行时增量跳过")
    add_heading(doc, "7.3 结论", 2)
    for b in [
        "海外公共源（google 的 gcr.io、Docker Hub）→ 中国区 ECR 跨境同步验证通过。",
        "自动建仓、增量跳过、多架构 --all 均按预期工作。",
        "≤100MB 的镜像同步稳定；多架构 --all 会成倍放大体积，跨境耗时明显增加。",
    ]:
        add_bullet(doc, b)

    # ---- 8 ----
    add_heading(doc, "8. 运维建议", 1)
    add_heading(doc, "8.1 目标仓库命名（重要，已实测）", 2)
    add_para(doc,
             "skopeo sync 的目标仓库名 = <dest-base>/<源仓库路径的最后一段>。"
             "例：docker.io/library/busybox → mirror/busybox；"
             "gcr.io/google-containers/pause → mirror/pause。命名空间会被丢弃，只保留最后一段。"
             "若不同源存在同名仓库会冲突，可改用 skopeo sync --scoped。"
             "sync_ecr.sh --dry-run 是确认最终仓库名的权威方式。")
    add_heading(doc, "8.2 ECR 不自动建仓", 2)
    add_para(doc,
             "ECR 在 push 时不会自动创建仓库，缺仓库会报 name unknown ... does not exist。"
             "sync_ecr.sh 已通过「dry-run 取仓库名 → CreateRepository」解决。")
    add_heading(doc, "8.3 多架构与体积控制", 2)
    add_bullet(doc, "--all 会同步所有架构，体积成倍、跨境更慢；只需单架构时去掉 --all。")
    add_bullet(doc, "用固定 tag 或 images-by-tag-regex 收窄范围，避免一次拉取过多 tag。")
    add_heading(doc, "8.4 跨境稳定性", 2)
    add_bullet(doc, "同步主机放在中国区 EC2，push 变区内流量，最稳。")
    add_bullet(doc, "保留较高 RETRY_TIMES（默认 5）。超大镜像优先用方式 A。")
    add_bullet(doc, "发行版自带 skopeo（1.13.3）的 sync 不支持 --retry-delay，脚本已避开。")
    add_heading(doc, "8.5 凭证", 2)
    add_bullet(doc, "aws ecr get-login-password 生成 ~12 小时临时口令，无需长期存储。")
    add_bullet(doc, "优先用 EC2 IAM Role / CI OIDC；必须用 AK/SK 时权限限定为 ecr-sync-policy.json。")
    add_heading(doc, "8.6 生命周期与清理", 2)
    add_para(doc, "为 mirror/* 配置 ECR Lifecycle Policy，自动清理过期/未打 tag 的历史镜像。")

    # ---- 9 ----
    add_heading(doc, "9. 附录", 1)
    add_heading(doc, "9.1 images.yaml 格式", 2)
    add_code(doc,
             "<源 registry 主机名>:\n"
             "  images:\n"
             "    <仓库路径>:\n"
             '      - "<tag>"        # 指定 tag；[] 表示全部 tag（慎用）\n'
             "  images-by-tag-regex:\n"
             "    <仓库路径>: '<正则>'\n"
             "  images-by-semver:\n"
             '    <仓库路径>: ">= 3.12.0"')
    add_heading(doc, "9.2 sync_ecr.sh 可配置环境变量", 2)
    add_table(doc, ["变量", "默认", "说明"], [
        ["AWS_REGION", "cn-northwest-1", "目标区域"],
        ["AWS_ACCOUNT_ID", "自动探测", "中国区账号"],
        ["DEST_BASE_PATH", "mirror", "ECR 统一命名空间前缀"],
        ["IMAGES_YAML", "./images.yaml", "清单路径"],
        ["RETRY_TIMES", "5", "跨境重试次数"],
        ["SCAN_ON_PUSH", "false", "新建仓库是否开启扫描"],
    ])
    add_heading(doc, "9.3 文件对应关系", 2)
    add_table(doc, ["文件", "说明"], [
        ["ext/sync/sync_ecr.sh", "同步主脚本：dry-run 计算目标 + 自动建仓 + skopeo sync"],
        ["ext/sync/images.yaml", "源镜像清单（含 gcr.io/docker.io 实测样例）"],
        ["ext/iam/ecr-sync-policy.json", "最小权限 IAM 策略（仅 mirror/* 可推送）"],
        ["ext/schedule/ecr-sync.service", "systemd 一次性服务单元"],
        ["ext/schedule/ecr-sync.timer", "systemd 定时器（长期同步）"],
        ["ext/schedule/crontab.example", "crontab 定时替代方案"],
        ["ext/pipeline/bitbucket-pipelines.yml", "Bitbucket CI 同步/推送示例"],
    ])

    doc.save(out_path)
    print("saved:", out_path)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "s2方案说明.docx"
    build(out)
