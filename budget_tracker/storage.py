import json
from pathlib import Path
from typing import Dict, List, Optional


class LocalStorage:
    def __init__(self, path: Path = Path("data.json")) -> None:
        self.path = path
        self.data = {"invite_codes": {}, "users": {}, "families": {}}
        if self.path.exists():
            self.data = json.loads(self.path.read_text())

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2))

    def get_sheet_by_invite(self, code: str) -> Optional[str]:
        return self.data["invite_codes"].get(code)

    def get_sheet_by_user(self, user_id: int) -> Optional[str]:
        return self.data["users"].get(str(user_id))

    def add_family(self, sheet_id: str, invite_code: str, creator_id: int) -> None:
        self.data["invite_codes"][invite_code] = sheet_id
        self.data["families"][sheet_id] = {
            "invite_code": invite_code,
            "members": [creator_id],
            "creator_id": creator_id,
        }
        self.data["users"][str(creator_id)] = sheet_id
        self.save()

    def add_user_to_family(self, sheet_id: str, user_id: int) -> None:
        fam = self.data["families"].setdefault(sheet_id, {})
        members: List[int] = fam.setdefault("members", [])
        if user_id not in members:
            members.append(user_id)
        self.data["users"][str(user_id)] = sheet_id
        self.save()
