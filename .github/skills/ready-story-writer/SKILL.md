---
name: ready-story-writer
description: 檢查 GitHub Project 中 Ready 欄位的每個 work item，若尚未撰寫 User Story 或 Acceptance Criteria，依該 item 的 title（與既有內容、專案程式碼）自動撰寫並回寫到 issue / draft issue。當使用者要求「補齊 Ready 的 User Story / 驗收條件」、「整理 backlog」、「檢查 Ready 欄位」時使用。
---

# Ready Story Writer

為 GitHub Project「Ready」欄位中缺少 **User Story** 或 **Acceptance Criteria** 的 work item 補上內容。

## 前置條件

- 已安裝並登入 `gh` CLI，token 需有 `project` scope。若出現 `missing required scopes [read:project]`，請使用者執行：
  ```
  gh auth refresh -s project
  ```
- 需要 Project 的擁有者與編號。若使用者沒有提供，用 `gh project list --owner <owner>` 查詢；只有一個 Project 時直接使用，有多個時詢問使用者。本 repo 預設擁有者為 `boringman1031`。

## 步驟

### 1. 找出需要補齊的 item

```bash
python .github/skills/ready-story-writer/scripts/project_items.py list --owner <owner> --project <number>
```

- 輸出 JSON 中的 `items` 只包含 Status 為 Ready、且缺少任一段落的 Issue / Draft Issue（Pull Request 會略過）。
- `missing` 列出缺少的段落。標題為 `User Story` / `使用者故事`、`Acceptance Criteria` / `驗收條件` 的 Markdown heading 都視為已存在。
- 欄位名稱不是 `Ready` 時，加上 `--column "<名稱>"`。
- `items` 為空時，回報「Ready 欄位所有 item 都已完整」並結束。

### 2. 理解情境

撰寫前先快速讀過 `README.md` 與相關程式碼（本 repo 為 Flask BMI 計算器：`app.py`、`templates/`、`static/`、`tests/`），讓內容貼合實際功能、用語與限制，而不是寫泛用的範本。

### 3. 撰寫內容

依 item 的 `title`（以及 `body` 中既有的描述）撰寫，**只補缺少的段落**，保留原有內容不動，將新段落附加在原 body 之後。語言跟隨 title（中文 title 用繁體中文）。

格式：

```markdown
## User Story

身為<角色>，我想要<功能/行為>，以便<價值/目的>。

## Acceptance Criteria

- [ ] **Given** <前提>，**When** <操作>，**Then** <可驗證的結果>
- [ ] ...
```

撰寫原則：

- User Story：一句話，角色具體（例如「使用 BMI 計算器的成人使用者」），價值要說明為什麼需要。
- Acceptance Criteria：3–6 條，每條都可以被測試或人工驗證；涵蓋正常流程、邊界值與錯誤輸入（若適用）；寫出具體的數值、文字或畫面行為，避免「正確顯示」「運作正常」這類模糊描述。
- 若 title 資訊太少、無法合理推斷需求，仍寫出最合理的版本，並在回報中標註「需人工確認」。
- 不要更改 title、labels、assignees 或 Status。

### 4. 回寫

每個 item：

1. 把 `items` 中該 item 的 JSON 物件存成暫存檔（例如 `item.json`）。
2. 把完整的新 body（原內容 + 新段落）存成 `body.md`。
3. 執行：
   ```bash
   python .github/skills/ready-story-writer/scripts/project_items.py update --item-json item.json --body-file body.md
   ```

完成後刪除暫存檔。

### 5. 回報

全部完成後，再執行一次步驟 1 的 `list` 確認 `items` 為空，並以表格回報：item（連結或 title）、補上的段落、是否需人工確認。
