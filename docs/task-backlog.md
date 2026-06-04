# Task backlog cho phan blockchain evidence

## Pham vi

Backlog nay chi danh cho phan:

- Luu tru bang chung
- Anchoring blockchain
- Kiem chung tinh bat bien

Khong bao gom viec sua model nhan dien bao luc.

## Uu tien P0

### P0.1 - Chot mo hinh bang chung

- Xac dinh bang chung la `snapshot`, `clip`, hay ca hai
- Chot ten field metadata
- Chot quy uoc dat ten file evidence
- Chot quy uoc tao hash

Ket qua mong doi:

- Co tai lieu schema ro rang de code theo

### P0.2 - Persist incident ra ngoai RAM

- Tao SQLite/PostgreSQL schema
- Luu `incident_id`, `source`, `detected_at`, `evidence_status`
- Khong phu thuoc vao `incident_log` trong RAM nua

Ket qua mong doi:

- Restart app van con lich su su kien

### P0.3 - Tao evidence artifact that

- Chup snapshot tai thoi diem su kien
- Hoac cat clip ngan quanh thoi diem phat hien
- Luu file vao thu muc `evidence/`

Ket qua mong doi:

- Moi incident co tep bang chung that de hash

### P0.4 - Hash file va metadata

- Tinh `sha256(file)`
- Tinh `sha256(metadata.json)`
- Luu vao DB

Ket qua mong doi:

- Hash khong con la hash tu `id|source|timestamp` don thuan

### P0.5 - Viet smart contract anchor hash

- Dinh nghia struct record
- Tao event `EvidenceAnchored`
- Ham anchor evidence

Ket qua mong doi:

- Co contract san sang deploy

### P0.6 - Tich hop transaction anchor

- Ket noi RPC
- Ky va gui transaction
- Nhan `tx_hash`, `block_number`
- Luu trang thai `submitted/confirmed/failed`

Ket qua mong doi:

- Evidence hash len duoc blockchain testnet

### P0.7 - Verify evidence

- Doi chieu file hien tai voi `file_sha256`
- Doi chieu metadata hien tai voi `metadata_sha256`
- Doi chieu hash tren DB voi hash on-chain

Ket qua mong doi:

- Co the chung minh tep chua bi sua

## Uu tien P1

### P1.1 - Nang cap dashboard blockchain

- Hien `tx_hash`
- Hien `anchor_status`
- Hien `verify_status`
- Hien link den transaction explorer

### P1.2 - Retry queue cho anchor that bai

- Danh dau `pending_retry`
- Cron/job retry
- Log loi RPC

### P1.3 - Tach service thanh module rieng

- `evidence_service`
- `anchor_service`
- `verify_service`
- `repository/db layer`

### P1.4 - Event audit log

- Ghi lai cac hanh dong:
  - tao incident
  - tao file
  - tao hash
  - gui tx
  - verify

## Uu tien P2

### P2.1 - Tich hop IPFS

- Pin file len IPFS
- Luu `cid`
- Dua `cid` vao metadata va anchor record

### P2.2 - Role va phan quyen

- Admin
- Viewer
- Auditor

### P2.3 - Pseudonymization thong tin nhay cam

- Ma hoa/ma gia danh camera, khu vuc, doi tuong

### P2.4 - Batch anchoring

- Gop nhieu incident vao 1 Merkle root
- Anchor root thay vi anchor tung hash

## Task ky thuat cu the

## Database

- Tao schema `incidents`
- Tao schema `evidence_artifacts`
- Tao schema `blockchain_anchors`
- Tao migration dau tien

## Backend Python

- Them service tao evidence package
- Them service hash file lon theo chunk
- Them service luu metadata JSON
- Them service submit blockchain tx
- Them service verify

## Smart contract

- Tao du an Hardhat/Foundry
- Viet contract anchor
- Viet unit test contract
- Viet script deploy testnet

## Dashboard/API

- Them API lich su incident
- Them API chi tiet incident
- Them API verify incident
- Them API trigger re-anchor neu can

## Logging va van hanh

- Log anchor fail
- Log verify fail
- Log storage fail
- Tach application log va audit log

## Tieu chi uu tien

Neu lam theo thu tu de nhanh co demo:

1. Persist incident
2. Tao snapshot/clip
3. Hash file that
4. Anchor blockchain
5. Verify
6. Dashboard

## Viec chua nen lam ngay

- Dua video len blockchain
- Lam contract qua phuc tap
- Toi uu gas qua som
- Xay permission system lon khi chua xong pipeline co ban

## Ket qua mong doi cuoi cung

Sau khi xong backlog P0, he thong phai tra loi duoc 4 cau hoi:

1. Su kien nao da xay ra?
2. Bang chung goc cua su kien nam o dau?
3. Hash nao dai dien cho bang chung do?
4. Transaction nao tren blockchain chung minh hash do da duoc ghi nhan?
