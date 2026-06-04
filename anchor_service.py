import hashlib
import json
import os
from datetime import datetime, timezone


try:
    from web3 import Web3
    from web3.providers.eth_tester import EthereumTesterProvider
except ImportError:  # pragma: no cover - optional dependency at runtime
    Web3 = None
    EthereumTesterProvider = None

try:
    from eth_tester import EthereumTester
except ImportError:  # pragma: no cover - optional dependency at runtime
    EthereumTester = None


ANCHOR_MODE = os.getenv("ANCHOR_MODE", "local-ledger").strip() or "local-ledger"
ANCHOR_LEDGER_PATH = os.getenv("ANCHOR_LEDGER_PATH", os.path.join("data", "anchor-ledger.jsonl"))
ANCHOR_CHAIN_ID = os.getenv("ANCHOR_CHAIN_ID", "local-demo-chain")
ANCHOR_EXPLORER_TX_BASE = os.getenv("ANCHOR_EXPLORER_TX_BASE", "").strip()
EVM_RPC_URL = os.getenv("EVM_RPC_URL", "").strip()
EVM_PRIVATE_KEY = os.getenv("EVM_PRIVATE_KEY", "").strip()
EVM_CONTRACT_ADDRESS = os.getenv("EVM_CONTRACT_ADDRESS", "").strip()
EVM_ACCOUNT_ADDRESS = os.getenv("EVM_ACCOUNT_ADDRESS", "").strip()
EVM_BYTECODE_PATH = os.getenv("EVIDENCE_REGISTRY_BYTECODE_PATH", os.path.join("contracts", "EvidenceRegistry.bytecode.json")).strip() or os.path.join("contracts", "EvidenceRegistry.bytecode.json")
LOCAL_EVM_WEB3 = None
LOCAL_EVM_CONTRACT_ADDRESS = None

EVIDENCE_REGISTRY_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "uint256", "name": "incidentId", "type": "uint256"},
            {"indexed": True, "internalType": "bytes32", "name": "fileHash", "type": "bytes32"},
            {"indexed": True, "internalType": "bytes32", "name": "metadataHash", "type": "bytes32"},
            {"indexed": False, "internalType": "string", "name": "storageUri", "type": "string"},
            {"indexed": False, "internalType": "uint256", "name": "detectedAt", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "anchoredAt", "type": "uint256"},
            {"indexed": False, "internalType": "address", "name": "submittedBy", "type": "address"},
        ],
        "name": "EvidenceAnchored",
        "type": "event",
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "incidentId", "type": "uint256"},
            {"internalType": "bytes32", "name": "fileHash", "type": "bytes32"},
            {"internalType": "bytes32", "name": "metadataHash", "type": "bytes32"},
            {"internalType": "string", "name": "storageUri", "type": "string"},
            {"internalType": "uint256", "name": "detectedAt", "type": "uint256"},
        ],
        "name": "anchorEvidence",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "incidentId", "type": "uint256"}],
        "name": "getEvidence",
        "outputs": [
            {
                "components": [
                    {"internalType": "uint256", "name": "incidentId", "type": "uint256"},
                    {"internalType": "bytes32", "name": "fileHash", "type": "bytes32"},
                    {"internalType": "bytes32", "name": "metadataHash", "type": "bytes32"},
                    {"internalType": "string", "name": "storageUri", "type": "string"},
                    {"internalType": "uint256", "name": "detectedAt", "type": "uint256"},
                    {"internalType": "uint256", "name": "anchoredAt", "type": "uint256"},
                    {"internalType": "address", "name": "submittedBy", "type": "address"},
                ],
                "internalType": "struct EvidenceRegistry.EvidenceRecord",
                "name": "",
                "type": "tuple",
            }
        ],
        "stateMutability": "view",
        "type": "function",
    },
]


