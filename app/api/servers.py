from typing import Annotated, List
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ulid import ulid
from app.database import get_db
from app.models.models import DBServer, DBUser
from app.schemas.schemas import ServerCreate, ServerResponse
from app.security.auth import get_current_active_user

router = APIRouter(tags=["servers"])


@router.post("/servers", response_model=ServerResponse)
async def create_server(
    server: ServerCreate,
    current_user: Annotated[DBUser, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    server_ulid = str(ulid)
    db_server = DBServer(
        server_ulid=server_ulid,
        server_name=server.server_name,
        owner_id=current_user.id,
        last_seen=datetime.now()
    )
    
    db.add(db_server)
    db.commit()
    db.refresh(db_server)
    
    return ServerResponse(
        server_ulid=db_server.server_ulid,
        server_name=db_server.server_name,
        status="online"
    )


@router.get("/health/all", response_model=List[ServerResponse])
async def get_all_servers_health(
    current_user: Annotated[DBUser, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    servers = db.query(DBServer).filter(DBServer.owner_id == current_user.id).all()
    
    # Server is considered offline if no data for 10 seconds
    time_threshold = datetime.now() - timedelta(seconds=10)
    
    result = []
    for server in servers:
        status = "online" if server.last_seen and server.last_seen >= time_threshold else "offline"
        result.append(
            ServerResponse(
                server_ulid=server.server_ulid,
                server_name=server.server_name,
                status=status
            )
        )
    
    return result



@router.get("/health/{server_ulid}", response_model=ServerResponse)
async def get_server_health(
    server_ulid: str,
    current_user: Annotated[DBUser, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    server = db.query(DBServer).filter(
        DBServer.server_ulid == server_ulid,
        DBServer.owner_id == current_user.id
    ).first()
    
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    # Server is considered offline if no data for 10 seconds
    status = "online"
    time_threshold = datetime.now() - timedelta(seconds=10)
    
    if server.last_seen is None or server.last_seen < time_threshold:
        status = "offline"
    
    return ServerResponse(
        server_ulid=server.server_ulid,
        server_name=server.server_name,
        status=status
    )

