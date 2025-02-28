from datetime import datetime, timedelta
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ulid import ulid

from app.database import get_db
from app.models.models import DBSensorData, DBServer, DBUser
from app.schemas.schemas import SensorDataPost, SensorDataResponse
from app.security.auth import get_current_active_user

router = APIRouter(tags=["sensor_data"])


@router.post("/data", status_code=status.HTTP_201_CREATED)
async def post_sensor_data(data: SensorDataPost, db: Session = Depends(get_db)):
    # Check if server exists
    server = db.query(DBServer).filter(DBServer.server_ulid == data.server_ulid).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    # Update last seen timestamp
    server.last_seen = datetime.now()
    
    # Create sensor data entry
    db_sensor_data = DBSensorData(
        id=str(ulid),
        server_ulid=data.server_ulid,
        timestamp=data.timestamp,
        temperature=data.temperature,
        humidity=data.humidity,
        voltage=data.voltage,
        current=data.current
    )
    
    db.add(db_sensor_data)
    db.commit()
    
    return {"message": "Data recorded successfully"}


@router.get("/data", response_model=List[SensorDataResponse])
async def get_sensor_data(
    current_user: Annotated[DBUser, Depends(get_current_active_user)],
    server_ulid: Optional[str] = Query(None, description="Filter by server ULID"),
    start_time: Optional[datetime] = Query(None, description="Start time for data filter"),
    end_time: Optional[datetime] = Query(None, description="End time for data filter"),
    sensor_type: Optional[str] = Query(None, description="Type of sensor (temperature, humidity, voltage, current)"),
    aggregation: Optional[str] = Query(None, description="Aggregation level (minute, hour, day)"),
    db: Session = Depends(get_db)
):
    # Validate sensor_type
    valid_sensor_types = ["temperature", "humidity", "voltage", "current"]
    if sensor_type and sensor_type not in valid_sensor_types:
        raise HTTPException(status_code=400, detail=f"Invalid sensor type. Must be one of {valid_sensor_types}")
    
    # Validate aggregation
    valid_aggregations = ["minute", "hour", "day"]
    if aggregation and aggregation not in valid_aggregations:
        raise HTTPException(status_code=400, detail=f"Invalid aggregation. Must be one of {valid_aggregations}")
    
    # Build query based on user's servers
    query = db.query(DBSensorData)
    query = query.join(DBServer)
    query = query.filter(DBServer.owner_id == current_user.id)
    
    # Apply filters
    if server_ulid:
        query = query.filter(DBSensorData.server_ulid == server_ulid)
    
    if start_time:
        query = query.filter(DBSensorData.timestamp >= start_time)
    
    if end_time:
        query = query.filter(DBSensorData.timestamp <= end_time)
    
    # If sensor_type is specified, ensure it's not null in the database
    if sensor_type:
        if sensor_type == "temperature":
            query = query.filter(DBSensorData.temperature != None)
        elif sensor_type == "humidity":
            query = query.filter(DBSensorData.humidity != None)
        elif sensor_type == "voltage":
            query = query.filter(DBSensorData.voltage != None)
        elif sensor_type == "current":
            query = query.filter(DBSensorData.current != None)
    
    # Apply aggregation if needed
    if aggregation:
        if aggregation == "minute":
            time_trunc = func.date_trunc('minute', DBSensorData.timestamp)
        elif aggregation == "hour":
            time_trunc = func.date_trunc('hour', DBSensorData.timestamp)
        elif aggregation == "day":
            time_trunc = func.date_trunc('day', DBSensorData.timestamp)
        
        # Build aggregation query with proper grouping
        stmt = (
            select([
                time_trunc.label('timestamp'),
                func.avg(DBSensorData.temperature).label('temperature') if not sensor_type or sensor_type == "temperature" else None,
                func.avg(DBSensorData.humidity).label('humidity') if not sensor_type or sensor_type == "humidity" else None,
                func.avg(DBSensorData.voltage).label('voltage') if not sensor_type or sensor_type == "voltage" else None,
                func.avg(DBSensorData.current).label('current') if not sensor_type or sensor_type == "current" else None
            ])
            .select_from(DBSensorData)
            .join(DBServer)
            .where(DBServer.owner_id == current_user.id)
        )
        
        # Apply the same filters from above
        if server_ulid:
            stmt = stmt.where(DBSensorData.server_ulid == server_ulid)
        if start_time:
            stmt = stmt.where(DBSensorData.timestamp >= start_time)
        if end_time:
            stmt = stmt.where(DBSensorData.timestamp <= end_time)
        if sensor_type:
            if sensor_type == "temperature":
                stmt = stmt.where(DBSensorData.temperature != None)
            elif sensor_type == "humidity":
                stmt = stmt.where(DBSensorData.humidity != None)
            elif sensor_type == "voltage":
                stmt = stmt.where(DBSensorData.voltage != None)
            elif sensor_type == "current":
                stmt = stmt.where(DBSensorData.current != None)
        
        # Group by the truncated time
        stmt = stmt.group_by(time_trunc).order_by(time_trunc)
        
        # Execute the aggregation query
        result = db.execute(stmt).all()
        
        # Convert result to Pydantic models
        response_data = []
        for row in result:
            data_dict = {
                "timestamp": row.timestamp,
            }
            
            if not sensor_type or sensor_type == "temperature":
                data_dict["temperature"] = row.temperature
            if not sensor_type or sensor_type == "humidity":
                data_dict["humidity"] = row.humidity
            if not sensor_type or sensor_type == "voltage":
                data_dict["voltage"] = row.voltage
            if not sensor_type or sensor_type == "current":
                data_dict["current"] = row.current
                
            response_data.append(SensorDataResponse(**data_dict))
        
        return response_data
    
    # If no aggregation, just return the filtered data
    result = query.order_by(DBSensorData.timestamp).all()
    
    # If a specific sensor was requested, only include that field in the response
    if sensor_type:
        response_data = []
        for item in result:
            data_dict = {"timestamp": item.timestamp}
            data_dict[sensor_type] = getattr(item, sensor_type)
            response_data.append(SensorDataResponse(**data_dict))
        return response_data
    
    return result
