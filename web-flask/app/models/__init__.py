# 将 devices.py 中的 Devices 类暴露给 app.models 包
from .db_config import Base, engine, get_db
from .devices import Devices
# 如果以后有 from .alarms import Alarms 也可以加在这里