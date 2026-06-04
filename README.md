<div align="center">
  <h2>Khoa Công nghệ Thông tin - Đại học Đại Nam</h2>
  <h3>Nhận diện hành vi bạo lực học đường và lưu giữ bằng chứng bất biến bằng blockchain</h3>
  <img src="docs/assets/logo-banner.png" alt="DNU AIoT Lab - Khoa Công nghệ Thông tin - Đại học Đại Nam" width="850">
</div>

<br>

# Hệ thống nhận diện bạo lực và lưu giữ bằng chứng bất biến

Dự án xây dựng một hệ thống phát hiện hành vi bạo lực học đường từ camera, webcam, RTSP hoặc video tải lên. Khi phát hiện sự kiện bạo lực, hệ thống tự động tạo bằng chứng số, lưu metadata, tính mã băm SHA-256 và ghi dấu vết bằng chứng lên blockchain hoặc sổ cái cục bộ.

Chủ đề:

```text
Nhận diện hành vi bạo lực và lưu giữ bằng chứng bất biến bạo lực học đường sử dụng công nghệ blockchain
```

## Chức năng đã triển khai

### Nhận diện bạo lực

- Nhận đầu vào từ webcam, RTSP, video stream hoặc video upload.
- Sử dụng YOLOv8 Pose để tracking người và trích xuất keypoints.
- Sử dụng mô hình PyTorch để phân loại hành vi đánh nhau.
- Hiển thị dashboard theo thời gian thực.

### Lưu giữ và kiểm chứng bằng chứng

- Lưu thông tin incident vào SQLite.
- Tạo snapshot cho mỗi sự kiện bạo lực được phát hiện.
- Tạo metadata JSON cho từng incident.
- Tính `SHA-256` cho file snapshot.
- Tính `SHA-256` cho metadata JSON.
- Cho phép xác minh lại bằng chứng bằng cách so sánh hash đã lưu.

### Blockchain anchoring

- Hỗ trợ sổ cái cục bộ dạng append-only tại `data/anchor-ledger.jsonl`.
- Có smart contract Solidity tại `contracts/EvidenceRegistry.sol`.
- Hỗ trợ chế độ `evm-local` để demo transaction smart contract ngay trên máy local.
- Lưu thông tin file hash, metadata hash, anchor status, transaction hash hoặc ledger proof.

## Cấu trúc thư mục

- `main.py`: Flask app, dashboard, API và luồng xử lý nhận diện.
- `fight_module/`: module YOLO Pose và mô hình nhận diện đánh nhau.
- `persistence.py`: tầng lưu trữ SQLite.
- `evidence_service.py`: tạo snapshot, metadata và hash bằng chứng.
- `anchor_service.py`: ghi dấu bằng chứng lên local ledger hoặc EVM.
- `contracts/EvidenceRegistry.sol`: smart contract lưu hash bằng chứng.
- `contracts/`: ABI, bytecode và tài liệu contract.
- `scripts/`: script compile/deploy smart contract.
- `tests/`: test pipeline bằng chứng, upload, verify và EVM local.
- `docs/`: tài liệu phân tích, kế hoạch triển khai và nội dung poster.
- `docs/assets/logo-banner.png`: banner logo hiển thị ở đầu README.
- `Nhan_dien_hanh_vi_bao_luc-1671020078-Nguyen_Duc_Dai.pptx`: file PowerPoint logo/poster của dự án.

## Cài đặt

Yêu cầu Python `3.10.x`.

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Chạy hệ thống

```bash
python main.py
```

Mở trình duyệt tại:

```text
http://127.0.0.1:8000
```

## Dữ liệu sinh ra khi chạy

Các thư mục sau được tạo tự động trong quá trình chạy:

- `data/`: SQLite database, ledger cục bộ và dữ liệu upload.
- `evidence/`: snapshot và metadata JSON của các incident.

Các thư mục này là dữ liệu runtime nên không được đưa lên Git.

## Chế độ blockchain

Chế độ mặc định hiện tại:

```text
ANCHOR_MODE=evm-local
```

Chế độ này deploy smart contract `EvidenceRegistry` vào EVM test chain chạy ngay trong máy local, sau đó anchor bằng chứng bằng transaction thật. Không cần RPC bên ngoài, ví blockchain hoặc faucet.

Chế độ thay thế:

```text
ANCHOR_MODE=local-ledger
```

Chế độ này ghi hash vào sổ cái cục bộ dạng append-only, phù hợp để demo nhanh hoặc kiểm thử khi không cần EVM.

Nếu muốn chuyển sang testnet thật, cần deploy `contracts/EvidenceRegistry.sol`, cấu hình RPC, private key và contract address trong `.env`, sau đó đặt:

