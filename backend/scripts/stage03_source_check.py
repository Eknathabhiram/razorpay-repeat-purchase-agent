"""Read-only real source check through the authenticated scoped application."""
import asyncio
import json
from pathlib import Path
import uuid
import httpx


async def main():
    root=Path(__file__).resolve().parents[2]
    access=json.loads((root/"backend/.local/stage02-qa.json").read_text())
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8766",timeout=180,headers={"Origin":"http://127.0.0.1:8766"}) as client:
        response=await client.post("/api/v1/auth/login",json=access)
        response.raise_for_status()
        csrf=response.json()["data"]["csrf_token"]
        workspaces=(await client.get("/api/v1/me")).json()["data"]["workspaces"]
        development=next(w for w in workspaces if w["environment"]=="development")
        base="/api/v1/workspaces/"+development["id"]+"/planning"
        response=await client.post(base+"/facts",json={"action":"sync"},headers={"X-CSRF-Token":csrf,"Idempotency-Key":str(uuid.uuid4())})
        if response.status_code!=200:
            evidence={"status":"blocked","http_status":response.status_code,"error":response.json().get("error",{}),"provider_writes":0}
        else:
            data=response.json()["data"]
            scope=[v["provider_variant_id"] for v in data["variants"] if v.get("sku")=="TEST-LAUNDRY-1L"]
            assert len(scope)==1
            response=await client.post(base+"/policies",json={"expected_revision":data["policy"]["revision"] if data["policy"] else 0,"config":{"variant_ids":scope,"fallback_days":30}},headers={"X-CSRF-Token":csrf,"Idempotency-Key":str(uuid.uuid4())})
            response.raise_for_status();data=response.json()["data"]
            assert not any(o["eligible"] for o in data["opportunities"])
            reasons=sorted({code for item in data["opportunities"] for code in item["exclusion_codes"]})
            assert data["fact_counts"]["paid_unfulfilled_orders"] >= 1
            assert data["fact_counts"]["confirmed_deliveries"] == 0
            evidence={"status":"passed_with_explicit_missing_facts","facts_version":data["facts_version"],"fact_counts":data["fact_counts"],"customer_count":len(data["opportunities"]),"eligible_count":0,"exclusion_codes":reasons,"coverage_complete":data["coverage_complete"],"notes":data["coverage_notes"],"provider_writes":0}
        await client.post("/api/v1/auth/logout",headers={"X-CSRF-Token":csrf})
    (root/"docs/implementation-evidence/stage-03-source.json").write_text(json.dumps(evidence,indent=2))
    print(json.dumps(evidence,indent=2))


if __name__=="__main__": asyncio.run(main())
