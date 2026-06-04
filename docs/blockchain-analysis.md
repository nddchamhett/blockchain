# Phan tich de tai: Luu giu bang chung bat bien bao luc hoc duong bang blockchain

## 1. Muc tieu tai lieu

Tai lieu nay chi phan tich ve phan `luu giu bang chung bat bien` cua de tai:

`Nhan dien hanh vi bao luc va luu giu bang chung bat bien bao luc hoc duong su dung cong nghe blockchain`

Phan nhan dien hanh vi bao luc hien da co trong he thong va **khong nam trong pham vi sua doi** cua tai lieu nay.

## 2. Trang thai hien tai cua he thong

### 2.1 Thanh phan da co

He thong hien tai da co:

- Web dashboard Flask de khoi dong stream webcam/RTSP/video.
- Mo hinh nhan dien hanh vi danh nhau dua tren YOLOv8 Pose + classifier.
- Co che tao `incident` khi phat hien bao luc.
- Co che tao `evidence_hash` bang `SHA-256`.
- Giao dien hien thi danh sach su kien va hash bang chung.

### 2.2 Nhung gi code dang lam o phan "blockchain"

Theo code hien tai:

- `main.py:429` tao `incident` gom `id`, `source`, `detected_at`, `evidence_hash`.
- `main.py:435-436` tao hash tu chuoi `incident_counter|source|timestamp`.
- `main.py:499-508` tra ve danh sach incident qua `/api/status`.
- `main.py:338-349` giao dien goi day la "Blockchain Evidence", nhung thuc te moi dung o muc `blockchain-ready`.

### 2.3 Khoang cach giua hien tai va de tai

He thong hien tai **chua dat muc blockchain** theo dung nghia hoc thuat va ky thuat, vi:

- Chua co luu tru ben vung bang chung ngoai RAM.
- Chua co file/chung cu goc duoc dong goi.
- Chua co chu ky so hay checksum day du cho tep anh/video.
- Chua co smart contract.
- Chua co transaction hash on-chain.
- Chua co co che doi soat tinh toan ven sau khi ghi.
- Chua co quy trinh truy vet chain-of-custody.

Ket luan: phan "nhan dien" da co, phan "luu giu bang chung bat bien bang blockchain" moi chi o muc mo phong hash noi bo.

## 3. Yeu cau nghiep vu cho phan blockchain

### 3.1 Bai toan can giai

Khi he thong phat hien hanh vi bao luc hoc duong, can:

1. Tao bang chung so co the kiem chung.
2. Luu metadata cua bang chung de tranh sua doi.
3. Ghi dau vet bat bien len blockchain.
4. Cho phep xac minh sau nay rang:
   - Su kien da ton tai tai mot thoi diem xac dinh.
   - Noi dung bang chung khong bi sua sau khi ghi nhan.
   - Ban ghi tren he thong khop voi ban ghi da anchor len blockchain.

### 3.2 Yeu cau dau ra

Mot su kien bao luc sau cung nen co:

- `incident_id`
- `detected_at`
- `camera_id` hoac `source`
- `snapshot_path` hoac `clip_path`
- `evidence_hash`
- `metadata_hash`
- `storage_uri`
- `blockchain_tx_hash`
- `block_number`
- `anchored_at`
- `verifier_status`

## 4. Dinh nghia "bang chung bat bien"

Trong de tai nay, "bat bien" khong co nghia la video khong bao gio bi xoa o moi noi. No co nghia thuc te hon:

- Bat ky thay doi nao len bang chung goc deu lam thay doi hash.
- Dau vet hash da duoc ghi len mot he thong kho chinh sua hon co so du lieu thong thuong.
- Co the doi chieu lai bang chung hien tai voi hash da ghi nhan truoc do.

Do vay, blockchain khong nen chua video truc tiep. Blockchain nen chua:

- Hash cua bang chung.
- Hash cua metadata.
- Timestamp anchor.
- Nguoi/ung dung thuc hien anchor.
- Trang thai hop le cua bang chung.

## 5. Kien truc de xuat

## 5.1 Nguyen tac kien truc

- Khong dua video thang len blockchain vi chi phi cao.
- Luu bang chung goc off-chain.
- Ghi hash va metadata toi gian len on-chain.
- Tach rieng `detection pipeline` va `evidence pipeline`.
- Dam bao neu blockchain tam thoi loi thi phan nhan dien van tiep tuc chay.

## 5.2 Kien truc 4 lop

