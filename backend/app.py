from flask import Flask, request, jsonify
from flask_cors import CORS
from tinydb import TinyDB, Query
from datetime import date, datetime
import os, uuid

app = Flask(__name__)

# allow firebase hosting domain, edit when deploy
CORS(app, origins=[
    "http://localhost:5000",
    "http://127.0.0.1:5000",
    "https://<your-firebase-app>.web.app",
    "https://<your-custom-domain>"
])

DB_PATH = os.environ.get("NCWC_DB", "db.json")
db = TinyDB(DB_PATH)
T_USERS = db.table("users")
T_TXNS = db.table("transactions")
T_SAV = db.table("savings")
T_SPL = db.table("splits")

USER_ID = "U1"

@app.get("/api/health")
def health():
    return {"ok": True, "time": datetime.utcnow().isoformat()}

@app.post("/api/transactions")
def add_txn():
    d = request.get_json(force=True)
    amount = float(d.get("amount", 0))
    direction = d.get("direction", "EXPENSE")
    category = d.get("category", "")
    note = d.get("note", "")
    day = d.get("date") or date.today().isoformat()
    if direction.upper() == "EXPENSE" and amount > 0:
        amount = -amount
    if direction.upper() == "INCOME" and amount < 0:
        amount = -amount
    doc = {
        "txn_id": str(uuid.uuid4()),
        "user_id": USER_ID,
        "amount": amount,
        "direction": direction.upper(),
        "category": category,
        "note": note,
        "date": day,
        "created_at": datetime.utcnow().isoformat()
    }
    T_TXNS.insert(doc)
    return {"ok": True, "data": doc}, 201

@app.get("/api/transactions")
def list_txn():
    ym = request.args.get("ym")
    q = Query()
    docs = [t for t in T_TXNS.search(q.user_id == USER_ID)]
    if ym:
        docs = [t for t in docs if str(t.get("date","")).startswith(ym)]
    docs.sort(key=lambda x: (x.get("date",""), x.get("created_at","")), reverse=True)
    return {"ok": True, "data": docs}

@app.delete("/api/transactions/<txn_id>")
def del_txn(txn_id):
    T_TXNS.remove(Query().txn_id == txn_id)
    return {"ok": True}

@app.post("/api/savings")
def add_saving():
    d = request.get_json(force=True)
    amount = float(d.get("amount", 0))
    note = d.get("note", "")
    day = d.get("date") or date.today().isoformat()
    doc = {
        "saving_id": str(uuid.uuid4()),
        "user_id": USER_ID,
        "amount": amount,
        "note": note,
        "date": day,
        "created_at": datetime.utcnow().isoformat()
    }
    T_SAV.insert(doc)
    return {"ok": True, "data": doc}, 201

@app.get("/api/savings")
def list_saving():
    q = Query()
    docs = [s for s in T_SAV.search(q.user_id == USER_ID)]
    docs.sort(key=lambda x: (x.get("date",""), x.get("created_at","")), reverse=True)
    return {"ok": True, "data": docs}

@app.delete("/api/savings/<saving_id>")
def del_saving(saving_id):
    T_SAV.remove(Query().saving_id == saving_id)
    return {"ok": True}

@app.post("/api/split")
def split():
    d = request.get_json(force=True)
    total = float(d.get("total_amount", 0))
    people = int(d.get("people_count", 1))
    if people <= 0:
        return {"ok": False, "error": "people_count must be > 0"}, 400
    per = round(total/people, 2)
    doc = {
        "split_id": str(uuid.uuid4()),
        "user_id": USER_ID,
        "total_amount": total,
        "people_count": people,
        "per_person": per,
        "date": date.today().isoformat(),
        "created_at": datetime.utcnow().isoformat()
    }
    T_SPL.insert(doc)
    return {"ok": True, "data": {"per_person": per, **doc}}, 201

@app.get("/api/summary")
def summary():
    ym = request.args.get("ym") or date.today().strftime("%Y-%m")
    q = Query()
    tx = [t for t in T_TXNS.search(q.user_id == USER_ID) if str(t.get("date","")).startswith(ym)]
    inc = sum(float(t["amount"]) for t in tx if t["direction"]=="INCOME")
    exp = sum(-float(t["amount"]) if t["amount"]<0 else float(t["amount"]) for t in tx if t["direction"]=="EXPENSE")
    net = inc - exp
    total_saving = sum(float(s["amount"]) for s in T_SAV.search(q.user_id == USER_ID))
    return {"ok": True, "ym": ym, "income": inc, "expense": exp, "net": net, "total_saving": total_saving}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
