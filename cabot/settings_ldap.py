import os
import ldap
from django_auth_ldap.config import LDAPSearch, GroupOfNamesType


# Baseline configuration.
AUTH_LDAP_SERVER_URI = os.environ.get('AUTH_LDAP_SERVER_URI', 'ldap://ldap.example.com')

AUTH_LDAP_BIND_DN =  os.environ.get('AUTH_LDAP_BIND_DN', 'cn=Manager,dc=example,dc=com')
AUTH_LDAP_BIND_PASSWORD = os.environ.get('AUTH_LDAP_BIND_PASSWORD', '')
AUTH_LDAP_USER_SEARCH = LDAPSearch(os.environ.get('AUTH_LDAP_USER_SEARCH', 'ou=user,dc=example,dc=com'),
    ldap.SCOPE_SUBTREE, '(uid=%(user)s)')

# Populate the Django user from the LDAP directory.
AUTH_LDAP_USER_ATTR_MAP = {
    'first_name': 'givenName',
    'last_name': 'sn',
    'email': 'mail',
}
