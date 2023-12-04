import re

pm_jid_re = re.compile('^[a-z_0-9\\.]{2,30}(_[a-z0-9]{3})?$')
alias_jid_re = re.compile('^[a-z0-9_-]{52}_[ab]$')
group_alias_jid_re = re.compile('^[a-z0-9_-]{52}_a$')
anon_alias_jid_re = re.compile('^[a-z0-9_-]{52}_b$')


def is_valid_jid(jid: str) -> bool:
    """
    Returns true if this is a valid JID (PMs, Groups, Alias JIDs)
    """
    if jid is None:
        return False
    if len(jid) == 67:
        return is_alias_jid(jid)
    elif jid.endswith('_g@groups.kik.com'):
        return is_group_jid(jid)
    else:
        return is_pm_jid(jid)


def is_pm_jid(jid: str) -> bool:
    """
    Returns true if this is a valid PM JID.

    PM JIDs always start with the real username of the user,
    followed by an optional underscore and 3 random alphameric characters.
    """
    if jid is None or not 15 <= len(jid) <= 47:
        return False
    if not jid.endswith('@talk.kik.com'):
        return False

    local_part = jid[:-13]
    return re.match(pm_jid_re, local_part) is not None


def is_group_jid(jid: str) -> bool:
    """
    Returns true if this is a valid Group JID.

    Group JIDs are used to manage / talk to a specific group.
    """
    if jid is None or len(jid) != 30:
        return False
    if not jid.endswith('_g@groups.kik.com'):
        return False
    group_id = jid[0:13]
    if not group_id.isdigit():
        return False

    group_number = int(group_id)
    # See XiGid in protobuf docs for an explanation
    return 1099511627776 <= group_number <= 2199023255551


def is_alias_jid(jid: str) -> bool:
    """
    Returns true if this is a valid Alias JID (public group or anon matching).

    Alias JIDs are used by Kik to conceal the real JID / username of the sender.
    """
    if jid is None or len(jid) != 67:
        return False
    if not jid.endswith('@talk.kik.com'):
        return False
    local_part = jid[0:54]
    return re.match(alias_jid_re, local_part) is not None


def is_group_alias_jid(jid: str) -> bool:
    """
    Returns true if this is a valid public group alias JID.

    These are only found in public groups, have a length of 67, and always end in '_a@talk.kik.com'
    """
    if jid is None or len(jid) != 67:
        return False
    if not jid.endswith('_a@talk.kik.com'):
        return False
    local_part = jid[0:54]
    return re.match(group_alias_jid_re, local_part) is not None


def is_anon_alias_jid(jid: str) -> bool:
    """
    Returns true if this is a valid anon matching JID.
    """
    if jid is None or len(jid) != 67:
        return False
    if not jid.endswith('_b@talk.kik.com'):
        return False
    local_part = jid[0:54]
    return re.match(anon_alias_jid_re, local_part) is not None
