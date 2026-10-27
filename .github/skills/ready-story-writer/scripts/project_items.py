"""列出 GitHub Project 指定欄位中缺少 User Story / Acceptance Criteria 的 item，並回寫內容。

需要 gh CLI，且 token 具備 project scope（gh auth refresh -s project）。

用法：
  python project_items.py list --owner OWNER --project NUMBER [--column Ready] [--all]
  python project_items.py update --item-json ITEM.json --body-file BODY.md
"""

import argparse
import json
import re
import subprocess
import sys

USER_STORY_RE = re.compile(r"^#{1,6}\s*(User Story|使用者故事)\b", re.IGNORECASE | re.MULTILINE)
ACCEPTANCE_RE = re.compile(r"^#{1,6}\s*(Acceptance Criteria|驗收條件)\b", re.IGNORECASE | re.MULTILINE)

ITEMS_QUERY = """
query($owner: String!, $number: Int!, $cursor: String) {
  repositoryOwner(login: $owner) {
    ... on User { projectV2(number: $number) { ...P } }
    ... on Organization { projectV2(number: $number) { ...P } }
  }
}
fragment P on ProjectV2 {
  id
  title
  items(first: 100, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    nodes {
      id
      type
      status: fieldValueByName(name: "Status") {
        ... on ProjectV2ItemFieldSingleSelectValue { name }
      }
      content {
        ... on Issue { id number title body url repository { nameWithOwner } }
        ... on DraftIssue { id title body }
      }
    }
  }
}
"""

UPDATE_ISSUE = """
mutation($id: ID!, $body: String!) {
  updateIssue(input: {id: $id, body: $body}) { issue { url } }
}
"""

UPDATE_DRAFT = """
mutation($id: ID!, $body: String!) {
  updateProjectV2DraftIssue(input: {draftIssueId: $id, body: $body}) { draftIssue { id } }
}
"""


def graphql(query, **variables):
    args = ["gh", "api", "graphql", "-f", f"query={query}"]
    for key, value in variables.items():
        if value is None:
            continue
        flag = "-F" if isinstance(value, int) else "-f"
        args += [flag, f"{key}={value}"]
    proc = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        sys.exit(proc.stderr.strip() or proc.stdout.strip())
    return json.loads(proc.stdout)["data"]


def list_items(owner, number, column, include_complete):
    items, cursor = [], None
    while True:
        owner_node = graphql(ITEMS_QUERY, owner=owner, number=number, cursor=cursor)["repositoryOwner"]
        project = owner_node and owner_node.get("projectV2")
        if not project:
            sys.exit(f"找不到 {owner} 的 Project #{number}")
        page = project["items"]
        for node in page["nodes"]:
            status = (node.get("status") or {}).get("name")
            content = node.get("content") or {}
            if status != column or node["type"] not in ("ISSUE", "DRAFT_ISSUE"):
                continue
            body = content.get("body") or ""
            missing = [
                name
                for name, pattern in (("User Story", USER_STORY_RE), ("Acceptance Criteria", ACCEPTANCE_RE))
                if not pattern.search(body)
            ]
            if missing or include_complete:
                items.append({
                    "type": node["type"],
                    "content_id": content["id"],
                    "number": content.get("number"),
                    "repository": (content.get("repository") or {}).get("nameWithOwner"),
                    "url": content.get("url"),
                    "title": content["title"],
                    "body": body,
                    "missing": missing,
                })
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
    json.dump({"project": project["title"], "column": column, "items": items}, sys.stdout, ensure_ascii=False, indent=2)
    print()


def update_item(item, body):
    mutation = UPDATE_ISSUE if item["type"] == "ISSUE" else UPDATE_DRAFT
    graphql(mutation, id=item["content_id"], body=body)
    print(f"已更新：{item.get('url') or item['title']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    list_parser = sub.add_parser("list", help="列出指定欄位中缺少 User Story / Acceptance Criteria 的 item")
    list_parser.add_argument("--owner", required=True, help="Project 擁有者（使用者或組織）")
    list_parser.add_argument("--project", required=True, type=int, help="Project 編號")
    list_parser.add_argument("--column", default="Ready", help="Status 欄位名稱，預設 Ready")
    list_parser.add_argument("--all", action="store_true", help="連已完整的 item 一起列出")

    update_parser = sub.add_parser("update", help="以新的內容覆寫 item 的 body")
    update_parser.add_argument("--item-json", required=True, help="list 輸出中單一 item 的 JSON 檔")
    update_parser.add_argument("--body-file", required=True, help="新的完整 body（Markdown）")

    args = parser.parse_args()
    if args.command == "list":
        list_items(args.owner, args.project, args.column, args.all)
    else:
        with open(args.item_json, encoding="utf-8") as f:
            item = json.load(f)
        with open(args.body_file, encoding="utf-8") as f:
            update_item(item, f.read())


if __name__ == "__main__":
    main()
