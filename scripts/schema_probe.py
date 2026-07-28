#!/usr/bin/env python3
import argparse
import json
import sys
import urllib.request
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="GenLayer Read-Only RPC Contract Schema Probe")
    parser.add_argument(
        "--rpc",
        default="https://studio.genlayer.com/api",
        help="GenLayer RPC URL endpoint (default: https://studio.genlayer.com/api)",
    )
    parser.add_argument(
        "contracts",
        nargs="*",
        default=["contracts/price_ledger.py", "contracts/merchant_bond.py"],
        help="Contract file paths to probe",
    )
    args = parser.parse_args()

    success_count = 0
    total_count = len(args.contracts)

    for contract_path_str in args.contracts:
        contract_path = Path(contract_path_str)
        if not contract_path.is_file():
            print(f"ERROR: Contract file not found: {contract_path_str}", file=sys.stderr)
            sys.exit(1)

        code = contract_path.read_text(encoding="utf-8")
        payload = {
            "jsonrpc": "2.0",
            "method": "gen_getContractSchemaForCode",
            "params": [code],
            "id": 1,
        }

        req = urllib.request.Request(
            args.rpc,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = json.loads(resp.read().decode("utf-8"))

            if "error" in body and body["error"]:
                err = body["error"]
                print(f"[{contract_path.name}] RPC ERROR: {err.get('message', err)}", file=sys.stderr)
            elif "result" in body and body["result"]:
                schema = body["result"]
                methods_count = len(schema.get("methods", {}))
                ctor_params = len(schema.get("ctor", {}).get("params", []))
                print(f"[{contract_path.name}] SCHEMA OK: ctor params={ctor_params}, methods={methods_count}")
                success_count += 1
            else:
                print(f"[{contract_path.name}] RPC RESPONSE UNKNOWN: {body}", file=sys.stderr)
        except Exception as e:
            print(f"[{contract_path.name}] HTTP/NETWORK ERROR: {e}", file=sys.stderr)

    if success_count < total_count:
        sys.exit(1)


if __name__ == "__main__":
    main()
