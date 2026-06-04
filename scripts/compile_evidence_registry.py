import json
import os
from pathlib import Path

from dotenv import load_dotenv
import requests

try:
    from solcx import compile_standard, get_installed_solc_versions, install_solc, set_solc_version
except ImportError as exc:
    raise SystemExit("py-solc-x is required. Install it before compiling the contract.") from exc


load_dotenv()


DEFAULT_SOLC_VERSION = os.getenv("SOLC_VERSION", "0.8.20").strip() or "0.8.20"
CONTRACT_PATH = Path("contracts") / "EvidenceRegistry.sol"
ABI_OUTPUT_PATH = Path("contracts") / "EvidenceRegistry.abi.json"
BYTECODE_OUTPUT_PATH = Path("contracts") / "EvidenceRegistry.bytecode.json"
SOLCX_INSTALL_DIR = Path(os.getenv("SOLCX_INSTALL_DIR", os.path.join("data", "solcx")))


def main():
    if not CONTRACT_PATH.exists():
        raise SystemExit(f"Contract source not found: {CONTRACT_PATH}")

    source = CONTRACT_PATH.read_text(encoding="utf-8")
    SOLCX_INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    os.environ["SOLCX_BINARY_PATH"] = str(SOLCX_INSTALL_DIR.resolve())
    installed_versions = {str(version) for version in get_installed_solc_versions(solcx_binary_path=SOLCX_INSTALL_DIR)}
    if DEFAULT_SOLC_VERSION not in installed_versions:
        try:
            install_solc(DEFAULT_SOLC_VERSION, solcx_binary_path=SOLCX_INSTALL_DIR)
        except requests.RequestException as exc:
            raise SystemExit(
                "Failed to download solc compiler. Check network/proxy settings or run this script with network access."
            ) from exc
    set_solc_version(DEFAULT_SOLC_VERSION, solcx_binary_path=SOLCX_INSTALL_DIR)

    compiled = compile_standard(
        {
            "language": "Solidity",
            "sources": {
                str(CONTRACT_PATH): {
                    "content": source,
                }
            },
            "settings": {
                "outputSelection": {
                    "*": {
                        "*": ["abi", "evm.bytecode.object"]
                    }
                }
            },
        }
    )

    contract_data = compiled["contracts"][str(CONTRACT_PATH)]["EvidenceRegistry"]
    abi = contract_data["abi"]
    bytecode = "0x" + contract_data["evm"]["bytecode"]["object"]

    ABI_OUTPUT_PATH.write_text(json.dumps(abi, ensure_ascii=True, indent=2), encoding="utf-8")
    BYTECODE_OUTPUT_PATH.write_text(json.dumps({"bytecode": bytecode}, ensure_ascii=True, indent=2), encoding="utf-8")

    print("Compilation successful")
    print("Solc version:", DEFAULT_SOLC_VERSION)
    print("ABI output:", ABI_OUTPUT_PATH)
    print("Bytecode output:", BYTECODE_OUTPUT_PATH)


if __name__ == "__main__":
    main()
