# 🛒 Smart Grocery Inventory & Procurement Management System

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![Slack Bolt](https://img.shields.io/badge/Integration-Slack%20Bolt-4A154B.svg)](https://slack.dev/bolt-python/)
[![SQLAlchemy](https://img.shields.io/badge/ORM-SQLAlchemy%202.0-red.svg)](https://www.sqlalchemy.org/)
[![Streamlit](https://img.shields.io/badge/Frontend-Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![Pytest](https://img.shields.io/badge/Tests-17%20Passed-brightgreen.svg)](https://pytest.org/)

> A demo-ready grocery inventory and procurement app built with Python, Streamlit, and LangGraph.
> Track stock, plan replenishment, and manage supplier orders with human approval before purchasing.

The dashboard runs locally with SQLite. Groq, Slack, and email integrations are optional.

## Quick Start for Windows

**Fastest option:** run the included launcher from the project folder:

```powershell
.\run.bat
```

It creates a virtual environment if needed, installs dependencies, and starts the dashboard. To run it manually instead:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app/main.py
```

Then open [http://localhost:8501](http://localhost:8501). No API keys are needed for the demo dashboard.

---

## 📋 Table of Contents

1. [Quick Start](#quick-start-for-windows)
2. [System Architecture](#1-system-architecture)
3. [AI Agents Roster](#2-ai-agents-roster)
4. [LangGraph StateGraph Workflow](#3-langgraph-stategraph-workflow)
5. [Key Business Rules](#4-key-business-rules)
6. [Slack Integration & Channels](#5-slack-integration--channels)
7. [Database Design](#6-database-design)
8. [Run Commands](#7-run-commands)
9. [Live Presentation Demo Scenarios](#8-live-presentation-demo-scenarios)
10. [Slack App Setup (Live Mode)](#9-slack-app-setup-live-mode)
11. [Test Suite](#10-test-suite)
12. [Project Structure](#11-project-structure)

---

## 1. System Architecture

The system orchestrates 8 specialized AI agents governed by a **LangGraph StateGraph** to monitor stock levels, compute reorder requirements, request human Admin sign-off, negotiate with wholesalers via Slack, track in-transit consignments, and update inventory only upon physical verification.

```
                          +------------------------------------+
                          |       Scheduled Stock Monitor      |
                          |            (APScheduler)           |
                          +-----------------+------------------+
                                            |
                                            v
                                 +---------------------+
                                 |   Inventory Agent   |
                                 +----------+----------+
                                            | (Stock <= Minimum)
                                            v
+------------------+             +---------------------+             +--------------------+
|  Supervisor Agent| <=========> |    Planner Agent    | <=========> |    Alert Agent     |
+------------------+             +----------+----------+             +---------+----------+
                                            |                                  |
                                            +-----------------+----------------+
                                                              |
                                                              v
                                              +-------------------------------+
                                              |      Admin Approval Agent     |
                                              |     (Slack #admin-approvals)  |
                                              +---------------+---------------+
                                                              |
                                             +----------------+----------------+
                                             |                                 |
                                      [❌ Rejected]                     [✅ Approved]
                                             |                                 |
                                             v                                 v
                                          [ END ]                  +-----------------------+
                                                                   |   Procurement Agent   |
                                                                   | (Slack #purchase-order)
                                                                   +-----------+-----------+
                                                                               |
                                                                               v
                                                                   +-----------------------+
                                                                   |     Supplier Agent    |
                                                                   +-----------+-----------+
                                                                               |
                                                  +----------------------------+----------------------------+
                                                  |                                                         |
                                            [📦 Available]                                         [🚫 Out of Stock]
                                                  |                                                         |
                                                  v                                                         v
                                      +-----------------------+                                 +-----------------------+
                                      |   Supplier Dispatch   |                                 |  Notify Admin of OOS  |
                                      | (Stock UNCHANGED!)    |                                 |  Recommend Alt Vendors|
                                      +-----------+-----------+                                 +-----------+-----------+
                                                  |                                                         |
                                                  v                                                         v
                                      +-----------------------+                                          [ END ]
                                      | Goods Received Signoff|
                                      |   (Admin Dock Verification)
                                      +-----------+-----------+
                                                  |
                                                  v
                                      +-----------------------+
                                      | Inventory Update Agent|
                                      | (Stock increases +50kg)|
                                      +-----------+-----------+
                                                  |
                                                  v
                                               [ END ]
```

---

## 2. AI Agents Roster

| Agent | Responsibility | Primary Interface / Channel |
|---|---|---|
| **Supervisor Agent** | Coordinates multi-agent lifecycle, resolves state transitions, routes execution branches. | LangGraph Coordinator |
| **Inventory Monitoring Agent** | Scans product catalog, evaluates threshold conditions, detects low-stock and stockouts. | Database / Inventory Scanner |
| **Planner Agent** | Calculates suggested reorder quantities using safety stock formulas; prepares purchase plan. *Never auto-approves.* | Procurement Engine / Groq LLM |
| **Alert Agent** | Dispatches immediate Slack alerts with product name, current stock, threshold, and suggested order. | `#inventory-alerts` |
| **Admin Approval Agent** | Dispatches interactive Approve/Reject Block Kit cards; validates role permissions. | `#admin-approvals` |
| **Procurement Agent** | Creates formal Purchase Orders in DB, validates against duplicate active orders, and sends POs to Wholesalers. | `#purchase-orders` |
| **Supplier Agent** | Allows Wholesalers to confirm availability or Out of Stock; prompts dispatch; suggests alternative vendors on stockout. | `#purchase-orders` & `#supplier-updates` |
| **Notification Agent** | Broadcasts dispatch advisories, delivery arrivals, executive summaries, and restocking confirmations. | `#supplier-updates` & `#inventory-reports` |

---

## 3. LangGraph StateGraph Workflow

The system is built on **LangGraph StateGraph** utilizing a `TypedDict` workflow state and checkpointing:

```mermaid
graph TD
    START([START]) --> IV[Input Validation]
    IV --> SA[Supervisor Agent]
    SA --> PA[Planner Agent]
    PA --> IMA[Inventory Monitoring Agent]
    IMA --> CR1{Stock <= Minimum?}
    CR1 -- Low Stock --> AA[Alert Agent]
    CR1 -- Sufficient --> END1([END])
    AA --> ADM[Admin Approval Agent<br/>Human-in-the-Loop]
    ADM --> CR2{Admin Decision?}
    CR2 -- Rejected --> END2([END])
    CR2 -- Approved --> PROC[Procurement Agent]
    PROC --> SUP[Supplier Agent]
    SUP --> CR3{Supplier Status?}
    CR3 -- Out of Stock --> OOS[Notify Admin & Recommend Alternatives]
    OOS --> END3([END])
    CR3 -- Available --> DISP[Supplier Dispatch<br/>Stock Unchanged!]
    DISP --> GRC[Goods Received Confirmation<br/>Admin In-Dock Signoff]
    GRC --> IUA[Inventory Update Agent<br/>Database Stock Restocked]
    IUA --> END4([END])
```

---

## 4. Key Business Rules

1. **Low Stock Condition:** Triggered strictly when `current_stock <= minimum_stock`.
2. **No Automatic Purchases:** AI agents **never** approve financial expenditures independently. Admin human authorization is mandatory.
3. **Duplicate Order Prevention:** The system blocks duplicate active POs (`PENDING_APPROVAL`, `APPROVED`, `SENT_TO_SUPPLIER`, `DISPATCHED`) for the same SKU.
4. **Unapproved Dispatch Prevention:** Wholesalers cannot dispatch orders that have not been approved by the Store Admin.
5. **No Stock Inflation at Dispatch:** Dispatched consignments do **not** increment inventory; stock is incremented only after physical dock verification.
6. **Out-of-Stock Alternative Sourcing:** If the primary wholesaler indicates `OUT_OF_STOCK`, the system alerts the Admin and suggests registered alternative suppliers.
7. **Complete Audit Trail:** Every state change, button click, actor ID, and quantity transition is recorded in the `audit_logs` table.

---

## 5. Slack Integration & Channels

The system integrates with Slack Bolt and SDK with interactive Block Kit buttons, real-time Socket Mode listener, role-based authorization, and automated multi-party email alerts.

### Roles Clarification: Do You Need 3 Accounts?
**NO.** In this supply chain architecture, **Wholesaler and Supplier are the exact same entity**:
- **Role 1: Store Admin (`U0CL03S65SR`)** — Monitors inventory, reviews low stock alerts, approves purchase orders, and confirms physical receipt of goods at the dock.
- **Role 2: Wholesaler / Supplier (`U0CL94EJPU4`)** — Receives approved purchase orders, confirms stock availability (`In Stock` / `Out of Stock`), and confirms consignment dispatch.

> **💡 Solo Presentation Mode:** If you are presenting alone from a single Slack account, the system automatically permits your account to test both Admin and Wholesaler buttons seamlessly without permission blocks!

### Channel Visibility: How to Show Only Relevant Channels to Wholesaler
To make Admin channels hidden from the Wholesaler:
1. **Admin-Only Channels (Make Private 🔒):**
   - `#admin-approvals` — Click channel name -> **Settings** -> Change to **Private Channel**. Invite only Admin (`@Admin`) and `@GroceryAgent`.
   - `#inventory-alerts` — Private channel (Admin + bot).
   - `#inventory-reports` — Private channel (Admin + bot).
2. **Wholesaler & Vendor Channels (Public or Shared):**
   - `#purchase-orders` — Add Wholesaler (`@Wholesaler`), Admin, and `@GroceryAgent`.
   - `#supplier-updates` — Add Wholesaler (`@Wholesaler`), Admin, and `@GroceryAgent`.

*Result:* When the Wholesaler logs in, they only see `#purchase-orders` and `#supplier-updates`!

### Automated Multi-Party Email Alerts
In addition to Slack, the system sends automated email notifications via `services/email_service.py`:
- **When stock reaches or falls below its minimum:** Low-stock alert sent to the Admin.
- **When Admin Approves PO:** Purchase Order email sent to Wholesaler's email (`orders@apexagro.com`).
- **When Wholesaler Confirms Stock:** Availability update email sent to Admin (`admin@groceryinventory.com`).
- **When Wholesaler Dispatches:** Consignment in-transit tracking email sent to Admin.
- **When Goods are Received:** Restocking confirmation email sent to both Admin and Wholesaler.
*(For live delivery, set `SMTP_USER`, `SMTP_PASSWORD`, `ADMIN_EMAIL`, and `SUPPLIER_EMAIL` in `.env` to the real sender and recipient accounts. Without SMTP credentials, no email is sent; the dashboard reports the failed low-stock notification and logs an SMTP warning. The Wholesaler email is sent after Admin approval, not at the initial low-stock alert.)*

---

## 6. Database Design

Implemented with **SQLAlchemy 2.0 ORM**, supporting both **MySQL** (production) and **SQLite** (out-of-the-box demo):

- **Product:** `id`, `name`, `category`, `current_stock`, `minimum_stock`, `reorder_quantity`, `unit`, `supplier_id`.
- **Supplier:** `id`, `name`, `slack_user_id`, `slack_channel_id`, `contact_email`.
- **PurchaseOrder:** `id`, `product_id`, `supplier_id`, `quantity`, `status`, `created_at`.
- **Approval:** `id`, `purchase_order_id`, `admin_id`, `approval_status`, `approved_at`.
- **SupplierResponse:** `id`, `purchase_order_id`, `availability_status`, `dispatch_status`, `response_at`.
- **GoodsReceipt:** `id`, `purchase_order_id`, `received_quantity`, `received_by`, `received_at`.
- **AuditLog:** `id`, `event_type`, `entity_type`, `entity_id`, `actor`, `details`, `created_at`.

The demo seeds 20 grocery products (including grains, pulses, spices, beverages, and oils) when the app starts. Seeding is additive and idempotent: existing products and their stock levels are preserved. **Reset Sample Database** restores all 20 products to their sample stock levels.

---

## 7. Run Commands

Run these commands from the project root in **PowerShell**. If you used `run.bat`, it already installed the dependencies.

### Start the dashboard

```powershell
.\.venv\Scripts\python.exe -m streamlit run app/main.py
```

Open [http://localhost:8501](http://localhost:8501). Press **Ctrl+C** in the terminal to stop it.

### Run a demo scenario without the dashboard

```powershell
.\.venv\Scripts\python.exe app/main.py --scenario 1
.\.venv\Scripts\python.exe app/main.py --scenario 2
```

### Start the Slack bot (optional)

First configure `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN` in `.env` as described in [Slack App Setup](#9-slack-app-setup-live-mode). Then, in a **second PowerShell window**:

```powershell
.\.venv\Scripts\python.exe run_slack.py
```

Keep the Slack bot and dashboard running in separate terminals when using the live Slack integration.

---

## 8. 🎬 Live Presentation & Demo Playbook (Step-by-Step)

Follow this guide for a seamless **5 to 10 minute live presentation**.

### 🖥️ Recommended Screen Setup (Split Screen)
Arrange your display side-by-side:
- **Left 50% of Screen:** Web Browser opened to **Streamlit Dashboard** (`http://localhost:8501`).
- **Right 50% of Screen:** **Slack App / Browser** showing the `Grocery Inventory` workspace.

```
+------------------------------------+------------------------------------+
|        LEFT SCREEN (50%)           |        RIGHT SCREEN (50%)          |
|    Streamlit Dashboard (UI)        |        Slack Workspace App         |
|                                    |                                    |
|  - Inventory Table                 |  Channels to switch between:       |
|  - Stock Adjustment Simulator      |   #inventory-alerts                |
|  - LangGraph State Inspector       |   #admin-approvals                 |
|                                    |   #purchase-orders                 |
|                                    |   #supplier-updates                |
|                                    |   #inventory-reports               |
+------------------------------------+------------------------------------+
```

---

### 🎭 Step-by-Step Presentation Script

#### 🟢 Part 1: System Intro (1 Minute)
1. **Show Left Screen (Streamlit):**
   - Point out the product catalog. Highlight **Basmati Rice**:
     - Current Stock: `20.0 kg`
     - Minimum Threshold: `10.0 kg`
     - Reorder Quantity: `50.0 kg`
2. **Explain the Architecture:**
   - Explain that 8 AI agents coordinated by **LangGraph** automate procurement while strictly enforcing human-in-the-loop authorization via **Slack**.

---

#### 🟢 Part 2: Scenario 1 — Full Procurement Lifecycle (5 Minutes)

1. **Trigger Stock Drop (Left Screen - Streamlit):**
   - In Tab 1 (*Inventory & Simulator*), scroll down to **Stock Adjustment Simulator**.
   - Select **Basmati Rice**.
   - Set stock level to **`5.0`** kg (below the `10.0 kg` threshold).
   - Click **"Update Stock & Run Agent Workflow"**.
   - *Tell Audience: "Customer purchases have drawn stock down to 5 kg. The Inventory Monitoring Agent immediately flags this below minimum safety levels."*

2. **Check Low Stock Alert (Right Screen - Slack):**
   - Click channel **`#inventory-alerts`**.
   - Show the **Alert Agent** message:
     - Product: *Basmati Rice*
     - Current Stock: *5.0 kg* | Minimum: *10.0 kg* | Suggested Reorder: *50.0 kg*.

3. **Admin Authorizes Procurement (Right Screen - Slack):**
   - Switch to channel **`#admin-approvals`**.
   - Show the interactive card sent by the **Admin Approval Agent** with `PO Number`.
   - As Admin (`U0CL03S65SR`), click the green button: **`[✅ Approve Purchase]`**.
   - *Tell Audience: "Safety Rule: The AI cannot spend money on its own. It requires authenticated Admin approval."*

4. **Wholesaler Receives PO (Right Screen - Slack):**
   - Switch to channel **`#purchase-orders`**.
   - Show the message sent by the **Procurement Agent** addressed to *Apex Agro Wholesalers*.
   - As Wholesaler (`U0CL94EJPU4`), click: **`[📦 In Stock - Confirm Availability]`**.

5. **Wholesaler Dispatches Goods (Right Screen - Slack):**
   - Switch to channel **`#supplier-updates`**.
   - Show the consignment prompt. As Wholesaler, click: **`[🚚 Confirm Consignment Dispatch]`**.
   - **Crucial Rule to highlight to audience:**
     *Look at the Streamlit screen on the left — stock is STILL 5.0 kg! Dispatched goods are in transit and must NOT be added to store inventory yet.*

6. **Store Confirms Goods Arrival (Right Screen - Slack):**
   - Switch back to channel **`#admin-approvals`**.
   - The consignment arrives physically at the loading dock.
   - Admin clicks: **`[📥 Confirm Physical Goods Received]`**.

7. **Verify Inventory Restocked (Both Screens):**
   - In Slack, open **`#inventory-reports`**: See the Restocking Confirmation: `+50.0 kg received. Updated Stock: 55.0 kg`.
   - Look at the **Left Screen (Streamlit)**: Click *Refresh* or view Tab 1 — Basmati Rice stock has automatically updated from **5.0 kg to 55.0 kg**!

---

#### 🟢 Part 3: Scenario 2 — Out of Stock & Alternative Sourcing (2 Minutes)

1. **Trigger Stockout:**
   - In Streamlit, set **Sugar** stock to `4.0 kg` (Minimum: `10.0 kg`).
2. **Approve:**
   - In Slack `#admin-approvals`, click **`[✅ Approve Purchase]`**.
3. **Wholesaler Reports Stockout:**
   - In Slack `#purchase-orders`, Wholesaler clicks **`[🚫 Out of Stock]`**.
4. **Alternative Supplier Recommendation:**
   - Switch to `#inventory-alerts`: Show that the **Supplier Agent** alerted the Admin that Golden Harvest is out of stock, and recommended registered alternatives (*Apex Agro*, *PureOil Refineries*).

---

## 9. Slack App Setup (Live Mode)

To connect the application to a live Slack workspace:

1. Visit [api.slack.com/apps](https://api.slack.com/apps) and click **Create New App** -> **From an app manifest**.
2. Select your workspace and paste the following manifest:

```json
{
  "display_information": {
    "name": "Smart Grocery AI Agent",
    "description": "Agentic AI Grocery Inventory & Procurement Agent"
  },
  "features": {
    "bot_user": {
      "display_name": "GroceryAgent",
      "always_online": true
    }
  },
  "oauth_config": {
    "scopes": {
      "bot": [
        "chat:write",
        "chat:write.public",
        "channels:read",
        "channels:history",
        "commands"
      ]
    }
  },
  "settings": {
    "socket_mode_enabled": true
  }
}
```

3. Enable **Socket Mode** and generate an **App-Level Token** (`xapp-...`) with `connections:write`.
4. Install the App to your workspace and copy the **Bot User OAuth Token** (`xoxb-...`) and **Signing Secret**.
5. Copy `.env.example` to `.env` and fill in the values:
```env
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_APP_TOKEN=xapp-your-token
SLACK_SIGNING_SECRET=your-signing-secret
```
6. Create the 5 channels (`#inventory-alerts`, `#admin-approvals`, `#purchase-orders`, `#supplier-updates`, `#inventory-reports`) and invite the `@GroceryAgent` bot.

---

## 10. Test Suite

Run the comprehensive test suite with `pytest`:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

### Test Coverage Summary:
- `tests/test_stock_detection.py` — Stock threshold checks (sufficient, low stock, stockout, planner formulas).
- `tests/test_approvals.py` — Admin approvals, rejections, duplicate active order prevention.
- `tests/test_supplier_responses.py` — Wholesaler availability confirmation and out-of-stock alternative recommendation.
- `tests/test_dispatch_and_receiving.py` — Strict verification that stock does NOT increase at dispatch, and increases ONLY upon confirmed goods receipt.
- `tests/test_langgraph_workflow.py` — Full LangGraph StateGraph traversal, conditional edge routing, checkpointer verification.

All **17 tests pass** cleanly.

---

## 11. Project Structure

```
smart_grocery_agent/
│
├── app/
│   ├── main.py                     # Streamlit Presentation Dashboard & CLI runner
│   ├── config.py                   # Pydantic Settings & environment variables
│   └── __init__.py
│
├── agents/
│   ├── supervisor_agent.py         # Multi-agent orchestrator & router
│   ├── inventory_agent.py          # Stock monitoring & restock execution
│   ├── alert_agent.py              # Low-stock Slack alert dispatcher
│   ├── planner_agent.py            # Safety stock & reorder calculation
│   ├── approval_agent.py           # Human-in-the-loop Admin authorization
│   ├── procurement_agent.py        # Purchase Order generation & PO dispatch
│   ├── supplier_agent.py           # Wholesaler availability, dispatch & OOS
│   ├── notification_agent.py       # Workflow status & delivery reports
│   └── __init__.py
│
├── graph/
│   ├── state.py                    # TypedDict workflow state schema
│   ├── nodes.py                    # LangGraph execution nodes
│   ├── routing.py                  # Conditional edges & branching logic
│   ├── builder.py                  # StateGraph builder, compiler & runner
│   ├── checkpoint.py               # MemorySaver checkpointer for human-in-the-loop
│   └── __init__.py
│
├── slack/
│   ├── slack_app.py                # Slack Bolt App, WebClient & Demo Simulator
│   ├── interactive_buttons.py      # Block Kit interactive button handlers
│   ├── events.py                   # Signature verification & role authorization
│   ├── commands.py                 # Slash commands (/stock-check, /pending-orders)
│   ├── messages.py                 # Slack Block Kit message builders
│   └── __init__.py
│
├── database/
│   ├── models.py                   # SQLAlchemy ORM models (Product, PO, Approval, etc.)
│   ├── connection.py               # Engine & session maker (MySQL / SQLite fallback)
│   ├── repository.py               # Transactional data access & business logic
│   └── __init__.py
│
├── tools/
│   ├── inventory_tools.py          # Stock inspection and restock tools
│   ├── purchase_tools.py           # Order generation & deficit math
│   ├── supplier_tools.py           # Wholesaler decision & dispatch tools
│   ├── notification_tools.py       # Slack Block Kit payload builders
│   └── __init__.py
│
├── services/
│   ├── stock_monitor.py            # Automated periodic inventory scanner
│   ├── scheduler.py                # APScheduler background monitor
│   ├── audit_service.py            # Audit logging & compliance history
│   └── __init__.py
│
├── tests/
│   ├── test_stock_detection.py
│   ├── test_approvals.py
│   ├── test_supplier_responses.py
│   ├── test_dispatch_and_receiving.py
│   ├── test_langgraph_workflow.py
│   └── __init__.py
│
├── .env.example                    # Sample configuration template
├── requirements.txt                # Production dependency list
├── README.md                       # Comprehensive documentation
├── run.bat                         # One-click Windows runner
└── app.py                          # Root proxy runner
```
