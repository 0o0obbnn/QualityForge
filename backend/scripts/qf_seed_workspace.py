"""WP-01A 本地联调种子面：为既有用户追加第二个工作区（切换 e2e 前置）。

用法（对本地运行库执行，幂等——同名工作区已存在时直接返回其 id）：
    cd backend && uv run python scripts/qf_seed_workspace.py \
        --db "$SQLITE_PATH" --email admin@test.com --name 第二项目

种子内容：workspace + 复制能力集的成员关系 + 默认 ACTIVE Release。
注意：服务进程持有内存态，若后端正在运行请先重启后再切换（成员关系每请求重查，实际无需重启）。
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qf.services.planning_workflow import planning_workflow_service  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="SQLite 数据库文件路径")
    parser.add_argument("--email", required=True, help="既有用户邮箱")
    parser.add_argument("--name", required=True, help="新工作区名称")
    args = parser.parse_args()

    planning_workflow_service.reconfigure(args.db)

    with sqlite3.connect(args.db) as connection:
        row = connection.execute(
            "SELECT m.user_id, m.tenant_id FROM tenant_memberships m "
            "JOIN users u ON u.id = m.user_id "
            "WHERE u.email = ? AND m.is_active = 1 ORDER BY m.rowid LIMIT 1",
            (args.email.casefold(),),
        ).fetchone()
        if row is None:
            print(f"用户不存在：{args.email}")
            return 1
        user_id, tenant_id = row
        existing = connection.execute(
            "SELECT id FROM workspaces WHERE tenant_id = ? AND name = ?", (tenant_id, args.name)
        ).fetchone()
    if existing is not None:
        print(f"工作区已存在：{args.name} -> {existing[0]}")
        return 0

    seeded = planning_workflow_service.seed_workspace(tenant_id, user_id, args.name)
    print(f"已种子工作区：{args.name} -> {seeded['id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
