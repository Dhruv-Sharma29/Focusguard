"""Tests for the blocklist / sensitive site filter."""

from focusguard.security.blocklist import is_sensitive, sanitize_title, REDACTED_TITLE


class TestIsSensitive:
    def test_banking_site(self):
        assert is_sensitive("Chase Bank - Account Summary")

    def test_healthcare_site(self):
        assert is_sensitive("MyChart - Patient Portal")

    def test_password_manager(self):
        assert is_sensitive("1Password - Vault")

    def test_private_browsing(self):
        assert is_sensitive("Private Browsing — Firefox")

    def test_normal_site_not_sensitive(self):
        assert not is_sensitive("Stack Overflow - Python question")

    def test_coding_not_sensitive(self):
        assert not is_sensitive("main.py — Visual Studio Code")

    def test_case_insensitive(self):
        assert is_sensitive("CHASE.COM - Banking")
        assert is_sensitive("PayPal - Send Money")

    def test_empty_string(self):
        assert not is_sensitive("")

    def test_custom_blocklist(self):
        custom = ["secret-project", "internal-wiki"]
        assert is_sensitive("secret-project dashboard", custom)
        assert not is_sensitive("Stack Overflow", custom)


class TestSanitizeTitle:
    def test_sensitive_title_redacted(self):
        assert sanitize_title("Chase Bank - Accounts") == REDACTED_TITLE

    def test_safe_title_unchanged(self):
        title = "main.py — VS Code"
        assert sanitize_title(title) == title

    def test_none_input(self):
        assert sanitize_title(None) is None

    def test_redacted_value(self):
        assert REDACTED_TITLE == "[private]"
