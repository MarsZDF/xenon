"""Tests for audit mode and threat detection (v1.0.0)."""

import pytest

from xenon import (
    AuditLogger,
    SecurityMetrics,
    Threat,
    ThreatDetector,
    ThreatSeverity,
    ThreatType,
)


class TestThreatDetector:
    """Test suite for threat detection."""

    def test_detect_xxe_attempt(self):
        """Test detection of XXE attacks."""
        detector = ThreatDetector()

        # DOCTYPE with SYSTEM entity
        xml = '<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><root>&xxe;</root>'
        threats = detector.detect_threats(xml)

        assert len(threats) > 0
        xxe_threats = [t for t in threats if t.type == ThreatType.XXE_ATTEMPT]
        assert len(xxe_threats) == 1
        assert xxe_threats[0].severity == ThreatSeverity.CRITICAL
        assert "XXE" in xxe_threats[0].description or "entity" in xxe_threats[0].description.lower()

    def test_detect_xxe_public(self):
        """Test detection of PUBLIC entity declarations."""
        detector = ThreatDetector()

        xml = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0//EN" "http://example.com"><root/>'
        threats = detector.detect_threats(xml)

        xxe_threats = [t for t in threats if t.type == ThreatType.XXE_ATTEMPT]
        assert len(xxe_threats) == 1

    def test_detect_dangerous_pi_php(self):
        """Test detection of PHP processing instructions."""
        detector = ThreatDetector()

        xml = '<?php system("whoami"); ?><root>data</root>'
        threats = detector.detect_threats(xml)

        pi_threats = [t for t in threats if t.type == ThreatType.DANGEROUS_PI]
        assert len(pi_threats) == 1
        assert pi_threats[0].severity == ThreatSeverity.HIGH
        assert "PHP" in pi_threats[0].description

    def test_detect_dangerous_pi_asp(self):
        """Test detection of ASP processing instructions."""
        detector = ThreatDetector()

        xml = '<?asp Response.Write("hack") ?><root>data</root>'
        threats = detector.detect_threats(xml)

        pi_threats = [t for t in threats if t.type == ThreatType.DANGEROUS_PI]
        assert len(pi_threats) == 1

    def test_detect_dangerous_pi_jsp(self):
        """Test detection of JSP processing instructions."""
        detector = ThreatDetector()

        xml = '<?jsp out.println("hack"); ?><root>data</root>'
        threats = detector.detect_threats(xml)

        pi_threats = [t for t in threats if t.type == ThreatType.DANGEROUS_PI]
        assert len(pi_threats) == 1

    def test_safe_pi_not_detected(self):
        """Test that safe PIs are not flagged."""
        detector = ThreatDetector()

        xml = '<?xml version="1.0"?><?xml-stylesheet href="style.xsl"?><root/>'
        threats = detector.detect_threats(xml)

        pi_threats = [t for t in threats if t.type == ThreatType.DANGEROUS_PI]
        assert len(pi_threats) == 0

    def test_detect_xss_script_tag(self):
        """Test detection of XSS via script tags."""
        detector = ThreatDetector()

        xml = '<root><script>alert("XSS")</script></root>'
        threats = detector.detect_threats(xml)

        xss_threats = [t for t in threats if t.type == ThreatType.XSS_VECTOR]
        assert len(xss_threats) == 1
        assert xss_threats[0].severity == ThreatSeverity.HIGH

    def test_detect_xss_iframe(self):
        """Test detection of XSS via iframe tags."""
        detector = ThreatDetector()

        xml = '<root><iframe src="evil.com"></iframe></root>'
        threats = detector.detect_threats(xml)

        xss_threats = [t for t in threats if t.type == ThreatType.XSS_VECTOR]
        assert len(xss_threats) == 1

    def test_detect_xss_event_handler(self):
        """Test detection of XSS via event handlers."""
        detector = ThreatDetector()

        xml = '<root><img src="x" onerror="alert(1)"/></root>'
        threats = detector.detect_threats(xml)

        xss_threats = [t for t in threats if t.type == ThreatType.XSS_VECTOR]
        assert len(xss_threats) == 1

    def test_detect_entity_bomb(self):
        """Test detection of entity bombs (billion laughs attack)."""
        detector = ThreatDetector()

        xml = """<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol1 "&lol;&lol;&lol;">
]><root>&lol1;</root>"""
        threats = detector.detect_threats(xml)

        bomb_threats = [t for t in threats if t.type == ThreatType.ENTITY_BOMB]
        assert len(bomb_threats) == 1
        assert bomb_threats[0].severity == ThreatSeverity.HIGH

    def test_detect_deep_nesting(self):
        """Test detection of deeply nested XML."""
        detector = ThreatDetector()

        # Create XML with many tags
        xml = "".join([f"<level{i}>" for i in range(1500)]) + "content"
        threats = detector.detect_threats(xml)

        nesting_threats = [t for t in threats if t.type == ThreatType.DEEP_NESTING]
        assert len(nesting_threats) == 1
        assert nesting_threats[0].severity == ThreatSeverity.MEDIUM

    def test_multiple_threats(self):
        """Test detection of multiple threats in single XML."""
        detector = ThreatDetector()

        xml = """<?php hack ?>
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<root>
    <script>alert('XSS')</script>
</root>"""
        threats = detector.detect_threats(xml)

        # Should detect XXE, dangerous PI, and XSS
        assert len(threats) >= 3

        types = {t.type for t in threats}
        assert ThreatType.XXE_ATTEMPT in types
        assert ThreatType.DANGEROUS_PI in types
        assert ThreatType.XSS_VECTOR in types

    def test_clean_xml_no_threats(self):
        """Test that clean XML has no detected threats."""
        detector = ThreatDetector()

        xml = "<root><item>clean data</item></root>"
        threats = detector.detect_threats(xml)

        assert len(threats) == 0

    def test_threat_to_dict(self):
        """Test threat serialization to dict."""
        threat = Threat(
            type=ThreatType.XXE_ATTEMPT,
            severity=ThreatSeverity.CRITICAL,
            description="Test threat",
            location="line 1",
            context="<test>",
        )

        data = threat.to_dict()

        assert data["type"] == "xxe_attempt"
        assert data["severity"] == "critical"
        assert data["description"] == "Test threat"
        assert data["location"] == "line 1"
        assert data["context"] == "<test>"
        assert "timestamp" in data


