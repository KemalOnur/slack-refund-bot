import os
from refund_store import init_db, insert_refund
from flask import Flask, request
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from dotenv import load_dotenv  


load_dotenv()


FINANCE_CHANNEL = os.getenv("FINANCE_CHANNEL", "#finance")

app = App(
    token = os.environ["SLACK_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"],
)


@app.view("refund_submit")
def handle_submit(ack, body, client, view):
    ack()


    vals = view["state"]["values"]
    order_id = vals["order"]["order_id"]["value"].strip()
    amount = float(vals["amount"]["amount"]["value"])
    reason = vals["reason"]["reason"]["value"].strip()
    user_id = body["user"]["id"]

    init_db()
    req_id = insert_refund(order_id=order_id, amount=amount, currency="TRY",
                           reason=reason, requested_by=user_id)
    
    client.chat_postMessage(
        channel=FINANCE_CHANNEL,
        text=f"New refund request #{req_id} - order `{order_id}` - {amount} TRY (PENDING)"
    )


@app.command("/refund")
def refund_cmd(ack,body,command, client):
    ack()
    parts = command.get("text","").split(maxsplit=2)
    order_id = parts[0] if len(parts) > 0 else ""
    amount = parts[1] if len(parts) > 1 else ""
    reason = parts[2] if len(parts) > 2 else ""

    client.views_open(
        trigger_id = body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "refund_submit",
            "title": {"type": "plain_text", "text": "Refund"},
            "submit": {"type": "plain_text", "text": "Submit"},
            "blocks": [
                {"type": "input", "block_id":"order",
                 "label": {"type":"plain_text","text":"Order ID"},
                 "element":{"type":"plain_text_input","action_id":"order_id","initial_value":order_id}},
                {"type": "input", "block_id":"amount",
                 "label":{"type":"plain_text","text":"Amount (TRY)"},
                 "element":{"type":"plain_text_input","action_id":"amount","initial_value":amount}},
                {"type":"input","block_id":"reason",
               "label":{"type":"plain_text","text":"Reason"},
               "element":{"type":"plain_text_input","action_id":"reason","initial_value":reason,"multiline":True}}
            ]

        }
    )

flask_app = Flask(__name__)
handler = SlackRequestHandler(app)

@flask_app.post("/slack/events")
def slack_events():
    return handler.handle(request)

@flask_app.get("/healthz")
def healthz():
    return {"ok": True}


if __name__ == "__main__":
    flask_app.run(host="0.0.0.0", port=3000)