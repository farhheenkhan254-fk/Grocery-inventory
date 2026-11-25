import logging
from pathlib import Path
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, scoped_session
from app.config import settings
from database.models import Base, Supplier, Product

logger = logging.getLogger("smart_grocery.database")

INITIAL_PRODUCTS = [
    {
        "name": "Basmati Rice",
        "category": "Grains",
        "current_stock": 20.0,
        "minimum_stock": 10.0,
        "reorder_quantity": 50.0,
        "unit": "kg",
        "supplier_id": 1,
    },
    {
        "name": "Wheat Flour",
        "category": "Grains",
        "current_stock": 40.0,
        "minimum_stock": 15.0,
        "reorder_quantity": 40.0,
        "unit": "kg",
        "supplier_id": 1,
    },
    {
        "name": "Sugar",
        "category": "Sweeteners",
        "current_stock": 25.0,
        "minimum_stock": 10.0,
        "reorder_quantity": 30.0,
        "unit": "kg",
        "supplier_id": 2,
    },
    {
        "name": "Cooking Oil",
        "category": "Oils",
        "current_stock": 15.0,
        "minimum_stock": 8.0,
        "reorder_quantity": 25.0,
        "unit": "litres",
        "supplier_id": 3,
    },
    {
        "name": "Tea Leaves",
        "category": "Beverages",
        "current_stock": 18.0,
        "minimum_stock": 6.0,
        "reorder_quantity": 20.0,
        "unit": "kg",
        "supplier_id": 2,
    },
    {
        "name": "Red Lentils",
        "category": "Pulses",
        "current_stock": 32.0,
        "minimum_stock": 10.0,
        "reorder_quantity": 25.0,
        "unit": "kg",
        "supplier_id": 1,
    },
    {
        "name": "Chickpeas",
        "category": "Pulses",
        "current_stock": 28.0,
        "minimum_stock": 10.0,
        "reorder_quantity": 25.0,
        "unit": "kg",
        "supplier_id": 1,
    },
    {
        "name": "Kidney Beans",
        "category": "Pulses",
        "current_stock": 24.0,
        "minimum_stock": 8.0,
        "reorder_quantity": 20.0,
        "unit": "kg",
        "supplier_id": 1,
    },
    {
        "name": "Moong Dal",
        "category": "Pulses",
        "current_stock": 22.0,
        "minimum_stock": 8.0,
        "reorder_quantity": 20.0,
        "unit": "kg",
        "supplier_id": 1,
    },
    {
        "name": "Chana Dal",
        "category": "Pulses",
        "current_stock": 26.0,
        "minimum_stock": 8.0,
        "reorder_quantity": 20.0,
        "unit": "kg",
        "supplier_id": 1,
    },
    {
        "name": "Toor Dal",
        "category": "Pulses",
        "current_stock": 20.0,
        "minimum_stock": 8.0,
        "reorder_quantity": 20.0,
        "unit": "kg",
        "supplier_id": 1,
    },
    {
        "name": "Maize Flour",
        "category": "Grains",
        "current_stock": 25.0,
        "minimum_stock": 8.0,
        "reorder_quantity": 20.0,
        "unit": "kg",
        "supplier_id": 1,
    },
    {
        "name": "Oats",
        "category": "Breakfast",
        "current_stock": 18.0,
        "minimum_stock": 6.0,
        "reorder_quantity": 15.0,
        "unit": "kg",
        "supplier_id": 1,
    },
    {
        "name": "Pasta",
        "category": "Packaged Foods",
        "current_stock": 30.0,
        "minimum_stock": 10.0,
        "reorder_quantity": 25.0,
        "unit": "kg",
        "supplier_id": 2,
    },
    {
        "name": "Salt",
        "category": "Seasonings",
        "current_stock": 35.0,
        "minimum_stock": 12.0,
        "reorder_quantity": 30.0,
        "unit": "kg",
        "supplier_id": 2,
    },
    {
        "name": "Turmeric Powder",
        "category": "Spices",
        "current_stock": 12.0,
        "minimum_stock": 4.0,
        "reorder_quantity": 10.0,
        "unit": "kg",
        "supplier_id": 2,
    },
    {
        "name": "Red Chili Powder",
        "category": "Spices",
        "current_stock": 10.0,
        "minimum_stock": 4.0,
        "reorder_quantity": 10.0,
        "unit": "kg",
        "supplier_id": 2,
    },
    {
        "name": "Cumin Seeds",
        "category": "Spices",
        "current_stock": 9.0,
        "minimum_stock": 3.0,
        "reorder_quantity": 8.0,
        "unit": "kg",
        "supplier_id": 2,
    },
    {
        "name": "Coffee",
        "category": "Beverages",
        "current_stock": 16.0,
        "minimum_stock": 5.0,
        "reorder_quantity": 12.0,
        "unit": "kg",
        "supplier_id": 2,
    },
    {
        "name": "Ghee",
        "category": "Dairy",
        "current_stock": 20.0,
        "minimum_stock": 6.0,
        "reorder_quantity": 15.0,
        "unit": "litres",
        "supplier_id": 3,
    },
]

def get_engine(db_url: str = None):
    url = db_url or settings.DATABASE_URL
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        engine = create_engine(url, connect_args=connect_args, echo=False)
    else:
        try:
            engine = create_engine(url, pool_pre_ping=True, echo=False)
            # Test connection
            with engine.connect() as conn:
                pass
            logger.info(f"Connected to database: {url.split('@')[-1] if '@' in url else url}")
        except Exception as e:
            logger.warning(f"Could not connect to configured DB ({e}). Falling back to local SQLite database.")
            sqlite_path = Path(__file__).resolve().parent.parent / "smart_grocery.db"
            engine = create_engine(f"sqlite:///{sqlite_path}", connect_args={"check_same_thread": False}, echo=False)
    return engine

engine = get_engine()
SessionFactory = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)
SessionLocal = scoped_session(SessionFactory)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db(target_engine=None):
    eng = target_engine or engine
    Base.metadata.create_all(bind=eng)
    session = SessionFactory(bind=eng)
    try:
        seed_data(session)
    finally:
        session.close()

def seed_data(session):
    # Check if suppliers exist
    if session.query(Supplier).count() == 0:
        s1 = Supplier(
            id=1,
            name="Apex Agro Wholesalers",
            slack_user_id="U0CL94EJPU4",
            slack_channel_id="C_SUPPLIER_APEX",
            contact_email="orders@apexagro.com"
        )
        s2 = Supplier(
            id=2,
            name="Golden Harvest Foods",
            slack_user_id="U_SUPPLIER_GOLDEN",
            slack_channel_id="C_SUPPLIER_GOLDEN",
            contact_email="sales@goldenharvest.com"
        )
        s3 = Supplier(
            id=3,
            name="PureOil Refineries Ltd",
            slack_user_id="U_SUPPLIER_PUREOIL",
            slack_channel_id="C_SUPPLIER_PUREOIL",
            contact_email="orders@pureoil.com"
        )
        session.add_all([s1, s2, s3])
        session.commit()

    existing_names = {
        name.casefold() for (name,) in session.query(Product.name).all()
    }
    new_products = [
        Product(**product)
        for product in INITIAL_PRODUCTS
        if product["name"].casefold() not in existing_names
    ]
    if new_products:
        session.add_all(new_products)
        session.commit()
