"""Opportunity Finder backend package."""

# Configure native OS certificate stores before HTTP clients import SSLContext.
# This keeps verification enabled while supporting managed Windows/Linux roots.
import truststore

truststore.inject_into_ssl()
