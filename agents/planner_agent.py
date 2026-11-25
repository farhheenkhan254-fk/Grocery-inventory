import logging
from typing import Dict, Any
from tools.purchase_tools import calculate_reorder_plan
from app.config import settings

logger = logging.getLogger("smart_grocery.agents.planner")

class PlannerAgent:
    """
    Planner Agent:
    - Analyses inventory requirements.
    - Calculates suggested reorder quantity using inventory rules & buffer formulas.
    - Prepares a purchase plan.
    - Safety rule: Never independently approves a purchase.
    """
    def __init__(self):
        self.name = "Planner Agent"

    def generate_plan(self, product: Dict[str, Any]) -> Dict[str, Any]:
        curr = product.get("current_stock", 0.0)
        min_stock = product.get("minimum_stock", 10.0)
        base_reorder = product.get("reorder_quantity", 50.0)

        plan = calculate_reorder_plan(
            current_stock=curr,
            minimum_stock=min_stock,
            base_reorder=base_reorder,
            lead_time_days=settings.DEFAULT_LEAD_TIME_DAYS,
            safety_factor=settings.SAFETY_STOCK_FACTOR
        )

        # Optional LLM justification if Groq is enabled
        justification = f"Stock level ({curr} {product.get('unit')}) is at or below safety threshold ({min_stock} {product.get('unit')}). Suggested order quantity is {plan['suggested_quantity']} {product.get('unit')}."

        if settings.is_groq_configured:
            try:
                from groq import Groq
                client = Groq(api_key=settings.GROQ_API_KEY)
                completion = client.chat.completions.create(
                    model=settings.GROQ_MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an AI inventory procurement specialist. In 1 concise sentence, provide a business justification for reordering this grocery item."
                        },
                        {
                            "role": "user",
                            "content": f"Product: {product.get('name')}, Current Stock: {curr}, Minimum Threshold: {min_stock}, Suggested Quantity: {plan['suggested_quantity']} {product.get('unit')}."
                        }
                    ],
                    max_tokens=60,
                    temperature=0.3
                )
                justification = completion.choices[0].message.content.strip()
            except Exception as e:
                logger.warning(f"Groq LLM planner call failed ({e}); using rule justification.")

        plan["justification"] = justification
        plan["never_auto_approve"] = True
        logger.info(f"[{self.name}] Reorder plan generated: {plan['suggested_quantity']} {product.get('unit')} for {product.get('name')}")
        return plan

planner_agent = PlannerAgent()
