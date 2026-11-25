import pytest
import smtplib
from importlib import import_module
from database.connection import INITIAL_PRODUCTS, init_db
from database.repository import repo
from app.config import settings
from tools.inventory_tools import check_stock_status, scan_all_inventory
from tools.purchase_tools import calculate_reorder_plan
from agents.alert_agent import alert_agent
from services.email_service import email_service
from slack.slack_app import slack_service

email_service_module = import_module("services.email_service")

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_sufficient_stock_detection():
    # Basmati Rice min is 10.0; set to 20.0
    repo.set_stock("Basmati Rice", 20.0)
    status = check_stock_status("Basmati Rice")
    assert status["status"] == "SUFFICIENT"
    assert status["needs_reorder"] is False
    assert status["current_stock"] == 20.0

def test_low_stock_detection():
    # Set to 5.0 kg (below min of 10.0 kg)
    repo.set_stock("Basmati Rice", 5.0)
    status = check_stock_status("Basmati Rice")
    assert status["status"] == "LOW_STOCK"
    assert status["needs_reorder"] is True
    assert status["current_stock"] == 5.0
    assert status["minimum_stock"] == 10.0

def test_out_of_stock_detection():
    # Set to 0.0 kg
    repo.set_stock("Basmati Rice", 0.0)
    status = check_stock_status("Basmati Rice")
    assert status["status"] == "OUT_OF_STOCK"
    assert status["needs_reorder"] is True

def test_reorder_plan_calculation():
    # Product with 5kg current, 10kg min, 50kg base reorder
    plan = calculate_reorder_plan(current_stock=5.0, minimum_stock=10.0, base_reorder=50.0)
    assert plan["suggested_quantity"] == 50.0
    assert plan["deficit"] == 5.0
    assert plan["urgency"] in ["HIGH", "CRITICAL", "MEDIUM"]

def test_scan_all_inventory_finds_low_items():
    repo.set_stock("Basmati Rice", 5.0)
    low_items = scan_all_inventory()
    names = [item["product_name"] for item in low_items]
    assert "Basmati Rice" in names

def test_catalog_seeds_fifteen_additional_products_idempotently():
    assert len(INITIAL_PRODUCTS) == 20
    assert len(repo.get_all_products()) == 20

    repo.set_stock("Red Lentils", 7.0)
    init_db()

    assert len(repo.get_all_products()) == 20
    assert repo.get_product_by_name("Red Lentils")["current_stock"] == 7.0

def test_low_stock_alert_emails_admin(monkeypatch):
    sent_emails = []
    monkeypatch.setattr(slack_service, "post_message", lambda **kwargs: {"ok": True})
    monkeypatch.setattr(
        email_service,
        "send_email",
        lambda to_email, subject, body_text, body_html=None: (
            sent_emails.append((to_email, subject, body_text)) or True
        ),
    )

    result = alert_agent.send_low_stock_alert(
        {
            "name": "Basmati Rice",
            "current_stock": 5.0,
            "minimum_stock": 10.0,
            "unit": "kg",
        },
        {"suggested_quantity": 50.0},
    )

    assert len(sent_emails) == 1
    recipient, subject, body = sent_emails[0]
    assert recipient
    assert "Low Stock Alert: Basmati Rice" in subject
    assert "Current Stock: 5.0 kg" in body
    assert "Minimum Stock: 10.0 kg" in body
    assert "Suggested Reorder: 50.0 kg" in body
    assert result["email_sent"] is True

def test_low_stock_alert_reports_email_failure(monkeypatch):
    monkeypatch.setattr(slack_service, "post_message", lambda **kwargs: {"ok": True})
    monkeypatch.setattr(email_service, "send_email", lambda *args, **kwargs: False)

    result = alert_agent.send_low_stock_alert(
        {
            "name": "Ghee",
            "current_stock": 2.0,
            "minimum_stock": 6.0,
            "unit": "litres",
        },
        {"suggested_quantity": 50.0},
    )

    assert result["email_sent"] is False

def test_smtp_failure_is_reported_as_not_sent(monkeypatch):
    monkeypatch.setattr(settings, "SMTP_USER", "test@example.com")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "test-password")
    monkeypatch.setattr(settings, "EMAIL_NOTIFICATIONS_ENABLED", True)

    def fail_smtp(*args, **kwargs):
        raise smtplib.SMTPConnectError(421, b"Connection unavailable")

    monkeypatch.setattr(email_service_module.smtplib, "SMTP", fail_smtp)

    assert email_service.send_email(
        "admin@example.com",
        "Test low-stock alert",
        "This test must not reach an SMTP server.",
    ) is False
