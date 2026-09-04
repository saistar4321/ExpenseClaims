from app.database import Base, SessionLocal, engine
from app.models import User, UserRole


Base.metadata.create_all(bind=engine)


def seed():
    db = SessionLocal()

    if db.query(User).count() > 0:
        print("Users already exist.")
        db.close()
        return

    # Create manager first so the employee can reference the manager.
    manager = User(
        name="Bob Manager",
        email="bob@example.com",
        role=UserRole.MANAGER,
        monthly_limit=50000,
    )

    finance = User(
        name="Carol Finance",
        email="carol@example.com",
        role=UserRole.FINANCE,
        monthly_limit=100000,
    )

    db.add(manager)
    db.add(finance)
    db.commit()

    # Employee is assigned to Bob Manager.
    employee = User(
        name="Alice Employee",
        email="alice@example.com",
        role=UserRole.STAFF,
        manager_id=manager.id,
        monthly_limit=30000,
    )

    db.add(employee)
    db.commit()

    print("Seeded demo users:")
    print("Employee ID:", employee.id)
    print("Manager ID:", manager.id)
    print("Finance ID:", finance.id)

    db.close()


if __name__ == "__main__":
    seed()