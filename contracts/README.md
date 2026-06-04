# EvidenceRegistry contract notes

`EvidenceRegistry.sol` is the EVM contract scaffold for anchoring evidence metadata.

## Expected flow

1. Backend detects an incident.
2. Backend writes a snapshot and metadata JSON off-chain.
3. Backend computes:
   - `file_sha256`
   - `metadata_sha256`
4. Backend calls `anchorEvidence(...)` on the contract.
5. Dashboard stores and shows:
   - transaction hash
   - block number
   - anchor status
   - verify status

## Required environment variables for EVM mode

- `ANCHOR_MODE=evm`
- `ANCHOR_CHAIN_ID=<numeric chain id>`
- `EVM_RPC_URL=<rpc endpoint>`
- `EVM_PRIVATE_KEY=<service wallet private key>`
- `EVM_ACCOUNT_ADDRESS=<optional sender address>`
- `EVM_CONTRACT_ADDRESS=<deployed EvidenceRegistry address>`
- `ANCHOR_EXPLORER_TX_BASE=<optional tx explorer base url>`

Example explorer base:

- Sepolia: `https://sepolia.etherscan.io/tx`
- Polygon Amoy: `https://amoy.polygonscan.com/tx`
