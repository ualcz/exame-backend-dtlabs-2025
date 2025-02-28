from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, field_validator, Field, ValidationInfo

# Pydantic models
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str


class User(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None
    disabled: Optional[bool] = None
    
    class ConfigDict:
        from_attributes = True



class UserInDB(User):
    hashed_password: str


class UserCreate(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None
    password: str


class ServerCreate(BaseModel):
    server_name: str


class ServerResponse(BaseModel):
    server_ulid: str
    server_name: str
    status: str
    
    class ConfigDict:
        from_attributes = True


class SensorDataPost(BaseModel):
    server_ulid: str
    timestamp: datetime
    temperature: Optional[float] =  Field(default = None, validate_default=True)
    humidity: Optional[float] =  Field(default = None, validate_default=True)
    voltage: Optional[float] =  Field(default = None, validate_default=True)
    current: Optional[float] =  Field(default = None, validate_default=True)
    
    @field_validator('timestamp')
    def check_timestamp_format(cls, v):
        # Ensure timestamp is in ISO 8601 format
        if not isinstance(v, datetime):
            try:
                return datetime.fromisoformat(v.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                raise ValueError('Timestamp must be in ISO 8601 format')
        return v
    
    @field_validator('humidity')
    def check_humidity_range(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError('Humidity must be between 0 and 100')
        return v
    
    @field_validator('server_ulid', 'timestamp')
    def check_required_fields(cls, v):
        if v is None:
            raise ValueError('This field is required')
        return v
    
    @field_validator('temperature', 'humidity', 'voltage', 'current')
    def check_at_least_one_sensor(cls, v, info: ValidationInfo) -> str:
        if v is None and all(info.data.get(field) is None for field in ['temperature', 'humidity', 'voltage', 'current']):
            raise ValueError('At least one sensor value must be provided')
        return v


class SensorDataResponse(BaseModel):
    timestamp: datetime
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    voltage: Optional[float] = None
    current: Optional[float] = None
    
    class ConfigDict:
        from_attributes = True
