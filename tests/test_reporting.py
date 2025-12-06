"""Tests for repair reporting and diagnostics."""

import pytest

from xenon import RepairAction, RepairReport, RepairType, TrustLevel, repair_xml_with_report


class TestRepairReport:
    """Test RepairReport class functionality."""

    def test_empty_report(self):
        """Test report with no repairs."""
        report = RepairReport(original_xml="<root></root>", repaired_xml="<root></root>")
        assert len(report) == 0
        assert not report  # Should be falsy
        assert "No repairs needed" in report.summary()

    def test_add_action(self):
        """Test adding repair actions."""
        report = RepairReport(original_xml="<root>", repaired_xml="<root></root>")
        report.add_action(
            RepairType.TRUNCATION,
            "Added closing tag",
            location="line 1",
            before="<root>",
            after="<root></root>",
        )

        assert len(report) == 1
        assert report  # Should be truthy
        assert report.actions[0].repair_type == RepairType.TRUNCATION
        assert report.actions[0].description == "Added closing tag"
        assert report.actions[0].location == "line 1"

    def test_summary(self):
        """Test summary generation."""
        report = RepairReport(original_xml="<root>", repaired_xml="<root></root>")
        report.add_action(RepairType.TRUNCATION, "Added closing tag")
        report.add_action(RepairType.UNESCAPED_ENTITY, "Escaped ampersand")

        summary = report.summary()
        assert "2 repair(s)" in summary
        assert "Added closing tag" in summary
        assert "Escaped ampersand" in summary

    def test_by_type(self):
        """Test grouping actions by type."""
        report = RepairReport(original_xml="<root>", repaired_xml="<root></root>")
        report.add_action(RepairType.TRUNCATION, "Fix 1")
        report.add_action(RepairType.TRUNCATION, "Fix 2")
        report.add_action(RepairType.UNESCAPED_ENTITY, "Fix 3")

        grouped = report.by_type()
        assert len(grouped[RepairType.TRUNCATION]) == 2
        assert len(grouped[RepairType.UNESCAPED_ENTITY]) == 1

    def test_statistics(self):
        """Test statistics generation."""
        report = RepairReport(original_xml="<root>", repaired_xml="<root></root>")
        report.add_action(RepairType.TRUNCATION, "Fix 1")
        report.add_action(RepairType.TRUNCATION, "Fix 2")

        stats = report.statistics()
        assert stats["total_repairs"] == 2
        assert stats["input_size"] == 6
        assert stats["output_size"] == 13
        assert stats["truncation_count"] == 2

    def test_to_dict(self):
        """Test conversion to dictionary."""
        report = RepairReport(original_xml="<root>", repaired_xml="<root></root>")
        report.add_action(
            RepairType.TRUNCATION,
            "Added closing tag",
            location="end",
            before="<root>",
            after="<root></root>",
        )

        data = report.to_dict()
        assert data["original_length"] == 6
        assert data["repaired_length"] == 13
        assert data["repair_count"] == 1
        assert len(data["actions"]) == 1
        assert data["actions"][0]["type"] == "truncation"
        assert data["actions"][0]["description"] == "Added closing tag"

    def test_has_security_issues(self):
        """Test security issue detection."""
        report = RepairReport(original_xml="", repaired_xml="")
        assert not report.has_security_issues()

        report.add_action(RepairType.TRUNCATION, "Normal fix")
        assert not report.has_security_issues()

        report.add_action(RepairType.DANGEROUS_PI_STRIPPED, "Removed PHP")
        assert report.has_security_issues()


class TestRepairAction:
    """Test RepairAction class."""

    def test_basic_action(self):
        """Test basic action creation."""
        action = RepairAction(repair_type=RepairType.TRUNCATION, description="Added closing tag")
        assert action.repair_type == RepairType.TRUNCATION
        assert action.description == "Added closing tag"
        assert action.location == ""
        assert action.before == ""
        assert action.after == ""

    def test_action_with_all_fields(self):
        """Test action with all fields."""
        action = RepairAction(
            repair_type=RepairType.MALFORMED_ATTRIBUTE,
            description="Added quotes",
            location="line 5, tag 'item'",
            before="name=john",
            after='name="john"',
        )
        assert action.location == "line 5, tag 'item'"
        assert action.before == "name=john"
        assert action.after == 'name="john"'

    def test_action_string_representation(self):
        """Test __str__ method."""
        action = RepairAction(repair_type=RepairType.TRUNCATION, description="Added closing tag")
        s = str(action)
        assert "[truncation]" in s
        assert "Added closing tag" in s

        action = RepairAction(
            repair_type=RepairType.MALFORMED_ATTRIBUTE,
            description="Added quotes",
            location="line 5",
            before="name=john",
            after='name="john"',
        )
        s = str(action)
        assert "at line 5" in s
        assert "'name=john' → 'name=\"john\"'" in s


