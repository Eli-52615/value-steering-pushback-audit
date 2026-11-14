#!/bin/bash
# 把 code/ 同步到服务器,并把"提交号 + 是否有未提交改动"写进 .commit,供运行登记使用。
cd "$(dirname "$0")"
if [ -n "$(git status --porcelain)" ]; then echo "$(git rev-parse --short HEAD)+未提交改动" > .commit; echo "警告:有未提交的改动"; else git rev-parse --short HEAD > .commit; fi
rsync -az --exclude __pycache__ --exclude .git ./ vt:/root/autodl-tmp/sprint/code/ && echo "已同步 $(cat .commit)"