### Lop 1: Detection

Giu nguyen nhu hien tai:

- Webcam / RTSP / video input
- YOLOv8 pose estimation
- Fight classifier
- Tao su kien `incident`

### Lop 2: Evidence packaging

Khi co incident:

- Cat 1 frame snapshot hoac clip ngan 5-10 giay xung quanh su kien.
- Tao metadata JSON.
- Tinh hash cho:
  - file bang chung
  - metadata
  - goi bang chung tong hop

### Lop 3: Off-chain storage

Lua chon luu tru:

- Local filesystem
- NAS/server noi bo
- IPFS
- MinIO / S3-compatible storage

De tai hoc thuat thuong hop ly nhat voi:

- Luu file bang chung tren local hoac object storage
- Neu muon "de chat blockchain" hon thi them IPFS CID

### Lop 4: On-chain anchoring

Smart contract chi luu:

- `incident_id`
- `evidence_hash`
- `metadata_hash`
- `storage_uri` hoac `ipfs_cid`
- `detected_at`
- `anchored_at`
- `submitted_by`

## 6. Luong du lieu de xuat

1. Camera gui frame vao detector.
2. Module nhan dien phat hien bao luc.
3. He thong tao `incident`.
4. Evidence worker cat `snapshot` hoac `clip`.
5. He thong tao `metadata.json`.
6. Tinh `sha256` cho file va metadata.
7. Luu bang chung goc vao kho off-chain.
8. Gui transaction len blockchain de anchor hash.
9. Nhan `tx_hash`, `block_number`.
10. Cap nhat trang thai xac minh tren dashboard.

## 7. Du lieu bang chung can co

## 7.1 Toi thieu

- `incident_id`
- `source`
- `detected_at_utc`
- `evidence_type` (`snapshot` / `clip`)
- `file_name`
- `file_sha256`
- `metadata_sha256`
- `storage_uri`
- `tx_hash`

## 7.2 Nen co them

- `model_version`
- `fight_threshold`
- `conclusion_threshold`
- `final_threshold`
- `app_version`
- `host_name`
- `camera_label`
- `frame_index` hoac `event_window`
- `created_by_service`

## 7.3 Khong nen dua len chain

- Video goc dung luong lon
- Hinh anh co do phan giai cao
- Thong tin nhay cam cua hoc sinh o dang plaintext neu khong can thiet
- Cac token bi mat, private key, raw API secret

## 8. Lua chon nen tang blockchain

## 8.1 Tieu chi lua chon

- Phi giao dich thap
- De demo va de bao ve de tai
- Co testnet on dinh
- De viet smart contract
- Cong cu pho bien

## 8.2 Lua chon kha thi

### Option A: Ethereum / Sepolia

Uu diem:

- Pho bien, de giai thich trong bao cao
- Ecosystem manh
- Solidity, Hardhat/Foundry de dung

Nhuoc diem:

- Phi co the khong re neu len mainnet
- Toc do khong phai luc nao cung nhanh

### Option B: Polygon

Uu diem:

- Phi thap hon
- Van dung EVM
- De chuyen tu local sang testnet/mainnet

Nhuoc diem:

- Can giai thich them ve he sinh thai neu hoi dong quen Ethereum hon

### Option C: Hyperledger Fabric

Uu diem:

- Hop bai toan noi bo, permissioned
- Quan tri truy cap tot

Nhuoc diem:

- Kho setup hon
- Vuot muc can thiet neu de tai can mot prototype nhanh

### Kien nghi

Cho do an/luan van cap sinh vien, phuong an can bang nhat thuong la:

- `Polygon Amoy` hoac `Sepolia` cho demo
- Smart contract don gian chi anchor hash
- Off-chain storage local/IPFS

## 9. De xuat thiet ke smart contract

## 9.1 Muc tieu contract

Contract khong xu ly AI. Contract chi:

- Nhan metadata hash/evidence hash
- Luu ban ghi anchoring
- Phat event de truy vet
- Cung cap ham kiem tra incident da ton tai chua

## 9.2 Cau truc du lieu goi y

```solidity
struct EvidenceRecord {
    uint256 incidentId;
    bytes32 evidenceHash;
    bytes32 metadataHash;
    string storageUri;
    uint256 detectedAt;
    uint256 anchoredAt;
    address submittedBy;
}
```

## 9.3 Chuc nang toi thieu

- `anchorEvidence(...)`
- `getEvidenceByIncidentId(...)`
- `isEvidenceAnchored(...)`
- Event `EvidenceAnchored`

