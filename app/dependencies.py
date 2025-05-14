from typing import Annotated

from fastapi import Depends

from app.auth.dependencies import get_current_user, get_admin_user

CurrentUser = Annotated[dict, Depends(get_current_user)]

CurrentAdminUser = Annotated[dict, Depends(get_admin_user)]
