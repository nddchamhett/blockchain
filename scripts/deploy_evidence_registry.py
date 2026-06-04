import json
import os
import sys

from dotenv import load_dotenv

try:
    from web3 import Web3
except ImportError as exc:
    raise SystemExit("web3 is required. Install dependencies from requirements.txt first.") from exc


load_dotenv()


DEFAULT_ARTIFACT_PATH = os.path.join("contracts", "EvidenceRegistry.bytecode.json")


def load_deploy_config():
    rpc_url = os.getenv("EVM_RPC_URL", "").strip()
    private_key = os.getenv("EVM_PRIVATE_KEY", "").strip()
    chain_id = os.getenv("ANCHOR_CHAIN_ID", "").strip()
    explorer_base = os.getenv("ANCHOR_EXPLORER_TX_BASE", "").strip()

    if not rpc_url:
        raise SystemExit("EVM_RPC_URL is missing")
    if not private_key:
        raise SystemExit("EVM_PRIVATE_KEY is missing")
    if not chain_id or not chain_id.isdigit():
        raise SystemExit("ANCHOR_CHAIN_ID must be set to a numeric EVM chain id")

    return rpc_url, private_key, int(chain_id), explorer_base


def load_contract_artifacts():
    abi_path = os.path.join("contracts", "EvidenceRegistry.abi.json")
    bytecode_path = os.getenv("EVIDENCE_REGISTRY_BYTECODE_PATH", DEFAULT_ARTIFACT_PATH).strip() or DEFAULT_ARTIFACT_PATH

    if not os.path.exists(abi_path):
        raise SystemExit(f"ABI file not found: {abi_path}")
    if not os.path.exists(bytecode_path):
        raise SystemExit(
            "Bytecode artifact not found: {0}\n"
            "Compile EvidenceRegistry.sol first and write JSON like {{\"bytecode\": \"0x...\"}}.".format(bytecode_path)
        )

    with open(abi_path, "r", encoding="utf-8") as handle:
        abi = json.load(handle)
    with open(bytecode_path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)

    bytecode = payload.get("bytecode", "").strip()
    if not bytecode.startswith("0x"):
        raise SystemExit("Bytecode JSON must contain a 'bytecode' field starting with 0x")

    return abi, bytecode, bytecode_path


def main():
    rpc_url, private_key, chain_id, explorer_base = load_deploy_config()
    abi, bytecode, bytecode_path = load_contract_artifacts()

    web3 = Web3(Web3.HTTPProvider(rpc_url))
    if not web3.is_connected():
        raise SystemExit("Unable to connect to the configured EVM RPC")

    account = web3.eth.account.from_key(private_key)
    contract = web3.eth.contract(abi=abi, bytecode=bytecode)

    tx = contract.constructor().build_transaction(
        {
            "from": account.address,
            "nonce": web3.eth.get_transaction_count(account.address),
            "chainId": chain_id,
            "gasPrice": web3.eth.gas_price,
        }
    )
    if "gas" not in tx:
        tx["gas"] = contract.constructor().estimate_gas({"from": account.address})

    signed = web3.eth.account.sign_transaction(tx, private_key=private_key)
    tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction).hex()
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

    print("Deployment successful")
    print("Sender:", account.address)
    print("Chain ID:", chain_id)
    print("Artifact bytecode:", bytecode_path)
    print("Transaction hash:", tx_hash)
    print("Contract address:", receipt.contractAddress)
    if explorer_base:
        print("Explorer:", explorer_base.rstrip("/") + "/" + tx_hash)


if __name__ == "__main__":
    main()
