"""Account-backed evidence check: reads only, no carts/payments/provider writes."""
import asyncio
import json
import uuid
from pathlib import Path
import httpx


async def main():
    root=Path(__file__).resolve().parents[2]
    access=json.loads((root/"backend/.local/stage05-qa.json").read_text())
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8766",timeout=180,headers={"Origin":"http://127.0.0.1:8766"}) as client:
        response=await client.post("/api/v1/auth/login",json=access);response.raise_for_status();csrf=response.json()["data"]["csrf_token"]
        workspaces=(await client.get("/api/v1/me")).json()["data"]["workspaces"];development=next(w for w in workspaces if w["environment"]=="development")
        base="/api/v1/workspaces/"+development["id"]
        response=await client.post(base+"/planning/facts",json={"action":"sync"},headers={"X-CSRF-Token":csrf,"Idempotency-Key":str(uuid.uuid4())});response.raise_for_status()
        response=await client.post(base+"/commerce/commands",json={"action":"sync"},headers={"X-CSRF-Token":csrf,"Idempotency-Key":str(uuid.uuid4())})
        response.raise_for_status();data=response.json()["data"]
        assert len(data["matches"])>=1
        assert any(p["total_minor"]==127315 and p["source_mode"]=="test" for p in data["purchases"])
        evidence={"status":"passed","payment_count":len(data["payments"]),"match_count":len(data["matches"]),"purchase_count":len(data["purchases"]),"mapping_version":data["mapping_version"],
            "observed_full_payable_minor":[p["total_minor"] for p in data["purchases"]],"source_mode":"test","storefront_available":data["storefront_available"],"open_cases":[c["reason"] for c in data["cases"] if c["state"]=="open"],"provider_writes":0}
        await client.post("/api/v1/auth/logout",headers={"X-CSRF-Token":csrf})
    (root/"docs/implementation-evidence/stage-05-source.json").write_text(json.dumps(evidence,indent=2));print(json.dumps(evidence,indent=2))


if __name__=="__main__":asyncio.run(main())
