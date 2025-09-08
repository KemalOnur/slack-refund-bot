import os
from refund_store import init_db, insert_refund, update_status, get_refund
from refund_service import RefundService
from flask import Flask, request
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from dotenv import load_dotenv  


load_dotenv()


FINANCE_CHANNEL = os.getenv("FINANCE_CHANNEL", "#finance")
APPROVER_USER_IDS = set(u.strip() for u in os.getenv("APPROVER_USER_IDS","").split(",") if u.strip())

app = App(
    token = os.environ["SLACK_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"],
)



def render_refund_blocks(req_id:int, order_id:str, amount:float, status:str, decided_by:str|None=None):     
    header = {"type":"section","text":{"type":"mrkdwn","text":f"*Refund #{req_id}*\n• Order `{order_id}`\n• Amount *{amount} TRY*\n_Status: *{status}*_" }}
    if status == "PENDING":
        actions = {"type":"actions","elements":[
            {"type":"button","text":{"type":"plain_text","text":"Approve"},"style":"primary","value":str(req_id),"action_id":"refund_approve"},
            {"type":"button","text":{"type":"plain_text","text":"Reject"},"style":"danger","value":str(req_id),"action_id":"refund_reject"}
        ]}
        return [header, actions]
    decided = {"type":"context","elements":[{"type":"mrkdwn","text":f"Decided by <@{decided_by}>" }]} if decided_by else None
    return [header] + ([decided] if decided else [])



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
        text=f"Refund #{req_id} created PENDING",
        blocks=render_refund_blocks(req_id, order_id, amount, "PENDING")
    )


@app.action("refund_approve")
def on_approve(ack, body, action, client, respond):
    ack()
    user = body["user"]["id"]
    if user not in APPROVER_USER_IDS:
        return respond(respond_type="ephemeral",text="You are not authorized for this task")
    
    #print(action)
    req_id = int(action["value"])
    row = get_refund(req_id)
    if not row:
        return respond(text=f"Refund #{req_id} not found" )
    

    svc = RefundService()
    ok, ext_id, err = svc.refund(order_id=row[1], amount=row[2], currency=row[3], reason="")

    channel = body["container"]["channel_id"]
    ts      = body["message"]["ts"]

    if ok:
        update_status(req_id, "SUCCEEDED")
        client.chat_update(
            channel=channel,
            ts=ts,
            text=f"Refund #{req_id} SUCCEEDED",
            blocks=render_refund_blocks(req_id, row[1], row[2], "SUCCEEDED", decided_by=user)
        )
    else:
        update_status(req_id, "FAILED")
        client.chat_update(
            channel=channel,
            ts=ts,
            text=f"Refund #{req_id} FAILED",
            blocks=render_refund_blocks(req_id, row[1], row[2], "FAILED", decided_by=user)
        )



@app.action("refund_reject")
def on_reject(ack, body, action, client, respond):    
    ack()
    user = body["user"]["id"]
    if user not in APPROVER_USER_IDS:
        return respond(respond_type="ephemeral", text="You are not authorized for this task")
    
    req_id = int(action["value"])
    row = get_refund(req_id)
    if not row:
        return respond(text=f"Refund #{req_id} not found" )
    
    update_status(req_id, "REJECTED")

    channel = body["container"]["channel_id"]
    ts      = body["message"]["ts"]

    client.chat_update(
        channel=channel,
        ts=ts,
        text=f"Refund #{req_id} REJECTED",
        blocks=render_refund_blocks(req_id, row[1], row[2], "REJECTED", decided_by=user)
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