class TestRepairXMLWithReport:
    """Test repair_xml_with_report() function."""

    def test_no_repairs_needed(self):
        """Test well-formed XML."""
        xml = "<root><item>Hello</item></root>"
        result, report = repair_xml_with_report(xml, trust=TrustLevel.TRUSTED)

        assert result == xml
        assert len(report) == 0
        assert "No repairs needed" in report.summary()

    def test_truncation_repair(self):
        """Test truncation detection."""
        xml = "<root><item>Hello"
        result, report = repair_xml_with_report(xml, trust=TrustLevel.TRUSTED)

        assert "</item>" in result
        assert "</root>" in result
        assert len(report) > 0

        # Check that truncation was detected
        types = [a.repair_type for a in report.actions]
        assert RepairType.TRUNCATION in types

    def test_entity_escaping_repair(self):
        """Test entity escaping detection."""
        xml = "<root>Tom & Jerry</root>"
        result, report = repair_xml_with_report(xml, trust=TrustLevel.TRUSTED)

        assert "&amp;" in result
        assert len(report.actions) == 1
        assert report.actions[0].repair_type == RepairType.UNESCAPED_ENTITY

    def test_attribute_repair(self):
        """Test attribute repair detection."""
        xml = "<root><item name=john>Hello</item></root>"
        result, report = repair_xml_with_report(xml, trust=TrustLevel.TRUSTED)

        assert 'name="john"' in result
        assert len(report.actions) == 1
        assert report.actions[0].repair_type == RepairType.MALFORMED_ATTRIBUTE

    def test_multiple_repairs(self):
        """Test multiple repairs in one document."""
        xml = "<root><item name=john>Tom & Jerry"
        result, report = repair_xml_with_report(xml, trust=TrustLevel.TRUSTED)

        # Should have multiple repairs
        assert len(report) >= 2

        # Should have repaired multiple issues
        assert "</item>" in result
        assert "</root>" in result

    def test_report_structure(self):
        """Test report has correct structure."""
        xml = "<root><item>Hello"
        result, report = repair_xml_with_report(xml, trust=TrustLevel.TRUSTED)

        assert isinstance(report, RepairReport)
        assert report.original_xml == xml
        assert report.repaired_xml == result
        assert isinstance(report.actions, list)

        # Can convert to dict
        data = report.to_dict()
        assert isinstance(data, dict)
        assert "actions" in data
        assert "statistics" in data

    def test_report_is_truthy_when_repairs_made(self):
        """Test that report evaluates to True when repairs were made."""
        xml = "<root><item>Hello"
        _result, report = repair_xml_with_report(xml, trust=TrustLevel.TRUSTED)

        # Report should be truthy if repairs were made
        if len(report) > 0:
            assert report
        else:
            assert not report

    def test_report_statistics_accuracy(self):
        """Test that statistics are accurate."""
        xml = "<root><item>Hello"
        result, report = repair_xml_with_report(xml, trust=TrustLevel.TRUSTED)

        stats = report.statistics()
        assert stats["total_repairs"] == len(report)
        assert stats["input_size"] == len(xml)
        assert stats["output_size"] == len(result)

    def test_complex_report_accuracy(self):
        """Test a complex scenario with multiple, specific repairs."""
        xml = "Here is the XML: <?php echo 'XSS'; ?><root><item name=john>data"
        # This XML has:
        # 1. Conversational fluff at the start.
        # 2. A dangerous PHP processing instruction.
        # 3. An unquoted attribute.
        # 4. Truncation (missing closing tags for item and root).

        _result, report = repair_xml_with_report(xml, trust=TrustLevel.UNTRUSTED)

        assert len(report.actions) == 4

        action_types = {action.repair_type for action in report.actions}

        assert RepairType.CONVERSATIONAL_FLUFF in action_types
        assert RepairType.DANGEROUS_PI_STRIPPED in action_types
        assert RepairType.MALFORMED_ATTRIBUTE in action_types
        assert RepairType.TRUNCATION in action_types
