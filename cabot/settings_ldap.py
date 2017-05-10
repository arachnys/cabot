import distutils
import os
import ldap
from django_auth_ldap.config import LDAPSearch, PosixGroupType


# Baseline configuration.
AUTH_LDAP_SERVER_URI = os.environ.get('AUTH_LDAP_SERVER_URI', 'ldap://ldap.example.com')

AUTH_LDAP_BIND_DN =  os.environ.get('AUTH_LDAP_BIND_DN', 'cn=Manager,dc=example,dc=com')
AUTH_LDAP_BIND_PASSWORD = os.environ.get('AUTH_LDAP_BIND_PASSWORD', '')
AUTH_LDAP_USER_FILTER =  os.environ.get('AUTH_LDAP_USER_FILTER', '(uid=%(user)s)')
AUTH_LDAP_USER_SEARCH = LDAPSearch(os.environ.get('AUTH_LDAP_USER_SEARCH', 'ou=user,dc=example,dc=com'),
    ldap.SCOPE_SUBTREE, AUTH_LDAP_USER_FILTER)

# Populate the Django user from the LDAP directory.
AUTH_LDAP_USER_ATTR_MAP = {
    'first_name': 'givenName',
    'last_name': 'sn',
    'email': 'mail',
}

AUTH_LDAP_ALWAYS_UPDATE_USER = bool(distutils.util.strtobool(os.environ.get('AUTH_LDAP_ALWAYS_UPDATE_USER', 'True')))
AUTH_LDAP_GROUP_TYPE = PosixGroupType()
AUTH_LDAP_GROUP_SEARCH = LDAPSearch(os.environ.get('AUTH_LDAP_GROUP_SEARCH', 'ou=group,dc=example,dc=com'), ldap.SCOPE_SUBTREE, "(objectClass=posixGroup)")

AUTH_LDAP_USER_FLAGS_BY_GROUP = {}
for user_flag in ["is_active", "is_staff", "is_superuser"]:
    env_variable = "AUTH_LDAP_USER_FLAGS_BY_GROUP_{user_flag}".format(user_flag=user_flag.upper())
    value = os.environ.get(env_variable)
    if value:
        AUTH_LDAP_USER_FLAGS_BY_GROUP[user_flag] = value