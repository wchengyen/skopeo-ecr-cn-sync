#!/usr/bin/env bash
# =============================================================================
# sync_ecr.sh — 将海外 repo 的镜像长期同步到 AWS 中国区 ECR（基于 skopeo）
#
# 功能：
#   1) 读取 images.yaml（skopeo sync 源清单）
#   2) 用 skopeo --dry-run 计算将要写入的中国区 ECR 目标仓库名
#   3) 自动在中国区 ECR 预创建缺失的仓库（ECR 不会在 push 时自动建仓）
#   4) 执行 skopeo sync，将镜像从海外源同步到中国区 ECR（带重试、容错）
#
# 用法：
#   ./sync_ecr.sh                 # 正式同步
#   ./sync_ecr.sh --dry-run       # 只打印将要同步的 源->目标 映射，不写数据
#
# 依赖：aws cli v2、skopeo、jq
# 适用分区：aws-cn（中国区）。endpoint 为 *.amazonaws.com.cn
# =============================================================================
set -euo pipefail

# ---------- 可通过环境变量覆盖的配置 ----------
AWS_REGION="${AWS_REGION:-cn-northwest-1}"                 # cn-north-1 或 cn-northwest-1
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}"
ECR_HOST="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com.cn"
DEST_BASE_PATH="${DEST_BASE_PATH:-mirror}"                 # ECR 下的统一前缀命名空间
DEST_BASE="${ECR_HOST}/${DEST_BASE_PATH}"
IMAGES_YAML="${IMAGES_YAML:-$(dirname "$0")/images.yaml}"
RETRY_TIMES="${RETRY_TIMES:-5}"                            # 跨境抖动重试次数（skopeo sync 支持 --retry-times）
# 说明：--retry-delay 仅较新版 skopeo 的 sync 子命令支持；
#       发行版自带版本（如 Ubuntu 24.04 的 1.13.3）不支持，本脚本不使用它。
SCAN_ON_PUSH="${SCAN_ON_PUSH:-false}"                     # 新建仓库是否开启扫描

DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

log() { echo "[$(date '+%F %T')] $*"; }

command -v skopeo >/dev/null || { echo "ERROR: 需要安装 skopeo"; exit 1; }
command -v jq     >/dev/null || { echo "ERROR: 需要安装 jq"; exit 1; }
[[ -f "$IMAGES_YAML" ]]       || { echo "ERROR: 找不到清单 $IMAGES_YAML"; exit 1; }

log "区域=$AWS_REGION 账号=$AWS_ACCOUNT_ID 目标前缀=$DEST_BASE"

# ---------- 获取中国区 ECR 临时登录口令 ----------
log "获取中国区 ECR 登录口令..."
ECR_PWD="$(aws ecr get-login-password --region "$AWS_REGION")"

# ---------- 用 dry-run 计算目标仓库名（权威来源）----------
log "计算目标仓库清单（skopeo --dry-run）..."
MAP_OUTPUT="$(skopeo sync --src yaml --dest docker --dry-run --all \
  "$IMAGES_YAML" "$DEST_BASE" \
  --dest-creds "AWS:${ECR_PWD}" 2>&1 || true)"

echo "$MAP_OUTPUT" | grep -i "Would have copied" || true

# 从 to="docker://<host>/<repo>:<tag>" 提取 <repo>（去掉 host 和 tag）
mapfile -t TARGET_REPOS < <(
  echo "$MAP_OUTPUT" \
  | grep -oE 'to="docker://[^"]+"' \
  | sed -E 's#to="docker://[^/]+/##; s#:[^:/]+"$##' \
  | sort -u
)

if [[ ${#TARGET_REPOS[@]} -eq 0 ]]; then
  log "WARN: 未解析出任何目标仓库，请检查 images.yaml 与源可达性。"
fi

if [[ $DRY_RUN -eq 1 ]]; then
  log "DRY-RUN：以下目标仓库将被使用（缺失的会被创建）："
  printf '  - %s\n' "${TARGET_REPOS[@]:-<none>}"
  exit 0
fi

# ---------- 预创建缺失的 ECR 仓库 ----------
for repo in "${TARGET_REPOS[@]}"; do
  if aws ecr describe-repositories --repository-names "$repo" --region "$AWS_REGION" >/dev/null 2>&1; then
    log "仓库已存在：$repo"
  else
    log "创建仓库：$repo"
    aws ecr create-repository \
      --repository-name "$repo" \
      --region "$AWS_REGION" \
      --image-scanning-configuration "scanOnPush=${SCAN_ON_PUSH}" \
      --output text --query 'repository.repositoryUri' >/dev/null
  fi
done

# ---------- 执行同步 ----------
log "开始同步 海外源 -> 中国区 ECR ..."
skopeo sync --src yaml --dest docker \
  --all \
  --retry-times "$RETRY_TIMES" \
  --keep-going \
  "$IMAGES_YAML" "$DEST_BASE" \
  --dest-creds "AWS:${ECR_PWD}"

log "同步完成。校验结果："
for repo in "${TARGET_REPOS[@]}"; do
  tags="$(aws ecr describe-images --repository-name "$repo" --region "$AWS_REGION" \
          --query 'imageDetails[?imageTags!=`null`].imageTags[]' --output json 2>/dev/null || echo '[]')"
  log "  $repo => $tags"
done
log "全部完成。"
