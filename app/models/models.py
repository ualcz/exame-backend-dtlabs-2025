from sqlalchemy import Column, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base

# Database Models
class DBUser(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    hashed_password = Column(String)
    disabled = Column(Boolean, default=False)
    servers = relationship("DBServer", back_populates="owner")


class DBServer(Base):
    __tablename__ = "servers"
    
    server_ulid = Column(String, primary_key=True, index=True)
    server_name = Column(String)
    owner_id = Column(String, ForeignKey("users.id"))
    last_seen = Column(DateTime)
    
    owner = relationship("DBUser", back_populates="servers")
    sensor_data = relationship("DBSensorData", back_populates="server")


class DBSensorData(Base):
    __tablename__ = "sensor_data"
    
    id = Column(String, primary_key=True, index=True)
    server_ulid = Column(String, ForeignKey("servers.server_ulid"))
    timestamp = Column(DateTime, index=True)
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    voltage = Column(Float, nullable=True)
    current = Column(Float, nullable=True)
    
    server = relationship("DBServer", back_populates="sensor_data")
