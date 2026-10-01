import io
import re

with io.open("backend/app/api/v1/conversations.py", "r", encoding="utf-8") as f:
    content = f.read()

bad_block = """async def list_messages(
    conversation_id: uuid.UUID,
    db: DatabaseDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
    current_user: CurrentUserDep,
) -> PaginatedResponse[MessageResponse]:"""

good_block = """async def list_messages(
    conversation_id: uuid.UUID,
    db: DatabaseDep,
    current_user: CurrentUserDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> PaginatedResponse[MessageResponse]:"""

content = content.replace(bad_block, good_block)

with io.open("backend/app/api/v1/conversations.py", "w", encoding="utf-8") as f:
    f.write(content)