```text
ANCHOR_MODE=evm
ANCHOR_CHAIN_ID=<numeric chain id>
```

## API chính

- `GET /api/status`: trạng thái dashboard và danh sách incident gần nhất.
- `GET /api/incidents`: danh sách incident đã lưu.
- `GET /api/incidents/<id>`: chi tiết một incident.
- `GET /api/incidents/<id>/verify`: xác minh snapshot và metadata bằng hash.
- `GET /api/incidents/<id>/chain-of-custody`: xuất chuỗi lưu giữ bằng chứng.
- `GET /api/incidents/<id>/export`: xuất gói incident, hash, anchor và audit event dưới dạng JSON.
- `GET /api/self-check`: kiểm tra nhanh trạng thái DB, evidence root, ledger và Web3.

## Trang demo

- `GET /`: dashboard chính.
- `GET /archive`: kho lưu trữ các incident.
- `GET /incidents/<id>`: trang chain-of-custody của một incident.
- `GET /raw`: stream MJPEG của frame đang xử lý.
- `GET /nvidia`: kiểm tra thông tin GPU/CUDA nếu có.

Từ dashboard chính, người dùng có thể:

- Chạy nhận diện từ webcam.
- Chạy nhận diện từ RTSP hoặc URL stream.
- Upload video local và chạy nhận diện từ giao diện web.

## Tài liệu poster và logo

Dự án có sẵn tài liệu phục vụ poster/logo:

- `Nhan_dien_hanh_vi_bao_luc-1671020078-Nguyen_Duc_Dai.pptx`
- `docs/assets/logo-banner.png`
- `docs/poster-content.md`

## Biến môi trường

Các biến cấu hình chính:

- `YOLO_MODEL`
- `FIGHT_MODEL`
- `DEFAULT_CAMERA_INDEX`
- `DEFAULT_CAMERA_INPUT`
- `DATABASE_PATH`
- `EVIDENCE_ROOT`
- `ANCHOR_MODE`
- `ANCHOR_LEDGER_PATH`
- `ANCHOR_CHAIN_ID`
- `ANCHOR_EXPLORER_TX_BASE`
- `EVM_RPC_URL`
- `EVM_PRIVATE_KEY`
- `EVM_ACCOUNT_ADDRESS`
- `EVM_CONTRACT_ADDRESS`
- `EVIDENCE_REGISTRY_BYTECODE_PATH`

Các ngưỡng nhận diện có thể cấu hình:

- `THRESHOLD`
- `CONCLUSION_THRESHOLD`
- `FINAL_THRESHOLD`

## Compile và deploy smart contract

Compile contract từ source:

```bash
python scripts/compile_evidence_registry.py
```

Deploy contract:

```bash
python scripts/deploy_evidence_registry.py
```

Script deploy đọc các file và biến cấu hình:

- `contracts/EvidenceRegistry.abi.json`
- `contracts/EvidenceRegistry.bytecode.json`
- `EVIDENCE_REGISTRY_BYTECODE_PATH`
- `EVM_RPC_URL`
- `EVM_PRIVATE_KEY`
- `EVM_ACCOUNT_ADDRESS`
- `EVM_CONTRACT_ADDRESS`

## Quy trình xử lý bằng chứng

1. Camera hoặc video gửi frame vào hệ thống.
2. YOLOv8 Pose tracking người và trích xuất keypoints.
3. Classifier PyTorch đánh giá hành vi đánh nhau.
4. Khi phát hiện bạo lực, hệ thống tạo incident trong SQLite.
5. Evidence service lưu snapshot và metadata JSON.
6. Hệ thống tính `file_sha256` và `metadata_sha256`.
7. Anchor service ghi payload hash vào local ledger hoặc smart contract EVM.
8. Dashboard/API cho phép xem chi tiết, export JSON và xác minh lại bằng chứng.

## Kiểm thử

Chạy test:

```bash
python -m unittest
```

Các test hiện có kiểm tra:

- Pipeline tạo bằng chứng và xác minh local ledger.
- Trang incident và archive.
- Upload video hợp lệ/không hợp lệ.
- API self-check.
- Anchoring bằng EVM local nếu có bytecode contract.

## Ghi chú bảo mật

- Không commit `.env`, private key, database runtime, evidence snapshot hoặc video upload.
- Không đưa ảnh/video nhạy cảm trực tiếp lên blockchain.
- Blockchain chỉ nên lưu hash, timestamp và metadata tối thiểu.
- File bằng chứng gốc nên lưu off-chain, sau đó dùng hash để xác minh tính toàn vẹn.

## Tham khảo

- [IMSOO Fight Detection](https://github.com/imsoo/fight_detection)
- [YOLOv8 Pose Estimation](https://docs.ultralytics.com/tasks/pose/)
