"""Tests for AuditLogger and ThreatDetector."""

import time
from datetime import datetime

from xenon import TrustLevel, repair_xml_safe
from xenon.audit import AuditLogger, Threat, ThreatDetector, ThreatSeverity, ThreatType


class TestThreatDetector:
    """Test detection of various security threats."""

    def test_detect_xxe(self):
        detector = ThreatDetector()
        xml = '<!DOCTYPE foo [ <!ENTITY xxe SYSTEM "file:///etc/passwd"> ]>'
        threats = detector.detect_threats(xml)

        assert len(threats) == 1
        assert threats[0].type == ThreatType.XXE_ATTEMPT
        assert threats[0].severity == ThreatSeverity.CRITICAL

    def test_detect_dangerous_pi(self):
        detector = ThreatDetector()
        xml = '<?php system("ls"); ?>'
        threats = detector.detect_threats(xml)

        assert len(threats) == 1
        assert threats[0].type == ThreatType.DANGEROUS_PI
        assert threats[0].severity == ThreatSeverity.HIGH

    def test_detect_xss_vector(self):
        detector = ThreatDetector()
        xml = "<script>alert(1)</script>"
        threats = detector.detect_threats(xml)

        assert len(threats) == 1
        assert threats[0].type == ThreatType.XSS_VECTOR
        assert threats[0].severity == ThreatSeverity.HIGH

    def test_detect_deep_nesting(self):
        detector = ThreatDetector()
        xml = "<root>" + "<a>" * 1001 + "</a>" * 1001 + "</root>"
        threats = detector.detect_threats(xml)

        assert any(t.type == ThreatType.DEEP_NESTING for t in threats)


class TestAuditLogger:
    """Test audit logging functionality."""

    def test_log_repair_operation(self):
        logger = AuditLogger()

        logger.log_repair_operation(
            xml_input="<in>",
            xml_output="<out>",
            trust_level="untrusted",
            threats=[],
            actions_taken=["fixed stuff"],
            processing_time_ms=10.5,
            security_flags={"flag": True},
        )

        entries = logger.get_entries()
        assert len(entries) == 1
        assert entries[0].trust_level == "untrusted"
        assert entries[0].actions_taken == ["fixed stuff"]

    def test_integration_with_repair_xml_safe(self):
        """Test that repair_xml_safe correctly populates the audit log."""
        logger = AuditLogger()

        # Input with threats but also valid structure so strict validation passes
        malicious_xml = "<root><?php hack ?> <script>alert(1)</script></root>"

        repair_xml_safe(malicious_xml, trust=TrustLevel.UNTRUSTED, audit_logger=logger)

        entries = logger.get_entries()
        assert len(entries) == 1

        entry = entries[0]
        # Check threats were detected
        assert "DANGEROUS_PI" in entry.threats_detected or "dangerous_pi" in entry.threats_detected
        # Check actions were taken
        assert any("DANGEROUS_PI_STRIPPED" in a for a in entry.actions_taken)
        assert any("DANGEROUS_TAG_STRIPPED" in a for a in entry.actions_taken)

        # Check metadata
        assert entry.input_length == len(malicious_xml)
        assert entry.security_flags["strip_pis"] is True

    def test_audit_disabled(self):
        logger = AuditLogger(enabled=False)
        logger.log_repair_operation("in", "out", "trust", [], [])
        assert len(logger.get_entries()) == 0
