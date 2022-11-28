import os

from django.db import connection
from django.db import migrations

env = os.environ
db_owner = env.get('DB_AUTH_USER')


def move_tables_to_public_schema(apps, schema_editor):
    with connection.cursor() as cr:
        q = """ SELECT table_schema, table_name FROM information_schema.tables 
                WHERE table_type='BASE TABLE' AND table_schema NOT IN ('public', 'information_schema', 'pg_catalog')
                ORDER BY table_schema, table_name;
            """
        cr.execute(q)
        for i in cr.fetchall():
            q_alter_table = f"ALTER TABLE {i[0]}.{i[1]} SET SCHEMA public;"
            print(f"{q_alter_table=}")
            cr.execute(q_alter_table)


class Migration(migrations.Migration):
    """ this mig does the following:
            1. change ownership of the public schema to db owner
            2. move all tables from custom schemas to public
            3. drop custom schemas
    """
    dependencies = [('admin_cohort', '0010_delete_provider')]

    operations = [migrations.RunSQL(sql=f"ALTER SCHEMA public OWNER TO {db_owner};"),
                  migrations.RunPython(code=move_tables_to_public_schema),
                  migrations.RunSQL(sql="DROP SCHEMA IF EXISTS accesses;"),
                  migrations.RunSQL(sql="DROP SCHEMA IF EXISTS cohort;"),
                  migrations.RunSQL(sql="DROP SCHEMA IF EXISTS job_requests;"),
                  migrations.RunSQL(sql="DROP SCHEMA IF EXISTS job_request;"),
                  migrations.RunSQL(sql="DROP SCHEMA IF EXISTS environments;"),
                  migrations.RunSQL(sql="DROP SCHEMA IF EXISTS workspaces;")]
