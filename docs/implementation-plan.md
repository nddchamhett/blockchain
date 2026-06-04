# Implementation Plan cho phan blockchain

## Nguyen tac

- Khong sua module nhan dien hanh vi bao luc.
- Chi bo sung pipeline bang chung va anchoring blockchain.
- Uu tien kha nang demo duoc, kiem chung duoc, de viet bao cao duoc.

## Muc tieu tong

Bien he thong tu:

- `fight detection + hash trong RAM`

thanh:

- `fight detection + evidence packaging + off-chain storage + blockchain anchor + verification`

## Giai doan 1: Chot pham vi va mo hinh du lieu

### Muc tieu

Xac dinh chinh xac ta se anchor cai gi, luu cai gi, hien thi cai gi.

### Dau ra

- Schema metadata incident
- Schema evidence artifact
- Schema blockchain anchor
- Lua chon blockchain/network
- Lua chon storage off-chain

### Quyết dinh de xuat

- Blockchain: EVM testnet (`Polygon Amoy` hoac `Sepolia`)
- Storage: local filesystem truoc, co the mo rong IPFS sau
- DB: SQLite neu muon nhanh, PostgreSQL neu muon bai ban

## Giai doan 2: Dong goi bang chung

### Muc tieu

Moi incident phai tao duoc bang chung that, khong chi la metadata trong RAM.

### Cong viec

- Chot dang bang chung:
  - snapshot
  - clip ngan 5-10 giay
- Tao thu muc luu bang chung theo ngay/thang
- Tao file metadata JSON cho moi incident
- Tinh `sha256` cho file bang chung
- Tinh `sha256` cho metadata JSON

### Dau ra

- Thu muc `evidence/`
- Cau truc metadata on dinh
- Hash duoc tinh tu file that

## Giai doan 3: Luu tru ben vung va truy van

### Muc tieu

Du lieu khong mat khi app restart va co the truy van lich su.

### Cong viec

- Tao DB `incidents`, `evidence_artifacts`, `blockchain_anchors`
- Ghi incident vao DB ngay khi detect
- Ghi artifact sau khi cat xong snapshot/clip
- Ghi trang thai anchor: `pending`, `submitted`, `confirmed`, `failed`

### Dau ra

- Du lieu su kien ton tai sau restart
- Co the truy van lai su kien cu

## Giai doan 4: Smart contract va blockchain anchoring

### Muc tieu

Co ban ghi on-chain chung minh bang chung ton tai va khong bi sua.

### Cong viec

- Viet smart contract anchor hash
- Viet script deploy len testnet
- Tao service Python goi transaction
- Luu `tx_hash`, `block_number`, `chain_id`
- Them co che retry khi RPC fail

### Dau ra

- Contract address
- Transaction anchor thanh cong
- Log su kien `EvidenceAnchored`

## Giai doan 5: Xac minh va doi soat

### Muc tieu

Cho phep kiem chung lai bang chung da luu.

### Cong viec

- Tao ham verify file hien tai voi `file_sha256`
- Tao ham verify metadata voi `metadata_sha256`
- Tao ham doi chieu DB voi transaction on-chain
- Hien thi ket qua verify tren dashboard

### Dau ra

- Nut hoac API verify
- Trang thai:
  - `verified`
  - `tampered`
  - `missing`
  - `anchor_mismatch`

## Giai doan 6: Nang cap dashboard

### Muc tieu

Dashboard khong chi hien "hash", ma hien duoc toan bo vong doi bang chung.

### Cong viec

- Them cot/field:
  - file bang chung
  - metadata hash
  - tx hash
  - anchor status
  - verify status
- Tach "Blockchain Evidence" thanh:
  - Evidence package
  - On-chain anchor
  - Verification

### Dau ra

- Dashboard dung voi ten de tai
- De demo va thuyet trinh

## Giai doan 7: Bao mat va van hanh

### Muc tieu

Tranh lam lo du lieu nhay cam va bi mat blockchain.

### Cong viec

- Luu private key trong `.env` va tach khoi log
- Han che thong tin hoc sinh trong metadata
- Co role cho verify/admin neu can
- Log loi RPC va retry queue

### Dau ra

- Pipeline an toan hon
- Giam rui ro demo loi

## Kien truc module de xuat

Khong sua `fight_module/`. Chi bo sung cac module moi:

- `evidence_service.py`
- `storage_service.py`
- `anchor_service.py`
- `verify_service.py`
- `db.py`

## API/ham can bo sung

- `create_evidence_package(incident, frame_or_clip)`
- `store_evidence_package(package)`
- `anchor_evidence(package)`
- `verify_evidence(incident_id)`
- `list_incidents()`
- `get_incident_detail(incident_id)`

## Milestone thuc te

### Milestone 1

- Incident duoc luu vao DB
- Co snapshot file
- Co `file_sha256`

### Milestone 2

- Contract deploy len testnet
- Incident duoc anchor len chain
- Dashboard hien `tx_hash`

### Milestone 3

- Verify lai file thanh cong
- Dashboard hien `verified/tampered`

## Dinh nghia hoan thanh

Phan blockchain duoc xem la hoan thanh cho prototype khi:

- Co file bang chung that
- Co hash dai dien cho file
- Co metadata duoc luu ben vung
- Co transaction ghi hash len blockchain
- Co chuc nang verify lai
- Co dashboard hien toan bo trang thai