class TestAuditLogger:
    """Test suite for audit logging."""

    def test_log_repair_operation(self):
        """Test logging a repair operation."""
        logger = AuditLogger()

        logger.log_repair_operation(
            xml_input="<root>test",
            xml_output="<root>test</root>",
            trust_level="untrusted",
            threats=[],
            actions_taken=["closed_tags"],
            processing_time_ms=1.5,
        )

        entries = logger.get_entries()
        assert len(entries) == 1

        entry = entries[0]
        assert entry.trust_level == "untrusted"
        assert entry.input_length == len("<root>test")
        assert entry.output_length == len("<root>test</root>")
        assert "closed_tags" in entry.actions_taken
        assert entry.processing_time_ms == 1.5

    def test_log_multiple_operations(self):
        """Test logging multiple operations."""
        logger = AuditLogger()

        for i in range(5):
            logger.log_repair_operation(
                xml_input=f"<root>test{i}",
                xml_output=f"<root>test{i}</root>",
                trust_level="untrusted",
                threats=[],
                actions_taken=[],
            )

        entries = logger.get_entries()
        assert len(entries) == 5

    def test_log_with_threats(self):
        """Test logging with detected threats."""
        logger = AuditLogger()

        threat = Threat(
            type=ThreatType.XXE_ATTEMPT,
            severity=ThreatSeverity.CRITICAL,
            description="XXE detected",
        )

        logger.log_repair_operation(
            xml_input="<!DOCTYPE foo><root/>",
            xml_output="<root/>",
            trust_level="untrusted",
            threats=[threat],
            actions_taken=["stripped_entities"],
        )

        entries = logger.get_entries()
        assert len(entries) == 1
        assert "xxe_attempt" in entries[0].threats_detected
        assert "stripped_entities" in entries[0].actions_taken

    def test_disabled_logger(self):
        """Test that disabled logger doesn't record entries."""
        logger = AuditLogger(enabled=False)

        logger.log_repair_operation(
            xml_input="<root>",
            xml_output="<root/>",
            trust_level="trusted",
            threats=[],
            actions_taken=[],
        )

        entries = logger.get_entries()
        assert len(entries) == 0

    def test_get_entries_with_limit(self):
        """Test getting limited number of entries."""
        logger = AuditLogger()

        for i in range(10):
            logger.log_repair_operation(
                xml_input=f"<root{i}>",
                xml_output=f"<root{i}/>",
                trust_level="trusted",
                threats=[],
                actions_taken=[],
            )

        # Get last 3 entries
        entries = logger.get_entries(limit=3)
        assert len(entries) == 3

    def test_clear_entries(self):
        """Test clearing audit log."""
        logger = AuditLogger()

        logger.log_repair_operation(
            xml_input="<root>",
            xml_output="<root/>",
            trust_level="trusted",
            threats=[],
            actions_taken=[],
        )

        assert len(logger.get_entries()) == 1

        logger.clear()
        assert len(logger.get_entries()) == 0

    def test_to_json(self):
        """Test JSON export of audit log."""
        logger = AuditLogger()

        logger.log_repair_operation(
            xml_input="<root>",
            xml_output="<root/>",
            trust_level="trusted",
            threats=[],
            actions_taken=["test"],
        )

        json_data = logger.to_json()
        assert isinstance(json_data, list)
        assert len(json_data) == 1
        assert json_data[0]["trust_level"] == "trusted"
        assert "timestamp" in json_data[0]


