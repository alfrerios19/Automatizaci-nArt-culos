import os
import json
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI

app = FastAPI()

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

ODOO_URL = os.environ["ODOO_URL"].rstrip("/")
ODOO_DB = os.environ["ODOO_DB"]
ODOO_UID = int(os.environ["ODOO_UID"])
ODOO_API_KEY = os.environ["ODOO_API_KEY"]
ODOO_BLOG_ID = int(os.environ.get("ODOO_BLOG_ID", "1"))


class PublishRequest(BaseModel):
    title: str
    subtitle: str
    html: str
    image_prompt: str


def odoo_call(model: str, method: str, args: list, request_id: int = 1):
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": "object",
            "method": "execute_kw",
            "args": [
                ODOO_DB,
                ODOO_UID,
                ODOO_API_KEY,
                model,
                method,
                args
            ]
        },
        "id": request_id
    }

    response = requests.post(
        f"{ODOO_URL}/jsonrpc",
        json=payload,
        timeout=120
    )
    response.raise_for_status()
    data = response.json()

    if "error" in data:
        raise Exception(data["error"])

    return data["result"]


def generate_image_base64(prompt: str):

    test_image_base64 = (
        "iVBORw0KGgoAAAANSUhEUgAAASwAAAEsCAIAAAD2HxkiAAAACXBIWXMAAAsSAAALEgHS3X78AAABFUlEQVR4nO3QMQEAAAgDINc/9K3h"
        "HBQ0Q0AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        "AAAAAPgG9wABv9cQtwAAAABJRU5ErkJggg=="
    )

    return test_image_base64, "image/png"


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/publish")
def publish_article(req: PublishRequest):
    try:
        image_b64, mimetype = generate_image_base64(req.image_prompt)

        post_id = odoo_call(
            "blog.post",
            "create",
            [{
                "name": req.title,
                "content": req.html,
                "subtitle": req.subtitle,
                "blog_id": ODOO_BLOG_ID,
                "website_published": True
            }],
            request_id=1
        )

        attachment_id = odoo_call(
            "ir.attachment",
            "create",
            [{
                "name": f"cover_{post_id}.png",
                "res_model": "blog.post",
                "res_id": post_id,
                "type": "binary",
                "public": True,
                "mimetype": mimetype,
                "datas": image_b64
            }],
            request_id=2
        )

        cover_properties = json.dumps({
            "background-image": f"url('/web/image/ir.attachment/{attachment_id}/datas')"
        })

        try:
            odoo_call(
                "blog.post",
                "write",
                [[post_id], {
                    "cover_properties": cover_properties
                }],
                request_id=3
            )
            cover_field = "cover_properties"
        except Exception:
            odoo_call(
                "blog.post",
                "write",
                [[post_id], {
                    "website_cover_properties": cover_properties
                }],
                request_id=4
            )
            cover_field = "website_cover_properties"

        return {
            "ok": True,
            "post_id": post_id,
            "attachment_id": attachment_id,
            "cover_field": cover_field
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))





