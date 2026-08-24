from app.core.database import Base, engine
from app.core.models import User

Base.metadata.create_all(bind=engine)

print("Database berhasil dibuat.")
print("Table users berhasil dibuat.")
