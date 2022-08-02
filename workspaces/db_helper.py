import json
from typing import List

import yaml

from workspaces.models import Account, Kernel, RangerHivePolicy, \
    RHP_TYPE_DEFAULT_USER, JupyterMachine, LdapGroup
from workspaces.serializers import DbAccountSerializer

USER_KEY = "users"


def create_vault(loader, node):
    value = loader.construct_scalar(node)
    return str(value)


class Loader(yaml.SafeLoader):
    pass


yaml.add_constructor(u'!vault', create_vault, Loader)

kernels = dict()
jup_machines = dict()
ranger_hive_policies = dict()
ldap_groups = dict()

POLICY_FIELDS_REQUIRED_IF_NOT_DEFAULT = [
    'ranger_hive_policy_db', 'ranger_hive_policy_db_tables',
    'ranger_hive_policy_db_work'
]


def get_kernel(name: str) -> Kernel:
    if name in kernels:
        return kernels[name]
    else:
        k, _ = Kernel.objects.get_or_create(name=name)
        kernels[name] = k
        return k


def get_jupyter_machine(name: str) -> JupyterMachine:
    if name in jup_machines:
        return jup_machines[name]
    else:
        m, _ = JupyterMachine.objects.get_or_create(name=name)
        jup_machines[name] = m
        return m


def get_ldap_group(name: str) -> LdapGroup:
    if name in ldap_groups:
        return ldap_groups[name]
    else:
        lg, _ = LdapGroup.objects.get_or_create(name=name)
        ldap_groups[name] = lg
        return lg


def build_policy_summary(user: dict) -> str:
    return "_".join([user[k] for k in POLICY_FIELDS_REQUIRED_IF_NOT_DEFAULT])


def get_ranger_hive_policy(user: dict) -> RangerHivePolicy:
    if user['ranger_hive_policy_type'] == RHP_TYPE_DEFAULT_USER:
        if RHP_TYPE_DEFAULT_USER in ranger_hive_policies:
            return ranger_hive_policies[RHP_TYPE_DEFAULT_USER]
        else:
            p, _ = RangerHivePolicy.objects.get_or_create(
                policy_type=RHP_TYPE_DEFAULT_USER
            )
            ranger_hive_policies[RHP_TYPE_DEFAULT_USER] = p
            return p
    else:
        if 'ranger_hive_policy_db_imagerie' not in user \
                and user.get('db_imagerie', False):
            raise Exception(
                f"MISSING VALUES: for a user, 'ranger_hive_policy_type' "
                f"value is not '{RHP_TYPE_DEFAULT_USER}', 'db_imagerie' is set "
                f"to True but no  'ranger_hive_policy_db_imagerie' is provided. "
                f"User details : {str(user)}")

        if any([
            k not in user for k in POLICY_FIELDS_REQUIRED_IF_NOT_DEFAULT
        ]):
            raise Exception(
                f"MISSING VALUES: for this user, 'ranger_hive_policy_type' "
                f"value is not '{RHP_TYPE_DEFAULT_USER}' and one of "
                f"{','.join(POLICY_FIELDS_REQUIRED_IF_NOT_DEFAULT)} fields "
                f"is not set. User details : {str(user)}"
            )

        k = build_policy_summary(user)
        if k not in ranger_hive_policies:
            p, _ = RangerHivePolicy.objects.get_or_create(
                policy_type=user['ranger_hive_policy_type'],
                db=user['ranger_hive_policy_db'],
                db_tables=user['ranger_hive_policy_db_tables'],
                db_imagerie=user.get('ranger_hive_policy_db_imagerie', None),
                db_work=user['ranger_hive_policy_db_work'],
            )
            ranger_hive_policies[k] = p
            return p


