from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django_auth_sgf.backend import SGFBackend


class Command(BaseCommand):
    help = 'Syncs the RA and Hall Staff users'

    def handle(self, *args, **options):
        ## Find all HallStaff and RAs to update them first (in case any are missing)
        ## Then just repopulate the data for every other user already in EXDB


        ldap_backend = SGFBackend()
        already_populated_usernames = set()

        # TODO: Ideally this would just read from the USER_FLAGS_BY_GROUP setting
        # Add any users from the special groups
        for group in ('RL-RESLIFE-HallStaff', 'RL-RESLIFE-RA', 'RL-RESLIFE-HallCouncil'):
            usernames = get_group_members(group)

            # Add/update the user
            for username in usernames:
                user = ldap_backend.populate_user(username)
                already_populated_usernames.add(user.username)

        # Update everyone else
        deactivated_usernames = []
        for username in get_user_model().objects.exclude(username__in=already_populated_usernames).values_list('username', flat=True):
            user = ldap_backend.populate_user(username)
            if user is None:
                deactivated_usernames.append(username)

        # Disable any accounts that no longer exist on AD
        UserGroupRelationshipModel = get_user_model().groups.through
        UserGroupRelationshipModel.objects.filter(exdbuser__username__in=deactivated_usernames).delete()
        get_user_model().objects.filter(username__in=deactivated_usernames).update(is_active=False)

        return

def get_group_members(group):
    # Find all the child groups, return all their members

    ldap_backend = SGFBackend()
    ldap_settings = ldap_backend.settings
    ldap = ldap_backend.ldap

    conn = ldap.initialize(ldap_settings.SERVER_URI)
    conn.set_option(ldap.OPT_PROTOCOL_VERSION, ldap.VERSION3)
    conn.set_option(ldap.OPT_REFERRALS, 0)
    conn.bind_s(ldap_settings.BIND_DN, ldap_settings.BIND_PASSWORD)

    search = ldap_settings.GROUP_SEARCH.search_with_additional_terms({'cn': group})


    group_DNs = {list(search.execute(conn))[0][0]}
    all_group_DNs = set(group_DNs)

    # Find all the nested groups contained in the group
    while group_DNs:
        search_str = '(|%s)' % ''.join('(memberof=%s)' % g for g in group_DNs)
        search = ldap_settings.GROUP_SEARCH.search_with_additional_term_string(search_str)

        group_DNs = {x[0] for x in list(search.execute(conn))}
        all_group_DNs |= group_DNs


    # Find the members of all the groups
    search_str = '(&(objectClass=person)(|%s))' % ''.join('(memberof=%s)' % g for g in all_group_DNs)
    user_search = ldap_settings.USER_SEARCH.search_with_additional_term_string('') # Make a copy of the original
    if hasattr(user_search, 'searches'):
        # LDAPSearchUnion
        for search in user_search.searches:
            search.filterstr = search_str
    else:
        # LDAPSearch
        user_search.filterstr = search_str

    usernames = {u[1]['cn'][0] for u in user_search.execute(conn)}

    return usernames
