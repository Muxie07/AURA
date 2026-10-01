with open("backend/app/api/deps.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
old_func = """
async def get_current_user(
    token_payload: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db_session)
):
"""
new_func = """
async def get_current_user(
    request: Request,
    token_payload: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db_session)
):
"""
text = text.replace(old_func.strip(), new_func.strip())

old_body = """
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
"""
new_body = """
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        request.state.organization_id = str(user.organization_id)
        return user
"""
text = text.replace(old_body.strip(), new_body.strip())

with open("backend/app/api/deps.py", "w", encoding="utf-8") as f:
    f.write(text)