def ensure_parent_dir(path):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def sha256_text(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_anchor_url(tx_hash):
    if not tx_hash or not ANCHOR_EXPLORER_TX_BASE:
        return None
    return f"{ANCHOR_EXPLORER_TX_BASE.rstrip('/')}/{tx_hash}"


def load_contract_bytecode():
    if not os.path.exists(EVM_BYTECODE_PATH):
        raise FileNotFoundError(f"Bytecode artifact not found: {EVM_BYTECODE_PATH}")
    with open(EVM_BYTECODE_PATH, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    bytecode = payload.get("bytecode", "").strip()
    if not bytecode.startswith("0x"):
        raise ValueError("Bytecode artifact must contain a 0x-prefixed bytecode field")
    return bytecode


def build_anchor_payload(incident, evidence_package):
    payload = {
        "incident_id": incident["id"],
        "source": incident["source"],
        "detected_at": incident["detected_at"],
        "file_sha256": evidence_package["file_sha256"],
        "metadata_sha256": evidence_package["metadata_sha256"],
        "storage_uri": evidence_package["storage_uri"],
    }
    payload_json = json.dumps(payload, ensure_ascii=True, sort_keys=True)
    return payload, sha256_text(payload_json)


def iso_to_unix_seconds(value):
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return int(dt.astimezone(timezone.utc).timestamp())


def anchor_evidence(incident, evidence_package, anchored_at):
    _, anchor_payload_hash = build_anchor_payload(incident, evidence_package)

    if ANCHOR_MODE == "local-ledger":
        return anchor_local_ledger(incident, anchor_payload_hash, anchored_at)
    if ANCHOR_MODE == "evm-local":
        return anchor_evm_local(incident, evidence_package, anchor_payload_hash, anchored_at)
    if ANCHOR_MODE == "evm":
        return anchor_evm(incident, evidence_package, anchor_payload_hash, anchored_at)

    return {
        "anchor_mode": ANCHOR_MODE,
        "anchor_status": "anchor_failed",
        "tx_hash": None,
        "block_number": None,
        "chain_id": ANCHOR_CHAIN_ID,
        "ledger_path": None,
        "anchor_payload_hash": anchor_payload_hash,
        "error_message": f"Unsupported ANCHOR_MODE '{ANCHOR_MODE}'",
        "anchored_at": anchored_at,
        "tx_url": None,
    }


def anchor_local_ledger(incident, anchor_payload_hash, anchored_at):
    ensure_parent_dir(ANCHOR_LEDGER_PATH)
    previous_hash = "GENESIS"
    block_number = 1

    if os.path.exists(ANCHOR_LEDGER_PATH):
        with open(ANCHOR_LEDGER_PATH, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                previous_hash = row["tx_hash"]
                block_number = int(row["block_number"]) + 1

    tx_hash = sha256_text(f"{previous_hash}|{anchor_payload_hash}|{anchored_at}|{incident['id']}")
    entry = {
        "block_number": block_number,
        "previous_hash": previous_hash,
        "tx_hash": tx_hash,
        "anchor_payload_hash": anchor_payload_hash,
        "anchored_at": anchored_at,
        "incident_id": incident["id"],
    }

    with open(ANCHOR_LEDGER_PATH, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=True, sort_keys=True) + "\n")

    return {
        "anchor_mode": ANCHOR_MODE,
        "anchor_status": "anchored",
        "tx_hash": tx_hash,
        "block_number": block_number,
        "chain_id": ANCHOR_CHAIN_ID,
        "ledger_path": ANCHOR_LEDGER_PATH.replace("\\", "/"),
        "anchor_payload_hash": anchor_payload_hash,
        "error_message": None,
        "anchored_at": anchored_at,
        "tx_url": build_anchor_url(tx_hash),
    }


def anchor_evm(incident, evidence_package, anchor_payload_hash, anchored_at):
    if Web3 is None:
        return failed_anchor(anchor_payload_hash, anchored_at, "web3 is not installed")
    if not EVM_RPC_URL:
        return failed_anchor(anchor_payload_hash, anchored_at, "EVM_RPC_URL is missing")
    if not EVM_PRIVATE_KEY:
        return failed_anchor(anchor_payload_hash, anchored_at, "EVM_PRIVATE_KEY is missing")
    if not EVM_CONTRACT_ADDRESS:
        return failed_anchor(anchor_payload_hash, anchored_at, "EVM_CONTRACT_ADDRESS is missing")

    web3 = Web3(Web3.HTTPProvider(EVM_RPC_URL))
    if not web3.is_connected():
        return failed_anchor(anchor_payload_hash, anchored_at, "Unable to connect to EVM RPC")

    account = web3.eth.account.from_key(EVM_PRIVATE_KEY)
    sender = EVM_ACCOUNT_ADDRESS or account.address
    contract = web3.eth.contract(address=Web3.to_checksum_address(EVM_CONTRACT_ADDRESS), abi=EVIDENCE_REGISTRY_ABI)

    tx = contract.functions.anchorEvidence(
        int(incident["id"]),
        Web3.to_bytes(hexstr=evidence_package["file_sha256"]),
        Web3.to_bytes(hexstr=evidence_package["metadata_sha256"]),
        evidence_package["storage_uri"],
        iso_to_unix_seconds(incident["detected_at"]),
    ).build_transaction(
        {
            "from": Web3.to_checksum_address(sender),
            "nonce": web3.eth.get_transaction_count(Web3.to_checksum_address(sender)),
            "chainId": int(ANCHOR_CHAIN_ID),
            "gasPrice": web3.eth.gas_price,
        }
    )

    if "gas" not in tx:
        tx["gas"] = contract.functions.anchorEvidence(
            int(incident["id"]),
            Web3.to_bytes(hexstr=evidence_package["file_sha256"]),
            Web3.to_bytes(hexstr=evidence_package["metadata_sha256"]),
            evidence_package["storage_uri"],
            iso_to_unix_seconds(incident["detected_at"]),
        ).estimate_gas({"from": Web3.to_checksum_address(sender)})

    signed = web3.eth.account.sign_transaction(tx, private_key=EVM_PRIVATE_KEY)
    tx_hash_bytes = web3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash_bytes)
    tx_hash = tx_hash_bytes.hex()

    return {
        "anchor_mode": ANCHOR_MODE,
        "anchor_status": "anchored",
        "tx_hash": tx_hash,
        "block_number": int(receipt.blockNumber),
        "chain_id": ANCHOR_CHAIN_ID,
        "ledger_path": None,
        "anchor_payload_hash": anchor_payload_hash,
        "error_message": None,
        "anchored_at": anchored_at,
        "tx_url": build_anchor_url(tx_hash),
    }


def get_local_evm_contract():
    global LOCAL_EVM_WEB3, LOCAL_EVM_CONTRACT_ADDRESS

    if Web3 is None or EthereumTesterProvider is None or EthereumTester is None:
        raise RuntimeError("web3 or eth-tester is not installed")

    if LOCAL_EVM_WEB3 is None:
        LOCAL_EVM_WEB3 = Web3(EthereumTesterProvider(EthereumTester()))

    if LOCAL_EVM_CONTRACT_ADDRESS is None:
        account = LOCAL_EVM_WEB3.eth.accounts[0]
        bytecode = load_contract_bytecode()
        contract = LOCAL_EVM_WEB3.eth.contract(abi=EVIDENCE_REGISTRY_ABI, bytecode=bytecode)
        tx_hash = contract.constructor().transact({"from": account, "gas": 5_000_000})
        receipt = LOCAL_EVM_WEB3.eth.wait_for_transaction_receipt(tx_hash)
        LOCAL_EVM_CONTRACT_ADDRESS = receipt.contractAddress

    return LOCAL_EVM_WEB3, LOCAL_EVM_WEB3.eth.contract(address=LOCAL_EVM_CONTRACT_ADDRESS, abi=EVIDENCE_REGISTRY_ABI)


def anchor_evm_local(incident, evidence_package, anchor_payload_hash, anchored_at):
    try:
        web3, contract = get_local_evm_contract()
        account = web3.eth.accounts[0]
        tx_hash = contract.functions.anchorEvidence(
            int(incident["id"]),
            Web3.to_bytes(hexstr=evidence_package["file_sha256"]),
            Web3.to_bytes(hexstr=evidence_package["metadata_sha256"]),
            evidence_package["storage_uri"],
            iso_to_unix_seconds(incident["detected_at"]),
        ).transact({"from": account, "gas": 5_000_000})
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        tx_hash_hex = tx_hash.hex() if hasattr(tx_hash, "hex") else str(tx_hash)
        return {
            "anchor_mode": ANCHOR_MODE,
            "anchor_status": "anchored",
            "tx_hash": tx_hash_hex,
            "block_number": int(receipt.blockNumber),
            "chain_id": str(web3.eth.chain_id),
            "ledger_path": LOCAL_EVM_CONTRACT_ADDRESS,
            "anchor_payload_hash": anchor_payload_hash,
            "error_message": None,
            "anchored_at": anchored_at,
            "tx_url": None,
        }
    except Exception as exc:
        return failed_anchor(anchor_payload_hash, anchored_at, f"evm-local failed: {exc}")


def failed_anchor(anchor_payload_hash, anchored_at, message):
    return {
        "anchor_mode": ANCHOR_MODE,
        "anchor_status": "anchor_failed",
        "tx_hash": None,
        "block_number": None,
        "chain_id": ANCHOR_CHAIN_ID,
        "ledger_path": None,
        "anchor_payload_hash": anchor_payload_hash,
        "error_message": message,
        "anchored_at": anchored_at,
        "tx_url": None,
    }


def verify_anchor_record(detail):
    if not detail:
        return "missing"

    tx_hash = detail.get("tx_hash")
    payload_hash = detail.get("anchor_payload_hash")
    if not tx_hash or not payload_hash:
        return "missing"

    if detail.get("anchor_mode") == "local-ledger":
        ledger_path = detail.get("ledger_path")
        if not ledger_path or not os.path.exists(ledger_path):
            return "missing"
        with open(ledger_path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                if row.get("tx_hash") == tx_hash:
                    return "anchored" if row.get("anchor_payload_hash") == payload_hash else "anchor_mismatch"
        return "missing"

    if detail.get("anchor_mode") == "evm":
        if Web3 is None or not EVM_RPC_URL or not EVM_CONTRACT_ADDRESS:
            return "unverified"
        web3 = Web3(Web3.HTTPProvider(EVM_RPC_URL))
        if not web3.is_connected():
            return "unverified"
        try:
            receipt = web3.eth.get_transaction_receipt(tx_hash)
        except Exception:
            return "missing"
        return "anchored" if receipt else "missing"

    if detail.get("anchor_mode") == "evm-local":
        try:
            web3, _ = get_local_evm_contract()
            receipt = web3.eth.get_transaction_receipt(detail.get("tx_hash"))
        except Exception:
            return "missing"
        return "anchored" if receipt else "missing"

    return "unverified"
