"""
Audit and threat detection for Xenon XML repair.

This module provides security auditing, threat detection, and metrics
collection for tracking security-relevant operations.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ThreatType(Enum):
    """Types of security threats that can be detected."""

    XXE_ATTEMPT = "xxe_attempt"
    DANGEROUS_PI = "dangerous_pi"
    XSS_VECTOR = "xss_vector"
    ENTITY_BOMB = "entity_bomb"
    DEEP_NESTING = "deep_nesting"
    MALFORMED_INPUT = "malformed_input"


class ThreatSeverity(Enum):
    """Severity levels for detected threats."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Threat:
    """Represents a detected security threat."""

    type: ThreatType
    severity: ThreatSeverity
    description: str
    location: Optional[str] = None
    context: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert threat to dictionary for logging."""
        return {
            "type": self.type.value,
            "severity": self.severity.value,
            "description": self.description,
            "location": self.location,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
        }


class ThreatDetector:
    """Detects and classifies security threats in XML input."""

    # Patterns for threat detection
    XXE_PATTERN = re.compile(r"<!(?:DOCTYPE|ENTITY)[^>]*(?:SYSTEM|PUBLIC)", re.IGNORECASE)
    DANGEROUS_PI_PATTERN = re.compile(r"<\?(?:php|asp|jsp)", re.IGNORECASE)
    XSS_TAG_PATTERN = re.compile(r"<(?:script|iframe|object|embed|form|input)[\s>]", re.IGNORECASE)
    XSS_EVENT_PATTERN = re.compile(r"\bon(?:load|error|click|mouse\w+)\s*=", re.IGNORECASE)
    ENTITY_EXPANSION_PATTERN = re.compile(r"<!ENTITY\s+\w+\s+[\"'][^\"']*&\w+;", re.IGNORECASE)

    def detect_threats(self, xml: str) -> List[Threat]:
        """
        Analyze XML input and detect security threats.

        Args:
            xml: XML string to analyze

        Returns:
            List of detected threats
        """
        threats = []

        # Check for XXE attempts
        if self.XXE_PATTERN.search(xml):
            match = self.XXE_PATTERN.search(xml)
            threats.append(
                Threat(
                    type=ThreatType.XXE_ATTEMPT,
                    severity=ThreatSeverity.CRITICAL,
                    description="External entity declaration detected (XXE vulnerability)",
                    location=f"Position {match.start()}" if match else None,
                    context=self._get_context(xml, match.start()) if match else None,
                )
            )

        # Check for dangerous processing instructions
        if self.DANGEROUS_PI_PATTERN.search(xml):
            match = self.DANGEROUS_PI_PATTERN.search(xml)
            pi_type = match.group(0)[2:5].upper() if match else "unknown"
            threats.append(
                Threat(
                    type=ThreatType.DANGEROUS_PI,
                    severity=ThreatSeverity.HIGH,
                    description=f"Dangerous processing instruction detected ({pi_type})",
                    location=f"Position {match.start()}" if match else None,
                    context=self._get_context(xml, match.start()) if match else None,
                )
            )

        # Check for XSS vectors
        if self.XSS_TAG_PATTERN.search(xml) or self.XSS_EVENT_PATTERN.search(xml):
            threats.append(
                Threat(
                    type=ThreatType.XSS_VECTOR,
                    severity=ThreatSeverity.HIGH,
                    description="Potential XSS payload detected (dangerous tags or event handlers)",
                    location=None,
                    context=None,
                )
            )

        # Check for entity bombs (entity expansion attacks)
        if self.ENTITY_EXPANSION_PATTERN.search(xml):
            threats.append(
                Threat(
                    type=ThreatType.ENTITY_BOMB,
                    severity=ThreatSeverity.HIGH,
                    description="Potential entity bomb detected (recursive entity definitions)",
                    location=None,
                    context=None,
                )
            )

        # Check for deep nesting (simple heuristic)
        if xml.count("<") > 1000:
            threats.append(
                Threat(
                    type=ThreatType.DEEP_NESTING,
                    severity=ThreatSeverity.MEDIUM,
                    description=f"Deeply nested XML detected ({xml.count('<')} tags)",
                    location=None,
                    context=None,
                )
            )

        return threats

    def _get_context(self, text: str, position: int, max_length: int = 50) -> str:
        """Extract context around a position."""
        start = max(0, position - max_length // 2)
        end = min(len(text), position + max_length // 2)
        snippet = text[start:end]

        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."

        return snippet.strip()


@dataclass
class AuditEntry:
    """Represents a single audit log entry."""

    timestamp: datetime
    trust_level: str
    input_length: int
    output_length: int
    threats_detected: List[str]
    actions_taken: List[str]
    security_flags: Dict[str, bool]
    processing_time_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert audit entry to dictionary for logging."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "trust_level": self.trust_level,
            "input_length": self.input_length,
            "output_length": self.output_length,
            "threats_detected": self.threats_detected,
            "actions_taken": self.actions_taken,
            "security_flags": self.security_flags,
            "processing_time_ms": self.processing_time_ms,
        }


class AuditLogger:
    """Logs security-relevant operations for compliance and debugging."""

    def __init__(self, enabled: bool = True):
        """
        Initialize audit logger.

        Args:
            enabled: Whether logging is enabled
        """
        self.enabled = enabled
        self.entries: List[AuditEntry] = []

    def log_repair_operation(
        self,
        xml_input: str,
        xml_output: str,
        trust_level: str,
        threats: List[Threat],
        actions_taken: List[str],
        processing_time_ms: Optional[float] = None,
        security_flags: Optional[Dict[str, bool]] = None,
    ) -> None:
        """
        Log a repair operation with security context.

        Args:
            xml_input: Original XML input
            xml_output: Repaired XML output
            trust_level: Trust level used
            threats: Detected threats
            actions_taken: Actions taken during repair
            processing_time_ms: Processing time in milliseconds
            security_flags: Security flags that were active
        """
        if not self.enabled:
            return

        entry = AuditEntry(
            timestamp=datetime.utcnow(),
            trust_level=trust_level,
            input_length=len(xml_input),
            output_length=len(xml_output),
            threats_detected=[t.type.value for t in threats],
            actions_taken=actions_taken,
            security_flags=security_flags or {},
            processing_time_ms=processing_time_ms,
        )

        self.entries.append(entry)

    def get_entries(self, limit: Optional[int] = None) -> List[AuditEntry]:
        """
        Get audit log entries.

        Args:
            limit: Maximum number of entries to return (most recent first)

        Returns:
            List of audit entries
        """
        if limit:
            return self.entries[-limit:]
        return self.entries

    def clear(self) -> None:
        """Clear all audit log entries."""
        self.entries.clear()

    def to_json(self) -> List[Dict[str, Any]]:
        """Export audit log as JSON-serializable list."""
        return [entry.to_dict() for entry in self.entries]


class SecurityMetrics:
    """Track security-related metrics over time."""

    def __init__(self) -> None:
        """Initialize security metrics."""
        self.counters = {
            "xxe_attempts_detected": 0,
            "xxe_attempts_blocked": 0,
            "dangerous_pis_detected": 0,
            "dangerous_pis_stripped": 0,
            "xss_vectors_detected": 0,
            "xss_vectors_blocked": 0,
            "entity_bombs_detected": 0,
            "deep_nesting_detected": 0,
            "untrusted_inputs_processed": 0,
            "internal_inputs_processed": 0,
            "trusted_inputs_processed": 0,
            "total_threats_detected": 0,
        }
        self.start_time = datetime.utcnow()

    def increment(self, metric: str, count: int = 1) -> None:
        """
        Increment a metric counter.

        Args:
            metric: Metric name
            count: Amount to increment by (default: 1)
        """
        if metric in self.counters:
            self.counters[metric] += count

    def record_threats(self, threats: List[Threat]) -> None:
        """
        Record detected threats in metrics.

        Args:
            threats: List of detected threats
        """
        self.increment("total_threats_detected", len(threats))

        for threat in threats:
            if threat.type == ThreatType.XXE_ATTEMPT:
                self.increment("xxe_attempts_detected")
            elif threat.type == ThreatType.DANGEROUS_PI:
                self.increment("dangerous_pis_detected")
            elif threat.type == ThreatType.XSS_VECTOR:
                self.increment("xss_vectors_detected")
            elif threat.type == ThreatType.ENTITY_BOMB:
                self.increment("entity_bombs_detected")
            elif threat.type == ThreatType.DEEP_NESTING:
                self.increment("deep_nesting_detected")

    def record_actions(self, actions: List[str]) -> None:
        """
        Record security actions taken.

        Args:
            actions: List of action descriptions
        """
        for action in actions:
            action_lower = action.lower()
            if "xxe" in action_lower or "entity" in action_lower:
                self.increment("xxe_attempts_blocked")
            if "php" in action_lower or "asp" in action_lower or "pi" in action_lower:
                self.increment("dangerous_pis_stripped")
            if "script" in action_lower or "xss" in action_lower:
                self.increment("xss_vectors_blocked")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get current statistics.

        Returns:
            Dictionary of metric names and values
        """
        uptime = (datetime.utcnow() - self.start_time).total_seconds()

        return {
            "counters": self.counters.copy(),
            "uptime_seconds": uptime,
            "last_updated": datetime.utcnow().isoformat(),
        }

    def reset(self) -> None:
        """Reset all metrics to zero."""
        for key in self.counters:
            self.counters[key] = 0
        self.start_time = datetime.utcnow()


__all__ = [
    "AuditEntry",
    "AuditLogger",
    "SecurityMetrics",
    "Threat",
    "ThreatDetector",
    "ThreatSeverity",
    "ThreatType",
]
