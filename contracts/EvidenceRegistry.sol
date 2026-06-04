// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract EvidenceRegistry {
    struct EvidenceRecord {
        uint256 incidentId;
        bytes32 fileHash;
        bytes32 metadataHash;
        string storageUri;
        uint256 detectedAt;
        uint256 anchoredAt;
        address submittedBy;
    }

    mapping(uint256 => EvidenceRecord) private records;

    event EvidenceAnchored(
        uint256 indexed incidentId,
        bytes32 indexed fileHash,
        bytes32 indexed metadataHash,
        string storageUri,
        uint256 detectedAt,
        uint256 anchoredAt,
        address submittedBy
    );

    function anchorEvidence(
        uint256 incidentId,
        bytes32 fileHash,
        bytes32 metadataHash,
        string calldata storageUri,
        uint256 detectedAt
    ) external {
        require(records[incidentId].incidentId == 0, "Incident already anchored");

        uint256 anchoredAt = block.timestamp;
        records[incidentId] = EvidenceRecord({
            incidentId: incidentId,
            fileHash: fileHash,
            metadataHash: metadataHash,
            storageUri: storageUri,
            detectedAt: detectedAt,
            anchoredAt: anchoredAt,
            submittedBy: msg.sender
        });

        emit EvidenceAnchored(
            incidentId,
            fileHash,
            metadataHash,
            storageUri,
            detectedAt,
            anchoredAt,
            msg.sender
        );
    }

    function getEvidence(uint256 incidentId) external view returns (EvidenceRecord memory) {
        require(records[incidentId].incidentId != 0, "Incident not anchored");
        return records[incidentId];
    }
}
