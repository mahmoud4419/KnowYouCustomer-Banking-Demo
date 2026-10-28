"""Amazon Bedrock helpers: bilingual relationship briefing + fraud case narrative (Converse API)."""
import json
import boto3

DEFAULT_MODEL_ID = "us.amazon.nova-pro-v1:0"   # cross-region inference profile; change to any enabled text model


def _ask(prompt, model_id=DEFAULT_MODEL_ID, region="us-east-1", max_tokens=700):
    br = boto3.client("bedrock-runtime", region_name=region)
    r = br.converse(modelId=model_id, messages=[{"role": "user", "content": [{"text": prompt}]}],
                    inferenceConfig={"maxTokens": max_tokens, "temperature": 0.2})
    return r["output"]["message"]["content"][0]["text"]


def customer_briefing(profile: dict, **kw):
    prompt = ("You are assisting a relationship manager at a retail bank. Using ONLY this golden customer profile, "
              "write a 3-sentence relationship briefing with one next-best-action suggestion. Write it in English, "
              "then in Arabic. Do not invent facts.\n\nPROFILE:\n" + json.dumps(profile, default=str, ensure_ascii=False))
    return _ask(prompt, **kw)


def fraud_case_narrative(customer: dict, alerts: list, **kw):
    prompt = ("You are a fraud investigator's assistant at a retail bank. Using ONLY the customer profile and the flagged "
              "transactions below, write a concise case summary: what happened, which risk signals fired, why it deviates "
              "from the customer's normal behavior, and a recommended action. Do not invent facts.\n\nCUSTOMER:\n"
              + json.dumps(customer, default=str, ensure_ascii=False) + "\n\nFLAGGED TRANSACTIONS:\n"
              + json.dumps(alerts, default=str, ensure_ascii=False))
    return _ask(prompt, **kw)