class TestSecurityMetrics:
    """Test suite for security metrics."""

    def test_increment_metric(self):
        """Test incrementing a metric."""
        metrics = SecurityMetrics()

        metrics.increment("xxe_attempts_detected")
        assert metrics.counters["xxe_attempts_detected"] == 1

        metrics.increment("xxe_attempts_detected", 5)
        assert metrics.counters["xxe_attempts_detected"] == 6

    def test_record_threats(self):
        """Test recording threats in metrics."""
        metrics = SecurityMetrics()

        threats = [
            Threat(ThreatType.XXE_ATTEMPT, ThreatSeverity.CRITICAL, "XXE"),
            Threat(ThreatType.DANGEROUS_PI, ThreatSeverity.HIGH, "PHP"),
            Threat(ThreatType.XSS_VECTOR, ThreatSeverity.HIGH, "XSS"),
        ]

        metrics.record_threats(threats)

        assert metrics.counters["total_threats_detected"] == 3
        assert metrics.counters["xxe_attempts_detected"] == 1
        assert metrics.counters["dangerous_pis_detected"] == 1
        assert metrics.counters["xss_vectors_detected"] == 1

    def test_record_actions(self):
        """Test recording security actions."""
        metrics = SecurityMetrics()

        actions = [
            "Stripped external entity declarations",
            "Removed dangerous PHP processing instruction",
            "Stripped script tag for XSS prevention",
        ]

        metrics.record_actions(actions)

        assert metrics.counters["xxe_attempts_blocked"] == 1
        assert metrics.counters["dangerous_pis_stripped"] == 1
        assert metrics.counters["xss_vectors_blocked"] == 1

    def test_get_stats(self):
        """Test getting statistics."""
        metrics = SecurityMetrics()

        metrics.increment("untrusted_inputs_processed", 10)
        metrics.increment("total_threats_detected", 5)

        stats = metrics.get_stats()

        assert "counters" in stats
        assert stats["counters"]["untrusted_inputs_processed"] == 10
        assert stats["counters"]["total_threats_detected"] == 5
        assert "uptime_seconds" in stats
        assert "last_updated" in stats

    def test_reset_metrics(self):
        """Test resetting metrics."""
        metrics = SecurityMetrics()

        metrics.increment("xxe_attempts_detected", 10)
        metrics.increment("dangerous_pis_detected", 5)

        assert metrics.counters["xxe_attempts_detected"] == 10

        metrics.reset()

        assert metrics.counters["xxe_attempts_detected"] == 0
        assert metrics.counters["dangerous_pis_detected"] == 0

    def test_all_metrics_initialized(self):
        """Test that all expected metrics are initialized."""
        metrics = SecurityMetrics()

        expected_metrics = [
            "xxe_attempts_detected",
            "xxe_attempts_blocked",
            "dangerous_pis_detected",
            "dangerous_pis_stripped",
            "xss_vectors_detected",
            "xss_vectors_blocked",
            "entity_bombs_detected",
            "deep_nesting_detected",
            "untrusted_inputs_processed",
            "internal_inputs_processed",
            "trusted_inputs_processed",
            "total_threats_detected",
        ]

        for metric in expected_metrics:
            assert metric in metrics.counters
            assert metrics.counters[metric] == 0


class TestAuditIntegration:
    """Test audit mode integration."""

    def test_audit_logger_and_metrics_together(self):
        """Test using logger and metrics together."""
        logger = AuditLogger()
        metrics = SecurityMetrics()
        detector = ThreatDetector()

        # Simulate processing untrusted XML
        xml = "<?php hack ?><root><script>XSS</script></root>"
        threats = detector.detect_threats(xml)

        # Record in metrics
        metrics.increment("untrusted_inputs_processed")
        metrics.record_threats(threats)

        # Record in audit log
        actions = ["Stripped PHP PI", "Stripped script tag"]
        metrics.record_actions(actions)

        logger.log_repair_operation(
            xml_input=xml,
            xml_output="<root>XSS</root>",
            trust_level="untrusted",
            threats=threats,
            actions_taken=actions,
        )

        # Verify metrics
        stats = metrics.get_stats()
        assert stats["counters"]["untrusted_inputs_processed"] == 1
        assert stats["counters"]["total_threats_detected"] >= 2
        assert stats["counters"]["dangerous_pis_stripped"] == 1

        # Verify audit log
        entries = logger.get_entries()
        assert len(entries) == 1
        assert len(entries[0].threats_detected) >= 2
        assert len(entries[0].actions_taken) == 2

    def test_threat_severity_levels(self):
        """Test all threat severity levels."""
        critical = Threat(ThreatType.XXE_ATTEMPT, ThreatSeverity.CRITICAL, "Critical threat")
        high = Threat(ThreatType.DANGEROUS_PI, ThreatSeverity.HIGH, "High threat")
        medium = Threat(ThreatType.DEEP_NESTING, ThreatSeverity.MEDIUM, "Medium threat")
        low = Threat(ThreatType.MALFORMED_INPUT, ThreatSeverity.LOW, "Low threat")

        assert critical.severity == ThreatSeverity.CRITICAL
        assert high.severity == ThreatSeverity.HIGH
        assert medium.severity == ThreatSeverity.MEDIUM
        assert low.severity == ThreatSeverity.LOW
