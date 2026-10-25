from enum import Enum
from typing import Optional
from sqlalchemy import String,ForeignKey
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class UserRole(str,Enum):
    STUDENT = 'Student'
    STAFF = 'Staff'
    ADMIN = 'Admin'

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(unique=True)
    role: Mapped[UserRole]

class Greivances(Base):
    __tablename__ = 'greivance'
    id: Mapped[int] = mapped_column(primary_key=True)
    description: Mapped[str]
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))

# To verify my models
if __name__ == "__main__":
    from sqlalchemy import create_engine,inspect
    from sqlalchemy.orm import Session
    engine = create_engine("sqlite:///:memory:", echo=True)
    
    check = inspect(engine)
    # inspecting this is kinda new for me,instead of creating tests
    for table_name in check.get_table_names():
        print(f"\nTable: {table_name}")
        for column in check.get_columns(table_name):
            print(f" - {column['name']}: {column['type']} (nullable="
        f"{column['nullable']})")
    try:
        Base.metadata.create_all(engine)
        print("Schema done <3")
        with Session(engine) as session:
            test_sub = User(
                name = "ABC",
                email = "ABC@clg.edu",
                role = UserRole.STUDENT
            )
            session.add(test_sub)
            session.commit()
            test_query = Greivances(
                description= "Wifi LAN disturbance",
                user_id = test_sub.id
            )
            session.add(test_query)
            session.commit()
            print("Checked the relationships")
    except Exception as e:
        print(f"\nError to correct: {e}")


