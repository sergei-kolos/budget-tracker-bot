import datetime
import uuid
from typing import List, Optional

import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import pandas as pd


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]


class SheetsManager:
    def __init__(self, index_sheet_id: str):
        self.index_sheet_id = index_sheet_id
        self.client = self._authorize()
        self.index_sheet = self.client.open_by_key(index_sheet_id).sheet1

    def _authorize(self) -> gspread.Client:
        try:
            return gspread.oauth()
        except Exception:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
            return gspread.authorize(creds)

    # ----- Family management -----
    def create_family(self, creator_id: int, creator_name: str) -> tuple[str, str]:
        family_id = str(uuid.uuid4())
        invite_code = uuid.uuid4().hex[:6].upper()
        spreadsheet = self.client.create(f"FamilyBudget_{family_id}")
        expenses = spreadsheet.add_worksheet("Expenses", rows=1, cols=6)
        meta = spreadsheet.add_worksheet("Meta", rows=2, cols=2)
        spreadsheet.del_worksheet(spreadsheet.sheet1)

        meta.update("A1", [["key", "value"], ["family_id", family_id]])
        meta.update("A3", [["invite_code", invite_code], ["creator_id", str(creator_id)]])
        meta.update("A5", [["members", f"{creator_id}"], ["sheet_version", "v1"]])

        expenses.update(
            "A1",
            [[
                "timestamp",
                "user_id",
                "user_name",
                "category",
                "amount",
                "currency",
            ]],
        )

        # register in index sheet
        self.index_sheet.append_row([family_id, invite_code, spreadsheet.id])
        return spreadsheet.id, invite_code

    def find_family_by_invite(self, invite_code: str) -> Optional[str]:
        records = self.index_sheet.get_all_records()
        for record in records:
            if record.get("invite_code") == invite_code:
                return record.get("sheet_id") or record.get("sheetId")
        return None

    def add_member(self, sheet_id: str, user_id: int):
        sheet = self.client.open_by_key(sheet_id)
        meta = sheet.worksheet("Meta")
        data = meta.get_all_records(head=1)
        members = []
        for row in data:
            if row["key"] == "members":
                members = row["value"].split(",") if row["value"] else []
                break
        if str(user_id) not in members:
            members.append(str(user_id))
            meta.update_cell(5, 2, ",".join(members))

    def find_family_by_user(self, user_id: int) -> Optional[str]:
        records = self.index_sheet.get_all_records()
        for record in records:
            sheet_id = record.get("sheet_id") or record.get("sheetId")
            sheet = self.client.open_by_key(sheet_id)
            meta = sheet.worksheet("Meta")
            data = meta.get_all_records(head=1)
            for row in data:
                if row["key"] == "members":
                    members = row["value"].split(",") if row["value"] else []
                    if str(user_id) in members:
                        return sheet_id
        return None

    # ----- Expenses -----
    def append_expense(
        self,
        sheet_id: str,
        user_id: int,
        user_name: str,
        category: str,
        amount: float,
        currency: str,
    ) -> None:
        sheet = self.client.open_by_key(sheet_id)
        expenses = sheet.worksheet("Expenses")
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        expenses.append_row([ts, user_id, user_name, category, amount, currency])

    # ----- Reports -----
    def monthly_report(self, sheet_id: str) -> str:
        sheet = self.client.open_by_key(sheet_id)
        expenses = sheet.worksheet("Expenses")
        records = expenses.get_all_records()
        if not records:
            return "Нет данных за текущий месяц."

        df = pd.DataFrame(records)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        now = datetime.datetime.now()
        df = df[df["timestamp"].dt.month == now.month]

        if df.empty:
            return "Нет данных за текущий месяц."

        by_cat = df.groupby(["category", "currency"])["amount"].sum()
        by_user = df.groupby(["user_name", "currency"])["amount"].sum()

        lines = ["Отчёт за текущий месяц:", ""]
        lines.append("По категориям:")
        for (cat, cur), value in by_cat.items():
            lines.append(f"- {cat} {value} {cur}")
        lines.append("")
        lines.append("По пользователям:")
        for (user, cur), value in by_user.items():
            lines.append(f"- {user} {value} {cur}")
        return "\n".join(lines)