def yaml_to_db(yaml_content: str):
    print("Starts updating environments' database")
    print("Loading yaml content")

    y = yaml.load(yaml_content, Loader)

    if USER_KEY not in y:
        raise Exception(
            f"FORMAT UNEXPECTED: Could not find '{USER_KEY}' field in yaml"
        )

    users = y['users']
    if not isinstance(users, dict):
        raise Exception(f"FORMAT UNEXPECTED: '{USER_KEY}' value in not a dict")
    print(f"{len(users)} users found")

    to_update: List[Account] = Account.objects \
        .filter(username__in=[name for name in users.keys()])
    updated_usernames = []

    count, length = 0, len(to_update)
    for a in to_update:
        try:
            user = users[a.username]
            a.__dict__.update(dict(
                name=user['name'],
                firstname=user['firstname'],
                lastname=user['lastname'],
                mail=user['mail'],
                gid=user['gid'],
                group=user['group'],
                home=user['home'],
                conda_enable=user['conda']['enable'],
                conda_py_version=user['conda']['py_version'],
                conda_r=user['conda']['r'],
                ssh=user['ssh'],
                brat_port=user.get('brat_port', None)
                if isinstance(user.get('brat_port', None), int) else None,
                tensorboard_port=user.get('tensorboard_port', None)
                if isinstance(user.get('tensorboard_port', None),
                              int) else None,
                airflow_port=user.get('airflow_port', None)
                if isinstance(user.get('airflow_port', None), int) else None,
                db_imagerie=user.get('db_imagerie', False),
                ranger_hive_policy=get_ranger_hive_policy(user),
                aphp_ldap_group_dn=user['aphp_ldap_group_dn'],
                spark_port_start=user['spark_port_start'],
            ))

            a.kernels.set([
                get_kernel(n) for n in [
                    name for name, used in user['kernels'].items()
                    if used
                ]]
            )
            a.jupyter_machines.set([
                get_jupyter_machine(n) for n in
                user['jupyter_machines']
            ])
            if user.get('ldap_groups', None):
                a.ldap_groups.set([
                    get_ldap_group(n) for n in user['ldap_groups'].split(" ")
                ])
            a.save()
            updated_usernames.append(a.username)
            count += 1
            print(f"Updated {count} accounts out of {length}   ", end="\r")
        except Exception:
            pass

    print("Updates finished")

    to_create = [
        (n, u) for (n, u) in users.items() if n not in updated_usernames
    ]
    count, length = 0, len(to_create)
    for username, user in to_create:
        try:
            a = Account(
                username=username,
                name=user['name'],
                firstname=user['firstname'],
                lastname=user['lastname'],
                mail=user['mail'],
                gid=user['gid'],
                group=user['group'],
                home=user['home'],
                conda_enable=user['conda']['enable'],
                conda_py_version=user['conda']['py_version'],
                conda_r=user['conda']['r'],
                ssh=user['ssh'],
                brat_port=user.get('brat_port', None)
                if isinstance(user.get('brat_port', None), int) else None,
                tensorboard_port=user.get('tensorboard_port', None)
                if isinstance(user.get('tensorboard_port', None),
                              int) else None,
                airflow_port=user.get('airflow_port', None)
                if isinstance(user.get('airflow_port', None), int) else None,
                db_imagerie=user.get('db_imagerie', False),
                ranger_hive_policy=get_ranger_hive_policy(user),
                aphp_ldap_group_dn=user['aphp_ldap_group_dn'],
                spark_port_start=user['spark_port_start'],
            )
            a.save()

            a.kernels.set([
                get_kernel(n) for n in [
                    name for name, used in user['kernels'].items()
                    if used
                ]]
            )
            a.jupyter_machines.set([
                get_jupyter_machine(n) for n in
                user['jupyter_machines']
            ])
            if user.get('ldap_groups', None):
                a.ldap_groups.set([
                    get_ldap_group(n) for n in user['ldap_groups'].split(" ")
                ])
            a.save()
            count += 1
            print(f"Added {count} new accounts out of {length}   ", end="\r")
        except Exception:
            pass

    print("Finished updating accounts")
    return


def yaml_file_to_db(yaml_file_path: str):
    with open(yaml_file_path, 'r') as f:
        r = yaml_to_db(f.read())
        f.close()
    return r


def db_to_yaml() -> str:
    accounts = Account.objects.all()

    data = DbAccountSerializer(accounts, many=True).data
    list_data = json.loads(json.dumps(data))
    dict_data = dict([(d.get('username'), d) for d in list_data])

    # with open('new_vars.yaml', 'w') as f:
    #     yaml.dump({'users': dict_data}, f)
    return yaml.dump({'users': dict_data})
