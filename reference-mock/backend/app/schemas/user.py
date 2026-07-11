"""ユーザー I/O スキーマ。"""

import uuid

from pydantic import BaseModel, ConfigDict


class UserOut(BaseModel):
    """認証済みユーザーの公開表現。"""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str
    role: str