## 9.4 Rang buoc nghiep vu

- Moi `incident_id` chi nen anchor 1 lan, hoac co version neu anchor lai.
- Neu cho phep anchor lai, phai co `revision` va lich su.
- Contract khong luu thong tin nhay cam khong can thiet.

## 10. De xuat co so du lieu off-chain

Mac du blockchain luu dau vet bat bien, he thong van can 1 CSDL off-chain de truy van nhanh:

- SQLite/PostgreSQL cho metadata
- Thu muc `evidence/` cho file

Bang de xuat:

### `incidents`

- incident_id
- source
- detected_at
- created_at
- detection_status

### `evidence_artifacts`

- artifact_id
- incident_id
- artifact_type
- file_path
- file_sha256
- file_size
- mime_type

### `blockchain_anchors`

- anchor_id
- incident_id
- metadata_sha256
- tx_hash
- block_number
- chain_id
- anchor_status
- anchored_at

## 11. Chuoi bao quan bang chung (chain of custody)

Day la phan rat quan trong neu de tai muon co tinh thuc tien.

Can ghi lai:

- Ai/ung dung nao tao bang chung
- Thoi diem tao
- Luu o dau
- Hash nao dai dien cho tep
- Ai gui transaction
- Transaction nao da ghi hash len chain
- Lan kiem chung gan nhat

Neu khong co chain-of-custody, phan blockchain se de bi hoi ngược:

"Hash thi co roi, nhung ai chung minh duoc file nay la file goc?"

## 12. Bao mat va quyen rieng tu

De tai lien quan den hoc sinh, nen can dac biet luu y:

- Khong dua mat hoc sinh, ho ten, lop hoc len blockchain.
- Neu can hien thi, nen pseudonymize hoac ma hoa thong tin nhay cam.
- Vi tri luu private key phai tach khoi source code.
- Tai khoan anchor on-chain nen dung vi dich vu rieng.
- Neu co API xac minh, can co phan quyen truy cap.

## 13. Rui ro ky thuat

### 13.1 Rui ro hien tai

- Incident dang chi nam trong RAM, restart la mat.
- Hash hien tai duoc tao tu `id|source|timestamp`, chua hash tep bang chung that.
- Chua co file snapshot/clip nen hash hien tai chua dai dien truc tiep cho chung cu media.
- Chua co retry queue khi blockchain loi.
- Chua co doi soat hash sau khi luu.

### 13.2 Rui ro khi tich hop blockchain

- Gas fee va do tre giao dich
- Ket noi RPC khong on dinh
- Mat private key
- Ghi nham du lieu nhay cam len chain va khong xoa duoc
- Drift giua du lieu off-chain va on-chain neu transaction fail giua chung

## 14. Tieu chi danh gia thanh cong

He thong dat yeu cau de tai neu chung minh duoc:

1. Phat hien su kien bao luc.
2. Tao duoc goi bang chung so.
3. Tinh duoc hash cho bang chung.
4. Luu duoc bang chung vao kho off-chain.
5. Anchor duoc hash len blockchain.
6. Truy xuat lai duoc `tx_hash`, `block_number`.
7. Kiem chung lai duoc file hien tai trung hash da anchor.

## 15. Pham vi de xuat cho ban prototype

De tranh over-engineering, prototype nen dung muc:

- Giu nguyen module detection.
- Khi co incident thi chup 1 snapshot hoac cat 1 clip ngan.
- Luu metadata vao local DB.
- Tinh `sha256(file)` va `sha256(metadata.json)`.
- Anchor len EVM testnet bang smart contract don gian.
- Hien thi `tx_hash`, `anchor_status`, `verify_result` tren dashboard.

## 16. Ket luan phan tich

Phan nhan dien bao luc cua de tai da co nen tang. Tuy nhien, de tai chi that su dung "cong nghe blockchain" khi bo sung day du 3 lop sau:

- Dong goi bang chung so
- Luu tru off-chain co kiem chung
- Anchoring hash len blockchain

Noi dung uu tien nhat khong phai la dua video len chain, ma la:

- Xac dinh `bang chung nao can duoc hash`
- `hash duoc luu o dau`
- `lam sao kiem chung lai duoc`

Do do, huong phat trien dung cho de tai la bien phan "Blockchain Evidence" hien tai tu mot dashboard hash noi bo thanh mot quy trinh `evidence integrity + on-chain anchoring + post-event verification`.
