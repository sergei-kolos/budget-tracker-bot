from __future__ import annotations

import datetime as dt
import random
import string
from dataclasses import dataclass
from typing import List, Dict

import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


@dataclass
class BudgetSheet:
    sheet_id: str
    invite_code: str


class SheetsService:
    def __init__(self, creds_path: str) -> None:
        self.creds_path = creds_path
        self.client = gspread.authorize(Credentials.from_service_account_file(creds_path, scopes=SCOPES))

    def _generate_invite_code(self, length: int = 6) -> str:
        letters = string.ascii_uppercase + string.digits
        return "".join(random.choice(letters) for _ in range(length))

    def create_budget_sheet(self, creator_id: int) -> BudgetSheet:
        invite_code = self._generate_invite_code()
        spreadsheet = self.client.create(f"FamilyBudget_{creator_id}")

        sheet = spreadsheet.add_worksheet("Expenses", rows="100", cols="6")
        sheet.append_row(["timestamp", "user_id", "user_name", "category", "amount", "currency"])

        meta = spreadsheet.add_worksheet("Meta", rows="10", cols="2")
        meta.append_rows([
            ["family_id", spreadsheet.id],
            ["invite_code", invite_code],
            ["creator_id", creator_id],
            ["members", str(creator_id)],
            ["version", "v1"],
        ])
        # remove default sheet
        spreadsheet.del_worksheet(spreadsheet.sheet1)
        return BudgetSheet(spreadsheet.id, invite_code)

    def append_expense(self, sheet_id: str, row: List[str]) -> None:
        spreadsheet = self.client.open_by_key(sheet_id)
        expenses = spreadsheet.worksheet("Expenses")
        expenses.append_row(row)

    def add_member(self, sheet_id: str, user_id: int) -> None:
        spreadsheet = self.client.open_by_key(sheet_id)
        meta = spreadsheet.worksheet("Meta")
        data = meta.get_all_records()
        for i, r in enumerate(data, start=2):
            if r["key"] == "members":
                members = r["value"].split(",")
                if str(user_id) not in members:
                    members.append(str(user_id))
                meta.update_cell(i, 2, ",".join(members))
                break

    def fetch_month_records(self, sheet_id: str, month: dt.date) -> List[Dict[str, str]]:
        spreadsheet = self.client.open_by_key(sheet_id)
        expenses = spreadsheet.worksheet("Expenses")
        records = expenses.get_all_records()
        result = []
        for r in records:
            ts = dt.datetime.fromisoformat(r["timestamp"])
            if ts.year == month.year and ts.month == month.month:
                result.append(r)
        return result
